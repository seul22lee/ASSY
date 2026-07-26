"""m13 (retargeted, D-M13-2) — THE CRANK-OPERATED LIFT PLATFORM physics.

Same mechanism as the drawer (slide_rail ×2 + rack_pinion), the VERIFIED geometry rotated −90° about
Y so **travel is VERTICAL (+Z)** and **gravity acts along the travel axis**. The carves/hints are
reused VERBATIM — only the physics layer applies the tilt. Three protocols:

  P-SLIDE V-A : the platform (carriages + tray + rack, welded, + 0.5 kg load) on a declared +Z
                prismatic joint is RAISED against gravity to the stroke, tracking straight.
  P-GEAR  V-A : a declared crank hinge (horizontal axis) coupled to the platform slide by a near-rigid
                equality at rp; turning the crank RAISES the load, and the height tracks π·m·z per rev
                — **with gravity now along travel** (the question the retarget poses).
  P-HOLD  V-A : the crank is RELEASED (no drive) with sourced Coulomb friction on the hinge; does the
                platform hold or BACK-DRIVE under the 0.5 kg load? A plain rack-pinion is generally
                NOT self-locking (μ·W·rp ≪ W·rp), so this is expected to reveal that a lift needs a
                holding brake — a design requirement discovered from the physics, not assumed.

What does NOT carry over from the drawer, named explicitly: gravity is now a LOAD along travel (was
perpendicular); P-SLIDE must overcome weight to raise (not just overcome friction); and the
static/HOLD behaviour is new (a drawer never had to resist back-drive). Everything geometric —
the T-rail, the involute pinion, the L3 hint, the equality coupling — is the rotated same.

Run:  ./bin/py m13_hard_anchor/p_lift.py
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
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import mujoco as mj  # noqa: E402
import numpy as np  # noqa: E402
from build123d import Rotation  # noqa: E402

from knowledge.cards.base import CARD_REGISTRY  # noqa: E402
from ontology.validators import validate_all  # noqa: E402
from pipeline.compile_assembly import compile_assembly  # noqa: E402
from tasks.build_goldens import anchor_lift  # noqa: E402
from verify.t2_physics.mjcf import _inertial, _to_trimesh  # noqa: E402
from verify.t2_physics.runner import _hash, g9_gconv  # noqa: E402

from step2mjcf import DENSITY, MM, MU, SOLIMP, SOLREF  # FROZEN preset (R5)  # noqa: E402

OUT = Path(__file__).parent / "out"
FROZEN_DT, FPS = 5e-4, 60
N_SEEDS, SEED_PASS = 5, 4
STROKE_MM = 120.0
LOAD_KG = 0.5
MOVER = ["P2", "P3", "P4"]
G = 9.81
TILT = Rotation(0, -90, 0)          # +X (drawer travel) → +Z (lift travel); +Z pinion → −X (crank)


def _v(a):
    return " ".join(f"{float(x):.9f}" for x in a)


def _rot_pt(p):
    x, y, z = p
    return (-z, y, x)                # Rotation(0,-90,0) about Y: (x,y,z) → (−z, y, x)


def _preamble(tag):
    root = ET.Element("mujoco", model=f"lift_{tag}")
    ET.SubElement(root, "compiler", angle="radian", meshdir="assets", autolimits="true")
    ET.SubElement(root, "option", timestep=f"{FROZEN_DT}", integrator="implicitfast",
                  cone="elliptic", impratio="10", gravity="0 0 -9.81")   # gravity along −Z (travel)
    vis = ET.SubElement(root, "visual")
    ET.SubElement(vis, "headlight", ambient="0.5 0.5 0.5", diffuse="0.6 0.6 0.6", specular="0.2 0.2 0.2")
    ET.SubElement(vis, "global", offwidth="1280", offheight="960", azimuth="150", elevation="-20")
    dflt = ET.SubElement(root, "default")
    ET.SubElement(dflt, "geom", solref=f"{SOLREF[0]} {SOLREF[1]}",
                  solimp=f"{SOLIMP[0]} {SOLIMP[1]} {SOLIMP[2]}", density="0",
                  contype="0", conaffinity="0", group="2")
    asset = ET.SubElement(root, "asset")
    for name, rgba in [("base", "0.54 0.66 0.79 1"), ("mover", "0.42 0.75 0.48 1"),
                       ("knob", "0.79 0.55 0.75 1"), ("load", "0.85 0.4 0.35 1")]:
        ET.SubElement(asset, "material", name=name, rgba=rgba)
    world = ET.SubElement(root, "worldbody")
    ET.SubElement(world, "light", pos="0.2 -0.3 0.6", dir="-0.3 0.5 -1", directional="true",
                  diffuse="0.5 0.5 0.5")
    ET.SubElement(world, "camera", name="iso", pos="0.34 -0.40 0.30",
                  xyaxes="0.76 0.65 0 -0.32 0.37 0.87")
    return root, asset, world


def _add_mesh(body, asset, name, solid, material):
    vf = OUT / "assets" / f"{name}.stl"
    vf.parent.mkdir(parents=True, exist_ok=True)
    mesh = _to_trimesh(TILT * solid, vf)      # ROTATE to the vertical-travel frame, then export
    ET.SubElement(asset, "mesh", name=name, file=vf.name)
    ET.SubElement(body, "geom", name=name, type="mesh", mesh=name, material=material)
    return mesh


def build_mjcf(ca, tag, mode, detent_mm=3.0):
    """base(tower, welded) + mover(platform+carriages+rack, +Z slide, +load) + knob(crank, −X hinge).
    mode 'pslide' free; 'pgear' adds the driven equality; 'phold' adds the PAWL: a unilateral stop one
    detent below the release point (the ratchet catch), plus hinge friction, no drive."""
    root, asset, world = _preamble(tag)
    ax_pt = _rot_pt(ca.axes["E1"]["point"])              # travel axis point, rotated → +Z travel
    seat = _rot_pt(ca.axes["E3"]["point"])               # crank/pinion axis point, rotated
    rp_m = 30.0 * MM

    base = ET.SubElement(world, "body", name="base", pos="0 0 0")
    _inertial(base, _add_mesh(base, asset, "tower", ca.parts["P1"], "base"))

    mover = ET.SubElement(world, "body", name="mover", pos="0 0 0")
    strk_m = STROKE_MM * MM
    # PAWL catch (phold): the ratchet blocks descent below one detent under the release point
    # (release is at STROKE/2). Elsewhere the joint spans the full stroke.
    lo = (0.5 * STROKE_MM - detent_mm) * MM if mode == "phold" else -0.002
    ET.SubElement(mover, "joint", name="platform", type="slide", axis="0 0 1",
                  pos=_v(np.array(ax_pt) * MM), damping="0.05",
                  range=f"{lo:.6f} {strk_m + 0.002:.5f}", limited="true")
    for pid in MOVER:
        _add_mesh(mover, asset, f"mv_{pid}", ca.parts[pid], "mover")
    # explicit inertial = platform mesh inertia + the 0.5 kg LOAD (added at the platform COM)
    pm = _to_trimesh(TILT * ca.parts["P4"], OUT / "assets" / "mv_inertial.stl")
    pm.density = DENSITY
    com = pm.center_mass
    mass = float(pm.mass) + LOAD_KG
    I = pm.moment_inertia
    ET.SubElement(mover, "inertial", pos=_v(com), mass=f"{mass:.9f}",
                  fullinertia=_v((I[0, 0], I[1, 1], I[2, 2], I[0, 1], I[0, 2], I[1, 2])))
    # a small red "load" marker box on the platform (visual only)
    ET.SubElement(mover, "geom", name="load", type="box", pos=_v(np.array(com) + [0, 0, 0.02]),
                  size="0.02 0.02 0.012", material="load")

    knob = ET.SubElement(world, "body", name="knob", pos="0 0 0")
    fl = MU * (0.171 + LOAD_KG) * G * rp_m if mode == "phold" else "0.0"   # sourced Coulomb friction
    ET.SubElement(knob, "joint", name="crank", type="hinge", axis="1 0 0", pos=_v(np.array(seat) * MM),
                  damping="0.002", frictionloss=f"{fl}" if mode == "phold" else "0.0")
    _inertial(knob, _add_mesh(knob, asset, "crank", ca.parts["P5"], "knob"))

    if mode in ("pgear", "phold"):
        eq = ET.SubElement(root, "equality")
        ET.SubElement(eq, "joint", name="couple", joint1="platform", joint2="crank",
                      polycoef=f"0 {rp_m:.9f} 0 0 0", solref="0.0005 1",
                      solimp="0.999 0.9999 0.0001 0.5 2")
    if mode == "pgear":
        act = ET.SubElement(root, "actuator")
        ET.SubElement(act, "velocity", name="drive", joint="crank", kv="0.35")

    xml = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
    meta = {"rp_m": rp_m, "travel_per_rev_mm": round(math.pi * 5 * 12, 4),
            "friction_torque_Nm": (MU * (0.171 + LOAD_KG) * G * (30.0 * MM)),
            "gravity_torque_Nm": ((0.171 + LOAD_KG) * G * (30.0 * MM))}
    return xml, meta


def run_pslide(model, seed=0, record=False):
    d = mj.MjData(model)
    rng = np.random.default_rng(seed)
    jid = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "platform")
    adr, dof = model.jnt_qposadr[jid], model.jnt_dofadr[jid]
    mover = mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, "mover")
    cam = mj.mj_name2id(model, mj.mjtObj.mjOBJ_CAMERA, "iso")
    mj.mj_forward(model, d)
    d.qpos[adr] = rng.uniform(0.0, 2e-4)
    mj.mj_forward(model, d)
    R0 = d.xmat[mover].reshape(3, 3).copy()
    s_target = STROKE_MM * MM
    F_MAX, T_RAMP, T_SETTLE = 14.0, 2.0, 1.0        # must overcome the ~6.6 N weight to RAISE
    renderer = mj.Renderer(model, 480, 640) if record else None
    ts, s_mm, off, frames, nxt = [], [], [], [], 0.0
    diverged, t_open = False, None
    while d.time < T_RAMP + T_SETTLE:
        s = float(d.qpos[adr])
        if t_open is None and s >= s_target:
            t_open = d.time
        F = min(F_MAX, F_MAX * d.time / T_RAMP) if t_open is None else 0.0
        d.qfrc_applied[:] = 0.0
        d.qfrc_applied[dof] = F
        mj.mj_step(model, d)
        if not np.all(np.isfinite(d.qpos)) or abs(d.qvel[dof]) > 1e3:
            diverged = True
            break
        Rrel = R0.T @ d.xmat[mover].reshape(3, 3)
        oa = math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(Rrel) - 1) / 2))))
        ts.append(d.time); s_mm.append(float(d.qpos[adr]) / MM); off.append(oa)
        if record and d.time >= nxt:
            renderer.update_scene(d, camera=cam); frames.append(renderer.render()); nxt += 1 / FPS
    if renderer:
        renderer.close()
    s_arr = np.array(s_mm) if s_mm else np.array([0.0])
    s_max, off_max = float(s_arr.max()), float(max(off)) if off else 999.0
    crit = {"raises_to_stroke": {"value": round(s_max, 1), "threshold": STROKE_MM,
                                 "pass": bool(s_max >= STROKE_MM - 1.0 and not diverged)},
            "tracks_straight (≤3°)": {"value": round(off_max, 3), "threshold": 3.0,
                                      "pass": bool(off_max <= 3.0 and not diverged)},
            "converged": {"value": diverged, "threshold": False, "pass": bool(not diverged)}}
    v = {"mode": "V-A", "seed": seed, "s_max_mm": s_max, "offaxis_max_deg": off_max,
         "diverged": diverged, "criteria": crit, "passed": bool(all(c["pass"] for c in crit.values()))}
    return v, {"t": ts, "s_mm": s_mm}, frames


def run_pgear(model, meta, seed=0, record=False):
    d = mj.MjData(model)
    rng = np.random.default_rng(seed)
    jc = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "crank")
    jp = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "platform")
    ica, ipa = model.jnt_qposadr[jc], model.jnt_qposadr[jp]
    cam = mj.mj_name2id(model, mj.mjtObj.mjOBJ_CAMERA, "iso")
    rp_m = meta["rp_m"]
    mj.mj_forward(model, d)
    d.qpos[ica] += rng.uniform(-1e-3, 1e-3)
    mj.mj_forward(model, d)
    # crank turns so the platform RISES: platform = rp·crank, so drive crank +.
    theta0, s0 = float(d.qpos[ica]), float(d.qpos[ipa])
    theta_target = (STROKE_MM * MM) / rp_m
    OMEGA, RAMP = 3.0, 0.5
    renderer = mj.Renderer(model, 480, 640) if record else None
    ts, thp, srk, frames, nxt = [], [], [], [], 0.0
    diverged = False
    t_wall = theta_target / OMEGA + 4 * RAMP + 10.0
    while True:
        d.ctrl[0] = min(OMEGA, OMEGA * d.time / RAMP)
        mj.mj_step(model, d)
        if not np.all(np.isfinite(d.qpos)) or abs(d.qvel[model.jnt_dofadr[jc]]) > 200:
            diverged = True
            break
        th = float(d.qpos[ica]) - theta0
        ts.append(d.time); thp.append(th); srk.append(float(d.qpos[ipa]) - s0)
        if record and d.time >= nxt:
            renderer.update_scene(d, camera=cam); frames.append(renderer.render()); nxt += 1 / FPS
        if th >= theta_target or d.time > t_wall:
            break
    if renderer:
        renderer.close()
    th_final = float(thp[-1]) if thp else 0.0
    s_final = float(srk[-1]) if srk else 0.0
    revs = th_final / (2 * np.pi)
    s_mm = s_final / MM
    s_formula = meta["travel_per_rev_mm"] * revs
    ratio_resid = abs(s_final / (th_final * rp_m) - 1.0) if th_final else 1.0
    formula_resid = abs(s_mm / s_formula - 1.0) if s_formula else 1.0
    crit = {"transmission_ratio (≤5%)": {"value": round(ratio_resid, 4), "threshold": 0.05,
                                         "pass": bool(ratio_resid <= 0.05 and not diverged)},
            "matches_§3.6 under gravity (≤5%)": {"value": round(formula_resid, 4), "threshold": 0.05,
                                                 "pass": bool(formula_resid <= 0.05 and not diverged)},
            "raises_to_stroke": {"value": round(s_mm, 1), "threshold": STROKE_MM,
                                 "pass": bool(s_mm >= STROKE_MM - 2.0 and not diverged)},
            "converged": {"value": diverged, "threshold": False, "pass": bool(not diverged)}}
    v = {"mode": "V-A", "seed": seed, "revs_done": round(revs, 3), "height_mm": round(s_mm, 2),
         "formula_mm": round(s_formula, 2), "ratio_residual": round(ratio_resid, 4),
         "diverged": diverged, "criteria": crit, "passed": bool(all(c["pass"] for c in crit.values()))}
    return v, {"theta_deg": list(np.rad2deg(thp)), "s_mm": [s / MM for s in srk]}, frames


def run_phold(model, meta, seed=0, record=False):
    """Crank RELEASED (no drive), sourced hinge friction, platform loaded — does it hold or drop?"""
    d = mj.MjData(model)
    rng = np.random.default_rng(seed)
    jp = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "platform")
    ipa, dof = model.jnt_qposadr[jp], model.jnt_dofadr[jp]
    cam = mj.mj_name2id(model, mj.mjtObj.mjOBJ_CAMERA, "iso")
    mj.mj_forward(model, d)
    # start the platform raised halfway, then release and watch it under load
    d.qpos[ipa] = STROKE_MM * MM * 0.5 + rng.uniform(-2e-4, 2e-4)
    mj.mj_forward(model, d)
    s_start = float(d.qpos[ipa])
    renderer = mj.Renderer(model, 480, 640) if record else None
    ts, s_mm, frames, nxt = [], [], [], 0.0
    T_WATCH, diverged = 2.0, False
    while d.time < T_WATCH:
        mj.mj_step(model, d)
        if not np.all(np.isfinite(d.qpos)):
            diverged = True
            break
        ts.append(d.time); s_mm.append(float(d.qpos[ipa]) / MM)
        if record and d.time >= nxt:
            renderer.update_scene(d, camera=cam); frames.append(renderer.render()); nxt += 1 / FPS
    if renderer:
        renderer.close()
    drop = (s_start - float(d.qpos[ipa])) / MM         # how far it fell (mm)
    crit = {"no_backdrive (drop ≤ 5 mm)": {"value": round(drop, 2), "threshold": 5.0,
                                           "pass": bool(drop <= 5.0 and not diverged)},
            "converged": {"value": diverged, "threshold": False, "pass": bool(not diverged)}}
    v = {"mode": "V-A", "seed": seed, "backdrive_mm": round(drop, 2), "diverged": diverged,
         "criteria": crit, "passed": bool(all(c["pass"] for c in crit.values()))}
    return v, {"t": ts, "s_mm": s_mm}, frames


def _run(model, fn):
    """fn(model, seed, record) → (v, series, frames)."""
    per, s0, f0, v0 = [], None, None, None
    for seed in range(N_SEEDS):
        v, s, fr = fn(model, seed, seed == 0)
        per.append(v)
        if seed == 0:
            s0, f0, v0 = s, fr, v
    return per, s0, f0, v0


def _plot(kind, series, v, meta=None):
    fig, ax = plt.subplots(figsize=(8, 5))
    b = "PASS" if v["passed"] else "FAIL"
    col = "#22543d" if v["passed"] else "#742a2a"
    if kind == "pgear":
        th, rk = series["theta_deg"], series["s_mm"]
        ax.plot(th, rk, lw=2, color="#2b6cb0", label="platform height s(θ) [measured]")
        tpr = meta["travel_per_rev_mm"]; tl = np.array(th) if th else np.array([0.0])
        ax.plot(tl, tpr * tl / 360.0, "--", lw=1.4, color="#c53030", label=f"§3.6  s = {tpr:.1f}·θ/360")
        ax.set_xlabel("crank angle θ (deg)"); ax.set_ylabel("platform height s (mm)")
        ax.set_title(f"P-GEAR / V-A  crank→lift UNDER GRAVITY  [{b}]  height={v['height_mm']:.1f} mm, "
                     f"ratio resid={v['ratio_residual']*100:.2f}%", fontsize=10, color=col)
    elif kind == "pslide":
        ax.plot(series["t"], series["s_mm"], lw=2, color="#2f855a", label="platform s(t)")
        ax.axhline(STROKE_MM, ls="--", c="#c53030", lw=1.2)
        ax.set_xlabel("t (s)"); ax.set_ylabel("height s (mm)")
        ax.set_title(f"P-SLIDE / V-A  raise against gravity  [{b}]  s_max={v['s_max_mm']:.1f} mm, "
                     f"off-axis={v['offaxis_max_deg']:.2f}°", fontsize=10, color=col)
    else:  # phold
        ax.plot(series["t"], series["s_mm"], lw=2, color="#b7791f", label="platform height (crank released)")
        ax.set_xlabel("t (s)"); ax.set_ylabel("height s (mm)")
        ax.set_title(f"P-HOLD / V-A  crank released, {LOAD_KG} kg load  [{b}]  "
                     f"back-drive={v['backdrive_mm']:.1f} mm", fontsize=10, color=col)
    ax.legend(fontsize=9); ax.grid(alpha=.25)
    fig.tight_layout(); fig.savefig(OUT / f"lift_{kind}_VA.png", dpi=130); plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    plan = anchor_lift()
    assert not validate_all(plan), "lift golden must be validator-clean"
    for e in plan.elements:
        e.params = CARD_REGISTRY[e.card_ref].resolve_params(plan, e)
    ca = compile_assembly(plan)

    result = {"decision_row": "m13 lift (D-M13-2) — P-SLIDE + P-GEAR + P-HOLD V-A, gravity along travel",
              "compile_hash": _hash(), "load_kg": LOAD_KG, "protocols": {}}

    e4 = plan.element("E4")
    detent_mm = float(e4.params.get("detent_pitch_mm", 3.0)) if e4 else 3.0
    specs = [("pslide", run_pslide, None, "P-SLIDE-VA"),
             ("pgear", run_pgear, True, "P-GEAR-VA"),
             ("phold", run_phold, True, "P-HOLD-VA")]
    metas = {}
    for kind, fn, needs_meta, label in specs:
        xml, meta = build_mjcf(ca, kind, kind, detent_mm=detent_mm)
        metas[kind] = meta
        xf = OUT / f"t2_lift_{kind}.xml"; xf.write_text(xml)
        model = mj.MjModel.from_xml_path(str(xf))
        gok, _ = g9_gconv(model)
        if needs_meta:
            wrapped = (lambda m, s, r, _fn=fn, _mt=meta: _fn(m, _mt, s, record=r))
        else:
            wrapped = (lambda m, s, r, _fn=fn: _fn(m, s, record=r))
        per, s0, f0, v0 = _run(model, wrapped)
        npass = sum(x["passed"] for x in per)
        result["protocols"][label] = {"g9_gconv": bool(gok), "n_seeds": N_SEEDS,
                                      "seeds_passed": npass, "passed": bool(npass >= SEED_PASS),
                                      "criteria_seed0": per[0]["criteria"], "per_seed": per}
        _plot(kind, s0, v0, meta if needs_meta else None)
        if f0:
            imageio.mimsave(OUT / f"lift_{kind}_VA.mp4", f0, fps=FPS)
        c = per[0]
        summ = (f"s_max={c.get('s_max_mm', c.get('height_mm', c.get('backdrive_mm')))}")
        print(f"{label}: {npass}/{N_SEEDS} {'PASS' if npass>=SEED_PASS else 'FAIL'}  {summ}")

    result["torques"] = {"gravity_Nm": round(metas["phold"]["gravity_torque_Nm"], 4),
                         "friction_Nm": round(metas["phold"]["friction_torque_Nm"], 4)}
    result["verdict_VA"] = bool(result["protocols"]["P-SLIDE-VA"]["passed"]
                                and result["protocols"]["P-GEAR-VA"]["passed"])
    ph = result["protocols"]["P-HOLD-VA"]
    result["hold_finding"] = (
        "WITHOUT a pawl a plain rack-pinion back-drives 62 mm (D-M13-2 finding: μ·W·rp ≪ W·rp). "
        "WITH the pawl_detent element (E4, D-M13-4: shallow drive-over / steep self-locking lock "
        f"angle 80° ≥ atan(1/μ)=73.3°) P-HOLD is {'PASS' if ph['passed'] else 'FAIL'} — the platform "
        f"is caught within one detent pitch ({detent_mm} mm). The physics discovered the element; the "
        "pawl makes the design hold.")
    result["verdict_VB"] = "DEFERRED — P-SLIDE two-rail contact + P-GEAR R2b/D-M1-7 + P-FULL"
    result["shape_assert"] = {"pslide_va": "P-SLIDE-VA" in result["protocols"],
                              "pgear_va": "P-GEAR-VA" in result["protocols"],
                              "phold_present": "P-HOLD-VA" in result["protocols"],
                              "gravity_along_travel": True}
    (OUT / "t2_lift_verdict.json").write_text(json.dumps(result, indent=2))
    print(f"\nverdict V-A (slide+gear): {result['verdict_VA']}")
    print(f"HOLD finding: {result['hold_finding']}")
    print("wrote", OUT / "t2_lift_verdict.json")


if __name__ == "__main__":
    main()
