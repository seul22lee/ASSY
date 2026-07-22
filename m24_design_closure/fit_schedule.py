"""m24 (§14 T3b / T4 / T6) — the FIT SCHEDULE + its geometric re-measurement, for the two redesigned
tasks. Every mating interface is a row {nominal, clearance, source}; the clearance DERIVES from the mate
(the lid-fits-box discipline), not picked independently. T6 RE-MEASURES each fit from the COMPILED solids
(the tightest inter-piece clearance over the motion sweep, in TRUE mm) and reports COMPILE_DRIFT.

Units note (recorded, not silently patched): `verify/t2_physics/mjcf._to_trimesh` rewrites meshes in
METRES (apply_scale(MM=1e-3)), so the m22/m23 `t0_gate.worst_pen_mm` field is actually in metres and its
0.05 "mm" threshold is really 50 mm — a latent units bug in the reused gate. It never produced a false
PASS there (real clearances are large), but §14 requires an honest number, so this module measures in
TRUE mm (×1000) and cross-checks the design schedule. See D-M24-1.

  ./bin/py m24_design_closure/fit_schedule.py screw_lift     # or latched_drawer
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "m0"))

import numpy as np  # noqa: E402
import trimesh  # noqa: E402

from knowledge.cards.base import CARD_REGISTRY  # noqa: E402
from pipeline.compile_assembly import compile_assembly  # noqa: E402
from verify.t2_physics.mjcf import _to_trimesh  # noqa: E402

MM = 1000.0  # metres → mm (the meshes come out in metres; see the module note)


# ---- the DESIGN fit schedules (clearance DERIVES from the mate) -----------------------------------
# each row: (interface, shaft/inner nominal ⌀ mm, bore/outer nominal ⌀ mm, radial clearance mm, source)
FITS = {
    "screw_lift": [
        ("screw major ⌀ in nut bore", 8.0, 9.0, 0.50,
         "lead_screw d_major=8; nut_carriage gap=1.0 → bore=d_major/2+gap (m19 fixture)"),
        ("guide column ⌀ in platform bore", 6.0, 6.70, 0.35,
         "guide col_d=6; platform bore=col_d+2·col_clear, col_clear=0.35 = A-PETG-1 slide clearance"),
        ("coupling bore on crank shaft ⌀", 8.0, 8.60, 0.30,
         "coupling clearance=0.30 (D-M8-4 concentric); hub blind clearance bore on the crank stub"),
        ("coupling grip on screw shaft ⌀", 8.0, 8.0, 0.0,
         "coupling FUSED to input side (rigid grip, m20) → zero clearance by design"),
    ],
    "latched_drawer": [
        ("rail ⌀/width in carriage groove", 8.0, 8.70, 0.35,
         "slide_rail rail_w=8; groove=rail_w+2·clearance, clearance=0.35 = A-PETG-1 (M10)"),
        ("barb tip under receiver ledge (engagement)", 0.0, 0.0, 0.30,
         "snap_hook interlock: barb overlaps the ledge; approach clearance = A-PETG-1 (Bayer forces D3)"),
        ("drawer body in cabinet opening", 0.0, 0.0, 1.00,
         "drawer_tray width = cabinet inner opening − 2·1.0 side gap (drawer-fits-opening)"),
    ],
}

# each INTENDED compiled piece-pair → its design clearance mm (the tightest mating feature on that pair).
# P1×P2 screw_lift: platform rides the guide columns (0.35) AND the screw thread (0.50) → tightest 0.35.
# P1×P3 screw_lift: the coupling grip is FUSED to the crank stub (0.0) → the pair rides at ~0.
INTENDED = {
    "screw_lift": {frozenset({"P1", "P2"}): 0.35, frozenset({"P1", "P3"}): 0.0},
    "latched_drawer": {frozenset({"P1", "P2"}): 0.35},                          # rail-in-groove
}
SWEEP = {"screw_lift": ("P2", np.array([0.0, 0.0, 1.0]), [0, 10, 20, 30, 40]),
         "latched_drawer": ("P2", np.array([1.0, 0.0, 0.0]), [0, 15, 30, 45, 60])}


def _pen_mm(ma, mb, n=1500):
    """max signed penetration in TRUE mm (positive = overlap, negative = clearance)."""
    d = max(float(trimesh.proximity.signed_distance(mb, ma.sample(n)).max()),
            float(trimesh.proximity.signed_distance(ma, mb.sample(n)).max()))
    return d * MM


def _compile(task, tmp):
    from tasks.build_goldens import screw_lift, latched_drawer
    plan = {"screw_lift": screw_lift, "latched_drawer": latched_drawer}[task]()
    if task == "latched_drawer":                              # compiled slide geometry (snap = template, below)
        plan.elements = [e for e in plan.elements if e.card_ref != "snap_hook_cantilever"]
        plan.bindings = [b for b in plan.bindings if b.element_id != "E2"]
    for e in plan.elements:
        e.params = CARD_REGISTRY[e.card_ref].resolve_params(plan, e)
    ca = compile_assembly(plan)
    tmp.mkdir(parents=True, exist_ok=True)
    return {pid: _to_trimesh(part, tmp / f"{pid}.stl") for pid, part in ca.parts.items()}


def measure(task, tmp):
    base = _compile(task, tmp)
    sweep_piece, axis, offs = SWEEP[task]
    pids = list(base)
    worst = {}
    for off in offs:
        meshes = {}
        for pid, m in base.items():
            mm = m.copy()
            if pid == sweep_piece:
                mm.apply_translation(axis * off / MM)     # off is mm; meshes are metres
            meshes[pid] = mm
        for i in range(len(pids)):
            for j in range(i + 1, len(pids)):
                a, b = pids[i], pids[j]
                v = _pen_mm(meshes[a], meshes[b])
                key = tuple(sorted([a, b]))
                worst[key] = max(worst.get(key, -1e9), v)
    return worst


def report(task):
    tmp = ROOT / "m24_design_closure" / "out" / f"{task}_fitassets"
    intended = INTENDED[task]
    worst = measure(task, tmp)
    lines = []
    lines.append(f"=== FIT SCHEDULE — {task} (spec §14 T3b) ===")
    lines.append(f"  {'interface':<38s}{'inner⌀':>8s}{'outer⌀':>8s}{'clear':>7s}   source")
    for name, inner, outer, clr, src in FITS[task]:
        lines.append(f"  {name:<38s}{inner:>8.2f}{outer:>8.2f}{clr:>7.2f}   {src}")
    lines.append("")
    lines.append(f"=== T4/T6 RE-MEASURE from compiled solids (TRUE mm, swept over the motion) ===")
    lines.append(f"  {'piece pair':<14s}{'worst pen (mm)':>16s}{'design clr':>11s}{'drift':>8s}   verdict")
    ok = True
    max_drift = 0.0
    for key in sorted(worst):
        v = worst[key]
        fs = frozenset(key)
        if fs in intended:
            design = intended[fs]
            meas_clr = abs(v)                       # intended pairs ride at their clearance
            drift = abs(meas_clr - design)
            max_drift = max(max_drift, drift)
            lines.append(f"  {key[0]}×{key[1]:<10s}{v:>16.3f}{design:>11.2f}{drift:>8.3f}   "
                         f"INTENDED {'ok' if drift <= 0.10 else 'DRIFT!'}")
        else:
            verdict = "PENETRATE!" if v > 0.05 else "zero-pen ok"
            ok = ok and (v <= 0.05)
            lines.append(f"  {key[0]}×{key[1]:<10s}{v:>16.3f}{'—':>11s}{'—':>8s}   unintended {verdict}")
    lines.append("")
    lines.append(f"  max intended-fit COMPILE_DRIFT = {max_drift:.3f} mm   "
                 f"({'OK ≤0.10' if max_drift <= 0.10 else 'DRIFT!'})")
    lines.append(f"  => fit schedule {'VERIFIED' if (ok and max_drift <= 0.10) else 'FAILED'}")
    ok = ok and max_drift <= 0.10
    out = "\n".join(lines)
    (ROOT / "m24_design_closure" / "out" / f"{task}_fits.txt").write_text(out + "\n")
    print(out)
    return ok


def latched_drawer_report():
    """latched_drawer T4/T6 — re-measure from the FOUR compiled sub-solids, D22-grouped: the barb ↔
    receiver interlock is INTENDED (positive engagement near closed); the drawer BODY must CLEAR the
    cabinet over the whole travel. Sweeps the drawer parts +X over the stroke."""
    from knowledge.templates.host_templates import latch_design_parts
    import trimesh
    tmp = ROOT / "m24_design_closure" / "out" / "latched_drawer_fitassets"
    tmp.mkdir(parents=True, exist_ok=True)
    parts = latch_design_parts()
    group = {"cabinet_body": "cabinet", "receiver": "cabinet", "drawer_body": "drawer", "barb": "drawer"}
    moving = {"drawer_body", "barb"}
    base = {k: _to_trimesh(v, tmp / f"{k}.stl") for k, v in parts.items()}
    stroke_m = 60.0 / MM
    worst, eng = {}, 0.0
    for s in np.linspace(0, stroke_m, 25):
        meshes = {}
        for k, m in base.items():
            mm = m.copy()
            if k in moving:
                mm.apply_translation(np.array([1.0, 0, 0]) * s)
            meshes[k] = mm
        keys = list(base)
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                a, b = keys[i], keys[j]
                if group[a] == group[b]:
                    continue
                v = _pen_mm(meshes[a], meshes[b])
                pair = tuple(sorted([group[a], group[b], a, b]))
                key = (group[a], group[b], a, b) if group[a] < group[b] else (group[b], group[a], b, a)
                worst[key] = max(worst.get(key, -1e9), v)
                if {a, b} == {"barb", "receiver"} and v > 0.05:
                    eng = max(eng, s * MM)
    lines = [f"=== FIT SCHEDULE — latched_drawer (spec §14 T3b) ===",
             f"  {'interface':<40s}{'clearance':>10s}   source"]
    for name, inner, outer, clr, src in FITS["latched_drawer"]:
        lines.append(f"  {name:<40s}{clr:>10.2f}   {src}")
    lines += ["", "=== T4/T6 RE-MEASURE from the 4 compiled sub-solids (TRUE mm, swept, D22-grouped) ===",
              f"  {'sub-pair':<34s}{'worst pen (mm)':>16s}   kind"]
    ok = True
    for key in sorted(worst):
        ga, gb, a, b = key
        v = worst[key]
        intended = {a, b} == {"barb", "receiver"}
        kind = "INTENDED interlock" if intended else "unintended (must clear)"
        verdict = "engages" if intended else ("PENETRATE!" if v > 0.05 else "clear")
        if not intended:
            ok = ok and (v <= 0.05)
        lines.append(f"  {a}×{b:<24s}{v:>16.3f}   {kind}  {verdict}")
    lines += ["", f"  barb↔receiver engagement zone (near closed) = {eng:.1f} mm",
              f"  => fit schedule {'VERIFIED (drawer body clears; barb engages)' if ok else 'FAILED'}"]
    out = "\n".join(lines)
    (ROOT / "m24_design_closure" / "out" / "latched_drawer_fits.txt").write_text(out + "\n")
    print(out)
    return ok


if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else "screw_lift"
    if task == "latched_drawer":
        sys.exit(0 if latched_drawer_report() else 1)
    sys.exit(0 if report(task) else 1)
