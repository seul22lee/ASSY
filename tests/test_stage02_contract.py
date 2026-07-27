"""Stage 01 -> Stage 02 contract tests.

Stage 02 is a strict consumer of the Stage 01 structured contract. These tests
assert that property directly rather than through pipeline side effects:

  * it reads structured fields and nothing else
  * it refuses, with a typed deficiency, rather than reconstructing intent
  * the same production implementation answers every entry point

Deterministic and fast: no model call, no filesystem, committed fixtures only.

    ./mujoco_core/bin/py -m unittest discover -s tests -t .
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from assy.domain.common import ObjectMeta, Stage, new_id, reset_ids
from assy.domain.upstream import (
    BehaviourSpec,
    Continuity,
    InterfaceKind,
    MechanismRole,
    ObligationKind,
    MechanicalArchitecture,
    QuantityKind,
    Requirement,
    RequirementKind,
    RequirementOrigin,
    RequirementSpec,
    Stage01ContractDeficiency,
)
from assy.pipeline import Pipeline
from assy.stages import IncompleteRequirementProducer, MechanicalArchitectureGenerator
from benchmarks import ALL
from tests.fixtures import BENCHMARK_IDS, deficiency_fingerprint, fingerprint, load_spec

# The single production entry point under test.
STAGE02 = MechanicalArchitectureGenerator


def stage02(spec: RequirementSpec):
    reset_ids()
    return STAGE02().run(spec=spec)


def minimal_spec(*requirements: Requirement) -> RequirementSpec:
    return RequirementSpec(
        meta=ObjectMeta(object_id=new_id("SPEC"), producer=Stage.REQUIREMENT),
        source_text="",
        product_intent="an unspecified mechanical product",
        requirements=list(requirements),
    )


def requirement(
    rid: str,
    *,
    kind: RequirementKind = RequirementKind.FUNCTIONAL,
    statement: str = "unspecified",
    behaviour: BehaviourSpec | None = None,
    bound=None,
) -> Requirement:
    return Requirement(
        id=rid,
        kind=kind,
        origin=RequirementOrigin.USER_STATED,
        statement=statement,
        behaviour=behaviour,
        bound=bound,
    )


ROTATION_TO_TRANSLATION = BehaviourSpec(
    actor="user",
    action="drive",
    object="platform",
    input_kind=QuantityKind.ROTATION,
    output_kind=QuantityKind.TRANSLATION,
    continuity=Continuity.CONTINUOUS,
    reversible=True,
)


# ---------------------------------------------------------------------------
# Fast unit tests: the consumer contract
# ---------------------------------------------------------------------------
class Stage02AcceptsStructuredContract(unittest.TestCase):
    def test_a_valid_structured_spec_yields_an_architecture(self):
        arch = stage02(minimal_spec(requirement("REQ-001", behaviour=ROTATION_TO_TRANSLATION)))
        self.assertIsInstance(arch, MechanicalArchitecture)
        self.assertTrue(arch.candidates)
        self.assertIn(arch.selected_id, {c.id for c in arch.candidates})

    def test_candidates_are_retrieved_by_structured_signature(self):
        """Selection follows (input_kind, output_kind, continuity), not words."""
        rotational = stage02(
            minimal_spec(requirement("REQ-001", behaviour=ROTATION_TO_TRANSLATION))
        )
        held = stage02(
            minimal_spec(
                requirement(
                    "REQ-001",
                    behaviour=BehaviourSpec(
                        actor="user",
                        action="retain",
                        object="closure",
                        input_kind=QuantityKind.FORCE,
                        output_kind=QuantityKind.STATE,
                        continuity=Continuity.HELD,
                    ),
                )
            )
        )
        # Identical prose, different declared signature -> disjoint candidate sets.
        self.assertTrue(
            {c.id for c in rotational.candidates}.isdisjoint({c.id for c in held.candidates})
        )

    def test_requirement_traceability_is_preserved(self):
        spec = minimal_spec(
            requirement("REQ-001", behaviour=ROTATION_TO_TRANSLATION),
            requirement("REQ-007", behaviour=ROTATION_TO_TRANSLATION),
        )
        arch = stage02(spec)
        for c in arch.candidates:
            self.assertEqual(sorted(c.serves_requirements), ["REQ-001", "REQ-007"])

    def test_freedoms_stay_open_and_do_not_become_assumptions(self):
        """A choice the user left open must not be silently decided here."""
        spec = load_spec("BM-001")
        self.assertTrue(spec.freedoms, "fixture must exercise freedoms")
        arch = stage02(spec)
        subjects = [f.subject.lower() for f in spec.freedoms]
        for c in arch.candidates:
            for a in c.assumptions:
                for subject in subjects:
                    self.assertNotIn(
                        subject,
                        a.lower(),
                        f"freedom '{subject}' was converted into an assumption: {a}",
                    )
        # A freedom is instead carried as still-available choice.
        self.assertTrue(
            any("left open" in a for c in arch.candidates for a in c.assumptions)
        )


class Stage02RefusesRatherThanGuessing(unittest.TestCase):
    def test_no_usable_transformation_is_blocking(self):
        spec = minimal_spec(requirement("REQ-001", statement="the box should latch shut"))
        result = stage02(spec)
        self.assertIsInstance(result, Stage01ContractDeficiency)
        blocking = [d for d in result.items if d.blocking]
        self.assertTrue(blocking)
        self.assertTrue(all(d.why_stage02_needs_it for d in result.items))
        self.assertTrue(all(d.remedy for d in result.items))

    def test_no_behavioural_requirement_at_all_is_blocking(self):
        spec = minimal_spec(
            requirement("REQ-001", kind=RequirementKind.MANUFACTURING, statement="low cost")
        )
        result = stage02(spec)
        self.assertIsInstance(result, Stage01ContractDeficiency)
        self.assertTrue(any(d.blocking for d in result.items))

    def test_deficiency_names_the_missing_field_and_its_source(self):
        spec = minimal_spec(requirement("REQ-001"))
        result = stage02(spec)
        self.assertEqual(result.source_spec_id, spec.meta.object_id)
        self.assertTrue(any("behaviour" in d.missing_field for d in result.items))

    def test_a_locally_missing_behaviour_is_advisory_not_blocking(self):
        """A quantitative requirement need not invent a meaningless BehaviourSpec.

        A bound that merely quantifies another behaviour has no transformation of
        its own. Blocking on it would stop synthesis for a gap that costs no
        geometric information.
        """
        spec = load_spec("BM-002")
        arch = stage02(spec)
        self.assertIsInstance(arch, MechanicalArchitecture, "must not block")
        self.assertTrue(arch.contract_advisories, "the gap must still be reported")

    def test_an_unrealizable_transformation_is_reported_not_silently_dropped(self):
        spec = minimal_spec(
            requirement(
                "REQ-001",
                behaviour=BehaviourSpec(
                    actor="user",
                    action="do",
                    object="thing",
                    input_kind=QuantityKind.DISPLACEMENT,
                    output_kind=QuantityKind.ROTATION,
                    continuity=Continuity.SINGLE_EVENT,
                ),
            )
        )
        result = stage02(spec)
        self.assertIsInstance(result, Stage01ContractDeficiency)
        self.assertIn("mechanism family", result.items[0].missing_field)


class Stage02IgnoresNaturalLanguage(unittest.TestCase):
    """Blanking or corrupting prose must not move a single decision."""

    def _invariant_under(self, bid: str, mutate) -> None:
        baseline = fingerprint(stage02(load_spec(bid)))
        mutated_spec = load_spec(bid)
        mutate(mutated_spec)
        self.assertEqual(fingerprint(stage02(mutated_spec)), baseline, bid)

    def test_source_text_is_ignored(self):
        for bid in BENCHMARK_IDS:
            with self.subTest(benchmark=bid):
                self._invariant_under(bid, lambda s: setattr(s, "source_text", ""))

    def test_misleading_source_text_is_ignored(self):
        decoy = "Design a bicycle gearbox with a chain tensioner and a freewheel hub. " * 8
        for bid in BENCHMARK_IDS:
            with self.subTest(benchmark=bid):
                self._invariant_under(bid, lambda s: setattr(s, "source_text", decoy))

    def test_requirement_prose_is_ignored(self):
        def scramble(spec):
            for i, r in enumerate(spec.requirements):
                r.statement = f"opaque requirement {i}"
        for bid in BENCHMARK_IDS:
            with self.subTest(benchmark=bid):
                self._invariant_under(bid, scramble)

    def test_product_intent_is_a_summary_not_an_input(self):
        def rename(spec):
            spec.product_intent = "a rotary gearbox for a bicycle"
            spec.user_intent_summary = "the user wants a bicycle gearbox"
        for bid in BENCHMARK_IDS:
            with self.subTest(benchmark=bid):
                self._invariant_under(bid, rename)

    def test_benchmark_identity_does_not_reach_selection(self):
        """No selection from a title, a filename, or a design id."""
        def relabel(spec):
            spec.meta.design_id = "BM-999_SNAP_FIT_MAGNETIC_LID"
            spec.product_intent = "Geneva mechanism indexing box"
        for bid in BENCHMARK_IDS:
            with self.subTest(benchmark=bid):
                self._invariant_under(bid, relabel)

    def test_deficiency_output_is_also_prose_invariant(self):
        spec = minimal_spec(requirement("REQ-001", statement="raise the platform by crank"))
        baseline = deficiency_fingerprint(stage02(spec))
        other = minimal_spec(requirement("REQ-001", statement="index the wheel one step"))
        self.assertEqual(deficiency_fingerprint(stage02(other)), baseline)

    def test_no_mechanism_vocabulary_in_the_stage_02_source(self):
        """A structural guard against the fallback being reintroduced."""
        source = Path("assy/stages/s02_mechanical.py").read_text()
        code = "\n".join(
            line for line in source.splitlines() if not line.lstrip().startswith("#")
        )
        code = code.split('"""', 2)[-1]  # drop the module docstring
        for banned in ("source_text", "re.search", "re.match", "re.findall", "regex"):
            self.assertNotIn(banned, code, f"Stage 02 must not use {banned}")
        for word in ("lift", "raise", "index", "latch", "lid", "crank", "geneva", "rack"):
            self.assertNotIn(word, code.lower(), f"Stage 02 must not mention '{word}'")


# ---------------------------------------------------------------------------
# Contract integration: committed fixtures -> production Stage 02
# ---------------------------------------------------------------------------
class GeometryHandoff(unittest.TestCase):
    """Geometry-relevant BM information survives Stage 01 and is used by Stage 02."""

    @classmethod
    def setUpClass(cls):
        cls.specs = {bid: load_spec(bid) for bid in BENCHMARK_IDS}
        cls.arch = {bid: stage02(s) for bid, s in cls.specs.items()}

    def signatures(self, bid):
        return {
            r.behaviour.signature for r in self.specs[bid].requirements if r.behaviour
        }

    def test_every_benchmark_synthesizes(self):
        for bid, arch in self.arch.items():
            with self.subTest(benchmark=bid):
                self.assertIsInstance(arch, MechanicalArchitecture, bid)

    def test_every_benchmark_offers_distinct_principles(self):
        """A single candidate would mean the choice was made before the evidence."""
        for bid, arch in self.arch.items():
            with self.subTest(benchmark=bid):
                self.assertGreaterEqual(len(arch.candidates), 2, bid)
                principles = {c.principle for c in arch.candidates}
                self.assertEqual(len(principles), len(arch.candidates), "duplicate principles")

    # -- BM-001: reusable latch ------------------------------------------
    def test_bm001_reusable_retention_and_intentional_release(self):
        spec, arch = self.specs["BM-001"], self.arch["BM-001"]
        self.assertTrue(
            any(r.behaviour.output_kind is QuantityKind.STATE for r in spec.requirements if r.behaviour),
            "a retained state must be declared",
        )
        self.assertTrue(
            any(r.behaviour.reversible for r in spec.requirements if r.behaviour),
            "repeated open/close means a reversible behaviour",
        )
        self.assertTrue(
            all(c.holding_principle for c in arch.candidates),
            "every candidate must say how the closed state is held",
        )

    def test_bm001_forces_no_particular_retention_mechanism(self):
        arch = self.arch["BM-001"]
        self.assertGreaterEqual(len(arch.candidates), 3)
        for banned in ("snap", "magnet", "screw", "living hinge", "living_hinge"):
            self.assertNotIn(banned, arch.selection_rationale.lower())

    # -- BM-002: enclosed platform lift ----------------------------------
    def test_bm002_rotation_to_reversible_translation(self):
        spec = self.specs["BM-002"]
        lifting = [
            r for r in spec.requirements
            if r.behaviour
            and r.behaviour.input_kind is QuantityKind.ROTATION
            and r.behaviour.output_kind is QuantityKind.TRANSLATION
        ]
        self.assertTrue(lifting, "rotation->translation must be declared")
        self.assertTrue(any(r.behaviour.reversible for r in lifting), "raise AND lower")

    def test_bm002_travel_and_payload_bounds_reach_stage_02(self):
        bounds = {r.id: r.bound for r in self.specs["BM-002"].requirements if r.bound}
        self.assertTrue(bounds, "quantities must survive Stage 01")
        travel = [b for b in bounds.values() if b.unit == "mm"]
        self.assertTrue(travel, "the 80-100 mm travel must be recorded")
        self.assertEqual((travel[0].lower, travel[0].upper), (80.0, 100.0))
        self.assertEqual(travel[0].precision, "bounded")
        payload = [b for b in bounds.values() if b.unit == "kg"]
        self.assertTrue(payload, "the ~1 kg payload must be recorded")
        self.assertTrue(
            payload[0].approximate,
            "'approximately 1 kg' must not be asserted as an exact value",
        )

    def test_bm002_enclosure_and_open_architecture(self):
        spec, arch = self.specs["BM-002"], self.arch["BM-002"]
        self.assertTrue(spec.freedoms, "transmission and support must remain open")
        self.assertGreaterEqual(len(arch.candidates), 3, "several transmissions must survive")
        self.assertTrue(
            any(c.spatial_implications for c in arch.candidates),
            "an enclosed mechanism imposes spatial obligations",
        )

    # -- BM-101: indexing ------------------------------------------------
    def test_bm101_one_discrete_advance_with_dwell(self):
        spec, arch = self.specs["BM-101"], self.arch["BM-101"]
        indexing = [
            r for r in spec.requirements
            if r.behaviour
            and r.behaviour.input_kind is QuantityKind.ROTATION
            and r.behaviour.continuity is Continuity.INTERMITTENT
        ]
        self.assertTrue(indexing, "intermittent rotation must be declared")
        self.assertTrue(
            all(c.holding_principle for c in arch.candidates),
            "dwell means the output is held between events",
        )

    def test_bm101_layout_and_support_remain_open(self):
        spec, arch = self.specs["BM-101"], self.arch["BM-101"]
        self.assertTrue(spec.freedoms)
        self.assertTrue(all(c.downstream_decisions for c in arch.candidates))

    def test_bm101_geneva_is_not_selectable_by_name(self):
        """The catalogue contains no entry the benchmark title could match."""
        from assy.knowledge import mechanisms as cat

        self.assertFalse(
            [f for f in cat.FAMILIES if "geneva" in f.id.lower() or "geneva" in f.principle.lower()],
            "a 'geneva' family would let the title choose the mechanism",
        )
        self.assertGreaterEqual(len(self.arch["BM-101"].candidates), 2)


# ---------------------------------------------------------------------------
# The production path reaches this same implementation
# ---------------------------------------------------------------------------
class ProductionEntryPoint(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_pipeline_reaches_the_structured_consumer(self):
        """Instrument the production class and prove the pipeline calls it."""
        calls = []
        original = MechanicalArchitectureGenerator.run

        def spy(inner, *, spec):
            calls.append(spec)
            return original(inner, spec=spec)

        MechanicalArchitectureGenerator.run = spy
        self.addCleanup(setattr, MechanicalArchitectureGenerator, "run", original)

        spec = load_spec("BM-002")
        result = Pipeline(out_dir=self.root, benchmark_id="BM-002", run_id="t").run(
            "", spec=spec, persist=False
        )
        self.assertEqual(len(calls), 1, "Stage 02 must be invoked exactly once")
        self.assertIs(calls[0], spec, "the pipeline must pass the structured spec through")
        self.assertIsInstance(result.get("MechanicalArchitecture"), MechanicalArchitecture)

    def test_pipeline_result_matches_direct_invocation(self):
        """The audit path and the production path are the same implementation."""
        for bid in BENCHMARK_IDS:
            with self.subTest(benchmark=bid):
                direct = fingerprint(stage02(load_spec(bid)))
                reset_ids()
                piped = Pipeline(out_dir=self.root / bid, benchmark_id=bid, run_id="t").run(
                    "", spec=load_spec(bid), persist=False
                )
                self.assertEqual(fingerprint(piped.get("MechanicalArchitecture")), direct)

    def test_incomplete_producer_stops_the_pipeline_at_stage_02(self):
        """The documented, expected outcome of an incomplete Stage 01."""
        bm = ALL["BM-002"]
        result = Pipeline(
            out_dir=self.root / "incomplete",
            benchmark_id=bm.id,
            run_id="t",
            interpreter=IncompleteRequirementProducer(),
        ).run(bm.request, clarifications=list(bm.clarifications), persist=False)

        deficiency = result.get("Stage01ContractDeficiency")
        self.assertIsInstance(deficiency, Stage01ContractDeficiency)
        self.assertTrue(any(d.blocking for d in deficiency.items))
        self.assertEqual(len(result.stages), 2, "no stage may run past the deficiency")
        self.assertIsNone(result.get("MechanicalArchitecture"))

    def test_incomplete_producer_contains_no_fabricated_behaviour(self):
        """It must stay honestly incomplete rather than imitate Stage 01."""
        source = Path("assy/stages/s01_requirement.py").read_text()
        body = source.split('"""', 2)[-1]
        self.assertNotIn("BehaviourSpec", body)

        bm = ALL["BM-002"]
        spec = IncompleteRequirementProducer().run(
            request=bm.request, clarifications=list(bm.clarifications)
        )
        self.assertEqual(
            [r.id for r in spec.requirements if r.behaviour is not None],
            [],
            "the incomplete producer must not emit behaviour",
        )


# ---------------------------------------------------------------------------
# Architecture completeness: can Stage 03 build a product without rediscovering?
# ---------------------------------------------------------------------------
class ArchitectureIsMachineConsumable(unittest.TestCase):
    """Architecture content must be typed, not buried in prose.

    The standard is not "is the information present somewhere" but "can a later
    stage act on it without parsing English".
    """

    @classmethod
    def setUpClass(cls):
        cls.arch = {bid: stage02(load_spec(bid)) for bid in ("BM-001", "BM-002")}

    def selected(self, bid):
        return self.arch[bid].selected

    def test_every_obligation_names_a_declared_element(self):
        for bid, arch in self.arch.items():
            for c in arch.candidates:
                names = {p.name for p in c.parts}
                for o in c.support_obligations:
                    with self.subTest(benchmark=bid, candidate=c.id, obligation=o.kind.value):
                        self.assertIn(o.element, names, "obligation on an undeclared element")
                        if o.reacted_by is not None:
                            self.assertIn(o.reacted_by, names, "reacted by an undeclared element")

    def test_every_interface_joins_declared_elements(self):
        for bid, arch in self.arch.items():
            for c in arch.candidates:
                names = {p.name for p in c.parts}
                for i in c.interfaces:
                    with self.subTest(benchmark=bid, candidate=c.id, interface=i.kind.value):
                        self.assertTrue(set(i.between) <= names, f"{i.between} not declared")

    def test_every_function_names_declared_performers(self):
        for bid, arch in self.arch.items():
            for c in arch.candidates:
                names = {p.name for p in c.parts}
                for f in c.functions:
                    with self.subTest(benchmark=bid, candidate=c.id, function=f.function):
                        self.assertTrue(set(f.performed_by) <= names)

    def test_an_unperformed_function_is_declared_not_hidden(self):
        """A family that cannot hold position must say so structurally."""
        from assy.knowledge import mechanisms as cat

        nonholding = cat.by_id("flexible_tension_drive")
        self.assertIn("provide a holding function", nonholding.unassigned_functions)
        # And the ranking must react to it rather than treating it as free.
        arch = self.arch["BM-002"]
        self.assertIn("does not itself perform", " ".join(arch.rejected.values()))

    def test_stage_02_states_no_dimensions(self):
        """Architecture level only: no numbers may leak into the obligations."""
        for bid, arch in self.arch.items():
            for c in arch.candidates:
                text = " ".join(
                    [o.why for o in c.support_obligations]
                    + [i.transmits for i in c.interfaces]
                    + [f.function for f in c.functions]
                    + c.spatial_implications
                    + c.motion_envelopes
                )
                with self.subTest(benchmark=bid, candidate=c.id):
                    self.assertNotRegex(text, r"\d+\s*(mm|kg|deg|N|°)", "a dimension leaked")

    # -- BM-001: what Stage 03 must not have to invent --------------------
    def test_bm001_supplies_the_closure_architecture(self):
        c = self.selected("BM-001")
        functions = {f.function for f in c.functions}
        for expected in (
            "retain the closure in the closed state",
            "release retention",
            "receive intentional user input",
            "limit opening travel",
            "move the closure between open and closed",
            "transfer retention loads into the structure",
        ):
            self.assertIn(expected, functions, f"Stage 03 would have to invent: {expected}")

    def test_bm001_supplies_opening_interface_and_stop_as_elements(self):
        for c in self.arch["BM-001"].candidates:
            names = {p.name for p in c.parts}
            with self.subTest(candidate=c.id):
                self.assertIn("opening_interface", names)
                self.assertIn("opening_stop", names)

    def test_bm001_supplies_a_mating_retaining_pair(self):
        for c in self.arch["BM-001"].candidates:
            with self.subTest(candidate=c.id):
                retention = [p for p in c.parts if p.role is MechanismRole.RETENTION]
                self.assertTrue(retention, "no retaining element")
                contacts = [i for i in c.interfaces if i.kind is InterfaceKind.CONTACT_PAIR]
                self.assertTrue(contacts, "no mating pair carrying retention")

    def test_bm001_release_surface_is_reachable_and_travel_is_limited(self):
        for c in self.arch["BM-001"].candidates:
            kinds = {(o.element, o.kind) for o in c.support_obligations}
            with self.subTest(candidate=c.id):
                self.assertTrue(
                    any(k is ObligationKind.USER_ACCESS for _, k in kinds),
                    "the release surface has no accessibility obligation",
                )
                self.assertTrue(
                    any(k is ObligationKind.TRAVEL_LIMIT for _, k in kinds),
                    "opening travel has no limit obligation",
                )

    # -- BM-002: what Stage 03 must not have to invent --------------------
    def test_bm002_supplies_the_drive_architecture(self):
        c = self.selected("BM-002")
        functions = {f.function for f in c.functions}
        for expected in (
            "support the rotating input",
            "transmit input across the enclosure boundary",
            "guide the output",
            "support the payload",
            "control reverse motion",
            "limit travel",
            "transfer loads into the structure",
        ):
            self.assertIn(expected, functions, f"Stage 03 would have to invent: {expected}")

    def test_bm002_supplies_guidance_thrust_and_anti_rotation(self):
        c = self.selected("BM-002")
        kinds = {o.kind for o in c.support_obligations}
        for required in (
            ObligationKind.GUIDANCE,
            ObligationKind.ANTI_ROTATION,
            ObligationKind.AXIAL_THRUST,
            ObligationKind.RADIAL_SUPPORT,
            ObligationKind.TRAVEL_LIMIT,
        ):
            self.assertIn(required, kinds, f"Stage 03 would have to invent {required.value}")

    def test_bm002_every_obligation_names_its_reacting_element(self):
        """An obligation with no reactor is a problem Stage 03 must solve blind."""
        c = self.selected("BM-002")
        for o in c.support_obligations:
            with self.subTest(obligation=f"{o.element}/{o.kind.value}"):
                self.assertIsNotNone(o.reacted_by)

    def test_bm002_swept_volume_and_boundary_crossing_are_explicit(self):
        c = self.selected("BM-002")
        self.assertTrue(
            any(o.kind is ObligationKind.CLEARANCE for o in c.support_obligations),
            "the platform swept volume imposes no clearance obligation",
        )
        self.assertTrue(
            any(i.crosses_boundary for i in c.interfaces),
            "the crank must be declared to cross the enclosure boundary",
        )

    def test_bm002_quantitative_bounds_reach_the_architecture(self):
        """Travel and payload constrain the architecture and must be traceable."""
        spec = load_spec("BM-002")
        bounded = {r.id for r in spec.requirements if r.bound is not None}
        c = self.selected("BM-002")
        self.assertEqual(set(c.constrained_by), bounded)
        self.assertTrue(bounded, "fixture must carry bounds")


if __name__ == "__main__":
    unittest.main()
