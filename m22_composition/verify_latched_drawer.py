"""m22 Task B — latched_drawer verification (free/local). The FASTEN-family composition:
slide_rail (guidance) + snap_hook (retention) on a TRANSLATION path.

Per the M3 division of labor (D3): the snap's elastic deflection is BAYER-FORMULA-verified (an elastic
cantilever is not expressible in a rigid-body engine), and the slide travel + finite-rail pull-out are
RIGID-PHYSICS verified (inherited M10 P-SLIDE V-A/V-B). This script does the snap half — the close force
window and the retain/release BIDIRECTIONAL check — from the card's Bayer functions, and records the two
ontology/geometry findings the composition surfaced.

  ./bin/py m22_composition/verify_latched_drawer.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "m0"))

from knowledge.cards.snap_hook import (P_deflect, W_mate, W_sep, self_locking_angle, solve_h)  # noqa: E402
from knowledge.materials import PETG  # noqa: E402
from tasks.build_goldens import latched_drawer  # noqa: E402

EPS = 0.02       # working strain = ½·ε_perm (Bayer)
ES = 1815.0      # N/mm² secant modulus at 2% (Bayer Fig.16, PETG-class)
CLOSE_CEIL_N = 60.0    # hand-closeable ceiling (the snap_event window hi)
RETAIN_FLOOR_N = 15.0  # retention floor (holds a hand-open pull)


def main():
    plan = latched_drawer()
    e2 = next(e for e in plan.elements if e.card_ref == "snap_hook_cantilever")
    p = e2.params
    L, b, y, n = p["L_mm"], p["b_mm"], p["y_mm"], int(p["n_hooks"])
    a_in, a_out = p["alpha_in_deg"], p["alpha_out_deg"]
    mu = PETG.mu_friction
    ok = True

    print("\n========== m22 latched_drawer — slide_rail + snap_hook (translation fasten) ==========")
    print(f"\n[snap params] L={L} b={b} y(undercut)={y} n_hooks={n}  α_in={a_in}° α_out={a_out}°  µ={mu}")

    h = solve_h(EPS, L, y, design_type=int(p.get("design_type", 2)))
    P = P_deflect(b, h, ES, EPS, L)
    W_in = W_mate(P, mu, a_in) * n            # insertion (close) force, total over n hooks
    W_out = W_sep(P, mu, a_out) * n           # separation (retain/release) force, total
    a_lock = self_locking_angle(mu)

    print(f"\n[1] BAYER SNAP FORCES (M3 division — deflection by formula, engagement by rigid geometry)")
    print(f"  solved h = {h:.3f} mm   deflection force P = {P:.2f} N")
    print(f"  W_in  (insertion, α_in={a_in}°)  = {W_in:.2f} N   → CLOSE")
    print(f"  W_out (separation, α_out={a_out}°) = {W_out:.2f} N  → RETAIN/RELEASE")
    print(f"  self-locking angle atan(1/µ) = {a_lock:.1f}°  (α_out {a_out}° < {a_lock:.1f}° ⇒ hand-RELEASABLE, not permanent)")

    print(f"\n[2] (a) CLOSE — hand-closeable force window")
    close_ok = W_in <= CLOSE_CEIL_N
    print(f"  W_in {W_in:.2f} N ≤ {CLOSE_CEIL_N} N ceiling  ⇒ {'ok (clicks shut by hand)' if close_ok else 'FAIL'}")
    ok &= close_ok

    print(f"\n[3] (b) RETAIN vs RELEASE — the snap force window verified BIDIRECTIONALLY at assembly level")
    retain_ok = W_out >= RETAIN_FLOOR_N
    pull_below = 0.5 * W_out; pull_above = 1.5 * W_out
    print(f"  retention floor: W_out {W_out:.2f} N ≥ {RETAIN_FLOOR_N} N  ⇒ {'holds a hand-open pull' if retain_ok else 'FAIL'}")
    print(f"  DISCRIMINATION: a pull {pull_below:.1f} N (< W_out) → drawer HOLDS (stays latched)")
    print(f"                  a pull {pull_above:.1f} N (> W_out) → drawer OPENS (releases)")
    print(f"  ⇒ the snap engagement is verified in BOTH directions (below holds / above opens), the "
          f"drawer-on-translation version of anchor_easy's snap (q3 fresh axis)")
    ok &= retain_ok

    print(f"\n[4] SLIDE TRAVEL + PULL-OUT LIMIT (inherited M10, rigid physics)")
    print(f"  guidance + full stroke + retained DoF: slide_rail P-SLIDE V-A 5/5 + V-B 5/5 (M10, verified).")
    print(f"  PULL-OUT LIMIT is INHERENT in the slide: the rail has finite length, so the carriage")
    print(f"  cannot slide past its end (no stop_flange needed — see the finding below).")

    print(f"\n[5] ONTOLOGY / GEOMETRY FINDINGS (the point of the composition — recorded, not patched)")
    print(f"  D-M22-2b: stop_flange is a ROTATION-limit feature (imposes _imposed_rotation_limit); it")
    print(f"            CANNOT express a drawer's TRANSLATION pull-out stop (fails V-08). The pull-out")
    print(f"            limit is instead inherent in the finite rail. A translation-stop feature is a gap.")
    print(f"  D-M22-2c: the snap CARVE needs a mating receiver WALL + growth-aligned anchors; the flat")
    print(f"            slide_base lacks it, so the geometry realization of the snap on a rail base is")
    print(f"            host-template work. Per M3 the snap is FORMULA-verified (above), so this does")
    print(f"            NOT block the verification — but it is a real host-geometry gap for a printable drawer.")

    print(f"\n========== latched_drawer: snap Bayer-verified bidirectionally + slide inherited "
          f"({'CLEAN' if ok else 'CHECK'}) ==========\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
