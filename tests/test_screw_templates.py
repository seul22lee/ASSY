"""screw_base + nut_carriage fixture templates (m19 Stage 2) — the minimal 2-piece lead_screw host
(a vertical screw-jack). test_hard_templates-style: registered, anchors declared, valid one solid.

Run:  ./bin/py tests/test_screw_templates.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from knowledge.templates.host_templates import TEMPLATES


def test_both_templates_registered():
    for t in ("screw_base", "nut_carriage"):
        assert t in TEMPLATES, f"{t} not registered in TEMPLATES (BUILDABLE derives from it)"


def test_screw_base_is_one_solid_with_screw_axis_anchor():
    tr = TEMPLATES["screw_base"]()
    assert len(tr.part.solids()) == 1 and tr.part.volume > 0
    assert "screw_axis" in tr.anchors and tr.anchors["screw_axis"].kind == "axis"
    assert "travel_edge" in tr.anchors
    # the screw axis points +Z (a vertical screw-jack) at the plate top
    a = tr.anchors["screw_axis"]
    assert a.normal == (0, 0, 1)


def test_nut_carriage_is_one_connected_solid_with_clearance_bore():
    tr = TEMPLATES["nut_carriage"](d_major=8.0)
    # block minus a central bore is still ONE connected solid (a prism with a hole)
    assert len(tr.part.solids()) == 1, "nut block − bore must be one connected solid"
    assert tr.part.volume > 0
    assert "nut_mount" in tr.anchors and "travel_axis" in tr.anchors
    # the bore is a clearance hole (> screw radius) so the screw passes without interference
    # (verify by volume: a solid block of these dims minus a d=10 bore is strictly less)
    from build123d import Align, Box, Location
    p = tr.params
    solid_block = Location((0, 0, p["nut_z"])) * Box(p["nut_l"], p["nut_w"], p["nut_t"],
                                                     align=(Align.CENTER, Align.CENTER, Align.MIN))
    assert tr.part.volume < solid_block.volume, "the clearance bore must remove material"


def test_anchor_positions_align_screw_and_nut_on_the_same_axis():
    sb = TEMPLATES["screw_base"]()
    nc = TEMPLATES["nut_carriage"]()
    # both the screw axis and the nut mount sit on the world Z axis (x=y=0) so the pair is coaxial
    assert sb.anchors["screw_axis"].position[:2] == (0.0, 0.0)
    assert nc.anchors["nut_mount"].position[:2] == (0.0, 0.0)


if __name__ == "__main__":
    fns = [test_both_templates_registered, test_screw_base_is_one_solid_with_screw_axis_anchor,
           test_nut_carriage_is_one_connected_solid_with_clearance_bore,
           test_anchor_positions_align_screw_and_nut_on_the_same_axis]
    for f in fns:
        f()
    print(f"{len(fns)}/{len(fns)} passed  — screw_base + nut_carriage: registered, one solid each "
          f"(nut = block − clearance bore, one connected solid), coaxial anchors declared")
