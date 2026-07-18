import sys as _s0
_s0.path[:] = [p for p in _s0.path if 'm15_naive' not in p]
from build123d import *

# Parameters
box_length = 50
box_width = 30
box_height = 20
wall_thickness = 2
lid_gap = 1.5
hinge_width = 5
hinge_height = 3
hinge_depth = 2
snap_fit_tolerance = 0.3

# Box body
box_body = Box(box_length, box_width, box_height, align=(Align.CENTER, Align.CENTER, Align.MIN))

# Inner cavity
inner_cavity = Box(
    box_length - 2 * wall_thickness,
    box_width - 2 * wall_thickness,
    box_height - wall_thickness,
    align=(Align.CENTER, Align.CENTER, Align.MIN)
)

# Subtract cavity from body
box_part = box_body - inner_cavity

# Hinge cutout
hinge_cutout = Box(
    hinge_width + 2 * snap_fit_tolerance,
    box_width,
    hinge_height + 2 * snap_fit_tolerance,
    align=(Align.CENTER, Align.CENTER, Align.MIN)
)

# Position hinge cutout at front of box
hinge_cutout = hinge_cutout.locate(Translation((0, 0, box_height - hinge_height)))

# Apply hinge cutout to box
box_part = box_part - hinge_cutout

# Lid
lid_thickness = wall_thickness
lid_length = box_length + 2 * snap_fit_tolerance
lid_width = box_width + 2 * snap_fit_tolerance
lid_height = box_height + lid_thickness

lid = Box(lid_length, lid_width, lid_height, align=(Align.CENTER, Align.CENTER, Align.MIN))

# Lid cavity
lid_cavity = Box(
    lid_length - 2 * wall_thickness,
    lid_width - 2 * wall_thickness,
    lid_height - wall_thickness,
    align=(Align.CENTER, Align.CENTER, Align.MIN)
)

lid_part = lid - lid_cavity

# Snap fit tabs on lid (front)
lid_snap_tabs = []
for i in range(3):
    tab_x = (i - 1) * (box_length / 3)
    tab = Box(
        box_length / 3 - 2 * snap_fit_tolerance,
        wall_thickness + 2 * snap_fit_tolerance,
        lid_height - 2 * snap_fit_tolerance,
        align=(Align.CENTER, Align.CENTER, Align.MIN)
    )
    tab = tab.locate(Translation((tab_x, box_width/2 - wall_thickness/2, 0)))
    lid_snap_tabs.append(tab)

# Combine tabs with lid
for tab in lid_snap_tabs:
    lid_part = lid_part - tab

# Hinge mechanism
hinge_pin = Cylinder(
    radius=hinge_depth/2,
    height=box_width,
    align=(Align.CENTER, Align.CENTER, Align.MIN)
)

# Position hinge pin at front of box
hinge_pin = hinge_pin.locate(Translation((0, 0, box_height - hinge_height)))

# Final parts
result = [box_part, lid_part]

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
