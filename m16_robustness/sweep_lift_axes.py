"""m16 — lift robustness AXES beyond μ×clearance (review pt 7): LOAD, MISALIGNMENT, finer-dt.

  LOAD    : load ∈ {0.25, 0.5, 1.0} kg × μ ∈ {0.5..1.5}× — P-SLIDE V-B retention region under load.
  MISALIGN: initial pitch misalignment ∈ {0, 0.5, 1°} × μ — does retention survive a tilted start?
  DT      : the D-M16-1 caveat — the default point (μ=0.30, cl=0.30, 0.5 kg) at dt ∈ {5e-4, 2.5e-4,
            1e-4} × 3 seeds each, to CHARACTERISE whether the dt/2 loss is a real sensitivity or a
            seed/boundary artifact.

Same preset discipline (R5): frozen preset stays the DEFAULT; μ/dt/load/misalign here are per-run
EXPERIMENT PARAMETERS, recorded per verdict.

Run:  ./bin/py m16_robustness/sweep_lift_axes.py
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

import m13_hard_anchor.p_slide_vb as VB  # noqa: E402
from knowledge.cards.base import CARD_REGISTRY  # noqa: E402
from pipeline.compile_assembly import compile_assembly  # noqa: E402
from tasks.build_goldens import anchor_lift  # noqa: E402

OUT = Path(__file__).parent / "out"
MU_NOM = 0.30
MU_FACTORS = [0.5, 0.75, 1.0, 1.25, 1.5]
LOADS = [0.25, 0.5, 1.0]
MISALIGNS = [0.0, 0.5, 1.0]


def one_run(mu=MU_NOM, clearance=0.30, load_kg=0.5, misalign=0.0, dt=5e-4, seed=0):
    VB.MU, VB.FROZEN_DT, VB.LOAD_KG, VB.OUT = mu, dt, load_kg, OUT   # per-run experiment params (R5 default intact)
    p = anchor_lift()
    for e in p.elements:
        if e.card_ref == "slide_rail":
            e.params["clearance"] = clearance
        e.params = CARD_REGISTRY[e.card_ref].resolve_params(p, e)
    ca = compile_assembly(p)
    xml, _ = VB.build_vb(ca, p)
    xf = OUT / "_axes.xml"; xf.write_text(xml)
    model = mj.MjModel.from_xml_path(str(xf))
    v, _s, _f = VB.run_vb(model, seed=seed, record=False, misalign_deg=misalign)
    return {"mu": round(mu, 3), "clearance": clearance, "load_kg": load_kg, "misalign": misalign,
            "dt": dt, "seed": seed, "retained": bool(v["passed"]), "off_deg": v["peak_offaxis_deg"]}


def _heat(grid, ylabels, ylab, xlabels, xlab, title, path):
    fig, ax = plt.subplots(figsize=(6, 4.4))
    Z = np.array([[1.0 if c else 0.0 for c in row] for row in grid])
    ax.imshow(Z, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto", origin="lower")
    ax.set_xticks(range(len(xlabels))); ax.set_xticklabels(xlabels)
    ax.set_yticks(range(len(ylabels))); ax.set_yticklabels(ylabels)
    ax.set_xlabel(xlab); ax.set_ylabel(ylab)
    for i in range(len(ylabels)):
        for j in range(len(xlabels)):
            ax.text(j, i, "✓" if grid[i][j] else "✗", ha="center", va="center", fontsize=13)
    ax.set_title(title, fontsize=10)
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    res = {"load": [], "misalign": [], "dt": []}

    # LOAD × μ (nominal clearance/dims, misalign 0)
    gridL = []
    for f in MU_FACTORS:
        row = []
        for L in LOADS:
            r = one_run(mu=MU_NOM * f, load_kg=L); r["mu_factor"] = f
            res["load"].append(r); row.append(r["retained"])
            print(f"  LOAD  μ={MU_NOM*f:.3f} load={L}kg → {'RET' if r['retained'] else 'lost'} ({r['off_deg']:.1f}°)")
        gridL.append(row)
    _heat(gridL, [f"{f:g}×" for f in MU_FACTORS], "μ (× frozen 0.30)",
          [f"{L}" for L in LOADS], "load (kg)",
          "P-SLIDE V-B retention — LOAD × μ (cl=0.30)", OUT / "heat_lift_load.png")

    # MISALIGN × μ (nominal clearance/load)
    gridM = []
    for f in MU_FACTORS:
        row = []
        for m in MISALIGNS:
            r = one_run(mu=MU_NOM * f, misalign=m); r["mu_factor"] = f
            res["misalign"].append(r); row.append(r["retained"])
            print(f"  MISAL μ={MU_NOM*f:.3f} tilt={m}° → {'RET' if r['retained'] else 'lost'} ({r['off_deg']:.1f}°)")
        gridM.append(row)
    _heat(gridM, [f"{f:g}×" for f in MU_FACTORS], "μ (× frozen 0.30)",
          [f"{m}°" for m in MISALIGNS], "initial misalignment",
          "P-SLIDE V-B retention — MISALIGN × μ (0.5 kg, cl=0.30)", OUT / "heat_lift_misalign.png")

    # DT characterization at the default point × seeds
    for dt in (5e-4, 2.5e-4, 1e-4):
        for seed in (0, 1, 2):
            r = one_run(dt=dt, seed=seed)
            res["dt"].append(r)
            print(f"  DT    dt={dt:.1e} seed={seed} → {'RET' if r['retained'] else 'lost'} ({r['off_deg']:.1f}°)")

    (OUT / "sweep_lift_axes.json").write_text(json.dumps(
        {"preset_default": {"mu": MU_NOM, "dt": 5e-4, "load_kg": 0.5,
                            "note": "R5 frozen; swept values are per-run experiment params"},
         "load": res["load"], "misalign": res["misalign"], "dt": res["dt"]}, indent=2))
    # dt summary
    dtsum = {}
    for r in res["dt"]:
        dtsum.setdefault(r["dt"], []).append(r["retained"])
    print("\n=== DT characterization (default point, 3 seeds each) ===")
    for dt, vals in sorted(dtsum.items(), reverse=True):
        print(f"  dt={dt:.1e}: retained {sum(vals)}/{len(vals)}")
    print("wrote heat_lift_load.png, heat_lift_misalign.png, sweep_lift_axes.json")


if __name__ == "__main__":
    main()
