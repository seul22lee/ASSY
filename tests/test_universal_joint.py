"""universal_joint card golden (m21 Stage 1) — the Cardan (Hooke) joint kinematics, reproduced
against a HAND-WORKED numeric example. If a formula assert fails, the CODE is wrong, not the
arithmetic (the source section is cited in knowledge/cards/universal_joint.py).

WORKED VALUES (bend β = 15°):
  velocity ratio  ω_out/ω_in = cos β / (1 − sin²β·sin²θ)
  min (θ=0)   = cos 15°            = 0.96593
  max (θ=90°) = 1/cos 15°          = 1.03528
  band        = [0.9659, 1.0353]   (fluctuation 6.9% of nominal)
  mean over a full rev             = 1.0 (lags then leads — a single Cardan is NOT constant-velocity)
  position: tan θ_out = cos β · tan θ_in  → at θ_in=45°, θ_out = atan(cos15°·tan45°) = 43.99°

  β = 0 (straight): band collapses to [1.0, 1.0] — the pulsation VANISHES (the discrimination).

Run:  ./bin/py tests/test_universal_joint.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from knowledge.cards.base import CARD_REGISTRY
from knowledge.cards.universal_joint import (ujoint_dims, ujoint_kinematics, ujoint_position,
                                             ujoint_ratio_at)
from ontology.schema import Behavior, DesignPlan, MotionSpec

CARD = CARD_REGISTRY["universal_joint"]


class _I:
    def __init__(self, params=None):
        self.params = params or {}
        self.id = "E1"


def _approx(a, b, tol=1e-3):
    return abs(a - b) <= tol * max(1.0, abs(b))


def test_kinematics_reproduces_the_hand_worked_example():
    k = ujoint_kinematics(ujoint_dims({"angle_deg": 15.0}))
    assert _approx(k["vel_ratio_min"], math.cos(math.radians(15)))    # 0.96593
    assert _approx(k["vel_ratio_max"], 1 / math.cos(math.radians(15)))  # 1.03528
    assert _approx(k["mean_ratio"], 1.0)
    assert _approx(k["fluctuation_pct"], (1 / math.cos(math.radians(15)) - math.cos(math.radians(15))) * 100)


def test_velocity_ratio_curve_and_band():
    b = math.radians(15.0)
    assert _approx(ujoint_ratio_at(0.0, b), math.cos(b))          # min at θ=0
    assert _approx(ujoint_ratio_at(math.pi / 2, b), 1 / math.cos(b))  # max at θ=90°
    # position: tan θ_out = cos β tan θ_in
    assert _approx(math.degrees(ujoint_position(math.radians(45), b)), 43.9917, tol=1e-3)


def test_beta_zero_has_no_fluctuation():
    """The discrimination anchor: at β=0 the joint is constant-velocity (band collapses to 1)."""
    k = ujoint_kinematics(ujoint_dims({"angle_deg": 0.0}))
    assert _approx(k["vel_ratio_min"], 1.0) and _approx(k["vel_ratio_max"], 1.0)
    assert _approx(k["fluctuation_pct"], 0.0)


def test_resolve_params_zero_None_all_within_bounds():
    """The m18 audit gap: resolve_params left yoke_d=None. Now EVERY param resolves, in-bounds."""
    out = CARD.resolve_params(DesignPlan(task_id="t", command="c"), _I({}))
    for name, (lo, hi, _u) in CARD.param_bounds.items():
        assert name in out and out[name] is not None, f"param {name} did not resolve (None)"
        assert lo <= float(out[name]) <= hi, f"{name}={out[name]} outside [{lo},{hi}]"
    assert float(out["yoke_d"]) >= 2.0 * float(out["bore_d"]), "yoke proportion must be enforced"


def test_card_surface_complete():
    assert {p.name for p in CARD.ports} == {"shaft_in", "shaft_out", "cross_pivot"}
    assert any(getattr(b.motion.kind, "value", b.motion.kind) == "translation"
               and getattr(b.phase, "value", b.phase) == "assembly" for b in CARD.imposes)
    prims = CARD.collision_hint(_I())
    assert prims and all(p["source"] == "card:universal_joint@E1" for p in prims)

    class _B:
        def __init__(s, port): s.port = port; s.piece_id = "P1"; s.anchor = "a"
    r = CARD.carve({}, _I(), [_B("shaft_in")])
    assert len(list(r.tags.values())[0].solids()) == 1
    ir = DesignPlan(task_id="t", command="c", behaviors=[
        Behavior(id="B", phase="use", motion=MotionSpec(kind="rotation", range_value=1080.0,
                 range_unit="deg"), axis_relationship="intersecting", realized_by="E1")])
    protos = CARD.verification(ir, _I({}))
    assert protos and protos[0].id.startswith("P-UJOINT-VA") and protos[0].mode == "V-A"
    names = {c.name for c in protos[0].criteria}
    assert {"transmits_mean_1to1", "cardan_fluctuation_matches_formula"} <= names


def test_emergent_check_argues_kinematics_verified_bearing_deferred():
    ec = CARD.taxonomy["emergent_check"]
    assert ec.status == "deferred"
    # the reason must distinguish the VERIFIED kinematics from the DEFERRED trunnion bearing contact
    assert "verified" in ec.reason.lower() and ("trunnion" in ec.reason.lower() or "bearing" in ec.reason.lower())
    # the risk must note this is pin-class (NOT R2b-curved) — earnable, not fundamental
    assert "pin" in ec.risk.lower()


if __name__ == "__main__":
    fns = [test_kinematics_reproduces_the_hand_worked_example, test_velocity_ratio_curve_and_band,
           test_beta_zero_has_no_fluctuation, test_resolve_params_zero_None_all_within_bounds,
           test_card_surface_complete, test_emergent_check_argues_kinematics_verified_bearing_deferred]
    for f in fns:
        f()
    print(f"{len(fns)}/{len(fns)} passed  — universal_joint card: Cardan kinematics (ω ratio = "
          f"cosβ/(1−sin²β sin²θ), band [cosβ,1/cosβ], mean 1:1) reproduced to the β=15° anchor; β=0 "
          f"flattens it; every param resolves in-bounds (yoke_d fixed); full surface present")
