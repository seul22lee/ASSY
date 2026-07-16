"""Golden G3.3 — the pin_hinge card reproduces M0's hand-built hinge dims.

There is no Bayer here; the golden is self-derived, and its source of truth is M0's HingeBox
(m0/hinge_box.py) — the geometry that actually passed STEP→MJCF→P-HINGE (V-A and V-B) and retired
R1. The card formalizes that geometry; this test asserts the card's derivations equal M0's,
number for number, so the cardified hinge IS the proven hinge.

  bore_d      = pin_d + clearance
  knuckle_od  = pin_d + 2·knuckle_wall
  stack_w     = n·knuckle_w + (n−1)·clearance
  chamfer_len = pin_d/2 + clearance          (§3.3 lid-edge rule)
  edge_margin = face_len/2 − stack_w/2       (>= knuckle_w)
  pin_len     = stack_w + 2·protrude

Run:  ./bin/py tests/test_golden_hinge.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "m0"))

from hinge_box import HingeBox               # M0's hand geometry — the source of truth
from knowledge.cards.pin_hinge import dims_from


def _card_dims(p: HingeBox):
    return dims_from({"pin_d": p.pin_d, "knuckle_w": p.knuckle_w, "knuckle_n": p.knuckle_n,
                      "clearance": p.clearance}, face_len=p.box_l)


def test_card_reproduces_m0_derivations():
    p = HingeBox()                            # M0 defaults (the proven geometry)
    g = _card_dims(p)
    checks = {
        "bore_d": (g.bore_d, p.bore_d),
        "knuckle_od": (g.knuckle_od, p.knuckle_od),
        "stack_w": (g.stack_w, p.stack_w),
        "chamfer_len": (g.chamfer_len, p.chamfer_len),
        "edge_margin": (g.edge_margin, p.edge_margin),
        "pin_len": (g.pin_len, p.pin_len),
        "bore_keepout_r": (g.bore_keepout_r, p.bore_keepout_r),
    }
    for name, (card, m0) in checks.items():
        assert abs(card - m0) < 1e-6, f"{name}: card {card} != M0 {m0}"


def test_interleave_matches_m0():
    p = HingeBox()
    g = _card_dims(p)
    card_spans = [(round(a, 4), round(b, 4), o) for a, b, o in g.knuckle_spans()]
    # M0 owns "box"/"lid"; the card uses "A"/"B" for mount_A/mount_B — map and compare.
    m0_spans = [(round(a, 4), round(b, 4), {"box": "A", "lid": "B"}[o]) for a, b, o in p.knuckle_spans()]
    assert card_spans == m0_spans, f"interleave mismatch:\n card {card_spans}\n  M0 {m0_spans}"


def test_chamfer_and_clearance_rules():
    p = HingeBox()
    g = _card_dims(p)
    assert g.chamfer_len >= p.pin_d / 2 + p.clearance - 1e-9, "chamfer rule (§3.3) violated"
    assert abs(g.bore_d - (p.pin_d + p.clearance)) < 1e-9, "bore clearance = print clearance (§3.3)"
    assert g.rule_violations() == [], f"unexpected rule violations: {g.rule_violations()}"


def test_variant_n5():
    p = HingeBox(knuckle_n=5)
    g = _card_dims(p)
    assert abs(g.stack_w - p.stack_w) < 1e-6 and len(g.knuckle_spans()) == 5


def main() -> int:
    tests = [f for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for t in tests:
        try:
            t(); print(f"  PASS  {t.__name__}")
        except AssertionError as e:
            failed += 1; print(f"  FAIL  {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed"
          + ("  — card == M0 proven hinge" if not failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
