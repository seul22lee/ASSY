"""m17 FILE 2 — R2b SDF FORMULATION ORACLE.

D21 FORBIDS the analytic `mujoco.sdf.gear` primitive as a MechSynth collider (our philosophy is
compiled geometry, not library primitives). We use it here ONLY as an ORACLE to answer one question
that F1 blocks us from answering with our own mesh: "if the collider were a perfect zero-facet SDF,
would R2b go away at the frozen dt?" It is NEVER a deliverable — no card, no compile path, no preset
touches it. The answer (see REVIEW F2/F3): NO — the exact analytic SDF gear still blows up at the
frozen dt under both rigid and soft contact; only dt/25 avoids divergence. So SDF removes the facet
make/break but NOT the small-dt requirement.

  export MUJOCO_GL=disable ; ./bin/py m17_gear_vb/sdf_formulation_probe.py
"""

from __future__ import annotations

import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "m0"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from step2mjcf import MU, SOLIMP, SOLREF           # noqa: E402  FROZEN preset (R5)
from _run import FINE, FROZEN, drive_measure       # noqa: E402

OUT = Path(__file__).parent / "out"

MODULE, Z1, Z2, FACE = 2e-3, 12, 24, 8e-3          # metres
D1, D2 = MODULE * Z1, MODULE * Z2                  # pitch diameters (task: D = module*teeth)
CD = (D1 + D2) / 2.0                               # 0.036 m
# Tooth-profile alpha (config key "alpha"). This is an ORACLE parameter, NOT a MechSynth quantity;
# 0.25 is chosen so the analytic teeth form a proper meshing regime at CD (a dip to a few contacts,
# 20+ elsewhere) rather than grazing — matching the task's landscape (alpha_gear~4.5 -> ncon0~3).
ALPHA_PROFILE = 0.25
INNER = 6e-3
# hand-set inertials (task): symmetric about the z axis, so seating rotation leaves them invariant.
INERTIAL = {"pinion": (0.00434, "1.6e-7 1.6e-7 3.1e-7"),
            "gear":   (0.01793, "2.6e-6 2.6e-6 5.2e-6")}
# soft-contact test params (NOT a preset change — a local softening, per task)
SOFT = dict(solref="0.01 1", solimp=".95 .99 .0001", friction="0.2 0.005 0.0001")


def build_oracle(alpha_gear_deg: float, soft: bool) -> Path:
    """Two gears on hinge journals with analytic SDF gear colliders; gear seated by alpha_gear_deg
    (body euler about z). soft=False -> FROZEN R5 contact; soft=True -> the softened test params."""
    root = ET.Element("mujoco", model="m17_sdf_oracle")
    ET.SubElement(root, "compiler", angle="radian", autolimits="true")
    ET.SubElement(root, "option", timestep="0.0005", integrator="implicitfast",
                  cone="elliptic", impratio="10")
    ext = ET.SubElement(root, "extension")
    plug = ET.SubElement(ext, "plugin", plugin="mujoco.sdf.gear")
    for nm, teeth, dia in (("pinion_sdf", Z1, D1), ("gear_sdf", Z2, D2)):
        inst = ET.SubElement(plug, "instance", name=nm)
        for k, v in (("alpha", ALPHA_PROFILE), ("diameter", dia), ("teeth", teeth),
                     ("thickness", FACE), ("innerdiameter", INNER)):   # keys EXACT; it is "thickness"
            ET.SubElement(inst, "config", key=k, value=f"{v}")

    dflt = ET.SubElement(root, "default")
    if soft:
        ET.SubElement(dflt, "geom", condim="4", **SOFT)
    else:
        ET.SubElement(dflt, "geom", condim="4", solref=f"{SOLREF[0]} {SOLREF[1]}",
                      solimp=f"{SOLIMP[0]} {SOLIMP[1]} {SOLIMP[2]}",
                      friction=f"{MU} 0.005 0.0001")

    asset = ET.SubElement(root, "asset")
    for nm in ("pinion", "gear"):
        m = ET.SubElement(asset, "mesh", name=f"{nm}_mesh")
        ET.SubElement(m, "plugin", instance=f"{nm}_sdf")

    world = ET.SubElement(root, "worldbody")
    ET.SubElement(world, "light", pos="0 0 0.2", dir="0 0 -1", directional="true")
    for nm, pos, euler in (("pinion", "0 0 0", "0 0 0"),
                           ("gear", f"{CD:.6f} 0 0", f"0 0 {math.radians(alpha_gear_deg):.6f}")):
        body = ET.SubElement(world, "body", name=nm, pos=pos, euler=euler)
        ET.SubElement(body, "joint", name=f"{nm}_shaft", type="hinge", axis="0 0 1", damping="1e-6")
        mass, diag = INERTIAL[nm]
        ET.SubElement(body, "inertial", pos="0 0 0", mass=f"{mass}", diaginertia=diag)
        g = ET.SubElement(body, "geom", name=f"{nm}_g", type="sdf", mesh=f"{nm}_mesh")
        ET.SubElement(g, "plugin", instance=f"{nm}_sdf")
    act = ET.SubElement(root, "actuator")
    ET.SubElement(act, "velocity", name="drive", joint="pinion_shaft", kv="0.05")

    xml = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
    out = OUT / f"sdf_oracle_{'soft' if soft else 'rigid'}_a{alpha_gear_deg:g}.xml"
    out.write_text(xml)
    return out


def seat_scan():
    """The pair interpenetrates at t=0 unless phased. Scan the gear seating rotation and pick the
    seat with the FEWEST contacts that is still a PROPER MESH — ncon0 >= 2. (Excluding ncon0 in {0,1}
    is deliberate: 0 = teeth not touching, 1 = a grazing kiss; neither exercises the tooth-on-tooth
    contact R2b is about. ~20+ = tooth-on-tooth OVERLAP -> instant divergence.) First occurrence of
    the minimum wins, for determinism. Scanned at 0.1 deg so the shallow proper-mesh dip is resolved."""
    scan = []
    for a in np.arange(0.0, 8.0001, 0.1):
        model = mujoco.MjModel.from_xml_path(str(build_oracle(float(a), soft=False)))
        d = mujoco.MjData(model)
        mujoco.mj_forward(model, d)
        scan.append({"alpha_gear_deg": round(float(a), 2), "ncon0": int(d.ncon)})
    proper = [s for s in scan if s["ncon0"] >= 2]
    best = min(proper, key=lambda s: (s["ncon0"], s["alpha_gear_deg"])) if proper else \
        min(scan, key=lambda s: s["ncon0"])
    return best, scan


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print("SDF gear (analytic ORACLE — D21-forbidden as a collider; oracle use only)")
    best, scan = seat_scan()
    alpha = best["alpha_gear_deg"]
    print(f"  seat scan: min contacts at alpha_gear={alpha} deg (ncon0={best['ncon0']}); "
          f"range {min(s['ncon0'] for s in scan)}..{max(s['ncon0'] for s in scan)}")

    verdict = {"probe": "m17 sdf_formulation_probe (FILE 2)",
               "collider": "mujoco.sdf.gear (analytic ORACLE, D21-forbidden as deliverable)",
               "geometry": {"module_m": MODULE, "z1": Z1, "z2": Z2, "CD_m": CD, "face_m": FACE},
               "seat_scan": scan, "chosen_alpha_gear_deg": alpha, "conditions": {}}

    runs = [("sdf_frozen_rigid", False, FROZEN), ("sdf_frozen_soft", True, FROZEN),
            ("sdf_dt25_soft", True, FINE)]
    for label, soft, dt in runs:
        xml = build_oracle(alpha, soft=soft)
        model = mujoco.MjModel.from_xml_path(str(xml))
        r = drive_measure(model, dt)
        r.pop("t"); r.pop("force"); r.pop("wp")
        verdict["conditions"][label] = r
        print(f"  {label:18s} peak {r['peak_force_N']:.2e} N  diverged={r['diverged']} "
              f"t={r['t_final']}  ncon0={r['ncon0']}  ratio={r['ratio']}")

    (OUT / "sdf_formulation_verdict.json").write_text(json.dumps(verdict, indent=2))
    print("wrote out/sdf_formulation_verdict.json")


if __name__ == "__main__":
    main()
