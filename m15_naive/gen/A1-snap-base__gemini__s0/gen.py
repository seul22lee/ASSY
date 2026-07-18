import sys as _s0
_s0.path[:] = [p for p in _s0.path if 'm15_naive' not in p]
from build123d import *

# --- Parameters ---
length = 60.0
width = 40.0
height = 30.0
box_wall = 2.0
lid_wall = 1.6  # Slightly thinner lid wall for better flex when snapping
clearance = 0.25  # Clearance between box and lid
lid_overlap = 12.0  # How far the lid skirts down over the box
snap_depth = 0.45  # How far the snap ridge protrudes
snap_width = 2.4  # Vertical thickness of the snap ridge
snap_offset = 5.0  # Distance from the top of the box to the center of the snap
corner_rad = 4.0

# Derived parameters for the hollow interior
inner_l = length - box_wall * 2
inner_w = width - box_wall * 2
inner_rad = max(0.1, corner_rad - box_wall)

# --- BOX BASE ---
with BuildPart() as box:
    # Main body
    with BuildSketch():
        RectangleRounded(length, width, corner_rad)
    extrude(amount=height)
    
    # Hollow out the box
    offset(amount=-box_wall, openings=box.faces().sort_by(Axis.Z)[-1])
    
    # Snap Ridge Bottom Half (Loft creates a chamfered overhang safe for FDM)
    with BuildSketch(Plane.XY.offset(height - snap_offset - snap_width/2)):
        RectangleRounded(length, width, corner_rad)
        RectangleRounded(inner_l, inner_w, inner_rad, mode=Mode.SUBTRACT)
    with BuildSketch(Plane.XY.offset(height - snap_offset)):
        RectangleRounded(length + snap_depth*2, width + snap_depth*2, corner_rad + snap_depth)
        RectangleRounded(inner_l, inner_w, inner_rad, mode=Mode.SUBTRACT)
    loft()
    
    # Snap Ridge Top Half
    with BuildSketch(Plane.XY.offset(height - snap_offset)):
        RectangleRounded(length + snap_depth*2, width + snap_depth*2, corner_rad + snap_depth)
        RectangleRounded(inner_l, inner_w, inner_rad, mode=Mode.SUBTRACT)
    with BuildSketch(Plane.XY.offset(height - snap_offset + snap_width/2)):
        RectangleRounded(length, width, corner_rad)
        RectangleRounded(inner_l, inner_w, inner_rad, mode=Mode.SUBTRACT)
    loft()

# --- LID ---
# Calculate lid dimensions based on clearances
lid_inner_l = length + clearance * 2
lid_inner_w = width + clearance * 2
lid_inner_rad = corner_rad + clearance

lid_outer_l = lid_inner_l + lid_wall * 2
lid_outer_w = lid_inner_w + lid_wall * 2
lid_outer_rad = lid_inner_rad + lid_wall

# Groove dimensions (slightly larger than the ridge to ensure it seats fully)
groove_z = lid_overlap - snap_offset
g_depth = snap_depth + 0.2
g_width = snap_width + 0.8

with BuildPart() as lid:
    # Main lid body
    with BuildSketch():
        RectangleRounded(lid_outer_l, lid_outer_w, lid_outer_rad)
    extrude(amount=lid_overlap + lid_wall)
    
    # Hollow out the lid from the bottom
    offset(amount=-lid_wall, openings=lid.faces().sort_by(Axis.Z)[0])
    
    # Groove Bottom Half (Subtracting a lofted solid to carve into the inner wall)
    with BuildSketch(Plane.XY.offset(groove_z - g_width/2)):
        RectangleRounded(lid_inner_l, lid_inner_w, lid_inner_rad)
    with BuildSketch(Plane.XY.offset(groove_z)):
        RectangleRounded(lid_inner_l + g_depth*2, lid_inner_w + g_depth*2, lid_inner_rad + g_depth)
    loft(mode=Mode.SUBTRACT)
    
    # Groove Top Half
    with BuildSketch(Plane.XY.offset(groove_z)):
        RectangleRounded(lid_inner_l + g_depth*2, lid_inner_w + g_depth*2, lid_inner_rad + g_depth)
    with BuildSketch(Plane.XY.offset(groove_z + g_width/2)):
        RectangleRounded(lid_inner_l, lid_inner_w, lid_inner_rad)
    loft(mode=Mode.SUBTRACT)

# --- PREPARE FOR EXPORT ---
box_part = box.part

# Rotate the lid 180 degrees so its flat top is on the build plate, and move it beside the box
lid_part = lid.part.rotated((180, 0, 0))
lid_z_min = lid_part.bounding_box().min.Z
lid_part = lid_part.moved(Location((0, width + 20, -lid_z_min)))

# Expose the final parts as a list
result = [box_part, lid_part]


# --- m15 export harness (appended) ---
import sys as _sys
_sys.path[:] = [p for p in _sys.path if "m15_naive/gen" not in p]  # never shadow stdlib
import json as _json
from pathlib import Path as _P
try:
    from build123d import export_stl as _export
    _parts = result if isinstance(result, (list, tuple)) else [result]
    _od = _P(_sys.argv[1]); _od.mkdir(parents=True, exist_ok=True)
    _n = 0
    for _i, _p in enumerate(_parts):
        _solid = getattr(_p, "part", _p)
        try:
            _export(_solid, str(_od / f"part_{_i}.stl"), tolerance=0.2, angular_tolerance=0.4)
            _n += 1
        except Exception as _e:
            pass
    print("M15_STATUS " + _json.dumps({"ok": True, "n_parts": len(_parts), "n_exported": _n}))
except Exception as _e:
    print("M15_STATUS " + _json.dumps({"ok": False, "error": type(_e).__name__ + ": " + str(_e)[:200]}))
