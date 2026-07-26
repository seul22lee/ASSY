"""P-COUPLING (MECHSYNTH §6.3) on the compiled coupling_fixture — V-A (m20 D-track).

WHY V-A, and the DESIGN QUESTION of m20. A rigid coupling transmits rotation 1:1 between two coaxial
shafts. Declaring 1:1 and measuring 1:1 verifies NOTHING (unlike m19, where polycoef came from the
card's lead formula and the ratio exercised real arithmetic). The non-tautological content of a rigid
coupling is TORQUE TRANSMISSION UNDER LOAD, so P-COUPLING has three parts:

  (a) RATIO — drive the input N revs; the output tracks to ≤0.1%. NECESSARY but weak alone (a 1:1
      equality trivially reproduces 1:1); we say so.
  (b) LOAD TRANSMISSION — a resisting torque on the OUTPUT, SOURCED from the card's rated-torque
      formula (T_load = load_fraction · T_rated, T_rated = τ·π·bore³/16; NOT invented). The input must
      transmit it: the output still tracks AND the input actuator torque matches the applied resistance
      to TORQUE_TOL. That number path exercises the card's torque rating and the N·mm→N·m unit path.
  (c) DISCRIMINATION (inherited from m19/D-M19-2) — break the coupling honestly (equality INACTIVE):
      the input spins but the output must NOT track. Recorded as discrimination_probe in the verdict.

CLOCK: contact-free declared-joint rig ⇒ dt=1e-4 (D-M19-2), NOT the frozen R5 contact preset (which
is a contact preset and does not apply — this rig declares no contact geoms). No gravity (pure rotation
about the shaft axis; a coupling's function is orientation-independent).

V-B: a rigid coupling is concentric CLAMPED solids — no curved conjugate contact, so there is NO
m17/R2b-class emergent-contact gap to defer. V-A fully covers the declared behaviour; emergent_check
is VERIFIED (properly reversing the D-M19-0 no-rig retag). The only untested thing is the hub↔shaft
FORCE-closure grip (clamp/set-screw slip) — a fastening-preload question, not a curved-contact V-B;
named in the verdict as a modeling assumption, not a deferred pass.

  export MUJOCO_GL=egl ; ./bin/py m20_coupling/p_coupling_va.py [out_dir]
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

from build123d import Align, Cylinder, Location, Pos  # noqa: E402
from knowledge.cards.base import CARD_REGISTRY  # noqa: E402
from knowledge.cards.coupling import coupling_dims, coupling_mechanics  # noqa: E402
from ontology.validators import validate_all  # noqa: E402
from pipeline.compile_assembly import compile_assembly  # noqa: E402
from tasks.build_goldens import coupling_fixture  # noqa: E402
from verify.t2_physics.mjcf import _inertial, _to_trimesh  # noqa: E402
from verify.t2_physics.runner import _hash, g9_gconv  # noqa: E402

from step2mjcf import MM, SOLIMP, SOLREF  # FROZEN preset (R5, contact only)  # noqa: E402

VA_DT = 1e-4          # D-M19-2 clock: contact-free joint rig; R5 (contact preset) does not apply here
ARMATURE = 1e-5       # driven-train rotor inertia (numerical rigidity, D-M19-2 recipe)
JOINT_DAMPING = 1e-5  # tiny — must not mask the transmission
CAPTURE_HZ = 240      # frame CAPTURE cadence (Hz of sim time) — dense so the 6-rev sweep is smooth
OUT_FPS = 60          # video OUTPUT fps ⇒ 240/60 = 4× slow-motion (legible marker sweep; HUD keeps it honest)
N_SEEDS, SEED_PASS = 5, 4
OMEGA = 40.0          # rad/s input drive (kinematic pair, fast is fine; keeps step count low at dt=1e-4)
RAMP = 0.15
KV = 1.0              # velocity-actuator gain (steady actuator torque = the reflected output load)
N_REV = 6.0           # revolutions to drive (a clean ratio + a steady torque window)
LOAD_FRACTION = 0.5   # design load = 0.5 · rated torque (SOURCED, within capacity — not invented)
RATIO_TOL = 0.001     # ≤0.1% output-vs-input tracking (the ratio gate)
TORQUE_TOL = 0.05     # ≤5% transmitted-vs-applied torque match (the load-transmission gate)


def _v(a):
    return " ".join(f"{float(x):.9f}" for x in a)


def build_va_mjcf(plan, ca, meshdir: Path, markers=True):
    """base(weld) + input(hinge +Z: shaft ⊕ hub, fused) + output(hinge +Z: shaft), coupled by an
    equality polycoef = 1.0 (the declared 1:1 pair). The input actuator drives; a resisting torque on
    the output is applied at run time (sourced from T_rated). markers=True adds visual-only rotation
    tabs (zero mass, no contact — physics identical, asserted)."""
    meshdir.mkdir(parents=True, exist_ok=True)
    e1 = plan.element("E1")
    g = coupling_dims(e1.params)
    mech = coupling_mechanics(g)

    # geometry positions (mirror the templates + carve): base_t=4, input stub top shaft_h, hub fused
    p1 = plan.piece("P1"); p2 = plan.piece("P2")
    base_t = float(p1.params.get("base_t", 4.0))
    shaft_h = float(p1.params.get("shaft_h", 30.0))
    base_l = float(p1.params.get("base_l", 50.0)); base_w = float(p1.params.get("base_w", 50.0))
    out_z0 = float(p2.params.get("z0", 40.0)); out_len = float(p2.params.get("shaft_len", 24.0))
    clr = float(p2.params.get("clearance", 0.30))
    overlap, floor = 4.0, 10.0
    hub_bottom = shaft_h - overlap
    bore_depth = max(6.0, g.length - floor)

    # solids (metres): base plate; input = stub ∪ hub(−blind bore); output = undersized shaft
    base_solid = Location(Pos(0, 0, 0)) * (
        __import__("build123d").Box(base_l, base_w, base_t, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    in_stub = Location(Pos(0, 0, base_t - 0.5)) * Cylinder(g.bore_d / 2, shaft_h - base_t + 0.5,
                                                           align=(Align.CENTER, Align.CENTER, Align.MIN))
    hub = Location(Pos(0, 0, hub_bottom)) * Cylinder(g.body_d / 2, g.length,
                                                     align=(Align.CENTER, Align.CENTER, Align.MIN))
    bore = Location(Pos(0, 0, hub_bottom + g.length - bore_depth)) * Cylinder(
        g.bore_d / 2, bore_depth + 1.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    input_solid = in_stub + (hub - bore)
    output_solid = Location(Pos(0, 0, out_z0)) * Cylinder(g.bore_d / 2 - clr, out_len,
                                                          align=(Align.CENTER, Align.CENTER, Align.MIN))

    ax_dir = np.array([0.0, 0.0, 1.0])
    ax_pt = np.array([0.0, 0.0, 0.0])

    # SOURCED load: rated torque then a design fraction (N·mm → N·m)
    T_rated_Nmm = mech["torque_capacity_Nmm"]
    T_rated_Nm = T_rated_Nmm * 1e-3
    T_load_Nm = LOAD_FRACTION * T_rated_Nm

    root = ET.Element("mujoco", model="t2_coupling_VA")
    ET.SubElement(root, "compiler", angle="radian", meshdir=meshdir.name, autolimits="true")
    ET.SubElement(root, "option", timestep=f"{VA_DT}", integrator="implicitfast",
                  cone="elliptic", impratio="10", gravity="0 0 0")   # no gravity (pure rotation)
    vis = ET.SubElement(root, "visual")
    ET.SubElement(vis, "headlight", ambient="0.5 0.5 0.5", diffuse="0.6 0.6 0.6", specular="0.2 0.2 0.2")
    ET.SubElement(vis, "global", offwidth="1280", offheight="960", azimuth="130", elevation="-20")
    dflt = ET.SubElement(root, "default")
    ET.SubElement(dflt, "geom", solref=f"{SOLREF[0]} {SOLREF[1]}",
                  solimp=f"{SOLIMP[0]} {SOLIMP[1]} {SOLIMP[2]}", density="0",
                  contype="0", conaffinity="0", group="2")    # NO contact — joints are the mechanism
    asset = ET.SubElement(root, "asset")
    ET.SubElement(asset, "material", name="base", rgba="0.35 0.65 0.85 1")
    ET.SubElement(asset, "material", name="input", rgba="0.95 0.62 0.25 1")
    ET.SubElement(asset, "material", name="output", rgba="0.55 0.78 0.55 1")
    ET.SubElement(asset, "material", name="mk_in", rgba="0.90 0.10 0.10 1")   # input marker (red)
    ET.SubElement(asset, "material", name="mk_hub", rgba="0.10 0.85 0.90 1")  # hub marker (cyan)
    ET.SubElement(asset, "material", name="mk_out", rgba="0.85 0.10 0.80 1")  # output marker (magenta)
    world = ET.SubElement(root, "worldbody")
    ET.SubElement(world, "light", pos="0.1 -0.15 0.4", dir="-0.2 0.3 -1", directional="true",
                  diffuse="0.5 0.5 0.5")
    ET.SubElement(world, "camera", name="iso", pos="0.10 -0.13 0.11",
                  xyaxes="0.79 0.61 0 -0.20 0.26 0.94")
    # SIDE camera (perpendicular to the +Z shaft axis) — the marker sweep is only legible side-on;
    # a near-axial view hides rotation even WITH markers (the m10/m19 lesson).
    ET.SubElement(world, "camera", name="side", pos="0 -0.16 0.032", xyaxes="1 0 0 0 0 1")

    # VISUAL-ONLY rotation markers (zero mass via default density=0, contype/conaffinity=0 → NO physics
    # effect; asserted identical below). Thin radial tabs so a rotationally-symmetric cylinder shows its
    # spin. One+ asymmetric feature per MOVING body (the standing V-A-video rule): input shaft + hub on
    # the input body; a tab on the output shaft. Positions/sizes in mm → metres.
    def _mk(mm):
        return tuple(x * MM for x in mm)
    MARKERS = {
        "input": [("mk_in", _mk((g.bore_d / 2 + 2.0, 0, 15.0)), _mk((3.0, 1.0, 4.0))),
                  ("mk_hub", _mk((g.body_d / 2 + 2.0, 0, 38.0)), _mk((4.0, 1.2, 6.0)))],
        "output": [("mk_out", _mk((g.bore_d / 2 - clr + 1.8, 0, 57.0)), _mk((3.0, 1.0, 4.0)))],
    }

    masses = {}
    specs = [("base", base_solid, "base", None),
             ("input", input_solid, "input", ("hinge", ax_dir)),
             ("output", output_solid, "output", ("hinge", ax_dir))]
    for name, solid, mat, joint in specs:
        body = ET.SubElement(world, "body", name=name, pos="0 0 0")
        if joint is not None:
            jkind, jaxis = joint
            jt = ET.SubElement(body, "joint",
                               name="input_hinge" if name == "input" else "output_hinge",
                               type=jkind, axis=_v(jaxis), pos=_v(ax_pt),
                               damping=f"{JOINT_DAMPING}", armature=f"{ARMATURE}")
        vf = meshdir / f"cp_{name}_vis.stl"
        mesh = _to_trimesh(solid, vf)
        masses[name] = _inertial(body, mesh)
        ET.SubElement(asset, "mesh", name=f"{name}_vis", file=vf.name)
        ET.SubElement(body, "geom", name=f"{name}_vis", type="mesh", mesh=f"{name}_vis", material=mat)
        if markers:
            for mname, mpos, msize in MARKERS.get(name, []):
                ET.SubElement(body, "geom", name=f"{name}_{mname}", type="box",
                              pos=_v(mpos), size=_v(msize), material=mname)   # density=0 default → 0 mass

    # THE DECLARED 1:1 PAIR (V-A): output_hinge(rad) = 1.0 · input_hinge(rad). RIGID coupling (D-M19-2):
    # a direct-stiffness solref so the applied output torque transmits to the input (a soft equality
    # would let the output lag/stretch and under-report transmission).
    eq = ET.SubElement(root, "equality")
    ET.SubElement(eq, "joint", name="couple", joint1="output_hinge", joint2="input_hinge",
                  polycoef="0 1.0 0 0 0", solref="-1e8 -1e4", solimp="0.9999 0.99999 0.000001 0.5 2")
    act = ET.SubElement(root, "actuator")
    ET.SubElement(act, "velocity", name="drive", joint="input_hinge", kv=f"{KV}")

    xml = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
    meta = {"bore_d_mm": g.bore_d, "body_d_mm": g.body_d, "length_mm": g.length,
            "tau_allow_MPa": g.tau_allow, "ratio_expected": mech["ratio"],
            "T_rated_Nmm": T_rated_Nmm, "T_rated_Nm": round(T_rated_Nm, 6),
            "load_fraction": LOAD_FRACTION, "T_load_Nm": round(T_load_Nm, 6),
            "n_rev": N_REV, "masses_kg": masses, "axis_m": {"point": list(ax_pt), "dir": list(ax_dir)}}
    return xml, meta


def run_va(model, meta, seed=0, record=False, break_coupling=False):
    """Drive the input N_REV; a resisting torque loads the output; measure ratio + transmitted torque.
    break_coupling=True DEACTIVATES the equality (the discrimination probe) — the output must not track.
    Returns (verdict, series, frames)."""
    rng = np.random.default_rng(seed)
    ji = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "input_hinge")
    jo = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "output_hinge")
    iia, ioa = model.jnt_qposadr[ji], model.jnt_qposadr[jo]
    idi, ido = model.jnt_dofadr[ji], model.jnt_dofadr[jo]
    a = mj.mj_name2id(model, mj.mjtObj.mjOBJ_ACTUATOR, "drive")
    eqid = mj.mj_name2id(model, mj.mjtObj.mjOBJ_EQUALITY, "couple")
    cam = mj.mj_name2id(model, mj.mjtObj.mjOBJ_CAMERA, "side")   # side-on: the marker sweep is legible

    eq_active0 = model.eq_active0.copy()
    if break_coupling:
        model.eq_active0[eqid] = 0                              # discrimination: coupling OFF
    d = mj.MjData(model)                                        # created AFTER, so it inherits eq_active0
    if break_coupling:
        d.eq_active[eqid] = 0                                   # belt-and-suspenders (runtime field)

    T_load = meta["T_load_Nm"]
    d.qpos[iia] += rng.uniform(-1e-3, 1e-3)                     # seed perturbs the start angle
    d.qpos[ioa] = d.qpos[iia]                                   # keep the 1:1 coupling satisfied at t=0
    mj.mj_forward(model, d)
    renderer = mj.Renderer(model, 480, 640) if record else None

    theta_target = meta["n_rev"] * 2 * math.pi
    thi0, tho0 = float(d.qpos[iia]), float(d.qpos[ioa])
    ts, thi, tho, torque, frames, nextf = [], [], [], [], [], 0.0
    diverged = False
    load_on = 0.0
    t_wall = theta_target / OMEGA + 6 * RAMP + 2.0

    while True:
        d.ctrl[0] = min(OMEGA, OMEGA * d.time / RAMP)
        # resisting torque on the OUTPUT (a brake), ramped in after the input is up to speed. Applied
        # only when coupled (the discrimination run drives a FREE output — output must simply not track).
        if not break_coupling:
            load_on = min(1.0, max(0.0, (d.time - 2 * RAMP) / RAMP))
            d.qfrc_applied[ido] = -T_load * load_on             # opposes the +ω output rotation
        mj.mj_step(model, d)
        if not np.all(np.isfinite(d.qpos)) or abs(d.qvel[idi]) > 2000:
            diverged = True; break
        ai = float(d.qpos[iia]) - thi0
        ao = float(d.qpos[ioa]) - tho0
        ts.append(d.time); thi.append(ai); tho.append(ao)
        torque.append(float(d.actuator_force[a]))               # input actuator torque = reflected load
        if record and d.time >= nextf:
            renderer.update_scene(d, camera=cam)
            frames.append((renderer.render(), d.time, ai, ao, load_on))
            nextf += 1.0 / CAPTURE_HZ
        if ai >= theta_target or d.time > t_wall:
            break
    if renderer:
        renderer.close()
    model.eq_active0[:] = eq_active0                             # restore for the next run

    ai_f = thi[-1] if thi else 0.0
    ao_f = tho[-1] if tho else 0.0
    revs_in = ai_f / (2 * math.pi)
    revs_out = ao_f / (2 * math.pi)
    ratio = (ao_f / ai_f) if abs(ai_f) > 1e-9 else 0.0
    ratio_residual = abs(ratio - meta["ratio_expected"]) if not break_coupling else abs(ratio - meta["ratio_expected"])
    reaches = ai_f >= theta_target - 0.05
    # transmitted torque = mean |input actuator torque| over the steady (loaded) window = last 35%
    n = len(torque)
    win = torque[int(0.65 * n):] if n > 5 else torque
    T_meas = float(np.mean(np.abs(win))) if win else 0.0
    torque_residual = abs(T_meas / T_load - 1.0) if T_load > 0 else 1.0
    all_retained = bool(np.all(np.isfinite(d.qpos)))

    crit = {
        "reaches_drive (input ≥ N_rev)": {"value": round(revs_in, 3), "threshold": meta["n_rev"],
                                          "pass": bool(reaches and not diverged)},
        "transmits_ratio (|out/in−1| ≤ 0.1%)": {"value": round(ratio_residual, 6), "threshold": RATIO_TOL,
                                                "pass": bool(ratio_residual <= RATIO_TOL and not diverged)},
        "transmits_rated_torque (|T_in/T_load−1| ≤ 5%)": {"value": round(torque_residual, 4),
                                                          "threshold": TORQUE_TOL,
                                                          "pass": bool(torque_residual <= TORQUE_TOL and not diverged)},
        "converged (no blow-up)": {"value": diverged, "threshold": False, "pass": bool(not diverged)},
        "all_parts_retained": {"value": all_retained, "threshold": True, "pass": all_retained},
    }
    v = {"ran": True, "mode": "V-A", "seed": seed, "diverged": diverged, "broke_coupling": break_coupling,
         "revs_in": round(revs_in, 3), "revs_out": round(revs_out, 3), "ratio": round(ratio, 5),
         "ratio_residual": round(ratio_residual, 6), "T_meas_Nm": round(T_meas, 5),
         "torque_residual": round(torque_residual, 4), "criteria": crit,
         "passed": bool(all(c["pass"] for c in crit.values()))}
    series = {"t": ts, "in_deg": [math.degrees(x) for x in thi], "out_deg": [math.degrees(x) for x in tho],
              "torque": torque}
    return v, series, frames


def _hud(img, lines, colors):
    from PIL import Image, ImageDraw
    im = Image.fromarray(img.copy()); dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, 470, 14 * len(lines) + 6], fill=(0, 0, 0))
    for i, (t, c) in enumerate(zip(lines, colors)):
        dr.text((5, 3 + 14 * i), t, fill=c)
    return np.asarray(im)


def _save_video(frames, meta, path, broken=False):
    tag = "COUPLING BROKEN (equality inactive)" if broken else "coupling INTACT   1:1 rigid"
    slow = f"{CAPTURE_HZ // OUT_FPS}x slow-mo"
    vid = []
    for img, t, ai, ao, load in frames:
        ratio = (ao / ai) if abs(ai) > 1e-6 else 0.0
        vid.append(_hud(img, [f"P-COUPLING V-A  {tag}   [{slow}]",
                              f"T {t:5.2f}s   in(red/cyan) {ai/(2*math.pi):5.2f} rev   "
                              f"out(magenta) {ao/(2*math.pi):5.2f} rev",
                              (f"load {load*meta['T_load_Nm']:.3f} / {meta['T_load_Nm']:.3f} Nm (0.5*T_rated)"
                               if not broken else "no load — showing the output does NOT track"),
                              f"ratio out/in = {ratio:.4f}"
                              + ("   <-- output DEAD STILL" if broken else "")],
                        [(255, 255, 255), (150, 220, 255), (255, 200, 120),
                         (255, 150, 150) if broken else (200, 255, 200)]))
    imageio.mimsave(path, vid, fps=OUT_FPS, macro_block_size=1)


def _plot(series, v, meta, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(2, 1, figsize=(8, 6.5), sharex=True)
    t = series["t"]
    ax[0].plot(t, series["in_deg"], lw=2, color="#c05621", label="input angle [driven]")
    ax[0].plot(t, series["out_deg"], lw=1.4, ls="--", color="#2f855a", label="output angle [tracks 1:1]")
    badge = "PASS" if v["passed"] else "FAIL"
    ax[0].set_ylabel("shaft angle (deg)")
    ax[0].set_title(f"P-COUPLING / V-A  coupling  [{badge}]   ratio out/in={v['ratio']:.4f} "
                    f"(resid {v['ratio_residual']*100:.3f}%),  T_transmitted={v['T_meas_Nm']:.3f} Nm "
                    f"(resid {v['torque_residual']*100:.2f}%)", fontsize=8.5,
                    color="#22543d" if v["passed"] else "#742a2a")
    ax[0].legend(fontsize=8); ax[0].grid(alpha=.25)
    ax[1].plot(t, series["torque"], lw=1.6, color="#6b46c1", label="input actuator torque (Nm)")
    ax[1].axhline(meta["T_load_Nm"], color="#888", ls=":", lw=1.2,
                  label=f"applied output load 0.5·T_rated = {meta['T_load_Nm']:.3f} Nm")
    ax[1].set_xlabel("t (s)"); ax[1].set_ylabel("torque (Nm)")
    ax[1].set_title("LOAD TRANSMISSION: input torque rises to carry the output's resisting load "
                    "(a broken coupling → ~0)", fontsize=8.5)
    ax[1].legend(fontsize=8); ax[1].grid(alpha=.25)
    fig.tight_layout(); fig.savefig(path, dpi=130)
    import matplotlib.pyplot as _p; _p.close(fig)


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "out"
    out.mkdir(parents=True, exist_ok=True)
    plan = coupling_fixture()
    e1 = plan.element("E1")
    e1.params = CARD_REGISTRY["coupling"].resolve_params(plan, e1)
    assert not validate_all(plan), "fixture must be validator-clean"
    ca = compile_assembly(plan)

    xml, meta = build_va_mjcf(plan, ca, out / "assets")
    xf = out / "t2_coupling_VA.xml"; xf.write_text(xml)
    model = mj.MjModel.from_xml_path(str(xf))
    gok, checks = g9_gconv(model)

    result = {
        "decision_row": "D-M20-1 P-COUPLING V-A on compiled coupling_fixture (V-B VERIFIED — no curved contact)",
        "compile_hash": _hash(), "card": "coupling", "element": "E1",
        "rule_chain": {"ratio": meta["ratio_expected"], "bore_d_mm": meta["bore_d_mm"],
                       "body_d_mm": meta["body_d_mm"], "length_mm": meta["length_mm"],
                       "tau_allow_MPa": meta["tau_allow_MPa"], "T_rated_Nmm (τ·π·d³/16)": meta["T_rated_Nmm"]},
        "sourced_load": {"T_rated_Nm": meta["T_rated_Nm"], "load_fraction": meta["load_fraction"],
                         "T_load_Nm (0.5·T_rated)": meta["T_load_Nm"],
                         "note": "resisting torque SOURCED from the card's rated torque — NOT invented (D-D-1)"},
        "g9_gconv": bool(gok), "g9_checks": [(c[0], bool(c[1]), c[2]) for c in checks], "modes": {},
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
        # MARKERS ARE PHYSICS-IDENTICAL: visual-only tabs (zero mass, no contact). Prove it — seed0's
        # triple (revs / ratio residual / torque residual) on a NO-marker model must match exactly.
        xml_nm, _ = build_va_mjcf(plan, ca, out / "assets", markers=False)
        (out / "_nomark.xml").write_text(xml_nm)
        v_nm, _, _ = run_va(mj.MjModel.from_xml_path(str(out / "_nomark.xml")), meta, seed=0, record=False)
        triple_mk = [per_seed[0]["revs_in"], per_seed[0]["ratio_residual"], per_seed[0]["torque_residual"]]
        triple_nm = [v_nm["revs_in"], v_nm["ratio_residual"], v_nm["torque_residual"]]
        assert triple_mk == triple_nm, f"markers CHANGED physics: {triple_mk} != {triple_nm}"
        (out / "_nomark.xml").unlink(missing_ok=True)
        result["modes"]["V-A"]["markers_physics_identical"] = {
            "with_markers (revs,ratio_resid,torque_resid)": triple_mk,
            "no_markers": triple_nm, "identical": True}

        # DISCRIMINATION (inherited, D-M19-2): break the coupling — the output must NOT track the input.
        # Recorded as its own clip (broken-vs-intact is the most legible evidence this element produces).
        vbreak, _, frames_break = run_va(model, meta, seed=0, record=True, break_coupling=True)
        intact_ratio_resid = per_seed[0]["ratio_residual"]
        result["modes"]["V-A"]["discrimination_probe"] = {
            "intact_ratio_residual": intact_ratio_resid,
            "intact_out_rev": per_seed[0]["revs_out"],
            "broken_out_rev": vbreak["revs_out"],
            "broken_in_rev": vbreak["revs_in"],
            "discriminates": bool(intact_ratio_resid <= RATIO_TOL and abs(vbreak["revs_out"]) < 0.1
                                  and vbreak["revs_in"] > 1.0),
            "note": "coupling INTACT: output tracks input 1:1; coupling BROKEN (equality inactive): input "
                    "spins, output stays put — the tracking is the coupling, not a solver artifact"}
        if frames_break:
            _save_video(frames_break, meta, out / "t2_coupling_VA_broken.mp4", broken=True)
            result["modes"]["V-A"]["discrimination_video"] = "t2_coupling_VA_broken.mp4"
        if series0:
            _plot(series0, v0, meta, out / "t2_coupling_VA.png")
            result["modes"]["V-A"]["plot"] = "t2_coupling_VA.png"
            if frames0:
                _save_video(frames0, meta, out / "t2_coupling_VA.mp4")
                result["modes"]["V-A"]["video"] = "t2_coupling_VA.mp4"
        print(f"\n=== P-COUPLING V-A ===  G-CONV {'ok' if gok else 'FAIL'}   seeds {n_pass}/{N_SEEDS} => "
              f"{'PASS' if n_pass >= SEED_PASS else 'FAIL'}")
        for name, c in per_seed[0]["criteria"].items():
            print(f"   {'ok  ' if c['pass'] else 'FAIL'} {name:<48s} {c['value']} (<= {c['threshold']})")
        dp = result["modes"]["V-A"]["discrimination_probe"]
        print(f"   ratio: out/in={v0['ratio']:.4f} resid {v0['ratio_residual']*100:.3f}%  |  "
              f"torque transmitted {v0['T_meas_Nm']:.3f} Nm vs applied {meta['T_load_Nm']:.3f} "
              f"({v0['torque_residual']*100:.2f}%)")
        print(f"   discrimination: intact out {dp['intact_out_rev']:.2f} rev  vs  BROKEN out "
              f"{dp['broken_out_rev']:.2f} rev (in {dp['broken_in_rev']:.2f}) => discriminates={dp['discriminates']}")
        mi = result["modes"]["V-A"]["markers_physics_identical"]
        print(f"   markers physics-identical: with {mi['with_markers (revs,ratio_resid,torque_resid)']} "
              f"== without {mi['no_markers']}  ({mi['identical']})")

    result["verdict_VA"] = result["modes"].get("V-A", {}).get("passed", False)
    result["verdict_VB"] = ("VERIFIED — a rigid coupling is concentric clamped solids with NO curved "
                            "conjugate contact, so there is no m17/R2b emergent-contact gap; V-A covers "
                            "the declared 1:1 + torque transmission (reverses the D-M19-0 no-rig retag)")
    result["emergent_check_resolution"] = {
        "status": "verified",
        "why": "no curved-contact V-B of the m17 class exists for a concentric rigid hub",
        "named_assumption": "the hub↔shaft FORCE-closure grip (clamp/set-screw slip vs applied torque) "
                            "is idealized as rigid; that is a fastening-preload question, NOT a deferred "
                            "curved-contact V-B — a future clamp-torque check, not an R2b defer"}
    (out / "t2_coupling_verdict.json").write_text(json.dumps(result, indent=2))
    print(f"\nV-A pass: {result['verdict_VA']}   V-B: VERIFIED (no curved contact)")
    print("wrote", out / "t2_coupling_verdict.json")


if __name__ == "__main__":
    main()
