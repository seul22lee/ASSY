"""Interface contract tests.

The priority of the vertical slice is that the interfaces are correct, so these
tests assert *contracts* rather than engineering quality: object ownership,
stage boundaries, provenance, determinism, and the Stage 05 working-state
invariants. They deliberately do not assert that any particular design is good.

    ./mujoco_core/bin/py -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from assy.domain.common import Stage, reset_ids
from assy.domain.downstream import ReqStatus, RestartStage, SolveStatus, ValidationBackend
from assy.runartifacts import SLOTS
from assy.stages.s11_evaluate import assess_evidence
from assy.domain.engineering import (
    GATING_KINDS,
    CheckKind,
    CommitmentKind,
    CommitmentStatus,
)
from assy.pipeline import Pipeline
from benchmarks import CORE, BM001, BM002, BM101

EXPECTED_STAGES = 12

# object type -> the single stage that owns it (DOMAIN_SPECIFICATION section 4.2)
OWNERSHIP = {
    "RequirementSpec": Stage.REQUIREMENT,
    "MechanicalArchitecture": Stage.MECHANICAL,
    "ProductArchitecture": Stage.PRODUCT,
    "ConceptVisualization": Stage.CONCEPT,
    "CADReadyEngineeringDefinition": Stage.ENGINEERING,
    "SolvedDesign": Stage.SOLVER,
    "CADArtifactManifest": Stage.CAD,
    "SimulationPlan": Stage.SIM_PLAN,
    "SimulationResult": Stage.SIM_RUN,
    "MetricReport": Stage.METRICS,
    "EvaluationReport": Stage.EVALUATION,
    "RevisionDirective": Stage.REVISION,
}


def run(benchmark, out: Path):
    return Pipeline(
        out_dir=out,
        benchmark_id=benchmark.id,
        tier=benchmark.tier.value,
        run_id="test",
    ).run(benchmark.request, clarifications=list(benchmark.clarifications))


class PipelineExecution(unittest.TestCase):
    """Every stage executes for every benchmark - the vertical slice objective."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        # Core tier only: advanced benchmarks validate a mature pipeline and are
        # explicitly outside the initial implementation milestone.
        cls.results = {bid: run(bm, root / bid) for bid, bm in CORE.items()}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_all_stages_execute_for_every_benchmark(self):
        for bid, result in self.results.items():
            with self.subTest(benchmark=bid):
                self.assertEqual(len(result.stages), EXPECTED_STAGES, result.report())
                failed = [s.name for s in result.stages if not s.ok]
                self.assertEqual(failed, [], f"{bid} failed stages: {failed}\n{result.report()}")

    def test_every_object_is_produced_by_its_owning_stage(self):
        for bid, result in self.results.items():
            for name, owner in OWNERSHIP.items():
                with self.subTest(benchmark=bid, object=name):
                    obj = result.get(name)
                    self.assertIsNotNone(obj, f"{name} missing for {bid}")
                    self.assertEqual(obj.meta.producer, owner)

    def test_objects_are_registered_in_the_session(self):
        for bid, result in self.results.items():
            with self.subTest(benchmark=bid):
                for name in OWNERSHIP:
                    self.assertIn(name, result.session.objects)

    def test_downstream_objects_reference_their_source(self):
        """No hidden information flow: each object names what it came from."""
        for bid, result in self.results.items():
            with self.subTest(benchmark=bid):
                self.assertEqual(
                    result.get("SolvedDesign").source_definition_id,
                    result.get("CADReadyEngineeringDefinition").meta.object_id,
                )
                self.assertEqual(
                    result.get("CADArtifactManifest").source_solved_id,
                    result.get("SolvedDesign").meta.object_id,
                )
                self.assertEqual(
                    result.get("EvaluationReport").source_metric_id,
                    result.get("MetricReport").meta.object_id,
                )


class Determinism(unittest.TestCase):
    """Rule CODE-10: identical inputs produce identical outputs."""

    def test_repeated_runs_agree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = run(BM002, root / "a")
            b = run(BM002, root / "b")
        self.assertEqual(a.get("SolvedDesign").as_dict(), b.get("SolvedDesign").as_dict())
        self.assertEqual(
            a.get("EvaluationReport").overall, b.get("EvaluationReport").overall
        )
        self.assertEqual(
            a.get("CADReadyEngineeringDefinition").iterations,
            b.get("CADReadyEngineeringDefinition").iterations,
        )


class StageBoundaries(unittest.TestCase):
    """Each stage answers one question and does not leak into its neighbours."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.result = run(BM002, Path(cls.tmp.name))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_requirements_carry_no_mechanism_choice(self):
        spec = self.result.get("RequirementSpec")
        banned = ("screw", "rack", "pinion", "gear", "cable drum")
        for r in spec.requirements:
            for word in banned:
                self.assertNotIn(word, r.statement.lower(), f"{r.id} names a mechanism")

    def test_concept_visualization_is_never_authoritative(self):
        self.assertFalse(self.result.get("ConceptVisualization").authoritative)

    def test_upstream_never_references_kernel_topology(self):
        """STAGE_05 section 21: no face_/edge_ ids upstream of the CAD builder."""
        definition = self.result.get("CADReadyEngineeringDefinition")
        for c in definition.working_state.active:
            self.assertNotRegex(c.subject, r"(face|edge|solid)_\d+")

    def test_semantic_map_is_generated_by_the_builder_only(self):
        manifest = self.result.get("CADArtifactManifest")
        definition = self.result.get("CADReadyEngineeringDefinition")
        subjects = {c.subject for c in definition.working_state.active}
        for semantic_id in manifest.semantic_map:
            self.assertIn(semantic_id, subjects, "map keys must be upstream identities")

    def test_metrics_do_not_decide_pass_or_fail(self):
        report = self.result.get("MetricReport")
        for m in report.metrics:
            self.assertNotIn("pass", m.name.lower())
            self.assertIsInstance(m.value, float)
            self.assertTrue(m.unit)

    def test_solver_does_not_invent_parameters(self):
        solved = self.result.get("SolvedDesign")
        definition = self.result.get("CADReadyEngineeringDefinition")
        known = {c.id for c in definition.working_state.active}
        for p in solved.parameters:
            self.assertIn(p.commitment_id, known)


class WorkingStateInvariants(unittest.TestCase):
    """The four-object model, including the Geneva-derived modifications."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.state = run(BM002, Path(cls.tmp.name)).get(
            "CADReadyEngineeringDefinition"
        ).working_state

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_commitments_are_never_deleted(self):
        for c in self.state.commitments.values():
            if c.status is CommitmentStatus.SUPERSEDED:
                self.assertIsNotNone(c.superseded_by)

    def test_every_check_declares_kind_and_domain(self):
        self.assertTrue(self.state.checks)
        for k in self.state.checks.values():
            self.assertIsInstance(k.kind, CheckKind)
            self.assertTrue(k.evaluation_domain)

    def test_only_gating_kinds_are_mandatory(self):
        for k in self.state.checks.values():
            if k.mandatory:
                self.assertIn(k.kind, GATING_KINDS)

    def test_problems_have_canonical_identity(self):
        keys = [p.key for p in self.state.problems.values()]
        self.assertEqual(len(keys), len(set(keys)), "duplicate problem keys present")

    def test_applied_commitments_carry_provenance(self):
        for c in self.state.active:
            if c.provenance.resolution_id is not None:
                self.assertIn(c.provenance.resolution_id, self.state.resolutions)
                self.assertIsNotNone(c.provenance.method)

    def test_objectives_are_representable(self):
        objectives = self.state.active_by_kind(CommitmentKind.OBJECTIVE)
        self.assertTrue(objectives, "trade-offs must be expressible as objectives")


class ReadinessGating(unittest.TestCase):
    """CAD readiness requires closure, not merely an empty agenda."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.ready = run(BM002, root / "ready")
        # BM-101 is advanced tier: the knowledge base has no resolvers for
        # intermittent indexing, so it is the honest under-evidenced case.
        cls.partial = run(BM101, root / "partial")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_ready_requires_every_condition(self):
        r = self.ready.get("CADReadyEngineeringDefinition").readiness
        if r.ready:
            self.assertTrue(r.no_blocking_problems)
            self.assertTrue(r.mandatory_checks_executed)
            self.assertTrue(r.mandatory_checks_passing)
            self.assertTrue(r.all_commitments_determined)
            self.assertTrue(r.system_structurally_solvable)
            self.assertEqual(r.undetermined, [])

    def test_incomplete_knowledge_reports_rather_than_pretends(self):
        """No intermittent-indexing resolvers exist; the run must say so."""
        r = self.partial.get("CADReadyEngineeringDefinition").readiness
        self.assertFalse(r.ready)
        # Incompleteness must surface through *some* named channel rather than
        # silently: a blocked reason, a failing check, or an undetermined item.
        self.assertTrue(
            r.blocked_reason is not None
            or r.failing_checks
            or r.undetermined
            or r.missing_checks
            or not r.no_blocking_problems,
            f"readiness gave no reason for ready=False: {r}",
        )

    def test_no_evidence_yields_insufficient_not_pass(self):
        evaluation = self.partial.get("EvaluationReport")
        self.assertNotEqual(evaluation.overall.value, "pass")

    def test_simulation_is_not_fabricated_without_a_mover(self):
        """No hinged or translating body means no motion model may be invented."""
        plan = self.partial.get("SimulationPlan")
        result = self.partial.get("SimulationResult")
        self.assertEqual(plan.tests, [])
        self.assertEqual(result.results, [])

    def test_compliant_design_reaches_full_evidence(self):
        """BM-001 has both backends wired, so it must not stall as under-evidenced."""
        with tempfile.TemporaryDirectory() as tmp:
            latch = run(BM001, Path(tmp))
        definition = latch.get("CADReadyEngineeringDefinition")
        self.assertTrue(definition.readiness.ready)
        self.assertNotEqual(latch.get("EvaluationReport").overall.value, "insufficient_evidence")


class RunArtifactLayout(unittest.TestCase):
    """Persistence is orthogonal: benchmark -> run -> stage, output.json authoritative."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.result = run(BM001, Path(cls.tmp.name))
        cls.root = cls.result.run_dir

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_run_root_is_benchmark_then_run(self):
        self.assertIsNotNone(self.root)
        self.assertEqual(self.root.name, "run-test")
        self.assertEqual(self.root.parent.name, BM001.id)

    def test_every_stage_has_its_own_directory(self):
        for slot in SLOTS:
            with self.subTest(stage=slot.number):
                d = self.root / f"stage_{slot.number:02d}_{slot.name}"
                self.assertTrue(d.is_dir(), f"missing {d}")
                self.assertTrue((d / "input_refs.json").exists())
                self.assertTrue((d / "report.md").exists())

    def test_output_json_is_the_authoritative_artifact(self):
        for slot in SLOTS:
            d = self.root / f"stage_{slot.number:02d}_{slot.name}"
            if self.result.get(slot.produces) is not None:
                with self.subTest(stage=slot.number):
                    payload = json.loads((d / "output.json").read_text())
                    self.assertIn("meta", payload)

    def test_input_refs_reference_rather_than_duplicate(self):
        for slot in SLOTS:
            d = self.root / f"stage_{slot.number:02d}_{slot.name}"
            refs = json.loads((d / "input_refs.json").read_text())
            for ref in refs["consumes"]:
                with self.subTest(stage=slot.number, ref=ref["object"]):
                    # A reference carries an id and a location, never the payload.
                    self.assertEqual(set(ref) & {"object", "object_id", "location"},
                                     {"object", "object_id", "location"})
                    self.assertNotIn("meta", ref)

    def test_run_level_artifacts_exist(self):
        for name in ("run_manifest.json", "run_summary.md", "assumptions.md"):
            self.assertTrue((self.root / name).exists(), name)

    def test_manifest_records_provenance_and_authority(self):
        manifest = json.loads((self.root / "run_manifest.json").read_text())
        for key in ("benchmark_id", "tier", "run_id", "timestamp", "commit",
                    "code_version", "stages", "artifacts"):
            self.assertIn(key, manifest)
        self.assertEqual(len(manifest["stages"]), EXPECTED_STAGES)
        allowed = {"authoritative", "evidence-backed", "provisional", "placeholder"}
        for entry in manifest["stages"]:
            self.assertIn(entry["authority"], allowed)

    def test_placeholder_stages_are_declared_as_such(self):
        manifest = json.loads((self.root / "run_manifest.json").read_text())
        by_number = {e["number"]: e for e in manifest["stages"]}
        for n in (1, 2, 3, 4):
            self.assertEqual(by_number[n]["authority"], "placeholder")

    def test_stage05_projections_avoid_one_huge_file(self):
        d = self.root / "stage_05_engineering_integration"
        for name in ("commitments.json", "problems.json", "resolutions.json",
                     "checks.json", "readiness_report.json", "trace.md"):
            with self.subTest(projection=name):
                self.assertTrue((d / name).exists(), name)
        commitments = json.loads((d / "commitments.json").read_text())
        self.assertIsInstance(commitments, list)
        self.assertTrue(commitments)

    def test_visualizations_are_derived_not_authoritative(self):
        cad = self.root / "stage_07_cad_builder"
        self.assertTrue((cad / "part_legend.md").exists())
        self.assertTrue((cad / "cad").is_dir())
        # A missing render must never invalidate the authoritative output.
        self.assertTrue((cad / "output.json").exists())


class ValidationBackends(unittest.TestCase):
    """Physics is split by phenomenon, not forced into one simulator."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.latch = run(BM001, Path(cls.tmp.name) / "latch")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_compliant_design_uses_both_backends(self):
        plan = self.latch.get("SimulationPlan")
        backends = {t.backend for t in plan.tests}
        self.assertIn(ValidationBackend.ANALYTICAL, backends)
        self.assertIn(ValidationBackend.MUJOCO, backends)

    def test_expected_latch_tests_are_planned(self):
        plan = self.latch.get("SimulationPlan")
        names = {t.name for t in plan.tests}
        for expected in ("close_and_engage", "hold_under_disturbance",
                         "release_latch", "reopen_without_interference"):
            self.assertIn(expected, names)

    def test_every_test_declares_a_validity_domain(self):
        plan = self.latch.get("SimulationPlan")
        for t in plan.tests:
            with self.subTest(test=t.name):
                self.assertTrue(t.validity_domain)
                self.assertTrue(t.phenomenon)

    def test_rigid_body_limitation_is_stated(self):
        plan = self.latch.get("SimulationPlan")
        text = " ".join(plan.modelling_limitations).lower()
        self.assertIn("rigid", text)
        self.assertIn("strain", text)

    def test_analytical_backend_produces_compliant_evidence(self):
        result = self.latch.get("SimulationResult")
        analytical = [r for r in result.results if r.backend is ValidationBackend.ANALYTICAL]
        self.assertTrue(analytical)
        summary = analytical[0].series_summary
        for key in ("peak_strain", "retention_force_n", "release_force_n", "strain_margin"):
            self.assertIn(key, summary)

    def test_pass_requires_both_evidence_classes(self):
        evaluation = self.latch.get("EvaluationReport")
        definition = self.latch.get("CADReadyEngineeringDefinition")
        plan = self.latch.get("SimulationPlan")
        result = self.latch.get("SimulationResult")
        coverage = assess_evidence(definition, plan, result)
        if evaluation.overall == ReqStatus.PASS:
            self.assertTrue(coverage.sufficient)
            self.assertTrue(coverage.needs_compliant and coverage.compliant_ok)
            self.assertTrue(coverage.needs_motion and coverage.motion_ok)


class RevisionRouting(unittest.TestCase):
    """Routing is derived from the Stage 05 dependency graph."""

    def test_pass_routes_to_no_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run(BM002, Path(tmp))
        evaluation = result.get("EvaluationReport")
        directive = result.get("RevisionDirective")
        if evaluation.overall.value == "pass":
            self.assertEqual(directive.restart, RestartStage.NONE)

    def test_directive_preserves_untouched_commitments(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run(BM001, Path(tmp))
        directive = result.get("RevisionDirective")
        overlap = set(directive.preserve) & set(directive.target_commitments)
        self.assertEqual(overlap, set(), "a commitment cannot be both preserved and revised")


if __name__ == "__main__":
    unittest.main(verbosity=2)
