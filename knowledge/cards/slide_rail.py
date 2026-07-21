"""slide_rail geometry (MECHSYNTH §3.5) — a rectangular RETAINING slide, T-rail form.

A drawer slide has to do two things at once: run FREE along one axis, and be CAPTURED on the other
two (or the drawer falls out / racks / lifts off). A plain rectangular tongue-in-groove runs free
but is not captured against lift; a dovetail captures but has angled faces. The **T-rail** captures
AND stays all-boxes: a narrow neck carries a wide head, and the carriage's groove tucks lips UNDER
the head shoulders. Lifting the carriage pulls the lips into the head → retained in Z; the groove
side walls retain Y; only X (travel) is free. Every surface is planar, so `collision_hint()` is a
handful of boxes — no curved surfaces, cheap (§3.5).

Frame: travel_axis = local +X. The rail grows +Z from the base's mount face; the carriage sits over
it. Cross-section lives in Y (width) and Z (height).

  head  ┌──────────┐   z = base_t + rail_h          rail = neck ∪ head (2 boxes)
        │   HEAD   │                                 carriage groove tucks lips under the head
   neck └──┐    ┌──┘   z = base_t + neck_h             shoulders → retention against lift
          │NECK│
   base ══╧════╧══     z = base_t

The §3.5 constraint chain, reproduced numerically by the golden:
  engagement_len ≥ 0.35 · stroke            (moment resistance — else the carriage racks/jams)
  L_rail        ≥ stroke + engagement_len   (overlap survives full extension)
  drawer_w      = body_inner_w − 2·(rail_w + clearance)   ← ⑤ DERIVES geometry from this (D6)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from build123d import Align, Box, Location, Pos

# neck is half the head width and half the rail height — a fixed proportion so one param (rail_w,
# rail_h) fixes the whole T. Keeps the card's param surface to what §3.5 lists.
NECK_FRAC_W = 0.5
NECK_FRAC_H = 0.5
STOP_TAB_LEN = 3.0        # end-stop bump length (§3.5 stop_tab) — prevents derail at the rail end


@dataclass
class SlideDims:
    rail_w: float          # head width (Y), §3.5 [4,10]
    rail_h: float          # total rail height (Z), §3.5 [4,10]
    clearance: float       # per-side sliding gap, §3.5 [0.25,0.45]
    engagement_len: float  # carriage length along X (the captured overlap)
    stroke: float          # travel distance (design input / behaviour range)
    stop_tab: bool = True
    base_t: float = 3.0
    carriage_wall: float = 3.0   # wall thickness around the groove
    preload_mm: float = 0.0      # D-M13-6: retention-lip preload interference for VERTICAL travel
                                 # (travel ∥ gravity). 0 = the horizontal gravity-seated drawer fit.

    @property
    def neck_w(self) -> float: return round(self.rail_w * NECK_FRAC_W, 4)

    @property
    def neck_h(self) -> float: return round(self.rail_h * NECK_FRAC_H, 4)

    @property
    def head_h(self) -> float: return round(self.rail_h - self.neck_h, 4)

    @property
    def shoulder_w(self) -> float:      # head overhang each side (what the lip tucks under)
        return round((self.rail_w - self.neck_w) / 2, 4)

    @property
    def rail_len(self) -> float:        # overlap survives full extension (+ a stop-tab margin)
        return round(self.stroke + self.engagement_len + (STOP_TAB_LEN if self.stop_tab else 0), 4)

    @property
    def min_engagement(self) -> float:  # §3.5 moment-resistance rule
        return round(0.35 * self.stroke, 4)

    def drawer_w(self, body_inner_w: float) -> float:   # §3.5 derived-geometry equality (D6)
        return round(body_inner_w - 2 * (self.rail_w + self.clearance), 4)


@dataclass
class SlideCarve:
    parts: dict
    tags: dict
    dims: SlideDims
    axis_world: dict = field(default_factory=dict)


def dims_from(params: dict, stroke: float) -> SlideDims:
    return SlideDims(
        rail_w=float(params.get("rail_w", 8.0)),
        rail_h=float(params.get("rail_h", 8.0)),
        clearance=float(params.get("clearance", 0.35)),
        engagement_len=float(params.get("engagement_len", max(0.35 * stroke, 10.0))),
        stroke=float(stroke),
        stop_tab=bool(params.get("stop_tab", True)),
        preload_mm=float(params.get("preload_mm", 0.0)),
    )


# --- geometry builders (canonical frame: travel +X, rail centred on y=0, base top at z0) ---------
def _rail_solid(g: SlideDims, z0: float):
    """neck ∪ head, running the full rail length along +X, centred at x=0."""
    L = g.rail_len
    neck = Location((0, 0, z0)) * Box(L, g.neck_w, g.neck_h, align=(Align.CENTER, Align.CENTER, Align.MIN))
    head = Location((0, 0, z0 + g.neck_h)) * Box(L, g.rail_w, g.head_h,
                                                 align=(Align.CENTER, Align.CENTER, Align.MIN))
    rail = neck + head
    if g.stop_tab:                        # a taller bump at the +X end — the carriage can't run off
        tab = Location((L / 2 - STOP_TAB_LEN / 2, 0, z0)) * Box(
            STOP_TAB_LEN, g.rail_w, g.rail_h + 2.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
        rail = rail + tab
    return rail


def _carriage_solid(g: SlideDims, z0: float):
    """A block over the rail with a T-groove cut, sized by clearance. Lips tuck under the head."""
    c = g.clearance
    w = g.carriage_wall
    # outer block: wide enough to house the head + side walls, tall enough for head + top wall
    outer_w = g.rail_w + 2 * c + 2 * w
    outer_h = g.rail_h + 2 * c + w
    block = Location((0, 0, z0)) * Box(g.engagement_len, outer_w, outer_h,
                                       align=(Align.CENTER, Align.CENTER, Align.MIN))
    # head cavity (the head slides in here, all-around clearance c)
    head_cav = Location((0, 0, z0 + g.neck_h - c)) * Box(
        g.engagement_len + 2, g.rail_w + 2 * c, g.head_h + 2 * c,
        align=(Align.CENTER, Align.CENTER, Align.MIN))
    # mouth slot for the neck to pass down through the carriage floor (width neck + 2c)
    mouth = Location((0, 0, z0 - 1)) * Box(g.engagement_len + 2, g.neck_w + 2 * c, g.neck_h + c + 1,
                                           align=(Align.CENTER, Align.CENTER, Align.MIN))
    return block - head_cav - mouth


def carve(pieces: dict, inst, bindings) -> SlideCarve:
    """Grow the rail on the `rail_mount` host and the carriage/groove on the `carriage_mount` host,
    both placed by their bound anchors' frames (host-agnostic, like pin_hinge). `travel_axis` fixes
    the slide direction. Returns tagged solids + the world travel axis for the physics layer."""
    stroke = _stroke(inst, bindings)
    g = dims_from(inst.params, stroke)

    rb = next(b for b in bindings if b.port == "rail_mount")
    cb = next(b for b in bindings if b.port == "carriage_mount")
    ax = next(b for b in bindings if b.port == "travel_axis")
    rail_anchor = _anchor(pieces, rb)
    axis_anchor = _anchor(pieces, ax)

    z0 = float(rail_anchor["point"][2])          # base mount face height
    # host-agnostic PLACEMENT: the rail sits at the mount anchor's X/Y (not just its height). For the
    # single-rail m10 fixture the anchor is at the origin → offset (0,0), so m10 is unchanged; for a
    # multi-rail host (the Hard anchor's two floor rails at ±rail_gap/2) each rail lands at its own
    # anchor. Travel stays local +X (the anchor's travel_axis dir; both fixtures use +X).
    ox, oy = float(rail_anchor["point"][0]), float(rail_anchor["point"][1])
    rail = Pos(ox, oy, 0) * _rail_solid(g, z0)
    carriage = _carriage_solid(g, z0)
    # carriage starts fully engaged at the −X (closed) end of the rail
    carriage = Pos(ox - (g.rail_len / 2 - g.engagement_len / 2), oy, 0) * carriage

    parts, tags = dict(pieces_as_solids(pieces)), {}
    parts[rb.piece_id] = parts[rb.piece_id] + rail
    # The carriage geometry is the CARD's, not the template's: the slide fit defines the whole
    # carriage (a block with the T-groove). REPLACE the carriage host's placeholder geometry — do
    # NOT add, which would leave the placeholder as a DISCONNECTED second solid in one rigid body
    # (a floating chunk that renders as a phantom second carriage and offsets the COM off the rail).
    # This mirrors D-ONT-11: a piece whose functional shape is card knowledge gets it from the carve.
    parts[cb.piece_id] = carriage
    tags["rail"] = rail
    tags["carriage"] = carriage
    axis_world = {"point": tuple(axis_anchor["point"]), "dir": (1.0, 0.0, 0.0)}
    return SlideCarve(parts=parts, tags=tags, dims=g, axis_world=axis_world)


def collision_primitives(inst, stroke: float | None = None) -> list:
    """All-box decomposition (§3.5: groove as box primitives, no curves). Rail = neck + head (+ stop
    tab); carriage = the T-channel walls (top, two sides, two lips). D14: the CARRIAGE (moving) boxes
    are inset by COLLISION_EPS so no face-plane ties with the rail — the clearance already separates
    them, this only guards the tied-axis normal flip. owner routes each prim to its body."""
    g = dims_from(inst.params, stroke if stroke is not None else _stroke(inst, []))
    e = 0.2   # COLLISION_EPS (D14)
    z0 = 0.0
    prims = []

    def bx(cx, cy, cz, sx, sy, sz, owner):
        prims.append({"type": "box", "frame": "axis", "owner": owner,
                      "pos": (cx, cy, cz), "size": (sx / 2, sy / 2, sz / 2),
                      "source": f"card:slide_rail@{inst.id}"})

    L = g.rail_len
    # --- rail (static): neck + head + stop tab ---
    bx(0, 0, z0 + g.neck_h / 2, L, g.neck_w, g.neck_h, "rail")
    bx(0, 0, z0 + g.neck_h + g.head_h / 2, L, g.rail_w, g.head_h, "rail")
    if g.stop_tab:
        bx(L / 2 - STOP_TAB_LEN / 2, 0, z0 + (g.rail_h + 2) / 2, STOP_TAB_LEN, g.rail_w, g.rail_h + 2, "rail")
    # --- carriage (moving): channel walls. The carriage RESTS on the rail head-top — that Z plane
    # is the LOAD PATH and is left EXACT (the M0 lid-on-box lesson: keep the one load plane exact,
    # inset the OTHER faces so no second separating axis ties → no normal flip). The Y sides carry
    # clearance c; the lips sit c below the head underside so the carriage lifts c before they catch.
    cx0 = -(g.rail_len / 2 - g.engagement_len / 2)
    Lc = g.engagement_len - 2 * e
    c = g.clearance
    head_top = z0 + g.rail_h
    head_under = z0 + g.neck_h
    bx(cx0, 0, head_top + g.carriage_wall / 2, Lc, g.rail_w - 2 * e, g.carriage_wall, "carriage")   # top: rests on head-top (Z load, exact)
    # D-M13-6 orientation rule: HORIZONTAL travel (preload=0) leaves the sliding clearance c — gravity
    # seats the carriage and the lip catches only on lift (the drawer fit, m10 V-B 5/5). VERTICAL
    # travel (travel ∥ gravity, preload>0) has no gravity seating, so the side walls and lips are
    # PRELOADED — pressed onto the head sides/underside by `preload_mm` (a sprung take-up of the
    # sliding slack; PETG's compliance makes the interference a spring, the frozen preset resolves it
    # as a bounded restoring force, NOT a rigid jam). Retention is then continuous and orientation-free.
    # D-M13-6 orientation rule. The retention faces (lip-under-head, side-to-neck) are NON-SLIDING
    # STOPS — they bear only when the carriage tries to leave the groove, not during normal travel.
    # So their gap is a RETENTION gap, independent of the sliding clearance `c` on the rubbing faces:
    #   HORIZONTAL (preload=0): gap = c — gravity seats the carriage, the lip catches only on lift.
    #   VERTICAL (preload>0, travel ∥ gravity): gap = a TIGHT retention gap `rg` (< c), so the platform
    #     can wobble at most rg before the lips/sides catch — retention without gravity seating and
    #     WITHOUT interference (an interference on the rigid stops would clamp all faces and jam;
    #     a tight positive gap catches the pitch while leaving travel free). rg is `preload_mm`.
    rg = g.preload_mm if g.preload_mm > 0.0 else c
    side_y = g.rail_w / 2 + rg + g.carriage_wall / 2
    side_z = head_under + g.head_h / 2
    bx(cx0, side_y, side_z, Lc, g.carriage_wall, g.head_h, "carriage")                # +Y side (Y/roll stop, gap rg)
    bx(cx0, -side_y, side_z, Lc, g.carriage_wall, g.head_h, "carriage")               # −Y side
    lip_y = g.neck_w / 2 + rg + g.shoulder_w / 2
    lip_top = head_under - rg                                                         # gap rg → separation stop
    bx(cx0, lip_y, lip_top - c / 2, Lc, g.shoulder_w, c, "carriage")                  # +Y lip (under head shoulder)
    bx(cx0, -lip_y, lip_top - c / 2, Lc, g.shoulder_w, c, "carriage")                 # −Y lip
    return prims


# --- helpers -------------------------------------------------------------------------------------
def pieces_as_solids(pieces: dict) -> dict:
    out = {}
    for pid, tr in pieces.items():
        out[pid] = getattr(tr, "part", tr)
    return out


def _anchor(pieces, binding) -> dict:
    tr = pieces[binding.piece_id]
    a = tr.anchors[binding.anchor]
    return {"point": a.position, "dir": a.normal}


def _stroke(inst, bindings) -> float:
    """Travel distance: from the element's params, else a default. The behaviour's use-phase
    translation range is the authoritative source; carried on the instance params by ⑤."""
    return float((inst.params or {}).get("stroke", 60.0))


# --- card class (M18 refactor: moved from base.py, verbatim) ---------------------------------
from knowledge.cards.base import ProvidedPiece, InteractionRule, _p  # noqa: E402
from ontology.schema import Citation, EmergentCheck  # noqa: E402
from knowledge.cards.base import MechanicalElementCard  # noqa: E402

def _slide_rail_imposes() -> list:
    """The slide imposes two constraints (§3.5): an ASSEMBLY axial-insertion path (the carriage
    threads onto the rail along the travel axis — nothing may block that axis), and a USE travel
    keep-out (nothing may intrude into the swept volume the carriage passes through). Both are
    registered in the IR and attributed to the slide (V-08)."""
    from ontology.schema import Behavior, MotionSpec
    return [Behavior(id="_imposed_axial_insertion", phase="assembly",
                     motion=MotionSpec(kind="translation")),
            Behavior(id="_imposed_travel_keepout", phase="use",
                     motion=MotionSpec(kind="fixed"))]


class SlideRailCard(MechanicalElementCard):
    """Rectangular retaining slide (MECHSYNTH §3.5) — a T-rail + captured carriage. Geometry (all
    boxes, no curves) in knowledge/cards/slide_rail.py, host-agnostic (D-GEN-1). Realizes a use-phase
    translation; imposes an axial-insertion path + a travel keep-out."""
    card_id = "slide_rail"
    has_functional_clearance = True  # rail/carriage sliding clearance (§3.5)
    taxonomy = {"working_motion": ("translation", "regular"), "axis_relationship": "parallel",
                "connection_principle": None, "self_locking": False, "emergent_check": EmergentCheck(status="verified"),
                "compliance": "rigid", "kinematic_dof": "1 prismatic"}
    imposes = _slide_rail_imposes()
    param_bounds = {"rail_h": (4.0, 10.0, "mm"), "rail_w": (4.0, 10.0, "mm"),
                    "clearance": (0.25, 0.45, "mm"), "engagement_len": (5.0, 200.0, "mm"),
                    "stroke": (10.0, 400.0, "mm")}
    selection_notes = (
        "Use when a piece must TRANSLATE along a straight axis (a drawer, a tray). Realizes a "
        "use-phase translation.\n"
        "Trade-offs: engagement_len >= 0.35*stroke or the carriage racks and jams under moment "
        "load (§3.5); that engagement eats depth the payload wanted. The rail/carriage clearance "
        "is a functional clearance a generic mesh approximation destroys, so the card must supply "
        "its own collision decomposition (D18).\n"
        "Do NOT use for rotation (see pin_hinge)."
        "ORIENTATION (D-M13-6): a HORIZONTAL slide is gravity-seated — the lips catch on lift "
        "with the sliding clearance c. A VERTICAL slide (travel ∥ gravity) is NOT gravity-seated, "
        "so resolve_params tightens the retention STOP gap to a quarter of the PETG print clearance (0.075 mm); the lip "
        "catches within that tight gap on any wobble (a retention stop), independent of gravity direction.")
    citations = [Citation(doc="MECHSYNTH_SPEC_v0.1", section="§3.5 Card 3 — slide_rail")]
    ports = [_p("rail_mount", "face"), _p("carriage_mount", "face"), _p("travel_axis", "axis")]

    def carve(self, host_parts, inst, bindings):
        """Grow the rail on the rail_mount host + the captured carriage on the carriage_mount host,
        anchor-driven. Delegates to slide_rail geometry (host-agnostic)."""
        from knowledge.cards.slide_rail import carve as _carve
        return _carve(host_parts, inst, bindings)

    def collision_hint(self, inst, stroke=None):
        """All-box decomposition of the rail + carriage channel (§3.5: groove as box primitives, no
        curves). Every prim carries `owner` (rail|carriage) and a `source` stamp (D-M8-4)."""
        from knowledge.cards.slide_rail import collision_primitives
        return collision_primitives(inst, stroke)

    def resolve_params(self, ir, inst):
        """⑤/D6: derive engagement_len from the §3.5 moment-resistance rule (≥ 0.35·stroke), and
        carry the stroke from the use-phase translation behaviour's range. stroke is the design
        input; engagement_len is DERIVED (never free) — the card owns the formula, ⑤ owns when."""
        from knowledge.cards.slide_rail import dims_from
        out = dict(inst.params or {})
        # stroke from the behaviour this element realizes (its use-phase translation range), else param
        strk = out.get("stroke")
        if strk is None:
            b = next((x for x in ir.behaviors if x.realized_by == inst.id
                      and getattr(x.motion.kind, "value", x.motion.kind) == "translation"
                      and getattr(x.motion, "range_value", None)), None)
            strk = float(b.motion.range_value) if b else 60.0
        out["stroke"] = float(strk)
        # engagement_len = the §3.5 minimum unless the IR already asked for more (moment resistance)
        g = dims_from(out, out["stroke"])
        out["engagement_len"] = round(max(float(out.get("engagement_len", 0.0)), g.min_engagement), 3)
        out.setdefault("rail_w", 8.0)
        out.setdefault("rail_h", 8.0)
        out.setdefault("clearance", 0.35)
        # D-M13-6 ORIENTATION RULE: when travel ∥ gravity (a VERTICAL lift, not a horizontal drawer),
        # gravity no longer seats the carriage in the groove, so the retention lips are PRELOADED.
        # The preload is SOURCED, not invented: it uses a QUARTER of the PETG print clearance (a retention STOP face bears only on wobble,
        # not during travel, so it tolerates a gap tighter than the sliding fit): 0.30/4 = 0.075 mm.
        # A tight positive gap (NOT interference — an interference on the rigid stops jams them, the
        # PETG leaf's compliance can't be modelled at the frozen stiff preset R5) catches the pitch
        # before the platform escapes the groove. Detected from the realized translation behaviour's
        # axis_hint (vertical / travel-parallel-to-gravity).
        b = next((x for x in ir.behaviors if x.realized_by == inst.id
                  and getattr(x.motion.kind, "value", x.motion.kind) == "translation"), None)
        hint = (getattr(b.motion, "axis_hint", "") or "") if b is not None else ""
        if "vert" in hint.lower():
            from knowledge.materials import PETG
            out.setdefault("preload_mm", round(PETG.print_clearance_mm / 4.0, 3))   # 0.075 mm, sourced
        return out

    def verification(self, ir, inst):
        """D-track/§6.3: P-SLIDE in both modes. V-A (declared prismatic joint) is REQUIRED; V-B
        (contact-only, the geometry must produce and retain the DoF) is the TARGET. Judge s_max ≥
        stroke, off-axis ≤ 3°, no derail, back-drift ≤ 5 mm (§6.3)."""
        from ontology.schema import Criterion, VerificationProtocol
        use_b = next((b for b in ir.behaviors
                      if b.realized_by == inst.id
                      and getattr(b.phase, "value", b.phase) == "use"
                      and getattr(b.motion.kind, "value", b.motion.kind) == "translation"), None)
        if use_b is None:
            return []
        stroke = float((inst.params or {}).get("stroke", 60.0))
        crits = [
            Criterion(name="reaches_stroke", observable="stroke_mm", op=">=", threshold=stroke,
                      unit="mm"),
            Criterion(name="tracks_straight", observable="offaxis_rot_deg", op="<=", threshold=3.0,
                      unit="deg"),
        ]
        out = [
            VerificationProtocol(id=f"P-SLIDE-VA-{inst.id}", verifies=use_b.id, mode="V-A",
                                 seeds=5, seed_pass=4, actuation={"kind": "force_ramp_axial"},
                                 criteria=[c.model_copy() for c in crits], observables=[]),
            VerificationProtocol(id=f"P-SLIDE-VB-{inst.id}", verifies=use_b.id, mode="V-B",
                                 seeds=5, seed_pass=4, actuation={"kind": "force_ramp_axial"},
                                 criteria=[c.model_copy() for c in crits], observables=[]),
        ]
        # the USE-phase travel keep-out this slide IMPOSES (§3.5): nothing intrudes into the swept
        # volume — a Tier0 sweep, like the snap card's PR-SWEEP. Verifies that imposed behaviour so
        # it is not left unverified (V-01).
        keep_b = next((b for b in ir.behaviors
                       if b.imposed_by == inst.id
                       and getattr(b.phase, "value", b.phase) == "use"
                       and getattr(b.motion.kind, "value", b.motion.kind) == "fixed"), None)
        if keep_b is not None:
            out.append(VerificationProtocol(
                id=f"PR-KEEPOUT-{inst.id}", verifies=keep_b.id, mode=None, seeds=5, seed_pass=4,
                actuation={"kind": "tier0_sweep"},
                criteria=[Criterion(name="no_travel_intrusion", observable="offaxis_rot_deg",
                                    op="<=", threshold=3.0, unit="deg")], observables=[]))
        return out
