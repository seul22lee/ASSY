"""m17 FILE 1 — R2b SDF probe, part 1: reproduce R2b on the wedge collider, then DOCUMENT that the
only D21-legal SDF option (an SDF over our OWN carved mesh) is not shippable with the pip wheel.

(A) BASELINE: the validated involute wedge pair (m1_gear.build) at the frozen dt and at dt/25 — this
    must reproduce R2b (16 orders of magnitude of contact force between the two).
(B) OWN-MESH SDF: emit an MJCF whose collider is the EXACT gear mesh as ONE geom type="sdf" (no
    wedges), via the mesh-import SDF plugin `mujoco.sdf.sdflib`. This is the ONLY SDF form D21 allows
    (our compiled geometry, not an analytic primitive). It FAILS TO COMPILE — the pip wheel ships no
    sdflib — and that failure IS finding F1. We keep (B) as executable documentation, never "fix" it.

  export MUJOCO_GL=disable ; ./bin/py m17_gear_vb/sdf_probe.py
"""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

import mujoco

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "m1_gear"))
sys.path.insert(0, str(ROOT / "m0"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import gear_mjcf                                   # noqa: E402
from gear_geom import GearSpec                     # noqa: E402
from step2mjcf import MU, SOLIMP, SOLREF           # noqa: E402  (FROZEN preset, R5)
from _run import FINE, FROZEN, drive_measure       # noqa: E402

OUT = Path(__file__).parent / "out"
# Keep every build artifact inside m17 (append-only: do not write into m1_gear).
gear_mjcf.OUT = OUT
gear_mjcf.MESHDIR = OUT / "assets"


def build_sdf_mjcf(tag="r2b_ownmesh_sdf") -> Path:
    """Emit the involute pair as SDF colliders over our OWN exact meshes (D21-legal). Reuses
    gear_mjcf._prep for the phase-baked, mm->m visual mesh (byte-for-byte the baseline geometry) and
    _inertial for mass. Declares mujoco.sdf.sdflib — which the pip wheel does not ship (F1)."""
    gear_mjcf.MESHDIR.mkdir(parents=True, exist_ok=True)
    pinion = GearSpec(z=12, profile="involute", m=2.0, face_width=8.0)
    gear = GearSpec(z=24, profile="involute", m=2.0, face_width=8.0)
    phase = gear_mjcf.MESH_PHASE["involute"] + gear_mjcf.BACKLASH_SEAT_DEG
    P = gear_mjcf._prep("pinion", pinion, 4, (0.0, 0.0), 0.0)
    G = gear_mjcf._prep("gear", gear, 4, (36.0, 0.0), phase)

    root = ET.Element("mujoco", model=f"m17_{tag}")
    ET.SubElement(root, "compiler", angle="radian", meshdir="assets", autolimits="true")
    # FROZEN option block (R5) + the SDF gradient-descent iteration counts (per task).
    ET.SubElement(root, "option", timestep="0.0005", integrator="implicitfast", cone="elliptic",
                  impratio="10", sdf_iterations="10", sdf_initpoints="40", ccd_iterations="50")
    # The D21-legal SDF: an imported-mesh plugin over OUR mesh. Absent from the pip wheel -> F1.
    ext = ET.SubElement(root, "extension")
    plug = ET.SubElement(ext, "plugin", plugin="mujoco.sdf.sdflib")
    for nm in ("sdf_pinion", "sdf_gear"):
        ET.SubElement(plug, "instance", name=nm)

    dflt = ET.SubElement(root, "default")
    ET.SubElement(dflt, "geom", solref=f"{SOLREF[0]} {SOLREF[1]}",
                  solimp=f"{SOLIMP[0]} {SOLIMP[1]} {SOLIMP[2]}",
                  friction=f"{MU} 0.005 0.0001", condim="4", density="0")

    asset = ET.SubElement(root, "asset")
    world = ET.SubElement(root, "worldbody")
    for pc, inst, cd in ((P, "sdf_pinion", 0.0), (G, "sdf_gear", 36.0)):
        mf = gear_mjcf.MESHDIR / f"{tag}_{pc.name}.stl"
        pc.vis_mesh.export(mf)                              # our EXACT carved mesh (metres)
        m = ET.SubElement(asset, "mesh", name=f"{pc.name}_mesh", file=mf.name)
        ET.SubElement(m, "plugin", instance=inst)          # tag the mesh asset with its SDF instance
        body = ET.SubElement(world, "body", name=pc.name, pos=f"{cd*gear_mjcf.MM:.9f} 0 0")
        ET.SubElement(body, "joint", name=f"{pc.name}_shaft", type="hinge", axis="0 0 1",
                      pos="0 0 0", damping="1e-6")
        gear_mjcf._inertial(body, pc.vis_mesh)             # mass/inertia from the EXACT mesh
        g = ET.SubElement(body, "geom", name=f"{pc.name}_sdf", type="sdf", mesh=f"{pc.name}_mesh")
        ET.SubElement(g, "plugin", instance=inst)
    act = ET.SubElement(root, "actuator")
    ET.SubElement(act, "velocity", name="drive", joint="pinion_shaft", kv="0.05")

    xml = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
    out = OUT / f"{tag}.xml"; out.write_text(xml)
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    verdict = {"probe": "m17 sdf_probe (FILE 1)", "conditions": {}}

    # --- (A) baseline wedge, frozen dt and dt/25 --------------------------------------------------
    xml, meta = gear_mjcf.build("involute", 4, tag="r2b_baseline_wedge", op_cd=36.0)
    for label, dt in (("wedge_frozen_5e-4", FROZEN), ("wedge_dt25_2e-5", FINE)):
        model = mujoco.MjModel.from_xml_path(str(xml))
        r = drive_measure(model, dt)
        r.pop("t"); r.pop("force"); r.pop("wp")            # keep the verdict json small
        verdict["conditions"][label] = r
        print(f"  {label:20s} peak {r['peak_force_N']:.2e} N  diverged={r['diverged']} "
              f"t={r['t_final']}  omega_pin={r['omega_pinion']}  ratio={r['ratio']}")

    # --- (B) own-mesh SDF: expected COMPILE FAILURE (F1) -----------------------------------------
    sdf_xml = build_sdf_mjcf()
    f1 = {"emitted_xml": sdf_xml.name, "compiles": None, "error": None}
    try:
        mujoco.MjModel.from_xml_path(str(sdf_xml))
        f1["compiles"] = True
        print("  own-mesh SDF: UNEXPECTEDLY COMPILED (sdflib present in this build?)")
    except Exception as e:
        f1["compiles"] = False
        f1["error"] = f"{type(e).__name__}: {str(e)[:240]}"
        print(f"  own-mesh SDF (mujoco.sdf.sdflib): FAILED TO COMPILE (F1) -> {f1['error']}")
    verdict["F1_ownmesh_sdf"] = f1

    (OUT / "sdf_probe_verdict.json").write_text(json.dumps(verdict, indent=2))
    print("wrote out/sdf_probe_verdict.json")


if __name__ == "__main__":
    main()
