import sys as _s0
_s0.path[:] = [p for p in _s0.path if 'm15_naive' not in p]
from build123d import *

# Parametric variables
L, W, H = 60.0, 40.0, 25.0
wall = 2.0
clearance = 0.3
lip_H = 6.0

# Derived dimensions
lip_l = L - 2 * wall - 2 * clearance
lip_w = W - 2 * wall - 2 * clearance

# Radii to maintain uniform wall thickness
corner_rad = 6.0
lip_rad = max(0.1, corner_rad - wall - clearance)
cavity_rad = max(0.1, lip_rad - wall)

# Snap fit parameters
bump_radius = 1.2
bump_protrusion = 0.5

# --- BASE ---
with BuildPart() as base_part:
    # Lower body
    with BuildSketch(Location((0, 0, 0))):
        RectangleRounded(L, W, corner_rad)
    extrude(amount=H - lip_H)
    
    # Inner lip
    with BuildSketch(Location((0, 0, H - lip_H))):
        RectangleRounded(lip_l, lip_w, lip_rad)
    extrude(amount=lip_H)
    
    # Snap fit bumps (spheres on the outer sides of the lip)
    with Locations(
        (lip_l / 2 - (bump_radius - bump_protrusion), 0, H - lip_H / 2),
        (-lip_l / 2 + (bump_radius - bump_protrusion), 0, H - lip_H / 2)
    ):
        Sphere(radius=bump_radius)
        
    # Hollow out the base
    with BuildSketch(Location((0, 0, H))):
        RectangleRounded(lip_l - 2 * wall, lip_w - 2 * wall, cavity_rad)
    extrude(amount=-(H - wall), mode=Mode.SUBTRACT)
    
    # Chamfer top outer edge of the lip for easy lid alignment
    top_face = base_part.faces().sort_by(Axis.Z)[-1]
    wires = sorted(top_face.wires(), key=lambda w: w.length)
    chamfer(wires[-1].edges(), length=1.0)
    
    # Chamfer the outer meeting edge to form a fingernail grip groove
    step_faces = base_part.faces().filter_by(Axis.Z).filter_by_position(Axis.Z, H - lip_H - 0.01, H - lip_H + 0.01)
    step_outer_wire = sorted(step_faces[0].wires(), key=lambda w: w.length)[-1]
    chamfer(step_outer_wire.edges(), length=0.5)

base = base_part.part

# --- LID ---
lid_H = lip_H + wall
with BuildPart() as lid_part:
    # Main lid body
    with BuildSketch(Location((0, 0, 0))):
        RectangleRounded(L, W, corner_rad)
    extrude(amount=lid_H)
    
    # Hollow out the cavity to receive the base lip
    with BuildSketch(Location((0, 0, 0))):
        RectangleRounded(lip_l + 2 * clearance, lip_w + 2 * clearance, lip_rad + clearance)
    extrude(amount=lip_H, mode=Mode.SUBTRACT)
    
    # Snap fit divots (subtracted spheres)
    with Locations(
        (lip_l / 2 - (bump_radius - bump_protrusion), 0, lip_H / 2),
        (-lip_l / 2 + (bump_radius - bump_protrusion), 0, lip_H / 2)
    ):
        Sphere(radius=bump_radius + clearance, mode=Mode.SUBTRACT)
        
    # Chamfer inner edge to easily slide over the bumps, and outer edge for the grip groove
    bottom_face = lid_part.faces().sort_by(Axis.Z)[0]
    wires = sorted(bottom_face.wires(), key=lambda w: w.length)
    chamfer(wires[0].edges(), length=1.0) # Inner wire
    chamfer(wires[-1].edges(), length=0.5) # Outer wire

# Rotate and translate the lid so it sits flat on the build plate next to the base
lid = lid_part.part.rotate(Axis.X, 180).translate((0, W + 10, lid_H))

# Final output
result = [base, lid]


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
