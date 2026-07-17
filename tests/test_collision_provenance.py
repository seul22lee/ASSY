"""D-M8-4, mechanized: every collision geom must trace to a declared source, or the build FAILS.

The regression this pins: m8 shipped a "designed open-stop" that was a fabrication — a collision
prim conjured in the physics driver, with no solid in the compiled STEP and no entity in the IR. It
turned a failing V-B green and nothing in the toolchain objected. The rule is now a BUILD ERROR, not
a warning, and these tests are the teeth:

  1. the real hints (cards + templates) are fully sourced and accepted
  2. a prim with NO source is refused
  3. a prim with a FORGED source (an entity the plan does not declare) is refused
  4. THE ACTUAL RETRACTED BACKSTOP, injected verbatim, is refused
  5. build_mjcf without a plan is refused — provenance cannot be checked against nothing

Run:  ./bin/py tests/test_collision_provenance.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pathlib import Path as _P

from pipeline.compile_assembly import compile_assembly
from tasks.build_goldens import anchor_easy
from tasks.run_m8_t2 import build_hints
from verify.t2_physics.mjcf import (UnsourcedCollisionPrim, assert_sourced, build_mjcf,
                                    declared_sources)


def _fixture(variant="stop"):
    plan = anchor_easy(variant)
    return plan, build_hints(plan, compile_assembly(plan))


def _refuses(hints, plan, must_mention):
    try:
        assert_sourced(hints, plan)
    except UnsourcedCollisionPrim as e:
        assert must_mention in str(e), f"refused, but for the wrong reason: {e}"
        return str(e)
    raise AssertionError("BUILD ACCEPTED an unsourced/forged collision prim — D-M8-4 is not enforced")


def test_real_hints_are_fully_sourced():
    """Every prim the cards and templates emit names a source the plan declares."""
    plan, hints = _fixture()
    assert_sourced(hints, plan)                      # must not raise
    ok = declared_sources(plan)
    assert "card:pin_hinge@E1" in ok and "card:stop_flange@F1" in ok
    assert "template:box_shell" in ok and "template:lid_panel" in ok
    seen = {p.get("source") for prims in hints.values() for p in prims}
    assert seen <= ok and None not in seen, f"unsourced prims leaked: {seen - ok}"


def test_unsourced_prim_is_refused():
    plan, hints = _fixture()
    hints["P1"] = hints["P1"] + [{"type": "box", "frame": "world", "pos": (0, 0, 50),
                                  "size": (5, 5, 5)}]          # no source at all
    _refuses(hints, plan, "declares NO source")


def test_forged_source_is_refused():
    """A source that names no declared IR entity is refused — inventing geometry cannot be done by
    simply asserting a provenance the plan does not back."""
    plan, hints = _fixture()
    hints["P1"] = hints["P1"] + [{"type": "box", "frame": "world", "pos": (0, 0, 50),
                                  "size": (5, 5, 5), "source": "card:pin_hinge@E99"}]
    _refuses(hints, plan, "resolves to NO declared IR entity")
    hints2 = dict(hints); hints2["P1"] = hints2["P1"][:-1] + [
        {"type": "box", "frame": "world", "pos": (0, 0, 50), "size": (5, 5, 5),
         "source": "template:nonexistent_template"}]
    _refuses(hints2, plan, "resolves to NO declared IR entity")


def test_the_retracted_backstop_is_refused():
    """THE regression. This is the retracted prim verbatim (D-M8-4): a V-B-only 'open_stop' ledge
    behind the hinge axis, with no carve and no IR entity behind it. It must not build."""
    plan, hints = _fixture("nostop")                  # the no-stop design it was smuggled into
    ca = compile_assembly(plan)
    ap = ca.axes["E1"]["point"]
    backstop = {"type": "box", "frame": "world",
                "pos": (ap[0], ap[1] - 10.0, ap[2] + 8.0),
                "size": (38.0, 2.0, 10.0), "modes": ["V-B"], "role_hint": "open_stop"}
    hints["P1"] = hints["P1"] + [backstop]
    msg = _refuses(hints, plan, "declares NO source")
    assert "open_stop" in msg, "the refusal must name the offending prim"


def test_build_mjcf_without_a_plan_is_refused():
    """Provenance cannot be verified against a plan we were not given, so no plan ⇒ no build."""
    plan, hints = _fixture()
    try:
        build_mjcf({}, hints, {"point": (0, 0, 0), "dir": (1, 0, 0)}, "P1", "P2", "P3",
                   "V-B", _P("/tmp/nope"), {}, "t", plan=None)
    except UnsourcedCollisionPrim as e:
        assert "requires `plan`" in str(e)
        return
    raise AssertionError("build_mjcf built a model with no plan to check provenance against")


if __name__ == "__main__":
    fns = [test_real_hints_are_fully_sourced, test_unsourced_prim_is_refused,
           test_forged_source_is_refused, test_the_retracted_backstop_is_refused,
           test_build_mjcf_without_a_plan_is_refused]
    for f in fns:
        f()
    print(f"{len(fns)}/{len(fns)} passed  — D-M8-4 enforced: unsourced collision geometry cannot build")
