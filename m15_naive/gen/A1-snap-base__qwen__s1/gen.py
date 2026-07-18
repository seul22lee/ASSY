import sys as _s0
_s0.path[:] = [p for p in _s0.path if 'm15_naive' not in p]
from build123d import *

# Parameters
box_length = 50.0
box_width = 30.0
box_height = 20.0
wall_thickness = 2.0
lip_height = 2.0
clip_width = 3.0
clip_height = 4.0

# Main box body
with BuildPart() as box_part:
    # Create the main box shape
    Box(box_length, box_width, box_height)
    
    # Create inner cavity with wall thickness
    with BuildSketch(Plane.XY.offset(wall_thickness)):
        Rectangle(box_length - 2*wall_thickness, box_width - 2*wall_thickness)
    extrude(amount=box_height - 2*wall_thickness)
    
    # Add lip for lid to click onto
    with BuildSketch(Plane.XZ) as lip_sketch:
        Rectangle(box_length, lip_height)
        Rectangle(box_length - 2*wall_thickness, lip_height - wall_thickness)
    extrude(amount=box_width, mode=Mode.SUBTRACT)
    
    # Add clips for lid retention
    with BuildSketch(Plane.YZ.offset(wall_thickness)) as clip_sketch:
        Rectangle(clip_width, clip_height)
        Rectangle(clip_width - 0.5, clip_height - 0.5)
    extrude(amount=box_length - 2*wall_thickness, mode=Mode.SUBTRACT)
    
    # Add second clip on opposite side
    with BuildSketch(Plane.YZ.offset(box_width - wall_thickness)) as clip_sketch2:
        Rectangle(clip_width, clip_height)
        Rectangle(clip_width - 0.5, clip_height - 0.5)
    extrude(amount=box_length - 2*wall_thickness, mode=Mode.SUBTRACT)

# Lid with corresponding clips
with BuildPart() as lid_part:
    # Create lid base
    Box(box_length + 1, box_width + 1, wall_thickness)
    
    # Add lip for clicking onto box
    with BuildSketch(Plane.XZ.offset(wall_thickness)) as lip_sketch:
        Rectangle(box_length + 1, lip_height)
        Rectangle(box_length - 2*wall_thickness + 1, lip_height - wall_thickness)
    extrude(amount=box_width + 1, mode=Mode.SUBTRACT)
    
    # Add clips that fit into box
    with BuildSketch(Plane.YZ.offset(wall_thickness)) as clip_sketch:
        Rectangle(clip_width, clip_height)
        Rectangle(clip_width - 0.5, clip_height - 0.5)
    extrude(amount=box_length + 1 - 2*wall_thickness, mode=Mode.ADD)
    
    # Add second clip on opposite side
    with BuildSketch(Plane.YZ.offset(box_width + 1 - wall_thickness)) as clip_sketch2:
        Rectangle(clip_width, clip_height)
        Rectangle(clip_width - 0.5, clip_height - 0.5)
    extrude(amount=box_length + 1 - 2*wall_thickness, mode=Mode.ADD)

# Create a small clearance for easier assembly
with BuildPart() as lid_part2:
    Box(box_length + 1, box_width + 1, wall_thickness)
    
    # Add lip for clicking onto box
    with BuildSketch(Plane.XZ.offset(wall_thickness)) as lip_sketch:
        Rectangle(box_length + 1, lip_height)
        Rectangle(box_length - 2*wall_thickness + 1, lip_height - wall_thickness)
    extrude(amount=box_width + 1, mode=Mode.SUBTRACT)
    
    # Add clips that fit into box
    with BuildSketch(Plane.YZ.offset(wall_thickness)) as clip_sketch:
        Rectangle(clip_width, clip_height)
        Rectangle(clip_width - 0.5, clip_height - 0.5)
    extrude(amount=box_length + 1 - 2*wall_thickness, mode=Mode.ADD)
    
    # Add second clip on opposite side
    with BuildSketch(Plane.YZ.offset(box_width + 1 - wall_thickness)) as clip_sketch2:
        Rectangle(clip_width, clip_height)
        Rectangle(clip_width - 0.5, clip_height - 0.5)
    extrude(amount=box_length + 1 - 2*wall_thickness, mode=Mode.ADD)

# Final result with two parts: box and lid
result = [box_part.part, lid_part.part]

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
