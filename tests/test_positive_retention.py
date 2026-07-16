"""Tier0 (d) positive_retention regression.

"Held by gravity only" must fail GEOMETRICALLY, not by annotation. For a snap_event retention
behavior the nose must bear against the catch when the retained piece is pulled out (along the
base→retained separation axis). Pins:

  * box (window catch)  -> bearing area > 0 (≈ y·b) — the lid is actually held.
  * panel (board clip)  -> bearing area = 0 — the compiled window-catch notch clears the nose on
                           +Z lift; the board would lift straight out = held by gravity only. This
                           machine-checks the panel EXPECTED_FAIL reason. (In the pipeline the panel
                           also fails earlier, at ⑥ / D-GEN-4 — this is the independent functional
                           confirmation.)

Run:  ./bin/py tests/test_positive_retention.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from knowledge.cards.snap_hook_geometry import carve
from pipeline.run_snap import _instantiate
from pipeline.s5_geometry import resolve_plan
from tasks.build_goldens import snap_panel, snap_starter
from verify.t0_static import positive_retention_area


def _retention_area(plan, box_params=None):
    resolve_plan(plan, frequent=False)
    pieces = _instantiate(plan)
    if box_params:
        for pid, bp in box_params.items():
            pieces[pid].params.update(bp)
    inst = plan.elements[0]
    binds = [b for b in plan.bindings if b.element_id == inst.id]
    cr = carve(pieces, inst, binds)                       # analysis geometry (no immutable guard)
    catch_pid = next(b.piece_id for b in binds if b.port == "catch_window")
    base_pid = next(pc.id for pc in plan.pieces if pc.is_base)
    ret_pid = next(pc.id for pc in plan.pieces if not pc.is_base)
    bc, rc = cr.parts[base_pid].center(), cr.parts[ret_pid].center()
    pull = np.array([rc.X - bc.X, rc.Y - bc.Y, rc.Z - bc.Z])
    d0 = cr.dims[0]
    return positive_retention_area(cr.tags["hook_" + d0.side_tag], cr.parts[catch_pid], pull)


def test_box_is_retained():
    area = _retention_area(snap_starter(), {"P1": {"box_l": 80.0, "box_w": 60.0,
                                                   "box_h": 40.0, "wall": 2.0}})
    assert area > 0.5, f"box lid must be positively retained, got {area:.2f} mm²"


def test_panel_is_held_by_gravity_only():
    area = _retention_area(snap_panel())
    assert area <= 0.5, (f"panel board clip must have NO pull-out bearing (window notch clears the "
                         f"nose on +Z lift), got {area:.2f} mm²")


def main() -> int:
    tests = [f for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL  {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed"
          + ("  — held-by-gravity fails geometrically" if not failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
