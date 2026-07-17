"""rack_pinion geometry (MECHSYNTH §3.6, amended) — a spur pinion driving a straight rack.

Reuses M1's proven involute pinion (`m1_gear/gear_geom.build_gear`, profile="involute" — the true
conjugate profile; the trapezoid is DEAD, D-M1-1) and its L3 flank-wedge decomposition for the
`collision_hint` (`m1_gear/gear_mjcf.flank_wedges` — convex prism per flank segment, the tooth-profile
analog of M0's ring-of-wedges; `mujoco.sdf.gear` is FORBIDDEN, D21). The rack's teeth are the involute
in its z→∞ limit: STRAIGHT flanks inclined at the pressure angle (a rack is exactly-conjugate to an
involute pinion — the one case where straight flanks are correct, not an approximation).

Frame: pinion axis = +Z at the origin; the rack lies along +X with its pitch line at y = −rp, teeth
pointing +Y toward the pinion, translating along X. The pinion pitch circle (r = m·z/2) rolls on the
rack pitch line.

§3.6 formulas (all reproduced numerically by the golden's docstring):
  pitch diameter  d = m·z            pitch radius rp = d/2
  travel per rev  = π·m·z            (the pitch circumference)
  rack length     L_rack ≥ stroke + π·m·z/4      (engagement margin)
  axis→rack dist  a = rp             (+ a backlash correction, small)
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

from build123d import Align, Box, Location, Polygon, Pos, Rotation, extrude

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "m1_gear"))
from gear_geom import GearSpec, build_gear, tooth_flanks  # noqa: E402  (M1 involute + flanks)


@dataclass
class RackPinionDims:
    module: float           # m, §3.6 amended bounds {5,6} (large — contact-sim stability, not mechanics)
    z_pinion: int           # tooth count [10,24]
    pressure_angle_deg: float = 20.0
    face_w: float = 8.0
    backlash: float = 0.20
    stroke: float = 120.0   # rack travel (design input)

    @property
    def rp(self) -> float: return self.module * self.z_pinion / 2.0        # pitch radius

    @property
    def pitch_d(self) -> float: return self.module * self.z_pinion         # pitch diameter d = m·z

    @property
    def travel_per_rev(self) -> float: return math.pi * self.module * self.z_pinion  # π·m·z

    @property
    def rack_len(self) -> float:                                           # ≥ stroke + π·m·z/4
        return round(self.stroke + self.travel_per_rev / 4.0, 3)

    @property
    def axis_to_rack(self) -> float: return round(self.rp, 3)              # a = rp (+ backlash corr.)


@dataclass
class RackPinionCarve:
    parts: dict
    tags: dict
    dims: RackPinionDims
    axis_world: dict = field(default_factory=dict)


def dims_from(params: dict) -> RackPinionDims:
    return RackPinionDims(
        module=float(params.get("module", 5.0)),
        z_pinion=int(params.get("z_pinion", 12)),
        pressure_angle_deg=float(params.get("pressure_angle_deg", 20.0)),
        face_w=float(params.get("face_w", 8.0)),
        backlash=float(params.get("backlash", 0.20)),
        stroke=float(params.get("stroke", 120.0)),
    )


def _pinion_spec(g: RackPinionDims) -> GearSpec:
    return GearSpec(z=g.z_pinion, m=g.module, face_width=g.face_w,
                    pressure_angle_deg=g.pressure_angle_deg, backlash=g.backlash, profile="involute")


def build_pinion(g: RackPinionDims):
    """The involute pinion, axis +Z, centred at origin (M1's proven builder)."""
    return build_gear(_pinion_spec(g))


def _rack_outline(g: RackPinionDims) -> list:
    """Rack cross-section in the X–Y plane (teeth point +Y). Straight flanks at the pressure angle —
    the involute's z→∞ limit, exactly conjugate to the pinion. Returns a CCW point list."""
    m, bl = g.module, g.backlash
    p = math.pi * m                                     # circular pitch
    t = p / 2.0 - bl / 2.0                              # tooth thickness at the pitch line
    add, ded = m, 1.25 * m                              # addendum / dedendum
    ta = math.tan(math.radians(g.pressure_angle_deg))
    y_pitch = -g.rp
    y_tip = y_pitch + add                               # toward the pinion
    y_root = y_pitch - ded
    back = y_root - 4.0                                 # rack body back face
    L = g.rack_len
    n_teeth = int(L / p) + 2
    x0 = -L / 2.0
    # top edge: walk the tooth zigzag left→right
    top = []
    for i in range(n_teeth):
        cx = x0 + i * p
        # root gap then a trapezoid tooth centred at cx
        half_root = t / 2.0 + ded * ta
        half_tip = t / 2.0 - add * ta
        top += [(cx - p / 2.0, y_root), (cx - half_root, y_root),
                (cx - half_tip, y_tip), (cx + half_tip, y_tip),
                (cx + half_root, y_root), (cx + p / 2.0, y_root)]
    # clip to [x0, x0+L] and close the polygon along the back
    top = [(min(max(x, x0), x0 + L), y) for (x, y) in top]
    outline = [(x0, back)] + top + [(x0 + L, back)]
    return outline


def build_rack(g: RackPinionDims):
    """The straight rack (toothed bar), extruded over the face width along +Z, pitch line at y=−rp."""
    face = Polygon(*_rack_outline(g), align=None)
    return extrude(face, amount=g.face_w)


def carve(pieces: dict, inst, bindings) -> RackPinionCarve:
    """Place the pinion on its axis piece and the rack on its mount piece, meshing at the pitch line.
    Anchor-driven (host-agnostic). Returns the pinion's world axis for the physics layer."""
    g = dims_from(inst.params)
    pb = next(b for b in bindings if b.port == "pinion_axis")
    rb = next(b for b in bindings if b.port == "rack_mount")
    ax = _anchor(pieces, pb)
    rk = _anchor(pieces, rb)

    parts, tags = dict(_solids(pieces)), {}
    pin = build_pinion(g)
    pin_pos = tuple(ax["point"])
    pin = Pos(*pin_pos) * pin
    rack = build_rack(g)
    # rack pitch line sits rp below the pinion axis, in the pinion's XY plane
    rack = Pos(pin_pos[0], pin_pos[1], pin_pos[2]) * rack
    parts[pb.piece_id] = parts[pb.piece_id] + pin
    parts[rb.piece_id] = parts[rb.piece_id] + rack
    tags["pinion"] = pin
    tags["rack"] = rack
    return RackPinionCarve(parts=parts, tags=tags, dims=g,
                           axis_world={"point": pin_pos, "dir": (0.0, 0.0, 1.0)})


def collision_primitives(inst, n_wedge: int = 4) -> list:
    """L3 wedge decomposition (§3.6, D18/D21): a convex PRISM per involute flank segment — the
    tooth-profile analog of M0's ring-of-wedges, and the ONLY hint allowed here (`mujoco.sdf.gear`
    is FORBIDDEN, D21: it would simulate an ideal analytic gear, not our compiled geometry). Each
    prism = the hull of {two flank points, their projections onto the tooth centreline}, extruded
    over the face width. Every prim `source`-stamped (D-M8-4). Wedge count = L3's default (4/flank);
    the passing rung is TBD until R2b is retired in-bounds. **Deferred with V-B: not consumed by the
    physics this session (V-A does not use tooth contact), but supplied so the card is D18-complete.**
    Returned as `hull` prims (vertex lists), not boxes — the flanks are not axis-aligned."""
    import numpy as np
    g = dims_from(inst.params)
    src = f"card:rack_pinion@{inst.id}"
    right, left = tooth_flanks(_pinion_spec(g))
    pitch = 2 * math.pi / g.z_pinion
    prims = []

    def resample(poly, n):
        pts = np.array(poly, float)
        idx = np.linspace(0, len(pts) - 1, n + 1)
        return [pts[int(round(t))] if t == int(t) else
                pts[int(t)] * (1 - (t - int(t))) + pts[int(t) + 1] * (t - int(t)) for t in idx]

    for i in range(g.z_pinion):
        c = i * pitch
        R = np.array([[math.cos(c), -math.sin(c)], [math.sin(c), math.cos(c)]])
        for flank in (right, left):
            fs = resample(flank, n_wedge)
            for k in range(n_wedge):
                a, b = np.array(fs[k]), np.array(fs[k + 1])
                pa = np.array([np.hypot(*a), 0.0]); pb = np.array([np.hypot(*b), 0.0])
                quad = [R @ q for q in (a, b, pb, pa)]
                verts = [[q[0], q[1], 0.0] for q in quad] + [[q[0], q[1], g.face_w] for q in quad]
                prims.append({"type": "hull", "owner": "pinion", "source": src,
                              "verts": [[round(v, 4) for v in vv] for vv in verts]})
    return prims


# --- helpers -------------------------------------------------------------------------------------
def _solids(pieces: dict) -> dict:
    return {pid: getattr(tr, "part", tr) for pid, tr in pieces.items()}


def _anchor(pieces, binding) -> dict:
    tr = pieces[binding.piece_id]
    a = tr.anchors[binding.anchor]
    return {"point": a.position, "dir": a.normal}
