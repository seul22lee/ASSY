"""Pipeline orchestration.

Wires every stage explicitly with typed inputs and outputs. The wiring is
deliberately hardcoded rather than dynamic: the point of this slice is to prove
the interfaces compose, and an explicit graph makes a mismatch a load-time
error instead of a runtime surprise.

Execution continues past a failed stage where the contract allows it, so that a
single broken stage still exercises the interfaces downstream of it.
"""

from __future__ import annotations

import json
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from assy.version import __version__
from assy.domain.common import ObjectMeta, Stage, new_id, reset_ids
from assy.domain.downstream import ReqStatus, RestartStage
from assy.domain.upstream import Stage01ContractDeficiency
from assy.domain.session import DesignSession, IterationRecord, SessionStatus
from assy.runartifacts import RunArtifactWriter, RunLayout
from assy.domain.upstream import RequirementSpec
from assy.stages import (
    Budget,
    CADBuilder,
    ConceptVisualizer,
    EngineeringIntegration,
    LLMRequirementInterpreter,
    MechanicalArchitectureGenerator,
    MetricExtraction,
    ParametricSolver,
    ProductArchitecturePlanner,
    RequirementEvaluation,
    RevisionRouting,
    SimulationPlanBuilder,
    SimulationRunner,
)
from assy.stages.base import Reasoner, StageError


@dataclass
class StageRecord:
    name: str
    produced: str | None
    ok: bool
    detail: str = ""
    error: str | None = None


@dataclass
class PipelineResult:
    session: DesignSession
    run_dir: Path | None = None
    objects: dict[str, Any] = field(default_factory=dict)
    stages: list[StageRecord] = field(default_factory=list)

    @property
    def all_stages_ran(self) -> bool:
        return all(s.ok for s in self.stages)

    def get(self, name: str) -> Any:
        return self.objects.get(name)

    def report(self) -> str:
        lines = ["stage".ljust(34) + "status  produced"]
        lines.append("-" * 74)
        for s in self.stages:
            mark = "ok    " if s.ok else "FAIL  "
            lines.append(f"{s.name.ljust(34)}{mark}  {s.produced or '-'}")
            if s.detail:
                lines.append(f"{'':36}{s.detail}")
            if s.error:
                lines.append(f"{'':36}! {s.error}")
        return "\n".join(lines)


class Pipeline:
    """The full ASSY-Next vertical slice."""

    def __init__(
        self,
        out_dir: str | Path = "out",
        reasoner: Reasoner | None = None,
        budget: Budget | None = None,
        benchmark_id: str = "custom",
        tier: str = "core",
        run_id: str | None = None,
        interpreter: Any | None = None,
    ):
        self.out = Path(out_dir)
        self.reasoner = reasoner
        self.budget = budget
        self.benchmark_id = benchmark_id
        self.tier = tier
        self.run_id = run_id
        # Stage 01 is a reasoning stage. The default is the real interpreter;
        # an incomplete producer may be injected to exercise deficiency handling.
        self.interpreter = interpreter or LLMRequirementInterpreter()

    def run(
        self,
        request: str,
        *,
        clarifications: list[str] | None = None,
        design_id: str = "design-001",
        persist: bool = True,
        spec: RequirementSpec | None = None,
    ) -> PipelineResult:
        """Execute the pipeline.

        `spec` supplies an already-accepted Stage 01 handoff and bypasses the
        Stage 01 reasoner. It exists so deterministic tests can drive stages
        02-12 from a committed fixture without a model call. It is *not* a
        fallback: the spec must satisfy the Stage 01 contract on its own, and
        Stage 02 judges it by exactly the same rules either way.
        """
        reset_ids()
        self.out.mkdir(parents=True, exist_ok=True)

        # The run layout is created up front so stages write their raw artifacts
        # directly into the stage directory that owns them.
        layout = RunLayout.create(self.out, self.benchmark_id, self.run_id)
        cad_dir = layout.dir_for("CADArtifactManifest") / "cad"
        sim_dir = layout.dir_for("SimulationResult") / "raw"

        session = DesignSession(
            meta=ObjectMeta(object_id=new_id("SESSION"), producer=Stage.SESSION, design_id=design_id),
            artifact_dir=str(layout.root),
        )
        result = PipelineResult(session=session, run_dir=layout.root)

        def step(name: str, fn, produces: str, detail=lambda o: ""):
            try:
                obj = fn()
            except StageError as exc:
                result.stages.append(StageRecord(name, None, False, error=str(exc)))
                return None
            except Exception as exc:  # pragma: no cover - defensive
                result.stages.append(
                    StageRecord(name, None, False, error=f"{type(exc).__name__}: {exc}")
                )
                traceback.print_exc()
                return None
            result.objects[produces] = obj
            if hasattr(obj, "meta"):
                session.register(obj)
            result.stages.append(StageRecord(name, produces, True, detail=detail(obj)))
            return obj

        # -- Stage 01-04: intent and concept --------------------------------
        supplied = spec
        spec = step(
            "01 requirement interpreter",
            (
                (lambda: supplied)
                if supplied is not None
                else lambda: self.interpreter.run(request=request, clarifications=clarifications)
            ),
            "RequirementSpec",
            lambda o: (
                f"{len(o.requirements)} requirements, {len(o.quantitative)} quantitative"
                + (" [supplied handoff, Stage 01 bypassed]" if supplied is not None else "")
            ),
        )
        if spec is None:
            session.status = SessionStatus.BLOCKED
            return result

        mech = step(
            "02 mechanical architecture",
            lambda: MechanicalArchitectureGenerator().run(spec=spec),
            "MechanicalArchitecture",
            lambda o: (
                f"CONTRACT DEFICIENCY: {len(o.items)} blocking item(s)"
                if isinstance(o, Stage01ContractDeficiency)
                else f"{len(o.candidates)} candidates, selected '{o.selected_id}'"
                + (f", {len(o.contract_advisories)} advisory" if o.contract_advisories else "")
            ),
        )
        if mech is None or isinstance(mech, Stage01ContractDeficiency):
            # A typed deficiency stops the pipeline deliberately. Stage 02 refuses to
            # re-read the request, so there is nothing downstream can proceed from.
            if isinstance(mech, Stage01ContractDeficiency):
                result.objects["Stage01ContractDeficiency"] = mech
                result.objects.pop("MechanicalArchitecture", None)
            session.status = SessionStatus.BLOCKED
            return result

        prod = step(
            "03 product architecture",
            lambda: ProductArchitecturePlanner().run(spec=spec, mechanical=mech),
            "ProductArchitecture",
            lambda o: f"{len(o.regions)} product regions",
        )
        concept = step(
            "04 concept visualization",
            lambda: ConceptVisualizer().run(product=prod, mechanical=mech),
            "ConceptVisualization",
            lambda o: f"authoritative={o.authoritative}",
        )

        # -- Stage 05: engineering integration ------------------------------
        definition = step(
            "05 engineering integration",
            lambda: EngineeringIntegration(self.reasoner, self.budget).run(
                spec=spec, mechanical=mech, product=prod, concept=concept
            ),
            "CADReadyEngineeringDefinition",
            lambda o: (
                f"{o.iterations} iterations, {len(o.working_state.commitments)} commitments, "
                f"{len(o.working_state.problems)} problems, ready={o.readiness.ready}"
            ),
        )
        if definition is None:
            session.status = SessionStatus.BLOCKED
            return result

        # -- Stage 06-07: deterministic execution ---------------------------
        solved = step(
            "06 parametric solver",
            lambda: ParametricSolver().run(definition=definition),
            "SolvedDesign",
            lambda o: f"{o.status.value}, {len(o.parameters)} parameters",
        )
        manifest = None
        if solved is not None:
            manifest = step(
                "07 cad builder",
                lambda: CADBuilder(cad_dir).run(solved=solved, definition=definition),
                "CADArtifactManifest",
                lambda o: f"{o.status.value}, {len(o.parts)} parts",
            )

        # -- Stage 08-11: validation ----------------------------------------
        plan = sim = metrics = evaluation = None
        if solved is not None and manifest is not None:
            plan = step(
                "08 simulation plan",
                lambda: SimulationPlanBuilder(sim_dir).run(
                    spec=spec, solved=solved, manifest=manifest, definition=definition
                ),
                "SimulationPlan",
                lambda o: f"{len(o.tests)} tests",
            )
        if plan is not None:
            sim = step(
                "09 simulation runner",
                lambda: SimulationRunner(sim_dir).run(plan=plan, definition=definition),
                "SimulationResult",
                lambda o: ", ".join(f"{r.backend.value}:{r.status.value}" for r in o.results),
            )
            if sim is not None:
                metrics = step(
                    "10 metric extraction",
                    lambda: MetricExtraction().run(plan=plan, result=sim),
                    "MetricReport",
                    lambda o: f"{len(o.metrics)} metrics",
                )
        if metrics is not None:
            evaluation = step(
                "11 requirement evaluation",
                lambda: RequirementEvaluation().run(
                    spec=spec, metrics=metrics, definition=definition, plan=plan, result=sim
                ),
                "EvaluationReport",
                lambda o: f"overall={o.overall.value}, {len(o.failed)} failed",
            )

        # -- Stage 12: revision ---------------------------------------------
        directive = None
        if evaluation is not None:
            directive = step(
                "12 revision routing",
                lambda: RevisionRouting().run(evaluation=evaluation, definition=definition),
                "RevisionDirective",
                lambda o: f"restart={o.restart.value}",
            )

        # -- session bookkeeping --------------------------------------------
        session.current_iteration = 0
        session.iterations.append(
            IterationRecord(
                index=0,
                metric_summary={m.name: m.value for m in (metrics.metrics if metrics else [])},
                evaluation_summary=(
                    {o.requirement_id: o.status.value for o in evaluation.outcomes}
                    if evaluation
                    else {}
                ),
                outcome=evaluation.overall.value if evaluation else "not_evaluated",
                is_best=True,
                artifacts=[p.step_path or "" for p in (manifest.parts if manifest else [])],
            )
        )
        session.best_iteration = 0
        session.open_questions = [
            q for c in mech.candidates for q in c.open_questions
        ]
        if evaluation is None:
            session.status = SessionStatus.BLOCKED
        elif evaluation.overall == ReqStatus.PASS:
            session.status = SessionStatus.PASSED
        elif directive is not None and directive.restart != RestartStage.NONE:
            session.status = SessionStatus.FAILED
        else:
            session.status = SessionStatus.FAILED

        if persist:
            writer = RunArtifactWriter(layout, self.benchmark_id, self.tier, __version__)
            writer.write(result)
        return result
