"""Stage 01 reasoning regression — real model, real BM documents.

    current BM Markdown -> LLMRequirementInterpreter -> production Stage 02

**Skipped by default.** These are nondeterministic quality checks and must never
be mixed into a deterministic pass count: a model regression would then be
indistinguishable from a contract break, and a flaky run would look like broken
code. Enable explicitly:

    ASSY_LLM_REGRESSION=1 ./mujoco_core/bin/py -m unittest tests.test_llm_regression

They are also deliberately *loose*. They assert that the contract Stage 02 needs
is satisfied — not that the model produced any particular wording. Asserting
wording would optimise the prompt against the benchmark, which is forbidden.

Temperature is non-zero: a temperature-0 run is not evidence of repeatability.
"""

from __future__ import annotations

import os
import unittest

from assy.domain.upstream import (
    MechanicalArchitecture,
    QuantityKind,
    Stage01ContractDeficiency,
)
from assy.stages import LLMRequirementInterpreter, MechanicalArchitectureGenerator
from assy.stages.s01_llm import LLMUnavailable
from benchmarks import ALL
from tests.fixtures import deficiency_fingerprint, fingerprint

ENABLED = os.environ.get("ASSY_LLM_REGRESSION") == "1"


@unittest.skipUnless(ENABLED, "set ASSY_LLM_REGRESSION=1 to run live-model regressions")
class Stage01ReachesTheStage02Contract(unittest.TestCase):
    """Whatever the model words, the structured contract must be satisfiable."""

    @classmethod
    def setUpClass(cls):
        cls.specs = {}
        for bid, bm in ALL.items():
            try:
                cls.specs[bid] = LLMRequirementInterpreter().run(
                    request=bm.request, clarifications=list(bm.clarifications)
                )
            except LLMUnavailable as exc:  # pragma: no cover - environment dependent
                raise unittest.SkipTest(f"model unavailable: {exc}") from exc

    def test_stage02_accepts_every_benchmark(self):
        for bid, spec in self.specs.items():
            with self.subTest(benchmark=bid):
                result = MechanicalArchitectureGenerator().run(spec=spec)
                if isinstance(result, Stage01ContractDeficiency):
                    self.fail(
                        f"{bid} Stage 01 output was rejected: "
                        + "; ".join(
                            f"{d.missing_field} ({d.requirement_id})"
                            for d in result.items
                            if d.blocking
                        )
                    )
                self.assertIsInstance(result, MechanicalArchitecture)

    def test_at_least_one_transformation_is_declared(self):
        for bid, spec in self.specs.items():
            with self.subTest(benchmark=bid):
                usable = [
                    r for r in spec.requirements
                    if r.behaviour
                    and not (
                        r.behaviour.input_kind is QuantityKind.NONE
                        and r.behaviour.output_kind is QuantityKind.NONE
                    )
                ]
                self.assertTrue(usable, f"{bid}: no requirement declares a transformation")

    def test_freedoms_are_preserved_not_resolved(self):
        """Every BM says several solutions are acceptable; that must survive."""
        for bid, spec in self.specs.items():
            with self.subTest(benchmark=bid):
                self.assertTrue(spec.freedoms, f"{bid}: user-granted freedom was discarded")

    def test_live_output_is_still_source_text_invariant(self):
        """The invariance is a Stage 02 property and must hold on live specs too.

        It holds for a refusal exactly as it holds for an architecture: a rejected
        spec must be rejected identically once its prose is gone.
        """
        def stamp(obj):
            if isinstance(obj, Stage01ContractDeficiency):
                return deficiency_fingerprint(obj)
            return fingerprint(obj)

        for bid, spec in self.specs.items():
            with self.subTest(benchmark=bid):
                baseline = stamp(MechanicalArchitectureGenerator().run(spec=spec))
                blanked = spec.model_copy(deep=True)
                blanked.source_text = ""
                self.assertEqual(
                    stamp(MechanicalArchitectureGenerator().run(spec=blanked)), baseline
                )

    def test_no_mechanism_is_invented_by_stage_01(self):
        """The hard requirement: Stage 01 asks questions, it does not name solutions."""
        banned = ("screw", "rack", "pinion", "geneva", "cam", "ratchet", "snap-fit", "magnet")
        for bid, spec in self.specs.items():
            for r in spec.requirements:
                for word in banned:
                    with self.subTest(benchmark=bid, requirement=r.id, word=word):
                        self.assertNotIn(word, r.statement.lower())


if __name__ == "__main__":
    unittest.main()
