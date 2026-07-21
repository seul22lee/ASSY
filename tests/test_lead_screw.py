"""lead_screw card golden (m19 Stage 1) — the Shigley §8-2 / P&B §7.4.3 power-screw rule chain,
reproduced against a HAND-WORKED numeric example. If a formula assert fails, the CODE is wrong, not
the arithmetic (the source section is cited in knowledge/cards/lead_screw.py).

WORKED VALUES (d_major=8, pitch=2, starts=1 mm; µ=0.30, the R5 preset friction):
  lead        = starts × pitch          = 1 × 2            = 2.0 mm
  d_mean      = d_major − pitch/2        = 8 − 1           = 7.0 mm
  lead angle  λ = atan(lead/(π·d_mean))  = atan(2/21.991)  = atan(0.090946) = 5.196°
  tan(λ)                                                    = 0.090946
  SELF-LOCK: tan(λ)=0.0909 ≤ µ=0.30  ⇒  SELF-LOCKS (holds a released load, no brake)
  friction φ  = atan(µ)                  = atan(0.30)      = 16.699°
  efficiency  η = tan(λ)/tan(λ+φ)        = 0.0909/tan(21.895°) = 0.0909/0.40200 = 0.2263

  A COARSE thread (pitch=4, starts=2 → lead=8, d_mean=6): λ=atan(8/18.850)=22.98°, tan=0.4244 > 0.30
  ⇒ does NOT self-lock (it back-drives — would need a pawl, like rack_pinion).

Run:  ./bin/py tests/test_lead_screw.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from knowledge.cards.base import CARD_REGISTRY
from knowledge.cards.lead_screw import lead_screw_dims, lead_screw_mechanics
from ontology.schema import Behavior, DesignPlan, MotionSpec

CARD = CARD_REGISTRY["lead_screw"]


class _I:
    def __init__(self, params=None):
        self.params = params or {}
        self.id = "E1"


def _approx(a, b, tol=1e-2, rel=True):
    return abs(a - b) <= (tol * max(1.0, abs(b)) if rel else tol)


def test_rule_chain_reproduces_the_hand_worked_example():
    f = lead_screw_mechanics(lead_screw_dims({"d_major": 8, "pitch": 2, "starts": 1, "mu": 0.30}))
    assert _approx(f["lead_mm"], 2.0) and _approx(f["travel_per_rev_mm"], 2.0)     # lead = starts×pitch
    assert _approx(f["d_mean_mm"], 7.0)                                            # d_major − pitch/2
    assert _approx(f["lead_angle_deg"], math.degrees(math.atan(2 / (math.pi * 7))))  # 5.196°
    assert _approx(f["tan_lambda"], math.tan(math.atan(2 / (math.pi * 7))))          # 0.0909
    assert _approx(f["friction_angle_deg"], math.degrees(math.atan(0.30)))           # 16.699°
    assert _approx(f["efficiency"], 0.2263, tol=2e-3)
    assert f["self_locks"] is True, "tan(λ)=0.091 ≤ µ=0.30 must self-lock"


def test_self_lock_criterion_is_tan_lambda_le_mu():
    # default (pitch 2, 1 start) self-locks; a COARSE lead (pitch 4, 2 starts) does NOT
    assert lead_screw_mechanics(lead_screw_dims({"d_major": 8, "pitch": 2, "starts": 1}))["self_locks"]
    coarse = lead_screw_mechanics(lead_screw_dims({"d_major": 8, "pitch": 4, "starts": 2}))
    assert coarse["self_locks"] is False, "lead=8 on d_mean=6 gives tan(λ)=0.42 > µ=0.30 → back-drives"


def test_resolve_params_zero_None_all_within_bounds():
    """The m18-audit gap: resolve_params left starts=None. Now EVERY param resolves, in-bounds."""
    ir = DesignPlan(task_id="t", command="c")
    out = CARD.resolve_params(ir, _I({}))
    for name, (lo, hi, _u) in CARD.param_bounds.items():
        assert name in out and out[name] is not None, f"param {name} did not resolve (None)"
        assert lo <= float(out[name]) <= hi, f"{name}={out[name]} outside [{lo},{hi}]"
    # lead is DERIVED from the rule chain, not free
    assert _approx(out["lead"], int(out["starts"]) * float(out["pitch"]))


def test_resolve_params_enforces_self_lock_when_behaviour_demands_it():
    """A hold-under-load behaviour (self_locking=True) must come out self-locking — the card shrinks
    the pitch until tan(λ)≤µ, guaranteeing the axis-4 property it advertises."""
    ir = DesignPlan(task_id="t", command="c", behaviors=[
        Behavior(id="B", phase="use", motion=MotionSpec(kind="rot_to_trans", range_value=40.0,
                                                        range_unit="mm", transmission={"mm_per_rev": 2.0}),
                 realized_by="E1", self_locking=True)])
    out = CARD.resolve_params(ir, _I({"pitch": 4.0, "starts": 2}))   # starts coarse → force self-lock
    assert lead_screw_mechanics(lead_screw_dims(out))["self_locks"], "must resolve to self-locking"


def test_card_surface_complete():
    # ports
    assert {p.name for p in CARD.ports} == {"screw_axis", "nut_mount", "travel_axis"}
    # imposes the assembly threading path (V-08)
    assert any(getattr(b.motion.kind, "value", b.motion.kind) == "translation"
               and getattr(b.phase, "value", b.phase) == "assembly" for b in CARD.imposes)
    # collision_hint source-stamped (D-M8-4)
    prims = CARD.collision_hint(_I())
    assert prims and all(p["source"] == "card:lead_screw@E1" for p in prims)
    # carve produces exactly one solid
    class _B:
        def __init__(s, port): s.port = port; s.piece_id = "P1"; s.anchor = "a"
    r = CARD.carve({}, _I(), [_B("screw_axis")])
    assert len(list(r.tags.values())[0].solids()) == 1
    # verification returns the P-SCREW V-A protocol (card knowledge, D5), criteria/observables split
    ir = DesignPlan(task_id="t", command="c", behaviors=[
        Behavior(id="B", phase="use", motion=MotionSpec(kind="rot_to_trans", range_value=40.0,
                 range_unit="mm", transmission={"mm_per_rev": 2.0}), realized_by="E1")])
    protos = CARD.verification(ir, _I({"stroke": 40.0}))
    assert protos and protos[0].id.startswith("P-SCREW-VA") and protos[0].mode == "V-A"
    names = {c.name for c in protos[0].criteria}
    assert {"reaches_stroke", "self_locks_holds"} <= names


def test_emergent_check_deferred_names_the_curved_contact_gap():
    ec = CARD.taxonomy["emergent_check"]
    assert ec.status == "deferred" and "curved" in ec.reason.lower() and ec.risk


if __name__ == "__main__":
    fns = [test_rule_chain_reproduces_the_hand_worked_example,
           test_self_lock_criterion_is_tan_lambda_le_mu,
           test_resolve_params_zero_None_all_within_bounds,
           test_resolve_params_enforces_self_lock_when_behaviour_demands_it,
           test_card_surface_complete, test_emergent_check_deferred_names_the_curved_contact_gap]
    for f in fns:
        f()
    print(f"{len(fns)}/{len(fns)} passed  — lead_screw card: rule chain (lead=starts×pitch, "
          f"tan λ≤µ self-lock) reproduced to the hand-worked anchor; every param resolves in-bounds; "
          f"full surface (ports/imposes/carve/collision/verification) present")
