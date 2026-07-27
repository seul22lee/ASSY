"""Stage 10 - Metric Extraction.

Question: what measurable engineering quantities were observed?

Extracts deterministic measurements from every backend and tags each with the
method and validity domain that produced it. It does not decide pass or fail
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
    ValidationBackend,
)
from assy.stages.base import PipelineStage

# observable -> (summary key, unit, method)
EXTRACTORS: dict[str, tuple[str, str, str]] = {
    # -- rigid-body motion and contact --
    "lid_angle_deg": ("lid_settled_deg", "deg", "settled lid hinge angle"),
    "input_torque_nmm": ("input_torque_nmm.peak_abs", "Nmm", "peak lid actuator torque"),
    "latch_contact_state": ("contact_fraction", "-", "fraction of the run in latch contact"),
    "retention_force_n": ("contact_force_n.peak_abs", "N", "peak hook/lip contact force"),
    "release_force_n": ("release_force_n.peak_abs", "Nmm", "peak beam actuator torque"),
    "engagement_event": ("engagement_events", "count", "hook/lip contact onsets"),
    "disengagement_event": ("disengagement_events", "count", "hook/lip contact losses"),
    "interference_event": ("contact_force_n.peak_abs", "N", "peak contact force during the swing"),
    # -- translating output --
    "platform_height_mm": ("settled_mm", "mm", "mean lift position over the final 10%"),
    "platform_travel_mm": ("travel_settled_mm", "mm", "settled minus start lift position"),
    "platform_overshoot_mm": ("overshoot_mm", "mm", "peak minus settled lift position"),
    "platform_drift_mm": ("drift_mm", "mm", "abs(final - start) lift position"),
    "peak_actuator_force_n": ("peak_actuator_force_n.peak_abs", "N", "peak actuator force"),
    # -- analytical compliant element --
    "beam_deflection_mm": ("beam_deflection_mm", "mm", "commanded beam deflection"),
    "peak_strain": ("peak_strain", "-", "1.5*t*y/L^2 at the beam root"),
    "peak_stress_mpa": ("peak_stress_mpa", "MPa", "E * peak strain, linear elastic"),
    "insertion_force_n": ("insertion_force_n", "N", "P(mu+tan a)/(1-mu tan a), lead face"),
    "retention_force_n_analytical": ("retention_force_n", "N", "same relation, retention face"),
    "strain_margin": ("strain_margin", "-", "allowable minus peak strain"),
}

# Observables whose analytical reading must not be confused with the contact one.
ANALYTICAL_ALIASES = {"retention_force_n": "retention_force_n_analytical"}


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
            if test.backend is ValidationBackend.MUJOCO and "platform_height_mm" in observables:
                observables.append("platform_travel_mm")

            for obs in observables:
                key_name = obs
                if test.backend is ValidationBackend.ANALYTICAL:
                    key_name = ANALYTICAL_ALIASES.get(obs, obs)
                spec = EXTRACTORS.get(key_name)
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
                        method=f"{res.backend.value}: {method}",
                        source_test=test.id,
                        entities=[test.phenomenon],
                        valid=valid,
                        invalidity_reason=reason,
                    )
                )

        return MetricReport(
            meta=ObjectMeta(object_id=new_id("METRICS"), producer=self.stage_id),
            metrics=metrics,
            source_result_id=result.meta.object_id,
        )
