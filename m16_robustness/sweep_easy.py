"""m16 — ROBUSTNESS SWEEP, Easy stop-box P-HINGE V-B (the SECOND representative design, review pt 7).

Sweeps the hinged-latch box's P-HINGE **V-B (contact-derived)** — lid opens on the pin/bore contact,
the stop caps it, it returns closed and the pin stays retained — across μ ∈ {0.5..1.5}× frozen-0.30 ×
clearance ∈ {0.20,0.30,0.40} mm. Success = V-B passes (≥ seed_pass seeds). Reports the region.

Preset discipline (R5): frozen preset is the DEFAULT; μ swept here is a per-run EXPERIMENT PARAMETER.

Run:  ./bin/py m16_robustness/sweep_easy.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "m0"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import verify.t2_physics.mjcf as MJCF          # holds the frozen MU we monkeypatch  # noqa: E402
import verify.t2_physics.runner as RUN          # holds N_SEEDS/SEED_PASS  # noqa: E402
from pipeline.compile_assembly import compile_assembly  # noqa: E402
from tasks.build_goldens import anchor_easy  # noqa: E402
from tasks.run_m8_t2 import build_hints, stop_angle_from_ir  # noqa: E402

OUT = Path(__file__).parent / "out"
MU_NOM = 0.30
MU_FACTORS = [0.5, 0.75, 1.0, 1.25, 1.5]
CLEARANCES = [0.20, 0.30, 0.40]
RUN.N_SEEDS, RUN.SEED_PASS = 3, 2               # lean sweep (regions from 3 seeds)


def one_run(mu, clearance):
    MJCF.MU = mu                                 # per-run experiment param (R5 default intact)
    plan = anchor_easy("stop")
    plan.element("E1").params["clearance"] = clearance
    ca = compile_assembly(plan)
    hints = build_hints(plan, ca)
    roles = {"P1": "base", "P2": "mover", "P3": "hardware"}
    parts = {pid: ca.parts[pid] for pid in ("P1", "P2", "P3")}
    bp = plan.piece("P1").params
    tip = (0.0, bp["box_w"] / 2.0, bp["box_h"])
    latch = (0.0, bp["box_w"] / 2.0 - bp["wall"], bp["box_h"] * 0.7)
    res = RUN.t2(parts, hints, ca.axes["E1"], roles, ["V-B"], OUT / "_easy",
                 "P1", "P2", "P3", "sweep", tip_point=tip, latch_point=latch, clearance=clearance,
                 protrusion=3.0, stop_angle_deg=stop_angle_from_ir(plan), record=False, plan=plan)
    vb = res["modes"].get("V-B", {}).get("p_hinge", {})
    return {"mu": round(mu, 3), "clearance": clearance, "ran": vb.get("ran", False),
            "seeds_passed": vb.get("seeds_passed", 0), "passed": bool(vb.get("passed", False))}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    results, grid = [], []
    for f in MU_FACTORS:
        row = []
        for cl in CLEARANCES:
            r = one_run(MU_NOM * f, cl); r["mu_factor"] = f
            results.append(r); row.append(r["passed"])
            print(f"  μ={MU_NOM*f:.3f} cl={cl:.2f} → {'PASS' if r['passed'] else 'fail'} "
                  f"({r['seeds_passed']}/{RUN.N_SEEDS}{'' if r['ran'] else ', G-CONV n/a'})")
        grid.append(row)
    fig, ax = plt.subplots(figsize=(6, 4.6))
    ax.imshow(np.array([[1.0 if c else 0.0 for c in r] for r in grid]), cmap="RdYlGn",
              vmin=0, vmax=1, aspect="auto", origin="lower")
    ax.set_xticks(range(len(CLEARANCES))); ax.set_xticklabels([f"{c:.2f}" for c in CLEARANCES])
    ax.set_yticks(range(len(MU_FACTORS))); ax.set_yticklabels([f"{f:g}×\n({f*MU_NOM:.3f})" for f in MU_FACTORS])
    ax.set_xlabel("clearance (mm)"); ax.set_ylabel("μ (× frozen 0.30)")
    for i in range(len(MU_FACTORS)):
        for j in range(len(CLEARANCES)):
            ax.text(j, i, "✓" if grid[i][j] else "✗", ha="center", va="center", fontsize=13)
    ax.set_title("Easy stop-box P-HINGE V-B region\n(opens/returns/pin-retained; frozen default μ=1×, cl=0.30)",
                 fontsize=10)
    fig.tight_layout(); fig.savefig(OUT / "heat_easy_hinge.png", dpi=130); plt.close(fig)
    (OUT / "sweep_easy.json").write_text(json.dumps(
        {"preset_default": {"mu": MU_NOM, "note": "R5 frozen; μ swept is a per-run experiment param"},
         "results": results}, indent=2))
    npass = sum(r["passed"] for r in results)
    print(f"\n=== Easy stop-box P-HINGE V-B: {npass}/{len(results)} cells PASS ===")
    print("wrote heat_easy_hinge.png + sweep_easy.json")


if __name__ == "__main__":
    main()
