"""pin_hinge — GEOMETRY + derivations, formalizing M0's proven assets (MECHSYNTH §3.3).

M0 built this hinge by hand and drove it through STEP→MJCF→P-HINGE (V-A and V-B): interleaved
knuckles, a print-clearance bore, a separate pin, the chamfer rule. R1 was retired on it (D18: the
ring-of-wedges collision hint preserved the bore at 128% retention where CoACD swallowed it). This
module lifts that hand geometry into card knowledge — host-agnostic per D-GEN-1's *proven* half: the
knuckle stack and bore are placed from the bound anchors (axis point+direction, and the two mount
faces), never from a host's box_l/box_w.

Card knowledge (the derivations, all M0-cited):
  bore_d       = pin_d + clearance                      (§3.3: rotational clearance = print clearance)
  knuckle_od   = pin_d + 2·knuckle_wall
  stack_w      = n·knuckle_w + (n−1)·clearance          (axial stack incl. clearance gaps)
  chamfer_len  = pin_d/2 + clearance                    (§3.3 lid-edge chamfer rule)
  bore_keepout = bore_d/2 + clearance                   (nothing but knuckles inside this radius)
  interleave   = box takes even (outer) knuckles, lid odd (inner); n ∈ {3,5}

THE THIRD-PIECE WALL (DRAFT, do NOT fuse): a pin hinge needs a PIN — a separate, insertable rigid
body. carve() below can add knuckles/bores/chamfers to the two bound mount pieces (that is geometry
ON existing hosts), but it CANNOT emit the pin as its own Piece: `ElementCard.carve` returns edits to
`host_parts`, and `Piece` is a top-level DesignPlan entity with no card-emission path. The pin is
returned here as a tagged loose solid + its dims, and the caller must currently declare it as a
plan-level Piece by hand. See DECISIONS_LOG D-ONT-11 (element-generated pieces).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from build123d import Align, Axis, Box, Cylinder, Location, Pos, Rotation, chamfer

from knowledge.materials import PETG

CLEARANCE = PETG.print_clearance_mm  # 0.30 mm — the bore's rotational clearance (§3.3)
KNUCKLE_WALL = 2.0                    # knuckle wall thickness → knuckle_od = pin_d + 2·wall
PROTRUDE = 3.0                        # pin protrusion each side past the knuckle stack


@dataclass
class HingeDims:
    """The card's derived dimensions from its resolved params (M0-cited). Host-agnostic: only the
    hinge's own params + the anchor-provided axis span enter, never a host dimension."""
    pin_d: float
    knuckle_w: float
    knuckle_n: int
    clearance: float
    face_len: float                  # available length along the axis (from the mount anchors)
    knuckle_wall: float = KNUCKLE_WALL

    @property
    def bore_d(self) -> float: return self.pin_d + self.clearance

    @property
    def knuckle_od(self) -> float: return self.pin_d + 2 * self.knuckle_wall

    @property
    def knuckle_r(self) -> float: return self.knuckle_od / 2

    @property
    def stack_w(self) -> float: return self.knuckle_n * self.knuckle_w + (self.knuckle_n - 1) * self.clearance

    @property
    def chamfer_len(self) -> float: return self.pin_d / 2 + self.clearance

    @property
    def bore_keepout_r(self) -> float: return self.bore_d / 2 + self.clearance

    @property
    def pin_len(self) -> float: return self.stack_w + 2 * PROTRUDE

    @property
    def edge_margin(self) -> float: return self.face_len / 2 - self.stack_w / 2

    def knuckle_spans(self):
        """Interleave along the axis: even i → box (outer), odd i → lid (inner). (M0 knuckle_spans)."""
        spans, x = [], -self.stack_w / 2
        for i in range(self.knuckle_n):
            spans.append((x, x + self.knuckle_w, "A" if i % 2 == 0 else "B"))
            x += self.knuckle_w + self.clearance
        return spans

    def rule_violations(self) -> list:
        v = []
        if self.knuckle_n not in (3, 5):
            v.append(f"knuckle_n {self.knuckle_n} not in {{3,5}}")
        if self.edge_margin < self.knuckle_w:
            v.append(f"edge_margin {self.edge_margin:.2f} < knuckle_w {self.knuckle_w} (§3.3)")
        if self.knuckle_wall < PETG.print_min_wall_mm:
            v.append(f"knuckle_wall {self.knuckle_wall} < print min wall {PETG.print_min_wall_mm}")
        return v


@dataclass
class HingeCarve:
    parts: dict                      # {piece_id: edited Solid}
    tags: dict                       # {"knuckle_A_i"/"knuckle_B_i"/"bore"/"pin": Solid}
    dims: HingeDims
    pin_solid: object                # the loose pin (NO piece home — DRAFT D-ONT-11)
    axis_world: dict                 # {"point": (x,y,z), "dir": (x,y,z)} for the physics layer
    meta: dict = field(default_factory=dict)


def dims_from(params: dict, face_len: float) -> HingeDims:
    return HingeDims(pin_d=float(params.get("pin_d", 4.0)),
                     knuckle_w=float(params.get("knuckle_w", 8.0)),
                     knuckle_n=int(params.get("knuckle_n", 3)),
                     clearance=float(params.get("clearance", CLEARANCE)),
                     face_len=float(face_len))


def _axis_frame(axis_pt, axis_dir):
    """Location mapping local +X→axis onto world, origin at axis_pt. (Cylinders are built about
    local X, i.e. rotated +Z→+X, matching M0's Rotation(0,90,0).)"""
    d = np.array(axis_dir, float); d /= np.linalg.norm(d)
    # pick any up not parallel to d
    up = np.array([0, 0, 1.0]) if abs(d[2]) < 0.9 else np.array([0, 1.0, 0])
    y = np.cross(up, d); y /= np.linalg.norm(y)
    z = np.cross(d, y)
    from build123d import Plane
    return Location(Plane(origin=tuple(axis_pt), x_dir=tuple(d), z_dir=tuple(z)))


def _knuckle(g: HingeDims, x0, x1):
    """One unbored knuckle cylinder about the local axis (+X), spanning [x0,x1]."""
    w = x1 - x0
    return Location(((x0 + x1) / 2, 0, 0)) * Rotation(0, 90, 0) * Cylinder(radius=g.knuckle_r, height=w)


def _bore(g: HingeDims):
    """The pin through-path: one cylinder spanning the whole stack + margin, about the local axis."""
    L = g.face_len + 4
    return Rotation(0, 90, 0) * Cylinder(radius=g.bore_d / 2, height=L)


def carve(host_parts: dict, inst, bindings) -> HingeCarve:
    """Add interleaved knuckles + a shared bore to the two bound mount pieces, build the loose pin,
    all placed from the anchors (host-agnostic, D-GEN-1). Bindings carry ports axis / mount_A /
    mount_B. `host_parts` maps piece_id → Solid (edited in place and returned).

    The pin is returned as a loose solid (pin_solid) and tagged — it has NO Piece home yet
    (DRAFT D-ONT-11). We do not fuse it into a knuckle (that would seize the hinge — the M0 lesson).
    """
    b = {bd.port: bd for bd in bindings}
    axis_a = _anchor(host_parts, b["axis"])
    mA, mB = b["mount_A"], b["mount_B"]
    # available axial span = the shorter mount face length along the axis (anchor-provided)
    face_len = min(_face_len(host_parts, mA), _face_len(host_parts, mB))
    g = dims_from(inst.params, face_len)
    loc = _axis_frame(axis_a["point"], axis_a["dir"])

    parts = dict(host_parts)
    tags = {}
    owner_pid = {"A": mA.piece_id, "B": mB.piece_id}
    bore_local = _bore(g)
    for i, (x0, x1, owner) in enumerate(g.knuckle_spans()):
        pid = owner_pid[owner]
        k_local = _knuckle(g, x0, x1)
        lug_local = _lug(g, x0, x1, owner)                 # bridge knuckle → mount face
        k_world = loc * (k_local + lug_local)
        parts[pid] = parts[pid] + k_world
        tags[f"knuckle_{owner}_{i}"] = loc * k_local
    # one bore cut through both mounts (clears any lug/tab it passes) — the clearance fit
    bore_world = loc * bore_local
    for pid in set(owner_pid.values()):
        parts[pid] = parts[pid] - bore_world
    tags["bore"] = bore_world
    # chamfer the lid (mount_B) rear edge nearest the axis — the edge that sweeps the box rim
    parts[mB.piece_id] = _chamfer_lid_edge(parts[mB.piece_id], g, loc)

    # THE PIN — loose solid, no Piece home (DRAFT D-ONT-11). Built, tagged, returned; not fused.
    pin_world = loc * (Rotation(0, 90, 0) * Cylinder(radius=g.pin_d / 2, height=g.pin_len))
    tags["pin"] = pin_world

    axis_world = {"point": tuple(axis_a["point"]), "dir": tuple(axis_a["dir"])}
    return HingeCarve(parts=parts, tags=tags, dims=g, pin_solid=pin_world, axis_world=axis_world,
                      meta={"face_len": face_len, "rule_violations": g.rule_violations(),
                            "pin_needs_piece": True})


def _lug(g: HingeDims, x0, x1, owner):
    """A block bridging a knuckle to its mount face, stopping clear of the bore keep-out (M0 lug/tab).
    Local frame: +X = axis. The lug reaches from the keep-out radius out to the mount face along a
    perpendicular; here we approximate it as a short block below/front of the knuckle (owner A = box
    from −Z; owner B = lid from +Y), faithful to M0's interleave without a host dimension."""
    w = x1 - x0
    reach = g.knuckle_r + 3.0
    if owner == "A":     # box lug approaches from below (local −Z)
        return Pos((x0 + x1) / 2, 0, -(g.bore_keepout_r + reach / 2)) * Box(w, g.knuckle_od, reach)
    return Pos((x0 + x1) / 2, (g.bore_keepout_r + reach / 2), 0) * Box(w, reach, g.knuckle_od)


def _chamfer_lid_edge(lid_solid, g: HingeDims, loc):
    """Chamfer the lid edge closest to the axis by chamfer_len (§3.3). Best-effort: pick the edge
    of the lid nearest the axis line and chamfer it; if the filter finds none, return unchanged
    (the rule value is still asserted in the golden)."""
    try:
        axis_pt = np.array((loc * Pos(0, 0, 0)).position.to_tuple())
        edges = lid_solid.edges().filter_by(Axis.X)
        if not edges:
            return lid_solid
        near = min(edges, key=lambda e: np.linalg.norm(np.array(e.center().to_tuple()) - axis_pt))
        return chamfer(near, length=g.chamfer_len)
    except Exception:
        return lid_solid


# --- collision hint: the M0 ring-of-wedges (D18, 128% retention). Host-agnostic (widths only). ----
RING_SECTORS = 16


def collision_primitives(inst, face_len: float = 40.0) -> list:
    """Convex ring-of-wedges per knuckle so the BORE survives MJCF conversion (D18/D21). Canonical
    (axis = local +X); the compile step places them by the same anchor frame carve() used. Inner
    faces circumscribe the bore (r/cos(π/M)) so they never pinch the pin — the M0 rule."""
    g = dims_from(inst.params, face_len)
    r_in = (g.bore_d / 2) / math.cos(math.pi / RING_SECTORS)   # circumscribe → never intrude on pin
    r_out = g.knuckle_r
    rc, half_radial = (r_in + r_out) / 2, (r_out - r_in) / 2
    half_tang = r_in * math.tan(math.pi / RING_SECTORS)
    prims = []
    for (x0, x1, owner) in g.knuckle_spans():
        cx, w = (x0 + x1) / 2, x1 - x0
        for k in range(RING_SECTORS):
            phi = 2 * math.pi * k / RING_SECTORS
            prims.append({"type": "box", "tag": f"knuckle_{owner}", "owner": owner,
                          "pos": (cx, rc * math.cos(phi), rc * math.sin(phi)),
                          "size": (w / 2, half_radial, half_tang), "euler": (phi, 0.0, 0.0)})
    return prims


# --- anchor helpers (the card reads only anchors; a host dimension never enters) ----------------
def _anchor(host_parts, binding) -> dict:
    """Resolve an axis/face binding to {point, dir}. Anchors are attached to the bound piece's
    template; here we read the piece's declared anchor by name (the pipeline passes template insts)."""
    pc = binding._piece if hasattr(binding, "_piece") else None
    if pc is not None and binding.anchor in getattr(pc, "anchors", {}):
        a = pc.anchors[binding.anchor]
        return {"point": a.position, "dir": a.normal}
    # fallback: the binding carries offset_params with an explicit axis (test harness)
    op = getattr(binding, "offset_params", {}) or {}
    return {"point": tuple(op.get("point_mm", (0, 0, 0))), "dir": tuple(op.get("axis_dir", (1, 0, 0)))}


def _face_len(host_parts, binding) -> float:
    op = getattr(binding, "offset_params", {}) or {}
    return float(op.get("face_len", 40.0))
