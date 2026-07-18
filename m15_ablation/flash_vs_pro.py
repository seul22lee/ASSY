"""m15 gate — FLASH vs PRO bindings check (full pipeline, Easy task, N=1 each).

Decision rule (user): flash bindings F1 >= 0.9 -> flash carries the m15 bulk; below -> bulk goes
local-qwen-where-meaningful + flash-free where model quality is not the variable, and we discuss.

Runs the SAME Easy command through ①②③④ on gemini flash then gemini pro, scores each against the
golden, and prints the ④ elements + ④ bindings numbers side by side. Stage logs (with per-call token
counts; the self-check is live) are written per tier.

Run:  ./bin/py m15_ablation/flash_vs_pro.py
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# gemini backend MUST be set before importing the pipeline (BACKEND binds at import). Tier is read
# per-call, so we switch flash<->pro at runtime via MECHSYNTH_LLM_TIER.
os.environ["MECHSYNTH_LLM_BACKEND"] = "gemini"
os.environ.pop("MECHSYNTH_LLM_MODEL", None)      # let the tier resolver choose

from ontology.schema import DesignPlan  # noqa: E402
from pipeline import s1_intent, s2_behavior, s3_decompose, s4_interface  # noqa: E402
from pipeline.llm_client import backend_info, resolve_model, stage_log_summary  # noqa: E402
from pipeline.stage_failure import StageFailure  # noqa: E402
from tasks.build_goldens import anchor_easy  # noqa: E402
from tests.eval_llm_stages import score_both  # noqa: E402

OUT = Path(__file__).parent / "out"
COMMAND = ("Design a small box whose lid opens and closes and latches shut. "
           "Plastic, for 3D printing.")
STAGES = (("s1", s1_intent), ("s2", s2_behavior), ("s3", s3_decompose), ("s4", s4_interface))


def run_tier(tier: str) -> dict:
    os.environ["MECHSYNTH_LLM_TIER"] = tier
    model = resolve_model()
    print(f"\n=== tier={tier}  model={model} ===")
    ir = DesignPlan(task_id=f"fvp_{tier}", command=COMMAND, functions=[], behaviors=[], pieces=[])
    stages = {}
    for key, mod in STAGES:
        try:
            ir = mod.run(ir)
            stages[key] = "PASS"
            print(f"  {key} PASS")
        except StageFailure as e:
            stages[key] = f"FAIL({e.code})"
            print(f"  {key} FAIL({e.code})")
            break
        except Exception as e:
            stages[key] = f"ERROR:{type(e).__name__}"
            print(f"  {key} ERROR: {e}")
            traceback.print_exc()
            break
    summ = stage_log_summary(ir)
    (OUT / f"stage_log_fvp_{tier}.json").write_text(json.dumps(
        {"tier": tier, "model": model, "backend": backend_info(),
         "summary": summ, "calls": ir.stage_log}, indent=2))
    (OUT / f"ir_fvp_{tier}.json").write_text(ir.model_dump_json(indent=2))
    gold = anchor_easy("stop")
    try:
        sc = score_both(gold, ir)
    except Exception as e:
        sc = {"error": str(e)[:200]}
    axes = {a["axis"]: a for a in sc.get("axes", [])}
    def ax(substr):
        for name, a in axes.items():
            if substr in name:
                return a
        return {"f1": 0.0, "precision": 0.0, "recall": 0.0}
    return {"tier": tier, "model": model, "stages": stages,
            "all_pass": all(v == "PASS" for v in stages.values()) and len(stages) == 4,
            "elements": ax("elements"), "bindings": ax("bindings"),
            "macro_f1": sc.get("macro_f1"), "tokens": summ.get("_total", {}),
            "elements_chosen": [(e.id, e.card_ref) for e in ir.elements],
            "n_bindings": len(ir.bindings)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    res = {t: run_tier(t) for t in ("flash", "pro")}
    (OUT / "flash_vs_pro.json").write_text(json.dumps(res, indent=2))

    print("\n" + "=" * 68)
    print(f"{'metric':28s} {'flash':>16s} {'pro':>16s}")
    print("-" * 68)
    f, p = res["flash"], res["pro"]
    print(f"{'model':28s} {f['model'][-16:]:>16s} {p['model'][-16:]:>16s}")
    print(f"{'all 4 gates pass':28s} {str(f['all_pass']):>16s} {str(p['all_pass']):>16s}")
    for k in ("elements", "bindings"):
        for m in ("f1", "precision", "recall"):
            print(f"{'④ '+k+' '+m:28s} {f[k].get(m,0):>16.3f} {p[k].get(m,0):>16.3f}")
    print(f"{'macro_f1':28s} {str(f['macro_f1'])[:16]:>16s} {str(p['macro_f1'])[:16]:>16s}")
    ft, pt = f["tokens"], p["tokens"]
    print(f"{'calls':28s} {ft.get('calls',0):>16d} {pt.get('calls',0):>16d}")
    print(f"{'prompt tok':28s} {ft.get('prompt_tokens',0):>16d} {pt.get('prompt_tokens',0):>16d}")
    print(f"{'output tok':28s} {ft.get('output_tokens',0):>16d} {pt.get('output_tokens',0):>16d}")
    print("=" * 68)
    fb = f["bindings"].get("f1", 0.0)
    verdict = "flash CARRIES the bulk" if fb >= 0.9 else "flash BELOW 0.9 -> discuss (local-qwen + flash-free split)"
    print(f"\nDECISION (rule: flash bindings F1 >= 0.9): flash bindings F1 = {fb:.3f} -> {verdict}")


if __name__ == "__main__":
    main()
