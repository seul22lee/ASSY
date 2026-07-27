"""Stage 08 - Simulation Plan Builder.

Question: how should the generated design be physically tested?

Test planning is driven by the **mechanism semantics present in the engineering
definition** - the engineering roles - never by the presence of a particular
entity. A hinged body gets swing and engagement tests because it is hinged.

Each test names the backend competent for its phenomenon and the validity domain
of that backend's answers. Rigid-body contact goes to MuJoCo; compliant-element
behaviour goes to closed-form analysis.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import ClassVar

from assy.domain.common import ObjectMeta, Stage, new_id
from assy.domain.downstream import (
    CADArtifactManifest,
    SimTest,
    SimulationPlan,
    SolvedDesign,
    ValidationBackend,
)
from assy.domain.engineering import CADReadyEngineeringDefinition
from assy.domain.upstream import RequirementSpec
from assy.knowledge import testplan
from assy.stages.base import PipelineStage
from assy.validation import mjcf

# Actuation and initial state per phenomenon. Keyed on the phenomenon under test,
# using the semantic joint names the model builder exposes.
LATCH_SETUP: dict[str, tuple[dict[str, float], dict[str, float]]] = {
    # phenomenon: (initial_conditions, actuation)
    # Beam flex is negative outward - the direction engagement pushes the hook.
    "closing_motion_and_engagement": ({"lid_hinge": 55.0, "beam_flex": 0.0}, {"lid_drive": -1.0}),
    "retention_under_load": ({"lid_hinge": 0.0, "beam_flex": 0.0}, {"lid_drive": 45.0}),
    "release_actuation": ({"lid_hinge": 0.0, "beam_flex": 0.0}, {"beam_release": -25.0, "lid_drive": 35.0}),
    "reopening_clearance": ({"lid_hinge": 0.0, "beam_flex": -25.0}, {"beam_release": -25.0, "lid_drive": 100.0}),
}


class SimulationPlanBuilder(PipelineStage):
    stage_id: ClassVar[Stage] = Stage.SIM_PLAN
    question: ClassVar[str] = "How should the generated design be physically tested?"
    produces: ClassVar[str] = "SimulationPlan"

    def __init__(self, out_dir: str | Path = "out/sim"):
        self.out_dir = Path(out_dir)

    def _payload(self, spec: RequirementSpec) -> float:
        req = next((r for r in spec.requirements if r.target and r.target.unit in ("kg", "g")), None)
        if req is None or req.target is None:
            return 1.0
        return req.target.value if req.target.unit == "kg" else req.target.value / 1000.0

    def run(
        self,
        *,
        spec: RequirementSpec,
        solved: SolvedDesign,
        manifest: CADArtifactManifest,
        definition: CADReadyEngineeringDefinition,
    ) -> SimulationPlan:
        self.out_dir.mkdir(parents=True, exist_ok=True)

        model = mjcf.build_for(definition, self._payload(spec))
        model_path = None
        limitations: list[str] = []
        if model is not None:
            model_path = self.out_dir / "model.xml"
            model_path.write_text(model.xml)
            limitations = list(model.limitations)

        rules = testplan.applicable_rules(definition.working_state)
        tests: list[SimTest] = []
        stroke_m = (
            definition.working_state.find_subject("platform.travel_envelope").value * 0.001
            if definition.working_state.find_subject("platform.travel_envelope")
            else 0.09
        )

        for rule, subject in rules:
            if rule.backend is ValidationBackend.MUJOCO and model is None:
                continue

            initial: dict[str, float] = {}
            actuation: dict[str, float] = {}
            if rule.backend is ValidationBackend.MUJOCO and model is not None:
                if model.kind == "latch":
                    # LATCH_SETUP is authored in degrees for readability, but MuJoCo
                    # qpos and position-actuator ctrl are radians at runtime whatever
                    # the compiler's angle setting. Convert here, once.
                    deg_initial, deg_actuation = LATCH_SETUP.get(rule.phenomenon, ({}, {}))
                    initial = {k: math.radians(v) for k, v in deg_initial.items()}
                    actuation = {k: math.radians(v) for k, v in deg_actuation.items()}
                elif model.kind == "lift":
                    if rule.phenomenon == "powered_travel":
                        initial, actuation = {"lift": 0.0}, {"lift_drive": stroke_m}
                    elif rule.phenomenon == "unpowered_hold":
                        initial, actuation = {"lift": stroke_m * 0.5}, {}

            served = [
                r.id
                for r in spec.requirements
                if r.kind.value in ("functional", "performance", "safety", "usability")
            ]
            tests.append(
                SimTest(
                    id=new_id("T"),
                    name=rule.name,
                    backend=rule.backend,
                    phenomenon=rule.phenomenon,
                    validity_domain=list(rule.validity_domain),
                    serves_requirements=served,
                    duration_s=rule.duration_s,
                    timestep_s=0.001 if (model and model.kind == "latch") else 0.002,
                    actuation=actuation,
                    initial_conditions=initial,
                    observables=list(rule.observables),
                    termination="time",
                    validity_conditions=["no solver warnings", "no unbounded velocity"],
                )
            )

        if any(t.backend is ValidationBackend.ANALYTICAL for t in tests) and any(
            t.backend is ValidationBackend.MUJOCO for t in tests
        ):
            limitations.append(
                "compliant retention requires BOTH backends: neither rigid-body contact "
                "nor closed-form beam analysis is sufficient alone"
            )

        return SimulationPlan(
            meta=ObjectMeta(object_id=new_id("SIMPLAN"), producer=self.stage_id),
            tests=tests,
            model_path=str(model_path) if model_path else None,
            contact_assumptions=dict(model.notes) if model else {},
            modelling_limitations=limitations,
            source_manifest_id=manifest.meta.object_id,
        )
