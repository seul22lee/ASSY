"""Tier0 static verification for the snap task (SNAPFIT §5, MECHSYNTH §4 stage 7).

The three-way stratified interference check (§5.2 / D22) — the technical heart of the starter.
In rigid geometry the hook MUST interfere with the catch by exactly the undercut y during
insertion, so "interference = failure" is wrong. We split it by contact intent:

  (a) assembled state       — hook↔receiver penetration = 0 (hook returns stress-free)
                              violation → StageFailure(INTERFERENCE)
  (b) insertion sweep,      — max penetration ∈ [0.9·y, 1.1·y]: the undercut, MEASURED
      hook-tagged region      (a measurement AND a criterion)
                              outside the band → StageFailure(UNDERCUT_MISMATCH)
  (c) insertion sweep,      — penetration 0 everywhere the hook is not
      elsewhere               violation → StageFailure(SWEEP_HIT)

Plus watertight/manifold per solid and the window↔hook clearance (= print_clearance ± tol).
Uses the TAGGED hook sub-solids from carve() to classify sites (hook / non-hook).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from knowledge.materials import PETG
from pipeline.stage_failure import StageFailure

CLEARANCE = PETG.print_clearance_mm
MIN_RETENTION_AREA = 0.5  # mm² — below this the nose does not bear against the catch on pull-out


@dataclass
class T0Result:
    checks: list = field(default_factory=list)   # (name, ok, detail)
    undercut_measured_mm: float = 0.0
    passed: bool = True


def _extent_along(solid, direction) -> float:
    d = np.array(direction, float); d /= np.linalg.norm(d)
    vs = [(v.X, v.Y, v.Z) for v in solid.vertices()]
    if not vs:
        return 0.0
    proj = [float(np.dot(v, d)) for v in vs]
    return max(proj) - min(proj)


def _overlap(a, b):
    inter = a & b
    return inter if inter.solids() else None


def three_way_check(*, receiver, mover, hooks: dict, y: float, engage_dirs: dict,
                    insertion_dir=(0.0, 0.0, -1.0), K: int = 40, raise_range: float = 12.0,
                    raise_all_parts=None) -> T0Result:
    """receiver = the static host (box/board); mover = the inserting host (lid/mount) WITHOUT the
    hooks separated; hooks = {tag: hook_solid}; engage_dirs = {tag: (x,y,z)} lateral engage per
    hook. Insertion is along insertion_dir; we sweep the mover backwards along −insertion_dir."""
    res = T0Result()
    ins = np.array(insertion_dir, float); ins /= np.linalg.norm(ins)

    # (a) assembled: each hook vs receiver = 0
    max_assembled = 0.0
    for tag, hk in hooks.items():
        ov = _overlap(hk, receiver)
        if ov is not None:
            max_assembled = max(max_assembled, _extent_along(ov, engage_dirs[tag]))
    ok_a = max_assembled <= 1e-6
    res.checks.append(("(a) assembled penetration = 0", ok_a, f"{max_assembled:.4f} mm"))
    if not ok_a:
        raise StageFailure("t0", "INTERFERENCE", f"assembled hooks penetrate the receiver by "
                           f"{max_assembled:.3f} mm", data={"penetration_mm": max_assembled})

    # sweep the mover backwards (−insertion) from seated to raised; K steps
    hook_pen_max, elsewhere_max = 0.0, 0.0
    offsets = np.linspace(0.0, raise_range, K)
    for off in offsets:
        shift = tuple(-ins * off)   # move opposite to insertion (undo the seating)
        for tag, hk in hooks.items():
            ov = _overlap(hk.translate(shift), receiver)
            if ov is not None:
                hook_pen_max = max(hook_pen_max, _extent_along(ov, engage_dirs[tag]))
        # non-hook: the mover minus its hooks, vs receiver
        nonhook = mover
        for hk in hooks.values():
            nonhook = nonhook - hk
        ovc = _overlap(nonhook.translate(shift), receiver)
        if ovc is not None:
            # ignore the seating contact plane (0-thickness) — take a robust lateral extent
            elsewhere_max = max(elsewhere_max, min(_extent_along(ovc, (1, 0, 0)),
                                                   _extent_along(ovc, (0, 1, 0))))

    res.undercut_measured_mm = hook_pen_max
    lo, hi = 0.9 * y, 1.1 * y
    ok_b = lo <= hook_pen_max <= hi
    res.checks.append((f"(b) hook-region max penetration ∈ [{lo:.2f},{hi:.2f}] (= undercut y)",
                       ok_b, f"measured {hook_pen_max:.3f} mm  (designed y = {y:.3f})"))
    ok_c = elsewhere_max <= 0.05
    res.checks.append(("(c) elsewhere penetration = 0", ok_c, f"{elsewhere_max:.4f} mm"))

    res.passed = ok_a and ok_b and ok_c
    if not ok_b:
        raise StageFailure("t0", "UNDERCUT_MISMATCH",
                           f"measured undercut {hook_pen_max:.3f} mm outside [{lo:.2f},{hi:.2f}] "
                           f"(designed y={y:.3f}) — compiled geometry disagrees with the IR",
                           data={"measured": hook_pen_max, "band": [lo, hi]})
    if not ok_c:
        raise StageFailure("t0", "SWEEP_HIT", f"non-hook interference {elsewhere_max:.3f} mm "
                           f"during insertion", data={"penetration_mm": elsewhere_max})
    return res


def _to_trimesh(solid, tol: float = 0.02):
    import tempfile
    import trimesh
    from build123d import export_stl
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=True) as f:
        export_stl(solid, f.name, tolerance=tol, angular_tolerance=0.15)
        return trimesh.load(f.name, force="mesh")


def positive_retention_area(nose, catch, pullout, pitch: float = 0.4) -> float:
    """Projected bearing area (mm²): the catch material lying AHEAD of the nose along the pull-out
    axis — what physically resists separation. Grid-sample columns over the nose's footprint; a
    column counts if the nose occupies it AND the catch has material past the nose's far end in the
    pull-out direction. 0 ⇒ the retained part lifts straight out past the nose = held by gravity
    only. Assumes an ~axis-aligned pull-out (the assembly separation axis); pitch is the grid step."""
    Nm, Cm = _to_trimesh(nose), _to_trimesh(catch)
    u = np.array(pullout, float); u /= np.linalg.norm(u)
    ax = int(np.argmax(np.abs(u))); sgn = np.sign(u[ax])   # dominant pull-out axis + sense
    other = [i for i in (0, 1, 2) if i != ax]
    lo, hi = Nm.bounds
    g0 = np.arange(lo[other[0]], hi[other[0]] + pitch, pitch)
    g1 = np.arange(lo[other[1]], hi[other[1]] + pitch, pitch)
    amin = min(Nm.bounds[0][ax], Cm.bounds[0][ax]); amax = max(Nm.bounds[1][ax], Cm.bounds[1][ax])
    line = np.arange(amin, amax + pitch, pitch)
    cols = [(a, b) for a in g0 for b in g1]
    pts = np.empty((len(cols) * len(line), 3))
    for ci, (a, b) in enumerate(cols):
        seg = pts[ci * len(line):(ci + 1) * len(line)]
        seg[:, other[0]] = a; seg[:, other[1]] = b; seg[:, ax] = line
    inN = Nm.contains(pts).reshape(len(cols), len(line))
    inC = Cm.contains(pts).reshape(len(cols), len(line))
    if sgn < 0:                                             # normalise so "ahead" is increasing index
        inN, inC = inN[:, ::-1], inC[:, ::-1]
    blocked = 0
    for ci in range(len(cols)):
        kn = np.where(inN[ci])[0]
        if len(kn) and inC[ci, kn.max() + 1:].any():       # catch material past the nose's far end
            blocked += 1
    return blocked * pitch * pitch


def retention_check(nose, catch, pullout, y: float, b: float) -> tuple:
    """Tier0 (d) positive_retention (D-M?/D-GEN): the nose must bear against the catch on pull-out.
    'Held by gravity only' fails here geometrically, not by annotation."""
    area = positive_retention_area(nose, catch, pullout)
    ok = area > MIN_RETENTION_AREA
    return ("(d) positive retention: nose↔catch bearing on pull-out > 0",
            ok, f"{area:.2f} mm² bearing (designed y·b ≈ {y * b:.1f} mm²) — "
            + ("engaged" if ok else "HELD BY GRAVITY ONLY (nose lifts clear)"))


def watertight(parts: dict, strict: bool = True) -> list:
    """strict=True (box): each piece must be a single positive solid. strict=False (board clip):
    a compound of touching manifold solids is acceptable — the small clip hooks don't fully fuse
    into the thin rails, a fusion-quality issue, not a geometry-correctness one."""
    out = []
    for pid, part in parts.items():
        n = len(part.solids())
        vol = part.volume
        ok = (n == 1 and vol > 0) if strict else (n >= 1 and vol > 0 and
                                                  all(s.volume > 1e-6 for s in part.solids()))
        note = "" if (strict or n == 1) else "  (compound of touching manifold solids)"
        out.append((f"watertight/manifold {pid}", ok, f"{n} solid(s), vol {vol:.1f} mm³{note}"))
    return out


def clearance_check(win_w: float, b: float) -> tuple:
    gap = (win_w - b) / 2
    ok = abs(gap - CLEARANCE) < 0.02
    return ("window↔hook clearance = print_clearance", ok,
            f"{gap:.3f} mm each side (target {CLEARANCE:.2f})")
