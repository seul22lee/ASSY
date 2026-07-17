"""THE RUN (E-track 1): command → ①②③④ (LLM) → ⑤ → ⑥ → t0 → t1 → t2 → report, fully automatic.

N repeats, because LLM nondeterminism is DATA. Nothing is hand-edited between stages: if the model
fails a gate and retries out, that is the result and it is recorded as such. The deterministic
machine (⑤–⑨) is the grader; this script only carries the IR to it and writes down what happened.

Run:  ./bin/py m9_llm_stages/run_e_track.py [N] [--seedless]
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ontology.schema import DesignPlan
from pipeline import s1_intent, s2_behavior, s3_decompose, s4_interface
from pipeline.llm_client import backend_info, stage_log_summary
from pipeline.stage_failure import StageFailure
from tasks.build_goldens import anchor_easy
from tests.eval_llm_stages import score, scorecard_md

OUT = Path(__file__).parent / "out"
# MECHSYNTH §8.1 — the Easy anchor command, verbatim.
COMMAND = ("Design a small box whose lid opens and closes and latches shut. "
           "Plastic, for 3D printing.")

LLM_STAGES = (("①", "s1", s1_intent), ("②", "s2", s2_behavior),
              ("③", "s3", s3_decompose), ("④", "s4", s4_interface))


def _fail(kind, stage, err):
    return {"reached": stage, "class": kind, "error": str(err)[:600]}


def run_once(i: int, temperature: float) -> dict:
    """One full attempt. Returns a record; never raises — a crash IS a datum."""
    t0 = time.time()
    rec = {"run": i, "command": COMMAND, "backend": backend_info(),
           "temperature": temperature, "stages": {}, "failure": None}
    ir = DesignPlan(task_id=f"llm_easy_run{i}", command=COMMAND,
                    functions=[], behaviors=[], pieces=[])

    # --- ①–④ : the LLM stages -----------------------------------------------------------
    for sym, key, mod in LLM_STAGES:
        try:
            ir = mod.run(ir)
            rec["stages"][key] = "PASS"
        except StageFailure as e:
            rec["stages"][key] = f"FAIL({e.code})"
            rec["failure"] = _fail("gate_failure_after_retries", key, e)
            break
        except Exception as e:
            rec["stages"][key] = "ERROR"
            rec["failure"] = _fail("unexpected_exception", key, e)
            rec["traceback"] = traceback.format_exc()[-1200:]
            break

    (OUT / f"stage_log_run{i}.json").write_text(json.dumps(
        {"run": i, "backend": backend_info(), "command": COMMAND,
         "summary": stage_log_summary(ir), "calls": ir.stage_log}, indent=2))
    (OUT / f"ir_run{i}.json").write_text(ir.model_dump_json(indent=2))

    llm_ok = all(v == "PASS" for v in rec["stages"].values()) and len(rec["stages"]) == 4
    rec["llm_stages_passed"] = llm_ok
    rec["retry_counts"] = {k: v["retries"] for k, v in stage_log_summary(ir).items()}

    # --- score against the golden (works even on a partial IR) ---------------------------
    gold = anchor_easy("stop")
    try:
        rec["score"] = score(gold, ir)
    except Exception as e:
        rec["score"] = {"error": str(e)[:200]}

    # --- ⑤ → ⑥ → t0/t1/t2 : the deterministic grader -------------------------------------
    downstream = {}
    if llm_ok:
        try:
            from pipeline.s5_geometry import resolve_plan
            resolve_plan(ir)
            downstream["s5_resolve"] = "PASS"
        except StageFailure as e:
            downstream["s5_resolve"] = f"FAIL({e.code})"
            rec["failure"] = rec["failure"] or _fail("stage_failure", "s5", e)
        except Exception as e:
            downstream["s5_resolve"] = f"ERROR: {type(e).__name__}"
            rec["failure"] = rec["failure"] or _fail("unexpected_exception", "s5", e)

        if downstream.get("s5_resolve") == "PASS":
            try:
                from pipeline.compile_assembly import compile_assembly
                ca = compile_assembly(ir)
                downstream["s6_compile"] = f"PASS ({len(ca.parts)} parts)"
                (OUT / f"ir_run{i}.json").write_text(ir.model_dump_json(indent=2))
            except Exception as e:
                downstream["s6_compile"] = f"FAIL: {type(e).__name__}: {str(e)[:160]}"
                rec["failure"] = rec["failure"] or _fail("compile_failure", "s6", e)
                ca = None

            if downstream.get("s6_compile", "").startswith("PASS"):
                try:
                    from verify.assembly_rules import evaluate
                    ars = [evaluate(ir, ar, {"parts": ca.parts}, next(iter(ca.axes.values())))
                           for ar in ir.assembly_rules]
                    downstream["t0_assembly_rules"] = (f"{sum(a['ok'] for a in ars)}/{len(ars)} PASS"
                                                       if ars else "n/a (no AssemblyRules in IR)")
                except Exception as e:
                    downstream["t0_assembly_rules"] = f"ERROR: {type(e).__name__}: {str(e)[:90]}"
                try:
                    from tasks.run_m8_t2 import build_hints, stop_angle_from_ir
                    from verify.t2_physics.runner import t2
                    hints = build_hints(ir, ca)
                    base = next(p.id for p in ir.pieces if p.is_base or p.role == "base")
                    mover = next((p.id for p in ir.pieces
                                  if p.provenance == "functional" and p.id != base), None)
                    pin = next((p.id for p in ir.pieces if p.provenance == "hardware"), None)
                    roles = {base: "base", mover: "mover"}
                    if pin:
                        roles[pin] = "hardware"
                    parts = {k: ca.parts[k] for k in roles}
                    bp = ir.piece(base).params
                    res = t2(parts, hints, next(iter(ca.axes.values())), roles, ["V-A", "V-B"],
                             OUT / f"t2_run{i}", base, mover, pin, f"llm{i}",
                             tip_point=(0.0, bp["box_w"] / 2, bp["box_h"]),
                             stop_angle_deg=stop_angle_from_ir(ir), plan=ir,
                             decision_row="E-track run: LLM-authored IR through stage-⑨")
                    downstream["t2_physics"] = {
                        m: f"{e['p_hinge'].get('seeds_passed', 0)}/5"
                        for m, e in res["modes"].items()}
                    downstream["t2_verdict"] = res["verdict"]
                except Exception as e:
                    downstream["t2_physics"] = f"ERROR: {type(e).__name__}: {str(e)[:160]}"
                    rec["failure"] = rec["failure"] or _fail("physics_failure", "t2", e)
    rec["downstream"] = downstream
    rec["wall_s"] = round(time.time() - t0, 1)

    extra = {"LLM ①–④": "PASS" if llm_ok else f"FAIL — {rec['stages']}", **downstream}
    (OUT / f"scorecard_run{i}.md").write_text(scorecard_md(
        rec["score"], f"E-track run {i} — scorecard (LLM: {backend_info()['model']})", extra)
        if "axes" in rec.get("score", {}) else f"# run {i}: scoring unavailable\n\n{rec['score']}\n")
    return rec


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 3
    runs = []
    for i in range(1, n + 1):
        # temperature 0 would make N=3 identical and measure nothing; the brief asks for variance,
        # so the repeats sample the model's actual nondeterminism.
        temp = 0.0 if i == 1 else 0.6
        print(f"\n{'='*70}\nRUN {i}/{n}  (temperature={temp})\n{'='*70}")
        r = run_once(i, temp)
        runs.append(r)
        print(f"  stages: {r['stages']}  retries: {r.get('retry_counts')}")
        print(f"  downstream: {r['downstream']}")
        if "axes" in r.get("score", {}):
            print(f"  macro F1: {r['score']['macro_f1']}  "
                  f"stop missed: {r['score']['stop_axis']['missed']}  "
                  f"validators clean: {r['score']['validators']['clean']}")
        if r["failure"]:
            print(f"  FAILURE [{r['failure']['class']}] at {r['failure']['reached']}: "
                  f"{r['failure']['error'][:150]}")
        print(f"  wall: {r['wall_s']}s")
    (OUT / "runs.json").write_text(json.dumps(runs, indent=2))
    print(f"\nwrote {OUT/'runs.json'} + per-run scorecards/stage logs/IRs")


if __name__ == "__main__":
    main()
