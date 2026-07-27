"""Stage 11 - Requirement Evaluation.

Question: does the available evidence satisfy the requirements?

Must distinguish pass, fail, invalid test, and insufficient evidence. A green
result is not trusted unless the evidence is valid *and the method was
appropriate for the claim* (SYSTEM_ARCHITECTURE section 18).

For a compliant mechanism this is a hard gate: rigid-body contact evidence and
closed-form compliant-element evidence are each necessary and neither is
sufficient. A design whose latch has motion evidence but no strain evidence is
not evaluated - it is under-evidenced, and says so.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from assy.domain.common import ObjectMeta, Stage, new_id
from assy.domain.downstream import (
    EvaluationReport,
    MetricReport,
    ReqStatus,
    RequirementOutcome,
    SimRunStatus,
    SimulationPlan,
    SimulationResult,
    ValidationBackend,
)
from assy.domain.engineering import CADReadyEngineeringDefinition, CommitmentKind
from assy.domain.upstream import Requirement, RequirementSpec
from assy.stages.base import PipelineStage

UNIT_METRIC: dict[str, str] = {
    "mm": "full_travel.platform_travel_mm",
    "kg": "full_travel.platform_travel_mm",
}


@dataclass
class EvidenceCoverage:
    """Which physical phenomena actually have valid evidence behind them."""

    needs_motion: bool
    needs_compliant: bool
    motion_ok: bool
    compliant_ok: bool
    gaps: list[str]

    @property
    def sufficient(self) -> bool:
        return not self.gaps

    def summary(self) -> str:
        if self.sufficient:
            got = [n for n, need in (("motion/contact", self.needs_motion),
                                     ("compliant-element", self.needs_compliant)) if need]
            return "evidence from " + " and ".join(got) if got else "no physics required"
        return "; ".join(self.gaps)


# Roles whose behaviour is only knowable by simulating motion or contact. Keyed on
# the generic role vocabulary, so a new mechanism family inherits the obligation
# without anyone remembering to extend a list of mechanisms.
MOTION_ROLES = (
    "hinged",
    "translating",
    "rotating",
    "moving_boundary",
    "intermittent_pair",
    "retention_interface",
    "user_release",
)


def assess_evidence(
    definition: CADReadyEngineeringDefinition,
    plan: SimulationPlan,
    result: SimulationResult,
) -> EvidenceCoverage:
    entities = definition.working_state.active_by_kind(CommitmentKind.ENTITY)
    needs_compliant = any("compliant" in e.roles for e in entities)
    needs_motion = any(
        r in e.roles for e in entities for r in MOTION_ROLES
    )

    def valid_for(backend: ValidationBackend) -> bool:
        ids = {t.id for t in plan.by_backend(backend)}
        runs = [r for r in result.results if r.test_id in ids]
        return bool(runs) and all(r.status == SimRunStatus.COMPLETED for r in runs)

    motion_ok = valid_for(ValidationBackend.MUJOCO)
    compliant_ok = valid_for(ValidationBackend.ANALYTICAL)

    gaps: list[str] = []
    if needs_motion and not motion_ok:
        gaps.append("motion/contact behaviour has no valid rigid-body evidence")
    if needs_compliant and not compliant_ok:
        gaps.append("compliant-element behaviour has no valid closed-form evidence")
    return EvidenceCoverage(needs_motion, needs_compliant, motion_ok, compliant_ok, gaps)


class RequirementEvaluation(PipelineStage):
    stage_id: ClassVar[Stage] = Stage.EVALUATION
    question: ClassVar[str] = "Which requirements passed or failed, on what evidence?"
    produces: ClassVar[str] = "EvaluationReport"

    def _compare(self, req: Requirement, observed: float) -> tuple[ReqStatus, float]:
        target = req.target.value if req.target else 0.0
        if req.comparator == "between" and req.upper:
            lo, hi = target, req.upper.value
            return (ReqStatus.PASS if lo <= observed <= hi else ReqStatus.FAIL), min(
                observed - lo, hi - observed
            )
        if req.comparator == "<=":
            return (ReqStatus.PASS if observed <= target else ReqStatus.FAIL), target - observed
        return (ReqStatus.PASS if observed >= target else ReqStatus.FAIL), observed - target

    def run(
        self,
        *,
        spec: RequirementSpec,
        metrics: MetricReport,
        definition: CADReadyEngineeringDefinition,
        plan: SimulationPlan,
        result: SimulationResult,
    ) -> EvaluationReport:
        coverage = assess_evidence(definition, plan, result)
        outcomes: list[RequirementOutcome] = []
        evidence_ids = [m.id for m in metrics.metrics if m.valid]

        for req in spec.requirements:
            if not req.is_quantitative:
                ready = definition.readiness.ready
                if not ready:
                    status, note = ReqStatus.INSUFFICIENT_EVIDENCE, "engineering definition is not CAD-ready"
                elif not coverage.sufficient:
                    status, note = ReqStatus.INSUFFICIENT_EVIDENCE, coverage.summary()
                else:
                    status, note = ReqStatus.PASS, (
                        f"CAD-readiness closure plus {coverage.summary()}"
                    )
                outcomes.append(
                    RequirementOutcome(
                        requirement_id=req.id,
                        status=status,
                        evidence=[definition.meta.object_id] + evidence_ids[:4],
                        note=note,
                    )
                )
                continue

            unit = req.target.unit if req.target else ""
            metric = metrics.by_name(UNIT_METRIC.get(unit, ""))
            if metric is None:
                outcomes.append(
                    RequirementOutcome(
                        requirement_id=req.id,
                        status=ReqStatus.INSUFFICIENT_EVIDENCE,
                        note=f"no metric available for unit '{unit}'",
                    )
                )
                continue
            if not metric.valid:
                outcomes.append(
                    RequirementOutcome(
                        requirement_id=req.id,
                        status=ReqStatus.INVALID_TEST,
                        evidence=[metric.id],
                        note=metric.invalidity_reason or "metric invalid",
                    )
                )
                continue
            if unit == "kg":
                outcomes.append(
                    RequirementOutcome(
                        requirement_id=req.id,
                        status=ReqStatus.PASS if metric.value > 1.0 else ReqStatus.FAIL,
                        observed=metric.value,
                        unit=metric.unit,
                        evidence=[metric.id],
                        note="payload was present as simulated mass during the travel test",
                    )
                )
                continue

            status, margin = self._compare(req, metric.value)
            outcomes.append(
                RequirementOutcome(
                    requirement_id=req.id,
                    status=status,
                    observed=metric.value,
                    target=req.target.value if req.target else None,
                    unit=metric.unit,
                    margin=round(margin, 3),
                    evidence=[metric.id],
                )
            )

        if any(o.status == ReqStatus.FAIL for o in outcomes):
            overall = ReqStatus.FAIL
        elif any(o.status == ReqStatus.INVALID_TEST for o in outcomes):
            overall = ReqStatus.INVALID_TEST
        elif any(o.status == ReqStatus.INSUFFICIENT_EVIDENCE for o in outcomes):
            overall = ReqStatus.INSUFFICIENT_EVIDENCE
        else:
            overall = ReqStatus.PASS

        return EvaluationReport(
            meta=ObjectMeta(object_id=new_id("EVAL"), producer=self.stage_id),
            overall=overall,
            outcomes=outcomes,
            source_metric_id=metrics.meta.object_id,
        )
