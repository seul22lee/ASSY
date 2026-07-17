"""m13 — THE HARD ANCHOR physics. P-SLIDE (the drawer moves) + P-GEAR (the knob transmits), both
V-A (declared kinematic pairs), on the compiled multi-body assembly.

WHY V-A. The rack_pinion carries the standing R2b-open flag (D-M1-5/-7): emergent tooth-contact
(V-B) is DEFERRED. The drawer P-SLIDE V-B (contact-only) is a two-rail welded-drawer contact problem
one step past m10's single-rail V-B — attempted honestly, and if it fights the frozen preset it is
CHECKPOINTED, not forced (the m8 lesson; the brief's "checkpoint honestly"). This runner establishes
the two declared-pair results the §8.2 mechanism turns on:

  P-SLIDE V-A : the drawer (carriages + tray + rack, welded) on a declared +X prismatic joint reaches
                its 120 mm design stroke under an axial pull, tracking straight.
  P-GEAR  V-A : a declared knob hinge (+Z) coupled to the drawer slide by a near-rigid equality at
                the pitch radius rp; turning the knob drives the drawer, and the travel matches the
                §3.6 transmission π·m·z per rev.

The FROZEN preset (R5) sets the clock; V-A declares no tooth contact (the joints are the mechanism).

Run:  ./bin/py m13_hard_anchor/p_full.py
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
from ontology.validators import validate_all  # noqa: E402
from pipeline.compile_assembly import compile_assembly  # noqa: E402
from tasks.build_goldens import anchor_hard  # noqa: E402
from verify.t2_physics.mjcf import _inertial, _to_trimesh  # noqa: E402
from verify.t2_physics.runner import _hash, g9_gconv  # noqa: E402

from step2mjcf import MM, SOLIMP, SOLREF  # FROZEN preset (R5)  # noqa: E402

OUT = Path(__file__).parent / "out"
FROZEN_DT, FPS = 5e-4, 60
N_SEEDS, SEED_PASS = 5, 4
STROKE_MM = 120.0
MOVER = ["P2", "P3", "P4"]          # carriages + drawer(+rack) — the welded moving assembly
G = 9.81


def _v(a):
    return " ".join(f"{float(x):.9f}" for x in a)


def _preamble(tag):
    root = ET.Element("mujoco", model=f"m13_{tag}")
    ET.SubElement(root, "compiler", angle="radian", meshdir="assets", autolimits="true")
    ET.SubElement(root, "option", timestep=f"{FROZEN_DT}", integrator="implicitfast",
                  cone="elliptic", impratio="10")
    vis = ET.SubElement(root, "visual")
    ET.SubElement(vis, "headlight", ambient="0.5 0.5 0.5", diffuse="0.6 0.6 0.6", specular="0.2 0.2 0.2")
    ET.SubElement(vis, "global", offwidth="1280", offheight="960", azimuth="150", elevation="-20")
    dflt = ET.SubElement(root, "default")
    ET.SubElement(dflt, "geom", solref=f"{SOLREF[0]} {SOLREF[1]}",
                  solimp=f"{SOLIMP[0]} {SOLIMP[1]} {SOLIMP[2]}", density="0",
                  contype="0", conaffinity="0", group="2")
    asset = ET.SubElement(root, "asset")
    for name, rgba in [("base", "0.54 0.66 0.79 1"), ("mover", "0.42 0.75 0.48 1"),
                       ("knob", "0.79 0.55 0.75 1")]:
        ET.SubElement(asset, "material", name=name, rgba=rgba)
    world = ET.SubElement(root, "worldbody")
    ET.SubElement(world, "light", pos="0.2 -0.3 0.5", dir="-0.3 0.5 -1", directional="true",
                  diffuse="0.5 0.5 0.5")
    ET.SubElement(world, "camera", name="iso", pos="0.28 -0.34 0.24",
                  xyaxes="0.78 0.63 0 -0.28 0.34 0.90")
    return root, asset, world


def _add_mesh_geom(body, asset, name, solid, material):
    vf = OUT / "assets" / f"{name}.stl"
    vf.parent.mkdir(parents=True, exist_ok=True)
    mesh = _to_trimesh(solid, vf)
    ET.SubElement(asset, "mesh", name=name, file=vf.name)
    ET.SubElement(body, "geom", name=name, type="mesh", mesh=name, material=material)
    return mesh


def build_mjcf(ca, tag, couple=False):
    """base(cabinet, welded) + mover(carriages+drawer+rack, one body, +X slide) + knob(+Z hinge).
    couple=True adds the near-rigid equality drawer_x = rp·knob_theta (P-GEAR); else free (P-SLIDE)."""
    root, asset, world = _preamble(tag)
    ax = ca.axes["E1"]                    # +X travel axis (both rails identical dir)
    rp_m = 30.0 * MM                       # pitch radius (m·z/2 = 30 mm) in metres

    # base: cabinet, welded to world
    base = ET.SubElement(world, "body", name="base", pos="0 0 0")
    m = _add_mesh_geom(base, asset, "cabinet", ca.parts["P1"], "base")
    _inertial(base, m)

    # mover: carriages + drawer(+rack) as one welded body on a declared +X prismatic joint
    mover = ET.SubElement(world, "body", name="mover", pos="0 0 0")
    strk_m = STROKE_MM * MM
    ET.SubElement(mover, "joint", name="drawer", type="slide", axis="1 0 0",
                  pos=_v(np.array(ax["point"]) * MM), damping="0.05",
                  range=f"-0.002 {strk_m + 0.002:.5f}", limited="true")
    masses = []
    for pid in MOVER:
        mm = _add_mesh_geom(mover, asset, f"mv_{pid}", ca.parts[pid], "mover")
        masses.append(float(mm.mass))
    # one inertial for the whole welded mover (sum of parts, at the drawer's COM)
    _inertial(mover, _to_trimesh(ca.parts["P4"], OUT / "assets" / "mv_inertial.stl"))

    # knob: pinion on a +Z hinge at the shaft seat
    knob = ET.SubElement(world, "body", name="knob", pos="0 0 0")
    seat = np.array(ca.axes["E3"]["point"]) * MM
    ET.SubElement(knob, "joint", name="pinion", type="hinge", axis="0 0 1", pos=_v(seat),
                  damping="0.002")
    mk = _add_mesh_geom(knob, asset, "knob", ca.parts["P5"], "knob")
    _inertial(knob, mk)

    if couple:
        eq = ET.SubElement(root, "equality")
        ET.SubElement(eq, "joint", name="couple", joint1="drawer", joint2="pinion",
                      polycoef=f"0 {rp_m:.9f} 0 0 0", solref="0.0005 1",
                      solimp="0.999 0.9999 0.0001 0.5 2")
        act = ET.SubElement(root, "actuator")
        ET.SubElement(act, "velocity", name="drive", joint="pinion", kv="5e-2")

    xml = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
    meta = {"rp_m": rp_m, "stroke_mm": STROKE_MM, "axis_pt_m": list(np.array(ax["point"]) * MM),
            "travel_per_rev_mm": round(math.pi * 5 * 12, 4)}
    return xml, meta


def run_pslide_va(model, seed=0, record=False):
    """Axial force ramp on the drawer; measure travel to the design stroke + off-axis tracking."""
    d = mj.MjData(model)
    rng = np.random.default_rng(seed)
    jid = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "drawer")
    adr = model.jnt_qposadr[jid]
    mover = mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, "mover")
    cam = mj.mj_name2id(model, mj.mjtObj.mjOBJ_CAMERA, "iso")
    mj.mj_forward(model, d)
    d.qpos[adr] = rng.uniform(0.0, 2e-4)
    mj.mj_forward(model, d)
    R0 = d.xmat[mover].reshape(3, 3).copy()
    s_target = STROKE_MM * MM
    renderer = mj.Renderer(model, 480, 640) if record else None
    F_MAX, T_RAMP, T_SETTLE = 2.0, 2.0, 1.0
    ts, s_mm, off, frames, nxt = [], [], [], [], 0.0
    diverged = False
    t_open = None
    while d.time < T_RAMP + T_SETTLE:
        s = float(d.qpos[adr])
        if t_open is None and s >= s_target:
            t_open = d.time
        F = min(F_MAX, F_MAX * d.time / T_RAMP) if t_open is None else 0.0
        d.qfrc_applied[:] = 0.0
        d.qfrc_applied[model.jnt_dofadr[jid]] = F
        mj.mj_step(model, d)
        if not np.all(np.isfinite(d.qpos)) or abs(d.qvel[model.jnt_dofadr[jid]]) > 1e3:
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
    s_max = float(s_arr.max()); off_max = float(max(off)) if off else 999.0
    crit = {"reaches_stroke": {"value": round(s_max, 1), "threshold": STROKE_MM,
                               "pass": bool(s_max >= STROKE_MM - 1.0 and not diverged)},
            "tracks_straight (≤3°)": {"value": round(off_max, 3), "threshold": 3.0,
                                      "pass": bool(off_max <= 3.0 and not diverged)},
            "converged": {"value": diverged, "threshold": False, "pass": bool(not diverged)}}
    v = {"mode": "V-A", "seed": seed, "s_max_mm": s_max, "offaxis_max_deg": off_max,
         "diverged": diverged, "criteria": crit, "passed": bool(all(c["pass"] for c in crit.values()))}
    return v, {"t": ts, "s_mm": s_mm}, frames


def run_pgear_va(model, meta, seed=0, record=False):
    """Drive the knob; the coupled drawer must travel the §3.6 amount (|s/(tpr·rev)−1| ≤ 5%)."""
    d = mj.MjData(model)
    rng = np.random.default_rng(seed)
    jpin = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "pinion")
    jdr = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "drawer")
    ipa, ida = model.jnt_qposadr[jpin], model.jnt_qposadr[jdr]
    cam = mj.mj_name2id(model, mj.mjtObj.mjOBJ_CAMERA, "iso")
    rp_m = meta["rp_m"]
    mj.mj_forward(model, d)
    d.qpos[ipa] += rng.uniform(-1e-3, 1e-3)
    mj.mj_forward(model, d)
    theta0, s0 = float(d.qpos[ipa]), float(d.qpos[ida])
    theta_target = (STROKE_MM * MM) / rp_m
    OMEGA, RAMP = 3.0, 0.4
    renderer = mj.Renderer(model, 480, 640) if record else None
    ts, thp, srk, frames, nxt = [], [], [], [], 0.0
    diverged = False
    t_wall = theta_target / OMEGA + 4 * RAMP + 8.0
    while True:
        d.ctrl[0] = min(OMEGA, OMEGA * d.time / RAMP)
        mj.mj_step(model, d)
        if not np.all(np.isfinite(d.qpos)) or abs(d.qvel[model.jnt_dofadr[jpin]]) > 200:
            diverged = True
            break
        th = float(d.qpos[ipa]) - theta0
        ts.append(d.time); thp.append(th); srk.append(float(d.qpos[ida]) - s0)
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
            "matches_§3.6 (≤5%)": {"value": round(formula_resid, 4), "threshold": 0.05,
                                   "pass": bool(formula_resid <= 0.05 and not diverged)},
            "reaches_stroke": {"value": round(s_mm, 1), "threshold": STROKE_MM,
                               "pass": bool(s_mm >= STROKE_MM - 2.0 and not diverged)},
            "converged": {"value": diverged, "threshold": False, "pass": bool(not diverged)}}
    v = {"mode": "V-A", "seed": seed, "revs_done": round(revs, 3), "drawer_travel_mm": round(s_mm, 2),
         "formula_travel_mm": round(s_formula, 2), "ratio_residual": round(ratio_resid, 4),
         "diverged": diverged, "criteria": crit, "passed": bool(all(c["pass"] for c in crit.values()))}
    return v, {"theta_deg": list(np.rad2deg(thp)), "s_mm": [s / MM for s in srk]}, frames


def _pgear_plot(series, v, meta):
    fig, ax = plt.subplots(figsize=(8, 5))
    th, rk = series["theta_deg"], series["s_mm"]
    ax.plot(th, rk, lw=2, color="#2b6cb0", label="drawer travel s(θ) [measured]")
    tpr = meta["travel_per_rev_mm"]
    tl = np.array(th) if th else np.array([0.0])
    ax.plot(tl, tpr * tl / 360.0, "--", lw=1.4, color="#c53030", label=f"§3.6  s = {tpr:.1f}·θ/360")
    b = "PASS" if v["passed"] else "FAIL"
    ax.set_xlabel("knob angle θ (deg)"); ax.set_ylabel("drawer travel s (mm)")
    ax.set_title(f"P-GEAR / V-A  knob→drawer  [{b}]  travel={v['drawer_travel_mm']:.1f} mm, "
                 f"ratio resid={v['ratio_residual']*100:.2f}%", fontsize=10,
                 color="#22543d" if v["passed"] else "#742a2a")
    ax.legend(fontsize=9); ax.grid(alpha=.25)
    fig.tight_layout(); fig.savefig(OUT / "p_gear_VA.png", dpi=130); plt.close(fig)


def _pslide_plot(series, v):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(series["t"], series["s_mm"], lw=2, color="#2f855a", label="drawer s(t)")
    ax.axhline(STROKE_MM, ls="--", c="#c53030", lw=1.2); ax.text(0, STROKE_MM + 2, f" stroke {STROKE_MM:g}", color="#c53030")
    b = "PASS" if v["passed"] else "FAIL"
    ax.set_xlabel("t (s)"); ax.set_ylabel("drawer travel s (mm)")
    ax.set_title(f"P-SLIDE / V-A  drawer  [{b}]  s_max={v['s_max_mm']:.1f} mm, off-axis={v['offaxis_max_deg']:.2f}°",
                 fontsize=10, color="#22543d" if v["passed"] else "#742a2a")
    ax.legend(fontsize=9); ax.grid(alpha=.25)
    fig.tight_layout(); fig.savefig(OUT / "p_slide_VA.png", dpi=130); plt.close(fig)


import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    plan = anchor_hard()
    assert not validate_all(plan), "golden must be validator-clean"
    for e in plan.elements:
        e.params = CARD_REGISTRY[e.card_ref].resolve_params(plan, e)
    ca = compile_assembly(plan)

    result = {"decision_row": "m13 Hard anchor — P-SLIDE V-A + P-GEAR V-A (declared pairs)",
              "compile_hash": _hash(), "protocols": {}}

    # P-SLIDE V-A
    xml, meta = build_mjcf(ca, "pslide", couple=False)
    xf = OUT / "t2_pslide_VA.xml"; xf.write_text(xml)
    model = mj.MjModel.from_xml_path(str(xf))
    gok, _ = g9_gconv(model)
    per, s0, f0, v0 = [], None, None, None
    for seed in range(N_SEEDS):
        v, s, fr = run_pslide_va(model, seed, record=(seed == 0))
        per.append(v)
        if seed == 0:
            s0, f0, v0 = s, fr, v
    npass = sum(x["passed"] for x in per)
    result["protocols"]["P-SLIDE-VA"] = {"g9_gconv": bool(gok), "n_seeds": N_SEEDS,
                                         "seeds_passed": npass, "passed": bool(npass >= SEED_PASS),
                                         "criteria_seed0": per[0]["criteria"], "per_seed": per}
    if s0:
        _pslide_plot(s0, v0)
        if f0:
            imageio.mimsave(OUT / "p_slide_VA.mp4", f0, fps=FPS)
    print(f"P-SLIDE V-A: {npass}/{N_SEEDS} {'PASS' if npass>=SEED_PASS else 'FAIL'}  "
          f"s_max={per[0]['s_max_mm']:.1f}mm off={per[0]['offaxis_max_deg']:.2f}°")

    # P-GEAR V-A
    xml, meta = build_mjcf(ca, "pgear", couple=True)
    xf = OUT / "t2_pgear_VA.xml"; xf.write_text(xml)
    model = mj.MjModel.from_xml_path(str(xf))
    gok, _ = g9_gconv(model)
    per, s0, f0, v0 = [], None, None, None
    for seed in range(N_SEEDS):
        v, s, fr = run_pgear_va(model, meta, seed, record=(seed == 0))
        per.append(v)
        if seed == 0:
            s0, f0, v0 = s, fr, v
    npass = sum(x["passed"] for x in per)
    result["protocols"]["P-GEAR-VA"] = {"g9_gconv": bool(gok), "n_seeds": N_SEEDS,
                                        "seeds_passed": npass, "passed": bool(npass >= SEED_PASS),
                                        "criteria_seed0": per[0]["criteria"], "per_seed": per,
                                        "v_b_gap": "emergent tooth contact PENDING preset_v2 (R2b/D-M1-7)"}
    if s0:
        _pgear_plot(s0, v0, meta)
        if f0:
            imageio.mimsave(OUT / "p_gear_VA.mp4", f0, fps=FPS)
    print(f"P-GEAR  V-A: {npass}/{N_SEEDS} {'PASS' if npass>=SEED_PASS else 'FAIL'}  "
          f"travel={per[0]['drawer_travel_mm']:.1f}mm ratio_resid={per[0]['ratio_residual']*100:.2f}%")

    result["verdict_VA"] = bool(result["protocols"]["P-SLIDE-VA"]["passed"]
                                and result["protocols"]["P-GEAR-VA"]["passed"])
    result["verdict_VB"] = "DEFERRED — P-SLIDE-VB (multi-body contact) + P-GEAR-VB (R2b/D-M1-7): checkpoint"
    result["shape_assert"] = {"pslide_va": "P-SLIDE-VA" in result["protocols"],
                              "pgear_va": "P-GEAR-VA" in result["protocols"],
                              "vb_named_deferred": True}
    (OUT / "t2_hard_verdict.json").write_text(json.dumps(result, indent=2))
    print(f"\nverdict V-A: {result['verdict_VA']}   V-B: {result['verdict_VB']}")
    print("wrote", OUT / "t2_hard_verdict.json")


if __name__ == "__main__":
    main()
