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


def carve(pieces: dict, inst, bindings) -> HingeCarve:
    """Add interleaved knuckles + a shared bore to the two bound mount pieces, cut the lid back so
    the box knuckles clear it (M0 lid_rear_y), chamfer the lid edge, and build the loose pin — all
    placed from the ANCHORS (host-agnostic, D-GEN-1). `pieces` maps piece_id → TemplateResult (with
    `.part` and `.anchors`), the pipeline convention (same as snap_hook_geometry.carve).

    The pin is returned as a loose solid (pin_solid) AND assigned to its hardware piece by the runner
    (D-ONT-11). We never fuse it into a knuckle (that seizes the hinge — the M0 lesson).
    """
    b = {bd.port: bd for bd in bindings}
    axis_a = _anchor(pieces, b["axis"])
    mA, mB = b["mount_A"], b["mount_B"]
    face_len = _face_len(pieces, mA)
    g = dims_from(inst.params, face_len)
    loc = _axis_frame(axis_a["point"], axis_a["dir"])

    parts = {pid: tr.part for pid, tr in pieces.items()}
    tags = {}
    owner_pid = {"A": mA.piece_id, "B": mB.piece_id}
    # LID CUTBACK (M0 lid_rear_y): the lid is pulled forward so the box (owner-A) knuckles clear its
    # panel — else knuckles and panel occupy the same band and t0 reports a real interference.
    parts[mB.piece_id] = _lid_cutback(parts[mB.piece_id], g, loc)
    for i, (x0, x1, owner) in enumerate(g.knuckle_spans()):
        pid = owner_pid[owner]
        k_local = _knuckle(g, x0, x1)
        lug_local = _lug(g, x0, x1, owner)                 # bridge knuckle → mount face
        parts[pid] = parts[pid] + loc * (k_local + lug_local)
        tags[f"knuckle_{owner}_{i}"] = loc * k_local
    # one bore cut through both mounts (clears any lug/tab it passes) — the clearance fit
    bore_world = loc * _bore(g)
    for pid in set(owner_pid.values()):
        parts[pid] = parts[pid] - bore_world
    tags["bore"] = bore_world
    parts[mB.piece_id] = _chamfer_lid_edge(parts[mB.piece_id], g, loc)

    pin_world = loc * (Rotation(0, 90, 0) * Cylinder(radius=g.pin_d / 2, height=g.pin_len))
    tags["pin"] = pin_world
    return HingeCarve(parts=parts, tags=tags, dims=g, pin_solid=pin_world,
                      axis_world={"point": tuple(axis_a["point"]), "dir": tuple(axis_a["dir"])},
                      meta={"face_len": face_len, "rule_violations": g.rule_violations(),
                            "pin_needs_piece": True})


def _lid_cutback(lid_solid, g: HingeDims, loc):
    """Remove lid material within (knuckle_r + clearance) of the axis on the rear side (M0
    lid_rear_y), so the box knuckles clear the panel. Local frame: axis = +X; cut a slab at
    local_y ≤ knuckle_r + clearance spanning the stack."""
    R = g.knuckle_r + g.clearance
    depth = g.knuckle_od + 40.0
    cutter = loc * Pos(0.0, R - depth / 2, 0.0) * Box(g.face_len + 10, depth, g.knuckle_od + 20)
    try:
        cut = lid_solid - cutter
        return cut if cut.volume > 1.0 else lid_solid
    except Exception:
        return lid_solid


def _lug(g: HingeDims, x0, x1, owner):
    """A block bridging a knuckle to its mount face, stopping clear of the bore keep-out (M0 lug/tab).
    Local frame: +X = axis, +Z = up (lid side / world +Z), the box body at local z<0. The box lug
    (owner A) reaches DOWN (−Z) into the box wall and fuses; the lid lug (owner B) is a PLATE at the
    lid plane (local z ∈ [0, knuckle_r]) reaching +Y to the lid — it must not dip to local z<0 or it
    pierces the box rear wall (the 64 mm³ interference this fixes)."""
    w = x1 - x0
    reach = g.knuckle_r + 3.0
    if owner == "A":     # box lug: down into the box body (local −Z)
        return Pos((x0 + x1) / 2, 0, -(g.bore_keepout_r + reach / 2)) * Box(w, g.knuckle_od, reach)
    return Pos((x0 + x1) / 2, (g.bore_keepout_r + reach / 2), g.knuckle_r / 2) * \
        Box(w, reach, g.knuckle_r)


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
    """Convex ring-of-wedges per knuckle so the BORE survives MJCF conversion (D18/D21), PLUS the
    pin cylinder itself. Canonical (axis = local +X); the compile step places them by the same anchor
    frame carve() used. Inner faces circumscribe the bore (r/cos(π/M)) so they never pinch the pin —
    the M0 rule.

    Every prim is stamped with `source` (D-M8-4): the MJCF layer REFUSES any collision geom that does
    not trace to a declared IR entity. The pin is emitted HERE, by the card that provides it
    (D-ONT-11), rather than hand-built in a physics driver — driver-side geometry with no card and no
    IR entity behind it is precisely the fabrication that rule exists to stop.
    `owner` routes each prim to its body: A → the base host, B → the mover host, pin → the hardware
    piece the element provides."""
    g = dims_from(inst.params, face_len)
    src = f"card:pin_hinge@{inst.id}"
    r_in = (g.bore_d / 2) / math.cos(math.pi / RING_SECTORS)   # circumscribe → never intrude on pin
    r_out = g.knuckle_r
    rc, half_radial = (r_in + r_out) / 2, (r_out - r_in) / 2
    half_tang = r_in * math.tan(math.pi / RING_SECTORS)
    prims = []
    for (x0, x1, owner) in g.knuckle_spans():
        cx, w = (x0 + x1) / 2, x1 - x0
        for k in range(RING_SECTORS):
            phi = 2 * math.pi * k / RING_SECTORS
            prims.append({"type": "box", "tag": f"knuckle_{owner}", "owner": owner, "source": src,
                          "pos": (cx, rc * math.cos(phi), rc * math.sin(phi)),
                          "size": (w / 2, half_radial, half_tang), "euler": (phi, 0.0, 0.0)})
    # the pin: a cylinder ON the axis (local +X). MuJoCo's cylinder is canonical about local +Z, so
    # the local euler rotates Z→X before the axis frame is applied.
    prims.append({"type": "cylinder", "tag": "pin", "owner": "pin", "source": src,
                  "pos": (0.0, 0.0, 0.0), "size": (g.pin_d / 2, g.pin_len / 2),
                  "euler": (0.0, math.pi / 2, 0.0)})
    return prims


# --- anchor helpers: the card reads ONLY the bound piece's declared anchors (D-GEN-1) ------------
def _anchor(pieces, binding) -> dict:
    """Resolve an axis/face binding to {point, dir} from the bound piece's TemplateResult anchors."""
    tr = pieces[binding.piece_id]
    a = tr.anchors[binding.anchor]
    return {"point": a.position, "dir": a.normal}


def _face_len(pieces, binding) -> float:
    """Available axial span = the mount piece's length along the axis (box_l), anchor-side info."""
    tr = pieces[binding.piece_id]
    op = getattr(binding, "offset_params", {}) or {}
    return float(op.get("face_len") or (tr.params or {}).get("box_l", 40.0))


# --- card class (M18 refactor: moved from base.py, verbatim) ---------------------------------
from knowledge.cards.base import ProvidedPiece, InteractionRule, _p  # noqa: E402
from ontology.schema import Citation, EmergentCheck  # noqa: E402
from knowledge.cards.base import MechanicalElementCard  # noqa: E402

def _pin_hinge_imposes() -> list:
    """The pin hinge imposes an assembly-phase constraint: the pin-insertion path must be open
    along the axis (§3.3). Expressed as an assembly/translation behaviour template that V-08
    requires the IR to register and attribute to the hinge."""
    from ontology.schema import Behavior, MotionSpec
    return [Behavior(id="_imposed_insertion_path", phase="assembly",
                     motion=MotionSpec(kind="translation"))]


class PinHingeCard(MechanicalElementCard):
    """Interleaved-knuckle pin hinge (MECHSYNTH §3.3), formalizing M0's proven assets. R1 was
    retired on this geometry (D18: ring-of-wedges preserved the bore where CoACD swallowed it).
    Geometry/derivations live in knowledge/cards/pin_hinge.py (host-agnostic per D-GEN-1).

    NOTE — the pin is a THIRD, separate piece the card cannot yet EMIT (DRAFT D-ONT-11,
    element-generated pieces). carve() adds knuckles/bores/chamfers to the two bound mounts and
    returns the loose pin geometry + dims; the pin is NOT fused into a knuckle (that seizes the
    hinge — the M0 lesson). Until D-ONT-11 is ruled, the caller declares the pin as a plan Piece.
    """
    card_id = "pin_hinge"
    has_functional_clearance = True  # the pin/bore rotational clearance (§3.3)
    taxonomy = {"working_motion": ("rotation", "regular"), "axis_relationship": "parallel",
                "connection_principle": None, "self_locking": False, "emergent_check": EmergentCheck(status="verified"),
                "compliance": "rigid", "kinematic_dof": "1 revolute"}  # M18 tag (D-M18-2)
    selection_notes = (
        "Use when one piece must ROTATE about a FIXED AXIS relative to another, repeatedly and "
        "through a large angle (a lid, a door, a flap). Realizes a use-phase rotation.\n"
        "Trade-offs: needs a loose PIN (a hardware piece the card provides, D-ONT-11) — a part "
        "count a snap-fit does not pay. Rotational clearance is the print clearance, so the fit is "
        "loose by design. IMPOSES an assembly constraint: the pin-insertion path must stay open "
        "along the axis (§3.3), which constrains where else you may put material.\n"
        "CAUTION — an over-centre lid (one whose CoM crosses the axis past ~90°) will FOLD FLAT "
        "under gravity unless a stop is added: physics showed 'opens >=90 AND returns closed' is "
        "unsatisfiable without one, so pair with the stop_flange PassiveFeature (D-M8-5).\n"
        "Do NOT use for straight-line travel (see slide_rail) or for a fasten-once joint (see "
        "snap_hook_cantilever).")
    citations = [Citation(doc="MECHSYNTH_SPEC_v0.1", section="§3.3 Card 1 — pin_hinge"),
                 Citation(doc="M0 hinge box (proven rig)", section="P-HINGE V-A/V-B"),
                 Citation(doc="DECISIONS_LOG", section="D-M8-5 (stop is a physics-derived requirement)")]
    ports = [_p("axis", "axis"), _p("mount_A", "face"), _p("mount_B", "face")]
    requires = {}
    imposes = _pin_hinge_imposes()  # §3.3: pin insertion path must be open (V-08)
    param_bounds = {"pin_d": (2.0, 6.0, "mm"), "knuckle_w": (4.0, 12.0, "mm"),
                    "knuckle_n": (3.0, 5.0, "count"), "clearance": (0.2, 0.4, "mm")}
    # D-ONT-11: the hinge PROVIDES the pin as a hardware piece (the third body). ④ instantiates it,
    # ⑤ resolves pin_d/pin_len via the card's formulas, ⑥ compiles it (geometry from carve()).
    provides_pieces = [ProvidedPiece("pin", ["pin_d", "pin_len"], role="pin")]
    # §3.3 placement rules (M0-cited; the derivations in pin_hinge.py enforce them).
    placement_rules = [
        "bore_d = pin_d + clearance  [§3.3: rotational clearance = print clearance]",
        "knuckle_od = pin_d + 2·knuckle_wall  [M0 hinge_box]",
        "lid-edge chamfer length >= pin_d/2 + clearance  [§3.3: pin lead-in]",
        "edge_margin (= face_len/2 − stack_w/2) >= knuckle_w  [§3.3]",
        "knuckle_n ∈ {3,5}; box takes even (outer) knuckles, lid odd (inner)  [M0 interleave]",
        "bore keep-out radius = bore_d/2 + clearance: nothing but knuckles inside it  [M0 D18]",
    ]

    def carve(self, host_parts, inst, bindings):
        """Add interleaved knuckles + shared bore to the two mounts, chamfer the lid, build the loose
        pin (DRAFT D-ONT-11 — no Piece home yet). Delegates to pin_hinge geometry (host-agnostic)."""
        from knowledge.cards.pin_hinge import carve as _carve
        return _carve(host_parts, inst, bindings)

    def collision_hint(self, inst):
        """Card-supplied ring-of-wedges per knuckle (D18/D21): the ONLY pathway that preserved the
        M0 bore (128% retention; CoACD swallowed it). Inner faces circumscribe the bore → never
        pinch the pin."""
        from knowledge.cards.pin_hinge import collision_primitives
        return collision_primitives(inst)
    def verification(self, ir, inst):
        """D-E-5: the hinge's own verification knowledge — P-HINGE in BOTH modes (§6.1/§6.3).

        Protocols are CARD knowledge (D5), never LLM-authored: which observables prove a hinge works,
        and at what thresholds, is exactly the handbook/M0 knowledge a card exists to hold. ④ attaches
        these at element selection; the model never writes a criterion.

        BOTH modes, always — the M0/D20 result made structural. V-A (declared joint) alone cannot
        tell a stop-less lid from a stopped one: its `range` silently supplies a stop the part does
        not have, and only V-B (contact-only) exposes it. A hinge card offering V-A alone would
        certify the fold-over."""
        from ontology.schema import Criterion, VerificationProtocol
        use_b = next((b for b in ir.behaviors
                      if b.realized_by == inst.id
                      and getattr(b.phase, "value", b.phase) == "use"
                      and getattr(b.motion.kind, "value", b.motion.kind) == "rotation"), None)
        if use_b is None:
            return []
        floor = float(getattr(use_b.motion, "range_value", None) or 90.0)
        clearance = float((inst.params or {}).get("clearance", 0.30))
        crits = [
            Criterion(name="opens", observable="theta_max_deg", op=">=", threshold=floor, unit="deg"),
            Criterion(name="pin_radial_retention", observable="pin_radial_max_mm", op="<=",
                      threshold=round(clearance + 0.1, 3), unit="mm"),
            Criterion(name="settles_closed", observable="theta_final_deg", op="<=", threshold=5.0,
                      unit="deg"),
            Criterion(name="no_travel_interference", observable="pen_travel_mm", op="<=",
                      threshold=0.20, unit="mm"),
        ]
        return [
            VerificationProtocol(
                id=f"P-HINGE-VA-{inst.id}", verifies=use_b.id, mode="V-A", seeds=5, seed_pass=4,
                actuation={"kind": "follower_force_ramp", "F_open_N": 0.15, "point": "free_edge_mid"},
                criteria=[c.model_copy() for c in crits], observables=[]),
            VerificationProtocol(
                id=f"P-HINGE-VB-{inst.id}", verifies=use_b.id, mode="V-B", seeds=5, seed_pass=4,
                actuation={"kind": "follower_force_ramp", "F_open_N": 0.15, "point": "free_edge_mid",
                           "release_at_theta_deg": 95.0},
                criteria=[c.model_copy() for c in crits], observables=[]),
        ]


    def resolve_piece_params(self, name, inst) -> dict:
        """D-ONT-11 ⑤: the pin's params from the hinge's own derivations. pin_len = stack_w + 6
        (M0: ~3 mm protrusion each side)."""
        if name != "pin":
            return {}
        from knowledge.cards.pin_hinge import dims_from
        g = dims_from(inst.params, face_len=40.0)  # face_len irrelevant to pin_d/pin_len
        return {"pin_d": round(g.pin_d, 4), "pin_len": round(g.pin_len, 4)}
