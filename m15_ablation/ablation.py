"""m15 — 4-RUNG ABLATION: what does each layer of scaffolding buy? (external review ITEM 1)

A clean ladder — each ADJACENT pair isolates exactly one layer:

  A direct-CAD     command -> build123d code directly. NO ontology/IR at all.
  B monolithic-IR  ONE LLM call -> the whole IR (functions..bindings). No staging, no KG, no gates.
  C staged-no-KG   the ①②③④ pipeline, but s4 sees the FULL card vocabulary (KG narrowing removed).
  D full           the pipeline as shipped: staged + KG-narrowed + gated/retried.

    B - A  = what the ontology / IR buys      C - B  = what staging + gates buy
    D - C  = what the knowledge graph buys

Grid: 6-task core x 2 paraphrases x N=3 seeds, per rung. Bulk on the free tier; paid Pro is reserved
for the final recorded frontier column only (cost policy). Resumable: each cell writes its own JSON
and is skipped if present. Token counts come from the live stage_log (self-check on). A running cost
projection is printed; the harness STOPS if it would exceed the hard cap. Each cell writes its own
JSON and is skipped on resume if present.

Run:  ./bin/py m15_ablation/ablation.py --backend flash|pro|qwen [--tasks A1,B1] [--seeds 0] [--rungs A,B,C,D]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "m0"))

OUT = Path(__file__).parent / "out"
CELLS = OUT / "cells"

# ---- the 6-task core (feasible, each has a golden), 2 paraphrases each --------------------------
CORE = {
    "A1-snap-base": [
        "Design a snap-lid box I can push shut and pull open by hand. Plastic, for 3D printing.",
        "Make a small plastic box with a lid that clicks on and pulls off by hand, FDM-printable."],
    "A3-snap-force": [
        "Design a push-on snap-lid box that closes with no more than 60 N by hand and needs at least 15 N of pull to open.",
        "I need a push-close snap-lid box; closing should take under 60 N and opening should require 15 N or more of pull."],
    "B1-hinge-latch-base": [
        "A small hinged box whose lid latches shut at the front. Plastic, for 3D printing.",
        "A little plastic box with a lid on a hinge that snaps closed at the front. For 3D printing."],
    "B5-hinge-openangle": [
        "A hinged box whose lid opens at least 100° and settles closed within 5°.",
        "A hinged-lid box where the lid swings open past 100 degrees and rests shut within 5 degrees of closed."],
    "C1-lift-base": [
        "Design a crank-operated platform that raises and lowers a load to different heights.",
        "A platform you raise and lower to different heights by turning a crank."],
    "C4-drawer": [
        "Design a desktop cabinet whose drawer slides out horizontally when you turn a knob.",
        "A small desk cabinet with a drawer that comes out sideways when a knob is turned."],
}

# ---- pricing (Gemini public rates $/M tok; approximate) + hard cap ------------------------------
PRICE = {"pro": (1.25, 10.0), "flash": (0.30, 2.50), "qwen": (0.0, 0.0)}
HARD_CAP_USD = 5.0


def set_backend(backend: str) -> str:
    """flash|pro -> gemini tier; qwen -> local ollama. Sets env BEFORE the pipeline is used."""
    if backend in ("flash", "pro"):
        os.environ["MECHSYNTH_LLM_BACKEND"] = "gemini"
        os.environ["MECHSYNTH_LLM_TIER"] = backend
        os.environ.pop("MECHSYNTH_LLM_MODEL", None)
    elif backend == "qwen":
        os.environ["MECHSYNTH_LLM_BACKEND"] = "ollama"
        os.environ["MECHSYNTH_LLM_MODEL"] = "qwen3-coder:latest"
    else:
        raise SystemExit(f"unknown backend {backend!r}")
    for m in [k for k in sys.modules if k.startswith("pipeline.llm_client")]:
        del sys.modules[m]                     # BACKEND binds at import — force a fresh read
    from pipeline.llm_client import resolve_model
    return resolve_model()


# ---- rung C: staged-no-KG — candidates() returns the FULL element vocabulary -------------------
@contextmanager
def no_kg():
    """Remove the knowledge-graph narrowing: every behaviour's candidate list becomes the whole
    element vocabulary, so s4 chooses from all cards (and the G4 allow-set opens up to match)."""
    import pipeline.s4_interface as S4
    from knowledge.cards.base import CARD_REGISTRY
    all_elems = [cid for cid, c in CARD_REGISTRY.items()
                 if getattr(c, "card_class", "element") != "feature"]
    orig_c, orig_w = S4.candidates, S4.why
    S4.candidates = lambda b: list(all_elems)
    S4.why = lambda cid, b: [f"offered (KG narrowing ablated — full vocabulary)"]
    try:
        yield
    finally:
        S4.candidates, S4.why = orig_c, orig_w


def expectation_from_golden(task_id):
    """The ② G2 expectation, CALIBRATED PER TASK from the golden's behaviour profile — the objective
    generalisation of the hardcoded EASY_EXPECTATION (which is itself the hinge golden's profile).
    It is a GATE, never whispered into the prompt (s2 docstring), so this leaks nothing to the LLM;
    it only asks 'did ② recover the essential phases this task needs?'. Returns EASY_EXPECTATION's
    tuple shape: (phase, {acceptable kinds}, min_range_or_None, why)."""
    from ontology.schema import DesignPlan
    gp = ROOT / "tasks" / "benchmark" / "goldens" / f"{task_id}.json"
    if not gp.exists():
        return None
    g = DesignPlan.model_validate_json(gp.read_text())
    use_kinds, use_min, has_static, has_assembly = set(), None, False, False
    for b in g.behaviors:
        ph = getattr(b.phase, "value", b.phase)
        k = getattr(b.motion.kind, "value", b.motion.kind)
        bd = getattr(b.motion.bound, "value", b.motion.bound)
        if ph == "use" and k in ("rotation", "translation", "rot_to_trans"):
            use_kinds.add(k)
            if bd == "min" and b.motion.range_value:
                use_min = max(use_min or 0.0, float(b.motion.range_value))
        if ph == "static" and k in ("fixed", "snap_event"):
            has_static = True
        if ph == "assembly" and k in ("translation", "snap_event"):
            has_assembly = True
    exp = []
    if use_kinds:
        exp.append(("use", set(use_kinds), use_min,
                    f"a use-phase {'/'.join(sorted(use_kinds))}"
                    + (f" of at least {use_min:g}" if use_min else "")))
    if has_static:
        exp.append(("static", {"fixed", "snap_event"}, None, "a static-phase hold"))
    if has_assembly:
        exp.append(("assembly", {"translation", "snap_event"}, None, "an assembly-phase fastening"))
    return tuple(exp)


def run_staged(command, task_id, kg=True):
    """Rungs C/D: the ①②③④ pipeline. kg=False ablates the knowledge graph (rung C). The ② G2
    expectation is calibrated per task from its golden (never in the prompt — a gate only)."""
    from ontology.schema import DesignPlan
    from pipeline import s1_intent, s2_behavior, s3_decompose, s4_interface
    ir = DesignPlan(task_id=task_id, command=command, functions=[], behaviors=[], pieces=[])
    exp = expectation_from_golden(task_id)
    ctx_dict = {"expectation": exp} if exp else {}
    stages = {}
    kgctx = no_kg() if not kg else _nullctx()
    with kgctx:
        for key, mod in (("s1", s1_intent), ("s2", s2_behavior),
                         ("s3", s3_decompose), ("s4", s4_interface)):
            try:
                ir = mod.run(ir, ctx_dict)
                stages[key] = "PASS"
            except Exception as e:
                stages[key] = _stage_err(e)
                break
    return ir, stages


@contextmanager
def _nullctx():
    yield


def _stage_err(e):
    from pipeline.stage_failure import StageFailure
    if isinstance(e, StageFailure):
        return f"FAIL({e.code})"
    return f"ERROR:{type(e).__name__}"


# ---- rung B: monolithic — ONE call for the entire IR, then deterministic assembly --------------
def _monolithic_schema():
    from pipeline import s1_intent, s2_behavior, s3_decompose, s4_interface as S4
    props = {"functions": s1_intent.SCHEMA["properties"]["functions"],
             "behaviors": s2_behavior.SCHEMA["properties"]["behaviors"],
             "pieces": s3_decompose.SCHEMA["properties"]["pieces"],
             "elements": S4.SCHEMA["properties"]["elements"],
             "bindings": S4.SCHEMA["properties"]["bindings"],
             "attributions": S4.SCHEMA["properties"].get("attributions",
                             {"type": "array", "items": {"type": "object"}})}
    return {"type": "object", "properties": props,
            "required": ["functions", "behaviors", "pieces", "elements", "bindings"]}


def _monolithic_prompt(command):
    from ontology.functional_basis import vocabulary_prompt_block
    from knowledge.cards.base import CARD_REGISTRY
    from knowledge.kg import card_brief
    from pipeline.s3_decompose import BUILDABLE
    cards = "\n\n".join(card_brief(cid) for cid, c in CARD_REGISTRY.items())
    return f"""You are a mechanical-design compiler. In ONE step, turn the request into a complete
structured design (an IR). Output a single JSON object with: functions, behaviors, pieces, elements,
bindings, attributions.

# functions — the purposes in the command
{vocabulary_prompt_block()}

# behaviors — each function's motion. phase in (assembly,use,static); motion.kind in
# (rotation,translation,rot_to_trans,fixed,snap_event). use-phase rotations/translations need
# range_value+range_unit+bound; a snap_event needs event_force_window_N=[mate_N,separate_N].

# pieces — the printed parts. Each has id, role, is_base (exactly ONE base), and a template_ref from:
{sorted(BUILDABLE)}

# elements — the mechanical cards that realise the behaviours, and their bindings to piece anchors.
# Choose card_ref from this catalogue; bind every PORT of each element to a piece anchor.
{cards}

# attributions — for each behaviour, which element realized_by / imposed_by it.

command: "{command}"
Answer with the JSON object only."""


def run_monolithic(command, task_id):
    from ontology.schema import DesignPlan, Function, Behavior, MotionSpec, Piece
    from pipeline import s4_interface as S4
    from pipeline.llm_client import _call_backend, CallRecord
    prompt = _monolithic_prompt(command)
    ir = DesignPlan(task_id=task_id, command=command, functions=[], behaviors=[], pieces=[])
    t0 = time.time()
    try:
        raw, ptok, etok = _call_backend(prompt, _monolithic_schema(), _resolve(), 0.0)
    except Exception as e:
        ir.stage_log.append({"stage": "monolithic", "ok": False, "error": str(e)[:200],
                             "tokens": {"prompt": 0, "output": 0, "total": 0}})
        return ir, {"monolithic": _stage_err(e)}
    ir.stage_log.append(CallRecord(stage="monolithic", attempt=0, model="monolithic",
                        prompt_sha256="", prompt=prompt, response_raw=raw,
                        latency_s=time.time() - t0, ok=True,
                        prompt_tokens=ptok, eval_tokens=etok).as_log())
    try:
        d = json.loads(raw)
        ir.functions = [Function(**f) for f in d["functions"]]
        bs = []
        for b in d["behaviors"]:
            m = dict(b["motion"])
            w = m.get("event_force_window_N")
            m["event_force_window_N"] = (float(w[0]), float(w[1])) if isinstance(w, list) and len(w) == 2 else None
            if m["event_force_window_N"] is None:
                m.pop("event_force_window_N")
            bs.append(Behavior(id=b["id"], phase=b["phase"], motion=MotionSpec(**m)))
        ir.behaviors = bs
        ir.pieces = [Piece(id=p["id"], role=p["role"], template_ref=p["template_ref"],
                           is_base=bool(p.get("is_base", False))) for p in d["pieces"]]
        plan = S4._build(ir, {"elements": d.get("elements", []), "bindings": d.get("bindings", []),
                              "attributions": d.get("attributions", [])})
        plan.stage_log = ir.stage_log
        return plan, {"monolithic": "PASS"}
    except Exception as e:
        return ir, {"monolithic": f"ASSEMBLE_ERROR:{type(e).__name__}: {str(e)[:120]}"}


def _resolve():
    from pipeline.llm_client import resolve_model
    return resolve_model()


# ---- downstream: does the IR become a valid, interference-free assembly? -----------------------
def downstream(ir):
    """s5 resolve -> s6 compile -> t0 assembly rules. A common functional floor for B/C/D."""
    out = {}
    try:
        from pipeline.s5_geometry import resolve_plan
        resolve_plan(ir)
        out["s5"] = "PASS"
    except Exception as e:
        out["s5"] = _stage_err(e)
        return out, False
    try:
        from pipeline.compile_assembly import compile_assembly
        ca = compile_assembly(ir)
        out["s6"] = f"PASS({len(ca.parts)})"
    except Exception as e:
        out["s6"] = f"FAIL:{type(e).__name__}"
        return out, False
    try:
        from verify.assembly_rules import evaluate
        ars = [evaluate(ir, ar, {"parts": ca.parts}, next(iter(ca.axes.values())))
               for ar in ir.assembly_rules]
        ok = all(a["ok"] for a in ars) if ars else True
        out["t0"] = f"{sum(a['ok'] for a in ars)}/{len(ars)}" if ars else "n/a"
    except Exception as e:
        out["t0"] = f"ERROR:{type(e).__name__}"; ok = False
    return out, bool(out.get("s6", "").startswith("PASS") and ok)


def score_ir(ir, task_id):
    from tests.eval_llm_stages import score_both
    from ontology.schema import DesignPlan
    gp = ROOT / "tasks" / "benchmark" / "goldens" / f"{task_id}.json"
    if not gp.exists():
        return {}
    gold = DesignPlan.model_validate_json(gp.read_text())
    try:
        sc = score_both(gold, ir)
    except Exception as e:
        return {"error": str(e)[:120]}
    axes = {a["axis"]: a for a in sc.get("axes", [])}
    def ax(sub):
        for n, a in axes.items():
            if sub in n:
                return round(a["f1"], 3)
        return 0.0
    return {"macro_f1": sc.get("macro_f1"), "elements_f1": ax("elements"),
            "bindings_f1": ax("bindings"), "behaviors_f1": ax("behaviors")}


# ---- one cell ----------------------------------------------------------------------------------
def run_cell(rung, task_id, para_i, command, seed, backend):
    tag = f"{rung}__{task_id}__p{para_i}__s{seed}__{backend}"
    cell = CELLS / f"{tag}.json"
    if cell.exists():
        return json.loads(cell.read_text()), True     # resumed
    rec = {"rung": rung, "task": task_id, "paraphrase": para_i, "seed": seed,
           "backend": backend, "tag": tag}
    t0 = time.time()
    try:
        if rung == "A":
            from m15_naive.naive import run_cell as naive_cell
            model = _resolve() if backend != "qwen" else "qwen3-coder:latest"
            mech = {"A1-snap-base": "snap-lid", "A3-snap-force": "snap-lid",
                    "B1-hinge-latch-base": "hinge+latch", "B5-hinge-openangle": "hinge+latch",
                    "C1-lift-base": "crank-lift", "C4-drawer": "rack-drawer"}[task_id]
            nr = naive_cell({"id": task_id, "axis": "core", "mechanism": mech, "command": command},
                            model, seed)
            rec.update(stages={"cad": "PASS" if nr.get("gen_ok") else "FAIL"},
                       executes=nr.get("executes", False), geometry_ok=nr.get("geometry_ok", False),
                       function=nr.get("function"), design_ok=bool(nr.get("geometry_ok")),
                       tokens={"total": nr.get("gen_tokens", 0)})
        else:
            if rung == "B":
                ir, stages = run_monolithic(command, task_id)
            elif rung == "C":
                ir, stages = run_staged(command, task_id, kg=False)
            elif rung == "D":
                ir, stages = run_staged(command, task_id, kg=True)
            else:
                raise ValueError(rung)
            allpass = all(str(v) == "PASS" for v in stages.values())
            rec["stages"] = stages
            rec["score"] = score_ir(ir, task_id) if allpass else {}
            if allpass:
                ds, ok = downstream(ir)
                rec["downstream"] = ds
                rec["design_ok"] = ok
            else:
                rec["design_ok"] = False
            from pipeline.llm_client import stage_log_summary
            rec["tokens"] = stage_log_summary(ir).get("_total", {})
    except Exception as e:
        rec["error"] = f"{type(e).__name__}: {str(e)[:160]}"
        rec["traceback"] = traceback.format_exc()[-800:]
        rec["design_ok"] = False
    rec["latency_s"] = round(time.time() - t0, 1)
    CELLS.mkdir(parents=True, exist_ok=True)
    cell.write_text(json.dumps(rec, indent=2))
    return rec, False


def cost_so_far(rows, backend):
    ci, co = PRICE[backend]
    pin = sum(r.get("tokens", {}).get("prompt_tokens", 0) for r in rows)
    pout = sum(r.get("tokens", {}).get("output_tokens", 0) for r in rows)
    # rung A reports only 'total'; approximate 30/70 split for costing
    tot_only = sum(r.get("tokens", {}).get("total", 0) for r in rows if "prompt_tokens" not in r.get("tokens", {}))
    pin += int(tot_only * 0.3); pout += int(tot_only * 0.7)
    return pin / 1e6 * ci + pout / 1e6 * co, pin, pout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="qwen", choices=["flash", "pro", "qwen"])
    ap.add_argument("--tasks", default="")
    ap.add_argument("--seeds", default="0,1,2")
    ap.add_argument("--rungs", default="A,B,C,D")
    ap.add_argument("--paras", default="0,1")
    args = ap.parse_args()
    model = set_backend(args.backend)
    print(f"backend={args.backend} model={model}")
    tasks = args.tasks.split(",") if args.tasks else list(CORE)
    seeds = [int(s) for s in args.seeds.split(",")]
    rungs = args.rungs.split(",")
    paras = [int(p) for p in args.paras.split(",")]
    OUT.mkdir(parents=True, exist_ok=True)

    rows = []
    n_total = len(rungs) * len(tasks) * len(paras) * len(seeds)
    n = 0
    for rung in rungs:
        for task_id in tasks:
            for pi in paras:
                command = CORE[task_id][pi]
                for seed in seeds:
                    n += 1
                    rec, resumed = run_cell(rung, task_id, pi, command, seed, args.backend)
                    rows.append(rec)
                    d = "✓" if rec.get("design_ok") else "✗"
                    sc = rec.get("score", {})
                    extra = (f"el={sc.get('elements_f1','—')} bd={sc.get('bindings_f1','—')}"
                             if sc else rec.get("function", ""))
                    print(f"  [{n}/{n_total}] {rec['tag']:42s} design={d} {extra}"
                          + ("  (resumed)" if resumed else ""))
                    cost, pin, pout = cost_so_far([r for r in rows if not r.get("_resumed")], args.backend)
                    if cost > HARD_CAP_USD:
                        print(f"\n!!! STOP: projected cost ${cost:.2f} exceeds hard cap ${HARD_CAP_USD} "
                              f"(in={pin} out={pout}). Reporting partial results.")
                        _dump(rows, args.backend)
                        return
    _dump(rows, args.backend)


def _dump(rows, backend):
    (OUT / f"ablation_{backend}.json").write_text(json.dumps(rows, indent=2))
    cost, pin, pout = cost_so_far(rows, backend)
    print(f"\n=== {len(rows)} cells | in={pin} out={pout} tok | est ${cost:.2f} on {backend} ===")
    # rung summary
    for rung in ("A", "B", "C", "D"):
        rs = [r for r in rows if r["rung"] == rung]
        if not rs:
            continue
        dok = sum(bool(r.get("design_ok")) for r in rs)
        bd = [r["score"]["bindings_f1"] for r in rs if r.get("score", {}).get("bindings_f1") is not None]
        el = [r["score"]["elements_f1"] for r in rs if r.get("score", {}).get("elements_f1") is not None]
        mean = lambda xs: round(sum(xs) / len(xs), 3) if xs else None
        print(f"  rung {rung}: design_ok {dok}/{len(rs)}"
              + (f" | elements_f1 {mean(el)} | bindings_f1 {mean(bd)}" if el else ""))
    print("wrote", OUT / f"ablation_{backend}.json")


if __name__ == "__main__":
    main()
