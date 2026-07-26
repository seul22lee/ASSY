"""m24 (§14 T5) — latched_drawer / latch V-A with the VISUAL BODIES = the COMPILED PART MESHES.

The m23 P-LATCH rig drew primitive boxes for the cabinet + drawer + hook. §14 T5 shows the ACTUAL
compiled geometry: the cabinet (floor + walls + lintel + receiver LEDGE) and the drawer (tray + carved
CANTILEVER + ramped BARB) — the design that closes DRAFT D-M22-2c at the template level. The physics is
kept EXACTLY (the drawer slide joint, the rigid latch equality whose breakaway is the SOURCED Bayer
W_out, the drive; the drawer mass+inertia pinned via <inertial>). Visuals are collision-off / density-0.

PHYSICS-IDENTICAL ASSERT (printed): criteria of this mesh rig vs a BARE rig (same inertial/joint/
equality/actuator, no visual geoms). Equal ⇒ meshes are pure visual and the recorded m23 verdict
(engage 0.399 / hold 0.449 / release 59.73) stands. Differ ⇒ STOP.

  export MUJOCO_GL=egl ; ./bin/py m24_design_closure/p_latch_mesh.py [out_dir]
"""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "m0"))
sys.path.insert(0, str(ROOT / "m23_latch_physics"))

import imageio.v2 as imageio  # noqa: E402
import mujoco as mj  # noqa: E402

from knowledge.templates.host_templates import latch_design_parts  # noqa: E402
from tasks.build_goldens import latched_drawer  # noqa: E402
from verify.t2_physics.mjcf import _to_trimesh  # noqa: E402
from verify.t2_physics.runner import _hash, g9_gconv  # noqa: E402
from step2mjcf import MM  # noqa: E402

import p_latch_va as P  # noqa: E402  (the m23 physics: run_latch, _sourced_W_out, _save_video, _plot)


def _inertial(parent, bi, model):
    m = float(model.body_mass[bi])
    ET.SubElement(parent, "inertial", mass=f"{m:.9f}",
                  pos=" ".join(f"{v:.9f}" for v in model.body_ipos[bi]),
                  quat=" ".join(f"{v:.9f}" for v in model.body_iquat[bi]),
                  diaginertia=" ".join(f"{v:.9e}" for v in model.body_inertia[bi]))


def _export_meshes(meshdir: Path):
    meshdir.mkdir(parents=True, exist_ok=True)
    parts = latch_design_parts()
    out = {}
    for name, part in parts.items():
        pth = meshdir / f"{name}.stl"
        _to_trimesh(part, pth)
        out[name] = pth
    return out


def build(plan, meshdir, prim_model, W_out, meshes=True, markers=True):
    e1 = next(e for e in plan.elements if e.card_ref == "slide_rail")
    stroke_m = float(e1.params["stroke"]) * MM
    mpaths = _export_meshes(meshdir) if meshes else {}

    root = ET.Element("mujoco", model="t2_latch_mesh" if meshes else "t2_latch_bare")
    ET.SubElement(root, "compiler", angle="radian", autolimits="true", meshdir=str(meshdir))
    ET.SubElement(root, "option", timestep=f"{P.VA_DT}", integrator="implicitfast", cone="elliptic",
                  impratio="10", gravity="0 0 0")
    vis = ET.SubElement(root, "visual")
    ET.SubElement(vis, "headlight", ambient="0.5 0.5 0.5", diffuse="0.6 0.6 0.6", specular="0.2 0.2 0.2")
    ET.SubElement(vis, "global", offwidth="1280", offheight="960")
    dflt = ET.SubElement(root, "default")
    ET.SubElement(dflt, "geom", density="0", contype="0", conaffinity="0", group="2")
    asset = ET.SubElement(root, "asset")
    # the cabinet is a FULL enclosure (all walls) — rendered TRANSLUCENT so the reviewer sees the drawer,
    # barb and receiver inside (the §14 cutaway; visual-only, physics is the declared latch).
    for name, rgba in [("cab", "0.60 0.66 0.72 0.30"), ("recv", "0.85 0.30 0.30 1"),
                       ("drawer", "0.95 0.72 0.35 1"), ("hook", "0.20 0.55 0.95 1"),
                       ("mk", "0.10 0.85 0.35 1")]:
        ET.SubElement(asset, "material", name=name, rgba=rgba)
    if meshes:
        for name in mpaths:
            ET.SubElement(asset, "mesh", name=f"m_{name}", file=mpaths[name].name)

    world = ET.SubElement(root, "worldbody")
    ET.SubElement(world, "light", pos="0.02 -0.2 0.3", dir="-0.05 0.3 -1", directional="true", diffuse="0.5 0.5 0.5")
    ET.SubElement(world, "camera", name="cutaway", pos="0.03 -0.11 0.05", xyaxes="1 0 0 0 0.4 0.92")
    ET.SubElement(world, "camera", name="zoom", pos="0.040 -0.040 0.024", xyaxes="1 0 0 0 0.45 0.89")
    if meshes:
        ET.SubElement(world, "geom", name="cab_mesh", type="mesh", mesh="m_cabinet_body", material="cab")
        ET.SubElement(world, "geom", name="receiver_mesh", type="mesh", mesh="m_receiver", material="recv")

    bi = mj.mj_name2id(prim_model, mj.mjtObj.mjOBJ_BODY, "drawer")
    bd = ET.SubElement(world, "body", name="drawer", pos="0 0 0")
    _inertial(bd, bi, prim_model)
    ET.SubElement(bd, "joint", name="drawer_slide", type="slide", axis="1 0 0", pos="0 0 0",
                  limited="true", range=f"0 {stroke_m:.6f}", damping="150",
                  solreflimit="0.002 1", solimplimit="0.99 0.9999 1e-5 0.5 2")
    if meshes:
        ET.SubElement(bd, "geom", name="dr_mesh", type="mesh", mesh="m_drawer_body", material="drawer")
        ET.SubElement(bd, "geom", name="barb_mesh", type="mesh", mesh="m_barb", material="hook")
    if markers:
        ET.SubElement(bd, "geom", name="mk_drawer", type="box", pos="0 -0.012 0.006", size="0.004 0.0015 0.004", material="mk")

    eq = ET.SubElement(root, "equality")
    ET.SubElement(eq, "joint", name="latch", joint1="drawer_slide", polycoef="0 0 0 0 0", active="false",
                  solref="-1e8 -1e4", solimp="0.9999 0.99999 1e-6 0.5 2")
    act = ET.SubElement(root, "actuator")
    ET.SubElement(act, "velocity", name="drive", joint="drawer_slide", kv="600")

    xml = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
    meta = {"stroke_mm": float(e1.params["stroke"]), "stroke_m": stroke_m, "W_out_N": W_out,
            "pull_hold_N": round(0.5 * W_out, 2), "pull_release_N": round(1.5 * W_out, 2)}
    return xml, meta


def _crit(v):
    return tuple((k, c["value"], c["pass"]) for k, c in v["criteria"].items())


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "out"
    out.mkdir(parents=True, exist_ok=True)
    plan = latched_drawer()
    src = P._sourced_W_out(plan)

    # m23 primitive rig → the exact drawer inertial (source of truth)
    prim_xml, _ = P.build_latch_mjcf(plan, src["W_out_N"])
    (out / "_prim_latch.xml").write_text(prim_xml)
    prim = mj.MjModel.from_xml_path(str(out / "_prim_latch.xml"))

    bare_xml, meta = build(plan, out / "latch_mesh_assets", prim, src["W_out_N"], meshes=False)
    mesh_xml, meta = build(plan, out / "latch_mesh_assets", prim, src["W_out_N"], meshes=True)
    (out / "t2_latch_bare.xml").write_text(bare_xml)
    (out / "t2_latch_mesh.xml").write_text(mesh_xml)
    bare = mj.MjModel.from_xml_path(str(out / "t2_latch_bare.xml"))
    mesh = mj.MjModel.from_xml_path(str(out / "t2_latch_mesh.xml"))
    gok, _ = g9_gconv(mesh)

    vb, _, _ = P.run_latch(bare, meta, seed=0, record=False)
    vm, s0, f0 = P.run_latch(mesh, meta, seed=0, record=True)
    identical = _crit(vb) == _crit(vm)
    print("=== PHYSICS-IDENTICAL ASSERT (bare declared-latch rig vs compiled-mesh rig) ===")
    for (kb, vbv, pbv), (km, vmv, pmv) in zip(_crit(vb), _crit(vm)):
        print(f"   {kb:<42s} bare={vbv} mesh={vmv}  {'OK' if (vbv==vmv and pbv==pmv) else 'DIFFERS!'}")
    print(f"   => criteria identical: {identical}")
    assert identical, "mesh visuals changed the physics — STOP (T5 forbids this)"

    per_seed = []
    for seed in range(P.N_SEEDS):
        v, _, _ = P.run_latch(mesh, meta, seed, record=False)
        per_seed.append(v)
    n_pass = sum(v["passed"] for v in per_seed)

    if f0:
        P._save_video(f0, meta, out / "t2_latch_mesh.mp4", view="cutaway")
        P._save_video(f0, meta, out / "t2_latch_mesh_zoom.mp4", view="zoom")
        eng = next((fr for fr in f0 if fr[6] == "hold"), f0[len(f0) // 2])
        imageio.imwrite(str(out / "engaged_closeup_mesh.png"), eng[1])
    if s0:
        P._plot(s0, vm, meta, out / "t2_latch_mesh.png")

    result = {
        "decision_row": "D-M24-3 latched_drawer T5 — visual bodies = compiled part meshes (physics-identical)",
        "compile_hash": _hash(), "task": "latched_drawer",
        "physics_identical_bare_vs_mesh": identical,
        "visual_bodies": {"cabinet(world)": "latch_cabinet: floor+walls+lintel+receiver ledge",
                          "drawer": "latch_drawer: tray + carved cantilever + ramped barb"},
        "sourced_breakaway": {**src, "note": "W_out SOURCED from Bayer M3 (D3), the m19 pattern"},
        "g9_gconv": bool(gok),
        "V-A": {"n_seeds": P.N_SEEDS, "seeds_passed": n_pass, "passed": bool(n_pass >= P.SEED_PASS),
                "criteria_seed0": per_seed[0]["criteria"], "per_seed": per_seed},
        "recorded_m23_verdict": {"engage_mm": 0.399, "hold_creep_mm": 0.449, "release_mm": 59.73},
        "video": "t2_latch_mesh.mp4", "video_zoom": "t2_latch_mesh_zoom.mp4", "plot": "t2_latch_mesh.png",
    }
    (out / "t2_latch_mesh_verdict.json").write_text(json.dumps(result, indent=2))
    c = per_seed[0]["criteria"]
    print(f"\n=== latched_drawer T5 (compiled-mesh visuals) ===  G-CONV {'ok' if gok else 'FAIL'}  "
          f"seeds {n_pass}/{P.N_SEEDS} => {'PASS' if n_pass >= P.SEED_PASS else 'FAIL'}")
    print(f"   SOURCED breakaway W_out = {src['W_out_N']} N")
    print(f"   engage {c['close_engages_at_closed']['value']} mm | "
          f"hold {c['holds_at_0.5·W_out (≤ tol)']['value']} mm | "
          f"release {c['releases_at_1.5·W_out (opens to rail)']['value']} mm")
    print(f"   vs recorded m23: engage 0.399 / hold 0.449 / release 59.73")
    print("wrote", out / "t2_latch_mesh_verdict.json")


if __name__ == "__main__":
    main()
