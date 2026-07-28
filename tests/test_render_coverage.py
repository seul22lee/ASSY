"""Renderer coverage audit - two-way traceability, enforced.

The picture must not assert engineering the contracts never stated, and must not
silently omit engineering they do. These tests hold both directions:

  * every glyph names the blueprint field it reads, and that field exists
  * every blueprint field is either drawn or excluded with a stated reason

They also assert the vocabulary is *complete*: a new relation kind or motion kind
added upstream must not render as a generic mark, because a generic mark makes two
different mechanical demands look identical.

    ./mujoco_core/bin/py -m unittest tests.test_render_coverage
"""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from assy.conceptcoverage import (
    FIELD_EXCLUSIONS,
    FIELD_GLYPHS,
    GLYPH_SOURCES,
    audit,
)
from assy.conceptrender import INTERFACE_MARK, STATUS_COLOR, render_concept
from assy.domain.common import reset_ids
from assy.domain.upstream import ConstraintStatus, MotionKind, SpatialRelationKind
from assy.stages import (
    ConceptVisualizer,
    MechanicalArchitectureGenerator,
    ProductArchitecturePlanner,
)
from tests.fixtures import load_spec

BENCHMARKS = ("BM-001", "BM-002")


def blueprint(bid: str) -> dict:
    reset_ids()
    spec = load_spec(bid)
    mech = MechanicalArchitectureGenerator().run(spec=spec)
    prod = ProductArchitecturePlanner().run(spec=spec, mechanical=mech)
    return ConceptVisualizer().run(product=prod, mechanical=mech).model_dump(mode="json")


class EveryGlyphTracesToAField(unittest.TestCase):
    def test_no_glyph_reads_a_field_the_blueprint_lacks(self):
        for bid in BENCHMARKS:
            report = audit(blueprint(bid))
            with self.subTest(benchmark=bid):
                self.assertEqual(
                    report["orphan_glyphs"], [],
                    "a glyph reads a field the blueprint does not carry",
                )

    def test_every_glyph_is_declared_against_a_field(self):
        report = audit(blueprint("BM-002"))
        self.assertEqual(
            report["undeclared_glyphs"], [],
            "a glyph exists that no field claims to produce",
        )

    def test_every_glyph_names_a_concrete_source(self):
        for name, source in GLYPH_SOURCES.items():
            with self.subTest(glyph=name):
                self.assertTrue(source, f"{name} names no source field")
                self.assertNotIn(" ", source, "a source must be a field path")


class EveryFieldIsDrawnOrExcluded(unittest.TestCase):
    def test_no_blueprint_field_is_unaccounted_for(self):
        for bid in BENCHMARKS:
            report = audit(blueprint(bid))
            with self.subTest(benchmark=bid):
                self.assertEqual(
                    report["unmapped_fields"], [],
                    "a blueprint field is neither drawn nor explicitly excluded",
                )

    def test_no_field_is_both_drawn_and_excluded(self):
        for bid in BENCHMARKS:
            with self.subTest(benchmark=bid):
                self.assertEqual(audit(blueprint(bid))["double_declared_fields"], [])

    def test_every_exclusion_states_a_reason(self):
        for field, reason in FIELD_EXCLUSIONS.items():
            with self.subTest(field=field):
                self.assertGreater(
                    len(reason), 40,
                    f"the exclusion of {field} is asserted rather than justified",
                )

    def test_the_coverage_report_ships_with_the_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            written = render_concept(blueprint("BM-002"), Path(tmp))
            names = {Path(p).name for p in written}
            self.assertIn("concept_layout.png", names)
            self.assertIn("render_coverage.json", names)
            report = json.loads((Path(tmp) / "render_coverage.json").read_text())
            self.assertEqual(report["unmapped_fields"], [])


class TheVisualVocabularyIsComplete(unittest.TestCase):
    """A new upstream kind must not silently degrade to a generic mark."""

    def test_every_relation_kind_has_its_own_mark(self):
        for relation in SpatialRelationKind:
            with self.subTest(relation=relation):
                self.assertIn(
                    relation.value, INTERFACE_MARK,
                    f"{relation.value} would render as a generic mark",
                )

    def test_relation_marks_are_distinguishable(self):
        marks = [m for m, _ in INTERFACE_MARK.values()]
        self.assertEqual(
            len(marks), len(set(marks)),
            "two relation kinds share a mark and would look identical",
        )

    def test_every_constraint_status_has_a_colour(self):
        for status in ConstraintStatus:
            with self.subTest(status=status):
                self.assertIn(status.value, STATUS_COLOR)

    def test_a_violated_relation_is_not_coloured_like_a_satisfied_one(self):
        self.assertNotEqual(
            STATUS_COLOR["violated"], STATUS_COLOR["satisfied"],
            "an unrealizable relation would be indistinguishable from a sound one",
        )
        self.assertNotEqual(
            STATUS_COLOR["not_checkable"], STATUS_COLOR["satisfied"],
            "an undecidable relation must not read as a pass",
        )

    def test_every_motion_kind_has_a_declared_glyph(self):
        declared = " ".join(FIELD_GLYPHS["placed_pieces"]) + " " + " ".join(
            FIELD_GLYPHS["swept_volumes"]
        )
        for motion in MotionKind:
            if motion is MotionKind.FIXED:
                continue  # a fixed element sweeps nothing; drawing one would invent motion
            token = {
                MotionKind.ROTATION: "arc",
                MotionKind.TRANSLATION: "linear",
                MotionKind.ROTATION_TRANSLATION: "helix",
                MotionKind.COMPLIANT_DEFORMATION: "deflection",
                MotionKind.UNSPECIFIED: "unspecified",
            }[motion]
            with self.subTest(motion=motion):
                self.assertIn(token, declared, f"{motion.value} has no glyph")


class RenderingStaysDeterministic(unittest.TestCase):
    def test_the_sheet_is_byte_identical_across_runs(self):
        for bid in BENCHMARKS:
            bp = blueprint(bid)
            digests = []
            for _ in range(2):
                with tempfile.TemporaryDirectory() as tmp:
                    paths = render_concept(bp, Path(tmp))
                    png = next(p for p in paths if p.endswith(".png"))
                    digests.append(hashlib.sha256(Path(png).read_bytes()).hexdigest())
            with self.subTest(benchmark=bid):
                self.assertEqual(digests[0], digests[1])

    def test_the_coverage_report_is_stable(self):
        bp = blueprint("BM-001")
        self.assertEqual(
            json.dumps(audit(bp), sort_keys=True), json.dumps(audit(bp), sort_keys=True)
        )

    def test_a_broken_blueprint_yields_no_image_and_no_exception(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(render_concept({"placed_pieces": [{"bad": 1}]}, Path(tmp)), [])


class SpatialExtentIsNeverReplacedByAGlyph(unittest.TestCase):
    """Every functional element answers both 'where is it' and 'what does it do'.

    A glyph augments a region; it never stands in for one. An element drawn only
    as a symbol has lost its spatial representation, and a reviewer can no longer
    ask whether it fits.
    """

    def blocks(self, bid):
        from assy.conceptrender import _derived_extents, _layout

        bp = blueprint(bid)
        bodies = _layout(bp)
        return bp, bodies, _derived_extents(bp, bodies)

    def test_every_joint_and_feature_has_a_drawn_extent(self):
        for bid in BENCHMARKS:
            bp, _, derived = self.blocks(bid)
            drawn = {b.name for b in derived}
            for p in bp["placed_pieces"]:
                if p.get("element_class") == "body" or not p.get("attached_to"):
                    continue
                with self.subTest(benchmark=bid, element=p["name"]):
                    self.assertIn(
                        p["name"], drawn,
                        f"{p['name']} collapsed into a symbol with no extent",
                    )

    def test_a_derived_extent_has_non_zero_size(self):
        for bid in BENCHMARKS:
            _, _, derived = self.blocks(bid)
            for b in derived:
                with self.subTest(benchmark=bid, region=b.name):
                    self.assertTrue(all(dim > 0 for dim in b.s), "an extent is degenerate")

    def test_a_joint_is_smaller_than_the_bodies_it_connects(self):
        """A joint is local: giving it body-scale bulk was the original error."""
        for bid in BENCHMARKS:
            bp, bodies, derived = self.blocks(bid)
            by_name = {b.name: b for b in bodies}
            for p in bp["placed_pieces"]:
                if p.get("element_class") != "joint":
                    continue
                region = next((b for b in derived if b.name == p["name"]), None)
                hosts = [by_name[n] for n in p.get("attached_to", []) if n in by_name]
                if region is None or not hosts:
                    continue
                with self.subTest(benchmark=bid, joint=p["name"]):
                    self.assertLess(
                        region.s[0] * region.s[1] * region.s[2],
                        max(h.s[0] * h.s[1] * h.s[2] for h in hosts),
                        "a joint is drawn as large as a member",
                    )

    def test_localized_relations_get_an_engagement_region(self):
        from assy.conceptrender import LOCALIZED_RELATIONS

        for bid in BENCHMARKS:
            bp, _, derived = self.blocks(bid)
            engagements = [b for b in derived if b.kind == "engagement_region"]
            expected = [
                c for c in bp["spatial_constraints"]
                if c["relation"] in LOCALIZED_RELATIONS
            ]
            with self.subTest(benchmark=bid):
                if expected:
                    self.assertTrue(
                        engagements, "a contact relation produced no engagement region"
                    )

    def test_contact_sits_between_surfaces_not_between_centres(self):
        """A contact placed at the centroid midpoint floats inside the enclosure."""
        from assy.conceptrender import _contact_centre, _surface_point

        class B:
            def __init__(self, c, s):
                self.c, self.s = c, s

        shell = B((0.0, 0.0, 1.0), (2.0, 2.0, 2.0))
        lid = B((0.0, 0.0, 2.0), (1.8, 1.8, 0.1))
        contact = _contact_centre(shell, lid)
        # The contact must lie on the shell's boundary, not deep inside it.
        self.assertGreater(contact[2], 1.5, "the contact sank into the enclosure")
        self.assertEqual(_surface_point(shell, lid.c)[2], 2.0)


if __name__ == "__main__":
    unittest.main()
