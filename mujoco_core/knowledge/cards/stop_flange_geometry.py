"""stop_flange geometry (D-ONT-4 PassiveFeature) — the M0 stop variant, cardified.

A rearward flange on the MOVING piece, extending behind the hinge axis. As the lid opens the flange
swings DOWN and bottoms out flat against the base's own rear wall — no added part (the card's
selection_notes). It CONSTRAINS the hinge's use-phase rotation; it realizes nothing.

`stop_angle_deg` is SOLVED from the geometry by M0's scan, not asserted: the closed form has a
branch ambiguity that silently returns the wrong root (m0/hinge_box.py::stop_angle_deg). The value
this returns is what the IR's B3-class behaviour (bound="max") must carry — the geometry and the
imposed behaviour agree by construction, which is what V-08 exists to enforce.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from build123d import Align, Box, Location

FUSE_GAP = 3.0        # the flange starts this far short of the axis, so it fuses into the knuckle
#                       without entering the bore keep-out (M0)


@dataclass
class FlangeCarve:
    parts: dict
    tags: dict
    stop_angle_deg: float


def stop_angle_deg(axis_y: float, axis_z: float, box_w: float, box_h: float,
                   stop_flange_r: float) -> float:
    """Where the flange bottoms out on the base's rear wall, by scan (M0's method — the closed form
    has a branch ambiguity that silently returns the wrong root).

    The flange's rear-bottom corner starts at (−r, box_h − axis_z) RELATIVE TO THE AXIS and rotates
    with the lid; the stop is the first angle at which it reaches the plane of the rear wall.

    NOTE the dz term: M0 hardcoded −lid_t/2, which silently encodes M0's own axis placement (the lid
    MID-PLANE). An axis placed elsewhere — anchor_easy puts it at z=box_h, off the box's rear top
    edge — has a different dz and therefore a different stop angle (120.05° here, not M0's 108.85°).
    Taking axis_z as an argument is what keeps this a solved property of THIS geometry rather than a
    number copied from a differently-built box. inf ⇒ no flange ⇒ no stop."""
    if stop_flange_r <= 0:
        return float("inf")           # no stop: the lid is free to fold flat. That is the finding.
    dy, dz = -stop_flange_r, box_h - axis_z
    y_wall = -box_w / 2 - axis_y      # wall plane, relative to the axis
    for deg in np.arange(0.0, 180.0, 0.05):
        t = np.radians(deg)
        if dy * np.cos(t) - dz * np.sin(t) >= y_wall:
            return round(float(deg), 2)
    return 180.0


def _flange_box(inst, lid_params, axis_pt):
    """The flange slab in world mm: rearward of the axis, at lid height, centred on the axis span."""
    r = float(inst.params["stop_flange_r"])
    w = float(inst.params.get("flange_w", 8.0))        # axial width (M0: the lid knuckle span)
    lid_t = float(lid_params["lid_t"])
    z0 = float(lid_params.get("box_h", 40.0))
    ay = float(axis_pt[1])
    y0, y1 = ay - r, ay - FUSE_GAP                     # rearward of the axis, fusing into the knuckle
    return (0.0, (y0 + y1) / 2, z0 + lid_t / 2), (w, y1 - y0, lid_t)


def carve(pieces: dict, inst, bindings, axis) -> FlangeCarve:
    """Grow the flange on the piece bound to the `contact` port (the lid). `axis` = the hinge axis
    the flange caps ({point, dir}) — the same information M0's builder had (it knew axis_y)."""
    cb = next(b for b in bindings if b.port == "contact")
    tr = pieces[cb.piece_id]
    lid_params = tr.params
    (cx, cy, cz), (sx, sy, sz) = _flange_box(inst, lid_params, axis["point"])
    flange = Location((cx, cy, cz)) * Box(sx, sy, sz, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    part = tr.part + flange
    ang = stop_angle_deg(axis_y=float(axis["point"][1]), axis_z=float(axis["point"][2]),
                         box_w=float(lid_params["box_w"]),
                         box_h=float(lid_params.get("box_h", 40.0)),
                         stop_flange_r=float(inst.params["stop_flange_r"]))
    # V-08's geometric teeth: the ceiling the IR declares (B3.range_value) must be the ceiling the
    # compiled flange actually produces. Disagreement means the IR is describing a different part.
    declared = inst.params.get("stop_angle")
    if declared is not None and abs(float(declared) - ang) > 0.5:
        raise ValueError(
            f"stop_flange {inst.id}: IR declares stop_angle={declared}° but the compiled flange "
            f"solves to {ang}° — the imposed limit and the geometry disagree (V-08). A stop angle "
            f"must be SOLVED from this box's own axis placement, never copied from another build.")
    return FlangeCarve(parts={cb.piece_id: part}, tags={"flange": flange}, stop_angle_deg=ang)


def collision_primitives(inst, lid_params: dict, axis) -> list:
    """The flange is a BOX — its convex proxy is EXACT, not an approximation. `seat` class: it must
    contact the base's rear wall (the seating/load-path class), which is how the stop actually acts.
    This prim represents REAL carved geometry (a solid in the compiled STEP, registered in the IR as
    F1's imposed B3 limit); it is not a stop conjured in the physics driver."""
    (cx, cy, cz), (sx, sy, sz) = _flange_box(inst, lid_params, axis["point"])
    return [{"type": "box", "frame": "world", "pos": (cx, cy, cz),
             "size": (sx / 2, sy / 2, sz / 2), "role_hint": "stop_flange",
             "source": f"card:stop_flange@{inst.id}"}]
