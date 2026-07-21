"""m17 FOLLOW-UP — isolate dt* (D-M17-3), no source build needed.

The oracle survivals in FILE 2 were transient-dominated (ratio far from the -0.5 clean roll). Here we
add a SETTLE phase (drive off for the first 0.05 s, so the seating penetration relaxes) and then judge
the CLEAN roll. dt* = the LARGEST (coarsest) dt that still gives a bounded, clean roll (|ratio+0.5| <
0.15). We measure dt* for:
  - the WEDGE collider (m1_gear) at the R2b scale  — the real R2b number,
  - the analytic SDF ORACLE at the same scale       — does a zero-facet collider buy a larger dt?
  - the analytic SDF ORACLE at 2x module (scale)     — does scale relax dt* (the m1_gear axis)?

If SDF's dt* is no larger than the wedge's at equal scale, SDF buys nothing on the dt axis and the
sdflib source build (D-M17-1) is not justified — reinforcing F3. The SDF oracle stays D21-forbidden as
a deliverable; oracle use only.

  export MUJOCO_GL=disable ; ./bin/py m17_gear_vb/dt_scale_ladder.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import mujoco  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "m1_gear"))
sys.path.insert(0, str(ROOT / "m0"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import gear_mjcf                          # noqa: E402
import sdf_formulation_probe as SP        # noqa: E402
from _run import drive_measure            # noqa: E402

OUT = Path(__file__).parent / "out"
gear_mjcf.OUT = OUT
gear_mjcf.MESHDIR = OUT / "assets"

DT_LADDER = [5e-4, 2.5e-4, 1e-4, 5e-5, 2e-5]
SETTLE, T_END, CLEAN_TOL = 0.05, 0.25, 0.15     # clean roll = |ratio - (-0.5)| < CLEAN_TOL


def _clean(r):
    return (not r["diverged"]) and r["ratio"] is not None and abs(r["ratio"] + 0.5) < CLEAN_TOL


def _dtstar(rows):
    """Largest dt whose row is a clean roll (V-B would require dt <= dt*)."""
    ok = [row["dt"] for row in rows if row["clean"]]
    return max(ok) if ok else None


def seat_current():
    """Fewest-contact proper mesh (ncon0>=2) for whatever geometry SP globals currently describe."""
    best = None
    for a in np.arange(0.0, 8.0001, 0.1):
        m = mujoco.MjModel.from_xml_path(str(SP.build_oracle(float(a), soft=False)))
        d = mujoco.MjData(m); mujoco.mj_forward(m, d)
        nc = int(d.ncon)
        if nc >= 2 and (best is None or nc < best[1]):
            best = (round(float(a), 2), nc)
    return best[0] if best else 0.0


def ladder_over(make_model):
    rows = []
    for dt in DT_LADDER:
        r = drive_measure(make_model(), dt, t_end=T_END, settle_start=SETTLE)
        rows.append({"dt": dt, "diverged": r["diverged"], "ratio": r["ratio"],
                     "peak_post_settle_N": r["peak_post_settle_N"], "clean": _clean(r)})
    return rows


def sdf_ladder(module):
    SP.MODULE = module
    SP.D1, SP.D2 = module * SP.Z1, module * SP.Z2
    SP.CD = (SP.D1 + SP.D2) / 2.0
    seat = seat_current()
    rows = ladder_over(lambda: mujoco.MjModel.from_xml_path(str(SP.build_oracle(seat, soft=False))))
    return seat, rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    verdict = {"probe": "m17 dt_scale_ladder (follow-up, dt*)",
               "settle_s": SETTLE, "t_end": T_END, "clean_tol": CLEAN_TOL, "ladders": {}}

    # WEDGE at the R2b scale (module 2 mm) — build once, reuse across dt.
    wxml, _ = gear_mjcf.build("involute", 4, tag="dt_ladder_wedge", op_cd=36.0)
    wrows = ladder_over(lambda: mujoco.MjModel.from_xml_path(str(wxml)))
    verdict["ladders"]["wedge_2mm"] = {"dt_star": _dtstar(wrows), "rows": wrows}
    print(f"WEDGE  2mm : dt* = {_dtstar(wrows)}")
    for r in wrows:
        print(f"    dt={r['dt']:.1e} div={r['diverged']} ratio={r['ratio']} clean={r['clean']}")

    # SDF oracle at the same scale, then 2x scale.
    for label, module in (("sdf_2mm", 2e-3), ("sdf_4mm", 4e-3)):
        seat, rows = sdf_ladder(module)
        verdict["ladders"][label] = {"module_m": module, "seat_deg": seat,
                                     "dt_star": _dtstar(rows), "rows": rows}
        print(f"SDF {label}: seat={seat} dt* = {_dtstar(rows)}")
        for r in rows:
            print(f"    dt={r['dt']:.1e} div={r['diverged']} ratio={r['ratio']} clean={r['clean']}")

    (OUT / "dt_scale_ladder_verdict.json").write_text(json.dumps(verdict, indent=2))

    # figure: dt* markers per collider/scale
    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    names, dstars = [], []
    for k in ("wedge_2mm", "sdf_2mm", "sdf_4mm"):
        L = verdict["ladders"][k]
        names.append(k); dstars.append(L["dt_star"] or np.nan)
    y = np.arange(len(names))
    ax.barh(y, [d if d == d else 0 for d in dstars], color=["#2f6fb0", "#b06a2f", "#6a9a3a"], height=0.5)
    for yi, d in zip(y, dstars):
        ax.text((d if d == d else 1e-5) * 1.1, yi, ("none" if d != d else f"{d:.0e}"),
                va="center", fontsize=9)
    ax.set_yticks(y); ax.set_yticklabels(names)
    ax.set_xscale("log"); ax.set_xlabel("dt* — largest dt giving a bounded CLEAN roll (s)")
    ax.set_title("R2b dt* — does SDF (zero-facet) buy a larger stable dt than wedges at equal scale?\n"
                 "(settle 0.05 s; clean = |ratio+0.5|<0.15)", fontsize=9)
    ax.grid(axis="x", alpha=0.3, which="both")
    fig.tight_layout(); fig.savefig(OUT / "dt_scale_ladder.png", dpi=140); plt.close(fig)
    print("wrote out/dt_scale_ladder_verdict.json + dt_scale_ladder.png")


if __name__ == "__main__":
    main()
