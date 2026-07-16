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

from build123d import Align, Box, Location, Part


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
    anchors = {
        "side_wall_left": AnchorGeom("side_wall_left", "face", (-xin, 0.0, z_mid), (1, 0, 0)),
        "side_wall_right": AnchorGeom("side_wall_right", "face", (xin, 0.0, z_mid), (-1, 0, 0)),
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
    anchors = {
        "rim_underside_left": AnchorGeom("rim_underside_left", "face", (-xr, 0.0, z0), (0, 0, -1)),
        "rim_underside_right": AnchorGeom("rim_underside_right", "face", (xr, 0.0, z0), (0, 0, -1)),
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


TEMPLATES = {"box_shell": box_shell, "lid_panel": lid_panel,
             "flat_panel_mount": flat_panel_mount, "retained_board": retained_board}
