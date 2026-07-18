import sys as _s0
_s0.path[:] = [p for p in _s0.path if 'm15_naive' not in p]
from build123d import *

# Design parameters
box_length = 100.0
box_width = 80.0
box_height = 50.0
wall_thickness = 2.0
lip_height = 3.0
snap_lip_width = 5.0
snap_lip_depth = 2.0
snap_lip_spacing = 15.0

# Create the main box body
box_body = Box(box_length, box_width, box_height, align=(Align.CENTER, Align.CENTER, Align.MIN))

# Create the inner cavity with wall thickness
inner_length = box_length - 2 * wall_thickness
inner_width = box_width - 2 * wall_thickness
inner_height = box_height - 2 * wall_thickness

box_cavity = Box(inner_length, inner_width, inner_height, align=(Align.CENTER, Align.CENTER, Align.MIN))

# Create the snap lid
lid = Box(box_length, box_width, wall_thickness + lip_height, align=(Align.CENTER, Align.CENTER, Align.MIN))

# Create snap lips on the lid
snap_lips = []
for i in range(2):
    for j in range(2):
        lip_x = (i - 0.5) * (box_length - snap_lip_width - 2 * wall_thickness)
        lip_y = (j - 0.5) * (box_width - snap_lip_width - 2 * wall_thickness)
        
        # Create a snap lip with a slight overhang for the snap fit
        lip = Box(snap_lip_width, snap_lip_width, lip_height, align=(Align.CENTER, Align.CENTER, Align.MIN))
        lip = lip.translate((lip_x, lip_y, 0))
        
        # Add clearance to prevent interference
        lip_clearance = Box(snap_lip_width + 0.3, snap_lip_width + 0.3, lip_height + 0.1, align=(Align.CENTER, Align.CENTER, Align.MIN))
        lip_clearance = lip_clearance.translate((lip_x, lip_y, 0))
        
        # Subtract the clearance from the lid to create the snap fit
        lid = lid - lip_clearance
        
        # Add the snap lip to the list
        snap_lips.append(lip)

# Create the main box with cavity
box = box_body - box_cavity

# Create the lid with snap lips
lid_with_lips = lid

# Combine parts into result
result = [box, lid_with_lips]

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
