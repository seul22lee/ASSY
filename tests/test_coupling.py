"""coupling card golden (m20 Stage 1) — the Shigley §3-12 shaft-torsion + rigid-coupling hub
proportions, reproduced against a HAND-WORKED numeric example. If a formula assert fails, the CODE
is wrong, not the arithmetic (the source section is cited in knowledge/cards/coupling.py).

WORKED VALUES (bore_d=8, τ_allow=25 MPa, body_d=20, length=24):
  rated torque  T = τ·π·d³/16 = 25·π·8³/16 = 25·π·512/16 = 25·π·32 = 800π = 2513.27 N·mm
  hub OD (min)  = 2·bore = 16 mm   → body_d 20 ≥ 16  ⇒ body_d_ok
  hub len (min) = 1.5·bore = 12 mm → length 24 ≥ 12  ⇒ length_ok
  ratio         = 1.0  (a coupling adds no ratio)

Run:  ./bin/py tests/test_coupling.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from knowledge.cards.base import CARD_REGISTRY
from knowledge.cards.coupling import coupling_dims, coupling_mechanics
from ontology.schema import Behavior, DesignPlan, MotionSpec

CARD = CARD_REGISTRY["coupling"]


class _I:
    def __init__(self, params=None):
        self.params = params or {}
        self.id = "E1"


def _approx(a, b, tol=1e-2, rel=True):
    return abs(a - b) <= (tol * max(1.0, abs(b)) if rel else tol)


def test_rule_chain_reproduces_the_hand_worked_example():
    m = coupling_mechanics(coupling_dims({"bore_d": 8, "tau_allow": 25, "body_d": 20, "length": 24}))
    assert _approx(m["torque_capacity_Nmm"], 800 * math.pi)      # τ·π·d³/16 = 800π = 2513.27 N·mm
    assert _approx(m["hub_od_min_mm"], 16.0)                     # 2·bore
    assert _approx(m["hub_len_min_mm"], 12.0)                    # 1.5·bore
    assert m["body_d_ok"] and m["length_ok"]
    assert _approx(m["ratio"], 1.0)                              # no ratio


def test_torque_scales_with_bore_cubed():
    t8 = coupling_mechanics(coupling_dims({"bore_d": 8}))["torque_capacity_Nmm"]
    t16 = coupling_mechanics(coupling_dims({"bore_d": 16}))["torque_capacity_Nmm"]
    assert _approx(t16 / t8, 8.0, tol=1e-3)                      # (16/8)³ = 8× (τ·π·d³/16)


def test_resolve_params_zero_None_all_within_bounds():
    ir = DesignPlan(task_id="t", command="c")
    out = CARD.resolve_params(ir, _I({}))
    for name, (lo, hi, _u) in CARD.param_bounds.items():
        assert name in out and out[name] is not None, f"param {name} did not resolve (None)"
        assert lo <= float(out[name]) <= hi, f"{name}={out[name]} outside [{lo},{hi}]"
    # hub proportions are DERIVED + enforced: body_d ≥ 2·bore, length ≥ 1.5·bore
    m = coupling_mechanics(coupling_dims(out))
    assert m["body_d_ok"] and m["length_ok"], "resolve must enforce the hub proportions"


def test_resolve_enforces_hub_proportions_for_a_large_bore():
    """A large bore forces body_d/length up so the advertised capacity geometry actually holds."""
    out = CARD.resolve_params(DesignPlan(task_id="t", command="c"), _I({"bore_d": 18.0}))
    assert float(out["body_d"]) >= 2.0 * 18.0            # ≥ 36
    assert float(out["length"]) >= 1.5 * 18.0            # ≥ 27
    m = coupling_mechanics(coupling_dims(out))
    assert m["body_d_ok"] and m["length_ok"]


def test_card_surface_complete():
    # ports
    assert {p.name for p in CARD.ports} == {"shaft_in", "shaft_out"}
    # imposes the assembly shaft-insertion path (V-08)
    assert any(getattr(b.motion.kind, "value", b.motion.kind) == "translation"
               and getattr(b.phase, "value", b.phase) == "assembly" for b in CARD.imposes)
    # collision_hint source-stamped (D-M8-4)
    prims = CARD.collision_hint(_I())
    assert prims and all(p["source"] == "card:coupling@E1" for p in prims)
    # carve produces exactly one solid
    class _B:
        def __init__(s, port): s.port = port; s.piece_id = "P1"; s.anchor = "a"
    r = CARD.carve({}, _I(), [_B("shaft_in")])
    assert len(list(r.tags.values())[0].solids()) == 1
    # verification returns the P-COUPLING V-A protocol, criteria = ratio + torque (the non-tautology)
    ir = DesignPlan(task_id="t", command="c", behaviors=[
        Behavior(id="B", phase="use", motion=MotionSpec(kind="rotation", range_value=1080.0,
                 range_unit="deg"), realized_by="E1")])
    protos = CARD.verification(ir, _I({}))
    assert protos and protos[0].id.startswith("P-COUPLING-VA") and protos[0].mode == "V-A"
    names = {c.name for c in protos[0].criteria}
    assert {"transmits_ratio", "transmits_rated_torque"} <= names


def test_emergent_check_names_the_rigid_no_curved_contact_reasoning():
    ec = CARD.taxonomy["emergent_check"]
    # concentric/rigid hub → the reason must explain there is no curved-contact V-B gap
    assert "concentric" in ec.reason.lower() or "curved" in ec.reason.lower()
    assert ec.risk


if __name__ == "__main__":
    fns = [test_rule_chain_reproduces_the_hand_worked_example,
           test_torque_scales_with_bore_cubed,
           test_resolve_params_zero_None_all_within_bounds,
           test_resolve_enforces_hub_proportions_for_a_large_bore,
           test_card_surface_complete,
           test_emergent_check_names_the_rigid_no_curved_contact_reasoning]
    for f in fns:
        f()
    print(f"{len(fns)}/{len(fns)} passed  — coupling card: Shigley §3-12 rule chain (T=τ·π·d³/16, "
          f"hub OD≥2·bore, len≥1.5·bore, ratio 1.0) reproduced to the hand-worked anchor; every param "
          f"resolves in-bounds + hub proportions enforced; full surface (ports/imposes/carve/collision/"
          f"verification) present")
