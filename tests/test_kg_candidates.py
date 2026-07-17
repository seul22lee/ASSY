"""Gate G3.2 (MECHSYNTH §3.7): for EVERY behaviour in BOTH anchor tasks, kg.candidates() must
contain the correct card.

This is the precondition for stage ④ being possible at all: the KG narrows the LLM's choice, so if
the correct card is not among the survivors, no amount of LLM skill can recover it — the failure
would surface at ④ as a wrong selection and be misread as a model error when it is a knowledge-graph
error. Pinning it here separates those two failure classes before the LLM ever runs.

Ground truth = the goldens' own realized_by / imposed_by attributions.

Run:  ./bin/py tests/test_kg_candidates.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from knowledge.kg import candidates
from tasks.build_goldens import anchor_easy, m0_hinge_box, snap_starter


def _expected(plan):
    """(behaviour, card the golden attributes it to) for every attributed behaviour."""
    out = []
    for b in plan.behaviors:
        for inst_id in (b.realized_by, b.imposed_by):
            if not inst_id:
                continue
            inst = plan.instance(inst_id) or plan.feature(inst_id)
            if inst is not None:
                out.append((b, inst.card_ref))
    return out


def _check(plan, label):
    n = 0
    for b, card_ref in _expected(plan):
        got = candidates(b)
        kind = getattr(b.motion.kind, "value", b.motion.kind)
        phase = getattr(b.phase, "value", b.phase)
        assert card_ref in got, (
            f"G3.2 FAIL [{label}] behaviour {b.id} (phase={phase}, motion={kind}) is realized/"
            f"imposed by '{card_ref}' in the golden, but candidates() offered {got} — the KG cannot "
            f"even present the right answer to stage ④.")
        n += 1
    return n


def test_g32_anchor_easy_benchmark():
    """The benchmark anchor (stop variant): includes F1/stop_flange → B3's rotation ceiling."""
    n = _check(anchor_easy("stop"), "anchor_easy[stop]")
    assert n >= 6, f"expected >=6 attributed behaviours, checked {n}"


def test_g32_anchor_easy_nostop():
    _check(anchor_easy("nostop"), "anchor_easy[nostop]")


def test_g32_snap_starter():
    """The second anchor task (T-S1) — the few-shot source for the Easy run (D-E-1)."""
    n = _check(snap_starter(), "snap_starter (T-S1)")
    assert n >= 1


def test_g32_m0_hinge_box_both_variants():
    for v in ("nostop", "stop"):
        _check(m0_hinge_box(v), f"m0_hinge_box[{v}]")


def test_candidates_is_honestly_empty_for_unknown_motion():
    """An unserviceable behaviour returns [] — NOT a fallback to 'all cards'. An empty set is a
    real signal that the ontology cannot express what ② asked for, and ④ must fail on it rather
    than guess."""
    from ontology.schema import Behavior, MotionSpec
    b = Behavior(id="BX", phase="use", motion=MotionSpec(kind="rot_to_trans"))
    assert candidates(b) == ["rack_pinion"]
    b2 = Behavior(id="BY", phase="static", motion=MotionSpec(kind="rot_to_trans"))
    assert candidates(b2) == [], "a static rot_to_trans has no realizer; must be honestly empty"


if __name__ == "__main__":
    fns = [test_g32_anchor_easy_benchmark, test_g32_anchor_easy_nostop, test_g32_snap_starter,
           test_g32_m0_hinge_box_both_variants, test_candidates_is_honestly_empty_for_unknown_motion]
    for f in fns:
        f()
    print(f"{len(fns)}/{len(fns)} passed  — G3.2: candidates() offers the correct card for every "
          f"anchor behaviour")
