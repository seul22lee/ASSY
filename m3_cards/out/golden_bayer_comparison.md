# Golden G-S1 — computed vs Bayer Calc Example I (PDF p.16)

Inputs (p.16): Makrolon PC · l=19 · b=9.5 · y=2.4 · α=30° · ε=2% · Es=1815 · μ=0.6 · design 2.

| Quantity | Unit | Formula | Computed | Book (p.16) | Δ | Tol | Pass |
|---|---|---|---:|---:|---:|---|:--:|
| h (root thickness) | mm | `solve_h, design 2` | 3.279 | 3.28 | -0.03% | ±1% | ✓ |
| P (deflection force) | N | `P_deflect` | 32.526 | 32.5 | +0.08% | ±2% | ✓ |
| Fig.18 factor | – | `fig18_factor` | 1.801 | 1.8 | +0.08% | ±2% | ✓ |
| W (mating force) | N | `W_mate` | 58.591 | 58.5 | +0.16% | ±2% | ✓ |

**Verdict: PASS — Calc Example I reproduced.** If this fails, the code is wrong, not the book.
