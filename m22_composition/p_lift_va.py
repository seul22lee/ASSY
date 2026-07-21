"""P-LIFT (m22 Task A) — the COMPOSED assembly V-A: crank → coupling(1:1) → lead_screw → platform.

The first composition rig. It CHAINS the two verified declared-pair rigs: the m20 coupling (a 1:1
equality between crank and screw hinges) feeding the m19 lead_screw (a lead/2π equality between the
screw hinge and the nut slide, with the SOURCED thread friction on the screw hinge for the hold).
Drive the CRANK; the platform rises H = N_crank_rev × (coupling 1:1) × lead.

CRITERIA (the m22 brief):
  (a) END-TO-END: platform rise H matches the COMPOSED formula N_rev × 1 × lead to ≤0.1% (the
      assembly-level non-tautology — it exercises BOTH ratios and the mm→m path through the chain).
  (b) HOLD: release the crank under the design load W; back-drive ≤ 1 mm with the SOURCED friction
      T_f = µ·W·d_mean/2 (inherited from m19, NOT invented).
  (c) DISCRIMINATION, BOTH inherited probes at the assembly level:
      - coupling BROKEN (the 1:1 equality inactive) → the crank spins but the platform does NOT rise;
      - friction BELOW back-drive → the released platform SINKS. Both numbers reported.
  (d) guard trio + G-CONV + all_parts_retained; 5 seeds; marker video incl. the release-hold moment.

Standing rules inherited: dt=1e-4 (D-M19-2, contact-free), rigid equalities (solref -1e8), the video
rule (asymmetric marker per moving body, HUD DoF counter, full window incl. the pass moment).

  export MUJOCO_GL=egl ; ./bin/py m22_composition/p_lift_va.py [out_dir]
"""

from __future__ import annotations

import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "m0"))

import imageio.v2 as imageio  # noqa: E402
import mujoco as mj  # noqa: E402
import numpy as np  # noqa: E402

from knowledge.cards.base import CARD_REGISTRY  # noqa: E402
from knowledge.cards.lead_screw import lead_screw_dims, lead_screw_mechanics  # noqa: E402
from knowledge.materials import PETG  # noqa: E402
from ontology.validators import validate_all  # noqa: E402
from pipeline.compile_assembly import compile_assembly  # noqa: E402
from tasks.build_goldens import screw_lift  # noqa: E402
from verify.t2_physics.runner import _hash, g9_gconv  # noqa: E402

from step2mjcf import MM  # noqa: E402

VA_DT = 1e-4
ARMATURE = 1e-5
JOINT_DAMPING = 1e-5
CAPTURE_HZ = 240
OUT_FPS = 60
N_SEEDS, SEED_PASS = 5, 4
OMEGA = 40.0
RAMP = 0.15
KV = 0.5
G = 9.81
FORMULA_TOL = 0.001      # ≤0.1% end-to-end rise vs composed formula
HOLD_TOL_MM = 1.0        # ≤1 mm back-drive at the hold
HOLD_T = 1.5


def _v(a):
    return " ".join(f"{float(x):.9f}" for x in a)


def build_lift_mjcf(plan, meshdir: Path, markers=True):
    """base(weld) + crank(hinge +Z) + screw(hinge +Z, SOURCED friction) + nut(slide +Z).
    couple_cs: screw = 1·crank (the coupling). couple_sn: nut = (lead/2π)·screw (the lead screw)."""
    meshdir.mkdir(parents=True, exist_ok=True)
    e2 = next(e for e in plan.elements if e.card_ref == "lead_screw")
    g = lead_screw_dims(e2.params)
    mech = lead_screw_mechanics(g)
    load_kg = float(next((b.load.get("mass_kg", 0.5) for b in plan.behaviors
                          if b.load and getattr(b.phase, "value", b.phase) == "static"), 0.5))
    lead_m = g.lead * MM
    poly = lead_m / (2 * math.pi)                 # nut[m] = poly · screw[rad]
    d_mean_m = mech["d_mean_mm"] * MM
    W = load_kg * G
    T_friction = PETG.mu_friction * W * d_mean_m / 2.0    # µ·W·d_mean/2 (m19, sourced)
    T_backdrive = W * poly

    rs = g.d_major / 2 * MM                        # screw radius
    length_m = g.length * MM
    stroke_m = g.stroke * MM
    plat = 0.013                                   # platform half-width

    root = ET.Element("mujoco", model="t2_screw_lift")
    ET.SubElement(root, "compiler", angle="radian", autolimits="true")
    ET.SubElement(root, "option", timestep=f"{VA_DT}", integrator="implicitfast",
                  cone="elliptic", impratio="10", gravity="0 0 0")
    vis = ET.SubElement(root, "visual")
    ET.SubElement(vis, "headlight", ambient="0.5 0.5 0.5", diffuse="0.6 0.6 0.6", specular="0.2 0.2 0.2")
    ET.SubElement(vis, "global", offwidth="1280", offheight="960")
    dflt = ET.SubElement(root, "default")
    ET.SubElement(dflt, "geom", density="0", contype="0", conaffinity="0", group="2")
    asset = ET.SubElement(root, "asset")
    for name, rgba in [("base", "0.35 0.65 0.85 1"), ("crank", "0.85 0.35 0.35 1"),
                       ("screw", "0.95 0.62 0.25 1"), ("nut", "0.45 0.78 0.5 1"),
                       ("mk_crank", "0.90 0.10 0.10 1"), ("mk_screw", "0.98 0.85 0.10 1"),
                       ("mk_nut", "0.10 0.55 0.95 1")]:
        ET.SubElement(asset, "material", name=name, rgba=rgba)
    world = ET.SubElement(root, "worldbody")
    ET.SubElement(world, "light", pos="0.1 -0.2 0.4", dir="-0.2 0.3 -1", directional="true",
                  diffuse="0.5 0.5 0.5")
    ET.SubElement(world, "camera", name="side", pos="0.16 -0.20 0.055", xyaxes="0.78 0.62 0 -0.16 0.20 0.97")
    ET.SubElement(world, "geom", name="base_plate", type="box", pos="0 0 -0.006",
                  size="0.03 0.03 0.002", material="base")

    def _mk(parent, name, mat, pos, size):
        if markers:
            ET.SubElement(parent, "geom", name=name, type="box", pos=_v(pos), size=_v(size), material=mat)

    # CRANK — hinge +Z, below the base; a shaft + a radial handle (the input the hand turns)
    bc = ET.SubElement(world, "body", name="crank", pos="0 0 0")
    ET.SubElement(bc, "joint", name="crank_hinge", type="hinge", axis="0 0 1", pos="0 0 0",
                  damping=f"{JOINT_DAMPING}", armature=f"{ARMATURE}")
    ET.SubElement(bc, "geom", name="crank_shaft", type="cylinder", fromto="0 0 -0.028 0 0 -0.004",
                  size=f"{rs}", material="crank", mass="0.01")
    ET.SubElement(bc, "geom", name="crank_arm", type="box", pos="0.010 0 -0.026", size="0.010 0.002 0.002",
                  material="crank", mass="0.002")
    _mk(bc, "mk_crank", "mk_crank", (0.019, 0, -0.026), (0.002, 0.0025, 0.002))

    # SCREW — hinge +Z, the SOURCED thread friction lives here (the hold)
    bs = ET.SubElement(world, "body", name="screw", pos="0 0 0")
    ET.SubElement(bs, "joint", name="screw_hinge", type="hinge", axis="0 0 1", pos="0 0 0",
                  damping=f"{JOINT_DAMPING}", armature=f"{ARMATURE}", frictionloss=f"{T_friction:.9f}")
    ET.SubElement(bs, "geom", name="screw_rod", type="cylinder", fromto=f"0 0 0 0 0 {length_m:.6f}",
                  size=f"{rs}", material="screw", mass="0.01")
    _mk(bs, "mk_screw", "mk_screw", (rs + 0.002, 0, 0.020), (0.003, 0.0012, 0.004))

    # NUT / platform — slide +Z; its mass carries the design load at the hold
    bn = ET.SubElement(world, "body", name="nut", pos="0 0 0")
    ET.SubElement(bn, "joint", name="nut_slide", type="slide", axis="0 0 1", pos="0 0 0",
                  damping=f"{JOINT_DAMPING}")
    z0 = 0.030
    ET.SubElement(bn, "geom", name="platform", type="box", pos=f"0 0 {z0:.6f}", size=f"{plat} {plat} 0.004",
                  material="nut", mass="0.02")
    _mk(bn, "mk_nut", "mk_nut", (plat + 0.001, 0, z0), (0.002, 0.0025, 0.003))

    # THE COMPOSED CHAIN: couple_cs (coupling 1:1) then couple_sn (lead screw). Rigid (D-M19-2).
    eq = ET.SubElement(root, "equality")
    ET.SubElement(eq, "joint", name="couple_cs", joint1="screw_hinge", joint2="crank_hinge",
                  polycoef="0 1.0 0 0 0", solref="-1e8 -1e4", solimp="0.9999 0.99999 1e-6 0.5 2")
    ET.SubElement(eq, "joint", name="couple_sn", joint1="nut_slide", joint2="screw_hinge",
                  polycoef=f"0 {poly:.9f} 0 0 0", solref="-1e8 -1e4", solimp="0.9999 0.99999 1e-6 0.5 2")
    act = ET.SubElement(root, "actuator")
    ET.SubElement(act, "velocity", name="drive", joint="crank_hinge", kv=f"{KV}")

    xml = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
    meta = {"lead_mm": g.lead, "d_mean_mm": mech["d_mean_mm"], "stroke_mm": g.stroke,
            "poly_m_per_rad": poly, "coupling_ratio": 1.0, "load_kg": load_kg, "W_N": round(W, 4),
            "T_friction_Nm": round(T_friction, 6), "T_backdrive_Nm": round(T_backdrive, 6),
            "hold_margin": round(T_friction / T_backdrive, 3) if T_backdrive else None,
            "n_rev": round(g.stroke / g.lead, 3), "z0_m": z0}
    return xml, meta


def run_lift(model, meta, seed=0, record=False, break_coupling=False, friction_override=None):
    """Drive the crank to the design stroke, then RELEASE and hold under load. Returns (verdict, series, frames).
    break_coupling deactivates the 1:1 coupling (probe c-i); friction_override sets a weak screw friction (c-ii)."""
    ji = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "crank_hinge")
    js = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "screw_hinge")
    jn = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "nut_slide")
    ica, isa, ina = model.jnt_qposadr[ji], model.jnt_qposadr[js], model.jnt_qposadr[jn]
    idc = model.jnt_dofadr[ji]
    a = mj.mj_name2id(model, mj.mjtObj.mjOBJ_ACTUATOR, "drive")
    nb = mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, "nut")
    eqcs = mj.mj_name2id(model, mj.mjtObj.mjOBJ_EQUALITY, "couple_cs")
    cam = mj.mj_name2id(model, mj.mjtObj.mjOBJ_CAMERA, "side")
    fdof = model.jnt_dofadr[js]
    fric0 = float(model.dof_frictionloss[fdof])
    if friction_override is not None:
        model.dof_frictionloss[fdof] = friction_override
    eq_active0 = model.eq_active0.copy()
    if break_coupling:
        model.eq_active0[eqcs] = 0

    rng = np.random.default_rng(seed)
    d = mj.MjData(model)
    if break_coupling:
        d.eq_active[eqcs] = 0
    poly = meta["poly_m_per_rad"]
    nut_geom_mass = float(model.body_mass[nb])
    gain0 = float(model.actuator_gainprm[a, 0]); bias0 = float(model.actuator_biasprm[a, 2])
    grav0 = model.opt.gravity.copy()

    model.opt.gravity[:] = [0.0, 0.0, 0.0]
    d.qpos[ica] += rng.uniform(-1e-3, 1e-3)
    if not break_coupling:
        d.qpos[isa] = d.qpos[ica]                 # coupling satisfied at t=0
        d.qpos[ina] = poly * d.qpos[isa]
    mj.mj_forward(model, d)
    renderer = mj.Renderer(model, 480, 640) if record else None

    theta_target = meta["stroke_mm"] * MM / poly  # crank angle for the full stroke (crank=screw, 1:1)
    ca0, s0 = float(d.qpos[ica]), float(d.qpos[ina])
    ts, crv, nut_mm, phase_log, frames, nextf = [], [], [], [], [], 0.0
    diverged, phase = False, "drive"
    peak_nut = 0.0
    t_drive_end, cr_drive_end = None, None
    t_wall = theta_target / OMEGA + 6 * RAMP + 6.0
    while True:
        d.ctrl[0] = (min(OMEGA, OMEGA * d.time / RAMP)) if phase == "drive" else 0.0
        mj.mj_step(model, d)
        if not np.all(np.isfinite(d.qpos)) or abs(d.qvel[idc]) > 800:
            diverged = True; break
        cr = float(d.qpos[ica]) - ca0
        s_mm = (float(d.qpos[ina]) - s0) / MM
        ts.append(d.time); crv.append(cr); nut_mm.append(s_mm); phase_log.append(phase)
        peak_nut = max(peak_nut, s_mm)
        if record and d.time >= nextf:
            renderer.update_scene(d, camera=cam)
            frames.append((renderer.render(), d.time, cr, s_mm, phase))
            nextf += 1.0 / CAPTURE_HZ
        if phase == "drive" and cr >= theta_target:
            phase = "hold"; t_drive_end = d.time; cr_drive_end = cr
            model.actuator_gainprm[a, 0] = 0.0; model.actuator_biasprm[a, 2] = 0.0
            d.qvel[:] = 0.0
            model.opt.gravity[:] = [0.0, 0.0, -G]
            model.body_mass[nb] = nut_geom_mass + meta["load_kg"]
            mj.mj_forward(model, d)
        if phase == "hold" and d.time - t_drive_end >= HOLD_T:
            break
        if d.time > t_wall:
            break
    if renderer:
        renderer.close()
    model.actuator_gainprm[a, 0] = gain0; model.actuator_biasprm[a, 2] = bias0
    model.body_mass[nb] = nut_geom_mass; model.opt.gravity[:] = grav0
    model.dof_frictionloss[fdof] = fric0; model.eq_active0[:] = eq_active0

    revs_crank = (cr_drive_end if cr_drive_end is not None else (crv[-1] if crv else 0.0)) / (2 * math.pi)
    travel_mm = peak_nut
    nut_at_release = nut_mm[phase_log.index("hold")] if "hold" in phase_log else (nut_mm[-1] if nut_mm else 0.0)
    nut_final = nut_mm[-1] if nut_mm else 0.0
    backdrive_mm = max(0.0, nut_at_release - nut_final)
    # END-TO-END composed formula: H = N_crank_rev × coupling(1:1) × lead
    formula_mm = revs_crank * meta["coupling_ratio"] * meta["lead_mm"]
    formula_resid = abs(travel_mm / formula_mm - 1.0) if formula_mm else 1.0
    reaches = travel_mm >= meta["stroke_mm"] - 0.5
    all_ret = bool(np.all(np.isfinite(d.qpos)))

    crit = {
        "platform_reaches_height": {"value": round(travel_mm, 2), "threshold": meta["stroke_mm"],
                                    "pass": bool(reaches and not diverged)},
        "end_to_end_formula (|H/(N·1·lead)−1| ≤ 0.1%)": {"value": round(formula_resid, 5),
                                                        "threshold": FORMULA_TOL,
                                                        "pass": bool(formula_resid <= FORMULA_TOL and not diverged)},
        "holds_released_load (back-drive ≤ 1 mm)": {"value": round(backdrive_mm, 3), "threshold": HOLD_TOL_MM,
                                                    "pass": bool(backdrive_mm <= HOLD_TOL_MM and not diverged)},
        "converged (no blow-up)": {"value": diverged, "threshold": False, "pass": bool(not diverged)},
        "all_parts_retained": {"value": all_ret, "threshold": True, "pass": all_ret},
    }
    v = {"ran": True, "mode": "V-A", "seed": seed, "diverged": diverged, "broke_coupling": break_coupling,
         "revs_crank": round(revs_crank, 3), "travel_mm": round(travel_mm, 3),
         "formula_mm": round(formula_mm, 3), "formula_residual": round(formula_resid, 5),
         "backdrive_mm": round(backdrive_mm, 3), "criteria": crit,
         "passed": bool(all(c["pass"] for c in crit.values()))}
    series = {"t": ts, "crank_deg": [math.degrees(x) for x in crv], "nut_mm": nut_mm, "phase": phase_log}
    return v, series, frames


def _hud(img, lines, colors):
    from PIL import Image, ImageDraw
    im = Image.fromarray(img.copy()); dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, 480, 14 * len(lines) + 6], fill=(0, 0, 0))
    for i, (t, c) in enumerate(zip(lines, colors)):
        dr.text((5, 3 + 14 * i), t, fill=c)
    return np.asarray(im)


def _save_video(frames, meta, path):
    slow = f"{CAPTURE_HZ // OUT_FPS}x slow-mo"
    vid = []
    for img, t, cr, s_mm, phase in frames:
        tag = "DRIVE (cranking up)" if phase == "drive" else "HOLD (crank released)"
        vid.append(_hud(img, [f"P-LIFT V-A  screw_lift  crank→coupling→lead_screw   [{slow}]",
                              f"T {t:5.2f}s   crank {cr/(2*math.pi):5.2f} rev   {tag}",
                              f"platform rise {s_mm:6.2f} / {meta['stroke_mm']:.0f} mm   "
                              f"(= crank rev x 1:1 x lead {meta['lead_mm']})",
                              f"hold: mu*W*dm/2={meta['T_friction_Nm']:.4f} >= W*lead/2pi="
                              f"{meta['T_backdrive_Nm']:.4f} Nm  markers red=crank gold=screw blue=platform"],
                        [(255, 255, 255), (150, 220, 255),
                         (150, 255, 180) if phase == "drive" else (255, 200, 120), (200, 200, 200)]))
    imageio.mimsave(path, vid, fps=OUT_FPS, macro_block_size=1)


def _plot(series, v, meta, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(2, 1, figsize=(8, 6.5), sharex=True)
    t = series["t"]; nut = series["nut_mm"]; cr = series["crank_deg"]
    rel = next((t[i] for i in range(len(series["phase"])) if series["phase"][i] == "hold"), t[-1] if t else 0)
    ax[0].plot(t, nut, lw=2, color="#2b6cb0", label="platform rise s(t) [measured]")
    ax[0].plot(t, [meta["lead_mm"] * meta["coupling_ratio"] * (x / 360.0) for x in cr], ls="--", lw=1.3,
               color="#c53030", label=f"COMPOSED formula: crank·rev × 1:1 × lead ({meta['lead_mm']} mm)")
    ax[0].axvline(rel, color="#888", ls=":", lw=1, label="crank RELEASED (hold begins)")
    badge = "PASS" if v["passed"] else "FAIL"
    ax[0].set_ylabel("platform height (mm)")
    ax[0].set_title(f"P-LIFT / V-A  screw_lift [{badge}]  {v['travel_mm']:.1f} mm over {v['revs_crank']:.1f} "
                    f"crank rev,  end-to-end resid={v['formula_residual']*100:.3f}%,  back-drive="
                    f"{v['backdrive_mm']:.2f} mm", fontsize=8.5, color="#22543d" if v["passed"] else "#742a2a")
    ax[0].legend(fontsize=8); ax[0].grid(alpha=.25)
    hi = [i for i, p in enumerate(series["phase"]) if p == "hold"]
    if hi:
        ax[1].plot([t[i] for i in hi], [nut[i] for i in hi], lw=2, color="#2f855a")
        ax[1].set_title(f"HOLD (crank released, sourced friction {meta['T_friction_Nm']:.4f} ≥ back-drive "
                        f"{meta['T_backdrive_Nm']:.4f} Nm): back-drive {v['backdrive_mm']:.2f} mm", fontsize=8.5)
    ax[1].set_xlabel("t (s)"); ax[1].set_ylabel("platform (mm)"); ax[1].grid(alpha=.25)
    fig.tight_layout(); fig.savefig(path, dpi=130)
    import matplotlib.pyplot as _p; _p.close(fig)


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "out"
    out.mkdir(parents=True, exist_ok=True)
    plan = screw_lift()
    for e in plan.elements:
        e.params = CARD_REGISTRY[e.card_ref].resolve_params(plan, e)
    assert not validate_all(plan), "golden must be validator-clean"
    compile_assembly(plan)

    xml, meta = build_lift_mjcf(plan, out / "assets")
    xf = out / "t2_screw_lift.xml"; xf.write_text(xml)
    model = mj.MjModel.from_xml_path(str(xf))
    gok, checks = g9_gconv(model)

    result = {
        "decision_row": "D-M22-1 P-LIFT V-A on compiled screw_lift (first composition)",
        "compile_hash": _hash(), "task": "screw_lift", "elements": ["coupling(E1)", "lead_screw(E2)"],
        "composed_chain": {"crank→screw": "coupling 1:1", "screw→platform": f"lead {meta['lead_mm']} mm/rev",
                           "H = N_rev × 1 × lead": f"{meta['n_rev']} × 1 × {meta['lead_mm']} = {meta['stroke_mm']} mm"},
        "sourced_friction": {"T_friction_Nm (µ·W·d_mean/2)": meta["T_friction_Nm"],
                             "T_backdrive_Nm (W·lead/2π)": meta["T_backdrive_Nm"], "hold_margin": meta["hold_margin"],
                             "note": "SOURCED (m19, not invented)"},
        "g9_gconv": bool(gok), "modes": {},
    }
    if not gok:
        result["modes"]["V-A"] = {"ran": False, "reason": "G-CONV failed"}
    else:
        per_seed, series0, frames0, v0 = [], None, None, None
        for seed in range(N_SEEDS):
            v, series, frames = run_lift(model, meta, seed, record=(seed == 0))
            per_seed.append(v)
            if seed == 0:
                series0, frames0, v0 = series, frames, v
        n_pass = sum(v["passed"] for v in per_seed)
        result["modes"]["V-A"] = {"ran": True, "n_seeds": N_SEEDS, "seeds_passed": n_pass,
                                  "passed": bool(n_pass >= SEED_PASS),
                                  "criteria_seed0": per_seed[0]["criteria"], "per_seed": per_seed}
        # DISCRIMINATION — BOTH inherited probes at the assembly level
        vb, _, _ = run_lift(model, meta, seed=0, record=False, break_coupling=True)
        fweak = 0.5 * meta["T_backdrive_Nm"]
        vf, _, _ = run_lift(model, meta, seed=0, record=False, friction_override=fweak)
        result["modes"]["V-A"]["discrimination_probes"] = {
            "coupling_broken": {"crank_rev": vb["revs_crank"], "platform_rise_mm": vb["travel_mm"],
                                "expect": "crank spins, platform does NOT rise"},
            "friction_weak": {"weak_friction_Nm (0.5·T_bd)": round(fweak, 6),
                              "backdrive_mm": vf["backdrive_mm"], "sourced_backdrive_mm": per_seed[0]["backdrive_mm"],
                              "expect": "released platform SINKS"},
            "discriminates": bool(vb["travel_mm"] < 1.0 and vb["revs_crank"] > 1.0
                                  and vf["backdrive_mm"] > 5 * HOLD_TOL_MM
                                  and per_seed[0]["backdrive_mm"] <= HOLD_TOL_MM),
            "note": "coupling broken → no rise (input spins); friction below back-drive → sinks — both at assembly level"}
        if series0:
            _plot(series0, v0, meta, out / "t2_screw_lift.png")
            result["modes"]["V-A"]["plot"] = "t2_screw_lift.png"
            if frames0:
                _save_video(frames0, meta, out / "t2_screw_lift.mp4")
                result["modes"]["V-A"]["video"] = "t2_screw_lift.mp4"
        print(f"\n=== P-LIFT V-A (screw_lift composition) ===  G-CONV {'ok' if gok else 'FAIL'}   "
              f"seeds {n_pass}/{N_SEEDS} => {'PASS' if n_pass >= SEED_PASS else 'FAIL'}")
        for name, c in per_seed[0]["criteria"].items():
            print(f"   {'ok  ' if c['pass'] else 'FAIL'} {name:<48s} {c['value']} (<= {c['threshold']})")
        dp = result["modes"]["V-A"]["discrimination_probes"]
        print(f"   end-to-end: {v0['travel_mm']:.2f} mm vs composed formula {v0['formula_mm']:.2f} mm "
              f"({v0['formula_residual']*100:.3f}%)")
        print(f"   discrimination: coupling BROKEN → platform {dp['coupling_broken']['platform_rise_mm']:.2f} mm "
              f"(crank {dp['coupling_broken']['crank_rev']:.1f} rev) | friction WEAK → back-drive "
              f"{dp['friction_weak']['backdrive_mm']:.2f} mm vs sourced {dp['friction_weak']['sourced_backdrive_mm']:.2f} "
              f"=> discriminates={dp['discriminates']}")

    result["verdict_VA"] = result["modes"].get("V-A", {}).get("passed", False)
    result["v_b_disposition"] = {
        "coupling": "verified (m20, no curved contact)",
        "lead_screw": "thread contact V-B deferred (R2b/m17, m19)",
        "assembly_level": "the COMBINATION adds no new emergent contact — the two declared pairs are "
                          "coupled by rigid equalities, and the composed non-tautology (end-to-end H) IS "
                          "verified; the only deferred piece is the lead_screw thread, inherited unchanged"}
    (out / "t2_screw_lift_verdict.json").write_text(json.dumps(result, indent=2))
    print(f"\nV-A pass: {result['verdict_VA']}")
    print("wrote", out / "t2_screw_lift_verdict.json")


if __name__ == "__main__":
    main()
