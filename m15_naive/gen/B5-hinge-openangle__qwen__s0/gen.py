import sys as _s0
_s0.path[:] = [p for p in _s0.path if 'm15_naive' not in p]
from build123d import *

# Parameters
box_length = 100.0
box_width = 80.0
box_height = 60.0
wall_thickness = 2.0
hinge_width = 15.0
hinge_depth = 10.0
hinge_offset = 5.0
lid_angle_open = 100.0
lid_angle_closed = 5.0

class HingedBox:
    def __init__(self):
        self.box_part = None
        self.lid_part = None
        self.hinge_pin = None
        
    def create_box(self):
        # Create the main box body
        box = Box(box_length, box_width, box_height)
        
        # Create inner cavity with wall thickness
        inner_box = Box(
            box_length - 2 * wall_thickness,
            box_width - 2 * wall_thickness,
            box_height - wall_thickness
        ).locate(Translation((0, 0, wall_thickness/2)))
        
        # Subtract cavity from box
        self.box_part = box - inner_box
        
    def create_lid(self):
        # Create lid with hinge cutout
        lid = Box(box_length, box_width, wall_thickness)
        
        # Create hinge cutout in lid
        hinge_cutout = Box(
            hinge_width,
            hinge_depth,
            wall_thickness * 2
        ).locate(Translation((0, -box_width/2 + hinge_offset + hinge_depth/2, 0)))
        
        self.lid_part = lid - hinge_cutout
        
    def create_hinge_pin(self):
        # Create the hinge pin that goes through both parts
        pin_radius = 3.0
        pin_length = box_width - 2 * hinge_offset - hinge_depth
        
        # Create cylindrical hinge pin
        self.hinge_pin = Cylinder(pin_radius, pin_length, rotation=(90, 0, 0))
        
    def build(self):
        self.create_box()
        self.create_lid()
        self.create_hinge_pin()
        
        # Return the parts as separate objects
        return [self.box_part, self.lid_part]

# Create the hinged box
box_design = HingedBox()
result = box_design.build()

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
