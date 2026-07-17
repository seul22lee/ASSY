"""D-E-10 (ruling: OPTION A) — the `alignment` AssemblyRule kind.

Two drawer rails must be PARALLEL and LEVEL: an instance↔instance POSE relation the ontology could
not state (exclusion is a negative volume, resource a scalar budget; this is neither). Option A adds
a third AssemblyRule kind whose t0 check compares the two bound axis frames — so the requirement is
CHECKABLE and, crucially, FALSIFIABLE (a shared datum, option B, would make it unfalsifiable).

These tests pin exactly that falsifiability:
  1. two parallel, level rails → the rule PASSES,
  2. a SKEWED pair → the rule FAILS (the negative test the brief demanded),
  3. a STEPPED pair (different height) → FAILS when level is required,
  4. V-16 accepts a well-formed alignment predicate and rejects a malformed one.

Run:  ./bin/py tests/test_alignment_rule.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ontology.schema import (AssemblyRule, Behavior, Binding, DesignPlan, ElementInstance,
                             Function, HostTemplate, MotionSpec, Piece)
from ontology.validators import v16
from verify.assembly_rules import check_alignment, evaluate


def _dual_rail_plan(skew_deg=0.0, step_mm=0.0, level=True) -> DesignPlan:
    """A base with two slide_rail instances + an `alignment` rule requiring their travel axes to be
    parallel (and level). skew_deg tilts the right rail's axis; step_mm raises it."""
    from knowledge.templates import TEMPLATES
    base_tr = TEMPLATES["slide_base_dual"](skew_deg=skew_deg, step_mm=step_mm)
    base = HostTemplate(template_ref="slide_base_dual",
                        params=dict(base_tr.params),
                        anchors=[__import__("ontology.schema", fromlist=["Anchor"]).Anchor(
                            name=a.name, kind=a.kind) for a in base_tr.anchors.values()])
    carr = HostTemplate(template_ref="slide_carriage", params={"car_l": 24.0, "car_w": 30.0,
                                                               "car_t": 3.0, "car_z": 3.0},
                        anchors=[__import__("ontology.schema", fromlist=["Anchor"]).Anchor(
                            name="groove_face", kind="face")])
    pieces = [Piece(id="P1", role="base", template_ref="slide_base_dual", is_base=True,
                    params=dict(base_tr.params)),
              Piece(id="P2", role="carriage_L", template_ref="slide_carriage", params={}),
              Piece(id="P3", role="carriage_R", template_ref="slide_carriage", params={})]
    elements = [ElementInstance(id="E1", card_ref="slide_rail", host_pieces=["P1", "P2"],
                                params={"stroke": 60.0}),
                ElementInstance(id="E2", card_ref="slide_rail", host_pieces=["P1", "P3"],
                                params={"stroke": 60.0})]
    bindings = [
        Binding(element_id="E1", port="rail_mount", piece_id="P1", anchor="face_L", mate="flush_face"),
        Binding(element_id="E1", port="carriage_mount", piece_id="P2", anchor="groove_face", mate="flush_face"),
        Binding(element_id="E1", port="travel_axis", piece_id="P1", anchor="rail_L", mate="coincident_axis"),
        Binding(element_id="E2", port="rail_mount", piece_id="P1", anchor="face_R", mate="flush_face"),
        Binding(element_id="E2", port="carriage_mount", piece_id="P3", anchor="groove_face", mate="flush_face"),
        Binding(element_id="E2", port="travel_axis", piece_id="P1", anchor="rail_R", mate="coincident_axis"),
    ]
    ar = AssemblyRule(id="AR1", kind="alignment", provenance="task",
                      subjects=["E1.travel_axis", "E2.travel_axis"],
                      predicate={"axes": ["E1.travel_axis", "E2.travel_axis"],
                                 "relation": "parallel", "level": level})
    behaviors = [Behavior(id="B1", phase="use",
                          motion=MotionSpec(kind="translation", range_value=60.0, range_unit="mm",
                                            bound="min"), realized_by="E1"),
                 Behavior(id="B2", phase="use",
                          motion=MotionSpec(kind="translation", range_value=60.0, range_unit="mm",
                                            bound="min"), realized_by="E2")]
    return DesignPlan(task_id="dual_rail", command="two-rail drawer",
                      functions=[Function(verb="guide", object="drawer", qualifier="two rails")],
                      behaviors=behaviors, pieces=pieces, templates=[base, carr],
                      elements=elements, bindings=bindings, assembly_rules=[ar])


def test_parallel_level_rails_pass():
    ok, detail = check_alignment(_dual_rail_plan(skew_deg=0.0, step_mm=0.0), _rule(0, 0))
    assert ok, detail
    r = evaluate(_dual_rail_plan(), _rule(0, 0), {"parts": {}}, {"point": (0, 0, 0), "dir": (1, 0, 0)})
    assert r["ok"] and r["kind"] == "alignment"


def test_skewed_rails_fail():
    """THE negative test (brief): a 5° skew between the rails must FAIL the alignment rule."""
    plan = _dual_rail_plan(skew_deg=5.0)
    ok, detail = check_alignment(plan, plan.assembly_rules[0])
    assert not ok, f"a 5° skew must fail alignment, got: {detail}"
    assert "MISALIGNED" in detail


def test_stepped_rails_fail_when_level_required():
    plan = _dual_rail_plan(skew_deg=0.0, step_mm=2.0, level=True)
    ok, _ = check_alignment(plan, plan.assembly_rules[0])
    assert not ok, "rails at different heights must fail when level=true"
    # but if level is NOT required, a pure height step is allowed (still parallel)
    plan2 = _dual_rail_plan(skew_deg=0.0, step_mm=2.0, level=False)
    ok2, _ = check_alignment(plan2, plan2.assembly_rules[0])
    assert ok2, "parallel-but-stepped rails pass when level is not required"


def test_v16_alignment_predicate():
    plan = _dual_rail_plan()
    assert not v16(plan), "well-formed alignment rule must be V-16 clean"
    plan.assembly_rules[0].predicate = {"axes": ["E1.travel_axis"], "relation": "parallel"}
    viols = v16(plan)
    assert any("axes[>=2]" in x.detail for x in viols), "one-axis alignment must be rejected"


def _rule(skew, step, level=True):
    return _dual_rail_plan(skew, step, level).assembly_rules[0]


if __name__ == "__main__":
    fns = [test_parallel_level_rails_pass, test_skewed_rails_fail,
           test_stepped_rails_fail_when_level_required, test_v16_alignment_predicate]
    for f in fns:
        f()
    print(f"{len(fns)}/{len(fns)} passed  — alignment kind: parallel/level pass, skew fails, step "
          f"fails when level, V-16 guards the predicate")
