"""Stage 05 working state: the four-object model.

    EngineeringWorkingState
    |-- Commitment Store
    |-- Problem Agenda
    |-- Resolution Graph
    +-- Check Registry

Implements STAGE_05 sections 6-10, including the six modifications the Geneva
falsification trace forced:

  1. supersession semantics          (section 7.6, blocking)
  2. mandatory total closure pass    (section 17, blocking)
  3. ``objective`` as a commitment   (section 7.2)
  4. check kinds                     (section 10.2)
  5. check evaluation domains        (section 10.4)
  6. canonical problem identity      (section 8.4)
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from assy.domain.common import DomainObject, Provenance, new_id


# --------------------------------------------------------------------------
# Commitment Store
# --------------------------------------------------------------------------
class CommitmentKind(str, Enum):
    ENTITY = "entity"
    RELATION = "relation"
    PARAMETER = "parameter"
    VALUE = "value"
    CONSTRAINT = "constraint"
    OBJECTIVE = "objective"  # mandatory: trade-offs are not pass/fail
    INTERFACE = "interface"
    MOTION = "motion"
    SUPPORT = "support"
    ASSEMBLY = "assembly"
    MANUFACTURING = "manufacturing"
    TOLERANCE = "tolerance"
    CRITICAL_CHARACTERISTIC = "critical_characteristic"
    ASSUMPTION = "assumption"


class CommitmentStatus(str, Enum):
    ASSUMED = "assumed"
    PROVISIONAL = "provisional"
    SELECTED = "selected"
    VERIFIED = "verified"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"


class Commitment(BaseModel):
    """Something the design currently asserts.

    May exist before a numeric value is known: ``symbolic=True`` with
    ``value=None`` is the normal state for a structural commitment, because
    loads and geometry are co-dependent (STAGE_05 section 7.4).
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: new_id("C"))
    kind: CommitmentKind
    subject: str  # stable semantic name, never a kernel face/edge id
    statement: str
    value: float | str | bool | None = None
    unit: str | None = None
    symbolic: bool = False
    expression: str | None = None  # for constraints/objectives
    status: CommitmentStatus = CommitmentStatus.PROVISIONAL
    roles: list[str] = Field(default_factory=list)
    """Engineering roles (``rotating``, ``guided``, ``user_contact``, ...).

    Spawning rules key on these rather than on part names, so the knowledge base
    stays benchmark-independent (Rule BM-1).
    """
    provenance: Provenance = Field(default_factory=Provenance)
    superseded_by: str | None = None  # resolution id
    replaces: str | None = None  # commitment id

    @property
    def is_active(self) -> bool:
        return self.status not in (
            CommitmentStatus.SUPERSEDED,
            CommitmentStatus.REJECTED,
        )

    @property
    def is_determined(self) -> bool:
        """A parameter is determined once it carries a value or an expression."""
        if self.kind in (CommitmentKind.PARAMETER, CommitmentKind.VALUE):
            return self.value is not None or self.expression is not None
        return True


# --------------------------------------------------------------------------
# Problem Agenda
# --------------------------------------------------------------------------
class ProblemType(str, Enum):
    UNDETERMINED = "undetermined"
    VIOLATED = "violated"
    UNVERIFIED = "unverified"
    CONFLICTING = "conflicting"
    UNKNOWN = "unknown"
    INCOMPLETE = "incomplete"
    INVALIDATED = "invalidated"


class ProblemOrigin(str, Enum):
    REQUIREMENT = "requirement-derived"
    SPAWNED = "spawned-by-commitment"
    CHECK = "detected-by-check"
    MANUFACTURING = "manufacturing-derived"
    ASSEMBLY = "assembly-derived"
    SIMULATION = "simulation-derived"
    HUMAN = "human-raised"
    EXTERNAL = "external-evidence-derived"


class Severity(str, Enum):
    BLOCKING = "blocking"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class Problem(BaseModel):
    """Something preventing the state from being complete, coherent, or verified.

    Canonical identity is (entities, phenomenon, evaluation_domain). The domain
    term is required: the same pair of entities can have genuinely different
    problems during dwell versus engagement (STAGE_05 section 8.4).
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: new_id("P"))
    type: ProblemType
    origin: ProblemOrigin
    entities: list[str] = Field(default_factory=list)
    phenomenon: str = ""
    evaluation_domain: str = "static"
    statement: str = ""
    severity: Severity = Severity.HIGH
    serves_requirements: list[str] = Field(default_factory=list)
    discovered_by: str | None = None  # check id or commitment id
    resolved_by: str | None = None  # resolution id
    open: bool = True
    reopened_count: int = 0

    @property
    def key(self) -> tuple[str, str, str]:
        """Canonical key used to merge duplicate discoveries."""
        return (
            "|".join(sorted(self.entities)),
            self.phenomenon,
            self.evaluation_domain,
        )

    @property
    def blocks_cad(self) -> bool:
        return self.open and self.severity == Severity.BLOCKING


# --------------------------------------------------------------------------
# Resolution Graph
# --------------------------------------------------------------------------
class ResolutionStatus(str, Enum):
    PROPOSED = "proposed"
    SELECTED = "selected"
    REJECTED = "rejected"
    APPLIED = "applied"
    VERIFIED = "verified"
    INVALIDATED = "invalidated"
    SUPERSEDED = "superseded"


class Resolution(BaseModel):
    """A candidate or selected response to a problem.

    ``supersedes`` is what makes retraction expressible; without it the store
    can only accumulate contradictions.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: new_id("R"))
    problem_id: str
    approach: str
    method: str = ""  # named rule/formula that justified it
    status: ResolutionStatus = ResolutionStatus.PROPOSED
    commitments: list[Commitment] = Field(default_factory=list)
    supersedes: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    invalidates_checks: list[str] = Field(default_factory=list)
    rejection_reason: str | None = None
    score: float | None = None


# --------------------------------------------------------------------------
# Check Registry
# --------------------------------------------------------------------------
class CheckKind(str, Enum):
    DETERMINISTIC = "deterministic"
    ANALYTICAL = "analytical"
    RULE = "rule"
    JUDGMENT = "judgment"
    EXTERNAL_EVIDENCE = "external-evidence"


GATING_KINDS = {CheckKind.DETERMINISTIC, CheckKind.ANALYTICAL, CheckKind.RULE}
"""Only these may autonomously gate CAD readiness (STAGE_05 section 10.2)."""


class CheckResult(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"
    NOT_RUN = "not_run"


class Check(BaseModel):
    """A recorded analysis of the commitment state.

    ``evaluation_domain`` is required and is not decoration: the Geneva trace
    showed a per-pose check passing where a full-cycle sweep failed.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: new_id("K"))
    name: str
    kind: CheckKind
    evaluation_domain: str
    store_version: int = 0
    input_commitments: list[str] = Field(default_factory=list)
    result: CheckResult = CheckResult.NOT_RUN
    detail: str = ""
    margin: float | None = None
    produced_problems: list[str] = Field(default_factory=list)
    stale: bool = False
    mandatory: bool = False

    @property
    def is_valid_evidence(self) -> bool:
        return (not self.stale) and self.result != CheckResult.NOT_RUN

    @property
    def gates(self) -> bool:
        return self.kind in GATING_KINDS


# --------------------------------------------------------------------------
# Working state
# --------------------------------------------------------------------------
class BlockedReason(str, Enum):
    CYCLIC_RESOLUTION = "cyclic resolution"
    INSUFFICIENT_KNOWLEDGE = "insufficient engineering knowledge"
    CONFLICTING_REQUIREMENTS = "conflicting requirements"
    NO_FEASIBLE_PACKAGING = "no feasible spatial arrangement"
    MANUFACTURING_INCOMPATIBLE = "manufacturing incompatibility"
    ARCHITECTURE_UNSUITABLE = "concept architecture unsuitable"
    BUDGET_EXHAUSTED = "budget exhausted"


class EngineeringWorkingState(BaseModel):
    """The mutable Stage 05 state. Not a persisted domain object itself."""

    model_config = ConfigDict(extra="forbid")

    version: int = 0
    commitments: dict[str, Commitment] = Field(default_factory=dict)
    problems: dict[str, Problem] = Field(default_factory=dict)
    resolutions: dict[str, Resolution] = Field(default_factory=dict)
    checks: dict[str, Check] = Field(default_factory=dict)
    trace: list[str] = Field(default_factory=list)

    # -- commitment store --------------------------------------------------
    def commit(self, c: Commitment) -> Commitment:
        self.commitments[c.id] = c
        self.version += 1
        return c

    def supersede(self, commitment_id: str, by_resolution: str) -> None:
        """Retire a commitment without deleting it (section 7.6)."""
        c = self.commitments[commitment_id]
        c.status = CommitmentStatus.SUPERSEDED
        c.superseded_by = by_resolution
        self.version += 1
        # Reopen any problem this commitment had closed.
        for p in self.problems.values():
            if p.resolved_by and p.resolved_by in self.resolutions:
                res = self.resolutions[p.resolved_by]
                if commitment_id in [x.id for x in res.commitments] and not p.open:
                    p.open = True
                    p.reopened_count += 1
                    p.type = ProblemType.INVALIDATED
                    self.trace.append(
                        f"reopened {p.id} (commitment {commitment_id} superseded)"
                    )

    @property
    def active(self) -> list[Commitment]:
        return [c for c in self.commitments.values() if c.is_active]

    def active_by_kind(self, kind: CommitmentKind) -> list[Commitment]:
        return [c for c in self.active if c.kind == kind]

    def find_subject(self, subject: str) -> Commitment | None:
        for c in self.active:
            if c.subject == subject:
                return c
        return None

    # -- problem agenda ----------------------------------------------------
    def open_problem(self, p: Problem) -> Problem:
        """Add a problem, merging on canonical key rather than duplicating."""
        for existing in self.problems.values():
            if existing.key == p.key:
                if not existing.open:
                    existing.open = True
                    existing.reopened_count += 1
                self.trace.append(f"merged duplicate problem into {existing.id}")
                return existing
        self.problems[p.id] = p
        return p

    def close_problem(self, problem_id: str, resolution_id: str) -> None:
        p = self.problems[problem_id]
        p.open = False
        p.resolved_by = resolution_id

    @property
    def open_problems(self) -> list[Problem]:
        return [p for p in self.problems.values() if p.open]

    @property
    def blocking_problems(self) -> list[Problem]:
        return [p for p in self.problems.values() if p.blocks_cad]

    # -- resolution graph --------------------------------------------------
    def propose(self, r: Resolution) -> Resolution:
        self.resolutions[r.id] = r
        return r

    def apply(self, r: Resolution) -> None:
        """Apply a selected resolution: supersede, commit, then close."""
        for old in r.supersedes:
            if old in self.commitments:
                self.supersede(old, r.id)
        for c in r.commitments:
            c.provenance.resolution_id = r.id
            c.provenance.problem_id = r.problem_id
            c.provenance.method = r.method
            self.commit(c)
        r.status = ResolutionStatus.APPLIED
        self.close_problem(r.problem_id, r.id)
        self.invalidate_checks(r)

    # -- check registry ----------------------------------------------------
    def record_check(self, k: Check) -> Check:
        k.store_version = self.version
        self.checks[k.id] = k
        return k

    def invalidate_checks(self, r: Resolution) -> list[Check]:
        """Stale any check whose inputs the resolution touched.

        A stale check is not evidence, so each mandatory one becomes an
        ``unverified`` problem (section 10.5).
        """
        touched = {c.subject for c in r.commitments} | set(r.supersedes)
        invalidated: list[Check] = []
        for k in self.checks.values():
            if k.stale or k.result == CheckResult.NOT_RUN:
                continue
            names = set(k.input_commitments)
            if names & touched or k.id in r.invalidates_checks:
                k.stale = True
                invalidated.append(k)
                if k.mandatory:
                    self.open_problem(
                        Problem(
                            type=ProblemType.UNVERIFIED,
                            origin=ProblemOrigin.CHECK,
                            entities=sorted(names) or [k.name],
                            phenomenon=f"{k.name}_stale",
                            evaluation_domain=k.evaluation_domain,
                            statement=f"check '{k.name}' is stale after {r.id}",
                            severity=Severity.BLOCKING,
                            discovered_by=k.id,
                        )
                    )
        return invalidated

    def clear_problems_from(self, check_name: str, evidence_id: str) -> list[str]:
        """Close problems a check raised, once that check passes.

        Symmetry with detection: if a deterministic check is the authority for
        opening a problem, a later passing run of the same check is the
        authority for closing it. Without this, a transient detection blocks the
        agenda forever even after the design has moved past it.
        """
        ids = {k.id for k in self.checks.values() if k.name == check_name}
        closed: list[str] = []
        for p in self.problems.values():
            if p.open and (p.discovered_by in ids or p.discovered_by == check_name):
                p.open = False
                p.resolved_by = evidence_id
                closed.append(p.id)
        return closed

    def check_by_name(self, name: str) -> Check | None:
        newest = None
        for k in self.checks.values():
            if k.name == name and (newest is None or k.store_version >= newest.store_version):
                newest = k
        return newest


# --------------------------------------------------------------------------
# Stage 05 output
# --------------------------------------------------------------------------
class ReadinessReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ready: bool
    no_blocking_problems: bool
    mandatory_checks_executed: bool
    mandatory_checks_passing: bool
    all_commitments_determined: bool
    system_structurally_solvable: bool
    undetermined: list[str] = Field(default_factory=list)
    missing_checks: list[str] = Field(default_factory=list)
    failing_checks: list[str] = Field(default_factory=list)
    blocked_reason: BlockedReason | None = None
    recommended_restart: str | None = None


class CADReadyEngineeringDefinition(DomainObject):
    """Stage 05 output: the complete engineering definition CAD compiles from.

    If the CAD Builder needs an engineering decision that is not here, Stage 05
    was incomplete (STAGE_05 section 20).
    """

    working_state: EngineeringWorkingState
    readiness: ReadinessReport
    iterations: int = 0
    non_blocking_risks: list[str] = Field(default_factory=list)

    # -- projections consumed downstream ----------------------------------
    def parameters(self) -> list[Commitment]:
        return [
            c
            for c in self.working_state.active
            if c.kind in (CommitmentKind.PARAMETER, CommitmentKind.VALUE)
        ]

    def constraints(self) -> list[Commitment]:
        return self.working_state.active_by_kind(CommitmentKind.CONSTRAINT)

    def objectives(self) -> list[Commitment]:
        return self.working_state.active_by_kind(CommitmentKind.OBJECTIVE)

    def entities(self) -> list[Commitment]:
        return self.working_state.active_by_kind(CommitmentKind.ENTITY)

    def interfaces(self) -> list[Commitment]:
        return self.working_state.active_by_kind(CommitmentKind.INTERFACE)

    def motions(self) -> list[Commitment]:
        return self.working_state.active_by_kind(CommitmentKind.MOTION)

    def critical_characteristics(self) -> list[Commitment]:
        return self.working_state.active_by_kind(CommitmentKind.CRITICAL_CHARACTERISTIC)
