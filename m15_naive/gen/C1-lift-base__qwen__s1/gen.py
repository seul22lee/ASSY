import sys as _s0
_s0.path[:] = [p for p in _s0.path if 'm15_naive' not in p]
from build123d import *

# Parameters
platform_width = 100
platform_length = 150
platform_height = 20
crank_radius = 25
crank_shaft_diameter = 8
support_height = 40
thread_pitch = 2
thread_diameter = 6
thread_height = 3

# Create the platform
platform = Box(platform_width, platform_length, platform_height)

# Create the crank mechanism
# Crank shaft
shaft = Cylinder(radius=crank_shaft_diameter/2, height=support_height)

# Crank arm
arm_length = crank_radius * 1.5
arm = Box(arm_length, crank_shaft_diameter, support_height)

# Position the crank arm
arm = arm.locate(Placement((0, -crank_shaft_diameter/2, 0)))

# Create the threaded rod
rod = Cylinder(radius=thread_diameter/2, height=support_height + thread_height)

# Create threads on the rod
threads = []
for i in range(int(support_height / thread_pitch)):
    thread = Box(thread_diameter * 0.8, thread_diameter * 0.8, thread_height)
    thread = thread.locate(Placement((0, 0, i * thread_pitch)))
    threads.append(thread)

# Combine all parts for the crank assembly
assembly = shaft + arm + rod
for thread in threads:
    assembly = assembly + thread

# Create support structure
support = Box(platform_width + 20, platform_length + 20, support_height)

# Create clearance hole for the crank shaft
clearance_hole = Cylinder(radius=crank_shaft_diameter/2 + 1, height=support_height)

# Position the assembly within the support structure
assembly = assembly.locate(Placement((0, 0, support_height - platform_height)))

# Final parts list
result = [platform, assembly, support]


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
