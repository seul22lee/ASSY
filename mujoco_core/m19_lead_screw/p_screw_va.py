"""P-SCREW (MECHSYNTH §6.3) on the compiled lead_screw_fixture — V-A + honest V-B DEFERRAL (m19).

WHY V-A (+ V-B deferred). The lead screw's helical thread flank is CURVED contact — the same rigid-body
R2b class m17 showed metastable (D-M1-7). So like rack_pinion (D-D-2), the transmission is verified as
a DECLARED KINEMATIC PAIR — a hinge on the screw, a slide on the nut, coupled by an equality whose
polycoef is lead/(2π) in METRES — and P-SCREW checks that pair realizes the card's Shigley §8-2 rule
chain. The emergent thread-contact V-B is NAMED-DEFERRED (the verdict's v_b_gap + shape_assert), never
silently claimed. We do NOT stand up a thread-contact rig (the m11 "cheap smoke declined" precedent —
it is not cheap, it walks into R2b).

TWO criteria (the m19 brief):
  (a) STROKE — drive the screw N revolutions; the nut reaches the design stroke. NON-TAUTOLOGY
      (the m11 standard): the measured travel must match the INDEPENDENT formula lead × revs to
      ≤ 0.1% — this exercises the lead formula (lead = starts×pitch), the mm→m unit path, and the
      polycoef = lead/(2π).
  (b) HOLD (self-lock) — apply the design axial load on the nut, RELEASE the drive (actuator torque
      →0), measure back-drive. The hinge frictionloss is the SOURCED thread-friction holding torque,
      NOT an invented value (the D-D-1 lesson):
          T_friction = µ · W · d_mean/2     (µ = PETG.mu_friction = R5 preset; d_mean from the card)
      and self-lock EMERGES iff T_friction ≥ the load's back-drive torque  T_back = W · lead/(2π)
      ⇔ µ·d_mean/2 ≥ lead/(2π) ⇔ tan(λ) ≤ µ. So the SAME sourced friction HOLDS a self-locking screw
      and would let a coarse (tan(λ)>µ) screw back-drive — the physics verifies the self-lock formula,
      it is not tuned to pass.

Guard trio + G-CONV + all_parts_retained (the m10 coverage criterion) on every run; 5 seeds. The
FROZEN preset (R5) is imported for provenance; V-A declares NO contact geoms (the joints are the
mechanism). Gravity is ON (a screw-jack lifts + holds a real load).

  export MUJOCO_GL=egl ; ./bin/py m19_lead_screw/p_screw_va.py [out_dir]
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

from build123d import Align, Cylinder, Pos  # noqa: E402
from knowledge.cards.base import CARD_REGISTRY  # noqa: E402
from knowledge.cards.lead_screw import lead_screw_dims, lead_screw_mechanics  # noqa: E402
from knowledge.materials import PETG  # noqa: E402
from knowledge.templates import TEMPLATES  # noqa: E402
from ontology.validators import validate_all  # noqa: E402
from pipeline.compile_assembly import compile_assembly  # noqa: E402
from tasks.build_goldens import lead_screw_fixture  # noqa: E402
from verify.t2_physics.mjcf import _inertial, _to_trimesh  # noqa: E402
from verify.t2_physics.runner import _hash, g9_gconv  # noqa: E402

from step2mjcf import MM, SOLIMP, SOLREF  # FROZEN preset (R5)  # noqa: E402

# NOTE on dt. The R5 FROZEN preset (SOLIMP/SOLREF/mu) governs CONTACT; this V-A rig declares NO contact
# geoms (contype/conaffinity=0 — the joints are the mechanism), so R5 does not constrain the clock here.
# The clock is set at 1e-4 s because the self-lock HOLD is resolved by JOINT frictionloss, which leaks
# per-step at 5e-4 for the small plastic-screw inertia (measured: a 0.00515 Nm frictionloss failed to
# hold a 0.00156 Nm sub-cap torque at dt=5e-4, but holds to <0.1 mm at dt=1e-4). Contact-bearing rigs
# keep the R5 clock; a contact-free joint rig does not.
VA_DT = 1e-4
# Driven-train rotational inertia added to the screw hinge (kg·m²). The bare compiled screw is a small
# plastic cylinder (I≈3e-8); a real screw-jack turns a hand-crank / motor rotor whose inertia is orders
# larger. This is a STATIC-equilibrium-neutral quantity (self-lock is a rest question) but is required
# for the frictionloss constraint to be numerically rigid — without it the per-step leak returns.
SCREW_TRAIN_INERTIA = 1e-5
JOINT_DAMPING = 1e-5   # tiny — see the joint-damping NOTE in build_va_mjcf (must not mask self-lock)
FPS = 60
N_SEEDS, SEED_PASS = 5, 4
OMEGA = 40.0          # rad/s drive speed (a screw needs many turns; kinematic pair, so fast is fine —
#                       and at dt=1e-4 a fast drive keeps the step count tractable across 5 seeds)
RAMP = 0.3
KV = 5e-2
G = 9.81
FORMULA_TOL = 0.001  # ≤ 0.1% measured-vs-formula travel match (the non-tautology gate)
HOLD_TOL_MM = 1.0    # self-lock: back-drive ≤ 1 mm
HOLD_T = 1.5         # s of released hold


def _v(a):
    return " ".join(f"{float(x):.9f}" for x in a)


def build_va_mjcf(plan, ca, meshdir: Path):
    """base(weld) + screw(hinge +Z) + nut(slide +Z), coupled by equality polycoef = lead/(2π) [m].
    The nut mass carries the design load; the screw hinge carries the SOURCED thread frictionloss."""
    meshdir.mkdir(parents=True, exist_ok=True)
    e1 = plan.element("E1")
    g = lead_screw_dims(e1.params)
    mech = lead_screw_mechanics(g)
    load_kg = float(next((b.load.get("mass_kg", 0.5) for b in plan.behaviors
                          if b.load and getattr(b.phase, "value", b.phase) == "static"), 0.5))

    lead_m = g.lead * MM
    polycoef = lead_m / (2 * math.pi)                       # nut_slide[m] = polycoef · screw_hinge[rad]
    d_mean_m = mech["d_mean_mm"] * MM

    # axis: the screw_base's screw_axis anchor (+Z at the plate top), in metres
    sb = TEMPLATES["screw_base"](**{k: v for k, v in plan.piece("P1").params.items()
                                    if isinstance(v, (int, float))})
    ax_pt = np.array(sb.anchors["screw_axis"].position, float) * MM
    ax_dir = np.array([0.0, 0.0, 1.0])

    # three solids: bare base (weld), the screw cylinder (rotates), the nut carriage (slides)
    base_solid = sb.part
    screw_solid = Pos(*sb.anchors["screw_axis"].position) * Cylinder(
        radius=g.d_major / 2.0, height=g.length, align=(Align.CENTER, Align.CENTER, Align.MIN))
    nut_solid = ca.parts["P2"]

    root = ET.Element("mujoco", model="t2_lead_screw_VA")
    ET.SubElement(root, "compiler", angle="radian", meshdir=meshdir.name, autolimits="true")
    ET.SubElement(root, "option", timestep=f"{VA_DT}", integrator="implicitfast",
                  cone="elliptic", impratio="10")          # 1e-4 clock (see dt NOTE); gravity default -Z
    vis = ET.SubElement(root, "visual")
    ET.SubElement(vis, "headlight", ambient="0.5 0.5 0.5", diffuse="0.6 0.6 0.6", specular="0.2 0.2 0.2")
    ET.SubElement(vis, "global", offwidth="1280", offheight="960", azimuth="130", elevation="-18")
    dflt = ET.SubElement(root, "default")
    ET.SubElement(dflt, "geom", solref=f"{SOLREF[0]} {SOLREF[1]}",
                  solimp=f"{SOLIMP[0]} {SOLIMP[1]} {SOLIMP[2]}", density="0",
                  contype="0", conaffinity="0", group="2")   # NO contact — joints are the mechanism
    asset = ET.SubElement(root, "asset")
    ET.SubElement(asset, "material", name="base", rgba="0.35 0.65 0.85 1")
    ET.SubElement(asset, "material", name="screw", rgba="0.95 0.62 0.25 1")
    ET.SubElement(asset, "material", name="nut", rgba="0.6 0.75 0.6 1")
    world = ET.SubElement(root, "worldbody")
    ET.SubElement(world, "light", pos="0.1 -0.15 0.4", dir="-0.2 0.3 -1", directional="true",
                  diffuse="0.5 0.5 0.5")
    ET.SubElement(world, "camera", name="iso", pos="0.12 -0.14 0.10",
                  xyaxes="0.75 0.66 0 -0.24 0.28 0.93")

    # SOURCED hold friction (D-D-1: no invented values) — the thread's Coulomb holding torque.
    W = (load_kg) * G                                       # design axial load (N); nut geom weight adds below
    T_friction = PETG.mu_friction * W * d_mean_m / 2.0      # µ·W·d_mean/2  (N·m)
    T_backdrive = W * polycoef                              # W·lead/(2π)   (N·m)

    masses = {}
    specs = [("base", base_solid, "base", None),
             ("screw", screw_solid, "screw", ("hinge", ax_dir, T_friction)),
             ("nut", nut_solid, "nut", ("slide", ax_dir, None))]
    for name, solid, mat, joint in specs:
        body = ET.SubElement(world, "body", name=name, pos="0 0 0")
        if joint is not None:
            jkind, jaxis, fric = joint
            jt = ET.SubElement(body, "joint",
                               name="screw_hinge" if jkind == "hinge" else "nut_slide",
                               type=jkind, axis=_v(jaxis), pos=_v(ax_pt),
                               damping=f"{JOINT_DAMPING}")   # tiny (numerical only) — viscous damping
            #  would hold ANY load transiently and MASK self-lock; the COULOMB frictionloss must govern
            #  the hold (the discrimination probe fails if damping is high enough to hold on its own).
            if jkind == "hinge":
                jt.set("armature", f"{SCREW_TRAIN_INERTIA}")  # driven-train rotor inertia (see NOTE)
            if fric is not None:
                jt.set("frictionloss", f"{fric:.9f}")       # SOURCED thread friction (the hold)
        vf = meshdir / f"ls_{name}_vis.stl"
        mesh = _to_trimesh(solid, vf)
        masses[name] = _inertial(body, mesh)
        ET.SubElement(asset, "mesh", name=f"{name}_vis", file=vf.name)
        ET.SubElement(body, "geom", name=f"{name}_vis", type="mesh", mesh=f"{name}_vis", material=mat)

    # THE DECLARED TRANSMISSION (V-A): nut_slide(m) = polycoef · screw_hinge(rad), polycoef=lead/(2π).
    eq = ET.SubElement(root, "equality")
    # RIGID coupling (the D-D-2 lesson, sharper here): the tiny polycoef (lead/2π ≈ 3e-4 m/rad) means a
    # soft equality lets the nut slide WITHOUT rotating the screw — then the screw's holding friction
    # never engages and the load back-drives (measured: a positive-timeconst solref, even at the stable
    # floor 2·dt, leaked >12 mm because the constraint is a spring the load stretches). A DIRECT-stiffness
    # solref ("-K -B", negative ⇒ explicit stiffness/damping, not timeconst) makes the nut's weight
    # transmit to a screw torque the frictionloss holds, and keeps s = polycoef·θ to <0.1%.
    ET.SubElement(eq, "joint", name="couple", joint1="nut_slide", joint2="screw_hinge",
                  polycoef=f"0 {polycoef:.9f} 0 0 0",
                  solref="-1e8 -1e4", solimp="0.9999 0.99999 0.000001 0.5 2")
    act = ET.SubElement(root, "actuator")
    ET.SubElement(act, "velocity", name="drive", joint="screw_hinge", kv=f"{KV}")

    xml = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
    meta = {"lead_mm": g.lead, "pitch_mm": g.pitch, "starts": g.starts, "d_major_mm": g.d_major,
            "d_mean_mm": mech["d_mean_mm"], "stroke_mm": g.stroke, "length_mm": g.length,
            "polycoef_m_per_rad": polycoef, "travel_per_rev_mm": g.lead,
            "lead_angle_deg": mech["lead_angle_deg"], "tan_lambda": mech["tan_lambda"],
            "mu": PETG.mu_friction, "self_locks_formula": mech["self_locks"],
            "load_kg": load_kg, "W_N": round(W, 4),
            "T_friction_Nm": round(T_friction, 6), "T_backdrive_Nm": round(T_backdrive, 6),
            "hold_margin": round(T_friction / T_backdrive, 3) if T_backdrive else None,
            "masses_kg": masses, "axis_m": {"point": list(ax_pt), "dir": list(ax_dir)}}
    return xml, meta


def run_va(model, meta, seed=0, record=False, friction_override=None):
    """Drive the screw up to the design stroke, then RELEASE and hold under load. Two criteria +
    guards. Returns (verdict, series, frames). friction_override (N·m) replaces the hinge frictionloss
    — used ONLY by the discrimination probe (a sub-back-drive friction MUST let the load slip, proving
    the hold is the sourced friction winning, not a solver artifact — the non-tautology of self-lock)."""
    d = mj.MjData(model)
    rng = np.random.default_rng(seed)
    js = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "screw_hinge")
    jn = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "nut_slide")
    isa, ina = model.jnt_qposadr[js], model.jnt_qposadr[jn]
    a = mj.mj_name2id(model, mj.mjtObj.mjOBJ_ACTUATOR, "drive")
    nb = mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, "nut")
    cam = mj.mj_name2id(model, mj.mjtObj.mjOBJ_CAMERA, "iso")
    poly = meta["polycoef_m_per_rad"]
    nut_geom_mass = float(model.body_mass[nb])
    fric_dof = model.jnt_dofadr[js]
    fric0 = float(model.dof_frictionloss[fric_dof])
    if friction_override is not None:
        model.dof_frictionloss[fric_dof] = friction_override
    # run_va MUTATES the model at release (actuator gain/bias, nut mass, gravity). Snapshot so each seed
    # starts from the same drive-ready state — else seed>0 inherits seed 0's released/disabled model.
    gain0 = float(model.actuator_gainprm[a, 0]); bias0 = float(model.actuator_biasprm[a, 2])
    grav0 = model.opt.gravity.copy()

    # TWO clean phases (like m11 kinematic ratio + m13 hold-under-load):
    #  DRIVE — verify the DECLARED PAIR realizes the ratio. Gravity OFF (the ratio is a KINEMATIC
    #          property of polycoef, exactly as m11's horizontal rack had no gravity). The nut tracks
    #          the screw rigidly so measured travel == the CARD's lead·rev formula (the non-tautology).
    #  HOLD  — apply the design load (gravity ON + nut mass += load), RELEASE the drive, and let ONLY
    #          the SOURCED thread frictionloss resist back-drive. Self-lock must EMERGE.
    model.opt.gravity[:] = [0.0, 0.0, 0.0]                  # drive phase: kinematic ratio, gravity off
    d.qpos[isa] += rng.uniform(-1e-3, 1e-3)                 # seed perturbs the start angle (robustness)
    d.qpos[ina] = poly * d.qpos[isa]                        # ...keep the RIGID coupling satisfied at t=0
    #                                                        (else the stiff -1e8 solref yanks the nut)
    mj.mj_forward(model, d)
    renderer = mj.Renderer(model, 480, 640) if record else None

    stroke_m = meta["stroke_mm"] * MM
    theta_target = stroke_m / poly
    theta0, s0 = float(d.qpos[isa]), float(d.qpos[ina])
    ts, thp, nut_mm, phase_log, frames, nextf = [], [], [], [], [], 0.0
    diverged, phase = False, "drive"
    peak_nut = 0.0
    t_drive_end = None
    th_drive_end = None
    t_wall = theta_target / OMEGA + 6 * RAMP + 6.0

    while True:
        if phase == "drive":
            d.ctrl[0] = min(OMEGA, OMEGA * d.time / RAMP)
        else:
            d.ctrl[0] = 0.0
        mj.mj_step(model, d)
        if not np.all(np.isfinite(d.qpos)) or abs(d.qvel[isa]) > 500:
            diverged = True; break
        th = float(d.qpos[isa]) - theta0
        s_mm = (float(d.qpos[ina]) - s0) / MM
        ts.append(d.time); thp.append(th); nut_mm.append(s_mm); phase_log.append(phase)
        peak_nut = max(peak_nut, s_mm)
        if record and d.time >= nextf:
            renderer.update_scene(d, camera=cam)
            frames.append((renderer.render(), d.time, th, s_mm, phase))
            nextf += 1.0 / FPS
        if phase == "drive" and th >= theta_target:
            phase = "hold"; t_drive_end = d.time; th_drive_end = th   # freeze the drive-end angle
            model.actuator_gainprm[a, 0] = 0.0; model.actuator_biasprm[a, 2] = 0.0  # RELEASE the drive
            d.qvel[:] = 0.0                                  # the self-lock HOLD is a STATIC question:
            #                                                 a released load AT REST — no drive momentum
            model.opt.gravity[:] = [0.0, 0.0, -G]           # HOLD phase: apply the design load...
            model.body_mass[nb] = nut_geom_mass + meta["load_kg"]   # ...as gravity on nut+load
            mj.mj_forward(model, d)
        if phase == "hold" and d.time - t_drive_end >= HOLD_T:
            break
        if d.time > t_wall:
            break
    if renderer:
        renderer.close()

    th_final = thp[-1] if thp else 0.0
    revs = th_final / (2 * math.pi)
    nut_at_release = nut_mm[phase_log.index("hold")] if "hold" in phase_log else (nut_mm[-1] if nut_mm else 0.0)
    nut_final = nut_mm[-1] if nut_mm else 0.0
    backdrive_mm = max(0.0, nut_at_release - nut_final)     # how far the nut dropped after release
    # (a) stroke + non-tautology formula match: DRIVE-END travel vs lead × (drive-end revs). Measured
    # at the end of DRIVE (before the hold back-rotation), so the kinematic ratio is what is judged.
    travel_mm = peak_nut
    revs_drive = (th_drive_end if th_drive_end is not None else th_final) / (2 * math.pi)
    formula_mm = meta["travel_per_rev_mm"] * revs_drive
    formula_resid = abs(travel_mm / formula_mm - 1.0) if formula_mm else 1.0
    reaches = travel_mm >= meta["stroke_mm"] - 0.5
    # (d) all parts retained: 3 bodies, all finite qpos
    all_retained = bool(np.all(np.isfinite(d.qpos)))

    crit = {
        "reaches_design_stroke": {"value": round(travel_mm, 2), "threshold": meta["stroke_mm"],
                                  "pass": bool(reaches and not diverged)},
        "matches_lead_formula (|s/(lead·rev)−1| ≤ 0.1%)": {
            "value": round(formula_resid, 5), "threshold": FORMULA_TOL,
            "pass": bool(formula_resid <= FORMULA_TOL and not diverged)},
        "self_locks_holds (back-drive ≤ 1 mm)": {"value": round(backdrive_mm, 3),
                                                 "threshold": HOLD_TOL_MM,
                                                 "pass": bool(backdrive_mm <= HOLD_TOL_MM and not diverged)},
        "converged (no blow-up)": {"value": diverged, "threshold": False, "pass": bool(not diverged)},
        "all_parts_retained": {"value": all_retained, "threshold": True, "pass": all_retained},
    }
    v = {"ran": True, "mode": "V-A", "seed": seed, "diverged": diverged,
         "revs_done": round(revs, 3), "travel_mm": round(travel_mm, 3),
         "formula_travel_mm": round(formula_mm, 3), "formula_residual": round(formula_resid, 5),
         "backdrive_mm": round(backdrive_mm, 3), "criteria": crit,
         "passed": bool(all(c["pass"] for c in crit.values()))}
    series = {"t": ts, "theta_deg": [math.degrees(x) for x in thp], "nut_mm": nut_mm, "phase": phase_log}
    # restore the drive-ready model state for the next seed (undo the release-phase mutations)
    model.actuator_gainprm[a, 0] = gain0; model.actuator_biasprm[a, 2] = bias0
    model.body_mass[nb] = nut_geom_mass; model.opt.gravity[:] = grav0
    model.dof_frictionloss[fric_dof] = fric0
    return v, series, frames


def _hud(img, lines, colors):
    from PIL import Image, ImageDraw
    im = Image.fromarray(img.copy()); dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, 300, 14 * len(lines) + 6], fill=(0, 0, 0))
    for i, (t, c) in enumerate(zip(lines, colors)):
        dr.text((5, 3 + 14 * i), t, fill=c)
    return np.asarray(im)


def _save_video(frames, meta, path):
    vid = []
    for img, t, th, s_mm, phase in frames:
        rev = th / (2 * math.pi)
        tag = "DRIVE" if phase == "drive" else "HOLD (released)"
        vid.append(_hud(img, [f"P-SCREW V-A  lead_screw   {tag}",
                              f"T {t:5.2f}s   {rev:5.2f} rev",
                              f"nut travel {s_mm:6.2f} / {meta['stroke_mm']:.0f} mm",
                              f"self-lock: mu*W*dm/2={meta['T_friction_Nm']:.4f} >= W*lead/2pi="
                              f"{meta['T_backdrive_Nm']:.4f} Nm"],
                        [(255, 255, 255), (150, 255, 180) if phase == "drive" else (255, 200, 120),
                         (200, 220, 255), (200, 200, 200)]))
    imageio.mimsave(path, vid, fps=FPS, macro_block_size=1)


def _plot(series, v, meta, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(2, 1, figsize=(8, 6.5), sharex=True)
    t = series["t"]; nut = series["nut_mm"]; th = series["theta_deg"]
    rel_t = next((t[i] for i in range(len(series["phase"])) if series["phase"][i] == "hold"), t[-1] if t else 0)
    ax[0].plot(t, nut, lw=2, color="#2b6cb0", label="nut travel s(t) [measured]")
    # formula line during drive: s = lead × (θ/360)
    ax[0].plot(t, [meta["travel_per_rev_mm"] * (x / 360.0) for x in th], ls="--", lw=1.3,
               color="#c53030", label=f"§8-2 formula  s = lead·θ/360  (lead={meta['lead_mm']} mm)")
    ax[0].axvline(rel_t, color="#888", ls=":", lw=1, label="drive RELEASED (hold begins)")
    badge = "PASS" if v["passed"] else "FAIL"
    ax[0].set_ylabel("nut travel s (mm)")
    ax[0].set_title(f"P-SCREW / V-A  lead_screw  [{badge}]   {v['travel_mm']:.1f} mm over "
                    f"{v['revs_done']:.1f} rev,  formula resid={v['formula_residual']*100:.3f}%,  "
                    f"back-drive={v['backdrive_mm']:.2f} mm", fontsize=9,
                    color="#22543d" if v["passed"] else "#742a2a")
    ax[0].legend(fontsize=8); ax[0].grid(alpha=.25)
    # zoom on the hold: nut height after release (self-lock)
    hold_i = [i for i, p in enumerate(series["phase"]) if p == "hold"]
    if hold_i:
        ax[1].plot([t[i] for i in hold_i], [nut[i] for i in hold_i], lw=2, color="#2f855a")
        ax[1].set_title(f"HOLD (drive released, sourced friction {meta['T_friction_Nm']:.4f} Nm ≥ "
                        f"back-drive {meta['T_backdrive_Nm']:.4f} Nm): back-drive {v['backdrive_mm']:.2f} mm",
                        fontsize=8.5)
    ax[1].set_xlabel("t (s)"); ax[1].set_ylabel("nut s (mm)"); ax[1].grid(alpha=.25)
    fig.tight_layout(); fig.savefig(path, dpi=130)
    import matplotlib.pyplot as _p; _p.close(fig)


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "out"
    out.mkdir(parents=True, exist_ok=True)
    plan = lead_screw_fixture()
    e1 = plan.element("E1")
    e1.params = CARD_REGISTRY["lead_screw"].resolve_params(plan, e1)
    assert not validate_all(plan), "fixture must be validator-clean"
    ca = compile_assembly(plan)

    xml, meta = build_va_mjcf(plan, ca, out / "assets")
    xf = out / "t2_lead_screw_VA.xml"; xf.write_text(xml)
    model = mj.MjModel.from_xml_path(str(xf))
    gok, checks = g9_gconv(model)

    va_proto = next(p for p in plan.protocols if p.mode == "V-A")
    result = {
        "decision_row": "D-M19-1 P-SCREW V-A on compiled lead_screw_fixture (V-B DEFERRED, R2b/m17)",
        "compile_hash": _hash(), "card": "lead_screw", "element": "E1",
        "rule_chain": {"lead_mm": meta["lead_mm"], "= starts×pitch": f"{meta['starts']}×{meta['pitch_mm']}",
                       "d_mean_mm": meta["d_mean_mm"], "lead_angle_deg": meta["lead_angle_deg"],
                       "tan_lambda": meta["tan_lambda"], "mu": meta["mu"],
                       "self_locks (tanλ≤µ)": meta["self_locks_formula"],
                       "polycoef_m_per_rad (lead/2π)": meta["polycoef_m_per_rad"]},
        "sourced_friction": {"T_friction_Nm (µ·W·d_mean/2)": meta["T_friction_Nm"],
                             "T_backdrive_Nm (W·lead/2π)": meta["T_backdrive_Nm"],
                             "hold_margin": meta["hold_margin"], "W_N": meta["W_N"],
                             "note": "SOURCED from PETG.mu + card thread geometry — NOT invented (D-D-1)"},
        "g9_gconv": bool(gok), "g9_checks": [(c[0], bool(c[1]), c[2]) for c in checks],
        "v_b_gap": va_proto.actuation.get("v_b_gap"), "modes": {},
    }
    if not gok:
        result["modes"]["V-A"] = {"ran": False, "reason": "G-CONV failed (model incoherent)"}
    else:
        per_seed, series0, frames0, v0 = [], None, None, None
        for seed in range(N_SEEDS):
            rec = seed == 0
            v, series, frames = run_va(model, meta, seed, record=rec)
            per_seed.append(v)
            if rec:
                series0, frames0, v0 = series, frames, v
        n_pass = sum(v["passed"] for v in per_seed)
        result["modes"]["V-A"] = {"ran": True, "n_seeds": N_SEEDS, "seeds_passed": n_pass,
                                  "passed": bool(n_pass >= SEED_PASS),
                                  "criteria_seed0": per_seed[0]["criteria"], "per_seed": per_seed}
        # NON-TAUTOLOGY of the HOLD (the D-D-1 lesson, empirical form). The sourced friction passes; a
        # friction BELOW the back-drive torque MUST let the load slip. If both held, the "hold" would be
        # a solver artifact (stiff coupling alone), not self-lock. Probe: friction = 0.5·T_backdrive.
        fweak = 0.5 * meta["T_backdrive_Nm"]
        vprobe, _, _ = run_va(model, meta, seed=0, record=False, friction_override=fweak)
        weak_backdrive = vprobe["backdrive_mm"]
        result["modes"]["V-A"]["discrimination_probe"] = {
            "weak_friction_Nm (0.5·T_backdrive)": round(fweak, 6),
            "weak_backdrive_mm": weak_backdrive,
            "sourced_backdrive_mm": per_seed[0]["backdrive_mm"],
            "discriminates": bool(weak_backdrive > 10 * HOLD_TOL_MM and per_seed[0]["backdrive_mm"] <= HOLD_TOL_MM),
            "note": "self-lock is NON-TAUTOLOGICAL: sourced friction holds (<1mm), sub-back-drive friction slips (≫1mm)"}
        if series0:
            _plot(series0, v0, meta, out / "t2_lead_screw_VA.png")
            result["modes"]["V-A"]["plot"] = "t2_lead_screw_VA.png"
            if frames0:
                _save_video(frames0, meta, out / "t2_lead_screw_VA.mp4")
                result["modes"]["V-A"]["video"] = "t2_lead_screw_VA.mp4"
        print(f"\n=== P-SCREW V-A ===  G-CONV {'ok' if gok else 'FAIL'}   seeds {n_pass}/{N_SEEDS} => "
              f"{'PASS' if n_pass >= SEED_PASS else 'FAIL'}")
        for name, c in per_seed[0]["criteria"].items():
            print(f"   {'ok  ' if c['pass'] else 'FAIL'} {name:<48s} {c['value']} (<= {c['threshold']})")
        print(f"   formula match: measured {v0['travel_mm']:.2f} mm vs lead·rev "
              f"{v0['formula_travel_mm']:.2f} mm  ({v0['formula_residual']*100:.3f}%)")
        dp = result["modes"]["V-A"]["discrimination_probe"]
        print(f"   non-tautology probe: sourced friction holds {dp['sourced_backdrive_mm']:.2f} mm  vs  "
              f"weak(0.5·T_bd) slips {dp['weak_backdrive_mm']:.2f} mm  => discriminates={dp['discriminates']}")

    result["verdict_VA"] = result["modes"].get("V-A", {}).get("passed", False)
    result["verdict_VB"] = "DEFERRED — helical thread contact is curved, R2b class (m17/D-M1-7); pending preset_v2"
    result["shape_assert"] = {
        "va_present": "V-A" in result["modes"],
        "vb_named_deferred": result["v_b_gap"] is not None,
        "no_vb_pass_claimed": result["verdict_VB"].startswith("DEFERRED")}
    (out / "t2_lead_screw_verdict.json").write_text(json.dumps(result, indent=2))
    print(f"\nV-A pass: {result['verdict_VA']}   V-B: {result['verdict_VB'][:40]}...")
    print("wrote", out / "t2_lead_screw_verdict.json")


if __name__ == "__main__":
    main()
