import sys as _s0
_s0.path[:] = [p for p in _s0.path if 'm15_naive' not in p]
from build123d import *

# Parameters
width = 100
height = 150
depth = 80
wall_thickness = 2
knob_diameter = 12
knob_offset = 40
drawer_width = 90
drawer_height = 140
drawer_depth = 70
slot_width = 8
slot_depth = 10
slot_height = 10

# Cabinet body
with BuildPart() as cabinet:
    # Main cabinet box
    Box(width, height, depth)
    
    # Remove inner cavity with wall thickness
    with BuildSketch(Plane.XZ) as inner:
        Rectangle(width - 2*wall_thickness, depth - 2*wall_thickness)
    extrude(amount=height - 2*wall_thickness, mode=Mode.SUBTRACT)
    
    # Add drawer slot
    with BuildSketch(Plane.YZ) as slot:
        Rectangle(slot_width, slot_height)
    extrude(amount=slot_depth, mode=Mode.SUBTRACT)
    
    # Add knob hole
    with BuildSketch(Plane.XZ) as knob_hole:
        Circle(knob_diameter/2)
    extrude(amount=wall_thickness, mode=Mode.SUBTRACT)
    
# Drawer
with BuildPart() as drawer:
    Box(drawer_width, drawer_height, drawer_depth)
    
    # Remove inner cavity for drawer
    with BuildSketch(Plane.XZ) as inner:
        Rectangle(drawer_width - 2*wall_thickness, drawer_depth - 2*wall_thickness)
    extrude(amount=drawer_height - 2*wall_thickness, mode=Mode.SUBTRACT)
    
    # Add drawer slide slots
    with BuildSketch(Plane.YZ) as slot:
        Rectangle(slot_width, slot_height)
    extrude(amount=slot_depth, mode=Mode.SUBTRACT)
    
# Knob
with BuildPart() as knob:
    Box(knob_diameter, knob_diameter, wall_thickness)
    
    # Add hole for shaft
    with BuildSketch(Plane.XZ) as shaft_hole:
        Circle(3)
    extrude(amount=wall_thickness, mode=Mode.SUBTRACT)
    
# Create drawer slide mechanism
with BuildPart() as slide:
    Box(slot_width, slot_height, slot_depth)
    
    # Add clearance for drawer movement
    with BuildSketch(Plane.YZ) as clearance:
        Rectangle(slot_width - 0.5, slot_height - 0.5)
    extrude(amount=slot_depth - 0.5, mode=Mode.SUBTRACT)
    
# Set result to list of parts
result = [cabinet.part, drawer.part, knob.part, slide.part]

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
