"""One failing case per validator (V-01..V-12) + positive checks.

No pytest in the env, so this is a plain-assert module with a runner:  ./bin/py tests/test_validators.py
Each test builds an IR that violates exactly one rule and asserts that rule (and, where
isolatable, only that rule) fires. Rules are called in isolation so an unrelated violation in
the fixture cannot mask the one under test.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ontology import validators as V
from ontology.schema import (Anchor, Behavior, Binding, Criterion, DesignPlan, ElementInstance,
                             HostTemplate, MotionSpec, Parameter, Piece, VerificationProtocol)


def _rule_ids(viols):
    return {v.rule for v in viols}


# --- fixtures ---------------------------------------------------------------------------
def _template(anchors=("a1",)):
    return HostTemplate(template_ref="box_shell",
                        anchors=[Anchor(name=n, kind="face") for n in anchors])


def _plan(**kw) -> DesignPlan:
    base = dict(task_id="t", command="c")
    base.update(kw)
    return DesignPlan(**base)


# ======================================================================================
# One failing case per rule
# ======================================================================================
def test_v01_use_behavior_needs_protocol():
    p = _plan(behaviors=[Behavior(id="B1", phase="use", motion=MotionSpec(kind="rotation"))])
    assert "V-01" in _rule_ids(V.v01(p)), "V-01 must flag a use behavior with no verified_by"


def test_v02_anchor_must_exist_in_template():
    p = _plan(
        pieces=[Piece(id="P1", role="base", template_ref="box_shell")],
        templates=[_template(anchors=("real_anchor",))],
        elements=[ElementInstance(id="E1", card_ref="pin_hinge", host_pieces=["P1"])],
        bindings=[Binding(element_id="E1", port="axis", piece_id="P1", anchor="ghost_anchor",
                          mate="flush_face")],
    )
    assert "V-02" in _rule_ids(V.v02(p)), "V-02 must flag an anchor not declared by the template"


def test_v03_port_must_exist_in_card():
    p = _plan(
        pieces=[Piece(id="P1", role="base", template_ref="box_shell")],
        templates=[_template(anchors=("a1",))],
        elements=[ElementInstance(id="E1", card_ref="pin_hinge", host_pieces=["P1"])],
        bindings=[Binding(element_id="E1", port="ghost_port", piece_id="P1", anchor="a1",
                          mate="flush_face")],
    )
    assert "V-03" in _rule_ids(V.v03(p)), "V-03 must flag a port not declared by the card"


def test_v04_parameter_within_bounds():
    p = _plan(parameters=[Parameter(name="x", value=99.0, unit="mm", lo=0.0, hi=1.0,
                                    resolved_by="user")])
    assert "V-04" in _rule_ids(V.v04(p)), "V-04 must flag value outside [lo,hi]"


def test_v05_material_satisfies_requires():
    # Unknown material -> V-05 cannot verify card requires -> violation.
    p = _plan(material="UNOBTANIUM",
              elements=[ElementInstance(id="E1", card_ref="snap_hook_cantilever", host_pieces=["P1"])])
    assert "V-05" in _rule_ids(V.v05(p)), "V-05 must flag an unknown / non-conforming material"


def test_v06_rot_to_trans_needs_transmission():
    p = _plan(behaviors=[Behavior(id="B1", phase="use",
                                  motion=MotionSpec(kind="rot_to_trans"))])
    assert "V-06" in _rule_ids(V.v06(p)), "V-06 must flag rot_to_trans with no transmission"


def test_v07_no_orphan_pieces():
    p = _plan(pieces=[Piece(id="P1", role="lid", template_ref="lid_panel")])  # not base, unbound
    assert "V-07" in _rule_ids(V.v07(p)), "V-07 must flag an orphan piece"


def test_v08_imposed_behavior_registered():
    # Temporarily give a card an imposed behaviour with no matching IR behaviour.
    from knowledge.cards.base import CARD_REGISTRY
    card = CARD_REGISTRY["snap_hook_cantilever"]
    saved = card.imposes
    card.imposes = [Behavior(id="_tmpl", phase="use", motion=MotionSpec(kind="fixed"))]
    try:
        p = _plan(elements=[ElementInstance(id="E2", card_ref="snap_hook_cantilever", host_pieces=["P1"])])
        assert "V-08" in _rule_ids(V.v08(p)), "V-08 must flag an unregistered imposed behaviour"
    finally:
        card.imposes = saved


def test_v09_on_face_uv_needs_uv_in_range():
    p = _plan(bindings=[Binding(element_id="E1", port="beam_root", piece_id="P1",
                                anchor="a1", mate="on_face_uv",
                                offset_params={"u": 1.5, "v": 0.2})])
    assert "V-09" in _rule_ids(V.v09(p)), "V-09 must flag u/v outside [0,1]"


def test_v10_roundtrip_lossless():
    # Positive direction: a well-formed plan round-trips. (A *negative* V-10 case is not
    # constructible without corrupting serialization itself, which pydantic prevents; the
    # honest test is that the rule PASSES on a valid plan and would catch a mismatch.)
    p = _plan(behaviors=[Behavior(id="B1", phase="static", motion=MotionSpec(kind="fixed"))])
    assert V.v10(p) == [], "V-10 must report a valid plan as lossless"


def test_v11_snap_event_needs_force_window():
    p = _plan(behaviors=[Behavior(id="B3", phase="assembly",
                                  motion=MotionSpec(kind="snap_event"))])
    assert "V-11" in _rule_ids(V.v11(p)), "V-11 must flag snap_event with no force window"


def test_v12_reserved_noop():
    # V-12 is a reserved stub (keepout, D-ONT-3). It must be a no-op until implemented, so any
    # plan passes it. This test pins that contract so a future implementation announces itself.
    assert V.v12(_plan()) == [], "V-12 is reserved and must be a no-op this session"


def test_v13_measurement_must_be_registered():
    # A protocol criterion referencing a measurement name not in the controlled registry
    # (D-ONT-6) must fail — the typo-catches-at-sim-time gap this rule closes.
    p = _plan(protocols=[VerificationProtocol(
        id="PR-X", verifies="B1", actuation={"kind": "x"},
        criteria=[Criterion(name="c", observable="not_a_real_measurement", op="<=",
                            threshold=1.0)])])
    assert "V-13" in _rule_ids(V.v13(p)), "V-13 must flag an unregistered measurement key"


def test_v14_window_catch_not_on_retained():
    # D-GEN-5 (④): a window catch (which cuts the receiver) may not target a role='retained'
    # (foreign/immutable) piece. Negative fixture = the board-clip golden. Positive control = the
    # box golden, whose catch is the printed box wall (role='base').
    from tasks.build_goldens import snap_panel, snap_starter
    assert "V-14" in _rule_ids(V.v14(snap_panel())), \
        "V-14 must reject a window_catch bound to the retained board (D-GEN-5)"
    assert "V-14" not in _rule_ids(V.v14(snap_starter())), \
        "V-14 must NOT flag the box (catch = owned, printed wall)"


# --- positive control: the goldens are clean --------------------------------------------
def test_goldens_validate_clean():
    from tasks.build_goldens import m0_hinge_box, snap_starter
    for plan in (m0_hinge_box("nostop"), m0_hinge_box("stop"), snap_starter()):
        viols = V.validate_all(plan)
        assert viols == [], f"{plan.task_id} should be clean, got {[ (v.rule,v.detail) for v in viols]}"


# ======================================================================================
def main() -> int:
    tests = [f for name, f in sorted(globals().items())
             if name.startswith("test_") and callable(f)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL  {t.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
