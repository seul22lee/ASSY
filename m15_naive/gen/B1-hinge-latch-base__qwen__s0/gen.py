import sys as _s0
_s0.path[:] = [p for p in _s0.path if 'm15_naive' not in p]
from build123d import *

# Parameters
box_length = 80.0
box_width = 60.0
box_height = 40.0
wall_thickness = 2.0
hinge_width = 8.0
latch_depth = 12.0
latch_width = 10.0
latch_height = 8.0

# Main box body
with BuildPart() as box_body:
    Box(box_length, box_width, box_height)
    
    # Create inner cavity with wall thickness
    with Locations((0, 0, wall_thickness/2)):
        Box(box_length - 2*wall_thickness, box_width - 2*wall_thickness, box_height - wall_thickness, align=(Align.CENTER, Align.CENTER, Align.MIN))
    
    # Create hinge cutout
    with Locations((box_length/2 - hinge_width/2, 0, 0)):
        Box(hinge_width, box_width, wall_thickness, align=(Align.CENTER, Align.CENTER, Align.MIN))
    
    # Create latch slot
    with Locations((box_length/2 - latch_width/2, box_width/2 - wall_thickness/2, wall_thickness/2)):
        Box(latch_width, wall_thickness, latch_height)
    
# Lid part
with BuildPart() as lid:
    Box(box_length, box_width, wall_thickness)
    
    # Create hinge cutout for lid
    with Locations((box_length/2 - hinge_width/2, 0, 0)):
        Box(hinge_width, box_width, wall_thickness, align=(Align.CENTER, Align.CENTER, Align.MIN))
    
    # Create latch tab
    with Locations((box_length/2 - latch_width/2, box_width/2 - wall_thickness/2, 0)):
        Box(latch_width, wall_thickness, latch_height)
    
# Hinge pin (separate part for printing)
with BuildPart() as hinge_pin:
    Cylinder(radius=hinge_width/2, height=box_width, align=(Align.CENTER, Align.CENTER, Align.MIN))
    
# Create a small gap for the latch to fit
with BuildPart() as latch_tab:
    Box(latch_width, wall_thickness, latch_height)
    
# Return the parts as separate printable components
result = [box_body.part, lid.part, hinge_pin.part, latch_tab.part]

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
