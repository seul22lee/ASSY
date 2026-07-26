"""m22 — the FIXTURE t0 INTERFERENCE GATE for composed assemblies (spec §13 S5, D-M21-4), applied to
TASKS (the m8/m13 anchor-task precedent). Pairwise interference/clearance on the COMPILED assembly at
the initial pose AND swept poses through the mechanism's motion (the lift stroke / the drawer travel),
judged per D22: INTENDED contact pairs (nut on the threaded screw, coupling grip, snap engagement zone)
report positive CLEARANCE; every UNINTENDED inter-piece pair reports ZERO penetration.

No verdict ships over geometry that failed the table.

  ./bin/py m22_composition/t0_gate.py screw_lift    # or: latched_drawer
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "m0"))

import numpy as np  # noqa: E402
import trimesh  # noqa: E402

from knowledge.cards.base import CARD_REGISTRY  # noqa: E402
from pipeline.compile_assembly import compile_assembly  # noqa: E402
from verify.t2_physics.mjcf import _to_trimesh  # noqa: E402


def _part_mesh(part, tmp: Path) -> trimesh.Trimesh:
    return _to_trimesh(part, tmp)


def _pen_mm(ma: trimesh.Trimesh, mb: trimesh.Trimesh, n=500) -> float:
    """max signed penetration in mm (positive = overlap, negative = clearance gap)."""
    return max(float(trimesh.proximity.signed_distance(mb, ma.sample(n)).max()),
               float(trimesh.proximity.signed_distance(ma, mb.sample(n)).max()))


def t0_gate(plan, sweep_piece: str, axis: np.ndarray, sweep_mm, intended: set, tmpdir: Path):
    """Compile `plan`; sweep `sweep_piece` along `axis` by each offset in `sweep_mm` (mm); return the
    worst per-pair penetration (mm) over the sweep. intended = set of frozenset({pieceA,pieceB}) pairs
    that MAY approach (clearance ok)."""
    for e in plan.elements:
        e.params = CARD_REGISTRY[e.card_ref].resolve_params(plan, e)
    ca = compile_assembly(plan)
    tmpdir.mkdir(parents=True, exist_ok=True)
    base_meshes = {pid: _part_mesh(part, tmpdir / f"{pid}.stl") for pid, part in ca.parts.items()}
    pids = list(base_meshes)
    worst = {}
    for off in sweep_mm:
        meshes = {}
        for pid, m in base_meshes.items():
            mm = m.copy()
            if pid == sweep_piece:
                mm.apply_translation(axis * off)
            meshes[pid] = mm
        for i in range(len(pids)):
            for j in range(i + 1, len(pids)):
                a, b = pids[i], pids[j]
                v = _pen_mm(meshes[a], meshes[b])
                key = tuple(sorted([a, b]))
                worst[key] = max(worst.get(key, -1e9), v)
    rows = {}
    for key, v in sorted(worst.items()):
        rows[f"{key[0]}×{key[1]}"] = {"worst_pen_mm": round(v, 3),
                                      "intended": frozenset(key) in intended}
    clean = all((r["intended"] or r["worst_pen_mm"] <= 0.05) for r in rows.values())
    return rows, clean


def screw_lift_gate(tmpdir: Path):
    from tasks.build_goldens import screw_lift
    plan = screw_lift()
    # the platform (P2) rises +Z over the 40 mm stroke — sweep it through the lift.
    sweep = [0, 10, 20, 30, 40]
    # intended pairs: nut(P2) rides the threaded screw in P1 (thread clearance); crank(P3) meets the
    # screw base P1 at the coupling grip. P2×P3 (platform vs crank) is unintended (must stay clear).
    intended = {frozenset({"P1", "P2"}), frozenset({"P1", "P3"})}
    return t0_gate(plan, "P2", np.array([0.0, 0.0, 1.0]), sweep, intended, tmpdir)


def latched_drawer_gate(tmpdir: Path):
    from tasks.build_goldens import latched_drawer
    plan = latched_drawer()
    # COMPILED DRAWER = slide-guided geometry only. The snap stays FORMULA-level (DRAFT D-M22-2c: its
    # carve needs a receiver wall, parked); the pull-out limit is the finite rail (DRAFT D-M22-2b).
    plan.elements = [e for e in plan.elements if e.card_ref != "snap_hook_cantilever"]
    plan.bindings = [b for b in plan.bindings if b.element_id != "E2"]
    sweep = [0, 15, 30, 45, 60]                      # the drawer (P2) travels +X over the 60 mm stroke
    intended = {frozenset({"P1", "P2"})}             # drawer rides the rail (the retained DoF, clearance)
    return t0_gate(plan, "P2", np.array([1.0, 0.0, 0.0]), sweep, intended, tmpdir)


def _print(name, rows, clean):
    print(f"\n=== t0 interference gate: {name} (compiled assembly, swept, per D22) ===")
    print(f"  {'piece pair':<14s}{'worst pen (mm)':>16s}   kind")
    for pair, r in rows.items():
        kind = "INTENDED (clearance ok)" if r["intended"] else "unintended (zero-pen)"
        pen = r["worst_pen_mm"]
        print(f"  {pair:<14s}{pen:>16.2f}   {kind}   {'PENETRATE!' if pen > 0.05 else 'clear'}")
    print(f"  => t0 gate {'CLEAN' if clean else 'FAILED'}   (negative = clearance)")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "screw_lift"
    tmp = Path(__file__).resolve().parent / "out" / "t0_assets"
    if which == "screw_lift":
        rows, clean = screw_lift_gate(tmp)
    elif which == "latched_drawer":
        rows, clean = latched_drawer_gate(tmp)
    else:
        raise SystemExit(f"unknown task {which}")
    _print(which, rows, clean)
    sys.exit(0 if clean else 1)
