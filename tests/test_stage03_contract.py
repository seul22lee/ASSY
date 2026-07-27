"""Stage 02 -> Stage 03 contract tests.

Stage 03 organises one selected mechanical architecture into a product. It is a
strict consumer: it reads the selected candidate's typed content and nothing else.

These assert the consumer property directly — no pipeline side effects, no model
call, committed fixtures only.

    ./mujoco_core/bin/py -m unittest tests.test_stage03_contract
"""

from __future__ import annotations

import unittest
from pathlib import Path

from assy.domain.common import reset_ids
from assy.domain.upstream import (
    MechanismRole,
    ObligationKind,
    PieceKind,
    RegionKind,
)
from assy.stages import MechanicalArchitectureGenerator, ProductArchitecturePlanner
from tests.fixtures import load_spec

BENCHMARKS = ("BM-001", "BM-002")


def stage03(spec):
    reset_ids()
    mech = MechanicalArchitectureGenerator().run(spec=spec)
    return mech, ProductArchitecturePlanner().run(spec=spec, mechanical=mech)


def fingerprint(prod) -> dict:
    """Everything Stage 03 organised, comparably. Ids excluded - minted per run."""
    return {
        "candidate": prod.source_candidate_id,
        "pieces": [(p.name, p.kind.value, p.moving, p.external) for p in prod.pieces],
        "regions": [(r.name, r.kind.value, r.external, r.moving, sorted(r.houses))
                    for r in prod.regions],
        "ownership": [(o.element, o.obligation.value, o.owner_piece, o.region)
                      for o in prod.obligation_ownership],
        "interfaces": [(list(i.between), i.kind.value, i.crosses_boundary)
                       for i in prod.interfaces],
        "placements": [(p.subject, p.relation.value, p.reference) for p in prod.placements],
        "assembly": [(s.order, s.action) for s in prod.assembly_sequence],
        "load_paths": [(lp.name, lp.path, lp.owning_regions) for lp in prod.load_path_ownership],
        "unresolved": sorted(prod.unresolved_decisions),
        "serves": sorted(prod.serves_requirements),
        "advisories": sorted(prod.architecture_advisories),
        "strategies": [prod.housing_strategy, prod.service_strategy,
                       prod.protection_strategy, prod.assembly_strategy],
    }


class Stage03IgnoresNaturalLanguage(unittest.TestCase):
    """Prose may change freely; the product organisation may not move."""

    def _invariant_under(self, bid, mutate):
        _, baseline = stage03(load_spec(bid))
        spec = load_spec(bid)
        mutate(spec)
        _, mutated = stage03(spec)
        self.assertEqual(fingerprint(mutated), fingerprint(baseline), bid)

    def test_source_text_is_ignored(self):
        for bid in BENCHMARKS:
            with self.subTest(benchmark=bid):
                self._invariant_under(bid, lambda s: setattr(s, "source_text", ""))

    def test_misleading_source_text_is_ignored(self):
        decoy = "Design an open-frame belt conveyor with no housing and no cover. " * 8
        for bid in BENCHMARKS:
            with self.subTest(benchmark=bid):
                self._invariant_under(bid, lambda s: setattr(s, "source_text", decoy))

    def test_requirement_prose_is_ignored(self):
        """The old Stage 03 keyed housing and service on 'enclos' and 'service'."""
        def scramble(spec):
            for i, r in enumerate(spec.requirements):
                r.statement = f"opaque requirement {i}"
        for bid in BENCHMARKS:
            with self.subTest(benchmark=bid):
                self._invariant_under(bid, scramble)

    def test_removing_the_word_enclosure_does_not_open_the_product(self):
        spec = load_spec("BM-002")
        for r in spec.requirements:
            r.statement = r.statement.replace("enclos", "XXXX").replace("service", "XXXX")
        _, prod = stage03(spec)
        self.assertTrue(
            any(p.kind is PieceKind.COVER for p in prod.pieces),
            "enclosure must follow from the architecture, not from a word",
        )

    def test_product_intent_and_identity_are_ignored(self):
        def relabel(spec):
            spec.product_intent = "an open-frame conveyor"
            spec.user_intent_summary = "the user wants a conveyor"
            spec.meta.design_id = "BM-999_OPEN_FRAME_CONVEYOR"
        for bid in BENCHMARKS:
            with self.subTest(benchmark=bid):
                self._invariant_under(bid, relabel)

    def test_no_prose_parsing_in_the_stage_03_source(self):
        """Structural guard against the old keyword branches returning."""
        source = Path("assy/stages/s03_product.py").read_text()
        code = source.split('"""', 2)[-1]
        for banned in ("source_text", "r.statement", ".statement.lower()", "re.search"):
            self.assertNotIn(banned, code, f"Stage 03 must not use {banned}")


class Stage03ConsumesOnlyTheSelectedCandidate(unittest.TestCase):
    def test_output_names_the_candidate_it_organised(self):
        for bid in BENCHMARKS:
            with self.subTest(benchmark=bid):
                mech, prod = stage03(load_spec(bid))
                self.assertEqual(prod.source_candidate_id, mech.selected_id)
                self.assertEqual(prod.source_architecture_id, mech.meta.object_id)

    def test_every_piece_traces_to_a_selected_element(self):
        for bid in BENCHMARKS:
            mech, prod = stage03(load_spec(bid))
            elements = {p.name for p in mech.selected.parts}
            for piece in prod.pieces:
                with self.subTest(benchmark=bid, piece=piece.name):
                    if piece.kind is PieceKind.COVER:
                        continue  # product-level, owned by Stage 03 and declared as such
                    self.assertTrue(set(piece.realises_elements) <= elements)

    def test_no_element_of_a_rejected_candidate_appears(self):
        """The decisive check that Stage 03 did not re-open the selection."""
        for bid in BENCHMARKS:
            mech, prod = stage03(load_spec(bid))
            chosen = {p.name for p in mech.selected.parts}
            rejected = {
                p.name
                for c in mech.candidates if c.id != mech.selected_id
                for p in c.parts
            } - chosen
            appearing = {
                n for piece in prod.pieces for n in piece.realises_elements
            } | {n for r in prod.regions for n in r.houses}
            with self.subTest(benchmark=bid):
                self.assertFalse(
                    appearing & rejected,
                    f"{appearing & rejected} came from a rejected candidate",
                )

    def test_a_different_selection_produces_a_different_product(self):
        """Proves the output actually depends on the selected candidate."""
        spec = load_spec("BM-001")
        mech = MechanicalArchitectureGenerator().run(spec=spec)
        alternative = next(c for c in mech.candidates if c.id != mech.selected_id)
        first = ProductArchitecturePlanner().run(spec=spec, mechanical=mech)
        mech.selected_id = alternative.id
        second = ProductArchitecturePlanner().run(spec=spec, mechanical=mech)
        self.assertNotEqual(fingerprint(first), fingerprint(second))


class Stage03OrganisesWithoutInventing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = {bid: stage03(load_spec(bid)) for bid in BENCHMARKS}

    def prod(self, bid):
        return self.out[bid][1]

    def test_every_obligation_is_owned_or_explicitly_unowned(self):
        for bid in BENCHMARKS:
            mech, prod = self.out[bid]
            self.assertEqual(
                len(prod.obligation_ownership), len(mech.selected.support_obligations),
                "an obligation was silently dropped",
            )
            for o in prod.obligation_ownership:
                with self.subTest(benchmark=bid, obligation=f"{o.element}/{o.obligation.value}"):
                    self.assertTrue(
                        o.owner_piece is not None or o.unowned_reason,
                        "an unowned obligation must say why",
                    )

    def test_every_owner_is_a_declared_piece(self):
        for bid in BENCHMARKS:
            prod = self.prod(bid)
            names = {p.name for p in prod.pieces}
            for o in prod.obligation_ownership:
                if o.owner_piece is not None:
                    with self.subTest(benchmark=bid, owner=o.owner_piece):
                        self.assertIn(o.owner_piece, names)

    def test_every_moving_element_gets_a_swept_region(self):
        for bid in BENCHMARKS:
            mech, prod = self.out[bid]
            swept = {
                n for r in prod.regions if r.kind is RegionKind.SWEPT_VOLUME for n in r.houses
            }
            for part in mech.selected.parts:
                if part.moving:
                    with self.subTest(benchmark=bid, element=part.name):
                        self.assertIn(part.name, swept)

    def test_stationary_elements_get_no_swept_region(self):
        for bid in BENCHMARKS:
            mech, prod = self.out[bid]
            moving = {p.name for p in mech.selected.parts if p.moving}
            for r in prod.regions:
                if r.kind is RegionKind.SWEPT_VOLUME:
                    with self.subTest(benchmark=bid, region=r.name):
                        self.assertTrue(set(r.houses) <= moving)

    def test_assembly_installs_supports_before_what_they_support(self):
        for bid in BENCHMARKS:
            prod = self.prod(bid)
            order = {s.pieces[0]: s.order for s in prod.assembly_sequence if s.pieces}
            for o in prod.obligation_ownership:
                if o.owner_piece and o.owner_piece in order and o.element in order:
                    if o.obligation in (
                        ObligationKind.RADIAL_SUPPORT,
                        ObligationKind.AXIAL_THRUST,
                        ObligationKind.GUIDANCE,
                        ObligationKind.STRUCTURAL_ROOT,
                    ):
                        with self.subTest(benchmark=bid, obligation=o.obligation.value):
                            self.assertLess(
                                order[o.owner_piece], order[o.element],
                                f"{o.owner_piece} must exist before {o.element}",
                            )

    def test_assembly_covers_every_piece_exactly_once(self):
        for bid in BENCHMARKS:
            prod = self.prod(bid)
            installed = [n for s in prod.assembly_sequence for n in s.pieces]
            with self.subTest(benchmark=bid):
                self.assertEqual(sorted(installed), sorted(p.name for p in prod.pieces))

    def test_load_path_hops_are_owned_by_regions(self):
        for bid in BENCHMARKS:
            prod = self.prod(bid)
            self.assertTrue(prod.load_path_ownership)
            for lp in prod.load_path_ownership:
                with self.subTest(benchmark=bid, path=lp.name):
                    self.assertTrue(lp.path)
                    self.assertTrue(lp.owning_regions, "no region owns any hop")

    def test_freedoms_and_open_decisions_survive(self):
        for bid in BENCHMARKS:
            mech, prod = self.out[bid]
            for d in mech.selected.downstream_decisions:
                with self.subTest(benchmark=bid, decision=d):
                    self.assertIn(d, prod.unresolved_decisions)

    def test_process_is_not_decided_here(self):
        """Material and process are design freedoms, not Stage 03 decisions."""
        for bid in BENCHMARKS:
            prod = self.prod(bid)
            with self.subTest(benchmark=bid):
                self.assertEqual(prod.manufacturing_intent, "")
                self.assertTrue(
                    any("process" in d for d in prod.unresolved_decisions),
                    "process must be recorded as unresolved",
                )

    def test_no_dimensions_are_emitted(self):
        for bid in BENCHMARKS:
            prod = self.prod(bid)
            text = " ".join(
                [r.purpose for r in prod.regions]
                + [p.rationale for p in prod.pieces]
                + [p.why for p in prod.placements]
                + [s.action for s in prod.assembly_sequence]
                + [prod.housing_strategy, prod.service_strategy, prod.proportions]
            )
            with self.subTest(benchmark=bid):
                self.assertNotRegex(text, r"\d+\s*(mm|kg|deg|N|°)", "a dimension leaked")

    def test_stage02_gaps_are_reported_not_compensated(self):
        """An unowned obligation must surface as an advisory."""
        spec = load_spec("BM-002")
        mech = MechanicalArchitectureGenerator().run(spec=spec)
        mech.selected.support_obligations[0].reacted_by = None
        prod = ProductArchitecturePlanner().run(spec=spec, mechanical=mech)
        self.assertTrue(prod.architecture_advisories)
        self.assertTrue(any(o.unowned_reason for o in prod.obligation_ownership))


class BM001ProductOrganisation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mech, cls.prod = stage03(load_spec("BM-001"))

    def region_kinds(self):
        return {r.kind for r in self.prod.regions}

    def test_body_and_closure_are_distinct_pieces(self):
        kinds = {p.kind for p in self.prod.pieces}
        self.assertIn(PieceKind.SHELL, kinds, "no body")
        self.assertIn(PieceKind.MOVING_BODY, kinds, "no closure")

    def test_opening_interface_and_stop_are_organised(self):
        names = {p.name for p in self.prod.pieces}
        self.assertIn("opening_interface", names)
        self.assertIn("opening_stop", names)
        self.assertIn(RegionKind.TRAVEL_LIMIT_ZONE, self.region_kinds())

    def test_retaining_pair_has_a_region_and_a_structural_owner(self):
        self.assertIn(RegionKind.RETENTION_ZONE, self.region_kinds())
        roots = [
            o for o in self.prod.obligation_ownership
            if o.obligation is ObligationKind.STRUCTURAL_ROOT
        ]
        self.assertTrue(roots, "the retaining feature has no structural root owner")
        self.assertTrue(all(o.owner_piece for o in roots))

    def test_release_access_region_exists(self):
        self.assertIn(RegionKind.USER_ACCESS, self.region_kinds())

    def test_storage_volume_and_closure_envelope_exist(self):
        self.assertIn(RegionKind.ENCLOSED_VOLUME, self.region_kinds())
        swept = [r for r in self.prod.regions if r.kind is RegionKind.SWEPT_VOLUME]
        self.assertTrue(any("closure_member" in r.houses for r in swept))

    def test_a_moving_closure_needs_no_separate_service_cover(self):
        """The closure already opens the product; a cover would be invented."""
        self.assertFalse(
            any(p.kind is PieceKind.COVER for p in self.prod.pieces),
            "a service cover was invented beside an opening closure",
        )


class BM002ProductOrganisation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mech, cls.prod = stage03(load_spec("BM-002"))

    def region_kinds(self):
        return {r.kind for r in self.prod.regions}

    def piece_kinds(self):
        return {p.kind for p in self.prod.pieces}

    def test_housing_and_service_cover_exist(self):
        self.assertIn(PieceKind.SHELL, self.piece_kinds())
        self.assertIn(PieceKind.COVER, self.piece_kinds())
        self.assertIn(RegionKind.SERVICE_ACCESS, self.region_kinds())

    def test_external_crank_access_region_exists(self):
        external = [r for r in self.prod.regions if r.external]
        self.assertTrue(external)
        self.assertIn(RegionKind.USER_ACCESS, self.region_kinds())

    def test_transmission_and_travel_regions_are_separate(self):
        names = {r.name for r in self.prod.regions}
        self.assertIn("transmission_region", names)
        self.assertIn("working_volume", names)

    def test_guide_radial_and_thrust_zones_are_owned(self):
        owned = {
            o.obligation: o.owner_piece
            for o in self.prod.obligation_ownership if o.owner_piece
        }
        for required in (
            ObligationKind.GUIDANCE,
            ObligationKind.ANTI_ROTATION,
            ObligationKind.RADIAL_SUPPORT,
            ObligationKind.AXIAL_THRUST,
            ObligationKind.TRAVEL_LIMIT,
        ):
            with self.subTest(obligation=required.value):
                self.assertIn(required, owned, f"{required.value} has no product owner")

    def test_platform_swept_volume_and_payload_region_exist(self):
        self.assertIn(RegionKind.SWEPT_VOLUME, self.region_kinds())
        self.assertIn(RegionKind.PAYLOAD, self.region_kinds())

    def test_travel_stop_is_a_piece(self):
        self.assertIn(PieceKind.LIMIT_ELEMENT, self.piece_kinds())

    def test_assembly_sequence_is_ordered_and_complete(self):
        steps = self.prod.assembly_sequence
        self.assertGreaterEqual(len(steps), 8)
        self.assertEqual([s.order for s in steps], list(range(1, len(steps) + 1)))
        self.assertEqual(steps[-1].pieces, ["service_cover"], "the cover must close last")

    def test_quantitative_constraints_remain_traceable(self):
        self.assertTrue(self.mech.selected.constrained_by)


if __name__ == "__main__":
    unittest.main()
