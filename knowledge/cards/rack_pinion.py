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


# --- card class (M18 refactor: moved from base.py, verbatim) ---------------------------------
from knowledge.cards.base import ProvidedPiece, InteractionRule, _p  # noqa: E402
from ontology.schema import Citation, EmergentCheck  # noqa: E402
from knowledge.cards.base import MechanicalElementCard  # noqa: E402

def _rack_pinion_imposes() -> list:
    """The rack_pinion imposes an assembly-phase constraint: the pinion must be inserted onto its
    shaft along the axis, and the rack threaded into mesh (§3.6). One assembly/translation behaviour,
    registered and attributed to the element (V-08)."""
    from ontology.schema import Behavior, MotionSpec
    return [Behavior(id="_imposed_mesh_assembly", phase="assembly",
                     motion=MotionSpec(kind="translation"))]


class RackPinionCard(MechanicalElementCard):
    """Spur rack & pinion (MECHSYNTH §3.6, amended) — the true INVOLUTE pinion (M1: the trapezoid is
    dead, D-M1-1) driving a straight rack. Realizes a use-phase rot_to_trans transmission. Geometry
    in knowledge/cards/rack_pinion.py (reuses M1's involute + L3 wedge decomposition)."""
    card_id = "rack_pinion"
    has_functional_clearance = True  # tooth-flank backlash (§3.6, D21)
    taxonomy = {"working_motion": ("rot_to_trans", "regular"), "axis_relationship": "parallel",
                "connection_principle": None, "self_locking": False, "emergent_check": EmergentCheck(status="deferred", reason="tooth flank contact is CURVED; bidirectional V-B diverges at the frozen preset (R2b, D-M1-5/-7, m17)", risk="declared-shaft ratio is V-A-verified; emergent bidirectional meshing / backlash-crossing under load is not physics-verified — formalizes the card v_b_gap/shape_assert"),
                "compliance": "rigid", "kinematic_dof": "1 rot coupled to 1 trans"}  # curved contact -> V-B deferred (R2b)
    imposes = _rack_pinion_imposes()
    # §3.6 AMENDED: module bounds are LARGE {5,6}, and the reason is SIMULATION STABILITY, not
    # mechanics — mechanically a smaller module meshes fine, but R2b (D-M1-2/-3/-5) showed the rigid
    # contact rig is dt-unstable below the large-module range at the frozen preset. The bounds encode
    # a physics-of-verification constraint, and selection_notes says so explicitly (D-M1-4 rule text).
    param_bounds = {"module": (5.0, 6.0, "mm"), "z_pinion": (10.0, 24.0, "count"),
                    "pressure_angle_deg": (20.0, 20.0, "deg"), "face_w": (4.0, 10.0, "mm"),
                    "backlash": (0.1, 0.25, "mm"), "stroke": (20.0, 400.0, "mm")}
    selection_notes = (
        "Use when ROTATION must be converted to TRANSLATION at a defined ratio (a knob that drives "
        "a drawer). Realizes a use-phase rot_to_trans transmission.\n"
        "WHY THE MODULE BOUNDS ARE LARGE ({5,6}, not the mechanically-natural 1-2): the bound is a "
        "CONTACT-SIMULATION-STABILITY requirement, NOT a mechanical one (D-M1-2/-4). Mechanically a "
        "fine-module rack meshes perfectly; but the rigid convex-facet contact rig is dt-unstable "
        "below the large-module range at the frozen preset (R5) — larger teeth = gentler contact "
        "geometry = a larger stable timestep. The card mandates the large module so the geometry it "
        "produces is the geometry the verifier can actually simulate.\n"
        "STANDING R2b-OPEN FLAG: contact-only (V-B) BIDIRECTIONAL meshing is NOT stable — the "
        "reversal backlash-crossing impact diverges at the frozen preset, and no module or preset "
        "param fixes it (a contact-FORMULATION limit, D-M1-5/-7). FORWARD meshing IS demonstrable "
        "(ratio −0.50). So a rack_pinion is verified V-A (declared-shaft ratio); its bidirectional "
        "contact verification is DEFERRED to a versioned preset_v2 or a pitch-cylinder proxy.\n"
        "Prefer a simpler element if the task does not genuinely need ratio'd rotation→translation.")
    citations = [Citation(doc="MECHSYNTH_SPEC_v0.1", section="§3.6 Card 4 — rack_pinion (amended)"),
                 Citation(doc="DECISIONS_LOG", section="D-M1-1/-2/-4/-5/-7 (involute; R2a retired; R2b frozen)"),
                 Citation(doc="M1 gear rig", section="gear_geom involute + L3 flank_wedges")]
    ports = [_p("pinion_axis", "axis"), _p("rack_mount", "face"), _p("mesh_line", "edge")]

    def carve(self, host_parts, inst, bindings):
        """Place the involute pinion on its shaft + the straight rack in mesh (host-agnostic)."""
        from knowledge.cards.rack_pinion import carve as _carve
        return _carve(host_parts, inst, bindings)

    def collision_hint(self, inst, n_wedge=4):
        """L3 involute flank-wedge decomposition (§3.6, D18/D21) — the card's OWN convex hint;
        mujoco.sdf.gear is FORBIDDEN. Deferred with V-B this session (V-A uses no tooth contact)."""
        from knowledge.cards.rack_pinion import collision_primitives
        return collision_primitives(inst, n_wedge)

    def resolve_params(self, ir, inst):
        """⑤/D6: stroke from the use-phase transmission behaviour's range; module snapped INTO the
        {5,6} stability band (never below); z_pinion carried. The card owns the §3.6 formulas."""
        out = dict(inst.params or {})
        b = next((x for x in ir.behaviors if x.realized_by == inst.id
                  and getattr(x.motion.kind, "value", x.motion.kind) == "rot_to_trans"), None)
        if b is not None and getattr(b.motion, "range_value", None):
            out["stroke"] = float(b.motion.range_value)
        out.setdefault("stroke", 120.0)
        out.setdefault("z_pinion", 12)
        # snap the module up into the stability band [5,6] (R2b — never below)
        m = float(out.get("module", 5.0))
        out["module"] = min(6.0, max(5.0, m))
        out.setdefault("backlash", 0.20)
        out.setdefault("face_w", 8.0)
        out.setdefault("pressure_angle_deg", 20.0)
        return out

    def verification(self, ir, inst):
        """§6.3 P-GEAR, V-A ONLY (the standing requirement, D-M1-7). V-A checks the declared-shaft
        transmission ratio: |s / (θ·r_pitch) − 1| ≤ 5% over N revolutions. **V-B (emergent contact
        ratio) is DOWNGRADED** — the bidirectional reversal is R2b-open; the gap is NAMED in the
        protocol so a design never silently claims contact-level meshing it cannot show."""
        from ontology.schema import Criterion, VerificationProtocol
        use_b = next((b for b in ir.behaviors
                      if b.realized_by == inst.id
                      and getattr(b.phase, "value", b.phase) == "use"
                      and getattr(b.motion.kind, "value", b.motion.kind) == "rot_to_trans"), None)
        if use_b is None:
            return []
        return [VerificationProtocol(
            id=f"P-GEAR-VA-{inst.id}", verifies=use_b.id, mode="V-A", seeds=5, seed_pass=4,
            actuation={"kind": "shaft_velocity", "n_rev": 3.0,
                       "v_b_gap": "bidirectional contact meshing PENDING preset_v2 (R2b/D-M1-7); "
                                  "forward V-B demonstrable, reversal backlash-crossing diverges"},
            criteria=[Criterion(name="transmission_ratio", observable="transmission_residual",
                                op="<=", threshold=0.05, unit="")], observables=[])]


# --------------------------------------------------------------------------------------
# PassiveFeature cards (D-ONT-4). These constrain/support; they realize nothing.
# --------------------------------------------------------------------------------------
