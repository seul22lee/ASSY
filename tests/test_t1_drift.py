"""Tier1 blind-spot regression (D-GEN-3 / §5.3).

Guards the exact hole that let a 5 mm L drift through on the panel: check_drift's IR reference must
be ⑤'s RESOLVED parameters, not the compiled HookDims. If the reference is the compiled dims, a
⑤↔⑥ disagreement is invisible (both sides trace to ⑥). These tests pin:

  1. measured == ir_params            -> no drift (the healthy case)
  2. ir L=12 but ⑥ built/measured 7   -> COMPILE_DRIFT fires (the blind spot, now closed)
  3. the OLD behaviour (reference = dims) would have MISSED case 2 — asserted explicitly, so the
     regression can never silently come back.

Run:  ./bin/py tests/test_t1_drift.py
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.stage_failure import StageFailure
from verify.t1_remeasure import check_drift


@dataclass
class _Dims:
    L: float
    h_root: float
    b: float
    y: float


def test_no_drift_when_ir_matches_measured():
    dims = _Dims(L=12.0, h_root=2.093, b=8.0, y=1.5)
    ir = {"L": 12.0, "h": 2.093, "b": 8.0, "y": 1.5}
    measured = {"L": 12.0, "h": 2.093, "b": 8.0, "y": 1.5}
    r = check_drift(dims, measured, ir_params=ir)
    assert r.ok, "identical IR and measured must not drift"


def test_resolved_ir_catches_L_mismatch():
    """The panel case in miniature: ⑤ resolved L=12, but ⑥ built (and thus measured) L=7. With the
    RESOLVED params as the reference, Tier1 MUST raise COMPILE_DRIFT."""
    dims = _Dims(L=7.0, h_root=2.093, b=8.0, y=1.5)          # ⑥'s compiled dims
    ir = {"L": 12.0, "h": 2.093, "b": 8.0, "y": 1.5}         # ⑤'s resolved IR
    measured = {"L": 7.0, "h": 2.093, "b": 8.0, "y": 1.5}    # geometry agrees with ⑥, not ⑤
    raised = False
    try:
        check_drift(dims, measured, ir_params=ir)
    except StageFailure as e:
        raised = True
        assert e.code == "COMPILE_DRIFT", f"expected COMPILE_DRIFT, got {e.code}"
        assert "L" in e.detail
    assert raised, "a 5 mm ⑤↔⑥ L disagreement must raise COMPILE_DRIFT"


def test_old_dims_reference_would_have_missed_it():
    """Documents WHY the bug was invisible: with the reference = compiled dims (the old default,
    ir_params=None), measured==dims==7, so no drift — the blind spot. Pinning it here means anyone
    who reverts check_drift to trust dims will trip this test."""
    dims = _Dims(L=7.0, h_root=2.093, b=8.0, y=1.5)
    measured = {"L": 7.0, "h": 2.093, "b": 8.0, "y": 1.5}
    r = check_drift(dims, measured, ir_params=None)          # OLD behaviour: reference = dims
    assert r.ok, "the OLD dims-reference path is blind to the ⑤↔⑥ mismatch (that was the bug)"


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
          + ("  — Tier1 blind spot closed" if not failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
