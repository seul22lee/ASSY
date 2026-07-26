"""Stage 10 - Metric Extraction.

Question: what measurable engineering quantities were observed?

Extracts deterministic measurements. It does not decide pass or fail
(DOMAIN_SPECIFICATION section 13).
"""

from __future__ import annotations

from typing import ClassVar

from assy.domain.common import ObjectMeta, Stage, new_id
from assy.domain.downstream import (
    Metric,
    MetricReport,
    SimRunStatus,
    SimulationPlan,
    SimulationResult,
)
from assy.stages.base import PipelineStage

# Observable -> (summary key, unit, extraction method)
EXTRACTORS: dict[str, tuple[str, str, str]] = {
    "platform_height_mm": ("settled_mm", "mm", "mean lift position over the final 10% of the run"),
    "platform_travel_mm": ("travel_settled_mm", "mm", "settled lift position minus start position"),
    "platform_overshoot_mm": ("overshoot_mm", "mm", "peak lift position minus settled position"),
    "platform_drift_mm": ("drift_mm", "mm", "abs(final - start) of lift joint position"),
    "peak_actuator_force_n": ("peak_actuator_force_n", "N", "max abs actuator force"),
}


class MetricExtraction(PipelineStage):
    stage_id: ClassVar[Stage] = Stage.METRICS
    question: ClassVar[str] = "What measurable physical quantities were observed?"
    produces: ClassVar[str] = "MetricReport"

    def run(self, *, plan: SimulationPlan, result: SimulationResult) -> MetricReport:
        by_id = {t.id: t for t in plan.tests}
        metrics: list[Metric] = []

        for res in result.results:
            test = by_id.get(res.test_id)
            if test is None:
                continue
            valid = res.status == SimRunStatus.COMPLETED
            reason = None if valid else f"run status {res.status.value}"

            observables = list(test.observables)
            if test.name == "full_travel":
                observables.append("platform_travel_mm")

            for obs in observables:
                spec = EXTRACTORS.get(obs)
                if spec is None:
                    continue
                key, unit, method = spec
                if key not in res.series_summary:
                    continue
                metrics.append(
                    Metric(
                        id=new_id("M"),
                        name=f"{test.name}.{obs}",
                        value=res.series_summary[key],
                        unit=unit,
                        method=method,
                        source_test=test.id,
                        entities=["platform"],
                        valid=valid,
                        invalidity_reason=reason,
                    )
                )

        return MetricReport(
            meta=ObjectMeta(object_id=new_id("METRICS"), producer=self.stage_id),
            metrics=metrics,
            source_result_id=result.meta.object_id,
        )
