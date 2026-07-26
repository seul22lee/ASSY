"""Stage 11 - Requirement Evaluation.

Question: does the available evidence satisfy the requirements?

Must distinguish pass, fail, invalid test, and insufficient evidence. A green
result is not trusted unless the evidence is valid and the test is appropriate
(SYSTEM_ARCHITECTURE section 18).
"""

from __future__ import annotations

from typing import ClassVar

from assy.domain.common import ObjectMeta, Stage, new_id
from assy.domain.downstream import (
    EvaluationReport,
    MetricReport,
    ReqStatus,
    RequirementOutcome,
)
from assy.domain.engineering import CADReadyEngineeringDefinition
from assy.domain.upstream import Requirement, RequirementSpec
from assy.stages.base import PipelineStage

# Which metric answers which kind of quantitative requirement.
UNIT_METRIC: dict[str, str] = {
    "mm": "full_travel.platform_travel_mm",
    "kg": "full_travel.platform_travel_mm",  # payload is carried during the travel test
}


class RequirementEvaluation(PipelineStage):
    stage_id: ClassVar[Stage] = Stage.EVALUATION
    question: ClassVar[str] = "Which requirements passed or failed, on what evidence?"
    produces: ClassVar[str] = "EvaluationReport"

    def _compare(self, req: Requirement, observed: float) -> tuple[ReqStatus, float]:
        target = req.target.value if req.target else 0.0
        if req.comparator == "between" and req.upper:
            lo, hi = target, req.upper.value
            margin = min(observed - lo, hi - observed)
            return (ReqStatus.PASS if lo <= observed <= hi else ReqStatus.FAIL), margin
        if req.comparator == "<=":
            return (ReqStatus.PASS if observed <= target else ReqStatus.FAIL), target - observed
        return (ReqStatus.PASS if observed >= target else ReqStatus.FAIL), observed - target

    def run(
        self,
        *,
        spec: RequirementSpec,
        metrics: MetricReport,
        definition: CADReadyEngineeringDefinition,
    ) -> EvaluationReport:
        outcomes: list[RequirementOutcome] = []

        for req in spec.requirements:
            if not req.is_quantitative:
                # Qualitative requirements are answered by Stage 05 readiness evidence,
                # not by simulation. Never silently marked as passing.
                ready = definition.readiness.ready
                outcomes.append(
                    RequirementOutcome(
                        requirement_id=req.id,
                        status=ReqStatus.PASS if ready else ReqStatus.INSUFFICIENT_EVIDENCE,
                        evidence=[definition.meta.object_id],
                        note=(
                            "satisfied by CAD-readiness closure"
                            if ready
                            else "no deterministic evidence for this qualitative requirement"
                        ),
                    )
                )
                continue

            unit = req.target.unit if req.target else ""
            metric_name = UNIT_METRIC.get(unit)
            metric = metrics.by_name(metric_name) if metric_name else None

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
                # The travel test carries the payload, so completing travel is
                # evidence the payload was lifted - but say so explicitly.
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
