"""Stage 03 -> Stage 04 contract tests.

Stage 04 arranges one product organisation in space and reports where it
contradicts itself. It is a strict consumer of Stage 03.

    ./mujoco_core/bin/py -m unittest tests.test_stage04_contract
"""

from __future__ import annotations

import unittest
from pathlib import Path

from assy.domain.common import reset_ids
from assy.domain.upstream import (
    MotionKind,
    ObligationKind,
    RegionKind,
    SpatialIssueKind,
    SpatialZone,
    SweptShape,
)
from assy.stages import (
    ConceptVisualizer,
    MechanicalArchitectureGenerator,
    ProductArchitecturePlanner,
)
from tests.fixtures import load_spec

BENCHMARKS = ("BM-001", "BM-002")


def stage04(spec):
    reset_ids()
    mech = MechanicalArchitectureGenerator().run(spec=spec)
    prod = ProductArchitecturePlanner().run(spec=spec, mechanical=mech)
    return mech, prod, ConceptVisualizer().run(product=prod, mechanical=mech)


def fingerprint(c) -> dict:
    return {
        "frame": (c.reference_frame.primary_axis.value,
                  c.reference_frame.primary_motion.value,
                  c.reference_frame.primary_element),
        "faces": sorted((f.face.value, tuple(r.value for r in f.roles), tuple(f.hosts))
                        for f in c.boundary_faces),
        "stations": sorted((p.name, p.axis_station.value if p.axis_station else None)
                           for p in c.placed_pieces),
        "constraints": sorted((tuple(x.between), x.relation.value, x.status.value)
                              for x in c.spatial_constraints),
        "placements": sorted((p.region, p.zone.value, p.relative_to) for p in c.region_placements),
        "swept": sorted((s.element, s.motion.value, s.shape.value, s.external)
                        for s in c.swept_volumes),
        "interference": sorted((list(i.between)[0], list(i.between)[1], i.addressed_by)
                               for i in c.interference_candidates),
        "access": sorted((a.region, a.purpose.value, tuple(sorted(a.obstructed_by)))
                         for a in c.access_routes),
        "issues": sorted((i.kind.value, i.concern) for i in c.issues),
        "views": sorted(v.name for v in c.views),
        "annotations": sorted((a.subject, a.note) for a in c.annotations),
    }


class Stage04IsNonAuthoritative(unittest.TestCase):
    def test_output_is_never_authoritative(self):
        for bid in BENCHMARKS:
            with self.subTest(benchmark=bid):
                _, _, c = stage04(load_spec(bid))
                self.assertFalse(c.authoritative, "a spatial hypothesis is not proof")

    def test_no_dimensions_or_coordinates_are_emitted(self):
        for bid in BENCHMARKS:
            _, _, c = stage04(load_spec(bid))
            text = " ".join(
                [p.why for p in c.region_placements]
                + [i.concern for i in c.issues]
                + [i.evidence for i in c.issues]
                + [v.purpose for v in c.views]
                + [a.note for a in c.annotations]
                + [c.reference_frame.derived_from, c.described_layout]
            )
            with self.subTest(benchmark=bid):
                self.assertNotRegex(text, r"\d+\s*(mm|kg|deg|N|°)", "a dimension leaked")
                self.assertNotRegex(text, r"\(\s*-?\d+\s*,\s*-?\d+", "a coordinate leaked")


class Stage04IgnoresNaturalLanguage(unittest.TestCase):
    def _invariant_under(self, bid, mutate):
        _, _, baseline = stage04(load_spec(bid))
        spec = load_spec(bid)
        mutate(spec)
        _, _, mutated = stage04(spec)
        self.assertEqual(fingerprint(mutated), fingerprint(baseline), bid)

    def test_source_text_is_ignored(self):
        for bid in BENCHMARKS:
            with self.subTest(benchmark=bid):
                self._invariant_under(bid, lambda s: setattr(s, "source_text", ""))

    def test_misleading_source_text_is_ignored(self):
        decoy = "Design a flat open tray with no moving parts and no housing. " * 8
        for bid in BENCHMARKS:
            with self.subTest(benchmark=bid):
                self._invariant_under(bid, lambda s: setattr(s, "source_text", decoy))

    def test_requirement_prose_and_identity_are_ignored(self):
        def scramble(spec):
            for i, r in enumerate(spec.requirements):
                r.statement = f"opaque requirement {i}"
            spec.product_intent = "a flat open tray"
            spec.meta.design_id = "BM-999_FLAT_TRAY"
        for bid in BENCHMARKS:
            with self.subTest(benchmark=bid):
                self._invariant_under(bid, scramble)

    def test_no_prose_parsing_in_the_stage_04_source(self):
        code = Path("assy/stages/s04_concept.py").read_text().split('"""', 2)[-1]
        for banned in ("source_text", "r.statement", "spec.", "re.search"):
            self.assertNotIn(banned, code, f"Stage 04 must not use {banned}")


class Stage04ConsumesStage03(unittest.TestCase):
    def test_output_traces_to_its_product_and_candidate(self):
        for bid in BENCHMARKS:
            with self.subTest(benchmark=bid):
                _, prod, c = stage04(load_spec(bid))
                self.assertEqual(c.source_product_id, prod.meta.object_id)
                self.assertEqual(c.source_candidate_id, prod.source_candidate_id)

    def test_every_region_is_placed_exactly_once(self):
        for bid in BENCHMARKS:
            _, prod, c = stage04(load_spec(bid))
            with self.subTest(benchmark=bid):
                self.assertEqual(
                    sorted(p.region for p in c.region_placements),
                    sorted(r.name for r in prod.regions),
                )

    def test_placements_and_issues_name_only_declared_regions(self):
        for bid in BENCHMARKS:
            _, prod, c = stage04(load_spec(bid))
            names = {r.name for r in prod.regions}
            for i in c.issues:
                for r in i.regions:
                    with self.subTest(benchmark=bid, issue=i.id):
                        self.assertIn(r, names | {p.name for p in prod.pieces})

    def test_a_different_product_produces_a_different_blueprint(self):
        spec = load_spec("BM-001")
        mech = MechanicalArchitectureGenerator().run(spec=spec)
        prod = ProductArchitecturePlanner().run(spec=spec, mechanical=mech)
        first = ConceptVisualizer().run(product=prod, mechanical=mech)
        mech.selected_id = next(c.id for c in mech.candidates if c.id != mech.selected_id)
        other = ProductArchitecturePlanner().run(spec=spec, mechanical=mech)
        second = ConceptVisualizer().run(product=other, mechanical=mech)
        self.assertNotEqual(fingerprint(first), fingerprint(second))

    def test_upstream_advisories_pass_through_untouched(self):
        spec = load_spec("BM-002")
        mech = MechanicalArchitectureGenerator().run(spec=spec)
        mech.selected.support_obligations[0].reacted_by = None
        prod = ProductArchitecturePlanner().run(spec=spec, mechanical=mech)
        c = ConceptVisualizer().run(product=prod, mechanical=mech)
        self.assertEqual(c.product_advisories, prod.architecture_advisories)
        self.assertTrue(c.product_advisories, "a Stage 03 gap must not be swallowed")


class SpatialBlueprintIsUsable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = {bid: stage04(load_spec(bid)) for bid in BENCHMARKS}

    def concept(self, bid):
        return self.out[bid][2]

    def test_a_reference_frame_is_established(self):
        for bid in BENCHMARKS:
            f = self.concept(bid).reference_frame
            with self.subTest(benchmark=bid):
                self.assertIsNotNone(f)
                self.assertIsNot(f.primary_motion, MotionKind.UNSPECIFIED)
                self.assertIsNotNone(f.primary_element)
                self.assertTrue(f.derived_from)

    def test_every_moving_element_has_a_classified_swept_volume(self):
        for bid in BENCHMARKS:
            _, prod, c = self.out[bid]
            classified = {s.element: s for s in c.swept_volumes}
            for piece in prod.pieces:
                if piece.moving:
                    with self.subTest(benchmark=bid, element=piece.name):
                        self.assertIn(piece.name, classified)
                        sv = classified[piece.name]
                        self.assertIsNot(sv.motion, MotionKind.UNSPECIFIED)
                        self.assertIsNot(sv.shape, SweptShape.UNKNOWN)

    def test_rotation_and_translation_sweep_different_shapes(self):
        """The distinction that motivated carrying motion kind downstream."""
        c = self.concept("BM-002")
        shapes = {s.element: s.shape for s in c.swept_volumes}
        self.assertEqual(shapes["input_member"], SweptShape.CYLINDRICAL)
        self.assertEqual(shapes["travelling_member"], SweptShape.PRISMATIC)

    def test_interference_candidates_are_produced_and_triaged(self):
        for bid in BENCHMARKS:
            c = self.concept(bid)
            with self.subTest(benchmark=bid):
                self.assertTrue(c.interference_candidates)
                self.assertTrue(
                    any(i.addressed_by for i in c.interference_candidates),
                    "a designed contact must be marked addressed, not reported raw",
                )

    def test_a_designed_interface_is_not_reported_as_a_conflict(self):
        """The threaded pair is meant to engage; it is not an interference issue."""
        c = self.concept("BM-002")
        unaddressed = {
            tuple(i.between) for i in c.interference_candidates if not i.addressed_by
        }
        self.assertNotIn(
            tuple(sorted(("threaded_member_swept_volume", "travelling_member_swept_volume"))),
            unaddressed,
        )

    def test_access_routes_cover_every_externally_reachable_region(self):
        for bid in BENCHMARKS:
            _, prod, c = self.out[bid]
            need = {
                r.name for r in prod.regions
                if r.kind in (RegionKind.USER_ACCESS, RegionKind.SERVICE_ACCESS,
                              RegionKind.PAYLOAD)
            }
            with self.subTest(benchmark=bid):
                self.assertTrue(need <= {a.region for a in c.access_routes})

    def test_every_issue_is_traceable_and_typed(self):
        for bid in BENCHMARKS:
            c = self.concept(bid)
            for i in c.issues:
                with self.subTest(benchmark=bid, issue=i.id):
                    self.assertIsInstance(i.kind, SpatialIssueKind)
                    self.assertTrue(i.regions, "an issue with no region is unactionable")
                    self.assertTrue(i.evidence)

    def test_views_and_annotations_are_produced(self):
        for bid in BENCHMARKS:
            c = self.concept(bid)
            with self.subTest(benchmark=bid):
                names = {v.name for v in c.views}
                self.assertIn("exterior", names)
                self.assertIn("cutaway_along_primary_axis", names)
                self.assertIn("exploded_assembly", names)
                self.assertTrue(any(v.name.startswith("envelope_") for v in c.views))
                self.assertTrue(c.annotations)

    def test_zones_are_not_all_identical(self):
        """A blueprint that puts everything in one zone has organised nothing."""
        for bid in BENCHMARKS:
            zones = {p.zone for p in self.concept(bid).region_placements}
            with self.subTest(benchmark=bid):
                self.assertGreaterEqual(len(zones), 3)


class BM001SpatialBlueprint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mech, cls.prod, cls.c = stage04(load_spec("BM-001"))

    def test_the_frame_follows_the_closure(self):
        f = self.c.reference_frame
        self.assertIs(f.primary_motion, MotionKind.ROTATION)
        self.assertEqual(f.primary_element, "closure_member")

    def test_the_closure_sweeps_an_arc(self):
        swept = {s.element: s for s in self.c.swept_volumes}
        self.assertIs(swept["closure_member"].shape, SweptShape.CYLINDRICAL)

    def test_retention_sits_on_the_boundary_and_release_is_reachable(self):
        """Reachable means external *or* on the boundary.

        A closure a user presses is part of the enclosure surface, not a body
        floating outside it; demanding EXTERNAL encoded the pre-synthesis model
        where the lid was placed beside the box rather than forming its wall.
        """
        zones = {p.region: p.zone for p in self.c.region_placements}
        self.assertIs(zones["retention_region"], SpatialZone.BOUNDARY)
        access = [z for r, z in zones.items() if "access" in r]
        self.assertTrue(access, "no access region was derived")
        self.assertTrue(
            set(access) & {SpatialZone.EXTERNAL, SpatialZone.BOUNDARY},
            "the release surface is not reachable from outside",
        )

    def test_no_service_access_route_is_invented(self):
        """The closure already opens the product."""
        self.assertNotIn(
            "service", {a.purpose.value for a in self.c.access_routes}
        )


class BM002SpatialBlueprint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mech, cls.prod, cls.c = stage04(load_spec("BM-002"))

    def test_translation_defines_the_frame_over_rotation(self):
        f = self.c.reference_frame
        self.assertIs(f.primary_motion, MotionKind.TRANSLATION)
        self.assertEqual(f.primary_element, "travelling_member")

    def test_guides_flank_and_supports_sit_at_the_ends(self):
        zones = {p.region: p.zone for p in self.c.region_placements}
        self.assertIs(zones["guidance_region"], SpatialZone.FLANKING)
        self.assertIs(zones["support_region"], SpatialZone.END)

    def test_the_crank_sweeps_outside_the_enclosure(self):
        crank = next(s for s in self.c.swept_volumes if s.element == "input_member")
        self.assertTrue(crank.external)
        self.assertIs(crank.shape, SweptShape.CYLINDRICAL)

    def test_the_crank_sweep_is_flagged_against_service_access(self):
        """The golden calls this out: the cover must not be blocked by the crank."""
        blocked = [i for i in self.c.issues if i.kind is SpatialIssueKind.ACCESS_BLOCKED]
        self.assertTrue(blocked)
        self.assertTrue(
            any("service_access_region" in i.regions for i in blocked),
            "service access blocked by the crank sweep was not detected",
        )

    def test_a_rotating_body_with_no_permitting_joint_is_reported(self):
        """A real Stage 02 gap: transmission_shaft has no joint permitting rotation."""
        spans = [i for i in self.c.issues if i.kind is SpatialIssueKind.UNGROUNDED_MOTION]
        self.assertTrue(spans)
        self.assertTrue(any("transmission_shaft" in i.concern for i in spans))

    def test_payload_and_travel_regions_are_placed(self):
        zones = {p.region: p.zone for p in self.c.region_placements}
        self.assertIn("payload_region", zones)
        self.assertIs(zones["travel_limit_region"], SpatialZone.END)


class ConceptRenderIsDeterministicAndDerived(unittest.TestCase):
    """The layout image is a review artifact: reproducible, and never an authority."""

    def _blueprint(self, bid):
        return stage04(load_spec(bid))[2].model_dump(mode="json")

    def test_the_blueprint_is_self_contained_for_rendering(self):
        """A renderer must not have to re-join with Stage 03 to know what to draw."""
        for bid in BENCHMARKS:
            bp = self._blueprint(bid)
            with self.subTest(benchmark=bid):
                self.assertTrue(bp["placed_pieces"], "no pieces to draw")
                for piece in bp["placed_pieces"]:
                    self.assertIsNotNone(piece["zone"], f"{piece['name']} has no zone")
                for rp in bp["region_placements"]:
                    self.assertIn("houses", rp)

    def test_rendering_is_byte_identical_across_runs(self):
        import hashlib
        import tempfile

        from assy.conceptrender import render_concept

        for bid in BENCHMARKS:
            bp = self._blueprint(bid)
            digests = []
            for _ in range(2):
                with tempfile.TemporaryDirectory() as tmp:
                    paths = render_concept(bp, Path(tmp))
                    self.assertTrue(paths, "no image was produced")
                    digests.append(hashlib.sha256(Path(paths[0]).read_bytes()).hexdigest())
            with self.subTest(benchmark=bid):
                self.assertEqual(digests[0], digests[1], "render is not deterministic")

    def test_a_render_failure_never_fails_the_stage(self):
        import tempfile

        from assy.conceptrender import render_concept

        with tempfile.TemporaryDirectory() as tmp:
            # A structurally invalid blueprint must yield no image, not an exception.
            self.assertEqual(render_concept({"placed_pieces": [{"bad": 1}]}, Path(tmp)), [])

    def test_a_moving_boundary_element_is_placed_on_the_boundary(self):
        """A lid is the box's own wall, not something buried in the storage volume."""
        bp = self._blueprint("BM-001")
        closure = next(p for p in bp["placed_pieces"] if p["name"] == "closure_member")
        self.assertEqual(closure["zone"], "boundary")
        # ...and the volume it closes stays interior.
        working = next(
            r for r in bp["region_placements"] if r["region"] == "working_volume"
        )
        self.assertEqual(working["zone"], "core")

    def test_the_shell_is_never_relocated_by_an_obligation_it_reacts(self):
        for bid in BENCHMARKS:
            bp = self._blueprint(bid)
            shell = next(p for p in bp["placed_pieces"] if p["kind"] == "shell")
            with self.subTest(benchmark=bid):
                self.assertEqual(shell["zone"], "boundary")


if __name__ == "__main__":
    unittest.main()
