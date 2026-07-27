"""Stage 05 - Engineering Integration.

Question: how must the design be engineered so it can exist, move, assemble,
manufacture, and proceed to deterministic CAD generation?

This is the architecturally novel stage: a problem-driven design loop over the
four-object working state, not a single generation call.

    seed commitments
        -> run checks (detect)
        -> pick problem
        -> propose candidates
        -> select
        -> apply (supersede, commit, close)
        -> spawn implied problems
        -> invalidate dependent checks
        -> repeat
        -> mandatory closure pass

Convergence is not guaranteed and is not claimed. The loop runs under an explicit
budget and returns a structured blocked result rather than forcing closure
(STAGE_05 section 18).
"""

from __future__ import annotations

from collections import Counter
from typing import ClassVar

from assy.domain.common import ObjectMeta, Provenance, Stage, new_id
from assy.domain.engineering import (
    BlockedReason,
    CADReadyEngineeringDefinition,
    CheckResult,
    Commitment,
    CommitmentKind,
    CommitmentStatus,
    EngineeringWorkingState,
    Problem,
    ProblemOrigin,
    ProblemType,
    ReadinessReport,
    Resolution,
    ResolutionStatus,
    Severity,
)
from assy.domain.upstream import (
    ConceptVisualization,
    MechanicalArchitecture,
    ProductArchitecture,
    RequirementSpec,
)
from assy.knowledge import checks as K
from assy.knowledge import mechanisms as cat
from assy.knowledge import resolvers as R
from assy.knowledge import spawning
from assy.stages.base import DeterministicReasoner, PipelineStage, Reasoner

SEVERITY_ORDER = {
    Severity.BLOCKING: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
    Severity.INFORMATIONAL: 4,
}


class Budget:
    """Explicit limits. Exceeding one produces a structured block, never a silent pass."""

    def __init__(self, max_iterations: int = 200, max_repeat: int = 4, max_supersession: int = 12):
        self.max_iterations = max_iterations
        self.max_repeat = max_repeat
        self.max_supersession = max_supersession


class EngineeringIntegration(PipelineStage):
    stage_id: ClassVar[Stage] = Stage.ENGINEERING
    question: ClassVar[str] = "How must this design be engineered to become CAD-ready?"
    produces: ClassVar[str] = "CADReadyEngineeringDefinition"

    def __init__(self, reasoner: Reasoner | None = None, budget: Budget | None = None):
        self.reasoner = reasoner or DeterministicReasoner()
        self.budget = budget or Budget()

    # -- seeding -----------------------------------------------------------
    def _context(self, spec: RequirementSpec, mechanical: MechanicalArchitecture) -> R.ResolveContext:
        """Derive resolver context from requirements. No benchmark branching."""
        ctx = R.ResolveContext(family_id=mechanical.selected_id or "")
        for r in spec.requirements:
            if r.target is None:
                continue
            unit, val = r.target.unit.lower(), r.target.value
            if unit == "mm":
                ctx.travel_mm = max(ctx.travel_mm, val) if r.comparator != "between" else val
                if r.upper:
                    ctx.travel_mm = (val + r.upper.value) / 2.0
            elif unit == "kg":
                ctx.payload_n = round(val * 9.81 + 5.0, 2)  # payload plus moving structure
            elif unit == "g":
                ctx.payload_n = round(val * 0.00981 + 5.0, 2)
        return ctx

    def _seed(
        self,
        state: EngineeringWorkingState,
        spec: RequirementSpec,
        mechanical: MechanicalArchitecture,
        product: ProductArchitecture,
    ) -> None:
        family = cat.by_id(mechanical.selected_id or "")
        role_map = {p.name: p.roles for p in family.roles}
        served = [r.id for r in spec.requirements]

        for part in family.roles:
            c = Commitment(
                kind=CommitmentKind.ENTITY,
                subject=part.name,
                statement=f"{part.name} ({part.role}) in the {family.id} architecture",
                roles=list(role_map[part.name]),
                status=CommitmentStatus.SELECTED,
                provenance=Provenance(
                    requirements=served,
                    method=f"mechanical_architecture/{family.id}",
                ),
            )
            state.commit(c)
            for p in spawning.spawn_for(c):
                state.open_problem(p)

        # Product architecture commitments carry forward, they are not re-decided.
        state.commit(
            Commitment(
                kind=CommitmentKind.ASSEMBLY,
                subject="product.housing_strategy",
                statement=product.housing_strategy,
                value=product.housing_strategy,
                status=CommitmentStatus.SELECTED,
                provenance=Provenance(method="product_architecture", requirements=served),
            )
        )

        # Requirement-derived problems for quantitative targets.
        for r in spec.quantitative:
            state.open_problem(
                Problem(
                    type=ProblemType.UNDETERMINED,
                    origin=ProblemOrigin.REQUIREMENT,
                    entities=["product"],
                    phenomenon=f"requirement_{r.id}",
                    evaluation_domain="requirement",
                    statement=r.statement,
                    severity=Severity.LOW,  # satisfied via downstream evaluation, not here
                    serves_requirements=[r.id],
                )
            )

    # -- loop --------------------------------------------------------------
    def _next_problem(self, state: EngineeringWorkingState) -> Problem | None:
        candidates = [p for p in state.open_problems if p.severity != Severity.LOW]
        if not candidates:
            return None
        # Blocking first; then prefer problems whose phenomenon we can actually resolve,
        # so a knowledge gap does not stall progress on the rest of the agenda.
        return min(
            candidates,
            key=lambda p: (
                SEVERITY_ORDER[p.severity],
                0 if p.phenomenon in R.REGISTRY else 1,
                p.id,
            ),
        )

    def _run_checks(self, state: EngineeringWorkingState) -> None:
        for spec in K.CHECKS:
            existing = state.check_by_name(spec.name)
            if existing and existing.is_valid_evidence and not existing.stale:
                continue
            K.run_check(spec, state)

    def _readiness(self, state: EngineeringWorkingState) -> ReadinessReport:
        """The mandatory total closure pass (STAGE_05 section 17)."""
        for spec in K.CHECKS:
            K.run_check(spec, state)

        blocking = state.blocking_problems
        executed, passing, missing, failing = [], [], [], []
        for name in K.MANDATORY:
            k = state.check_by_name(name)
            if k is None or k.result == CheckResult.NOT_RUN:
                missing.append(name)
                continue
            executed.append(name)
            if k.is_satisfied:
                # PASS, or NOT_APPLICABLE because this product class has nothing
                # for the check to evaluate - vacuously satisfied either way.
                passing.append(name)
            else:
                failing.append(f"{name}:{k.result.value}{' (stale)' if k.stale else ''}")

        undetermined = [c.subject for c in state.active if not c.is_determined]
        solvable = state.check_by_name("system_solvable")
        structurally_solvable = bool(solvable and solvable.result == CheckResult.PASS)

        ready = (
            not blocking
            and not missing
            and not failing
            and not undetermined
            and structurally_solvable
        )
        return ReadinessReport(
            ready=ready,
            no_blocking_problems=not blocking,
            mandatory_checks_executed=not missing,
            mandatory_checks_passing=not failing,
            all_commitments_determined=not undetermined,
            system_structurally_solvable=structurally_solvable,
            undetermined=undetermined,
            missing_checks=missing,
            failing_checks=failing,
        )

    def run(
        self,
        *,
        spec: RequirementSpec,
        mechanical: MechanicalArchitecture,
        product: ProductArchitecture,
        concept: ConceptVisualization | None = None,
    ) -> CADReadyEngineeringDefinition:
        state = EngineeringWorkingState()
        ctx = self._context(spec, mechanical)
        self._seed(state, spec, mechanical, product)

        seen: Counter[tuple[str, str, str]] = Counter()
        supersessions = 0
        blocked: BlockedReason | None = None
        iterations = 0

        while iterations < self.budget.max_iterations:
            iterations += 1
            self._run_checks(state)

            problem = self._next_problem(state)
            if problem is None:
                break

            seen[problem.key] += 1
            if seen[problem.key] > self.budget.max_repeat:
                blocked = BlockedReason.CYCLIC_RESOLUTION
                state.trace.append(f"iter {iterations}: {problem.id} exceeded repeat budget")
                break

            candidates = R.propose(problem, state, ctx)
            if not candidates:
                # Honest signal: the knowledge base has no rule for this phenomenon.
                problem.severity = Severity.HIGH
                problem.type = ProblemType.UNKNOWN
                problem.statement += " [no resolver in knowledge base]"
                state.trace.append(
                    f"iter {iterations}: no resolver for '{problem.phenomenon}' ({problem.id})"
                )
                if all(
                    p.type == ProblemType.UNKNOWN
                    for p in state.open_problems
                    if p.severity != Severity.LOW
                ):
                    blocked = BlockedReason.INSUFFICIENT_KNOWLEDGE
                    break
                continue

            for c in candidates:
                state.propose(c)
            chosen: Resolution = self.reasoner.propose(
                task=f"resolve {problem.phenomenon} on {problem.entities}",
                context={"problem": problem.statement, "domain": problem.evaluation_domain},
                options=candidates,
            )
            for c in candidates:
                if c.id != chosen.id:
                    c.status = ResolutionStatus.REJECTED
                    c.rejection_reason = f"not selected over {chosen.id}"
            chosen.status = ResolutionStatus.SELECTED

            supersessions += len(chosen.supersedes)
            if supersessions > self.budget.max_supersession:
                blocked = BlockedReason.CYCLIC_RESOLUTION
                state.trace.append(f"iter {iterations}: supersession budget exceeded")
                break

            state.apply(chosen)
            state.trace.append(f"iter {iterations}: {problem.id} <- {chosen.id} ({chosen.approach})")

            for c in chosen.commitments:
                for sp in spawning.spawn_for(c):
                    state.open_problem(sp)
        else:
            blocked = BlockedReason.BUDGET_EXHAUSTED

        readiness = self._readiness(state)
        if blocked:
            readiness.ready = False
            readiness.blocked_reason = blocked
            readiness.recommended_restart = (
                "product_architecture"
                if blocked is BlockedReason.NO_FEASIBLE_PACKAGING
                else "engineering_integration"
            )

        risks: list[str] = [
            f"{p.id}: {p.statement}"
            for p in state.open_problems
            if p.severity in (Severity.MEDIUM, Severity.LOW, Severity.HIGH)
        ]

        return CADReadyEngineeringDefinition(
            meta=ObjectMeta(object_id=new_id("CRED"), producer=self.stage_id),
            working_state=state,
            readiness=readiness,
            iterations=iterations,
            non_blocking_risks=risks,
        )
