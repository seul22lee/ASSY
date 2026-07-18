import sys as _s0
_s0.path[:] = [p for p in _s0.path if 'm15_naive' not in p]
from build123d import *

# Parameters
width = 100
height = 150
depth = 80
wall_thickness = 2
knob_diameter = 12
knob_radius = knob_diameter / 2
knob_offset = 15
drawer_width = width - 2 * wall_thickness
drawer_height = height - 2 * wall_thickness
drawer_depth = depth - 2 * wall_thickness
slot_width = 8
slot_depth = 40
slot_height = 10

# Cabinet body
with BuildPart() as cabinet_body:
    Box(width, height, depth)
    # Inner cavity
    with Locations((0, 0, 0)):
        Box(drawer_width, drawer_height, drawer_depth, mode=Subtract)
    
    # Slot for drawer guide
    with Locations((0, -depth/2 + slot_depth/2, 0)):
        Box(slot_width, slot_height, depth - 2 * wall_thickness, mode=Subtract)
    
    # Knob hole
    with Locations((width/2 - knob_offset, 0, 0)):
        Cylinder(knob_diameter, wall_thickness, rotation=(0, 90, 0), mode=Subtract)
    
    # Drawer front
    with Locations((0, -depth/2 + drawer_depth/2, 0)):
        Box(drawer_width, drawer_height, wall_thickness, mode=Subtract)

# Drawer
with BuildPart() as drawer:
    Box(drawer_width, drawer_height, wall_thickness)
    
    # Handle cutout
    with Locations((0, 0, 0)):
        Box(30, 20, wall_thickness/2, mode=Subtract)
    
    # Slot for cabinet guide
    with Locations((0, -drawer_depth/2 + slot_depth/2, 0)):
        Box(slot_width, slot_height, wall_thickness, mode=Subtract)

# Knob
with BuildPart() as knob:
    Cylinder(knob_diameter, wall_thickness, rotation=(0, 90, 0))
    
    # Center hole
    with Locations((0, 0, 0)):
        Cylinder(4, wall_thickness, rotation=(0, 90, 0), mode=Subtract)

# Result list
result = [cabinet_body.part, drawer.part, knob.part]

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
