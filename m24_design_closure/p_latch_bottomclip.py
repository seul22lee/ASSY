"""m24 Phase A (§14 T5) — latched_drawer (BOTTOM-CLIP) V-A with visual bodies = the COMPILED PART MESHES.

The bottom-clip organizer drawer: a cabinet (floor + walls + face frame + centre rail + catch bump) and
a drawer (tray + oversized front panel + groove + downward clip). The physics is the m23 sourced-latch
pattern, but with the DESIGNED breakaway W_out (from the inverse-Bayer fit chain, not the m23 fixture),
and the CLOSED STOP is the front-panel-on-face-frame landing (the slide joint's lower limit at s=0, a
PART, not a drive-off). Visuals are the compiled sub-solid meshes (cabinet_body+bump → world;
drawer_body+clip → the slide body), density 0.

PHYSICS-IDENTICAL ASSERT (printed): mesh rig vs a BARE rig (same inertial/joint/equality/actuator, no
visuals). CRITERIA CHANGE vs m23 is EXPECTED (W_out is now designed = 30.38 N, was 32.81 N) — old vs new
reported with the chain.

  export MUJOCO_GL=egl ; ./bin/py m24_design_closure/p_latch_bottomclip.py [out_dir]
"""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "m0"))
sys.path.insert(0, str(ROOT / "m23_latch_physics")); sys.path.insert(0, str(ROOT / "m24_design_closure"))

import imageio.v2 as imageio  # noqa: E402
import mujoco as mj  # noqa: E402
import numpy as np  # noqa: E402

from dim_chain import chain  # noqa: E402
from knowledge.templates.host_templates import latch_design_parts  # noqa: E402
from verify.t2_physics.mjcf import _to_trimesh  # noqa: E402
from verify.t2_physics.runner import _hash, g9_gconv  # noqa: E402
from step2mjcf import MM  # noqa: E402

import p_latch_va as P  # noqa: E402  (m23 physics: run_latch, _save_video, _plot)

DRAWER_MASS = 0.05          # a light plastic parts-drawer (kg)


def _export(meshdir: Path):
    meshdir.mkdir(parents=True, exist_ok=True)
    parts = latch_design_parts()
    out = {k: (meshdir / f"{k}.stl") for k in parts}
    meshes = {k: _to_trimesh(v, out[k]) for k, v in parts.items()}
    return out, meshes


def _drawer_inertial(meshes):
    """mass/com/inertia of the moving group (drawer_body ∪ clip) at DRAWER_MASS, from the compiled mesh."""
    import trimesh
    m = trimesh.util.concatenate([meshes["drawer_body"], meshes["clip"]])
    m.density = DRAWER_MASS / m.volume
    I = m.moment_inertia
    # principal diagonal (the mesh is near-axis-aligned; use the diagonal, clamp positive)
    diag = np.clip(np.diag(I), 1e-9, None)
    return DRAWER_MASS, m.center_mass, diag


def build(meshdir, W_out, stroke_mm, meshes=True, markers=True):
    stroke_m = stroke_mm * MM
    mpaths, meshset = _export(meshdir)
    mass, com, diag = _drawer_inertial(meshset)

    root = ET.Element("mujoco", model="t2_ld_mesh" if meshes else "t2_ld_bare")
    ET.SubElement(root, "compiler", angle="radian", autolimits="true", meshdir=str(meshdir))
    ET.SubElement(root, "option", timestep=f"{P.VA_DT}", integrator="implicitfast", cone="elliptic",
                  impratio="10", gravity="0 0 0")
    vis = ET.SubElement(root, "visual")
    ET.SubElement(vis, "headlight", ambient="0.5 0.5 0.5", diffuse="0.6 0.6 0.6", specular="0.2 0.2 0.2")
    ET.SubElement(vis, "global", offwidth="1280", offheight="960")
    dflt = ET.SubElement(root, "default")
    ET.SubElement(dflt, "geom", density="0", contype="0", conaffinity="0", group="2")
    asset = ET.SubElement(root, "asset")
    for name, rgba in [("cab", "0.60 0.66 0.72 0.30"), ("bump", "0.85 0.30 0.30 1"),
                       ("drawer", "0.95 0.72 0.35 1"), ("clip", "0.20 0.55 0.95 1"),
                       ("mk", "0.10 0.85 0.35 1")]:
        ET.SubElement(asset, "material", name=name, rgba=rgba)
    if meshes:
        for k in mpaths:
            ET.SubElement(asset, "mesh", name=f"m_{k}", file=mpaths[k].name)

    world = ET.SubElement(root, "worldbody")
    ET.SubElement(world, "light", pos="0.02 -0.2 0.3", dir="-0.05 0.3 -1", directional="true", diffuse="0.5 0.5 0.5")
    ET.SubElement(world, "camera", name="cutaway", pos="0.03 -0.12 0.055", xyaxes="1 0 0 0 0.4 0.92")
    ET.SubElement(world, "camera", name="zoom", pos="0.020 -0.045 0.020", xyaxes="1 0 0 0 0.5 0.87")
    if meshes:
        ET.SubElement(world, "geom", name="cab_mesh", type="mesh", mesh="m_cabinet_body", material="cab")
        ET.SubElement(world, "geom", name="bump_mesh", type="mesh", mesh="m_bump", material="bump")

    bd = ET.SubElement(world, "body", name="drawer", pos="0 0 0")
    ET.SubElement(bd, "inertial", mass=f"{mass:.6f}", pos=" ".join(f"{v:.6f}" for v in com),
                  diaginertia=" ".join(f"{v:.6e}" for v in diag))
    # the slide joint: range [0, stroke]; the LOWER LIMIT at s=0 is the panel-on-face landing (M1),
    # the closed hard stop — a PART, not a drive-off. damping 150 (snug drawer, visible pop).
    ET.SubElement(bd, "joint", name="drawer_slide", type="slide", axis="1 0 0", pos="0 0 0",
                  limited="true", range=f"0 {stroke_m:.6f}", damping="150",
                  solreflimit="0.002 1", solimplimit="0.99 0.9999 1e-5 0.5 2")
    if meshes:
        ET.SubElement(bd, "geom", name="dr_mesh", type="mesh", mesh="m_drawer_body", material="drawer")
        ET.SubElement(bd, "geom", name="clip_mesh", type="mesh", mesh="m_clip", material="clip")
    if markers:
        ET.SubElement(bd, "geom", name="mk_drawer", type="box", pos="0.030 -0.030 0.012",
                      size="0.004 0.0015 0.004", material="mk")

    eq = ET.SubElement(root, "equality")
    ET.SubElement(eq, "joint", name="latch", joint1="drawer_slide", polycoef="0 0 0 0 0", active="false",
                  solref="-1e8 -1e4", solimp="0.9999 0.99999 1e-6 0.5 2")
    act = ET.SubElement(root, "actuator")
    ET.SubElement(act, "velocity", name="drive", joint="drawer_slide", kv="600")

    xml = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
    meta = {"stroke_mm": stroke_mm, "stroke_m": stroke_m, "W_out_N": W_out,
            "pull_hold_N": round(0.5 * W_out, 2), "pull_release_N": round(1.5 * W_out, 2)}
    return xml, meta


def _crit(v):
    return tuple((k, c["value"], c["pass"]) for k, c in v["criteria"].items())


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "out"
    out.mkdir(parents=True, exist_ok=True)
    c = chain()
    W_out = c["geom"]["W_out"]; stroke_mm = c["geom"]["stroke"]

    bare_xml, meta = build(out / "ld_mesh_assets", W_out, stroke_mm, meshes=False)
    mesh_xml, meta = build(out / "ld_mesh_assets", W_out, stroke_mm, meshes=True)
    (out / "t2_ld_bare.xml").write_text(bare_xml)
    (out / "t2_ld_mesh.xml").write_text(mesh_xml)
    bare = mj.MjModel.from_xml_path(str(out / "t2_ld_bare.xml"))
    mesh = mj.MjModel.from_xml_path(str(out / "t2_ld_mesh.xml"))
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
        P._save_video(f0, meta, out / "t2_ld_mesh.mp4", view="cutaway")
        P._save_video(f0, meta, out / "t2_ld_mesh_zoom.mp4", view="zoom")
        eng = next((fr for fr in f0 if fr[6] == "hold"), f0[len(f0) // 2])
        imageio.imwrite(str(out / "engaged_closeup_ld.png"), eng[1])
    if s0:
        P._plot(s0, vm, meta, out / "t2_ld_mesh.png")

    cr = per_seed[0]["criteria"]
    result = {
        "decision_row": "D-M24-5 latched_drawer bottom-clip T5 — designed W_out, panel-on-face stop",
        "compile_hash": _hash(), "task": "latched_drawer (bottom-clip)",
        "physics_identical_bare_vs_mesh": identical,
        "closed_stop": "front panel lands on the face frame (the slide lower limit at s=0) — a PART, not a drive-off",
        "sourced_breakaway": {"W_out_N": round(W_out, 3), "chain": "inverse Bayer: L=12,b=6,undercut=1.35 → "
                              f"P={c['geom']['P']:.2f} N, W_out=P·fig18(0.30,45°)={W_out:.2f} N (DESIGNED)"},
        "criteria_old_vs_new": {
            "W_out_N": {"m23_fixture": 32.81, "bottom_clip_designed": round(W_out, 3)},
            "pull_hold_N": {"m23": 16.4, "new": meta["pull_hold_N"]},
            "pull_release_N": {"m23": 49.2, "new": meta["pull_release_N"]},
            "engage_mm": {"m23": 0.399, "new": cr["close_engages_at_closed"]["value"]},
            "hold_creep_mm": {"m23": 0.449, "new": cr["holds_at_0.5·W_out (≤ tol)"]["value"]},
            "release_mm": {"m23": 59.73, "new": cr["releases_at_1.5·W_out (opens to rail)"]["value"]},
            "note": "criteria CHANGE is expected: W_out is now DESIGNED (30.38 N) via the fit chain, not the m23 fixture (32.81 N); stroke 50 (was 60)"},
        "g9_gconv": bool(gok),
        "V-A": {"n_seeds": P.N_SEEDS, "seeds_passed": n_pass, "passed": bool(n_pass >= P.SEED_PASS),
                "criteria_seed0": cr, "per_seed": per_seed},
        "video": "t2_ld_mesh.mp4", "video_zoom": "t2_ld_mesh_zoom.mp4", "plot": "t2_ld_mesh.png",
    }
    (out / "t2_ld_mesh_verdict.json").write_text(json.dumps(result, indent=2))
    print(f"\n=== latched_drawer bottom-clip T5 ===  G-CONV {'ok' if gok else 'FAIL'}  "
          f"seeds {n_pass}/{P.N_SEEDS} => {'PASS' if n_pass >= P.SEED_PASS else 'FAIL'}")
    print(f"   DESIGNED W_out = {W_out:.2f} N (was m23 32.81) | hold {meta['pull_hold_N']} N | release {meta['pull_release_N']} N")
    print(f"   engage {cr['close_engages_at_closed']['value']} mm | hold {cr['holds_at_0.5·W_out (≤ tol)']['value']} mm | "
          f"release {cr['releases_at_1.5·W_out (opens to rail)']['value']} mm")
    print(f"   closed stop = panel-on-face-frame landing (slide lower limit s=0)")
    print("wrote", out / "t2_ld_mesh_verdict.json")


if __name__ == "__main__":
    main()
