"""Stage 06 - Parametric Solver.

Question: what numerical values satisfy the declared engineering constraints?

Deterministic by contract (Rule L-2). The solver may never invent topology or
change a mechanism - it only resolves declared parameters and reports constraint
status, including explicit failure (DOMAIN_SPECIFICATION section 9).
"""

from __future__ import annotations

from typing import ClassVar

from assy.domain.common import ObjectMeta, Stage, new_id
from assy.domain.downstream import (
    ConstraintOutcome,
    SolvedDesign,
    SolvedParameter,
    SolveStatus,
)
from assy.domain.engineering import CADReadyEngineeringDefinition, CommitmentKind
from assy.stages.base import PipelineStage


class ParametricSolver(PipelineStage):
    stage_id: ClassVar[Stage] = Stage.SOLVER
    question: ClassVar[str] = "What numerical values satisfy the declared constraints?"
    produces: ClassVar[str] = "SolvedDesign"

    def run(self, *, definition: CADReadyEngineeringDefinition) -> SolvedDesign:
        params: list[SolvedParameter] = []
        diagnostics: list[str] = []
        free: list[str] = []

        # Any active commitment carrying a number is a solved value, whatever its
        # kind: CAD needs a stroke declared as MOTION exactly as much as a diameter
        # declared as PARAMETER. Only declared parameters can be *undetermined*.
        declared = {c.id for c in definition.parameters()}
        seen: set[str] = set()

        for c in definition.working_state.active:
            is_number = isinstance(c.value, (int, float)) and not isinstance(c.value, bool)
            if is_number:
                if c.subject in seen:
                    continue
                seen.add(c.subject)
                params.append(
                    SolvedParameter(
                        name=c.subject,
                        value=float(c.value),
                        unit=c.unit or "mm",
                        commitment_id=c.id,
                        derived=c.expression is not None,
                    )
                )
            elif c.id in declared:
                if c.expression:
                    diagnostics.append(
                        f"{c.subject}: symbolic '{c.expression}' left to CAD-time evaluation"
                    )
                elif c.value is None:
                    free.append(c.subject)

        satisfied: list[ConstraintOutcome] = []
        violated: list[ConstraintOutcome] = []
        for c in definition.constraints():
            expr = c.expression or c.statement
            ok = True
            residual = None
            if isinstance(c.value, bool):
                ok = c.value
            elif isinstance(c.value, (int, float)):
                # Constraints carrying a numeric bound are checked against their
                # like-named parameter where one exists.
                target = next((p for p in params if p.name == c.subject), None)
                if target is not None:
                    residual = float(c.value) - target.value
                    ok = residual >= 0
            outcome = ConstraintOutcome(
                commitment_id=c.id, expression=expr, satisfied=ok, residual=residual
            )
            (satisfied if ok else violated).append(outcome)

        objectives = {
            o.subject: 0.0 for o in definition.objectives()
        }  # objective values are reported, not optimised in the slice
        if objectives:
            diagnostics.append(
                f"{len(objectives)} objective(s) recorded but not optimised in this implementation"
            )

        if free:
            status = SolveStatus.UNDERDETERMINED
            diagnostics.append(f"undetermined parameters: {', '.join(free)}")
        elif violated:
            status = SolveStatus.INFEASIBLE
        else:
            status = SolveStatus.SOLVED

        return SolvedDesign(
            meta=ObjectMeta(object_id=new_id("SOLVED"), producer=self.stage_id),
            status=status,
            parameters=params,
            satisfied=satisfied,
            violated=violated,
            objective_values=objectives,
            diagnostics=diagnostics,
            source_definition_id=definition.meta.object_id,
        )
