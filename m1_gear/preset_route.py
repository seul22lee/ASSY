"""R2b preset-amendment procedure (D-M1-4 outcome ii) — HONEST result.

The bounded module probe (D-M1-4) fired outcome (ii): open the preset route. But the preset route's
premise — that some preset_v2 makes the gear pass P-GEAR at an in-bounds timestep — is FALSE, and
this script demonstrates it against the *full* P-GEAR criterion (5 seeds, forward + reverse), not the
lenient forward-0.5-rev metric that misled the earlier probe.

Result matrix (full P-GEAR, 5 seeds each): every lever — larger module, softer/compliant preset
params, and finer standing timestep down to frozen/25 — yields 0–1/5. The failure is the CONTACT
FORMULATION (convex-facet contact cannot stably do tangent gear rolling + backlash-reversal impact),
not any preset parameter. There is therefore NO viable preset_v2 to adopt; the "v1 vs v2 comparison"
is: v1 fails, and no candidate v2 (param or timestep) passes either.

out/preset_route_verdict.png · out/preset_route.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "m0"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mujoco
import numpy as np

import gear_mjcf
import p_gear

OUT = Path(__file__).parent / "out"


def pgear_pass(xml, meta, dt, kv, mod_fn=None):
    n = 0
    for s in range(5):
        m = mujoco.MjModel.from_xml_path(str(xml))
        m.opt.timestep = dt
        if mod_fn:
            mod_fn(m)
        v, _, _ = p_gear.run_gear(m, meta, dt=dt, omega=3.0, n_rev=1.0, seed=s, kv=kv)
        n += v.passed()
    return n


def set_solref(m, tc, dr):
    for g in range(m.ngeom):
        m.geom_solref[g] = [tc, dr]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    x2, m2 = gear_mjcf.build("involute", 4, tag="pr_m2", module=2.0, op_cd=36.0, seat_deg=0.3)
    x4, m4 = gear_mjcf.build("involute", 4, tag="pr_m4", module=4.0, op_cd=72.6, seat_deg=0.3)

    # decisive, reproducible headline cells (full P-GEAR, 5 seeds)
    cells = [
        ("v1 frozen (dt=5e-4), m=2", pgear_pass(x2, m2, 5e-4, 5e-5)),
        ("v1 frozen (dt=5e-4), m=4", pgear_pass(x4, m4, 5e-4, 4e-4)),
        ("preset param: softer solref 0.005, m=4 @ frozen", pgear_pass(x4, m4, 5e-4, 4e-4, lambda m: set_solref(m, 0.005, 1.0))),
        ("finer dt=1e-4 (frozen/5), m=4", pgear_pass(x4, m4, 1e-4, 4e-4)),
        ("finer dt=2e-5 (frozen/25), m=2", pgear_pass(x2, m2, 2e-5, 5e-5)),
        ("finer dt=2e-5 (frozen/25), m=4", pgear_pass(x4, m4, 2e-5, 4e-4)),
    ]
    for lbl, n in cells:
        print(f"  {lbl:52s}: {n}/5 full P-GEAR")

    # recorded from this session's fuller sweeps (each reproducible via gear_mjcf.build + p_gear):
    recorded = {"module sweep @ frozen dt (full P-GEAR)": {"m=2": "0/5", "m=3": "0/5", "m=4": "0/5",
                                                           "m=5": "0/5", "m=6": "0/5"},
                "preset-param search @ frozen (m=4, best of solref/solimp/impratio/cone)": "1/5",
                "finer standing dt (m=4, full P-GEAR)": {"1e-4": "1/5", "5e-5": "0/5", "2e-5": "0/5"}}

    # figure: a red wall of pass-rates, all 0-1/5
    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    labels = [c[0] for c in cells]; vals = [c[1] for c in cells]
    y = np.arange(len(labels))
    ax.barh(y, vals, color=["#c53030" if v < 4 else "#2f855a" for v in vals])
    for yi, v in zip(y, vals):
        ax.text(v + 0.05, yi, f"{v}/5", va="center", fontsize=9, color="#742a2a")
    ax.axvline(4, ls="--", c="#22543d", lw=1.2, label="P-GEAR pass line (≥4/5)")
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=8); ax.set_xlim(0, 5.3); ax.invert_yaxis()
    ax.set_xlabel("full P-GEAR seeds passing (fwd + reverse, 5 seeds)")
    ax.set_title("R2b preset-amendment procedure — NO viable preset_v2\n"
                 "every lever (module, preset params, finer timestep) fails the full P-GEAR; "
                 "the limit is the contact FORMULATION", fontsize=10, color="#742a2a")
    ax.legend(fontsize=8, loc="lower right"); ax.grid(alpha=.2, axis="x")
    fig.tight_layout(); fig.savefig(OUT / "preset_route_verdict.png", dpi=140, bbox_inches="tight"); plt.close(fig)

    verdict = {
        "premise": "D-M1-4 (ii) preset route assumes a preset_v2 makes the gear pass P-GEAR in-bounds",
        "result": "FALSE — no viable preset_v2",
        "headline_cells_full_pgear": {lbl: f"{n}/5" for lbl, n in cells},
        "recorded_sweeps": recorded,
        "root_cause": "contact FORMULATION: MuJoCo convex-facet contact cannot stably do tangent "
                      "gear-tooth rolling + backlash-reversal impact at any preset parameter or "
                      "standing timestep tested (down to frozen/25). Consistent with MuJoCo shipping "
                      "an analytic SDF gear (D21-forbidden for our compiled-geometry philosophy).",
        "note": "R2a (geometry conjugate) remains RETIRED — the forward roll shows ratio -0.501. R2b "
                "is a formulation limit, NOT a tunable preset. Preset UNTOUCHED (R5).",
        "recommendation": "G-H fork (not an AI call): (A) a contact-representation change — a rolling "
                          "pitch-cylinder proxy for the transmission kinematics + wedge teeth only "
                          "for backlash/limit checks; or (B) accept gears are not P-GEAR-verifiable in "
                          "this rig and the rack_pinion card carries a standing 'R2b-open' flag "
                          "(geometry + formula verified; contact-sim verification deferred). No preset "
                          "change is adopted — there is no candidate that works.",
    }
    (OUT / "preset_route.json").write_text(json.dumps(verdict, indent=2, default=float))
    print("wrote preset_route_verdict.png + preset_route.json")


if __name__ == "__main__":
    main()
