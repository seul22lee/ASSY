import sys as _s0
_s0.path[:] = [p for p in _s0.path if 'm15_naive' not in p]
from build123d import *

# Parameters
box_length = 60
box_width = 40
box_height = 25
wall_thickness = 2
lid_overlap = 3
hinge_width = 8
hinge_depth = 5
hinge_height = 3
snap_fit_clearance = 0.3

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
    hinge_depth,
    hinge_height,
    align=(Align.CENTER, Align.CENTER, Align.MIN)
)

# Position hinge cutout at front of lid
hinge_cutout = hinge_cutout.locate(Location((0, box_width/2 - hinge_depth/2, 0)))

# Remove hinge cutout from lid
lid = lid - hinge_cutout

# Create hinge on box body
hinge = Box(
    hinge_width,
    hinge_depth,
    hinge_height,
    align=(Align.CENTER, Align.CENTER, Align.MIN)
)

# Position hinge at front of box
hinge = hinge.locate(Location((0, box_width/2 - hinge_depth/2, 0)))

# Add hinge to box body
box_part = box_part + hinge

# Snap fit features
# Add snap ridges on lid edges
snap_ridge_height = 1.5
snap_ridge_width = 3

# Create snap ridges along the front edge of the lid
lid_front_edge = Line(
    (-(box_length/2 + lid_overlap - snap_ridge_width/2), box_width/2, 0),
    (box_length/2 + lid_overlap - snap_ridge_width/2, box_width/2, 0)
)

# Create ridges
snap_ridges = []
for i in range(3):
    ridge_x = -(box_length/2 + lid_overlap - snap_ridge_width/2) + i * (box_length + 2 * lid_overlap) / 4
    ridge = Box(
        snap_ridge_width,
        wall_thickness + snap_fit_clearance,
        snap_ridge_height,
        align=(Align.CENTER, Align.CENTER, Align.MIN)
    )
    ridge = ridge.locate(Location((ridge_x, box_width/2 - wall_thickness/2, 0)))
    snap_ridges.append(ridge)

# Add ridges to lid
lid_with_ridges = lid
for ridge in snap_ridges:
    lid_with_ridges = lid_with_ridges + ridge

# Create corresponding snap sockets on box body
snap_sockets = []
for i in range(3):
    socket_x = -(box_length/2 + lid_overlap - snap_ridge_width/2) + i * (box_length + 2 * lid_overlap) / 4
    socket = Box(
        snap_ridge_width,
        wall_thickness + snap_fit_clearance,
        snap_ridge_height,
        align=(Align.CENTER, Align.CENTER, Align.MIN)
    )
    socket = socket.locate(Location((socket_x, box_width/2 - wall_thickness/2, 0)))
    snap_sockets.append(socket)

# Add sockets to box body
box_with_sockets = box_part
for socket in snap_sockets:
    box_with_sockets = box_with_sockets - socket

# Final parts
result = [box_with_sockets, lid_with_ridges]

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
