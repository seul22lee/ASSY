"""Hard-anchor host templates (m12 / D-track 3) — smoke + anchor-contract regressions.

m12 builds ONLY the four templates + their anchors; m13 is the assembly. These tests pin what m13
will rely on: every template instantiates to a valid solid, and every anchor the m13 bindings will
reference EXISTS now, at the matched positions the alignment rule and the rack/pinion mesh need.

  cabinet_shell : rail_mount_L/R + rail_axis_L/R (matched height = alignment subjects), knob_mount, floor
  drawer_tray   : carriage_mount_L/R + travel_axis_L/R (matched height), rack_mount (underside), front_pull
  knob_shaft    : mount_axis, shaft_seat (pinion seat), grip_face — ONE connected solid
  rack_bar      : mount_face (to drawer underside), rack_line

Run:  ./bin/py tests/test_hard_templates.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from knowledge.templates import TEMPLATES, TEMPLATE_COLLISION

REQUIRED = {
    "cabinet_shell": ["rail_mount_L", "rail_mount_R", "rail_axis_L", "rail_axis_R",
                      "knob_mount", "floor"],
    "drawer_tray": ["carriage_mount_L", "carriage_mount_R", "travel_axis_L", "travel_axis_R",
                    "rack_mount", "front_pull"],
    "knob_shaft": ["mount_axis", "shaft_seat", "grip_face"],
    "rack_bar": ["mount_face", "rack_line"],
}


def test_all_templates_instantiate_valid():
    """Every template builds a VALID (watertight) solid with positive volume."""
    for name in REQUIRED:
        tr = TEMPLATES[name]()
        assert tr.part.is_valid, f"{name} is not a valid solid"
        assert tr.part.volume > 0, f"{name} has non-positive volume"


def test_every_required_anchor_exists():
    """m13 binding failures must not be blamable on a missing anchor — assert them all NOW."""
    for name, anchors in REQUIRED.items():
        got = set(TEMPLATES[name]().anchors)
        missing = set(anchors) - got
        assert not missing, f"{name} is missing anchors {missing} (have {sorted(got)})"


def test_knob_shaft_is_one_connected_solid():
    """The shaft + grip must fuse into ONE solid — a disjoint grip is the two-yellow-bodies bug
    (D-D-1) one template earlier than the assembly."""
    n = len(TEMPLATES["knob_shaft"]().part.solids())
    assert n == 1, f"knob_shaft has {n} disjoint solids — shaft and grip must overlap into one"


def test_cabinet_rails_are_a_matched_level_pair():
    """The two rail axes are the alignment rule's subjects: SAME height (level), MIRRORED in X, and
    both run along +Y (parallel travel). If these disagree, the alignment rule can never pass."""
    a = TEMPLATES["cabinet_shell"]().anchors
    L, R = a["rail_axis_L"], a["rail_axis_R"]
    assert abs(L.position[2] - R.position[2]) < 1e-9, "rails must be LEVEL (equal z)"
    assert abs(L.position[0] + R.position[0]) < 1e-9, "rails must be mirrored in X"
    assert L.normal == (0, 1, 0) and R.normal == (0, 1, 0), "both rails travel along +Y (parallel)"


def test_drawer_carriage_pair_matches_cabinet_rail_height():
    """The drawer's carriage anchors are a matched L/R pair and its travel axes run along +Y, so
    they can pair with the cabinet rails under the alignment rule."""
    a = TEMPLATES["drawer_tray"]().anchors
    L, R = a["travel_axis_L"], a["travel_axis_R"]
    assert abs(L.position[2] - R.position[2]) < 1e-9, "carriage anchors must be level"
    assert abs(L.position[0] + R.position[0]) < 1e-9, "carriage anchors must be mirrored in X"
    assert L.normal == (0, 1, 0) and R.normal == (0, 1, 0)


def test_rack_mount_is_underside_and_front_pull_is_front():
    """rack_mount faces DOWN (−Z, the rack bar bolts under the drawer); front_pull faces +Y (front)."""
    a = TEMPLATES["drawer_tray"]().anchors
    assert a["rack_mount"].normal == (0, 0, -1), "rack_mount must face the underside (−Z)"
    assert a["front_pull"].normal == (0, 1, 0), "front_pull must face the front (+Y)"


def test_collision_hints_present_and_sourced():
    """Every template declares seating/support collision prims, each source-stamped to itself
    (D-M8-4): the m8 lesson — declare every intended contact, and let nothing be unsourced."""
    for name in REQUIRED:
        prims = TEMPLATE_COLLISION[name]()
        assert prims, f"{name} declares no collision prims"
        for pr in prims:
            assert pr.get("source") == f"template:{name}", f"{name} prim not self-sourced: {pr.get('source')}"


if __name__ == "__main__":
    fns = [test_all_templates_instantiate_valid, test_every_required_anchor_exists,
           test_knob_shaft_is_one_connected_solid, test_cabinet_rails_are_a_matched_level_pair,
           test_drawer_carriage_pair_matches_cabinet_rail_height,
           test_rack_mount_is_underside_and_front_pull_is_front,
           test_collision_hints_present_and_sourced]
    for f in fns:
        f()
    print(f"{len(fns)}/{len(fns)} passed  — 4 Hard-anchor templates valid; every m13 anchor exists; "
          f"knob is one solid; rails + carriage are matched level pairs (alignment subjects); "
          f"collision hints sourced")
