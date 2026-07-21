"""Golden G-S1 — reproduce Bayer "Calculation Example I" (PDF p.16) exactly.

If this fails, the CODE is wrong, not the book. The example is the only end-to-end anchor the
snap_hook_cantilever formulas have until a physical print, so it is transcribed verbatim from
the PDF (verified page-by-page) and checked to the tolerances the session brief fixed.

  Given (p.16):  Makrolon PC · l=19 mm · b=9.5 mm · y=2.4 mm (undercut) · α=30°
                 ε_perm = 4% (Table 2, p.12) → working ε = ½·ε_perm = 2% = 0.02
                 Es = 1815 N/mm² (Fig.16 at ε=2.0%) · μ = 0.6 (Table 3: PC-on-PC 0.50×1.2)
  Find:          h = 3.28 mm (±1%) · P = 32.5 N (±2%) · W = 58.5 N (±2%)
                 Fig.18 factor (μ=0.6, α=30°) = 1.8

Run:  ./bin/py tests/test_golden_bayer.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from knowledge.cards.snap_hook import (P_deflect, W_mate, fig18_factor, solve_h,
                                                  y_perm)

# --- Example I inputs (PDF p.16) ---------------------------------------------------------
L, B, Y, ALPHA = 19.0, 9.5, 2.4, 30.0
EPS = 0.02          # = ½ · ε_perm(4%)
ES = 1815.0         # N/mm² (Fig.16 @ 2%)
MU = 0.6            # Table 3: PC-on-PC = 0.50 × 1.2
DESIGN = 2          # "design type 2, shape A" (p.16 / Fig.19)

# --- expected outputs (PDF p.16) ---------------------------------------------------------
H_EXP, P_EXP, W_EXP, FACTOR_EXP = 3.28, 32.5, 58.5, 1.8


def _close(got, exp, tol_frac, label):
    assert abs(got - exp) <= tol_frac * exp, \
        f"{label}: got {got:.4f}, expected {exp} (±{tol_frac*100:.0f}%)"


def test_solve_h():
    h = solve_h(EPS, L, Y, design_type=DESIGN)
    _close(h, H_EXP, 0.01, "h (p.16a)")


def test_deflection_force_P():
    # Use the book's rounded h=3.28 so P is checked independently of solve_h's last digit.
    P = P_deflect(B, H_EXP, ES, EPS, L)
    _close(P, P_EXP, 0.02, "P (p.16b)")


def test_fig18_factor():
    _close(fig18_factor(MU, ALPHA), FACTOR_EXP, 0.02, "Fig.18 factor")


def test_mating_force_W():
    W = W_mate(P_EXP, MU, ALPHA)
    _close(W, W_EXP, 0.02, "W (p.16c)")


def test_end_to_end_chain():
    # The whole chain from solved h, no book-rounded intermediates: h → P → W.
    h = solve_h(EPS, L, Y, design_type=DESIGN)
    P = P_deflect(B, h, ES, EPS, L)
    W = W_mate(P, MU, ALPHA)
    _close(h, H_EXP, 0.01, "chain h")
    _close(P, P_EXP, 0.02, "chain P")
    _close(W, W_EXP, 0.02, "chain W")


def test_y_perm_roundtrips_solve_h():
    # solve_h and y_perm are inverses: y_perm(eps, l, solve_h(eps,l,y)) == y.
    h = solve_h(EPS, L, Y, design_type=DESIGN)
    y_back = y_perm(EPS, L, h, design_type=DESIGN)
    _close(y_back, Y, 1e-9, "y_perm∘solve_h")


def test_design1_coefficient():
    # Design 1 (constant section) coefficient 0.67 — a different, smaller permissible deflection
    # than design 2 (1.09). Guards the Table 1 shape-A coefficients.
    h1 = solve_h(EPS, L, Y, design_type=1)
    h2 = solve_h(EPS, L, Y, design_type=2)
    assert abs(h2 / h1 - 1.09 / 0.67) < 1e-6, "design2/design1 must be 1.09/0.67 (Table 1, p.9)"


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
          + ("  — Calc Example I reproduced" if not failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
