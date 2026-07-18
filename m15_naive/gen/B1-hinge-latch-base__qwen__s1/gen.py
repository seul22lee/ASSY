import sys as _s0
_s0.path[:] = [p for p in _s0.path if 'm15_naive' not in p]
from build123d import *

# Parameters
box_length = 80.0
box_width = 60.0
box_height = 40.0
wall_thickness = 2.0
lid_overlap = 5.0
hinge_width = 8.0
hinge_height = 10.0
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

# Lid
lid_thickness = wall_thickness
lid = Box(
    box_length + 2 * lid_overlap,
    box_width,
    lid_thickness,
    align=(Align.CENTER, Align.CENTER, Align.MIN)
)

# Create hinge cutout in lid
hinge_cutout = Box(
    hinge_width,
    box_width - 2 * wall_thickness,
    hinge_height,
    align=(Align.CENTER, Align.CENTER, Align.MIN)
)

# Position hinge cutout at front of lid
hinge_cutout = hinge_cutout.locate(Location((0, 0, box_height)))

# Remove hinge cutout from lid
lid = lid - hinge_cutout

# Create hinge on box
hinge = Box(
    hinge_width,
    box_width - 2 * wall_thickness,
    hinge_height,
    align=(Align.CENTER, Align.CENTER, Align.MIN)
)

# Position hinge at front of box
hinge = hinge.locate(Location((0, 0, box_height)))

# Box with hinge
box_with_hinge = box_part + hinge

# Snap fit features
# Add snap fit tabs to lid
snap_tab_width = 5.0
snap_tab_height = 3.0
snap_tab_depth = wall_thickness - snap_fit_tolerance

# Create snap tabs on lid edges
snap_tabs = []
for i in [-1, 1]:
    tab = Box(
        snap_tab_width,
        snap_tab_height,
        snap_tab_depth,
        align=(Align.CENTER, Align.CENTER, Align.MIN)
    )
    tab = tab.locate(Location((i * (box_length + lid_overlap) / 2 - i * snap_tab_width / 2, 0, 0)))
    snap_tabs.append(tab)

# Combine all snap tabs
snap_fit_features = Union(snap_tabs)

# Add snap fit features to lid
lid_with_snap = lid + snap_fit_features

# Create the final parts
result = [box_with_hinge, lid_with_snap]

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
