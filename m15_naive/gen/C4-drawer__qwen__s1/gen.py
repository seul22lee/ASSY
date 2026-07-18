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
slot_depth = 10
slot_height = 20

# Cabinet body
with BuildPart() as cabinet_body:
    Box(width, height, depth)
    
    # Remove inner cavity
    with Locations((0, 0, 0)):
        Box(drawer_width, drawer_height, drawer_depth, mode=Subtract)
    
    # Add drawer slot
    with Locations((0, -height/2 + drawer_height/2, 0)):
        Box(slot_width, slot_height, depth, mode=Subtract)
    
    # Add knob hole
    with Locations((width/2 - knob_offset, 0, 0)):
        Cylinder(knob_radius, height, rotation=(0, 90, 0), mode=Subtract)
    
# Drawer front
with BuildPart() as drawer_front:
    Box(drawer_width, drawer_height, wall_thickness)
    
    # Add drawer handle cutout
    with Locations((0, 0, 0)):
        Box(20, 15, wall_thickness + 1, mode=Subtract)
    
# Drawer slide mechanism
with BuildPart() as slide_mechanism:
    # Base plate
    Box(width, 20, 10)
    
    # Slot for drawer to slide in
    with Locations((0, 0, 0)):
        Box(slot_width, 20, 5, mode=Subtract)
    
    # Add mounting holes
    with Locations((-width/2 + 10, 0, 0), (width/2 - 10, 0, 0)):
        Cylinder(3, 10, rotation=(0, 90, 0), mode=Subtract)
    
# Cabinet back panel
with BuildPart() as cabinet_back:
    Box(width, height, wall_thickness)
    
    # Add ventilation holes
    with Locations((-width/3, -height/4, 0), (0, -height/4, 0), (width/3, -height/4, 0)):
        Cylinder(3, wall_thickness + 1, mode=Subtract)
    
# Cabinet front panel
with BuildPart() as cabinet_front:
    Box(width, height, wall_thickness)
    
    # Add knob mount
    with Locations((width/2 - knob_offset, 0, 0)):
        Cylinder(knob_radius + 2, wall_thickness + 1, rotation=(0, 90, 0), mode=Subtract)
    
# Cabinet left panel
with BuildPart() as cabinet_left:
    Box(wall_thickness, height, depth)
    
# Cabinet right panel
with BuildPart() as cabinet_right:
    Box(wall_thickness, height, depth)
    
# Cabinet top panel
with BuildPart() as cabinet_top:
    Box(width, wall_thickness, depth)
    
# Cabinet bottom panel
with BuildPart() as cabinet_bottom:
    Box(width, wall_thickness, depth)
    
# Knob
with BuildPart() as knob:
    Cylinder(knob_radius, 3)
    
    # Add screw hole
    with Locations((0, 0, 0)):
        Cylinder(2, 3, rotation=(0, 90, 0), mode=Subtract)
    
# Result list - each part that needs to be printed separately
result = [
    cabinet_body.part,
    drawer_front.part,
    slide_mechanism.part,
    cabinet_back.part,
    cabinet_front.part,
    cabinet_left.part,
    cabinet_right.part,
    cabinet_top.part,
    cabinet_bottom.part,
    knob.part
]

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
