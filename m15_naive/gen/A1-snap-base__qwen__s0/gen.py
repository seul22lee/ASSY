import sys as _s0
_s0.path[:] = [p for p in _s0.path if 'm15_naive' not in p]
from build123d import *

# Parameters
box_length = 50
box_width = 30
box_height = 20
wall_thickness = 2
lip_height = 2
lip_width = 3
slot_width = 1.5
slot_depth = 4

# Main box body
def create_box_body():
    # Create the base box with walls
    outer_box = Box(box_length, box_width, box_height)
    inner_box = Box(box_length - 2*wall_thickness, box_width - 2*wall_thickness, box_height - wall_thickness)
    
    # Subtract to create hollow box
    box_body = outer_box - inner_box
    
    # Add lip for lid attachment
    lip = Box(box_length, lip_width, lip_height)
    lip = lip.locate(Placement((0, box_width/2 - lip_width/2, 0)))
    box_body = box_body + lip
    
    return box_body

# Lid with snap fit
def create_lid():
    # Create lid with slightly smaller dimensions for snap fit
    lid_length = box_length - 0.5
    lid_width = box_width - 0.5
    lid_height = box_height + 1  # Slightly taller to allow for snap fit
    
    outer_lid = Box(lid_length, lid_width, lid_height)
    inner_lid = Box(lid_length - 2*wall_thickness, lid_width - 2*wall_thickness, lid_height - wall_thickness)
    
    # Subtract to create hollow lid
    lid = outer_lid - inner_lid
    
    # Add lip for snap fit
    lip = Box(lid_length, lip_width, lip_height)
    lip = lip.locate(Placement((0, -lid_width/2 + lip_width/2, 0)))
    lid = lid + lip
    
    # Add slots for easier removal
    slot1 = Box(slot_width, lid_width - 2*lip_width, slot_depth)
    slot1 = slot1.locate(Placement((0, 0, lid_height/2 - slot_depth/2)))
    
    slot2 = Box(slot_width, lid_width - 2*lip_width, slot_depth)
    slot2 = slot2.locate(Placement((0, 0, -lid_height/2 + slot_depth/2)))
    
    lid = lid - slot1 - slot2
    
    return lid

# Create parts
box_body = create_box_body()
lid = create_lid()

# Set result to list of parts
result = [box_body, lid]

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
