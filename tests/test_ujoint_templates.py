"""universal_joint fixture templates (m21 Stage 2) — the input carrier (reused m20 shaft_carrier_in,
now also emitting a cross_pivot anchor) + the ANGLED output carrier (new geometry: the bend β is the
whole point). DESIGN CHOICE (stated): reuse the straight input carrier; add shaft_carrier_out_angled
for the intersecting output axis.

Run:  ./bin/py tests/test_ujoint_templates.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from knowledge.templates.host_templates import TEMPLATES


def test_input_carrier_reused_now_emits_cross_pivot():
    tr = TEMPLATES["shaft_carrier_in"](shaft_d=8.0, shaft_h=30.0)
    assert len(tr.part.solids()) == 1
    assert "shaft_in" in tr.anchors and "cross_pivot" in tr.anchors
    # both at the joint centre (stub top), shaft axis +Z
    assert tr.anchors["shaft_in"].position == (0.0, 0.0, 30.0)
    assert tr.anchors["cross_pivot"].position == (0.0, 0.0, 30.0)


def test_angled_output_declares_the_intersecting_axis_at_beta():
    tr = TEMPLATES["shaft_carrier_out_angled"](shaft_d=8.0, beta_deg=20.0, joint_z=30.0)
    assert len(tr.part.solids()) == 1 and tr.part.volume > 0
    a = tr.anchors["shaft_out"]
    b = math.radians(20.0)
    # the anchor normal IS the output axis B=(sinβ,0,cosβ) — intersecting the input +Z at the joint centre
    assert abs(a.normal[0] - math.sin(b)) < 1e-4 and abs(a.normal[2] - math.cos(b)) < 1e-4
    assert a.position == (0.0, 0.0, 30.0)
    # the tilt shows as an X-extent in the bbox (a straight +Z shaft would have X≈diameter only)
    sz = tr.part.bounding_box().size
    assert sz.X > 8.0, "the β tilt must lean the shaft into +X"


def test_output_undersized_for_clearance():
    tr = TEMPLATES["shaft_carrier_out_angled"](shaft_d=8.0, beta_deg=0.0)
    # at β=0 the shaft is straight +Z; its diameter is undersized by the print clearance
    sz = tr.part.bounding_box().size
    assert sz.X < 8.0 and sz.Y < 8.0
    assert tr.anchors["shaft_out"].normal == (0.0, 0.0, 1.0)   # β=0 → straight (the discrimination case)


if __name__ == "__main__":
    fns = [test_input_carrier_reused_now_emits_cross_pivot,
           test_angled_output_declares_the_intersecting_axis_at_beta,
           test_output_undersized_for_clearance]
    for f in fns:
        f()
    print(f"{len(fns)}/{len(fns)} passed  — ujoint templates: input carrier reused (+cross_pivot anchor), "
          f"angled output declares the intersecting axis normal=B(β) at the joint centre, one solid each, "
          f"β=0 → straight")
