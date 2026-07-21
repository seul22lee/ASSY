"""Generate the m3_cards review artifacts (D-ONT-7).

Writes into m3_cards/out/:
  golden_bayer_comparison.md   computed vs Bayer Calc Example I (p.16), with % error
  strain_curve.png             permissible deflection y vs root thickness h (design 1 & 2),
                               with the example anchor point and the ε_allow limit
  force_curve.png              mating / separation force vs angle, retention ratio, example point

Run:  ./bin/py m3_cards/build_review.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from knowledge.cards.snap_hook import (P_deflect, W_mate, W_sep, fig18_factor,
                                                  solve_h, y_perm)

OUT = Path(__file__).parent / "out"

# Calc Example I inputs / expected (PDF p.16)
L, B, Y, EPS, ES, MU, ALPHA, DESIGN = 19.0, 9.5, 2.4, 0.02, 1815.0, 0.6, 30.0, 2
EXP = {"h": 3.28, "P": 32.5, "W": 58.5, "factor": 1.8}


def comparison_table() -> dict:
    h = solve_h(EPS, L, Y, design_type=DESIGN)
    P = P_deflect(B, h, ES, EPS, L)
    factor = fig18_factor(MU, ALPHA)
    W = W_mate(P, MU, ALPHA)
    return {"h": h, "P": P, "W": W, "factor": factor}


def write_table(got: dict) -> None:
    rows = [
        ("h (root thickness)", "mm", "solve_h, design 2", got["h"], EXP["h"], "±1%"),
        ("P (deflection force)", "N", "P_deflect", got["P"], EXP["P"], "±2%"),
        ("Fig.18 factor", "–", "fig18_factor", got["factor"], EXP["factor"], "±2%"),
        ("W (mating force)", "N", "W_mate", got["W"], EXP["W"], "±2%"),
    ]
    lines = [
        "# Golden G-S1 — computed vs Bayer Calc Example I (PDF p.16)",
        "",
        "Inputs (p.16): Makrolon PC · l=19 · b=9.5 · y=2.4 · α=30° · ε=2% · Es=1815 · μ=0.6 · design 2.",
        "",
        "| Quantity | Unit | Formula | Computed | Book (p.16) | Δ | Tol | Pass |",
        "|---|---|---|---:|---:|---:|---|:--:|",
    ]
    all_ok = True
    for name, unit, fn, got_v, exp_v, tol in rows:
        err = (got_v - exp_v) / exp_v
        tolfrac = float(tol.strip("±%")) / 100
        ok = abs(err) <= tolfrac
        all_ok = all_ok and ok
        lines.append(f"| {name} | {unit} | `{fn}` | {got_v:.3f} | {exp_v} | "
                     f"{err*100:+.2f}% | {tol} | {'✓' if ok else '✗'} |")
    lines += ["", f"**Verdict: {'PASS — Calc Example I reproduced' if all_ok else 'FAIL'}.** "
              "If this fails, the code is wrong, not the book.", ""]
    (OUT / "golden_bayer_comparison.md").write_text("\n".join(lines))
    return all_ok


def strain_curve() -> None:
    """Permissible deflection y vs root thickness h, designs 1 & 2, at the example's l and ε.
    Shows design 2 permitting >60% more deflection, and the Example I anchor point."""
    h = np.linspace(1.2, 4.0, 200)  # h_mm param_bounds
    fig, ax = plt.subplots(figsize=(7, 4.6))
    for d, style in ((1, "--"), (2, "-")):
        y = [y_perm(EPS, L, hi, design_type=d) for hi in h]
        ax.plot(h, y, style, lw=2, label=f"design {d} (C={ {1:0.67,2:1.09}[d] })")
    ax.scatter([EXP["h"]], [Y], c="#e53e3e", zorder=5, s=60,
               label=f"Calc Example I (h={EXP['h']}, y={Y})")
    ax.axhline(Y, color="#e53e3e", ls=":", lw=1)
    ax.axvline(EXP["h"], color="#e53e3e", ls=":", lw=1)
    ax.set_xlabel("root thickness h (mm)")
    ax.set_ylabel("permissible deflection / undercut y (mm)")
    ax.set_title(f"y = C·ε·l²/h   (Bayer Table 1 p.9;  l={L} mm, ε={EPS*100:g}%)")
    ax.legend(); ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(OUT / "strain_curve.png", dpi=130); plt.close(fig)


def force_curve() -> None:
    """Mating & separation force vs angle at the example's P and μ, plus the retention ratio.
    Marks the Example I mating point (α=30° → 58.5 N) and the self-locking asymptote."""
    P = EXP["P"]
    lock_deg = np.degrees(np.arctan(1.0 / MU))  # μ·tanα = 1 → force → ∞ (permanent joint)

    def safe(fn, ang):  # NaN past self-lock so the line just breaks
        try:
            return fn(P, MU, ang)
        except ValueError:
            return np.nan

    a = np.linspace(25, 89, 400)  # spans alpha_in and alpha_out bounds
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.4))

    wm = [safe(W_mate, ai) for ai in a]
    ax1.plot(a, wm, lw=2, color="#2b6cb0", label="W = P·(μ+tanα)/(1−μtanα)")
    ax1.scatter([ALPHA], [EXP["W"]], c="#e53e3e", zorder=5, s=60,
                label=f"Example I (α=30°, W={EXP['W']} N)")
    ax1.axvspan(25, 35, color="#bee3f8", alpha=.35, label="α_in bounds [25,35]")
    ax1.axvline(lock_deg, color="#dd6b20", ls="--", lw=1.2,
                label=f"self-lock α={lock_deg:.1f}° (permanent)")
    ax1.set_ylim(0, 300)
    ax1.set_xlabel("angle α (deg)"); ax1.set_ylabel("force W (N)")
    ax1.set_title(f"Mating/separation force  (P={P} N, μ={MU})")
    ax1.legend(fontsize=8); ax1.grid(alpha=.3)

    # retention ratio W_sep(α_out)/W_mate(α_in=30), vs retract angle α_out
    wmate30 = W_mate(P, MU, ALPHA)
    ratio = [safe(W_sep, ao) / wmate30 for ao in a]
    ax2.plot(a, ratio, lw=2, color="#2f855a")
    ax2.axhline(2.0, color="#e53e3e", ls="--", lw=1, label="retention ratio ≥ 2 (target)")
    ax2.axvspan(30, 90, color="#c6f6d5", alpha=.3, label="α_out bounds [30,90]")
    ax2.axvline(lock_deg, color="#dd6b20", ls="--", lw=1.2,
                label=f"self-lock α′={lock_deg:.1f}° → permanent")
    ax2.set_ylim(0, 6)
    ax2.set_xlabel("retract angle α′ (deg)"); ax2.set_ylabel("W_sep / W_mate")
    ax2.set_title("Retention ratio vs retract angle (α_in=30°)")
    ax2.legend(fontsize=8); ax2.grid(alpha=.3)

    fig.tight_layout(); fig.savefig(OUT / "force_curve.png", dpi=130); plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    got = comparison_table()
    ok = write_table(got)
    strain_curve()
    force_curve()
    print(f"  golden_bayer_comparison.md  (pass={ok})")
    print(f"  strain_curve.png")
    print(f"  force_curve.png")
    print(f"  computed: h={got['h']:.3f}  P={got['P']:.2f}  W={got['W']:.2f}  "
          f"factor={got['factor']:.3f}")


if __name__ == "__main__":
    main()
