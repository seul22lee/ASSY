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
    side_y = g.rail_w / 2 + c + g.carriage_wall / 2
    side_z = head_under + g.head_h / 2
    bx(cx0, side_y, side_z, Lc, g.carriage_wall, g.head_h, "carriage")                # +Y side (yaw/Y retention, clearance c)
    bx(cx0, -side_y, side_z, Lc, g.carriage_wall, g.head_h, "carriage")               # −Y side
    lip_y = g.neck_w / 2 + c + g.shoulder_w / 2
    lip_top = head_under - c                                                          # gap c → lift stop
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
