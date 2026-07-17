"""rack_pinion §3.6 golden — the formulas are EXECUTED and pinned to hand-worked arithmetic (D5:
knowledge as executable formulas, not retrieved text). Self-derived (no external handbook example
exists for this card), so the arithmetic is worked out here in full and the code must reproduce it.

WORKED EXAMPLE (module m = 5 mm, tooth count z = 12, stroke = 120 mm, backlash bl = 0.20 mm):

  pitch radius     rp   = m·z/2      = 5·12/2         = 30.0   mm
  pitch diameter   d    = m·z        = 5·12           = 60.0   mm
  travel / rev     tpr  = π·m·z      = π·5·12         = 188.4956 mm   (the pitch circumference)
  rack length      L    = stroke + tpr/4 = 120 + 188.4956/4 = 167.124 mm   (engagement margin)
  axis→rack dist   a    = rp                          = 30.0   mm
  rack circular pitch    p = π·m     = π·5            = 15.708 mm
  rack tooth thickness   t = p/2 − bl/2 = 15.708/2 − 0.10 = 7.754 mm   (at the pitch line)

The rack teeth are STRAIGHT flanks at the pressure angle — the involute's z→∞ limit, which is
EXACTLY conjugate to an involute pinion (the one case where straight flanks are correct, not an
approximation). So the pinion reuses M1's involute builder verbatim (profile="involute"; the
trapezoid is dead, D-M1-1) and only the rack is new geometry.

If this fails, the CODE is wrong (a formula or unit slip), not the arithmetic above.

Run:  ./bin/py tests/test_rack_pinion_geometry.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from knowledge.cards.base import CARD_REGISTRY
from knowledge.cards.rack_pinion import build_pinion, build_rack, collision_primitives, dims_from


def _g():
    return dims_from({"module": 5.0, "z_pinion": 12, "stroke": 120.0, "backlash": 0.20})


def test_section36_formulas_match_worked_arithmetic():
    g = _g()
    assert abs(g.rp - 30.0) < 1e-9, g.rp
    assert abs(g.pitch_d - 60.0) < 1e-9, g.pitch_d
    assert abs(g.travel_per_rev - math.pi * 60.0) < 1e-6, g.travel_per_rev
    assert abs(g.travel_per_rev - 188.4956) < 1e-3, g.travel_per_rev
    assert abs(g.rack_len - 167.124) < 1e-3, g.rack_len          # 120 + 188.4956/4
    assert abs(g.axis_to_rack - 30.0) < 1e-9, g.axis_to_rack


def test_rack_length_covers_stroke_plus_engagement_margin():
    """§3.6: L_rack ≥ stroke + π·m·z/4 — the rack must be long enough that the pinion never runs off
    the toothed span across the full stroke."""
    g = _g()
    assert g.rack_len >= g.stroke + g.travel_per_rev / 4.0 - 1e-9


def test_pinion_is_one_involute_solid():
    """The pinion is ONE connected solid built by M1's involute builder (profile carried through)."""
    g = _g()
    pin = build_pinion(g)
    assert len(pin.solids()) == 1, f"pinion must be one solid, got {len(pin.solids())}"
    assert pin.volume > 0


def test_rack_is_one_solid_and_spans_its_length():
    """The rack is one connected toothed bar spanning ~rack_len in X (the two-yellow-bodies lesson,
    D-D-1: a fixture body must not be a disjoint chunk)."""
    g = _g()
    rack = build_rack(g)
    assert len(rack.solids()) == 1, f"rack must be one solid, got {len(rack.solids())}"
    bb = rack.bounding_box()
    span_x = bb.max.X - bb.min.X
    assert abs(span_x - g.rack_len) < 2.0, f"rack X-span {span_x:.1f} != rack_len {g.rack_len:.1f}"


def test_collision_hint_is_sourced_and_hull_typed():
    """The L3 wedge decomposition (collision_hint) returns source-stamped hull prims (D-M8-4 / D18):
    one prism per flank segment, z_pinion·2 flanks · n_wedge. Every prim owner=pinion + card source."""
    inst = type("I", (), {"params": {"module": 5.0, "z_pinion": 12}, "id": "E1"})()
    prims = collision_primitives(inst, n_wedge=4)
    assert len(prims) == 12 * 2 * 4, len(prims)                  # z · 2 flanks · n_wedge
    assert all(p["type"] == "hull" for p in prims)
    assert all(p["owner"] == "pinion" for p in prims)
    assert all(p["source"] == "card:rack_pinion@E1" for p in prims)


def test_module_bounds_are_the_stability_band():
    """§3.6 amended: the module bounds are the LARGE contact-sim-stability band {5,6} (D-M1-2/-4),
    and resolve_params snaps INTO it (never below) — a physics-of-verification constraint the card
    owns, stated in selection_notes."""
    card = CARD_REGISTRY["rack_pinion"]
    assert card.param_bounds["module"][:2] == (5.0, 6.0)
    assert "contact-sim" in card.selection_notes.lower() or "simulation" in card.selection_notes.lower()

    class _Ir:
        behaviors = []
    out = card.resolve_params(_Ir(), type("I", (), {"id": "E1", "params": {"module": 2.0}})())
    assert out["module"] == 5.0, f"module 2.0 must snap up to the 5.0 stability floor, got {out['module']}"


if __name__ == "__main__":
    fns = [test_section36_formulas_match_worked_arithmetic,
           test_rack_length_covers_stroke_plus_engagement_margin,
           test_pinion_is_one_involute_solid,
           test_rack_is_one_solid_and_spans_its_length,
           test_collision_hint_is_sourced_and_hull_typed,
           test_module_bounds_are_the_stability_band]
    for f in fns:
        f()
    print(f"{len(fns)}/{len(fns)} passed  — §3.6 formulas match the worked arithmetic (rp=30, "
          f"d=60, tpr=188.50, L=167.12), pinion+rack each one solid, L3 hint sourced, "
          f"module snaps into the {{5,6}} stability band")
