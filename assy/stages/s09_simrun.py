"""Stage 09 - Simulation Runner.

Question: what did each validation backend produce?

Dispatches every test to the backend its phenomenon requires and records evidence
without converting it into engineering conclusions. Backend instability must stay
distinguishable from product failure. Raw series go to disk; only compact
deterministic summaries travel in the domain object (Rule TOK-4).
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import ClassVar

import mujoco
import numpy as np

from assy.domain.common import ObjectMeta, Stage, new_id
from assy.domain.downstream import (
    SimRunStatus,
    SimTest,
    SimTestResult,
    SimulationPlan,
    SimulationResult,
    ValidationBackend,
)
from assy.domain.engineering import CADReadyEngineeringDefinition
from assy.stages.base import PipelineStage
from assy.validation import analytical

VELOCITY_LIMIT = 500.0
"""Runaway threshold, not a dynamics limit. Real snap-through reaches ~50 rad/s."""

# Observable -> (mjcf entity kind, name). Resolved generically against the model.
JOINT_OBSERVABLES = {
    "lid_angle_deg": ("joint", "lid_hinge", 180.0 / np.pi),
    "beam_deflection_deg": ("joint", "beam_flex", 180.0 / np.pi),
    "platform_height_mm": ("joint", "lift", 1000.0),
    "platform_drift_mm": ("joint", "lift", 1000.0),
    "platform_overshoot_mm": ("joint", "lift", 1000.0),
}
ACTUATOR_OBSERVABLES = {
    "input_torque_nmm": ("lid_drive", 1000.0),
    "release_force_n": ("beam_release", 1000.0),
    "peak_actuator_force_n": ("lift_drive", 1.0),
}


class SimulationRunner(PipelineStage):
    stage_id: ClassVar[Stage] = Stage.SIM_RUN
    question: ClassVar[str] = "What did each validation backend produce?"
    produces: ClassVar[str] = "SimulationResult"

    def __init__(self, out_dir: str | Path = "out/sim"):
        self.out_dir = Path(out_dir)

    # -- MuJoCo -----------------------------------------------------------
    def _run_mujoco(self, test: SimTest, model, data) -> SimTestResult:
        mujoco.mj_resetData(model, data)

        def jid(name: str) -> int | None:
            i = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
            return None if i < 0 else i

        def aid(name: str) -> int | None:
            i = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, name)
            return None if i < 0 else i

        for joint, value in test.initial_conditions.items():
            i = jid(joint)
            if i is not None:
                data.qpos[model.jnt_qposadr[i]] = value
        mujoco.mj_forward(model, data)
        for act, value in test.actuation.items():
            i = aid(act)
            if i is not None:
                data.ctrl[i] = value

        hook = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "hook")
        lip = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "lid_lip")
        rib = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "lid_rib")

        series: dict[str, list[float]] = {"time_s": []}
        tracked_joints = {
            name: jid(spec[1])
            for name, spec in JOINT_OBSERVABLES.items()
            if jid(spec[1]) is not None
        }
        tracked_acts = {
            name: aid(spec[0])
            for name, spec in ACTUATOR_OBSERVABLES.items()
            if aid(spec[0]) is not None
        }
        for name in list(tracked_joints) + list(tracked_acts):
            series[name] = []
        series["latch_contact_state"] = []
        series["contact_force_n"] = []

        steps = int(test.duration_s / model.opt.timestep)
        status = SimRunStatus.COMPLETED
        diagnostics: list[str] = []
        events: list[str] = []
        prev_contact = 0

        for _ in range(steps):
            mujoco.mj_step(model, data)
            series["time_s"].append(float(data.time))

            for name, i in tracked_joints.items():
                scale = JOINT_OBSERVABLES[name][2]
                series[name].append(float(data.qpos[model.jnt_qposadr[i]]) * scale)
            for name, i in tracked_acts.items():
                scale = ACTUATOR_OBSERVABLES[name][1]
                series[name].append(float(data.actuator_force[i]) * scale)

            contact, force_mag = 0, 0.0
            for c in range(data.ncon):
                con = data.contact[c]
                pair = {con.geom1, con.geom2}
                if hook >= 0 and hook in pair and (lip in pair or rib in pair):
                    contact = 1
                    f = np.zeros(6)
                    mujoco.mj_contactForce(model, data, c, f)
                    force_mag = max(force_mag, float(np.linalg.norm(f[:3])))
            series["latch_contact_state"].append(float(contact))
            series["contact_force_n"].append(force_mag)

            if contact and not prev_contact:
                events.append(f"engagement at t={data.time:.3f}s")
            elif prev_contact and not contact:
                events.append(f"disengagement at t={data.time:.3f}s")
            prev_contact = contact

            # Divergence is detected from the solver's own signals plus finiteness.
            # A bare velocity threshold misreads legitimately fast dynamics - a
            # snapping beam genuinely reaches tens of rad/s - as instability.
            warned = [
                int(w)
                for w in (
                    mujoco.mjtWarning.mjWARN_BADQPOS,
                    mujoco.mjtWarning.mjWARN_BADQVEL,
                    mujoco.mjtWarning.mjWARN_BADQACC,
                    mujoco.mjtWarning.mjWARN_BADCTRL,
                )
                if data.warning[int(w)].number > 0
            ]
            if warned or not np.all(np.isfinite(data.qpos)):
                status = SimRunStatus.UNSTABLE
                diagnostics.append(f"solver divergence (warnings={warned})")
                break
            if np.max(np.abs(data.qvel)) > VELOCITY_LIMIT:
                status = SimRunStatus.UNSTABLE
                diagnostics.append(
                    f"|qvel| exceeded {VELOCITY_LIMIT} - runaway rather than fast motion"
                )
                break

        path = self.out_dir / f"{test.name}.csv"
        keys = [k for k in series if series[k]]
        with path.open("w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(keys)
            writer.writerows(zip(*[series[k] for k in keys]))

        summary: dict[str, float] = {"samples": float(len(series["time_s"]))}
        for key in keys:
            if key == "time_s":
                continue
            values = series[key]
            tail = values[max(1, int(len(values) * 0.9)) :] or values
            settled = sum(tail) / len(tail)
            summary[f"{key}.settled"] = round(settled, 4)
            summary[f"{key}.max"] = round(max(values), 4)
            summary[f"{key}.min"] = round(min(values), 4)
            summary[f"{key}.peak_abs"] = round(max(abs(v) for v in values), 4)
            if key.startswith("platform_height"):
                summary["settled_mm"] = round(settled, 3)
                summary["travel_settled_mm"] = round(settled - values[0], 3)
                summary["overshoot_mm"] = round(max(values) - settled, 3)
                summary["drift_mm"] = round(abs(values[-1] - values[0]), 3)
            if key == "lid_angle_deg":
                summary["lid_start_deg"] = round(values[0], 3)
                summary["lid_settled_deg"] = round(settled, 3)
                summary["lid_swing_deg"] = round(max(values) - min(values), 3)
        summary["engagement_events"] = float(sum(1 for e in events if "engagement at" in e))
        summary["disengagement_events"] = float(sum(1 for e in events if "disengagement" in e))
        summary["contact_fraction"] = round(
            sum(series["latch_contact_state"]) / max(1, len(series["latch_contact_state"])), 4
        )

        return SimTestResult(
            test_id=test.id,
            backend=ValidationBackend.MUJOCO,
            status=status,
            simulator="mujoco",
            simulator_version=mujoco.__version__,
            duration_s=float(data.time),
            trajectory_path=str(path),
            events=events[:12],
            diagnostics=diagnostics,
            series_summary=summary,
        )

    # -- dispatch ---------------------------------------------------------
    def run(
        self, *, plan: SimulationPlan, definition: CADReadyEngineeringDefinition
    ) -> SimulationResult:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        results: list[SimTestResult] = []

        analytical_tests = plan.by_backend(ValidationBackend.ANALYTICAL)
        mujoco_tests = plan.by_backend(ValidationBackend.MUJOCO)

        for test in analytical_tests:
            results.append(analytical.run_test(test, definition))

        if mujoco_tests:
            if plan.model_path is None:
                for test in mujoco_tests:
                    results.append(
                        SimTestResult(
                            test_id=test.id,
                            backend=ValidationBackend.MUJOCO,
                            status=SimRunStatus.ERROR,
                            diagnostics=["no MJCF model was produced for this design"],
                        )
                    )
            else:
                try:
                    model = mujoco.MjModel.from_xml_path(str(plan.model_path))
                    data = mujoco.MjData(model)
                except Exception as exc:
                    for test in mujoco_tests:
                        results.append(
                            SimTestResult(
                                test_id=test.id,
                                backend=ValidationBackend.MUJOCO,
                                status=SimRunStatus.ERROR,
                                diagnostics=[f"model load failed: {exc}"],
                            )
                        )
                else:
                    for test in mujoco_tests:
                        results.append(self._run_mujoco(test, model, data))

        return SimulationResult(
            meta=ObjectMeta(object_id=new_id("SIMRES"), producer=self.stage_id),
            results=results,
            source_plan_id=plan.meta.object_id,
        )
