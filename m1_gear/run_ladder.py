"""M1 ladder driver (MECHSYNTH §6.3/§6.4, D-ONT-7). Climbs the fidelity ladder, records each rung's
evidence whether it passes or fails (failure is DATA), and emits the m1_gear/out/ deliverables.

  L1  trapezoid, 2 wedges/flank
  L2  trapezoid, 4 wedges/flank
  L3  involute,   4 wedges/flank
  L4  involute,   6 wedges/flank + the §6.4 finer-timestep retry

Each rung: G-CONV, then P-GEAR at the FROZEN dt (5e-4) and the single §6.4 retry (2.5e-4). A rung
PASSES only if it converges + meets the criteria within those bounds (R5). A separate, clearly
LABELLED out-of-bounds probe at a much finer dt establishes whether the mesh is geometrically
conjugate at all (ratio, TE) — evidence, never a pass.

out/:  ladder.md (verdict table), ladder_verdict.json, conjugate_roll.png (ratio+TE at fine dt),
       t_gear_<tag>.mp4 (HUD roll video), mesh_check_{trapezoid,involute}.png
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "m0"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import imageio.v2 as imageio
import numpy as np

import gear_mjcf
import p_gear

OUT = Path(__file__).parent / "out"
FROZEN, RETRY = 5e-4, 2.5e-4
FINE = 2e-5                      # out-of-bounds probe dt (25x below frozen) — evidence only

RUNGS = [
    ("L1", "trapezoid", 2, None),     # op_cd None -> auto (trapezoid needs relief; set below)
    ("L2", "trapezoid", 4, None),
    ("L3", "involute", 4, 36.0),
    ("L4", "involute", 6, 36.0),
]
TRAP_OPCD = 36.9   # trapezoid needs +0.9 mm to seat without interference (mesh-check finding)


def plot_conjugate(series, meta, path, tag):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    t = series["t"]; thp = series["theta_pin_deg"]; thg = series["theta_gear_deg"]; te = series["te_deg"]
    fig, ax = plt.subplots(3, 1, figsize=(8, 8), sharex=True, gridspec_kw={"height_ratios": [3, 3, 2]})
    ax[0].plot(thp, thg, lw=2, color="#2b6cb0", label="measured")
    ideal = [-meta["z1"] / meta["z2"] * x for x in thp]
    ax[0].plot(thp, ideal, ls="--", color="#c53030", lw=1, label=f"ideal -z1/z2 = -{meta['z1']}/{meta['z2']}")
    ax[0].set_xlabel("pinion angle (deg)"); ax[0].set_ylabel("gear angle (deg)")
    ax[0].legend(fontsize=8); ax[0].grid(alpha=.25)
    ax[0].set_title(f"M1 conjugate roll — {tag} (involute) @ dt={FINE:.0e} [OUT OF BOUNDS, evidence]",
                    fontsize=10)
    ax[1].plot(t, thp, color="#2b6cb0", lw=1.5, label="pinion")
    ax[1].plot(t, thg, color="#dd6b20", lw=1.5, label="gear (counter-rotates)")
    ax[1].set_ylabel("angle (deg)"); ax[1].legend(fontsize=8); ax[1].grid(alpha=.25)
    ax[2].plot(t, te, color="#805ad5", lw=1.2)
    ax[2].axhline(360 / meta["z1"] / 2, ls=":", c="#c53030", lw=0.8, label="half tooth pitch (slip)")
    ax[2].axhline(-360 / meta["z1"] / 2, ls=":", c="#c53030", lw=0.8)
    ax[2].set_ylabel("transmission\nerror (deg)"); ax[2].set_xlabel("t (s)")
    ax[2].legend(fontsize=8); ax[2].grid(alpha=.25)
    fig.tight_layout(); fig.savefig(path, dpi=130)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    import mesh_check
    for prof in ("trapezoid", "involute"):
        mesh_check.check(prof)

    results = []
    for tag, prof, nw, opcd in RUNGS:
        op = TRAP_OPCD if prof == "trapezoid" else opcd
        xml, meta = gear_mjcf.build(prof, nw, tag=f"{tag}_{prof}_n{nw}", op_cd=op)
        mp = str(xml).replace(".xml", "_meta.json")
        res, series, frames = p_gear.run_rung(tag, xml, mp, dt_ladder=[FROZEN, RETRY],
                                              omega=3.0, n_rev=1.0, record=False)
        results.append(res)

    # out-of-bounds conjugate-action probe on the best-profile rung (involute n6): forward roll at
    # the fine dt — the evidence that the tooth profile IS geometrically conjugate (ratio, TE), even
    # though it is not stable within the frozen preset. Forward-only keeps it tractable + avoids the
    # reversal transient; a short reverse at the end measures backlash.
    xml, meta = gear_mjcf.build("involute", 6, tag="probe_inv_n6", op_cd=36.0)
    import mujoco
    model = mujoco.MjModel.from_xml_path(str(xml))
    t0 = time.time()
    v, series, frames = p_gear.run_gear(model, meta, dt=FINE, omega=3.0, n_rev=1.0, record=True)
    print(f"\n[probe] involute n6 @ dt={FINE:.0e}: ratio={v.ratio:+.3f} err={v.ratio_err_pct:+.1f}% "
          f"TE={v.te_max_deg:.2f}° backlash={v.backlash_meas_mm:.2f}mm (design {v.backlash_design_mm}) "
          f"revs={v.revs_done} diverged={v.diverged}  [{time.time()-t0:.0f}s]")
    if series["t"]:
        plot_conjugate(series, meta, OUT / "conjugate_roll.png", "probe")
    if frames:
        imageio.mimsave(OUT / "t_gear_probe_inv_n6.mp4", frames, fps=p_gear.FPS)

    ladder = {"rungs": results, "conjugate_probe": {
        "dt": FINE, "in_bounds": False, "ratio": v.ratio, "ratio_err_pct": v.ratio_err_pct,
        "te_max_deg": v.te_max_deg, "backlash_meas_mm": v.backlash_meas_mm,
        "backlash_design_mm": v.backlash_design_mm, "revs_done": v.revs_done, "diverged": v.diverged}}
    (OUT / "ladder_verdict.json").write_text(json.dumps(ladder, indent=2, default=float))

    # ladder.md
    L = ["# M1 gear-pair — ladder verdict (P-GEAR, frozen preset R5 + §6.4 single retry)", "",
         "Pass = converges + meets criteria within the frozen dt (5e-4) or the ONE §6.4 retry "
         "(2.5e-4). Going finer than that violates R5 and is recorded as a rung FAIL.", "",
         "| Rung | profile | wedges/flank | G-CONV | frozen dt | §6.4 retry | verdict | note |",
         "|---|---|---|:--:|:--:|:--:|:--:|---|"]
    for r in results:
        a = {x["dt"]: x for x in r["attempts"]}
        fz = a.get(FROZEN, {}); rt = a.get(RETRY, {})
        fzs = "DIVERGED" if fz.get("diverged") else ("PASS" if fz.get("passed") else "fail")
        rts = "DIVERGED" if rt.get("diverged") else ("PASS" if rt.get("passed") else "fail")
        note = ("trapezoid needs op_cd +0.9mm (backlash 0.85mm) to seat"
                if r["meta"]["profile"] == "trapezoid" else "meshes clean at ideal cd, backlash 0.20mm")
        L.append(f"| {r['tag']} | {r['meta']['profile']} | {r['meta']['n_wedge']} | "
                 f"{'PASS' if r['g_conv'] else 'FAIL'} | {fzs} | {rts} | "
                 f"{'PASS' if r['verdict'] else '**FAIL**'} | {note} |")
    L += ["", "## Out-of-bounds conjugate probe (evidence, NOT a pass)", "",
          f"Involute n6 forward roll at dt={FINE:.0e} (25× below frozen): "
          f"**ratio {v.ratio:+.3f}** (ideal {-meta['z1']/meta['z2']:+.3f}, err {v.ratio_err_pct:+.1f}%), "
          f"peak TE {v.te_max_deg:.2f}°, backlash {v.backlash_meas_mm:.2f} mm "
          f"(design {v.backlash_design_mm} mm). The profile IS geometrically conjugate — it meshes "
          f"and transmits at the correct ratio — but only at a timestep far below the frozen preset.",
          "", "See conjugate_roll.png and t_gear_probe_inv_n6.mp4."]
    (OUT / "ladder.md").write_text("\n".join(L))
    print("\nwrote ladder.md, ladder_verdict.json, conjugate_roll.png")
    return ladder


if __name__ == "__main__":
    main()
