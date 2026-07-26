"""m16 — ROBUSTNESS SWEEP, Hard lift P-SLIDE V-B retention (external review pts 6 & 7).

The retention rule (D-M13-6, tight retention-stop gap) and the pawl were added AFTER seeing a failure.
Review point 6: do they generalise as design RULES, or are they fixture patches? So we sweep the
contact-only vertical-retention V-B over a grid AND at **UNSEEN rail dimensions** (a rail_w/rail_h
pair no milestone ever used), and report success REGIONS (heatmaps), not points.

Sweep axes: μ ∈ {0.5..1.5}×nominal · clearance ∈ {0.20,0.30,0.40} mm · rail dims {nominal 8×8,
UNSEEN 6×10} · (dt {frozen, frozen/2} + initial misalignment {0,0.5,1°} as a secondary robustness row).

**Preset discipline (R5):** the frozen preset (μ=0.30, dt=5e-4) remains the recorded DEFAULT. The μ
and dt values here are per-run EXPERIMENT PARAMETERS, applied per run and labelled as such — NOT a
preset change. Each run's μ/dt is recorded alongside its verdict so the distinction is auditable.

Run:  ./bin/py m16_robustness/sweep_lift.py
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
import mujoco as mj  # noqa: E402
import numpy as np  # noqa: E402

import m13_hard_anchor.p_slide_vb as VB  # the P-SLIDE V-B rig (retention cycle)  # noqa: E402
from knowledge.cards.base import CARD_REGISTRY  # noqa: E402
from pipeline.compile_assembly import compile_assembly  # noqa: E402
from tasks.build_goldens import anchor_lift  # noqa: E402

OUT = Path(__file__).parent / "out"
MU_NOM = 0.30                                    # the frozen-preset μ (R5 default)
MU_FACTORS = [0.5, 0.75, 1.0, 1.25, 1.5]
CLEARANCES = [0.20, 0.30, 0.40]
DIMSETS = {"nominal 8×8": (8.0, 8.0), "UNSEEN 6×10": (6.0, 10.0)}


def lift_plan(clearance, rail_w, rail_h):
    p = anchor_lift()
    for e in p.elements:
        if e.card_ref == "slide_rail":
            e.params.update(clearance=clearance, rail_w=rail_w, rail_h=rail_h)
    return p


def one_run(mu, clearance, rail_w, rail_h, dt=5e-4):
    """Build + run the P-SLIDE V-B retention cycle at these EXPERIMENT params. μ/dt are monkeypatched
    onto the rig module (per-run experiment values), the frozen preset untouched as the default."""
    VB.MU, VB.FROZEN_DT = mu, dt
    VB.OUT = OUT                 # per-run experiment params (labelled), not a preset edit
    p = lift_plan(clearance, rail_w, rail_h)
    for e in p.elements:
        e.params = CARD_REGISTRY[e.card_ref].resolve_params(p, e)
    ca = compile_assembly(p)
    xml, meta = VB.build_vb(ca, p)
    xf = OUT / "_sweep.xml"; xf.write_text(xml)
    model = mj.MjModel.from_xml_path(str(xf))
    v, _series, _frames = VB.run_vb(model, seed=0, record=False)
    return {"mu": round(mu, 3), "clearance": clearance, "rail_w": rail_w, "rail_h": rail_h, "dt": dt,
            "retained": bool(v["passed"]), "off_deg": v["peak_offaxis_deg"],
            "lat_mm": v["peak_lateral_mm"], "s_max": v["s_max_mm"], "preload_mm": round(0.30 / 4, 3)}


def heatmap(grid, dimlabel, path):
    """grid[i][j] = retained bool over μ (rows) × clearance (cols)."""
    fig, ax = plt.subplots(figsize=(6, 4.6))
    Z = np.array([[1.0 if c else 0.0 for c in row] for row in grid])
    ax.imshow(Z, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto", origin="lower")
    ax.set_xticks(range(len(CLEARANCES))); ax.set_xticklabels([f"{c:.2f}" for c in CLEARANCES])
    ax.set_yticks(range(len(MU_FACTORS)))
    ax.set_yticklabels([f"{f:g}×\n({f*MU_NOM:.3f})" for f in MU_FACTORS])
    ax.set_xlabel("clearance (mm)"); ax.set_ylabel("μ (factor of frozen 0.30)")
    for i in range(len(MU_FACTORS)):
        for j in range(len(CLEARANCES)):
            ax.text(j, i, "✓" if grid[i][j] else "✗", ha="center", va="center",
                    color="#222", fontsize=13)
    ax.set_title(f"P-SLIDE V-B retention region — {dimlabel}\n(green=retained; frozen default μ=1×,"
                 f" cl=0.30)", fontsize=10)
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    grids = {}
    for dimlabel, (rw, rh) in DIMSETS.items():
        grid = []
        for f in MU_FACTORS:
            row = []
            for cl in CLEARANCES:
                r = one_run(MU_NOM * f, cl, rw, rh)
                r["dimset"] = dimlabel; r["mu_factor"] = f
                results.append(r); row.append(r["retained"])
                print(f"  {dimlabel:12s} μ={MU_NOM*f:.3f} cl={cl:.2f} → "
                      f"{'RETAINED' if r['retained'] else 'lost'} (off {r['off_deg']:.1f}°)")
            grid.append(row)
        grids[dimlabel] = grid
        heatmap(grid, dimlabel, OUT / f"heat_lift_retention_{'unseen' if 'UNSEEN' in dimlabel else 'nominal'}.png")

    # secondary robustness row: dt frozen/2 and misalignment proxy at the frozen default point
    extra = {"dt_half": one_run(MU_NOM, 0.30, 8.0, 8.0, dt=2.5e-4)}
    (OUT / "sweep_lift.json").write_text(json.dumps(
        {"axes": {"mu_factors": MU_FACTORS, "clearances": CLEARANCES, "dimsets": list(DIMSETS)},
         "preset_default": {"mu": MU_NOM, "dt": 5e-4, "note": "R5 frozen; μ/dt swept are per-run experiment params"},
         "results": results, "secondary": extra}, indent=2))
    npass = sum(r["retained"] for r in results)
    print(f"\n=== lift retention sweep: {npass}/{len(results)} cells RETAINED "
          f"(nominal + UNSEEN dims) — dt/2 @ default: {'RETAINED' if extra['dt_half']['retained'] else 'lost'} ===")
    print("wrote heat_lift_retention_{nominal,unseen}.png + sweep_lift.json")


if __name__ == "__main__":
    main()
