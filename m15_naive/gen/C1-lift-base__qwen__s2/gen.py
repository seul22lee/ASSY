import sys as _s0
_s0.path[:] = [p for p in _s0.path if 'm15_naive' not in p]
from build123d import *

# Parameters
platform_width = 100.0
platform_length = 150.0
platform_height = 20.0
shaft_diameter = 12.0
crank_length = 60.0
hole_diameter = 8.0
wall_thickness = 2.0
bearing_inner_diameter = 14.0
bearing_outer_diameter = 24.0
bearing_height = 6.0

# Platform part
platform = Box(platform_width, platform_length, platform_height)

# Crank shaft with bearing
shaft = Cylinder(shaft_diameter/2, platform_height + bearing_height + 10)

# Bearing housing
bearing_housing = Cylinder(bearing_outer_diameter/2, bearing_height)

# Crank handle
handle = Box(crank_length, 8, 4)

# Assembly
with BuildPart() as crank_assembly:
    # Platform base
    platform_base = platform
    
    # Shaft with bearing
    shaft_pos = Location((0, 0, platform_height/2))
    shaft_part = shaft.locate(shaft_pos)
    
    # Bearing housing
    bearing_pos = Location((0, 0, platform_height + bearing_height/2))
    bearing_part = bearing_housing.locate(bearing_pos)
    
    # Crank handle
    handle_pos = Location((crank_length/2, 0, platform_height + bearing_height + 2))
    handle_part = handle.locate(handle_pos)
    
    # Combine parts
    result = [platform_base, shaft_part, bearing_part, handle_part]

# Create platform with clearance holes
with BuildPart() as platform_part:
    platform_body = Box(platform_width, platform_length, platform_height)
    
    # Add clearance holes
    for i in range(2):
        for j in range(3):
            hole_pos = Location(
                (platform_width/2 - 40 + i * 80, 
                 platform_length/2 - 50 + j * 50, 
                 platform_height/2)
            )
            Hole(hole_diameter/2).locate(hole_pos)
    
    result = [platform_body]

# Create crank assembly with proper positioning
with BuildPart() as crank_part:
    # Main shaft
    main_shaft = Cylinder(shaft_diameter/2, platform_height + bearing_height + 10)
    
    # Bearing housing
    bearing_housing = Cylinder(bearing_outer_diameter/2, bearing_height)
    bearing_housing = bearing_housing.locate(Location((0, 0, platform_height + bearing_height/2)))
    
    # Crank handle
    crank_handle = Box(crank_length, 8, 4)
    crank_handle = crank_handle.locate(Location((crank_length/2, 0, platform_height + bearing_height + 2)))
    
    result = [main_shaft, bearing_housing, crank_handle]

# Final assembly with separate parts
platform_part = platform_part.part
result = [platform_part, crank_part.part]

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
