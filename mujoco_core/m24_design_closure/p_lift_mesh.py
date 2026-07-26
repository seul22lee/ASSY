"""m24 (§14 T5) — screw_lift V-A with the VISUAL BODIES = the COMPILED PART MESHES.

The m22 P-LIFT rig drew primitive boxes/cylinders (the reviewer's "primitive-proxy rendering"). §14 T5
requires the reviewer to see the ACTUAL compiled geometry move. This rig keeps the m22 physics EXACTLY
(same joints, equalities, sourced friction, actuator, and — pinned via explicit <inertial> — the same
per-body mass/inertia) and swaps the visual geoms for the compiled meshes (collision off, density 0):

  world (static)  ← screw_base(frame=True): base plate + bearing boss + two guide columns  [design frame]
  screw body      ← the screw rod (lead_screw geometry, coarse-cylinder proxy per D-M8-4)
  nut  body       ← nut_carriage: platform + nut boss + two column bores  [rides the columns]
  crank body      ← shaft_carrier_out(crank=True) + coupling hub  [the hand crank]

PHYSICS-IDENTICAL ASSERT (printed): the criteria from this mesh rig are compared BYTE-FOR-BYTE against a
BARE rig (identical inertials/joints/equalities/actuator, NO visual geoms). Equal ⇒ the meshes are pure
visual and the recorded verdict (reaches 40.00 / formula 0.000% / backdrive 0.080 / discrimination 9.20)
is untouched by the reshape. If the criteria differ, the mesh changed the physics — STOP.

  export MUJOCO_GL=egl ; ./bin/py m24_design_closure/p_lift_mesh.py [out_dir]
"""

from __future__ import annotations

import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "m0"))
sys.path.insert(0, str(ROOT / "m22_composition"))

import mujoco as mj  # noqa: E402
import numpy as np  # noqa: E402
from build123d import Align, Cylinder, Location  # noqa: E402

from knowledge.cards.base import CARD_REGISTRY  # noqa: E402
from knowledge.cards.lead_screw import lead_screw_dims, lead_screw_mechanics  # noqa: E402
from knowledge.materials import PETG  # noqa: E402
from knowledge.templates.host_templates import screw_base, nut_carriage, shaft_carrier_out  # noqa: E402
from ontology.validators import validate_all  # noqa: E402
from pipeline.compile_assembly import compile_assembly  # noqa: E402
from tasks.build_goldens import screw_lift  # noqa: E402
from verify.t2_physics.mjcf import _to_trimesh  # noqa: E402
from verify.t2_physics.runner import _hash, g9_gconv  # noqa: E402
from step2mjcf import MM  # noqa: E402

# reuse the m22 physics VERBATIM (drive/hold loop, criteria, discrimination probes, plot, video HUD)
import p_lift_va as P  # noqa: E402

G = 9.81


def _inertial(parent, bi, model):
    """emit an <inertial> reproducing body `bi`'s mass/com/inertia from the primitive rig exactly."""
    m = float(model.body_mass[bi])
    pos = " ".join(f"{v:.9f}" for v in model.body_ipos[bi])
    quat = " ".join(f"{v:.9f}" for v in model.body_iquat[bi])
    diag = " ".join(f"{v:.9e}" for v in model.body_inertia[bi])
    ET.SubElement(parent, "inertial", mass=f"{m:.9f}", pos=pos, quat=quat, diaginertia=diag)


def _meshes(plan, meshdir: Path):
    """export the four compiled per-body meshes (metres) and return {name: path}."""
    meshdir.mkdir(parents=True, exist_ok=True)
    e2 = next(e for e in plan.elements if e.card_ref == "lead_screw")
    g = lead_screw_dims(e2.params)
    p1 = next(p for p in plan.pieces if p.id == "P1")
    p2 = next(p for p in plan.pieces if p.id == "P2")
    # world frame: base plate + boss + guide columns (the screw is card-carved, so the template part is
    # exactly the STATIC frame — no screw). nut_carriage part = the platform (bores + boss).
    base_part = screw_base(**p1.params).part
    nut_part = nut_carriage(**p2.params).part
    # screw rod: the lead_screw geometry as a compiled cylinder (thread = card knowledge, coarse-cylinder
    # collision proxy per D-M8-4). Grows from the base top (z = base_t) to base_t + length.
    T = p1.params["base_t"]
    screw_part = Location((0, 0, T)) * Cylinder(g.d_major / 2, g.length,
                                                align=(Align.CENTER, Align.CENTER, Align.MIN))
    # crank + coupling hub: the compiled P3 (shaft_carrier_out(crank=True) with the coupling hub fused).
    ca = compile_assembly(plan)
    crank_part = ca.parts["P3"]
    out = {}
    for name, part in [("base", base_part), ("screw", screw_part), ("nut", nut_part), ("crank", crank_part)]:
        pth = meshdir / f"{name}.stl"
        _to_trimesh(part, pth)                       # writes STL in metres
        out[name] = pth
    return out, g


def build(plan, meshdir: Path, prim_model, meshes=True, markers=True):
    """build the screw_lift rig. meshes=True → compiled-mesh visuals; meshes=False → BARE (no visuals).
    Physics (inertials from prim_model, joints, equalities, friction, actuator) is identical either way."""
    e2 = next(e for e in plan.elements if e.card_ref == "lead_screw")
    g = lead_screw_dims(e2.params)
    mech = lead_screw_mechanics(g)
    load_kg = float(next((b.load.get("mass_kg", 0.5) for b in plan.behaviors
                          if b.load and getattr(b.phase, "value", b.phase) == "static"), 0.5))
    lead_m = g.lead * MM
    poly = lead_m / (2 * math.pi)
    d_mean_m = mech["d_mean_mm"] * MM
    W = load_kg * G
    T_friction = PETG.mu_friction * W * d_mean_m / 2.0
    T_backdrive = W * poly
    rs = g.d_major / 2 * MM
    length_m = g.length * MM
    z0 = 0.030

    mpaths, _ = _meshes(plan, meshdir) if meshes else ({}, g)

    root = ET.Element("mujoco", model="t2_screw_lift_mesh" if meshes else "t2_screw_lift_bare")
    ET.SubElement(root, "compiler", angle="radian", autolimits="true", meshdir=str(meshdir))
    ET.SubElement(root, "option", timestep=f"{P.VA_DT}", integrator="implicitfast",
                  cone="elliptic", impratio="10", gravity="0 0 0")
    vis = ET.SubElement(root, "visual")
    ET.SubElement(vis, "headlight", ambient="0.5 0.5 0.5", diffuse="0.6 0.6 0.6", specular="0.2 0.2 0.2")
    ET.SubElement(vis, "global", offwidth="1280", offheight="960")
    dflt = ET.SubElement(root, "default")
    ET.SubElement(dflt, "geom", density="0", contype="0", conaffinity="0", group="2")
    asset = ET.SubElement(root, "asset")
    for name, rgba in [("base", "0.62 0.66 0.72 1"), ("crank", "0.85 0.35 0.35 1"),
                       ("screw", "0.95 0.62 0.25 1"), ("nut", "0.45 0.78 0.5 1"),
                       ("mk_crank", "0.90 0.10 0.10 1"), ("mk_screw", "0.98 0.85 0.10 1"),
                       ("mk_nut", "0.10 0.55 0.95 1")]:
        ET.SubElement(asset, "material", name=name, rgba=rgba)
    if meshes:
        for name, pth in mpaths.items():
            ET.SubElement(asset, "mesh", name=f"m_{name}", file=pth.name)

    world = ET.SubElement(root, "worldbody")
    ET.SubElement(world, "light", pos="0.1 -0.2 0.4", dir="-0.2 0.3 -1", directional="true",
                  diffuse="0.5 0.5 0.5")
    ET.SubElement(world, "camera", name="side", pos="0.19 -0.24 0.055",
                  xyaxes="0.78 0.62 0 -0.14 0.18 0.98")
    ET.SubElement(world, "camera", name="iso", pos="0.16 -0.16 0.10",
                  xyaxes="0.71 0.71 0 -0.35 0.35 0.87")
    if meshes:
        ET.SubElement(world, "geom", name="frame_mesh", type="mesh", mesh="m_base", material="base")

    ci = mj.mj_name2id(prim_model, mj.mjtObj.mjOBJ_BODY, "crank")
    si = mj.mj_name2id(prim_model, mj.mjtObj.mjOBJ_BODY, "screw")
    ni = mj.mj_name2id(prim_model, mj.mjtObj.mjOBJ_BODY, "nut")

    def _mk(parent, name, mat, pos, size):
        if markers:
            ET.SubElement(parent, "geom", name=name, type="box",
                          pos=" ".join(f"{v:.6f}" for v in pos), size=" ".join(f"{v:.6f}" for v in size),
                          material=mat)

    bc = ET.SubElement(world, "body", name="crank", pos="0 0 0")
    _inertial(bc, ci, prim_model)
    ET.SubElement(bc, "joint", name="crank_hinge", type="hinge", axis="0 0 1", pos="0 0 0",
                  damping=f"{P.JOINT_DAMPING}", armature=f"{P.ARMATURE}")
    if meshes:
        ET.SubElement(bc, "geom", name="crank_mesh", type="mesh", mesh="m_crank", material="crank")
    _mk(bc, "mk_crank", "mk_crank", (0.026, 0, -0.030), (0.0025, 0.0025, 0.002))

    bs = ET.SubElement(world, "body", name="screw", pos="0 0 0")
    _inertial(bs, si, prim_model)
    ET.SubElement(bs, "joint", name="screw_hinge", type="hinge", axis="0 0 1", pos="0 0 0",
                  damping=f"{P.JOINT_DAMPING}", armature=f"{P.ARMATURE}", frictionloss=f"{T_friction:.9f}")
    if meshes:
        ET.SubElement(bs, "geom", name="screw_mesh", type="mesh", mesh="m_screw", material="screw")
    _mk(bs, "mk_screw", "mk_screw", (rs + 0.002, 0, 0.020), (0.003, 0.0012, 0.004))

    bn = ET.SubElement(world, "body", name="nut", pos="0 0 0")
    _inertial(bn, ni, prim_model)
    ET.SubElement(bn, "joint", name="nut_slide", type="slide", axis="0 0 1", pos="0 0 0",
                  damping=f"{P.JOINT_DAMPING}")
    if meshes:
        ET.SubElement(bn, "geom", name="nut_mesh", type="mesh", mesh="m_nut", material="nut")
    _mk(bn, "mk_nut", "mk_nut", (0.023, 0, z0), (0.002, 0.0025, 0.003))

    eq = ET.SubElement(root, "equality")
    ET.SubElement(eq, "joint", name="couple_cs", joint1="screw_hinge", joint2="crank_hinge",
                  polycoef="0 1.0 0 0 0", solref="-1e8 -1e4", solimp="0.9999 0.99999 1e-6 0.5 2")
    ET.SubElement(eq, "joint", name="couple_sn", joint1="nut_slide", joint2="screw_hinge",
                  polycoef=f"0 {poly:.9f} 0 0 0", solref="-1e8 -1e4", solimp="0.9999 0.99999 1e-6 0.5 2")
    act = ET.SubElement(root, "actuator")
    ET.SubElement(act, "velocity", name="drive", joint="crank_hinge", kv=f"{P.KV}")

    xml = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
    meta = {"lead_mm": g.lead, "d_mean_mm": mech["d_mean_mm"], "stroke_mm": g.stroke,
            "poly_m_per_rad": poly, "coupling_ratio": 1.0, "load_kg": load_kg, "W_N": round(W, 4),
            "T_friction_Nm": round(T_friction, 6), "T_backdrive_Nm": round(T_backdrive, 6),
            "hold_margin": round(T_friction / T_backdrive, 3) if T_backdrive else None,
            "n_rev": round(g.stroke / g.lead, 3), "z0_m": z0}
    return xml, meta


def _crit_tuple(v):
    return tuple((k, c["value"], c["pass"]) for k, c in v["criteria"].items())


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "out"
    out.mkdir(parents=True, exist_ok=True)
    plan = screw_lift()
    for e in plan.elements:
        e.params = CARD_REGISTRY[e.card_ref].resolve_params(plan, e)
    assert not validate_all(plan), "golden must be validator-clean"
    compile_assembly(plan)

    # the primitive rig supplies the exact inertials (source of truth for the physics)
    prim_xml, _ = P.build_lift_mjcf(plan, out / "_prim_assets")
    (out / "_prim.xml").write_text(prim_xml)
    prim_model = mj.MjModel.from_xml_path(str(out / "_prim.xml"))

    # BARE rig (no visuals) and MESH rig (compiled visuals) — identical physics
    bare_xml, meta = build(plan, out / "mesh_assets", prim_model, meshes=False)
    (out / "t2_screw_lift_bare.xml").write_text(bare_xml)
    mesh_xml, meta = build(plan, out / "mesh_assets", prim_model, meshes=True)
    (out / "t2_screw_lift_mesh.xml").write_text(mesh_xml)

    bare = mj.MjModel.from_xml_path(str(out / "t2_screw_lift_bare.xml"))
    mesh = mj.MjModel.from_xml_path(str(out / "t2_screw_lift_mesh.xml"))
    gok, _ = g9_gconv(mesh)

    # PHYSICS-IDENTICAL ASSERT: seed-0 criteria + discrimination probes, bare vs mesh
    vb, _, _ = P.run_lift(bare, meta, seed=0, record=False)
    vm, series0, frames0 = P.run_lift(mesh, meta, seed=0, record=True)
    identical = _crit_tuple(vb) == _crit_tuple(vm)
    print("=== PHYSICS-IDENTICAL ASSERT (bare declared-joint rig vs compiled-mesh rig) ===")
    for (kb, vbv, pbv), (km, vmv, pmv) in zip(_crit_tuple(vb), _crit_tuple(vm)):
        print(f"   {kb:<48s} bare={vbv} mesh={vmv}  {'OK' if (vbv==vmv and pbv==pmv) else 'DIFFERS!'}")
    print(f"   => criteria identical: {identical}")
    assert identical, "mesh visuals changed the physics — STOP (T5 forbids this)"

    # 5 seeds on the mesh rig (the deliverable) + discrimination
    per_seed = []
    for seed in range(P.N_SEEDS):
        v, s, f = P.run_lift(mesh, meta, seed, record=False)
        per_seed.append(v)
    n_pass = sum(v["passed"] for v in per_seed)
    vbk, _, _ = P.run_lift(mesh, meta, seed=0, record=False, break_coupling=True)
    fweak = 0.5 * meta["T_backdrive_Nm"]
    vf, _, _ = P.run_lift(mesh, meta, seed=0, record=False, friction_override=fweak)

    # video + plot from the mesh rig (real compiled geometry on film)
    if frames0:
        P._save_video(frames0, meta, out / "t2_screw_lift_mesh.mp4")
    if series0:
        P._plot(series0, vm, meta, out / "t2_screw_lift_mesh.png")

    result = {
        "decision_row": "D-M24-2 screw_lift T5 — visual bodies = compiled part meshes (physics-identical)",
        "compile_hash": _hash(), "task": "screw_lift",
        "physics_identical_bare_vs_mesh": identical,
        "visual_bodies": {"world": "screw_base(frame): base+boss+guide columns",
                          "screw": "lead_screw rod (coarse-cylinder proxy, D-M8-4)",
                          "nut": "nut_carriage: platform+nut boss+column bores",
                          "crank": "shaft_carrier_out(crank)+coupling hub (compiled P3)"},
        "g9_gconv": bool(gok),
        "V-A": {"n_seeds": P.N_SEEDS, "seeds_passed": n_pass, "passed": bool(n_pass >= P.SEED_PASS),
                "criteria_seed0": per_seed[0]["criteria"], "per_seed": per_seed,
                "discrimination_probes": {
                    "coupling_broken": {"crank_rev": vbk["revs_crank"], "platform_rise_mm": vbk["travel_mm"]},
                    "friction_weak": {"weak_friction_Nm": round(fweak, 6), "backdrive_mm": vf["backdrive_mm"],
                                      "sourced_backdrive_mm": per_seed[0]["backdrive_mm"]},
                    "discriminates": bool(vbk["travel_mm"] < 1.0 and vbk["revs_crank"] > 1.0
                                          and vf["backdrive_mm"] > 5 * P.HOLD_TOL_MM
                                          and per_seed[0]["backdrive_mm"] <= P.HOLD_TOL_MM)}},
        "recorded_m22_verdict": {"reaches_mm": 40.00, "formula_pct": 0.000, "backdrive_mm": 0.080,
                                 "discrimination_sink_mm": 9.20},
        "video": "t2_screw_lift_mesh.mp4", "plot": "t2_screw_lift_mesh.png",
    }
    (out / "t2_screw_lift_mesh_verdict.json").write_text(json.dumps(result, indent=2))
    c = per_seed[0]["criteria"]
    print(f"\n=== screw_lift T5 (compiled-mesh visuals) ===  G-CONV {'ok' if gok else 'FAIL'}  "
          f"seeds {n_pass}/{P.N_SEEDS} => {'PASS' if n_pass >= P.SEED_PASS else 'FAIL'}")
    print(f"   reaches {c['platform_reaches_height']['value']} mm | "
          f"formula {c['end_to_end_formula (|H/(N·1·lead)−1| ≤ 0.1%)']['value']*100:.3f}% | "
          f"backdrive {c['holds_released_load (back-drive ≤ 1 mm)']['value']} mm")
    print(f"   discrimination: coupling BROKEN → {vbk['travel_mm']:.2f} mm rise | "
          f"friction WEAK → sinks {vf['backdrive_mm']:.2f} mm")
    print(f"   vs recorded m22: reaches 40.00 / formula 0.000% / backdrive 0.080 / sink 9.20")
    print("wrote", out / "t2_screw_lift_mesh_verdict.json")


if __name__ == "__main__":
    main()
