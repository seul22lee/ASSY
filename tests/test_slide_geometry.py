"""slide_rail geometry regressions (D-D-1).

Pins the two things a G-H review caught or relied on:
  1. the carriage compiles to ONE CONNECTED solid — not a body with a disjoint placeholder plate
     (the "two yellow bodies" bug: the template plate was `+`-added at a different X, offsetting the
     carriage COM off the rail and tripping V-B). A part of the assembly must not be a floating chunk.
  2. the T-rail actually RETAINS: lifting the carriage past the clearance makes the lips capture the
     head (boolean overlap), and it slides free within the stroke.

Run:  ./bin/py tests/test_slide_geometry.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from build123d import CenterOf, Pos
from knowledge.cards.base import CARD_REGISTRY
from knowledge.cards.slide_rail import _carriage_solid, _rail_solid, dims_from
from pipeline.compile_assembly import compile_assembly
from tasks.build_goldens import slide_fixture


def _resolved():
    plan = slide_fixture()
    e1 = plan.element("E1")
    e1.params = CARD_REGISTRY["slide_rail"].resolve_params(plan, e1)
    return plan, compile_assembly(plan)


def test_carriage_is_one_connected_solid():
    """The carriage body must be a SINGLE connected solid. A disjoint second solid in one rigid body
    is the 'phantom carriage' bug — it renders as a floating part and offsets the COM off the rail."""
    _plan, ca = _resolved()
    carriage = ca.parts["P2"]
    n = len(carriage.solids())
    assert n == 1, (f"carriage P2 has {n} disjoint solids — must be ONE connected solid. A second "
                    f"solid is a floating placeholder chunk (the two-yellow-bodies bug, D-D-1).")


def test_carriage_com_is_over_the_rail():
    """The carriage COM must sit within its engagement span over the rail — not pulled off toward a
    floating appendage (which made V-B pitch and trip G-CONV)."""
    plan, ca = _resolved()
    e1 = plan.element("E1")
    g = dims_from(e1.params, float(e1.params["stroke"]))
    com_x = ca.parts["P2"].center(CenterOf.MASS).X
    cx0 = -(g.rail_len / 2 - g.engagement_len / 2)     # engagement centre
    assert abs(com_x - cx0) <= g.engagement_len / 2 + 1e-6, (
        f"carriage COM x={com_x:.1f} is outside the engagement span (centre {cx0:.1f} "
        f"± {g.engagement_len/2:.1f}) — it is cantilevered off the rail.")


def test_t_rail_retains_on_lift_and_slides_free():
    """Retention (the point of a T-rail): lift beyond the clearance → lips capture the head; slide
    within stroke → free."""
    g = dims_from({"rail_w": 8.0, "rail_h": 8.0, "clearance": 0.35, "stroke": 60.0}, 60.0)
    rail = _rail_solid(g, 3.0)
    car = _carriage_solid(g, 3.0)
    below = (rail & (Pos(0, 0, 0.3) * car))          # within clearance → free
    above = (rail & (Pos(0, 0, 0.6) * car))          # beyond clearance → captured
    v_below = below.volume if below.solids() else 0.0
    v_above = above.volume if above.solids() else 0.0
    assert v_below < 1.0, f"within clearance the carriage should be free (got {v_below:.2f} mm³)"
    assert v_above > 1.0, f"beyond clearance the lips must capture the head (got {v_above:.2f} mm³)"


def test_engagement_rule_and_drawer_equality():
    """§3.5: engagement_len ≥ 0.35·stroke, and the drawer-width equality ⑤ derives (D6)."""
    plan, _ca = _resolved()
    e1 = plan.element("E1")
    g = dims_from(e1.params, float(e1.params["stroke"]))
    assert g.engagement_len >= g.min_engagement, "engagement_len must satisfy §3.5 moment rule"
    assert abs(g.drawer_w(100.0) - (100.0 - 2 * (g.rail_w + g.clearance))) < 1e-6


def test_vertical_travel_tightens_retention_gap():
    """D-M13-6: when travel ∥ gravity, the retention lips run at a TIGHT stop gap (sourced
    print_clearance/4), not the loose gravity-seated sliding clearance — so the platform stays on the
    rails without gravity seating it. Horizontal (preload=0) is UNCHANGED."""
    from knowledge.cards.slide_rail import collision_primitives
    horiz = type("I", (), {"params": {"rail_w": 8.0, "rail_h": 8.0, "clearance": 0.35,
                                       "stroke": 120.0}, "id": "E1"})()
    vert = type("I", (), {"params": {"rail_w": 8.0, "rail_h": 8.0, "clearance": 0.35,
                                     "stroke": 120.0, "preload_mm": 0.075}, "id": "E1"})()
    # the lip Y-position encodes the retention gap: tighter (smaller |y|) under preload
    def lip_y(prims):
        lips = [pr for pr in prims if abs(pr["pos"][1]) > 0]   # any off-centre carriage box
        return max(abs(pr["pos"][1]) for pr in prims if pr["owner"] == "carriage")
    ph, pv = collision_primitives(horiz, 120.0), collision_primitives(vert, 120.0)
    assert lip_y(pv) < lip_y(ph), "vertical retention must pull the lips/sides IN (tighter gap)"


def test_vertical_rule_fires_from_axis_hint():
    """slide_rail.resolve_params sets the sourced preload only for a VERTICAL (travel∥gravity) slide."""
    from knowledge.cards.base import CARD_REGISTRY
    from ontology.schema import Behavior, MotionSpec
    card = CARD_REGISTRY["slide_rail"]
    class _Ir:
        def __init__(self, hint):
            self.behaviors = [Behavior(id="B1", phase="use", realized_by="E1",
                              motion=MotionSpec(kind="translation", axis_hint=hint,
                                                range_value=120.0, range_unit="mm", bound="min"))]
    inst = type("I", (), {"id": "E1", "params": {"stroke": 120.0}})()
    v = card.resolve_params(_Ir("vertical"), inst)
    h = card.resolve_params(_Ir("horizontal"), type("I", (), {"id": "E1", "params": {"stroke": 120.0}})())
    assert v.get("preload_mm", 0) > 0, "vertical must set a preload"
    assert h.get("preload_mm", 0) == 0, "horizontal must NOT set a preload"


if __name__ == "__main__":
    fns = [test_carriage_is_one_connected_solid, test_carriage_com_is_over_the_rail,
           test_t_rail_retains_on_lift_and_slides_free, test_engagement_rule_and_drawer_equality,
           test_vertical_travel_tightens_retention_gap, test_vertical_rule_fires_from_axis_hint]
    for f in fns:
        f()
    print(f"{len(fns)}/{len(fns)} passed  — carriage is one connected solid, COM over rail, T-rail "
          f"retains, §3.5 chain holds")
