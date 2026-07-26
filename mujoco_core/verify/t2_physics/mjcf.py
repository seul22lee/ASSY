"""Stage ⑨ (Tier2) — compiled assembly → MJCF. The generic form of m0/step2mjcf: instead of a
hand-built HingeBox manifest, it takes the PIPELINE's compiled parts (⑥ carve output), the cards'
collision hints, the hinge axis (from the binding), and the D23 base (from Piece.is_base), and emits
an MJCF that MuJoCo can run. The FROZEN contact preset is imported from m0 so it is provably
identical across every experiment (R5).

Two modes (spec §6.1), both proven on M0:
  V-A  the hinge axis is a declared MuJoCo hinge joint on the mover; the pin is visual-only.
  V-B  contact-only: the base is welded (D23), the mover + pin are free bodies, and the pin/bore
       DoF must EMERGE from the card's ring-of-wedges collision hint (the M0 R1 result).
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

import numpy as np
import trimesh
from build123d import export_stl

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "m0"))
from step2mjcf import DENSITY, MM, MU, SOLIMP, SOLREF  # FROZEN preset (R5)  # noqa: E402

MATS = {"base": "0.35 0.65 0.85 1", "mover": "0.95 0.62 0.25 1", "hardware": "0.8 0.8 0.85 1",
        "other": "0.6 0.75 0.6 1"}


def _to_trimesh(solid, out_stl: Path, tol=0.05) -> trimesh.Trimesh:
    export_stl(solid, str(out_stl), tolerance=tol, angular_tolerance=0.2)
    m = trimesh.load(out_stl, force="mesh"); m.apply_scale(MM); m.export(out_stl)  # rewrite in metres
    return m


def _inertial(body, mesh):
    mesh.density = DENSITY
    com, I = mesh.center_mass, mesh.moment_inertia
    ET.SubElement(body, "inertial", pos=" ".join(f"{v:.9f}" for v in com),
                  mass=f"{float(mesh.mass):.9f}",
                  fullinertia=" ".join(f"{v:.12f}" for v in
                                       (I[0, 0], I[1, 1], I[2, 2], I[0, 1], I[0, 2], I[1, 2])))
    return float(mesh.mass)


def _ring_world(prim, loc_pts):
    """Place a canonical ring-of-wedges primitive (axis = local +X) into world by the axis frame.
    loc_pts = (origin, xdir, ydir, zdir) columns of the axis frame (metres)."""
    o, X, Y, Z = loc_pts
    R = np.column_stack([X, Y, Z])
    pos = o + R @ (np.array(prim["pos"]) * MM)
    # euler about local X only (ring wedges) — compose into the world frame via R
    return pos, R, prim


class UnsourcedCollisionPrim(ValueError):
    """A collision primitive that traces to no declared source. **This is a BUILD ERROR, not a
    warning** (D-M8-4).

    The rule exists because m8 shipped a "designed open-stop" that was pure fabrication: a prim
    conjured in the physics driver with no solid in the compiled STEP and no entity in the IR. It
    made a failing V-B go green, and nothing in the toolchain objected. Physics may only ever
    simulate geometry the design actually declares — so every collision geom must name a source that
    resolves to a declared IR entity:

        card:<card_ref>@<inst_id>   an element/feature's own collision_hint (the instance must exist
                                    in the plan, with that card_ref)
        template:<template_ref>     host geometry (some piece in the plan must use that template)
        fixture:D23                 the base-weld boundary condition

    A prim with no `source`, or a source naming an entity the plan does not declare, cannot be
    emitted. Inventing geometry now requires forging a provenance that the IR would have to back —
    a deliberate act, not an oversight.
    """


def declared_sources(plan) -> set[str]:
    """Every collision-geom source this plan legitimately authorizes (D-M8-4)."""
    src = {"fixture:D23"}
    for e in getattr(plan, "elements", []):
        src.add(f"card:{e.card_ref}@{e.id}")
    for f in getattr(plan, "features", []):
        src.add(f"card:{f.card_ref}@{f.id}")
    for p in getattr(plan, "pieces", []):
        if getattr(p, "template_ref", None):
            src.add(f"template:{p.template_ref}")
    return src


def assert_sourced(hints: dict, plan) -> None:
    """Refuse any collision geom that does not trace to a declared source. Called by build_mjcf
    before a single geom is emitted — the mechanized form of D-M8-4."""
    ok = declared_sources(plan)
    for pid, prims in (hints or {}).items():
        for i, prim in enumerate(prims or []):
            s = prim.get("source")
            where = f"{pid}[{i}] ({prim.get('type', '?')}, role_hint={prim.get('role_hint')})"
            if not s:
                raise UnsourcedCollisionPrim(
                    f"collision geom {where} declares NO source. Every collision geom must trace to "
                    f"a card collision_hint, a template hint, or the D23 fixture (D-M8-4). A prim "
                    f"with no declared source is geometry the design does not contain.")
            if s not in ok:
                raise UnsourcedCollisionPrim(
                    f"collision geom {where} claims source '{s}', which resolves to NO declared IR "
                    f"entity (D-M8-4). Authorized sources for this plan: {sorted(ok)}. Physics may "
                    f"only simulate geometry the IR declares.")


def build_mjcf(parts: dict, hints: dict, axis: dict, base_pid: str, mover_pid: str,
               pin_pid: str, mode: str, meshdir: Path, roles: dict, tag: str,
               tip_point=None, latch_point=None, plan=None, joint_kind="hinge",
               slide_friction_N=None):
    """parts: {pid: build123d Solid}; hints: {pid: [collision prim dicts]}; axis: {point,dir} in mm;
    roles: {pid: 'base'|'mover'|'hardware'|'other'}. Emits MJCF for `mode` ('V-A'|'V-B')."""
    meshdir.mkdir(parents=True, exist_ok=True)
    ax_pt = np.array(axis["point"], float) * MM
    ax_dir = np.array(axis["dir"], float); ax_dir /= np.linalg.norm(ax_dir)

    root = ET.Element("mujoco", model=f"t2_{tag}_{mode}")
    # D-M8-4, mechanized: nothing is emitted until every collision geom names a declared source.
    # `plan` is required — provenance cannot be checked against a plan we were not given.
    if plan is None:
        raise UnsourcedCollisionPrim(
            "build_mjcf requires `plan`: collision-geom provenance cannot be verified without the "
            "IR to check against (D-M8-4).")
    assert_sourced(hints, plan)

    ET.SubElement(root, "compiler", angle="radian", meshdir=meshdir.name, autolimits="true")
    ET.SubElement(root, "option", timestep="0.0005", integrator="implicitfast",
                  cone="elliptic", impratio="10")   # FROZEN (R5)
    vis = ET.SubElement(root, "visual")
    ET.SubElement(vis, "headlight", ambient="0.5 0.5 0.5", diffuse="0.6 0.6 0.6", specular="0.2 0.2 0.2")
    ET.SubElement(vis, "global", offwidth="1280", offheight="960", azimuth="140", elevation="-20")
    dflt = ET.SubElement(root, "default")
    ET.SubElement(dflt, "geom", solref=f"{SOLREF[0]} {SOLREF[1]}",
                  solimp=f"{SOLIMP[0]} {SOLIMP[1]} {SOLIMP[2]}",
                  friction=f"{MU} 0.005 0.0001", condim="4", density="0")
    asset = ET.SubElement(root, "asset")
    for r, rgba in MATS.items():
        ET.SubElement(asset, "material", name=r, rgba=rgba)
    world = ET.SubElement(root, "worldbody")
    ET.SubElement(world, "light", pos="0.15 -0.25 0.4", dir="-0.3 0.5 -1", directional="true",
                  diffuse="0.5 0.5 0.5")
    ET.SubElement(world, "camera", name="iso", pos="0.125 -0.125 0.115",
                  xyaxes="0.707 0.707 0 -0.38 0.38 0.84")

    masses = {}
    for pid, solid in parts.items():
        role = roles.get(pid, "other")
        body = ET.SubElement(world, "body", name=pid, pos="0 0 0")
        # joints per mode / role (D23: base welded in V-B; V-A welds base, hinges the mover)
        if mode == "V-A":
            if role == "mover":
                if joint_kind == "slide":
                    # P-SLIDE (§6.3): a declared PRISMATIC joint along the travel axis. V-A REQUIRED.
                    # Like the hinge's declared joint, this supplies constraints the geometry may not
                    # (retention against off-axis/lift, AND the travel-limit stop) — so V-B
                    # (contact-only) is the real test. Range = [−eps, stroke]: the joint models the
                    # physical stop the T-rail's stop-tab provides in V-B; without a limit a prismatic
                    # joint just accelerates forever under a constant push.
                    strk_m = float(axis.get("stroke_mm", 60.0)) * MM
                    # frictionloss = the slide's real Coulomb friction, PHYSICALLY SOURCED by the
                    # caller as μ·N (PETG.mu_friction × the carriage weight) — the same μ the frozen
                    # contact preset gives V-B, so V-A models what V-B feels. A material property, not
                    # an invented number (the m8 lesson: a value chosen to pass a gate is a fabrication).
                    fl = slide_friction_N if slide_friction_N is not None else 0.0
                    ET.SubElement(body, "joint", name="slide", type="slide", axis=_v(ax_dir),
                                  pos=_v(ax_pt), damping="0.05", frictionloss=f"{fl:.5f}",
                                  range=f"-0.002 {strk_m + 0.002:.5f}", limited="true")
                else:
                    ET.SubElement(body, "joint", name="hinge", type="hinge", axis=_v(ax_dir),
                                  pos=_v(ax_pt), damping="0.002", range="-0.02 1.92", limited="true")
            # base + hardware(pin): welded / visual-only (joint replaces the pin in V-A)
        else:  # V-B
            if role == "base":
                pass  # welded to world (D23 fixture)
            else:
                ET.SubElement(body, "freejoint", name=f"{pid}_free")
        vf = meshdir / f"{tag}_{pid}_vis.stl"
        mesh = _to_trimesh(solid, vf)
        masses[pid] = _inertial(body, mesh)
        ET.SubElement(asset, "mesh", name=f"{pid}_vis", file=vf.name)
        ET.SubElement(body, "geom", name=f"{pid}_vis", type="mesh", mesh=f"{pid}_vis",
                      contype="0", conaffinity="0", group="2", material=role)
        # collision geoms. Two provenances (D-ONT-11): template SEATING prims (frame='world' — the
        # lid-on-box load path) and card MECHANISM prims (the ring-of-wedges + pin, frame='axis').
        # In V-A the declared hinge joint IS the mechanism, so its collision approximation is not
        # only redundant but JAMS the joint (a convex wedge ring is not clearance-perfect) — emit
        # only the world-frame seating prims. In V-B the DoF emerges FROM the mechanism prims, so
        # emit everything. The pin (hardware) is visual-only in V-A likewise.
        if mode == "V-A" and role == "hardware":
            continue
        for i, prim in enumerate(hints.get(pid, [])):
            if mode == "V-A" and prim.get("frame") != "world":
                continue
            if prim.get("modes") and mode not in prim["modes"]:   # e.g. the V-B-only open-stop
                continue
            _emit_prim(body, prim, ax_pt, ax_dir, f"{pid}_c{i}", role)

    # sites: the follower-force point (mover free edge), the latch point (release tracking), and the
    # V-B pin-drift references (M0: pin centre vs the base's axis).
    mb = world.find(f"body[@name='{mover_pid}']")
    if tip_point is not None:
        ET.SubElement(mb, "site", name="tip", pos=_v(np.array(tip_point) * MM), size="0.002",
                      rgba="1 0.2 0.2 1")
    if latch_point is not None:
        ET.SubElement(mb, "site", name="latch", pos=_v(np.array(latch_point) * MM), size="0.002",
                      rgba="0.2 0.8 0.2 1")
    if mode == "V-B":
        ET.SubElement(world.find(f"body[@name='{base_pid}']"), "site", name="axis_ref",
                      pos=_v(ax_pt), size="0.0012", rgba="0.1 0.9 0.2 1")
        ET.SubElement(world.find(f"body[@name='{pin_pid}']"), "site", name="pin_center",
                      pos=_v(ax_pt), size="0.0012", rgba="0.9 0.1 0.9 1")

    xml = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
    meta = {"mode": mode, "masses_kg": masses, "axis_m": {"point": list(ax_pt), "dir": list(ax_dir)},
            "base": base_pid, "mover": mover_pid, "pin": pin_pid,
            "tip_point_mm": list(tip_point) if tip_point is not None else None,
            "contact_preset": {"solref": SOLREF, "solimp": SOLIMP, "friction_mu": MU,
                               "timestep": 0.0005, "frozen": True}}
    return xml, meta


# Two contact classes so convex-proxy artefacts between the MECHANISM (ring-of-wedges + pin) and
# the SEATING load path (walls, lid panel, floor) never grind. A geom collides with another iff
# (contype & other.conaffinity) is nonzero, so same-class geoms collide and cross-class do not:
#   seat  (1): lid-on-box seating + floor — the load path
#   mech  (2): pin ↔ bore ring-of-wedges — the rotational DoF
# The pin/bore contact and the seating both work; the box-knuckle-vs-lid-panel and lid-knuckle-vs-
# rear-wall grazes (which jammed the sweep at ~26°) are suppressed as the proxy artefacts they are.
CCLASS = {"seat": (1, 1), "mech": (2, 2)}


def _cclass(prim):
    return "mech" if (prim.get("owner") or prim.get("cclass") == "mech") else "seat"


def _emit_prim(body, prim, ax_pt, ax_dir, name, role):
    """Emit one collision primitive. `frame='world'` prims (template seating boxes, the pin) are
    already in the piece frame → emitted as-is. Ring-of-wedge boxes (`frame='axis'`, the default for
    card hints) are canonical about local +X → placed by the world axis frame. Each geom is assigned
    a contact class (seat|mech) so cross-class convex-proxy artefacts do not jam the sweep."""
    ct, ca = CCLASS[_cclass(prim)]
    if prim.get("frame") == "world":
        attrs = {"name": name, "type": prim["type"], "pos": _v(np.array(prim["pos"]) * MM),
                 "size": _v(np.array(prim["size"]) * MM), "group": "3", "material": role,
                 "contype": str(ct), "conaffinity": str(ca)}
        if "euler_world" in prim:      # a world-oriented prim (e.g. the pin cylinder along the axis)
            attrs["euler"] = _v(np.deg2rad(np.array(prim["euler_world"])))
        ET.SubElement(body, "geom", **attrs)
        return
    # axis frame: X = ax_dir; Y,Z arbitrary orthonormal
    X = ax_dir
    up = np.array([0, 0, 1.0]) if abs(X[2]) < 0.9 else np.array([0, 1.0, 0])
    Y = np.cross(up, X); Y /= np.linalg.norm(Y); Z = np.cross(X, Y)
    R = np.column_stack([X, Y, Z])
    pos = ax_pt + R @ (np.array(prim["pos"]) * MM)
    attrs = {"name": name, "type": prim["type"], "pos": _v(pos),
             "size": _v(np.array(prim["size"]) * MM), "group": "3", "material": role,
             "contype": str(ct), "conaffinity": str(ca)}
    if "euler" in prim:
        # local euler about X composed with the axis frame → use a rotation matrix via zaxis/xyaxes
        from scipy.spatial.transform import Rotation as SR
        Rloc = SR.from_euler("xyz", prim["euler"]).as_matrix()
        Rw = R @ Rloc
        q = SR.from_matrix(Rw).as_quat()  # x,y,z,w
        attrs["quat"] = f"{q[3]:.6f} {q[0]:.6f} {q[1]:.6f} {q[2]:.6f}"
    ET.SubElement(body, "geom", **attrs)


def _v(a):
    return " ".join(f"{float(x):.9f}" for x in a)
