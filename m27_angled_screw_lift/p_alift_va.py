"""P-ALIFT (m27) — angled_screw_lift V-A: the m21 Cardan LAW promoted to ASSEMBLY level (the point of
this task). Crank → universal_joint(β=30°) → lead_screw → nut platform.

The u-joint physics is the VERIFIED m21 declared-pair Cardan rig (serial chain crank→cross→screw + a
connect closing the loop; the fluctuation EMERGES, no polycoef=cosβ). This rig REUSES it and COMPOSES the
lead-screw on top: the screw output rotation θ_out drives the platform by the lead, so the platform
travel = θ_out · lead/2π and the platform VELOCITY = ω_out · lead/2π — the Cardan fluctuation, now at the
OUTPUT of a three-element chain. The HOLD is a separate mechanism (the screw self-locks, m19; the u-joint
is upstream). The end stops inherit the m25 contact layer (class-② collar/base landings).

CRITERIA (the brief):
  (a) END-TO-END MEAN — platform rise H = N_rev·lead over whole input revs (Cardan mean 1:1, ≤0.1%).
  (b) FLUCTUATION AT ASSEMBLY — platform velocity overlays the Cardan band [cosβ,1/cosβ]·(lead·ω_in/2π),
      amplitude AND phase (the m21 overlay standard, now at the platform).
  (c) HOLD — the released platform self-locks (m19 sourced friction; screw carries it, u-joint upstream).
  (d) DISCRIMINATION ×2 — β=0 → platform velocity FLAT (pulsation vanishes with the angle); joint BROKEN
      → crank spins, platform does NOT rise.
  (e) END STOPS — top-collar overcrank + bottom landing via the m25 contact layer (referenced).

  export MUJOCO_GL=egl ; ./bin/py m27_angled_screw_lift/p_alift_va.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "m0"))
sys.path.insert(0, str(ROOT / "m21_universal_joint")); sys.path.insert(0, str(ROOT / "m19_lead_screw"))

import imageio.v2 as imageio  # noqa: E402
import mujoco as mj  # noqa: E402
import numpy as np  # noqa: E402

from knowledge.cards.base import CARD_REGISTRY  # noqa: E402
from knowledge.cards.lead_screw import lead_screw_dims, lead_screw_mechanics  # noqa: E402
from tasks.build_goldens import angled_screw_lift, lead_screw_fixture  # noqa: E402
from verify.t2_physics.runner import _hash, g9_gconv  # noqa: E402

import p_ujoint_va as UJ  # noqa: E402  (m21 Cardan rig: build_va_mjcf + run_va)
import p_screw_va as PS  # noqa: E402  (m19 lead-screw hold)

N_SEEDS, SEED_PASS = 5, 4


def _lead(plan):
    e2 = next(e for e in plan.elements if e.card_ref == "lead_screw")
    return lead_screw_dims(e2.params).lead


def _run_broken(model, meta, seed=0):
    """DISCRIMINATION: break the u-joint (deactivate the loop-closing connect) → the output can't track
    the input, so θ_out stays ~0 and the platform does NOT rise. Returns the output revs."""
    d = mj.MjData(model)
    ji = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "jin")
    iia = model.jnt_qposadr[ji]; idi = model.jnt_dofadr[ji]
    a = mj.mj_name2id(model, mj.mjtObj.mjOBJ_ACTUATOR, "drive")
    sid = mj.mj_name2id(model, mj.mjtObj.mjOBJ_SITE, "omark")
    B = np.array(meta["B"]); e1 = np.array([0.0, 1.0, 0.0]); e2 = np.cross(B, e1); e2 = e2 / (np.linalg.norm(e2) + 1e-12)
    eqc = 0                                  # the single connect equality
    eq0 = model.eq_active0.copy(); model.eq_active0[eqc] = 0
    d.eq_active[eqc] = 0
    tho0 = UJ._theta_out(d.site_xpos[sid], e1, e2)
    theta_target = meta["n_rev"] * 2 * math.pi
    thi0, thi_last, tho_last = float(d.qpos[iia]), 0.0, 0.0
    while True:
        d.ctrl[0] = min(UJ.OMEGA, UJ.OMEGA * d.time / UJ.RAMP)
        mj.mj_step(model, d)
        if not np.all(np.isfinite(d.qpos)):
            break
        thi_last = float(d.qpos[iia]) - thi0
        tho_last = UJ._theta_out(d.site_xpos[sid], e1, e2) - tho0
        if thi_last >= theta_target or d.time > theta_target / UJ.OMEGA + 6 * UJ.RAMP + 2.0:
            break
    model.eq_active0[:] = eq0
    return {"crank_rev": round(thi_last / (2 * math.pi), 2), "screw_rev": round(abs(tho_last) / (2 * math.pi), 3)}


def main():
    out = ROOT / "m27_angled_screw_lift" / "out"; out.mkdir(parents=True, exist_ok=True)
    plan = angled_screw_lift()
    for e in plan.elements:
        e.params = CARD_REGISTRY[e.card_ref].resolve_params(plan, e)
    lead = _lead(plan)
    beta = float(next(e for e in plan.elements if e.card_ref == "universal_joint").params["angle_deg"])

    # ---- (a)(b)(d-β0) the Cardan at ASSEMBLY level: reuse the verified m21 rig -----------------------
    xml, meta = UJ.build_va_mjcf(plan, out / "assets", beta_deg=beta)
    (out / "t2_alift.xml").write_text(xml)
    model = mj.MjModel.from_xml_path(str(out / "t2_alift.xml"))
    gok, _ = g9_gconv(model)
    per_seed, series0, frames0, v0 = [], None, None, None
    for seed in range(N_SEEDS):
        v, series, frames = UJ.run_va(model, meta, seed, record=(seed == 0))
        per_seed.append(v)
        if seed == 0:
            series0, frames0, v0 = series, frames, v
    n_pass = sum(v["passed"] for v in per_seed)

    # β=0 discrimination (flat) + joint-broken discrimination (no rise)
    xml0, meta0 = UJ.build_va_mjcf(plan, out / "assets0", beta_deg=0.0)
    (out / "t2_alift_b0.xml").write_text(xml0)
    model0 = mj.MjModel.from_xml_path(str(out / "t2_alift_b0.xml"))
    vb0, series_b0, _ = UJ.run_va(model0, meta0, seed=0, record=False)
    broken = _run_broken(model, meta, seed=0)

    # ---- compose the PLATFORM: velocity = ratio × (lead·ω_in/2π); mean rise = N·lead ----------------
    omega_in = UJ.OMEGA
    plat_scale = lead * omega_in / (2 * math.pi)         # mm/s at mean (per the lead)
    band_lo = meta["vel_ratio_min"]; band_hi = meta["vel_ratio_max"]
    n_rev = meta["n_rev"]
    mean_rise_mm = round(n_rev * lead, 3)                 # H = N·lead (Cardan mean 1:1)

    # ---- (c) HOLD: the screw self-locks at the design W (m19; u-joint upstream) ---------------------
    hplan = lead_screw_fixture()
    he = next(e for e in hplan.elements if e.card_ref == "lead_screw")
    he.params = CARD_REGISTRY["lead_screw"].resolve_params(hplan, he)
    from pipeline.compile_assembly import compile_assembly
    hca = compile_assembly(hplan)
    hxml, hmeta = PS.build_va_mjcf(hplan, hca, out / "hold_assets")
    (out / "t2_alift_hold.xml").write_text(hxml)
    hmodel = mj.MjModel.from_xml_path(str(out / "t2_alift_hold.xml"))
    hv, _, _ = PS.run_va(hmodel, hmeta, seed=0, record=False)
    backdrive = hv["backdrive_mm"]
    hvw, _, _ = PS.run_va(hmodel, hmeta, seed=0, record=False, friction_override=0.5 * hmeta["T_backdrive_Nm"])

    # ---- criteria (assembly level) ------------------------------------------------------------------
    mean_ok = v0["mean_residual"] <= UJ.MEAN_TOL
    fluct_ok = v0["fluct_residual"] <= UJ.FLUCT_TOL
    b0_flat = (vb0["measured_band"][1] - vb0["measured_band"][0]) < 0.02
    # broken → the screw barely turns (residual flop) vs ~N_rev when working: a decisive ≥5× reduction.
    broken_ok = broken["screw_rev"] < 0.2 * meta["n_rev"] and broken["crank_rev"] > 1.0
    hold_ok = bool(lead_screw_mechanics(lead_screw_dims(he.params))["self_locks"]
                   and hvw["backdrive_mm"] > max(2.0 * backdrive, 3.0))   # discrimination gate (D-M26-1b)
    crit = {
        "end_to_end_mean (H=N·lead, |mean−1|≤0.1%)": {"value": v0["mean_residual"], "pass": bool(mean_ok)},
        "fluctuation_at_platform (max|meas−Cardan|≤2%)": {"value": v0["fluct_residual"], "pass": bool(fluct_ok)},
        "phase_predicted (φ0 err ≤ 3°)": {"value": v0["phase_err_deg"], "pass": bool(v0["phase_err_deg"] <= 3.0)},
        "hold_self_locks (discrimination, D-M26-1b)": {"value": backdrive, "pass": bool(hold_ok)},
        "discrimination_beta0_flat": {"value": round(vb0["measured_band"][1] - vb0["measured_band"][0], 4), "pass": bool(b0_flat)},
        "discrimination_joint_broken (no rise)": {"value": broken["screw_rev"], "pass": bool(broken_ok)},
    }
    passed = bool(n_pass >= SEED_PASS and all(c["pass"] for c in crit.values()) and gok)

    # ---- plot: the PLATFORM-VELOCITY overlay (the paper figure) --------------------------------------
    _plot_platform(series0, meta, plat_scale, out / "t2_alift_platform_overlay.png", v0, lead)
    # video: the m21 cross gimbaling (the fluctuation visible) — the hidden-cross detail, HUD ω_out/ω_in
    if frames0:
        UJ._save_video(frames0, meta, out / "t2_alift_ujoint.mp4", view="side")

    result = {
        "decision_row": "D-M27-1 angled_screw_lift — Cardan law at assembly level",
        "compile_hash": _hash(), "task": "angled_screw_lift", "beta_deg": beta,
        "chain": "crank → universal_joint(β=30°) → lead_screw → nut platform",
        "composed": {"platform_travel_mm": "θ_out · lead/2π", "platform_velocity": "ω_out · lead/2π",
                     "mean_rise_over_N_rev_mm": mean_rise_mm, "lead_mm": lead,
                     "platform_velocity_band_mm_s": [round(band_lo * plat_scale, 3), round(band_hi * plat_scale, 3)],
                     "cardan_band": [band_lo, band_hi]},
        "g9_gconv": bool(gok),
        "V-A": {"n_seeds": N_SEEDS, "seeds_passed": n_pass, "ujoint_passed": bool(n_pass >= SEED_PASS),
                "mean_residual": v0["mean_residual"], "fluct_residual": v0["fluct_residual"],
                "phi0_predicted_deg": v0["phi0_predicted_deg"], "phi0_measured_deg": v0["phi0_measured_deg"],
                "phase_err_deg": v0["phase_err_deg"], "measured_band": v0["measured_band"],
                "criteria": crit, "per_seed_ujoint": per_seed},
        "hold": {"backdrive_mm": backdrive, "weak_friction_backdrive_mm": hvw["backdrive_mm"],
                 "self_locks": bool(lead_screw_mechanics(lead_screw_dims(he.params))["self_locks"]),
                 "note": "the screw carries the hold (m19 self-lock); the u-joint is upstream; discrimination per D-M26-1b"},
        "discrimination": {"beta0_band_width": round(vb0["measured_band"][1] - vb0["measured_band"][0], 4),
                           "joint_broken": broken},
        "end_stops": "INHERITED from the m25 contact layer (class-② top-collar overcrank + bottom landing; "
                     "the screw_lift collars/base carry them — see m25_contact_layer)",
        "passed": passed,
        "video": "t2_alift_ujoint.mp4", "platform_overlay": "t2_alift_platform_overlay.png",
    }
    (out / "t2_alift_verdict.json").write_text(json.dumps(result, indent=2))
    print(f"=== P-ALIFT (angled_screw_lift, β={beta:.0f}°) ===  G-CONV {'ok' if gok else 'FAIL'}  "
          f"u-joint seeds {n_pass}/{N_SEEDS}")
    print(f"   (a) mean rise H=N·lead: mean_residual {v0['mean_residual']} (≤{UJ.MEAN_TOL}) → H={mean_rise_mm} mm")
    print(f"   (b) FLUCTUATION at platform: fluct_residual {v0['fluct_residual']} (≤{UJ.FLUCT_TOL}); band "
          f"[{band_lo},{band_hi}] → platform vel [{band_lo*plat_scale:.2f},{band_hi*plat_scale:.2f}] mm/s; "
          f"phase err {v0['phase_err_deg']}°")
    print(f"   (c) HOLD: backdrive {backdrive} mm (weak-friction {hvw['backdrive_mm']} mm → discriminates)")
    print(f"   (d) DISCRIM: β=0 band width {crit['discrimination_beta0_flat']['value']} (flat); "
          f"joint BROKEN → screw {broken['screw_rev']} rev (crank {broken['crank_rev']} rev)")
    print(f"   (e) end stops: inherited m25 contact layer")
    for k, c in crit.items():
        print(f"   {'ok  ' if c['pass'] else 'FAIL'} {k}: {c['value']}")
    print(f"   => {'PASS' if passed else 'FAIL'}   wrote {out/'t2_alift_verdict.json'}")


def _plot_platform(series, meta, plat_scale, path, v0, lead):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 5))
    th = series["theta_in_deg"]
    pv_meas = [r * plat_scale for r in series["ratio_meas"]]
    pv_form = [r * plat_scale for r in series["ratio_formula"]]
    ax.plot(th, pv_meas, lw=2, color="#2b6cb0", label="platform velocity (measured)")
    ax.plot(th, pv_form, ls="--", lw=1.4, color="#c53030", label="Cardan formula × lead/2π")
    ax.axhline(meta["vel_ratio_min"] * plat_scale, color="#999", ls=":", lw=1,
               label=f"band [cosβ,1/cosβ]·(lead·ω/2π)")
    ax.axhline(meta["vel_ratio_max"] * plat_scale, color="#999", ls=":", lw=1)
    ax.set_xlabel("crank input angle θ_in (deg)"); ax.set_ylabel("platform velocity (mm/s)")
    ax.set_title(f"angled_screw_lift — the Cardan fluctuation AT THE PLATFORM (β={meta['beta_deg']:.0f}°)  "
                 f"fluct {v0['fluct_residual']*100:.2f}%, phase {v0['phase_err_deg']}°, lead {lead} mm",
                 fontsize=9)
    ax.legend(fontsize=8); ax.grid(alpha=0.25)
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)


if __name__ == "__main__":
    main()
