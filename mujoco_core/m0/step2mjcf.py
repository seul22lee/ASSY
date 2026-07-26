"""M0: STEP -> MJCF. This is risk R1 (spec 11), the reason M0 exists.

The hazard is specific. MuJoCo treats every mesh geom as its *convex hull*, so a naive
STEP->mesh->MJCF path silently fills in exactly the features a mechanism is made of: the
box's cavity closes up, and the knuckle's bore closes around the pin. The mechanism becomes
a brick, the sim runs happily, and reports nonsense. Collision geometry is therefore the
whole ballgame, and spec 6.2 gives the priority order we follow:

    (a) primitive substitution   -- the card knows its own shape; a bore is a cylinder pair,
                                    a wall is a box. Exact, cheap, stable.
    (b) CoACD convex decomposition -- general fallback for anything without a hint.
    (c) MuJoCo SDF               -- not needed yet; noted for gears (spec 6.2).

Visual geoms always use the full-fidelity tessellation, so the render shows the true part
while the solver sees the approximation. The overlay PNG (spec 6.2, mandatory) is what makes
any degradation visible instead of invisible.

Two modes (spec 6.1):
    V-A  constraint-assisted: the hinge axis the IR knows about is declared as a MuJoCo
         hinge joint. Stable. Verifies range of motion, interference, behaviour under load.
    V-B  contact-only: no joints. Free bodies + contacts. The strict test of whether the
         *geometry itself* produces the DoF -- the pin must be held by the bore alone.
"""

from __future__ import annotations

import json
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from xml.dom import minidom

import numpy as np
import trimesh

VARIANT = os.environ.get("M0_VARIANT", "nostop")
OUT = Path(__file__).parent / "out" / VARIANT
MESHDIR = OUT / "meshes"
MM = 1e-3  # mm -> m. Explicit, once, here. (spec 6.2 step 1)

DENSITY = 1270.0  # PETG, kg/m^3 (spec 3.1)
MU = 0.30  # PETG friction (spec 3.1)

# --- The contact preset. ONE set, used across every experiment. -----------------------
# Spec 6.2 / R5: results must not be manufactured by per-experiment tuning. Any change to
# these numbers gets recorded in FINDINGS.md with the reason, and re-run across the board.
#
# It is fixed by a physical requirement, not by whatever makes a test go green:
#
#   the contact must be stiff enough that penetration under the assembly's own working
#   loads is negligible against the feature size the design is built from -- the 0.30 mm
#   PETG print clearance (spec 3.1). Target: steady-state penetration <= 0.05 mm, i.e.
#   under 1/6 of the clearance.
#
# A softer contact makes the sim squash parts by as much as the clearances we are trying to
# verify, which renders the whole exercise meaningless. Timeconst is held at 2x the 0.5 ms
# timestep -- MuJoCo's recommended floor, and the stiffest value that stays stable.
SOLREF = (0.001, 1.0)  # (time_const s, damping_ratio) -- 1 ms = 2*dt, critically damped
SOLIMP = (0.99, 0.9999, 0.0001)  # (d0, d_width, width m) -- near-rigid, saturates in 0.1 mm

# --- Collision-hint invariant (M0 finding; see FINDINGS.md) ---------------------------
# No collision primitive of a *moving* piece may share a face plane -- or be exactly
# tangent to -- a primitive of a static piece. Our lid is flush with the box walls, so its
# panel box was coplanar with the wall tops (z, the real contact) AND with the wall sides
# (x = +-40). Two tied separating axes let MuJoCo's box-box routine flip its normal, and it
# produced a -57.7 mm / 362 N contact between parts that were 0.0002 mm apart -- launching
# the lid at 214 rad/s. The tie is broken by shrinking the moving piece's collision
# primitives laterally by COLLISION_EPS. This cannot hide a real interference: Tier0 has
# already proved, in exact B-rep, that there is none. The plane that carries the load
# (z = box top) is deliberately left exact.
COLLISION_EPS = 0.2  # mm


@dataclass
class Piece:
    name: str
    mesh: trimesh.Trimesh  # full-fidelity, in metres
    collision: list[trimesh.Trimesh]  # convex parts, in metres
    strategy: str  # "primitive" | "coacd"


def load_step_mesh(step_path: Path, tol: float = 0.05) -> trimesh.Trimesh:
    """STEP -> triangle mesh, in metres. Tessellation tolerance in mm.

    The STL is rewritten *in metres* after scaling. Scaling only the in-memory mesh leaves
    a millimetre file on disk, and MuJoCo reads mesh files as metres -- so the physics
    (built from the scaled mesh) is right while the render is 1000x too big. Everything
    that lands in meshdir/ is in metres, no exceptions.
    """
    from build123d import export_stl, import_step

    part = import_step(str(step_path))
    stl = MESHDIR / f"{step_path.stem}_visual.stl"
    MESHDIR.mkdir(parents=True, exist_ok=True)
    export_stl(part, str(stl), tolerance=tol, angular_tolerance=0.2)

    mesh = trimesh.load(stl, force="mesh")
    mesh.apply_scale(MM)
    mesh.export(stl)  # rewrite in metres -- the units the MJCF will read it in
    return mesh


# --- (a) primitive collision hints ----------------------------------------------------
# In the real pipeline these come from ElementCard.collision_hint() (spec 3.2). Here they
# are hand-written, which is exactly what M0 is: the experiment that tells us what the card
# API actually has to be able to express.


def box_prim(cx, cy, cz, sx, sy, sz) -> dict:
    """A box primitive, centre + half-sizes, in mm -> emitted in m."""
    return {
        "type": "box",
        "pos": (cx * MM, cy * MM, cz * MM),
        "size": (sx / 2 * MM, sy / 2 * MM, sz / 2 * MM),
    }


def cyl_prim(cx, cy, cz, r, half_len_x) -> dict:
    """A cylinder about the +X axis (the hinge axis), in mm -> emitted in m."""
    return {
        "type": "cylinder",
        "pos": (cx * MM, cy * MM, cz * MM),
        "size": (r * MM, half_len_x * MM),
        "euler": (0.0, 1.5707963267948966, 0.0),  # +Z cylinder rotated onto +X
    }


RING_SECTORS = 16


def ring_prims(cx: float, w: float, ax_y: float, ax_z: float,
               r_bore: float, r_out: float, M: int = RING_SECTORS) -> list[dict]:
    """A *bored* knuckle as a ring of convex wedges -- collision level (c).

    MuJoCo collides every mesh as its convex hull, so a bore can only survive as a set of
    convex parts arranged around the hole. The inner faces are placed on a polygon that
    *circumscribes* the bore circle (r/cos(pi/M)), never inside it: an inscribed polygon
    would eat into the bore and pinch the pin, converting a clearance fit into an
    interference fit -- the exact failure this whole exercise is meant to detect.

    Cost of the approximation: the hole is polygonal, so the effective radial clearance
    grows by r_bore*(1/cos(pi/M) - 1). At M=16 that is +0.042 mm on a 0.150 mm radial
    clearance. Reported in FINDINGS; it is a known, bounded slop, not a hidden one.
    """
    r_in = r_bore / np.cos(np.pi / M)  # circumscribing polygon -> never intrudes on the pin
    rc = (r_in + r_out) / 2
    half_radial = (r_out - r_in) / 2
    half_tang = r_in * np.tan(np.pi / M)

    prims = []
    for i in range(M):
        phi = 2 * np.pi * i / M
        # Rotation about +X by phi maps local +y onto the radial direction.
        prims.append({
            "type": "box",
            "pos": (cx * MM, (ax_y + rc * np.cos(phi)) * MM, (ax_z + rc * np.sin(phi)) * MM),
            "size": ((w / 2) * MM, half_radial * MM, half_tang * MM),
            "euler": (float(phi), 0.0, 0.0),
        })
    return prims


def primitives_for(name: str, m: dict, bored: bool = False) -> list[dict] | None:
    """The collision hint for each piece. Returns None if we have no hint (-> CoACD).

    bored=True (V-B): knuckles are emitted as ring wedges with a real hole, so the pin is
    held by the bore through contact alone. bored=False (V-A): knuckles are solid cylinders,
    since the declared joint does the pin's job and a solid hint is cheaper and stabler.
    """
    p, d = m["params"], m["derived"]
    L, W, H = p["box_l"], p["box_w"], p["box_h"]
    wall, lid_t = p["wall"], p["lid_t"]
    ax_y, ax_z = m["hinge_axis"]["point_mm"][1], m["hinge_axis"]["point_mm"][2]
    kr = d["knuckle_od"] / 2
    r_bore = d["bore_d"] / 2

    def knuckle_col(cx, w, owner_moving: bool):
        e = COLLISION_EPS if owner_moving else 0.0
        if bored:
            return ring_prims(cx, w, ax_y, ax_z, r_bore, kr - e)
        return [cyl_prim(cx, ax_y, ax_z, kr - e, w / 2)]

    if name == "box_shell":
        lug_z0, lug_z1 = d["lug_top_z"] - 5.0, d["lug_top_z"]
        lug_y0, lug_y1 = ax_y, -W / 2 + wall
        prims = [
            box_prim(0, 0, wall / 2, L, W, wall),  # floor
            box_prim(0, -(W - wall) / 2, H / 2, L, wall, H),  # rear wall
            box_prim(0, +(W - wall) / 2, H / 2, L, wall, H),  # front wall
            box_prim(-(L - wall) / 2, 0, H / 2, wall, W - 2 * wall, H),  # left wall
            box_prim(+(L - wall) / 2, 0, H / 2, wall, W - 2 * wall, H),  # right wall
        ]
        # Knuckles: solid cylinders. The bore is *not* represented -- in V-A the pin is not
        # a contact participant, so it costs nothing. In V-B this hint is refused (below).
        for k in m["knuckles"]:
            if k["owner"] != "box":
                continue
            w = k["x1"] - k["x0"]
            prims += knuckle_col((k["x0"] + k["x1"]) / 2, w, owner_moving=False)
            prims.append(
                box_prim(
                    (k["x0"] + k["x1"]) / 2, (lug_y0 + lug_y1) / 2, (lug_z0 + lug_z1) / 2,
                    w, lug_y1 - lug_y0, lug_z1 - lug_z0,
                )
            )
        return prims

    if name == "lid_panel":
        # The lid is the moving piece -> its primitives are inset by COLLISION_EPS in the
        # directions that would otherwise tie with the box's faces. Z is left exact: that
        # is the plane the lid actually rests on.
        e = COLLISION_EPS
        y0, y1 = d["lid_rear_y"], W / 2
        prims = [box_prim(0, (y0 + y1) / 2, H + lid_t / 2, L - 2 * e, (y1 - y0) - 2 * e, lid_t)]
        fr = d.get("stop_flange_r", 0.0)
        for k in m["knuckles"]:
            if k["owner"] != "lid" or fr <= 0:
                continue
            # The stop flange must be in the collision model, or the end stop it provides is
            # invisible to the solver and the lid folds over anyway.
            w = k["x1"] - k["x0"]
            fy0, fy1 = ax_y - fr, ax_y - 3.0
            prims.append(box_prim((k["x0"] + k["x1"]) / 2, (fy0 + fy1) / 2, H + lid_t / 2,
                                  w - 2 * e, (fy1 - fy0) - 2 * e, lid_t - 2 * e))
        for k in m["knuckles"]:
            if k["owner"] != "lid":
                continue
            w = k["x1"] - k["x0"]
            # Radius inset too: at full radius the lid knuckle is exactly tangent to the
            # rear wall's outer face -- another tie.
            prims += knuckle_col((k["x0"] + k["x1"]) / 2, w, owner_moving=True)
        return prims

    if name == "hinge_pin":
        return [cyl_prim(0, ax_y, ax_z, p["pin_d"] / 2, d["pin_len"] / 2)]

    return None


# --- (b) CoACD fallback ---------------------------------------------------------------


# The only CoACD setting (of 5 swept) that leaves the 4.3 mm bore open at all. The default
# threshold=0.03 fills it solid. Even this one eats 91% of the radial clearance -- see
# FINDINGS -- but it is CoACD's best case, so it is the one we test.
COACD_CFG = dict(threshold=0.005, resolution=10000, merge=False)


def coacd_parts(mesh: trimesh.Trimesh, cfg: dict | None = None) -> list[trimesh.Trimesh]:
    import coacd

    cm = coacd.Mesh(mesh.vertices, mesh.faces)
    parts = coacd.run_coacd(cm, **(cfg or COACD_CFG))
    return [trimesh.Trimesh(vertices=v, faces=f) for v, f in parts]


def prim_to_mesh(prim: dict) -> trimesh.Trimesh:
    """Only for the overlay render + mass bookkeeping; the MJCF emits the primitive itself."""
    if prim["type"] == "box":
        m = trimesh.creation.box(extents=[2 * s for s in prim["size"]])
    else:
        r, hl = prim["size"]
        m = trimesh.creation.cylinder(radius=r, height=2 * hl)
        m.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
    m.apply_translation(prim["pos"])
    return m


# --- MJCF emission --------------------------------------------------------------------


def _inertial(body: ET.Element, mesh: trimesh.Trimesh) -> float:
    """Mass + inertia from the *exact* mesh, never from the collision approximation.
    (spec 6.2 step 3.) Convex parts overlap; trusting their mass would inflate it."""
    mesh.density = DENSITY
    mass = float(mesh.mass)
    com = mesh.center_mass
    I = mesh.moment_inertia  # about COM, body axes
    ET.SubElement(
        body,
        "inertial",
        pos=" ".join(f"{v:.9f}" for v in com),
        mass=f"{mass:.9f}",
        fullinertia=" ".join(
            f"{v:.12f}" for v in (I[0, 0], I[1, 1], I[2, 2], I[0, 1], I[0, 2], I[1, 2])
        ),
    )
    return mass


def build_mjcf(pieces: dict[str, Piece], m: dict, mode: str) -> tuple[str, dict]:
    ax = m["hinge_axis"]
    axis_pos = " ".join(f"{v * MM:.9f}" for v in ax["point_mm"])

    root = ET.Element("mujoco", model=f"m0_hinge_box_{mode}")
    ET.SubElement(root, "compiler", angle="radian", meshdir="meshes", autolimits="true")
    ET.SubElement(root, "option", timestep="0.0005", integrator="implicitfast",
                  cone="elliptic", impratio="10")

    vis = ET.SubElement(root, "visual")
    ET.SubElement(vis, "headlight", ambient="0.5 0.5 0.5", diffuse="0.6 0.6 0.6",
                  specular="0.2 0.2 0.2")
    ET.SubElement(vis, "global", offwidth="1280", offheight="960", azimuth="140",
                  elevation="-20")
    ET.SubElement(vis, "rgba", haze="0.9 0.93 0.96 1")

    dflt = ET.SubElement(root, "default")
    ET.SubElement(
        dflt, "geom",
        solref=f"{SOLREF[0]} {SOLREF[1]}",
        solimp=f"{SOLIMP[0]} {SOLIMP[1]} {SOLIMP[2]}",
        friction=f"{MU} 0.005 0.0001",
        condim="4",
        density="0",  # mass comes from <inertial>, not from overlapping convex parts
    )

    asset = ET.SubElement(root, "asset")
    ET.SubElement(asset, "texture", name="grid", type="2d", builtin="checker",
                  rgb1=".15 .17 .2", rgb2=".22 .24 .28", width="300", height="300")
    ET.SubElement(asset, "material", name="grid", texture="grid", texrepeat="6 6",
                  reflectance=".1")
    ET.SubElement(asset, "material", name="petg", rgba="0.35 0.65 0.85 1")
    ET.SubElement(asset, "material", name="petg_lid", rgba="0.95 0.62 0.25 1")
    ET.SubElement(asset, "material", name="steel", rgba="0.8 0.8 0.85 1")

    world = ET.SubElement(root, "worldbody")
    ET.SubElement(world, "light", pos="0.15 -0.25 0.4", dir="-0.3 0.5 -1",
                  directional="true", diffuse="0.5 0.5 0.5")
    ET.SubElement(world, "light", pos="-0.2 0.2 0.3", dir="0.4 -0.4 -1",
                  directional="true", diffuse="0.25 0.25 0.25")
    ET.SubElement(world, "geom", name="floor", type="plane", size="1 1 .05",
                  rgba="0.82 0.85 0.88 1", pos="0 0 0")
    # Fixed cameras, so every run's video frames the mechanism the same way and the human
    # at gate G-H is always looking at the same thing (spec 7.4).
    ET.SubElement(world, "camera", name="iso", pos="0.125 -0.125 0.115",
                  xyaxes="0.707 0.707 0 -0.38 0.38 0.84")
    ET.SubElement(world, "camera", name="hinge_closeup", pos="0.065 -0.105 0.085",
                  xyaxes="0.85 0.53 0 -0.32 0.51 0.80")

    mats = {"box_shell": "petg", "lid_panel": "petg_lid", "hinge_pin": "steel"}
    masses: dict[str, float] = {}

    for name, pc in pieces.items():
        # Visual mesh (full fidelity) -- always.
        vis = MESHDIR / f"{name}_visual.stl"
        ET.SubElement(asset, "mesh", name=f"{name}_vis", file=vis.name)

        static = mode == "V-A" and name == "box_shell"
        body = ET.SubElement(world, "body", name=name, pos="0 0 0")

        if mode == "V-A":
            if name == "lid_panel":
                # damping: sized so the lid opens quasi-statically under the P-HINGE force
                # ramp instead of slamming (see FINDINGS.md). range: the upper stop stands
                # in for the physical knuckle/lug hard stop, which the primitive collision
                # hint does not reproduce.
                ET.SubElement(body, "joint", name="hinge", type="hinge",
                              axis="1 0 0", pos=axis_pos, damping="0.002",
                              range="-0.02 1.745", limited="true")
            elif name == "hinge_pin":
                pass  # welded to world: the pin's job in V-A is done by the joint
        else:  # V-B: no joint is declared. The geometry must produce the DoF on its own.
            # D23 fixture rule: optionally weld the base (box_shell) to the world. This is a
            # boundary condition -- a bench vice -- NOT a joint declaration on the mechanism
            # under test. Everything the behaviour spec claims moves (lid) and its realizing
            # element (pin) stays free, so the pin/bore DoF must still emerge from contact.
            # Without it, the lid's reaction torque tumbles the unfixtured box and that noise
            # corrupts the closing-seat contact. Set M0_FIXTURE_BASE=1 to enable.
            # D23 is ON by default: the unfixtured box's reaction tumble corrupts pin
            # retention (a seed drifts past the 0.4 mm limit) and the closing seat. Welding
            # the base is a boundary condition, not a joint on the mechanism under test.
            # Set M0_FIXTURE_BASE=0 to reproduce the un-fixtured tumble.
            if os.environ.get("M0_FIXTURE_BASE", "1") != "0" and name == "box_shell":
                pass  # welded to world (D23)
            else:
                ET.SubElement(body, "freejoint", name=f"{name}_free")

        masses[name] = _inertial(body, pc.mesh)

        ET.SubElement(body, "geom", name=f"{name}_vis", type="mesh", mesh=f"{name}_vis",
                      contype="0", conaffinity="0", group="2", material=mats[name])

        # Collision geoms.
        for i, prim in enumerate(pc.prims or []):
            attrs = {
                "name": f"{name}_c{i}",
                "type": prim["type"],
                "pos": " ".join(f"{v:.9f}" for v in prim["pos"]),
                "size": " ".join(f"{v:.9f}" for v in prim["size"]),
                "group": "3",
                "material": mats[name],
            }
            if "euler" in prim:
                attrs["euler"] = " ".join(f"{v:.9f}" for v in prim["euler"])
            ET.SubElement(body, "geom", **attrs)
        for i, cm in enumerate(pc.collision_meshes or []):
            f = MESHDIR / f"{name}_col{i}.stl"
            cm.export(f)
            ET.SubElement(asset, "mesh", name=f"{name}_col{i}", file=f.name)
            ET.SubElement(body, "geom", name=f"{name}_c{i}", type="mesh",
                          mesh=f"{name}_col{i}", group="3", material=mats[name])

        if static:
            # No joint => welded to the world. Keeps V-A stable and matches "the box is
            # held while you open the lid".
            pass

    # Sites for actuation + observation: the lid's free edge midpoint (spec 6.3 P-HINGE).
    lid_free_edge = (0.0, m["params"]["box_w"] / 2, m["params"]["box_h"] + m["params"]["lid_t"] / 2)
    ET.SubElement(
        world.find("body[@name='lid_panel']"), "site", name="lid_tip",
        pos=" ".join(f"{v * MM:.9f}" for v in lid_free_edge), size="0.002",
        rgba="1 0.2 0.2 1",
    )
    # Retention observables (V-B). Pin drift is only meaningful *relative to the box*, since
    # in V-B the box is a free body too and moves. So the axis reference lives on the box.
    axp = ax["point_mm"]
    ET.SubElement(world.find("body[@name='box_shell']"), "site", name="box_axis",
                  pos=" ".join(f"{v * MM:.9f}" for v in axp), size="0.0012",
                  rgba="0.1 0.9 0.2 1")
    ET.SubElement(world.find("body[@name='hinge_pin']"), "site", name="pin_center",
                  pos=" ".join(f"{v * MM:.9f}" for v in axp), size="0.0012",
                  rgba="0.9 0.1 0.9 1")

    xml = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
    meta = {
        "mode": mode,
        "masses_kg": masses,
        "strategies": {n: p.strategy for n, p in pieces.items()},
        "contact_preset": {"solref": SOLREF, "solimp": SOLIMP, "friction_mu": MU},
        "hinge_axis_m": [v * MM for v in ax["point_mm"]],
        "lid_tip_m": [v * MM for v in lid_free_edge],
        "clearance_mm": m["params"]["clearance"],
        "radial_clearance_mm": (m["derived"]["bore_d"] - m["params"]["pin_d"]) / 2,
        "pin_protrusion_mm": (m["derived"]["pin_len"] - m["derived"]["stack_w"]) / 2,
        "ring_sectors": RING_SECTORS,
    }
    return xml, meta


class _P:
    """Piece record; prims and meshes are mutually exclusive per strategy."""

    def __init__(self, name, mesh, prims, collision_meshes, strategy):
        self.name, self.mesh = name, mesh
        self.prims, self.collision_meshes = prims, collision_meshes
        self.strategy = strategy


def convert(mode: str = "V-A", strategy: str = "primitive") -> tuple[Path, dict]:
    """strategy (V-B only): 'coacd' = level (a), 'ring' = level (c). Level (b), MuJoCo SDF,
    is *unavailable*: the SDF plugin ships analytic shapes only (bolt/bowl/gear/nut/torus),
    with no mesh-SDF, so a carved bore cannot be expressed. See FINDINGS."""
    m = json.loads((OUT / "manifest.json").read_text())
    pieces: dict[str, _P] = {}
    suffix = mode if mode == "V-A" else f"{mode}_{strategy}"

    for name, info in m["pieces"].items():
        mesh = load_step_mesh(OUT / info["step"])

        # In V-A the declared hinge joint *is* what the pin does, and the knuckle hints are
        # solid (unbored) cylinders -- so a colliding pin would start fully interpenetrated
        # and detonate G-CONV. The pin is therefore visual-only here. This is not a fudge:
        # it is the honest content of "constraint-assisted". V-B gives the pin its contacts
        # back and makes the geometry earn the DoF.
        if mode == "V-A":
            if name == "hinge_pin":
                pieces[name] = _P(name, mesh, [], None, "none (V-A: joint replaces pin)")
            else:
                pieces[name] = _P(name, mesh, primitives_for(name, m, bored=False), None,
                                  "primitive (solid knuckle)")
            continue

        # V-B: the bore must exist in the collision model. That is the entire experiment.
        if strategy == "coacd" and name in ("box_shell", "lid_panel"):
            parts = coacd_parts(mesh)
            pieces[name] = _P(name, mesh, None, parts, f"coacd ({len(parts)} hulls)")
        else:
            prims = primitives_for(name, m, bored=True)
            tag = "cylinder (convex, exact)" if name == "hinge_pin" else \
                  f"ring ({RING_SECTORS} wedges/knuckle)"
            pieces[name] = _P(name, mesh, prims, None, tag)

    xml, meta = build_mjcf(pieces, m, mode)
    meta["strategy"] = strategy if mode == "V-B" else "primitive"
    out = OUT / f"hinge_{suffix}.xml"
    out.write_text(xml)
    (OUT / f"hinge_{suffix}_meta.json").write_text(json.dumps(meta, indent=2))

    print(f"[{suffix}] wrote {out.name}")
    for n, p in pieces.items():
        ngeom = len(p.prims or []) + len(p.collision_meshes or [])
        print(f"    {n:11s} {p.strategy:28s} {ngeom:3d} collision geom(s)  "
              f"mass {meta['masses_kg'][n]*1000:6.2f} g")
    return out, meta


if __name__ == "__main__":
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "V-A"
    strat = sys.argv[2] if len(sys.argv) > 2 else ("ring" if mode == "V-B" else "primitive")
    convert(mode, strat)
