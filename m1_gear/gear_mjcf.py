"""M1: gear-pair -> MJCF, reusing the M0 rig's FROZEN contact preset (R5). This is the R2 analog
of m0/step2mjcf: MuJoCo collides every mesh as its convex hull, so a tooth is only as good as its
collision hint. The hint here is the ladder variable — N convex WEDGES per flank (the tooth-profile
analog of m0's ring-of-wedges around a bore).

Assembly (V-B for the TEETH): each gear sits on a declared MuJoCo hinge joint about its own axis —
the SHAFT journals, a fixture (D23: fixture what the experiment does not ask about; the axes are
not under test, the meshing is). No joint couples the two gears: the ratio must EMERGE from
tooth-on-tooth contact. A velocity actuator drives the pinion shaft. Gear axes are +Z (vertical),
so gravity acts along the axis and is reacted by the hinge — no spurious gravity torque on the DoF
under test.

Collision wedge: each working flank (root->tip polyline) is split into N segments; each segment
becomes a convex prism spanning from the flank chord inward to the tooth centreline, extruded over
the face width. The prism's OUTER face is the true flank (the contact surface); N is the ladder
variable (2, 4, 6...). Mass/inertia always come from the EXACT gear mesh, never the wedges
(overlapping convex parts would inflate it) — same rule as m0.
"""

from __future__ import annotations

import json
import math
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from xml.dom import minidom

import numpy as np
import trimesh
from build123d import export_stl

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "m0"))

from gear_geom import GearSpec, build_gear, mesh_centres, tooth_flanks

# --- FROZEN preset, imported from the M0 rig so it is provably identical (R5). ---------------
from step2mjcf import DENSITY, MM, MU, SOLIMP, SOLREF  # noqa: E402

OUT = Path(__file__).parent / "out"
MESHDIR = OUT / "assets"   # STL/MJCF build intermediates — gitignored (housekeeping rider); the
#                            review artifacts (png/mp4/md/verdict-json) live directly in out/

# Mesh phase (deg) that seats the z=24 gear's tooth-space against the pinion, per profile. Found by
# the exact-B-rep / wedge clearance scan (mesh_check); baked into the gear geometry so the pair
# meshes at joint angle 0. Sign differs by profile because the flanks mirror.
MESH_PHASE = {"trapezoid": 7.5, "involute": -7.5}
BACKLASH_SEAT_DEG = 0.25  # tiny extra rotation off the drive flank so nothing penetrates at t=0


def _b123d_to_trimesh(solid, tol=0.05) -> trimesh.Trimesh:
    MESHDIR.mkdir(parents=True, exist_ok=True)
    tmp = MESHDIR / "_tmp.stl"
    export_stl(solid, str(tmp), tolerance=tol, angular_tolerance=0.2)
    m = trimesh.load(tmp, force="mesh")
    tmp.unlink()
    return m


def _rotm(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s], [s, c]])


def flank_wedges(g: GearSpec, n_wedge: int, phase_deg: float = 0.0):
    """Convex prism per flank segment, in the gear's local frame (mm, extruded 0..face_width in Z).
    Each prism = convex hull of {segment a, b on the flank} + {their projections onto the tooth
    centreline}, over the face width. N segments per flank, both flanks, all z teeth."""
    right, left = tooth_flanks(g)
    ph = math.radians(phase_deg)
    wedges = []

    def resample(poly, n):
        pts = np.array(poly)
        seg = np.linspace(0, len(pts) - 1, n + 1)
        return [tuple(pts[int(round(s))] if s == int(s) else
                      pts[int(s)] * (1 - (s - int(s))) + pts[int(s) + 1] * (s - int(s)))
                for s in seg]

    for i in range(g.z):
        c = 2 * math.pi * i / g.z + ph
        Rc = _rotm(c)
        for flank in (right, left):
            fs = resample(flank, n_wedge)
            for k in range(n_wedge):
                a, b = np.array(fs[k]), np.array(fs[k + 1])
                # centreline (tooth bisector) projections: same radius, angle 0 in local -> (r,0)
                pa = np.array([np.hypot(*a), 0.0])
                pb = np.array([np.hypot(*b), 0.0])
                quad = [a, b, pb, pa]
                quad = [Rc @ q for q in quad]                       # place at tooth c
                v2 = np.array(quad)
                verts = np.vstack([np.c_[v2, np.zeros(4)],
                                   np.c_[v2, np.full(4, g.face_width)]])
                wedges.append(trimesh.Trimesh(vertices=verts).convex_hull)
    return wedges


@dataclass
class GearPiece:
    name: str
    vis_mesh: trimesh.Trimesh          # metres
    wedges: list                       # trimesh convex prisms, metres
    center_mm: tuple
    phase_deg: float
    spec: GearSpec


def _prep(name, spec: GearSpec, n_wedge, center_mm, phase_deg) -> GearPiece:
    vis = _b123d_to_trimesh(build_gear(spec)); vis.apply_scale(MM)
    ws = [w.copy().apply_scale(MM) for w in flank_wedges(spec, n_wedge, phase_deg)]
    # bake the mesh phase into the visual mesh too, so render and collision agree at joint angle 0
    if phase_deg:
        Rz = trimesh.transformations.rotation_matrix(math.radians(phase_deg), [0, 0, 1])
        vis.apply_transform(Rz)
    return GearPiece(name, vis, ws, center_mm, phase_deg, spec)


def _inertial(body, mesh):
    mesh.density = DENSITY
    com, I = mesh.center_mass, mesh.moment_inertia
    ET.SubElement(body, "inertial", pos=" ".join(f"{v:.9f}" for v in com),
                  mass=f"{float(mesh.mass):.9f}",
                  fullinertia=" ".join(f"{v:.12f}" for v in
                                       (I[0, 0], I[1, 1], I[2, 2], I[0, 1], I[0, 2], I[1, 2])))
    return float(mesh.mass)


def build(profile="trapezoid", n_wedge=2, omega_in=6.0, tag=None, op_cd=None,
          module=2.0, face_width=8.0, seat_deg=BACKLASH_SEAT_DEG) -> tuple[Path, dict]:
    """op_cd = operating centre distance (mm). None -> ideal (rp1+rp2). A profile that interferes at
    ideal centre (the trapezoidal approximation does — its straight flank is fatter than the
    conjugate involute in the dedendum) needs op_cd > ideal to seat with clearance; the extra is a
    recorded cost of the approximation, and it inflates the realised backlash. `module` scales the
    whole tooth (R2b mitigation probe: a larger module is a gentler contact geometry)."""
    tag = tag or f"{profile}_n{n_wedge}"
    MESHDIR.mkdir(parents=True, exist_ok=True)
    pinion = GearSpec(z=12, profile=profile, m=module, face_width=face_width)
    gear = GearSpec(z=24, profile=profile, m=module, face_width=face_width)
    cd_ideal = mesh_centres(pinion, gear)
    cd = op_cd if op_cd is not None else cd_ideal
    phase = MESH_PHASE[profile] + seat_deg

    P = _prep("pinion", pinion, n_wedge, (0.0, 0.0), 0.0)
    G = _prep("gear", gear, n_wedge, (cd, 0.0), phase)

    root = ET.Element("mujoco", model=f"m1_gear_{tag}")
    ET.SubElement(root, "compiler", angle="radian", meshdir="assets", autolimits="true")
    # FROZEN option block — identical to m0 (R5): dt, integrator, cone, impratio.
    ET.SubElement(root, "option", timestep="0.0005", integrator="implicitfast",
                  cone="elliptic", impratio="10")
    vis = ET.SubElement(root, "visual")
    ET.SubElement(vis, "headlight", ambient="0.5 0.5 0.5", diffuse="0.6 0.6 0.6",
                  specular="0.2 0.2 0.2")
    ET.SubElement(vis, "global", offwidth="1280", offheight="960", azimuth="90", elevation="-70")
    ET.SubElement(vis, "rgba", haze="0.9 0.93 0.96 1")

    dflt = ET.SubElement(root, "default")
    ET.SubElement(dflt, "geom", solref=f"{SOLREF[0]} {SOLREF[1]}",
                  solimp=f"{SOLIMP[0]} {SOLIMP[1]} {SOLIMP[2]}",
                  friction=f"{MU} 0.005 0.0001", condim="4", density="0")

    asset = ET.SubElement(root, "asset")
    ET.SubElement(asset, "material", name="pinion", rgba="0.35 0.65 0.85 1")
    ET.SubElement(asset, "material", name="gear", rgba="0.95 0.62 0.25 1")

    world = ET.SubElement(root, "worldbody")
    ET.SubElement(world, "light", pos="0.04 -0.04 0.25", dir="0 0 -1", directional="true",
                  diffuse="0.6 0.6 0.6")
    # Top-down camera (looks along -Z at the meshing plane) + a mesh-zone close-up at the pitch point.
    ET.SubElement(world, "camera", name="top", pos=f"{cd/2*MM:.5f} 0 0.16", xyaxes="1 0 0 0 1 0")
    ET.SubElement(world, "camera", name="mesh", pos=f"{cd*MM:.5f} {-0.02:.5f} 0.06",
                  xyaxes="1 0 0 0 0.6 0.8")

    masses, meta_pieces = {}, {}
    for pc, mat in ((P, "pinion"), (G, "gear")):
        body = ET.SubElement(world, "body", name=pc.name,
                             pos=f"{pc.center_mm[0]*MM:.9f} {pc.center_mm[1]*MM:.9f} 0")
        ET.SubElement(body, "joint", name=f"{pc.name}_shaft", type="hinge", axis="0 0 1",
                      pos="0 0 0", damping="1e-6")
        masses[pc.name] = _inertial(body, pc.vis_mesh)
        vf = MESHDIR / f"{tag}_{pc.name}_vis.stl"; pc.vis_mesh.export(vf)
        ET.SubElement(asset, "mesh", name=f"{pc.name}_vis", file=vf.name)
        ET.SubElement(body, "geom", name=f"{pc.name}_vis", type="mesh", mesh=f"{pc.name}_vis",
                      contype="0", conaffinity="0", group="2", material=mat)
        for j, w in enumerate(pc.wedges):
            wf = MESHDIR / f"{tag}_{pc.name}_w{j}.stl"; w.export(wf)
            ET.SubElement(asset, "mesh", name=f"{pc.name}_w{j}", file=wf.name)
            ET.SubElement(body, "geom", name=f"{pc.name}_w{j}", type="mesh", mesh=f"{pc.name}_w{j}",
                          group="3", material=mat)
        meta_pieces[pc.name] = {"n_wedge_geoms": len(pc.wedges), "center_mm": list(pc.center_mm),
                                "phase_deg": pc.phase_deg, "z": pc.spec.z}

    # velocity actuator on the pinion shaft (the drive). kv sized for a stiff velocity servo.
    act = ET.SubElement(root, "actuator")
    ET.SubElement(act, "velocity", name="drive", joint="pinion_shaft", kv="0.05")

    xml = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
    out = OUT / f"gear_{tag}.xml"; out.write_text(xml)
    # realised backlash from the operating centre distance: a centre increase of Δ opens the
    # circumferential backlash by 2·Δ·tan(α) on top of the tooth-thickness backlash (0.20 designed).
    op_backlash = pinion.backlash + 2 * (cd - cd_ideal) * math.tan(math.radians(pinion.pressure_angle_deg))
    meta = {"tag": tag, "profile": profile, "n_wedge": n_wedge, "omega_in": omega_in,
            "center_distance_mm": cd, "center_distance_ideal_mm": cd_ideal,
            "backlash_realised_mm": round(op_backlash, 3),
            "module": pinion.m, "z1": pinion.z, "z2": gear.z,
            "ratio_z1_z2": pinion.z / gear.z, "pitch_r1_mm": pinion.rp, "pitch_r2_mm": gear.rp,
            "backlash_design_mm": pinion.backlash, "face_width_mm": pinion.face_width,
            "pressure_angle_deg": pinion.pressure_angle_deg, "mesh_phase_deg": phase,
            "masses_kg": masses, "pieces": meta_pieces,
            "contact_preset": {"solref": SOLREF, "solimp": SOLIMP, "friction_mu": MU,
                               "timestep": 0.0005, "integrator": "implicitfast",
                               "cone": "elliptic", "impratio": 10}}
    (OUT / f"gear_{tag}_meta.json").write_text(json.dumps(meta, indent=2))
    print(f"[{tag}] wrote {out.name}")
    for n in ("pinion", "gear"):
        print(f"    {n:7s} z={meta_pieces[n]['z']:2d}  {meta_pieces[n]['n_wedge_geoms']:3d} wedge "
              f"geoms  mass {masses[n]*1000:6.2f} g")
    return out, meta


if __name__ == "__main__":
    prof = sys.argv[1] if len(sys.argv) > 1 else "trapezoid"
    nw = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    build(prof, nw)
