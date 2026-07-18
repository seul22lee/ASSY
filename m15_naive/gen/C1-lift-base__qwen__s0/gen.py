import sys as _s0
_s0.path[:] = [p for p in _s0.path if 'm15_naive' not in p]
from build123d import *

# Parameters
platform_width = 100.0
platform_depth = 80.0
platform_height = 20.0
shaft_diameter = 12.0
crank_length = 40.0
hole_radius = 5.0
wall_thickness = 2.0
bearing_inner_diameter = 12.0
bearing_outer_diameter = 22.0
bearing_height = 7.0

# Create the platform
platform = Box(platform_width, platform_depth, platform_height)

# Create the crank mechanism
# Shaft
shaft = Cylinder(shaft_diameter/2, platform_height + 10, align=(Align.CENTER, Align.CENTER, Align.MIN))

# Crank arm
crank_arm = Box(crank_length, 6, 4, align=(Align.CENTER, Align.CENTER, Align.MIN))

# Bearing housing
bearing_housing = Cylinder(bearing_outer_diameter/2, bearing_height, align=(Align.CENTER, Align.CENTER, Align.MIN))

# Create the crank assembly
assembly = Compound([shaft, crank_arm, bearing_housing])

# Create the base plate with mounting holes
base_plate = Box(platform_width + 20, platform_depth + 20, 8)

# Add mounting holes for the crank mechanism
mounting_holes = [
    Pos(0, 0, 0) * Cylinder(hole_radius, 10),
    Pos(0, platform_depth/2 - 10, 0) * Cylinder(hole_radius, 10),
    Pos(0, -(platform_depth/2 - 10), 0) * Cylinder(hole_radius, 10),
]

# Create the base with mounting holes
base_with_holes = base_plate - Union(mounting_holes)

# Create the platform with clearance for the crank mechanism
platform_with_clearance = platform + Pos(0, 0, platform_height) * Cylinder(shaft_diameter/2 + 5, 10)

# Create the final assembly
result = [base_with_holes, platform_with_clearance, assembly]

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
