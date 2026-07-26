"""Stage 08 - Simulation Plan Builder.

Question: how should the generated design be physically tested?

Tests are derived from requirements and critical characteristics, never invented.
Every test traces to at least one requirement (DOMAIN_SPECIFICATION section 11).
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from assy.domain.common import ObjectMeta, Stage, new_id
from assy.domain.downstream import CADArtifactManifest, SimTest, SimulationPlan, SolvedDesign
from assy.domain.engineering import CADReadyEngineeringDefinition, CommitmentKind
from assy.domain.upstream import RequirementKind, RequirementSpec
from assy.stages.base import PipelineStage

MJCF_TEMPLATE = """<mujoco model="assy_design">
  <compiler angle="degree" coordinate="local"/>
  <option timestep="{timestep}" gravity="0 0 -9.81" integrator="implicitfast"/>
  <default>
    <geom rgba="0.7 0.7 0.75 1" friction="{friction} 0.005 0.0001"/>
    <joint damping="{damping}"/>
  </default>
  <worldbody>
    <light pos="0 0 {light_z}" dir="0 0 -1"/>
    <geom name="ground" type="plane" size="1 1 0.01" rgba="0.3 0.3 0.3 1"/>
    <body name="housing" pos="0 0 {housing_z}">
      <geom name="housing_base" type="box" size="{hw} {hd} {wall}"/>
      <geom name="housing_left"  type="box" size="{wall} {hd} {hh}" pos="-{hw} 0 {hh}"/>
      <geom name="housing_right" type="box" size="{wall} {hd} {hh}" pos="{hw} 0 {hh}"/>
    </body>
    <body name="platform" pos="0 0 {platform_z}">
      <joint name="lift" type="slide" axis="0 0 1" range="0 {stroke}" damping="{damping}"
             frictionloss="{frictionloss}"/>
      <geom name="platform_plate" type="box" size="{pw} {pd} {pt}" mass="{platform_mass}"/>
      <body name="payload" pos="0 0 {payload_z}">
        <geom name="payload_mass" type="box" size="{pw2} {pd2} {payload_h}" mass="{payload_mass}" rgba="0.8 0.4 0.2 1"/>
      </body>
    </body>
  </worldbody>
  <actuator>
    <position name="lift_drive" joint="lift" kp="{kp}" ctrlrange="0 {stroke}" forcerange="-{fmax} {fmax}"/>
  </actuator>
</mujoco>
"""


class SimulationPlanBuilder(PipelineStage):
    stage_id: ClassVar[Stage] = Stage.SIM_PLAN
    question: ClassVar[str] = "How should the generated design be physically tested?"
    produces: ClassVar[str] = "SimulationPlan"

    def __init__(self, out_dir: str | Path = "out/sim"):
        self.out_dir = Path(out_dir)

    def run(
        self,
        *,
        spec: RequirementSpec,
        solved: SolvedDesign,
        manifest: CADArtifactManifest,
        definition: CADReadyEngineeringDefinition,
    ) -> SimulationPlan:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        p = solved.as_dict()
        state = definition.working_state

        # Only model what the design actually declares. Fabricating a translating
        # body for a product that has none would produce evidence about a machine
        # that does not exist.
        mover = next(
            (
                e
                for e in state.active_by_kind(CommitmentKind.ENTITY)
                if "translating" in e.roles
                and state.find_subject(f"{e.subject}.travel_envelope") is not None
            ),
            None,
        )
        if mover is None:
            return SimulationPlan(
                meta=ObjectMeta(object_id=new_id("SIMPLAN"), producer=self.stage_id),
                tests=[],
                model_path=None,
                contact_assumptions={},
                source_manifest_id=manifest.meta.object_id,
            )

        stroke_mm = p.get(f"{mover.subject}.travel_envelope", 90.0)
        stroke_m = stroke_mm / 1000.0
        hw = p.get("housing.internal_width", 110.0) / 2000.0
        hd = p.get("housing.internal_depth", 90.0) / 2000.0
        hh = p.get("housing.internal_height", 120.0) / 2000.0
        wall = p.get("housing.wall_thickness", 2.4) / 1000.0

        payload_req = next(
            (r for r in spec.requirements if r.target and r.target.unit in ("kg", "g")), None
        )
        payload_kg = 1.0
        if payload_req and payload_req.target:
            payload_kg = (
                payload_req.target.value
                if payload_req.target.unit == "kg"
                else payload_req.target.value / 1000.0
            )

        # The simulation must represent the engineering commitments, not a generic
        # positioner. A self-locking drive holds its load when unpowered, so it is
        # modelled as joint friction exceeding the payload weight; a back-driving
        # drive is modelled as nearly free. Reading this from the commitment keeps
        # the experiment honest about what the design actually claims.
        backdrive = definition.working_state.find_subject("lift_screw.backdrive_behaviour")
        self_locking = bool(backdrive.value) if backdrive is not None else False
        weight_n = (payload_kg + 0.08) * 9.81
        frictionloss = round(weight_n * 1.5, 3) if self_locking else 0.05
        kp = round(max(3000.0, frictionloss * 400.0), 1)
        fmax = round(max(300.0, frictionloss * 20.0), 1)

        xml = MJCF_TEMPLATE.format(
            timestep=0.002,
            friction=0.35,
            damping=2.0,
            frictionloss=frictionloss,
            light_z=hh * 4,
            housing_z=wall,
            hw=hw,
            hd=hd,
            hh=hh,
            wall=wall,
            platform_z=wall * 2 + 0.01,
            stroke=stroke_m,
            pw=max(hw - 0.004, 0.01),
            pd=max(hd - 0.004, 0.01),
            pt=0.003,
            pw2=max(hw / 2, 0.01),
            pd2=max(hd / 2, 0.01),
            payload_h=0.015,
            payload_z=0.021,
            platform_mass=0.08,
            payload_mass=payload_kg,
            kp=kp,
            fmax=fmax,
        )
        model_path = self.out_dir / "model.xml"
        model_path.write_text(xml)

        travel_reqs = [
            r.id for r in spec.requirements if r.target and r.target.unit == "mm"
        ]
        hold_reqs = [
            r.id
            for r in spec.requirements
            if r.kind in (RequirementKind.SAFETY, RequirementKind.PERFORMANCE)
        ]

        tests = [
            SimTest(
                id=new_id("T"),
                name="full_travel",
                serves_requirements=travel_reqs,
                duration_s=4.0,
                actuation={"lift_drive": stroke_m},
                initial_conditions={"lift": 0.0},
                observables=["platform_height_mm", "platform_overshoot_mm", "peak_actuator_force_n"],
                termination="time",
                validity_conditions=["no solver warnings", "no unbounded velocity"],
            ),
            SimTest(
                id=new_id("T"),
                name="hold_under_load",
                serves_requirements=hold_reqs,
                duration_s=3.0,
                actuation={},  # unpowered: does the design hold position?
                initial_conditions={"lift": stroke_m * 0.5},
                observables=["platform_drift_mm", "platform_height_mm"],
                termination="time",
                validity_conditions=["no solver warnings"],
            ),
        ]

        return SimulationPlan(
            meta=ObjectMeta(object_id=new_id("SIMPLAN"), producer=self.stage_id),
            tests=tests,
            model_path=str(model_path),
            contact_assumptions={
                "friction": 0.35,
                "timestep": 0.002,
                "joint_frictionloss_n": frictionloss,
                "self_locking_modelled": float(self_locking),
            },
            source_manifest_id=manifest.meta.object_id,
        )
