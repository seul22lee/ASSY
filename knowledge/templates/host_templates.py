"""box_shell + lid_panel host templates (SNAPFIT §4-⑥).

Each returns a TemplateResult(part, anchors): the build123d solid plus its DECLARED anchors as
metadata. Anchor names are exactly those T-S1's bindings reference (V-02):
    box_shell : side_wall_left, side_wall_right   (the ±X wall outer faces — catch-window sites)
    lid_panel : rim_underside_left, rim_underside_right  (lid underside near ±X edges — hook roots)

Frame: origin at box centre of the XY plane, floor at z=0, +Z up. Units mm. The lid sits ON the
box (z ∈ [box_h, box_h+lid_t]); an anchor's `normal` points OUT of the material at that feature.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from build123d import Align, Box, Cylinder, Location, Part, Rotation


@dataclass(frozen=True)
class AnchorGeom:
    """A named geometric feature emitted alongside geometry (SNAPFIT §4-⑥: anchors as metadata).
    position/normal are in the piece's own frame, mm. `kind` matches the ontology PortKind."""
    name: str
    kind: str                       # "face" | "edge" | "axis" | "point"
    position: tuple[float, float, float]
    normal: tuple[float, float, float]


@dataclass
class TemplateResult:
    part: Part
    anchors: dict[str, AnchorGeom] = field(default_factory=dict)
    params: dict = field(default_factory=dict)

    def anchor(self, name: str) -> AnchorGeom:
        return self.anchors[name]


# --- defaults (T-S1 box). Real values arrive from stage 5 later; carried here so the template
#     is runnable standalone this session. ------------------------------------------------
BOX_DEFAULTS = {"box_l": 80.0, "box_w": 60.0, "box_h": 40.0, "wall": 2.0}
LID_DEFAULTS = {"box_l": 80.0, "box_w": 60.0, "lid_t": 3.0}
# how far inboard of each side wall the hook root sits (so the beam hangs just inside the wall)
HOOK_INSET = 3.0
# D14 / M0 COLLISION_EPS: the MOVING piece's seating primitive is inset laterally so it never shares
# a face-plane with the static rim (the drawer lesson — a tied separating axis flips the contact
# normal). The load-bearing Z seating plane is left EXACT.
COLLISION_EPS = 0.2  # mm


def _bx(cx, cy, cz, sx, sy, sz, frame="world", source=None):
    """A box collision primitive: centre (mm) + FULL extents (mm) → half-extents at emit time.
    `source` (D-M8-4) names the declared host template this geom traces to; the MJCF layer refuses
    any collision geom whose source does not resolve to a declared IR entity."""
    return {"type": "box", "frame": frame, "pos": (cx, cy, cz),
            "size": (sx / 2, sy / 2, sz / 2), "source": source}


def box_shell_collision(**params) -> list:
    """Floor + four walls (M0 primitives_for box_shell). Static host — no COLLISION_EPS inset."""
    p = {**BOX_DEFAULTS, **params}
    L, W, H, wall = p["box_l"], p["box_w"], p["box_h"], p["wall"]
    src = "template:box_shell"
    return [_bx(0, 0, wall / 2, L, W, wall, source=src),                        # floor
            _bx(0, -(W - wall) / 2, H / 2, L, wall, H, source=src),             # rear wall
            _bx(0, (W - wall) / 2, H / 2, L, wall, H, source=src),              # front wall
            _bx(-(L - wall) / 2, 0, H / 2, wall, W - 2 * wall, H, source=src),  # left wall
            _bx((L - wall) / 2, 0, H / 2, wall, W - 2 * wall, H, source=src)]   # right wall


def lid_panel_collision(**params) -> list:
    """The lid panel, INSET by COLLISION_EPS in X and Y (D14) so its edges do not tie with the box
    wall outer faces; the Z seating plane (lid underside on the wall tops) is left exact — that is
    the load path (M0 lid_panel primitive)."""
    p = {**LID_DEFAULTS, **params}
    L, W, lid_t = p["box_l"], p["box_w"], p["lid_t"]
    H = p.get("box_h", BOX_DEFAULTS["box_h"])
    e = COLLISION_EPS
    return [_bx(0, 0, H + lid_t / 2, L - 2 * e, W - 2 * e, lid_t, source="template:lid_panel")]


TEMPLATE_COLLISION = {"box_shell": box_shell_collision, "lid_panel": lid_panel_collision}


def box_shell(**params) -> TemplateResult:
    """Open-top box: four walls + floor. Catch windows are cut later by carve()."""
    p = {**BOX_DEFAULTS, **params}
    L, W, H, wall = p["box_l"], p["box_w"], p["box_h"], p["wall"]

    shell = Box(L, W, H, align=(Align.CENTER, Align.CENTER, Align.MIN))
    cavity = Location((0, 0, wall)) * Box(
        L - 2 * wall, W - 2 * wall, H,  # runs past the top face -> open top
        align=(Align.CENTER, Align.CENTER, Align.MIN))
    part = shell - cavity

    z_mid = H * 0.7  # where the catch window sits — anchor marks the wall INNER face there, so the
    #                  hook nose (grown from the lid) reaches it and seats in the window (not past
    #                  the outer wall). normal points inward (toward the cavity / the hook).
    xin = L / 2 - wall
    # hinge anchors (pin_hinge card): the axis runs along +X behind the REAR (−Y) wall at lid
    # height, offset out by a nominal knuckle radius so the lid clears the box on opening (M0).
    y_rear = -W / 2
    anchors = {
        "side_wall_left": AnchorGeom("side_wall_left", "face", (-xin, 0.0, z_mid), (1, 0, 0)),
        "side_wall_right": AnchorGeom("side_wall_right", "face", (xin, 0.0, z_mid), (-1, 0, 0)),
        # front wall inner face (a latch catch site distinct from the ±X side walls)
        "front_wall_inner": AnchorGeom("front_wall_inner", "face", (0.0, W / 2 - wall, z_mid), (0, -1, 0)),
        "rear_top_edge": AnchorGeom("rear_top_edge", "axis", (0.0, y_rear - 4.0, H), (1, 0, 0)),
        "rear_wall_outer": AnchorGeom("rear_wall_outer", "face", (0.0, y_rear, H * 0.75), (0, -1, 0)),
    }
    return TemplateResult(part=part, anchors=anchors, params=p)


def lid_panel(**params) -> TemplateResult:
    """Flat lid that seats on top of the box. Hooks are grown from its underside by carve()."""
    p = {**LID_DEFAULTS, **params}
    L, W, lid_t = p["box_l"], p["box_w"], p["lid_t"]
    z0 = p.get("box_h", BOX_DEFAULTS["box_h"])  # lid sits on top of the box

    part = Location((0, 0, z0)) * Box(L, W, lid_t, align=(Align.CENTER, Align.CENTER, Align.MIN))

    # underside anchors near the ±X edges; normal points DOWN (−Z) — the hook grows downward.
    xr = L / 2 - HOOK_INSET
    yr = W / 2 - HOOK_INSET
    anchors = {
        "rim_underside_left": AnchorGeom("rim_underside_left", "face", (-xr, 0.0, z0), (0, 0, -1)),
        "rim_underside_right": AnchorGeom("rim_underside_right", "face", (xr, 0.0, z0), (0, 0, -1)),
        # front-edge underside (a latch beam root on the FRONT of the lid, +Y)
        "front_edge_underside": AnchorGeom("front_edge_underside", "face", (0.0, yr, z0), (0, 0, -1)),
        # rear edge underside — the hinge lid mount (mount_B); the knuckles/tab attach here
        "rear_edge_underside": AnchorGeom("rear_edge_underside", "face", (0.0, -W / 2, z0), (0, 0, -1)),
        # the stop_flange contact site (D-ONT-4): a rearward flange grows from here, swings down as
        # the lid opens and bottoms out on the box's rear wall. Normal points rearward (−Y).
        "stop_flange_face": AnchorGeom("stop_flange_face", "face", (0.0, -W / 2, z0), (0, -1, 0)),
    }
    return TemplateResult(part=part, anchors=anchors, params={**p, "box_h": z0})


PANEL_DEFAULTS = {"plate_l": 60.0, "plate_w": 40.0, "plate_t": 3.0, "rail_h": 22.0,
                  "rail_t": 3.0, "board_t": 3.0, "board_z": 18.0}


def flat_panel_mount(**params) -> TemplateResult:
    """Board-clip host (Bayer p.5 Fig.1): a base plate with two upstand rails; snap hooks grow UP
    from the rail inner faces and their noses curl inward over a retained flat board. A DIFFERENT
    host geometry from the box — used to prove D-GEN-1 (the same carve attaches via anchors).

    Anchors `rail_inner_left/right` sit on the rail inner face BELOW the board's top edge, normal
    +Z (hooks grow up); their paired catch anchors live on the board (see retained_board)."""
    p = {**PANEL_DEFAULTS, **params}
    L, W, t, rh, rt = p["plate_l"], p["plate_w"], p["plate_t"], p["rail_h"], p["rail_t"]
    part = Box(L, W, t, align=(Align.CENTER, Align.CENTER, Align.MIN))          # base plate
    for sx in (-1, 1):
        cx = sx * (L / 2 - rt / 2)
        # rails overlap the plate by 0.5 mm so the union merges into one solid (D14 lesson)
        part += Location((cx, 0, t - 0.5)) * Box(rt, W, rh + 0.5,
                                                 align=(Align.CENTER, Align.CENTER, Align.MIN))
    x_inner = L / 2 - rt                                                        # rail inner face
    z_root = t + p["board_z"] - 4.0                                             # below the board top
    anchors = {
        "rail_inner_left": AnchorGeom("rail_inner_left", "face", (-x_inner, 0.0, z_root), (0, 0, 1)),
        "rail_inner_right": AnchorGeom("rail_inner_right", "face", (x_inner, 0.0, z_root), (0, 0, 1)),
    }
    return TemplateResult(part=part, anchors=anchors, params=p)


def retained_board(**params) -> TemplateResult:
    """The flat part the clip retains — a plate sitting between the rails. Catch anchors
    `board_edge_left/right` mark its top edges, where the hook noses catch (normal points inward)."""
    p = {**PANEL_DEFAULTS, **params}
    L, W, t, bt, bz = p["plate_l"], p["plate_w"], p["plate_t"], p["board_t"], p["board_z"]
    bl, bw = L - 2 * p["rail_t"] - 4.0, W - 6.0                                 # fits between rails
    z0 = t + bz
    part = Location((0, 0, z0)) * Box(bl, bw, bt, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ztop = z0 + bt
    anchors = {
        "board_edge_left": AnchorGeom("board_edge_left", "face", (-bl / 2, 0.0, ztop), (1, 0, 0)),
        "board_edge_right": AnchorGeom("board_edge_right", "face", (bl / 2, 0.0, ztop), (-1, 0, 0)),
    }
    return TemplateResult(part=part, anchors=anchors, params={**p, "board_l": bl})




def slide_base(**params) -> TemplateResult:
    """Minimal slide fixture host — a flat base plate the rail grows on (§3.5 / D-track fixture).
    Anchors: `rail_face` (top face, where the T-rail grows, +Z) + `travel_edge` (the +X travel axis)."""
    p = {"base_l": 120.0, "base_w": 40.0, "base_t": 3.0, **params}
    L, W, T = p["base_l"], p["base_w"], p["base_t"]
    part = Box(L, W, T, align=(Align.CENTER, Align.CENTER, Align.MIN))
    anchors = {
        "rail_face": AnchorGeom("rail_face", "face", (0.0, 0.0, T), (0, 0, 1)),
        "travel_edge": AnchorGeom("travel_edge", "axis", (0.0, 0.0, T), (1, 0, 0)),
    }
    return TemplateResult(part=part, anchors=anchors, params=p)


def slide_carriage(**params) -> TemplateResult:
    """Minimal slide fixture carriage — the moving block whose groove captures the rail. The groove
    is CARVED by the card; this template is just the mount host. Anchor `groove_face` (underside)."""
    p = {"car_l": 24.0, "car_w": 30.0, "car_t": 3.0, "car_z": 3.0, **params}
    # a thin top plate the carriage body hangs from (kept minimal — the card grows the real groove)
    part = Location((0, 0, p["car_z"])) * Box(p["car_l"], p["car_w"], p["car_t"],
                                              align=(Align.CENTER, Align.CENTER, Align.MIN))
    anchors = {
        "groove_face": AnchorGeom("groove_face", "face", (0.0, 0.0, p["car_z"]), (0, 0, -1)),
    }
    return TemplateResult(part=part, anchors=anchors, params={**p, "box_h": p["car_z"]})




def slide_base_dual(**params) -> TemplateResult:
    """A base carrying TWO parallel rails (the Hard-anchor drawer form) — the alignment test host
    (D-E-10). Two travel-axis anchors rail_L / rail_R; `skew_deg` tilts rail_R's axis and `step_mm`
    raises it, so a skewed/stepped pair can be constructed and MUST fail check_alignment."""
    import math
    p = {"base_l": 120.0, "base_w": 80.0, "base_t": 3.0, "rail_gap": 60.0,
         "skew_deg": 0.0, "step_mm": 0.0, **params}
    L, W, T = p["base_l"], p["base_w"], p["base_t"]
    part = Box(L, W, T, align=(Align.CENTER, Align.CENTER, Align.MIN))
    th = math.radians(p["skew_deg"])
    anchors = {
        "rail_L": AnchorGeom("rail_L", "axis", (0.0, -p["rail_gap"] / 2, T), (1, 0, 0)),
        "rail_R": AnchorGeom("rail_R", "axis", (0.0, p["rail_gap"] / 2, T + p["step_mm"]),
                             (math.cos(th), math.sin(th), 0.0)),
        "face_L": AnchorGeom("face_L", "face", (0.0, -p["rail_gap"] / 2, T), (0, 0, 1)),
        "face_R": AnchorGeom("face_R", "face", (0.0, p["rail_gap"] / 2, T + p["step_mm"]), (0, 0, 1)),
    }
    return TemplateResult(part=part, anchors=anchors, params=p)


def pinion_carrier(**params) -> TemplateResult:
    """rack_pinion host (§3.6 fixture) — a base plate with a bearing post the pinion rotates on.
    `axis_h` sets the pinion-axis height above the floor. Anchors: `pinion_axis` (the +Z rotation
    axis at the post top) + `mesh_line` (the +X pitch line where the rack engages)."""
    p = {"base_l": 70.0, "base_w": 44.0, "base_t": 4.0, "axis_h": 45.0, "post_w": 14.0, **params}
    L, W, T, H, pw = p["base_l"], p["base_w"], p["base_t"], p["axis_h"], p["post_w"]
    part = Box(L, W, T, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # bearing post to the axis (overlaps the plate by 0.5 so the union is one solid, D14)
    part += Location((0, 0, T - 0.5)) * Box(pw, pw, H - T + 0.5,
                                            align=(Align.CENTER, Align.CENTER, Align.MIN))
    anchors = {
        "pinion_axis": AnchorGeom("pinion_axis", "axis", (0.0, 0.0, H), (0, 0, 1)),
        "mesh_line": AnchorGeom("mesh_line", "edge", (0.0, 0.0, H), (1, 0, 0)),
    }
    return TemplateResult(part=part, anchors=anchors, params=p)


def rack_carrier(**params) -> TemplateResult:
    """rack_pinion host — the sliding bar the rack is mounted to. Sized from the pinion (module,
    z_pinion) so its top face meets the rack's back and the union is ONE solid (the two-yellow-bodies
    lesson, D-D-1). Anchor `rack_mount` sits at the pinion axis point so the rack's built-in −rp pitch
    offset lands the teeth in mesh with the pinion."""
    p = {"module": 5.0, "z_pinion": 12, "axis_h": 45.0, "rail_l": 200.0,
         "carrier_t": 5.0, "face_w": 8.0, **params}
    m, z, H = p["module"], int(p["z_pinion"]), p["axis_h"]
    rp = m * z / 2.0
    L, ct, fw = p["rail_l"], p["carrier_t"], p["face_w"]
    y_back = -rp - 1.25 * m - 4.0                     # rack body back face (see _rack_outline)
    # a guide bar just behind the rack, overlapping it by 0.5 in +Y so rack∪carrier is one solid
    part = Location((-L / 2, y_back - ct + 0.5, H)) * Box(L, ct, fw,
                                                         align=(Align.MIN, Align.MIN, Align.MIN))
    anchors = {"rack_mount": AnchorGeom("rack_mount", "face", (0.0, 0.0, H), (0, 0, 1))}
    return TemplateResult(part=part, anchors=anchors, params=p)


def shaft_carrier_in(**params) -> TemplateResult:
    """coupling host (m20 D-track fixture) — the INPUT side: a base plate with a vertical shaft stub
    the coupling hub is fused onto (a driven input shaft standing up). Mirrors screw_base/pinion_carrier
    (is_base). Anchor `shaft_in` (+Z rotation axis at the stub top, where the card grows the hub)."""
    p = {"base_l": 50.0, "base_w": 50.0, "base_t": 4.0, "shaft_d": 8.0, "shaft_h": 30.0, **params}
    L, W, T, sd, H = p["base_l"], p["base_w"], p["base_t"], p["shaft_d"], p["shaft_h"]
    part = Box(L, W, T, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # input shaft stub (overlaps the plate by 0.5 so the union is one solid, D14); full nominal radius
    # because the hub is FUSED to it (a rigid coupling grips the input rigidly).
    part += Location((0, 0, T - 0.5)) * Cylinder(sd / 2, H - T + 0.5,
                                                 align=(Align.CENTER, Align.CENTER, Align.MIN))
    anchors = {"shaft_in": AnchorGeom("shaft_in", "axis", (0.0, 0.0, H), (0, 0, 1))}
    return TemplateResult(part=part, anchors=anchors, params=p)


def shaft_carrier_out(**params) -> TemplateResult:
    """coupling host — the OUTPUT side: the driven output shaft (the MOVER, is_base=False, like
    nut_carriage). A floating stub that inserts into the coupling's blind bore with print clearance
    (undersized by the A-PETG-1 clearance so it slides in). Anchor `shaft_out` (−Z, the end that
    enters the bore)."""
    p = {"shaft_d": 8.0, "z0": 40.0, "shaft_len": 24.0, "clearance": 0.30, **params}
    sd, z0, sl, c = p["shaft_d"], p["z0"], p["shaft_len"], p["clearance"]
    part = Location((0, 0, z0)) * Cylinder(sd / 2 - c, sl, align=(Align.CENTER, Align.CENTER, Align.MIN))
    anchors = {"shaft_out": AnchorGeom("shaft_out", "axis", (0.0, 0.0, z0), (0, 0, -1))}
    return TemplateResult(part=part, anchors=anchors, params=p)


def screw_base(**params) -> TemplateResult:
    """lead_screw host (m19 D-track fixture) — a base plate the screw stands VERTICALLY on (a
    screw-jack: rotation about +Z drives the nut up/down, gravity is the hold load). Mirrors
    slide_base/pinion_carrier. Anchors: `screw_axis` (+Z rotation axis at the plate top, where the
    card grows the screw) + `travel_edge` (the +Z travel line the nut rides)."""
    p = {"base_l": 60.0, "base_w": 60.0, "base_t": 4.0, **params}
    L, W, T = p["base_l"], p["base_w"], p["base_t"]
    part = Box(L, W, T, align=(Align.CENTER, Align.CENTER, Align.MIN))
    anchors = {
        "screw_axis": AnchorGeom("screw_axis", "axis", (0.0, 0.0, T), (0, 0, 1)),
        "travel_edge": AnchorGeom("travel_edge", "axis", (0.0, 0.0, T), (0, 0, 1)),
    }
    return TemplateResult(part=part, anchors=anchors, params=p)


def nut_carriage(**params) -> TemplateResult:
    """lead_screw host — the driven nut block riding the screw (m19 D-track fixture). A clearance BORE
    (radius d_major/2 + gap) lets the screw pass without interference — the THREAD is card knowledge
    the card would carve, so this host provides only the clearance mount (the slide_carriage lesson:
    the template is the host, the card owns the functional geometry, D-ONT-11). One connected solid
    (block − bore). Anchors: `nut_mount` (the underside the card threads onto) + `travel_axis` (+Z)."""
    p = {"nut_l": 26.0, "nut_w": 26.0, "nut_t": 10.0, "nut_z": 30.0, "d_major": 8.0, "gap": 1.0,
         **params}
    z = p["nut_z"]
    block = Location((0, 0, z)) * Box(p["nut_l"], p["nut_w"], p["nut_t"],
                                      align=(Align.CENTER, Align.CENTER, Align.MIN))
    bore = Location((0, 0, z - 1)) * Cylinder(p["d_major"] / 2 + p["gap"], p["nut_t"] + 2,
                                              align=(Align.CENTER, Align.CENTER, Align.MIN))
    part = block - bore
    anchors = {
        "nut_mount": AnchorGeom("nut_mount", "face", (0.0, 0.0, z), (0, 0, -1)),
        "travel_axis": AnchorGeom("travel_axis", "axis", (0.0, 0.0, z), (0, 0, 1)),
    }
    return TemplateResult(part=part, anchors=anchors, params={**p, "box_h": z})


# =====================================================================================
# The HARD ANCHOR host templates (MECHSYNTH §8.2 / D-track 3, m12). A hand-cranked drawer:
# a cabinet with TWO parallel rails, a drawer tray riding them, a knob-shaft carrying the
# pinion, and a rack bar fixed under the drawer. m12 builds ONLY the templates + their anchors;
# m13 is the assembly. The point of this milestone: every anchor the m13 assembly will bind to
# is DECLARED and LABELLED now, so a later binding failure cannot be blamed on a missing anchor.
#
# Shared frame: origin at the cabinet floor centre, +Z up, **+Y = FRONT** (the drawer pulls out
# toward +Y; −Y is the rear wall). The drawer travels along Y; the two rails run front-to-back at
# matched height `rail_z`. Units mm.
# =====================================================================================

CABINET_DEFAULTS = {"cab_d": 200.0, "cab_w": 120.0, "cab_h": 90.0, "wall": 4.0,
                    "rail_gap": 80.0, "knob_y": 52.0}


def cabinet_shell(**params) -> TemplateResult:
    """The Hard anchor's cabinet (is_base).

    **Frame (corrected at m13 — see the REVIEW's kinematic finding): +X = FRONT (pull-out), the
    drawer travels +X.** m12 first mounted the rails on the vertical side walls and put the knob on a
    +Y front shaft; assembling the mechanism showed neither closes the loop — a spur pinion on a
    front-facing shaft cannot drive the drawer, and the proven `slide_rail` T-rail is a FLOOR rail
    (m10). So the cabinet is reframed to the axes the proven carves realize: two FLOOR rails running
    +X at ±rail_gap/2 (matched height — the alignment subjects), a vertical +Z knob whose pinion
    meshes an +X rack. Open front at +X; floor + rear(−X) + two side walls(±Y) + top.

    Anchors: `rail_mount_L/R` (floor seats for the two rails, +Z, matched height, mirrored in Y) ·
    `rail_axis_L/R` (the +X travel axes — the alignment subjects) · `knob_mount` (top face where the
    vertical knob shaft is journalled, +Z) · `floor` (base seat, +Z)."""
    p = {**CABINET_DEFAULTS, **params}
    D, W, H, t, rg, ky = p["cab_d"], p["cab_w"], p["cab_h"], p["wall"], p["rail_gap"], p["knob_y"]
    floor = Box(D, W, t, align=(Align.CENTER, Align.CENTER, Align.MIN))
    rear = Location((-D / 2 + t / 2, 0, t)) * Box(t, W, H - t,
                                                  align=(Align.CENTER, Align.CENTER, Align.MIN))
    left = Location((0, -W / 2 + t / 2, t)) * Box(D, t, H - t,
                                                  align=(Align.CENTER, Align.CENTER, Align.MIN))
    right = Location((0, W / 2 - t / 2, t)) * Box(D, t, H - t,
                                                  align=(Align.CENTER, Align.CENTER, Align.MIN))
    top = Location((0, 0, H - t)) * Box(D, W, t, align=(Align.CENTER, Align.CENTER, Align.MIN))
    part = floor + rear + left + right + top
    anchors = {
        "rail_mount_L": AnchorGeom("rail_mount_L", "face", (0.0, -rg / 2, t), (0, 0, 1)),
        "rail_mount_R": AnchorGeom("rail_mount_R", "face", (0.0, rg / 2, t), (0, 0, 1)),
        "rail_axis_L": AnchorGeom("rail_axis_L", "axis", (0.0, -rg / 2, t), (1, 0, 0)),
        "rail_axis_R": AnchorGeom("rail_axis_R", "axis", (0.0, rg / 2, t), (1, 0, 0)),
        "knob_mount": AnchorGeom("knob_mount", "face", (D / 2 - 24.0, ky, H), (0, 0, 1)),
        # pawl bracket: near the rack (rack_pinion lays it at y=rp inboard of the pinion); the spring
        # arm reaches -Y to catch the ratchet. D-M13-4 (physics-discovered hold element #2).
        "pawl_mount": AnchorGeom("pawl_mount", "face", (D / 2 - 24.0, 42.0, 36.0), (0, -1, 0)),
        "floor": AnchorGeom("floor", "face", (0.0, 0.0, t), (0, 0, 1)),
    }
    return TemplateResult(part=part, anchors=anchors, params=p)


def cabinet_shell_collision(**params) -> list:
    """Static base (D23-weldable): floor + rear + two side walls + top. The drawer rides the rails
    (mechanism prims, card-owned); here the CABINET's own bodies are declared so the seating load
    path (drawer-on-rail transferred into the floor/walls) has geometry to bear on."""
    p = {**CABINET_DEFAULTS, **params}
    D, W, H, t = p["cab_d"], p["cab_w"], p["cab_h"], p["wall"]
    s = "template:cabinet_shell"
    return [_bx(0, 0, t / 2, D, W, t, source=s),                                    # floor
            _bx(-D / 2 + t / 2, 0, t + (H - t) / 2, t, W, H - t, source=s),         # rear
            _bx(0, -W / 2 + t / 2, t + (H - t) / 2, D, t, H - t, source=s),         # left
            _bx(0, W / 2 - t / 2, t + (H - t) / 2, D, t, H - t, source=s),          # right
            _bx(0, 0, H - t / 2, D, W, t, source=s)]                                # top


DRAWER_DEFAULTS = {"tray_d": 150.0, "tray_w": 96.0, "tray_h": 42.0, "wall": 3.0, "floor_z": 16.0}


def drawer_tray(**params) -> TemplateResult:
    """The drawer — an open-TOP tray that RIDES both rails (via the two carriage pieces the
    slide_rail carves own — the tray itself is a plain rigid body welded to them; the slide_rail
    carve REPLACES its mover piece, so it cannot also BE the tray, D-D-1 replace-semantics). Travels
    +X. `floor_z` sits the tray underside on the carriage tops.

    Anchors: `rack_mount` (underside centreline, −Z — the rack bar bolts along the drawer bottom) ·
    `front_pull` (the +X front face, a knob/handle site) · `carriage_seat_L/R` (the underside seats
    over the two rails, −Z, matched height — for reference/inspection of the ride)."""
    p = {**DRAWER_DEFAULTS, **params}
    D, W, H, t, fz = p["tray_d"], p["tray_w"], p["tray_h"], p["wall"], p["floor_z"]
    floor = Location((0, 0, fz)) * Box(D, W, t, align=(Align.CENTER, Align.CENTER, Align.MIN))
    walls = Part()
    for (cx, cy, sx, sy) in [(-D / 2 + t / 2, 0, t, W), (D / 2 - t / 2, 0, t, W),
                             (0, -W / 2 + t / 2, D, t), (0, W / 2 - t / 2, D, t)]:
        walls += Location((cx, cy, fz + t)) * Box(sx, sy, H - t,
                                                  align=(Align.CENTER, Align.CENTER, Align.MIN))
    part = floor + walls
    rg = 80.0                                          # nominal rail gap (matches cabinet default)
    anchors = {
        "rack_mount": AnchorGeom("rack_mount", "face", (0.0, 0.0, fz), (0, 0, -1)),
        # rack_line: the +X tooth line where the rack_pinion carves the rack into the drawer underside
        # (§8.2 "rack integrated into the drawer" branch). Offset to the +Y side, clear of the rails.
        "rack_line": AnchorGeom("rack_line", "edge", (0.0, 30.0, fz), (1, 0, 0)),
        "front_pull": AnchorGeom("front_pull", "face", (D / 2, 0.0, fz + H / 2), (1, 0, 0)),
        "carriage_seat_L": AnchorGeom("carriage_seat_L", "face", (0.0, -rg / 2, fz), (0, 0, -1)),
        "carriage_seat_R": AnchorGeom("carriage_seat_R", "face", (0.0, rg / 2, fz), (0, 0, -1)),
    }
    return TemplateResult(part=part, anchors=anchors, params=p)


def drawer_tray_collision(**params) -> list:
    """The moving drawer body: floor slab + four side walls. Inset by COLLISION_EPS (D14 — the §8.2
    flush-panel-in-flush-opening hazard) so its faces do not tie with the cabinet wall planes; the
    load path (drawer weight into the carriages) is carried by the carriage/rail prims, not here."""
    p = {**DRAWER_DEFAULTS, **params}
    D, W, H, t, fz = p["tray_d"], p["tray_w"], p["tray_h"], p["wall"], p["floor_z"]
    e = COLLISION_EPS
    s = "template:drawer_tray"
    out = [_bx(0, 0, fz + t / 2, D - 2 * e, W - 2 * e, t, source=s)]                # floor slab
    for (cx, cy, sx, sy) in [(-D / 2 + t / 2, 0, t, W), (D / 2 - t / 2, 0, t, W),
                             (0, -W / 2 + t / 2, D, t), (0, W / 2 - t / 2, D, t)]:
        out.append(_bx(cx, cy, fz + t + (H - t) / 2, sx - 2 * e, sy - 2 * e, H - t, source=s))
    return out


KNOB_DEFAULTS = {"shaft_d": 10.0, "grip_d": 28.0, "grip_t": 10.0,
                 "seat_x": 76.0, "seat_y": 60.0, "seat_z": 30.0, "top_z": 90.0}


def knob_shaft(**params) -> TemplateResult:
    """The hand knob — a **VERTICAL (+Z) shaft** with a grip disc on top, built at its world position
    beside the drawer (compile places pieces in-frame, so the template carries its own location).
    Reframed at m13: the pinion seat is on a vertical shaft so the pinion axis is +Z (the axis the
    proven `rack_pinion` carve realizes), driving the +X rack — a front/side crank can't do that.
    `shaft_seat` is where the rack_pinion `pinion_axis` port binds (the pinion mounts here); the shaft
    rises to `mount_axis` (journalled in the cabinet top) and a `grip_face` on top.

    Anchors: `shaft_seat` (pinion seat, +Z) · `mount_axis` (cabinet-top journal, +Z) · `grip_face`
    (top grip, +Z)."""
    p = {**KNOB_DEFAULTS, **params}
    sd, gd, gt = p["shaft_d"], p["grip_d"], p["grip_t"]
    sx, sy, sz, tz = p["seat_x"], p["seat_y"], p["seat_z"], p["top_z"]
    grip_top = tz + 12.0
    shaft = Location((sx, sy, (sz + grip_top) / 2)) * Cylinder(
        radius=sd / 2, height=grip_top - sz, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    grip = Location((sx, sy, grip_top - gt / 2)) * Cylinder(
        radius=gd / 2, height=gt, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    part = shaft + grip
    anchors = {
        "shaft_seat": AnchorGeom("shaft_seat", "axis", (sx, sy, sz), (0, 0, 1)),
        "mount_axis": AnchorGeom("mount_axis", "axis", (sx, sy, tz), (0, 0, 1)),
        "grip_face": AnchorGeom("grip_face", "face", (sx, sy, grip_top), (0, 0, 1)),
    }
    return TemplateResult(part=part, anchors=anchors, params=p)


def knob_shaft_collision(**params) -> list:
    """The knob: the vertical shaft cylinder + the grip disc (world-frame cylinder prims)."""
    p = {**KNOB_DEFAULTS, **params}
    sd, gd, gt = p["shaft_d"], p["grip_d"], p["grip_t"]
    sx, sy, sz, tz = p["seat_x"], p["seat_y"], p["seat_z"], p["top_z"]
    grip_top = tz + 12.0
    s = "template:knob_shaft"
    return [{"type": "cylinder", "frame": "world", "pos": (sx, sy, (sz + grip_top) / 2),
             "size": (sd / 2, (grip_top - sz) / 2), "source": s},
            {"type": "cylinder", "frame": "world", "pos": (sx, sy, grip_top - gt / 2),
             "size": (gd / 2, gt / 2), "source": s}]


RACK_BAR_DEFAULTS = {"bar_l": 170.0, "bar_w": 12.0, "bar_t": 8.0,
                     "cx": 0.0, "cy": 30.0, "cz": 30.0}


def rack_bar(**params) -> TemplateResult:
    """The rack's host strip — a bar running along **X** (the drawer travel) into which the
    rack_pinion card carves the rack teeth, built at its world position under the drawer's +Y side.
    The rack_pinion carve UNIONS the rack solid here (so bar and teeth are one body); the bar moves
    with the drawer (welded in physics). `mount_face` (+Z) bolts to the drawer underside; `rack_line`
    marks the +X tooth line.

    Frame: bar centred at (cx, cy, cz), running along X."""
    p = {**RACK_BAR_DEFAULTS, **params}
    L, w, t, cx, cy, cz = p["bar_l"], p["bar_w"], p["bar_t"], p["cx"], p["cy"], p["cz"]
    part = Location((cx, cy, cz)) * Box(L, w, t, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    anchors = {
        "mount_face": AnchorGeom("mount_face", "face", (cx, cy, cz + t / 2), (0, 0, 1)),
        "rack_line": AnchorGeom("rack_line", "axis", (cx, cy, cz + t / 2), (1, 0, 0)),
    }
    return TemplateResult(part=part, anchors=anchors, params=p)


def rack_bar_collision(**params) -> list:
    """The rack bar body (the toothed strip). One box at its world centre — the card's rack teeth are
    the mechanism prims (carved later); this is the strip it bolts through."""
    p = {**RACK_BAR_DEFAULTS, **params}
    L, w, t, cx, cy, cz = p["bar_l"], p["bar_w"], p["bar_t"], p["cx"], p["cy"], p["cz"]
    return [_bx(cx, cy, cz, L, w, t, source="template:rack_bar")]


TEMPLATE_COLLISION.update({"cabinet_shell": cabinet_shell_collision,
                           "drawer_tray": drawer_tray_collision,
                           "knob_shaft": knob_shaft_collision,
                           "rack_bar": rack_bar_collision})


TEMPLATES = {"box_shell": box_shell, "lid_panel": lid_panel,
             "slide_base": slide_base, "slide_carriage": slide_carriage,
             "slide_base_dual": slide_base_dual,
             "pinion_carrier": pinion_carrier, "rack_carrier": rack_carrier,
             "screw_base": screw_base, "nut_carriage": nut_carriage,
             "shaft_carrier_in": shaft_carrier_in, "shaft_carrier_out": shaft_carrier_out,
             "cabinet_shell": cabinet_shell, "drawer_tray": drawer_tray,
             "knob_shaft": knob_shaft, "rack_bar": rack_bar,
             "flat_panel_mount": flat_panel_mount, "retained_board": retained_board}
