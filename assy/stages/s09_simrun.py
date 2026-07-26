"""Stage 09 - Simulation Runner (MuJoCo).

Question: what did the simulator produce?

Records evidence without converting it into engineering conclusions. Simulator
instability must stay distinguishable from product failure (DOMAIN_SPECIFICATION
section 12). Raw trajectories go to disk; only compact deterministic summaries
travel in the domain object (Rule TOK-4).
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import ClassVar

import mujoco
import numpy as np

from assy.domain.common import ObjectMeta, Stage, new_id
from assy.domain.downstream import SimRunStatus, SimTestResult, SimulationPlan, SimulationResult
from assy.stages.base import PipelineStage

VELOCITY_LIMIT = 50.0  # m/s; beyond this the run is unstable, not informative


class SimulationRunner(PipelineStage):
    stage_id: ClassVar[Stage] = Stage.SIM_RUN
    question: ClassVar[str] = "What did the simulator produce?"
    produces: ClassVar[str] = "SimulationResult"

    def __init__(self, out_dir: str | Path = "out/sim"):
        self.out_dir = Path(out_dir)

    def _run_one(self, plan: SimulationPlan, test, model, data) -> SimTestResult:
        mujoco.mj_resetData(model, data)
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "lift")
        qadr = model.jnt_qposadr[jid]

        for _, value in test.initial_conditions.items():
            data.qpos[qadr] = value
        mujoco.mj_forward(model, data)

        if test.actuation:
            data.ctrl[0] = list(test.actuation.values())[0]
        else:
            data.ctrl[0] = data.qpos[qadr]  # hold command equals start: unpowered hold

        steps = int(test.duration_s / model.opt.timestep)
        rows: list[tuple[float, float, float]] = []
        status = SimRunStatus.COMPLETED
        diagnostics: list[str] = []
        events: list[str] = []
        peak_force = 0.0

        for _ in range(steps):
            mujoco.mj_step(model, data)
            height = float(data.qpos[qadr])
            vel = float(data.qvel[model.jnt_dofadr[jid]])
            force = float(abs(data.actuator_force[0])) if model.nu else 0.0
            peak_force = max(peak_force, force)
            rows.append((float(data.time), height, vel))
            if abs(vel) > VELOCITY_LIMIT or not np.isfinite(height):
                status = SimRunStatus.UNSTABLE
                diagnostics.append(f"velocity {vel:.1f} m/s exceeded stability limit")
                break

        traj = self.out_dir / f"{test.name}.csv"
        with traj.open("w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["time_s", "lift_m", "vel_m_s"])
            writer.writerows(rows)

        heights = [r[1] for r in rows] or [0.0]
        start_h, final_h = heights[0], heights[-1]
        # Settled value over the final 10% of the run. Peak-to-peak would report
        # servo overshoot as achieved travel, which is not what "travel" means.
        tail = heights[max(1, int(len(heights) * 0.9)) :] or [final_h]
        settled_h = sum(tail) / len(tail)
        summary = {
            "start_mm": round(start_h * 1000.0, 3),
            "final_mm": round(final_h * 1000.0, 3),
            "settled_mm": round(settled_h * 1000.0, 3),
            "max_mm": round(max(heights) * 1000.0, 3),
            "overshoot_mm": round((max(heights) - settled_h) * 1000.0, 3),
            "travel_settled_mm": round((settled_h - start_h) * 1000.0, 3),
            "travel_peak_to_peak_mm": round((max(heights) - min(heights)) * 1000.0, 3),
            "drift_mm": round(abs(final_h - start_h) * 1000.0, 3),
            "peak_actuator_force_n": round(peak_force, 3),
            "samples": float(len(rows)),
        }
        if summary["drift_mm"] > 1.0 and not test.actuation:
            events.append(f"platform drifted {summary['drift_mm']:.2f} mm while unpowered")

        return SimTestResult(
            test_id=test.id,
            status=status,
            simulator="mujoco",
            simulator_version=mujoco.__version__,
            duration_s=float(data.time),
            trajectory_path=str(traj),
            events=events,
            diagnostics=diagnostics,
            series_summary=summary,
        )

    def run(self, *, plan: SimulationPlan) -> SimulationResult:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        results: list[SimTestResult] = []
        if not plan.tests or plan.model_path is None:
            return SimulationResult(
                meta=ObjectMeta(object_id=new_id("SIMRES"), producer=self.stage_id),
                results=[],
                source_plan_id=plan.meta.object_id,
            )
        try:
            model = mujoco.MjModel.from_xml_path(str(plan.model_path))
            data = mujoco.MjData(model)
        except Exception as exc:
            for test in plan.tests:
                results.append(
                    SimTestResult(
                        test_id=test.id,
                        status=SimRunStatus.ERROR,
                        diagnostics=[f"model load failed: {exc}"],
                    )
                )
            return SimulationResult(
                meta=ObjectMeta(object_id=new_id("SIMRES"), producer=self.stage_id),
                results=results,
                source_plan_id=plan.meta.object_id,
            )

        for test in plan.tests:
            results.append(self._run_one(plan, test, model, data))

        return SimulationResult(
            meta=ObjectMeta(object_id=new_id("SIMRES"), producer=self.stage_id),
            results=results,
            source_plan_id=plan.meta.object_id,
        )
