"""pawl_detent golden — the Bayer cantilever arithmetic, reused ASYMMETRICALLY (D-M13-4).

The pawl is snap_hook's mechanical cousin: SAME formulas (P_deflect, fig18_factor, self_locking_angle
from snap_hook_cantilever), used with a shallow drive-over angle and a steep self-locking lock angle.
The m3 permanent-lock cliff (α→90°, where the Fig.18 factor diverges) is here a FEATURE — it is what
blocks back-drive.

WORKED VALUES (L=14, b=5, h=1.0 mm PETG; μ=0.30; α_drive=30°, α_lock=80°):
  self-locking angle   atan(1/μ)          = atan(3.333)        = 73.3°
  deflection force      P                  = (b·h²/6)·(Es·ε/L)  ≈ 1.5 N
  drive-over force      W_drive = P·fig18(30°) with fig18 = (μ+tan30)/(1−μ·tan30) ≈ 1.06
  LOCK: α_lock 80° ≥ 73.3° ⇒ fig18(80°) DIVERGES (μ·tan80 ≥ 1) ⇒ self-locks (back-drive blocked)

If this fails the CODE is wrong, not the arithmetic.

Run:  ./bin/py tests/test_pawl_detent.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from knowledge.cards.base import CARD_REGISTRY
from knowledge.cards.pawl_detent import PawlDims, forces
from knowledge.cards.snap_hook_cantilever import fig18_factor, self_locking_angle


def test_self_locking_angle_is_the_m3_asymptote():
    assert abs(self_locking_angle(0.30) - math.degrees(math.atan(1 / 0.30))) < 1e-9
    assert abs(self_locking_angle(0.30) - 73.3) < 0.1


def test_lock_angle_self_locks_drive_angle_does_not():
    g = PawlDims()                       # α_drive=30, α_lock=80
    f = forces(g)
    assert f["self_locks"], "α_lock 80° must be ≥ the 73.3° self-lock angle → holds"
    # the drive-over angle is BELOW self-lock, so its Fig.18 factor is finite (rides over)
    assert fig18_factor(0.30, g.alpha_drive) < 2.0
    # the lock angle is AT/ABOVE self-lock, so its Fig.18 factor DIVERGES (raises)
    try:
        fig18_factor(0.30, g.alpha_lock)
        assert False, "fig18 at the lock angle must diverge (self-locking)"
    except ValueError:
        pass


def test_drive_over_force_is_within_a_crank_budget():
    """The click-over force must be modest vs the lift force the crank already carries (~4.9 N for
    0.5 kg + platform). A stiff pawl that doubles the crank effort would be a bad design."""
    f = forces(PawlDims())
    assert f["W_drive_N"] < 4.0, f"drive-over {f['W_drive_N']} N too stiff"
    assert f["W_drive_N"] > 0.2


def test_card_resolve_snaps_lock_angle_into_self_locking():
    card = CARD_REGISTRY["pawl_detent"]
    out = card.resolve_params(type("Ir", (), {"behaviors": []})(),
                              type("I", (), {"id": "E4", "params": {"alpha_lock_deg": 40.0}})())
    assert out["alpha_lock_deg"] >= self_locking_angle(0.30), "must snap up into self-locking"


def test_card_is_registered_with_clearance_and_hint():
    card = CARD_REGISTRY["pawl_detent"]
    assert card.has_functional_clearance
    prims = card.collision_hint(type("I", (), {"params": {}, "id": "E4"})())
    assert prims and all(p["source"] == "card:pawl_detent@E4" for p in prims)


if __name__ == "__main__":
    fns = [test_self_locking_angle_is_the_m3_asymptote,
           test_lock_angle_self_locks_drive_angle_does_not,
           test_drive_over_force_is_within_a_crank_budget,
           test_card_resolve_snaps_lock_angle_into_self_locking,
           test_card_is_registered_with_clearance_and_hint]
    for f in fns:
        f()
    print(f"{len(fns)}/{len(fns)} passed  — pawl reuses the Bayer formulas asymmetrically: drive-over "
          f"rides (fig18 finite), lock self-locks (fig18 diverges at 80° ≥ 73.3°), drive force in budget")
