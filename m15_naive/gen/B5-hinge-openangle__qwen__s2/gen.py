import sys as _s0
_s0.path[:] = [p for p in _s0.path if 'm15_naive' not in p]
from build123d import *

# Parameters
box_length = 100.0
box_width = 80.0
box_height = 60.0
wall_thickness = 2.0
hinge_width = 15.0
hinge_depth = 8.0
hinge_offset = 5.0
lid_angle_open = 100.0
lid_angle_closed = 5.0

# Create the main box body
box_body = Box(box_length, box_width, box_height, align=(Align.CENTER, Align.CENTER, Align.MIN))

# Create the lid
lid = Box(box_length, box_width, box_height, align=(Align.CENTER, Align.CENTER, Align.MIN))

# Create hinge cutout in box
hinge_cutout = Pos(0, 0, -box_height/2 + wall_thickness) * \
    Box(hinge_width, box_width - 2*wall_thickness, hinge_depth, align=(Align.CENTER, Align.CENTER, Align.MIN))

# Create hinge cutout in lid
lid_hinge_cutout = Pos(0, 0, box_height/2 - wall_thickness) * \
    Box(hinge_width, box_width - 2*wall_thickness, hinge_depth, align=(Align.CENTER, Align.CENTER, Align.MAX))

# Subtract hinge cutouts from box and lid
box_body = box_body - hinge_cutout
lid = lid - lid_hinge_cutout

# Create the hinge pin
hinge_pin_radius = 3.0
hinge_pin_length = box_width - 2*wall_thickness - 4.0
hinge_pin = Pos(0, 0, -box_height/2 + wall_thickness + hinge_depth/2) * \
    Cylinder(hinge_pin_radius, hinge_pin_length, align=(Align.CENTER, Align.CENTER, Align.MIN))

# Create the box with hinge
box_with_hinge = box_body + hinge_pin

# Create the lid with hinge pin
lid_with_hinge = lid + hinge_pin

# Adjust the lid to allow for proper rotation
# The lid needs to be rotated around the hinge axis
# We'll create a separate part that can be assembled

# Create the main box part
main_box = box_with_hinge

# Create the lid part
lid_part = lid_with_hinge

# Set result to list of parts
result = [main_box, lid_part]

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
