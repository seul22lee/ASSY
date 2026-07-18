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
    with BuildSketch() as base:
        Rectangle(box_length, box_width)
    extrude(amount=box_height)
    
    # Create inner cavity
    with BuildSketch(Plane.YZ) as inner_base:
        Rectangle(box_length - 2*wall_thickness, box_width - 2*wall_thickness, align=(Align.CENTER, Align.CENTER))
    extrude(amount=box_height - wall_thickness)
    
    # Create lips for clicking
    with BuildSketch(Plane.XZ) as lip:
        Rectangle(box_length - 2*wall_thickness, lip_height, align=(Align.CENTER, Align.CENTER))
    extrude(amount=wall_thickness)
    
    # Create clips on the sides
    with BuildSketch(Plane.YZ) as clip_base:
        Rectangle(clip_width, clip_height, align=(Align.CENTER, Align.CENTER))
    extrude(amount=wall_thickness)
    
    # Make clips on both sides
    with BuildSketch(Plane.YZ) as clip_base2:
        Rectangle(clip_width, clip_height, align=(Align.CENTER, Align.CENTER))
    extrude(amount=wall_thickness)
    
    # Position clips
    translate((box_length/2 - wall_thickness - clip_width/2, 0, box_height - wall_thickness))
    translate((-box_length/2 + wall_thickness + clip_width/2, 0, box_height - wall_thickness))
    
# Box lid
with BuildPart() as lid_part:
    with BuildSketch() as lid_base:
        Rectangle(box_length, box_width)
    extrude(amount=wall_thickness)
    
    # Create inner cavity for lid
    with BuildSketch(Plane.YZ) as inner_lid:
        Rectangle(box_length - 2*wall_thickness, box_width - 2*wall_thickness, align=(Align.CENTER, Align.CENTER))
    extrude(amount=wall_thickness)
    
    # Create lip for clicking
    with BuildSketch(Plane.XZ) as lid_lip:
        Rectangle(box_length - 2*wall_thickness, lip_height, align=(Align.CENTER, Align.CENTER))
    extrude(amount=wall_thickness)
    
# Create the box with clips and lid
with BuildPart() as box_with_lid:
    # Box body
    with BuildSketch() as base:
        Rectangle(box_length, box_width)
    extrude(amount=box_height)
    
    # Inner cavity
    with BuildSketch(Plane.YZ) as inner_base:
        Rectangle(box_length - 2*wall_thickness, box_width - 2*wall_thickness, align=(Align.CENTER, Align.CENTER))
    extrude(amount=box_height - wall_thickness)
    
    # Outer lip for clicking
    with BuildSketch(Plane.XZ) as lip:
        Rectangle(box_length - 2*wall_thickness, lip_height, align=(Align.CENTER, Align.CENTER))
    extrude(amount=wall_thickness)
    
    # Clips on sides
    with BuildSketch(Plane.YZ) as clip_base:
        Rectangle(clip_width, clip_height, align=(Align.CENTER, Align.CENTER))
    extrude(amount=wall_thickness)
    
    # Position clips
    translate((box_length/2 - wall_thickness - clip_width/2, 0, box_height - wall_thickness))
    translate((-box_length/2 + wall_thickness + clip_width/2, 0, box_height - wall_thickness))
    
# Create a lid that fits the box
with BuildPart() as lid:
    with BuildSketch() as lid_base:
        Rectangle(box_length, box_width)
    extrude(amount=wall_thickness)
    
    # Inner cavity for lid
    with BuildSketch(Plane.YZ) as inner_lid:
        Rectangle(box_length - 2*wall_thickness, box_width - 2*wall_thickness, align=(Align.CENTER, Align.CENTER))
    extrude(amount=wall_thickness)
    
    # Lip for clicking
    with BuildSketch(Plane.XZ) as lid_lip:
        Rectangle(box_length - 2*wall_thickness, lip_height, align=(Align.CENTER, Align.CENTER))
    extrude(amount=wall_thickness)
    
# Final result - two separate parts
result = [box_with_lid.part, lid.part]

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
