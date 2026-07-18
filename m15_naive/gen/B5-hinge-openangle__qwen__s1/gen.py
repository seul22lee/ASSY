import sys as _s0
_s0.path[:] = [p for p in _s0.path if 'm15_naive' not in p]
from build123d import *

# Parameters
box_length = 100.0
box_width = 80.0
box_height = 60.0
wall_thickness = 2.0
lid_hinge_offset = 10.0
lid_hinge_width = 15.0
hinge_pin_diameter = 4.0

# Create the main box body
box_body = Box(box_length, box_width, box_height, align=(Align.CENTER, Align.CENTER, Align.MIN))

# Create the inner cavity with wall thickness
inner_length = box_length - 2 * wall_thickness
inner_width = box_width - 2 * wall_thickness
inner_height = box_height - 2 * wall_thickness

box_cavity = Box(inner_length, inner_width, inner_height, align=(Align.CENTER, Align.CENTER, Align.MIN))

# Subtract cavity from body to create hollow box
box_part = box_body - box_cavity

# Create hinge pin holes in the box
hinge_pin_hole = Cylinder(hinge_pin_diameter/2, wall_thickness * 2, align=(Align.CENTER, Align.CENTER, Align.MIN))

# Position hinge pin holes on the bottom edge
hole1 = hinge_pin_hole.locate(Location((box_length/2 - lid_hinge_offset, 0, 0)))
hole2 = hinge_pin_hole.locate(Location((-box_length/2 + lid_hinge_offset, 0, 0)))

# Subtract holes from box
box_part = box_part - hole1 - hole2

# Create the lid
lid_thickness = wall_thickness
lid_length = box_length - 2 * wall_thickness
lid_width = box_width - 2 * wall_thickness
lid_height = box_height + lid_thickness

lid_body = Box(lid_length, lid_width, lid_height, align=(Align.CENTER, Align.CENTER, Align.MIN))

# Create the lid cavity to match the box interior
lid_cavity = Box(inner_length, inner_width, inner_height, align=(Align.CENTER, Align.CENTER, Align.MIN))

# Subtract cavity from lid
lid_part = lid_body - lid_cavity

# Add hinge cutout to the lid
hinge_cutout = Box(lid_hinge_width, wall_thickness * 2, lid_height, align=(Align.CENTER, Align.CENTER, Align.MIN))

# Position the hinge cutout on the edge of the lid
lid_part = lid_part - hinge_cutout.locate(Location((0, box_width/2 - wall_thickness, 0)))

# Create a small tab to hold the lid in place when closed
lid_tab_length = 10.0
lid_tab_height = 5.0
lid_tab_width = wall_thickness * 2

lid_tab = Box(lid_tab_length, lid_tab_width, lid_tab_height, align=(Align.CENTER, Align.CENTER, Align.MIN))

# Position the tab on the back of the lid
lid_part = lid_part + lid_tab.locate(Location((0, -box_width/2 + wall_thickness + lid_tab_width/2, lid_height/2 - lid_tab_height/2)))

# Create a small gap for the hinge pin to fit through
hinge_gap = Box(lid_hinge_width, 1.5 * wall_thickness, lid_height, align=(Align.CENTER, Align.CENTER, Align.MIN))

# Position the hinge gap on the edge of the lid
lid_part = lid_part - hinge_gap.locate(Location((0, box_width/2 - wall_thickness, 0)))

# Add clearance for the hinge pin in the lid
lid_hinge_pin_hole = Cylinder(hinge_pin_diameter/2, lid_height + 1, align=(Align.CENTER, Align.CENTER, Align.MIN))

# Position the hinge pin hole on the edge of the lid
lid_part = lid_part - lid_hinge_pin_hole.locate(Location((0, box_width/2 - wall_thickness, 0)))

# Create a small gap in the box for the lid to rest when closed
box_rest_gap = Box(lid_length, lid_width, 1.5 * wall_thickness, align=(Align.CENTER, Align.CENTER, Align.MIN))

# Position the rest gap at the bottom of the box
box_part = box_part - box_rest_gap.locate(Location((0, 0, -wall_thickness)))

# Set result to list of parts
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
