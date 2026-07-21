"""shaft_carrier_in + shaft_carrier_out fixture templates (m20 Stage 2) — the minimal 2-piece
coupling host (two coaxial vertical shafts, a rigid hub bridging them).

DESIGN CHOICE (stated per the brief): TWO distinct templates, not one instantiated twice — because
the two sides are structurally different, exactly like the lead_screw fixture (screw_base is the
is_base carrier; nut_carriage is the floating mover). shaft_carrier_in is the base (plate + input
shaft stub the hub FUSES onto); shaft_carrier_out is the floating output shaft (the MOVER) that
inserts into the hub's blind bore with print clearance.

Run:  ./bin/py tests/test_coupling_templates.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from knowledge.templates.host_templates import TEMPLATES


def test_both_templates_registered():
    for t in ("shaft_carrier_in", "shaft_carrier_out"):
        assert t in TEMPLATES, f"{t} not registered in TEMPLATES (BUILDABLE derives from it)"


def test_shaft_carrier_in_is_one_solid_with_shaft_in_anchor():
    tr = TEMPLATES["shaft_carrier_in"](shaft_d=8.0, shaft_h=30.0)
    assert len(tr.part.solids()) == 1 and tr.part.volume > 0, "base ∪ stub must be one solid"
    assert "shaft_in" in tr.anchors and tr.anchors["shaft_in"].kind == "axis"
    a = tr.anchors["shaft_in"]
    assert a.normal == (0, 0, 1) and a.position == (0.0, 0.0, 30.0)   # +Z axis at the stub top


def test_shaft_carrier_out_is_one_solid_and_undersized_for_clearance():
    tr = TEMPLATES["shaft_carrier_out"](shaft_d=8.0, z0=40.0)
    assert len(tr.part.solids()) == 1 and tr.part.volume > 0
    assert "shaft_out" in tr.anchors and tr.anchors["shaft_out"].normal == (0, 0, -1)
    # the output stub is undersized by the print clearance so it slides into the bore_d bore
    sz = tr.part.bounding_box().size
    assert sz.X < 8.0 and sz.Y < 8.0, "output stub must be undersized (clearance fit)"


def test_anchors_are_coaxial_on_the_world_z_axis():
    sin = TEMPLATES["shaft_carrier_in"]()
    sout = TEMPLATES["shaft_carrier_out"]()
    assert sin.anchors["shaft_in"].position[:2] == (0.0, 0.0)
    assert sout.anchors["shaft_out"].position[:2] == (0.0, 0.0)   # coaxial ⇒ a valid coupling pair


if __name__ == "__main__":
    fns = [test_both_templates_registered, test_shaft_carrier_in_is_one_solid_with_shaft_in_anchor,
           test_shaft_carrier_out_is_one_solid_and_undersized_for_clearance,
           test_anchors_are_coaxial_on_the_world_z_axis]
    for f in fns:
        f()
    print(f"{len(fns)}/{len(fns)} passed  — shaft_carrier_in + shaft_carrier_out: registered, one solid "
          f"each (base+stub / floating undersized mover), coaxial shaft_in(+Z)/shaft_out(−Z) anchors")
