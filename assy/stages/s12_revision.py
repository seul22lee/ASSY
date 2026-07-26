"""Stage 12 - Revision Routing.

Question: what is the earliest stage that must change?

Routing is derived from the Stage 05 dependency graph rather than a separate
hidden mechanism (STAGE_05 section 9.5): a failed requirement is traced through
commitment provenance to the resolutions that produced the implicated
commitments, and the restart level follows from what those resolutions touched.

Rule REV-1: always attempt the smallest justified modification.
"""

from __future__ import annotations

from typing import ClassVar

from assy.domain.common import ObjectMeta, Stage, new_id
from assy.domain.downstream import EvaluationReport, ReqStatus, RestartStage, RevisionDirective
from assy.domain.engineering import CADReadyEngineeringDefinition, CommitmentKind
from assy.stages.base import PipelineStage

# Commitment kinds ordered by how expensive they are to revise.
KIND_RESTART: list[tuple[set[CommitmentKind], RestartStage]] = [
    ({CommitmentKind.PARAMETER, CommitmentKind.VALUE}, RestartStage.PARAMETER),
    (
        {
            CommitmentKind.CONSTRAINT,
            CommitmentKind.OBJECTIVE,
            CommitmentKind.INTERFACE,
            CommitmentKind.MOTION,
            CommitmentKind.SUPPORT,
            CommitmentKind.TOLERANCE,
            CommitmentKind.MANUFACTURING,
            CommitmentKind.ASSEMBLY,
        },
        RestartStage.ENGINEERING,
    ),
    ({CommitmentKind.ENTITY, CommitmentKind.RELATION}, RestartStage.MECHANICAL),
]


class RevisionRouting(PipelineStage):
    stage_id: ClassVar[Stage] = Stage.REVISION
    question: ClassVar[str] = "What should change next, and where should execution restart?"
    produces: ClassVar[str] = "RevisionDirective"

    def run(
        self, *, evaluation: EvaluationReport, definition: CADReadyEngineeringDefinition
    ) -> RevisionDirective:
        state = definition.working_state

        if evaluation.overall == ReqStatus.PASS:
            return RevisionDirective(
                meta=ObjectMeta(object_id=new_id("REV"), producer=self.stage_id),
                restart=RestartStage.NONE,
                diagnosis="all requirements satisfied on valid evidence",
                confidence=0.9,
                source_evaluation_id=evaluation.meta.object_id,
            )

        failing = evaluation.failed + [
            o for o in evaluation.outcomes if o.status == ReqStatus.INVALID_TEST
        ]
        insufficient = evaluation.insufficient

        if not failing and insufficient:
            return RevisionDirective(
                meta=ObjectMeta(object_id=new_id("REV"), producer=self.stage_id),
                restart=RestartStage.ENGINEERING,
                diagnosis=(
                    f"{len(insufficient)} requirement(s) lack deterministic evidence; "
                    "extend readiness coverage rather than changing the design"
                ),
                evidence=[o.requirement_id for o in insufficient],
                preserve=[c.id for c in state.active],
                allowed_scope=["add checks", "add critical characteristics"],
                expected_effects=["requirements become evaluable"],
                confidence=0.6,
                source_evaluation_id=evaluation.meta.object_id,
            )

        failed_ids = {o.requirement_id for o in failing}
        implicated = [
            c
            for c in state.active
            if failed_ids & set(c.provenance.requirements)
        ]

        restart = RestartStage.PARAMETER
        for kinds, level in KIND_RESTART:
            if any(c.kind in kinds for c in implicated):
                restart = level
        # Smallest justified change: prefer the cheapest level that has a target.
        for kinds, level in KIND_RESTART:
            targets = [c for c in implicated if c.kind in kinds]
            if targets:
                restart = level
                implicated = targets
                break

        return RevisionDirective(
            meta=ObjectMeta(object_id=new_id("REV"), producer=self.stage_id),
            restart=restart,
            diagnosis=(
                f"{len(failing)} requirement(s) failed; "
                f"{len(implicated)} commitment(s) trace to them via provenance"
            ),
            evidence=[e for o in failing for e in o.evidence] or [evaluation.meta.object_id],
            preserve=[c.id for c in state.active if c not in implicated],
            allowed_scope=[f"modify {c.subject}" for c in implicated[:8]],
            target_commitments=[c.id for c in implicated],
            expected_effects=["failed requirement moves inside its target band"],
            risks=["revision may invalidate checks that currently pass"],
            confidence=0.55,
            source_evaluation_id=evaluation.meta.object_id,
        )
