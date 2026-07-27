"""Domain objects produced by Stages 01-04.

These are the authoritative engineering inputs to Stage 05. The authority order
is RequirementSpec > MechanicalArchitecture > ProductArchitecture > Concept
(STAGE_05 section 3); the concept visualisation is explicitly non-authoritative.
"""

from __future__ import annotations

from enum import Enum

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from assy.domain.common import DomainObject, Quantity


# --------------------------------------------------------------------------
# Stage 01 - RequirementSpec
# --------------------------------------------------------------------------
class RequirementKind(str, Enum):
    FUNCTIONAL = "functional"
    PERFORMANCE = "performance"
    USABILITY = "usability"
    SAFETY = "safety"
    MANUFACTURING = "manufacturing"
    MATERIAL = "material"
    ASSEMBLY = "assembly"
    ENVIRONMENTAL = "environmental"


class RequirementOrigin(str, Enum):
    """Stated requirements must stay distinguishable from inferred ones (section 6)."""

    USER_STATED = "user_stated"
    CLARIFICATION = "clarification"
    INFERRED = "inferred"
    PROJECT_DEFAULT = "project_default"


class SourceOrigin(str, Enum):
    """Where a clause of the ledger came from. Clarifications have equal standing."""

    REQUEST = "request"
    CLARIFICATION = "clarification"
    POLICY = "policy"


class ClauseDisposition(str, Enum):
    """STAGE_01 §6.1 Pass A. Every clause carries exactly one."""

    FUNCTION = "function"
    CONSTRAINT = "constraint"
    CONTEXT = "context"
    FREEDOM = "freedom"
    NON_ENGINEERING = "non_engineering"


class SourceClause(BaseModel):
    """One clause of the request or a clarification (SD-1).

    The ledger is what makes semantic coverage auditable: every derived object
    points back to the clause it came from, and every ``function`` clause must be
    discharged by at least one requirement (STAGE_01 A-3).
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    text: str
    source: SourceOrigin
    disposition: ClauseDisposition


class VerificationKind(str, Enum):
    """How a requirement could eventually be falsified (SD-2).

    Intent only. The test plan itself belongs to Stage 08.
    """

    MEASUREMENT = "measurement"
    DEMONSTRATION = "demonstration"
    INSPECTION = "inspection"
    ANALYSIS = "analysis"
    NOT_YET_VERIFIABLE = "not_yet_verifiable"


class VerificationIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: VerificationKind
    observable: str | None = None
    condition: str | None = None
    reason: str | None = None  # required when kind is NOT_YET_VERIFIABLE


class QuantityKind(str, Enum):
    """What kind of engineering quantity crosses a boundary."""

    ROTATION = "rotation"
    TRANSLATION = "translation"
    FORCE = "force"
    DISPLACEMENT = "displacement"
    STATE = "state"
    NONE = "none"


class Continuity(str, Enum):
    CONTINUOUS = "continuous"
    INTERMITTENT = "intermittent"
    HELD = "held"
    SINGLE_EVENT = "single_event"


class BehaviourSpec(BaseModel):
    """RD-2's content, structurally.

    RD-2 has always required actor, action, object, and condition. Without a
    representation it degraded into the `statement` string, so the transformation
    a behaviour performs — what goes in, what comes out — was recoverable only by
    re-reading prose. That forced the consumer to re-interpret the request, which
    STAGE_01 §5 forbids. This field is not a new obligation; it is the existing
    one made expressible.
    """

    model_config = ConfigDict(extra="forbid")

    actor: str
    action: str
    object: str
    condition: str | None = None
    input_kind: QuantityKind = QuantityKind.NONE
    output_kind: QuantityKind = QuantityKind.NONE
    continuity: Continuity = Continuity.SINGLE_EVENT
    reversible: bool = False

    @property
    def signature(self) -> str:
        """The transformation, as a consumer filters on it."""
        return f"{self.input_kind.value}->{self.output_kind.value}/{self.continuity.value}"


class RequirementBound(BaseModel):
    """A quantitative bound as one engineering object (SD-8).

    A bound is an interval, not three loose fields. Modelling it as an interval
    makes the failure that motivated SD-8 unrepresentable: a stated range cannot
    lose an endpoint, because ``between`` without both endpoints does not
    construct.

        >= X        [X, inf)      lower=X   upper=None
        <= X        (-inf, X]     lower=None upper=X
        == X        [X, X]        lower=X   upper=X
        between X,Y [X, Y]        lower=X   upper=Y
    """

    model_config = ConfigDict(extra="forbid")

    comparator: Literal[">=", "<=", "==", "between"]
    lower: float | None = None
    upper: float | None = None
    unit: str
    tolerance: float | None = None
    approximate: bool = False
    """The user stated the value loosely ("about X"), not exactly.

    Without this, canonicalising [X, X] to "==" asserts an exactness the user
    never stated - PD-10, and an L1 failure in its own right. An approximate
    nominal with no stated tolerance is `approximate=True, tolerance=None`, and
    the missing tolerance is an unknown.
    """

    @property
    def precision(self) -> str:
        """exact | approximate | bounded | toleranced - what the user actually fixed."""
        if self.comparator == "between":
            return "bounded"
        if self.approximate:
            return "approximate"
        return "toleranced" if self.tolerance is not None else "exact"

    @model_validator(mode="after")
    def _interval_is_well_formed(self) -> RequirementBound:
        if not self.unit.strip():
            raise ValueError("a bound must carry a unit")
        if self.lower is None and self.upper is None:
            raise ValueError("a bound must carry at least one endpoint")
        if self.lower is not None and self.upper is not None and self.lower > self.upper:
            raise ValueError(f"lower {self.lower} exceeds upper {self.upper}")

        if self.comparator == ">=" and (self.lower is None or self.upper is not None):
            raise ValueError("'>=' requires a lower endpoint only")
        if self.comparator == "<=" and (self.upper is None or self.lower is not None):
            raise ValueError("'<=' requires an upper endpoint only")
        if self.comparator == "==" and self.lower != self.upper:
            raise ValueError("'==' requires identical endpoints")
        if self.comparator == "between":
            if self.lower is None or self.upper is None:
                raise ValueError("'between' requires both endpoints")
            if self.lower == self.upper:
                # Canonicalise, do not reject. [X, X] written as a range carries
                # complete and correct engineering content in a redundant encoding;
                # rejecting it is a false failure on a labelling technicality.
                # Contrast with a MISSING endpoint, which is absent information and
                # is still rejected above - the distinction is invention versus
                # notation.
                self.comparator = "=="
        return self

    @property
    def is_range(self) -> bool:
        return self.comparator == "between"


class Requirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    kind: RequirementKind
    origin: RequirementOrigin
    statement: str
    bound: RequirementBound | None = None
    behaviour: BehaviourSpec | None = None
    """Required for functional/performance requirements (RD-2, A-34)."""
    priority: int = 3  # 1 highest
    derived_from: list[str] = Field(default_factory=list)
    """Source clause ids (SD-1). Empty is legal only for supplied origins."""
    verification: VerificationIntent | None = None

    @property
    def is_quantitative(self) -> bool:
        return self.bound is not None

    # -- read-compatibility -------------------------------------------------
    # Downstream stages consume target/upper/comparator. Those are now views of
    # the bound object rather than independently settable fields, so the illegal
    # combinations they used to permit can no longer be constructed.
    @property
    def target(self) -> Quantity | None:
        if self.bound is None:
            return None
        value = self.bound.lower if self.bound.lower is not None else self.bound.upper
        return Quantity(value=float(value), unit=self.bound.unit)

    @property
    def upper(self) -> Quantity | None:
        if self.bound is None or not self.bound.is_range or self.bound.upper is None:
            return None
        return Quantity(value=float(self.bound.upper), unit=self.bound.unit)

    @property
    def comparator(self) -> str | None:
        return self.bound.comparator if self.bound else None

    @property
    def tolerance(self) -> Quantity | None:
        if self.bound is None or self.bound.tolerance is None:
            return None
        return Quantity(value=float(self.bound.tolerance), unit=self.bound.unit)

    @property
    def verifiable(self) -> bool:
        """Derived, not stored: a requirement is verifiable when an intent says so."""
        return (
            self.verification is not None
            and self.verification.kind is not VerificationKind.NOT_YET_VERIFIABLE
        )


class FreedomKind(str, Enum):
    """The five forms of STAGE_01 §6.8. Preserved, never invented."""

    UNCONSTRAINED = "unconstrained"
    OPTIONAL = "optional"
    PERMITTED = "permitted"
    PROHIBITED = "prohibited"
    PREFERRED = "preferred"


class DesignFreedom(BaseModel):
    """Information about the solution space rather than the product's behaviour (SD-3).

    Stage 01 preserves these exactly as stated or supplied. Interpreting a freedom
    into mechanism alternatives is Stage 02's responsibility.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    kind: FreedomKind
    subject: str
    statement: str
    origin: RequirementOrigin
    derived_from: list[str] = Field(default_factory=list)


class RelationKind(str, Enum):
    CONFLICTS_WITH = "conflicts_with"
    DEPENDS_ON = "depends_on"
    REFINES = "refines"
    DUPLICATES = "duplicates"


class RequirementRelation(BaseModel):
    """A recorded tension or dependency (SD-4). Stage 01 records; it never arbitrates."""

    model_config = ConfigDict(extra="forbid")

    kind: RelationKind
    source: str
    target: str
    rationale: str = ""


class OperatingScenario(BaseModel):
    """A named condition under which requirements must hold (SD-5).

    ``applies_to`` is what distinguishes a scenario from a label.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str = ""
    applies_to: list[str] = Field(default_factory=list)
    derived_from: list[str] = Field(default_factory=list)


class Unknown(BaseModel):
    """Something required but not determinable from the request (SD-6)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    subject: str
    reason: str
    affects: list[str] = Field(default_factory=list)
    resolvable_by: str = ""
    derived_from: list[str] = Field(default_factory=list)
    """Source clause ids (SD-7). Matches the provenance its siblings already carry,
    so groundedness is decided by citation rather than by word overlap."""


class Assumption(BaseModel):
    """Something the interpreter supplied rather than read (SD-6).

    ``stands_in_for`` pairs it with the unknown it replaces, so resolving that
    unknown identifies exactly what must be revisited.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    statement: str
    stands_in_for: str | None = None
    origin: RequirementOrigin = RequirementOrigin.INFERRED
    derived_from: list[str] = Field(default_factory=list)


class DiscoveryState(str, Enum):
    """How a required discovery concluded (SD-9, revised).

    Absence is a *completion state*, not a closing action. Every required
    discovery reaches exactly one of these, so an empty result is never
    ambiguous between "none exist" and "the pass never ran".
    """

    FOUND = "found"
    UNKNOWN = "unknown"
    EXPLICITLY_ABSENT = "explicitly_absent"
    NOT_APPLICABLE = "not_applicable"
    DEFERRED = "deferred"


class DiscoveryOutcome(BaseModel):
    """The completion state of one required discovery (RD-1 ... RD-15)."""

    model_config = ConfigDict(extra="forbid")

    discovery: str
    state: DiscoveryState
    reason: str = ""

    @property
    def needs_reason(self) -> bool:
        return self.state in (
            DiscoveryState.EXPLICITLY_ABSENT,
            DiscoveryState.NOT_APPLICABLE,
            DiscoveryState.DEFERRED,
        )


class RequirementSpec(DomainObject):
    """Structured engineering meaning of the user's request."""

    source_text: str
    product_intent: str
    """Solution-independent functional abstraction: the outcome requested, with no
    solution nouns. This is what Stage 02 reasons from, so anchoring it on a
    solution the user happened to name would pre-empt mechanism selection."""
    user_intent_summary: str = ""
    """Faithful summary in the user's own terms, preserving any solution wording
    they imposed. Fidelity and abstraction are two obligations; one field could
    satisfy only one of them, which is what made A-1 unsatisfiable."""
    clauses: list[SourceClause] = Field(default_factory=list)
    requirements: list[Requirement] = Field(default_factory=list)
    operating_scenarios: list[OperatingScenario] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    unknowns: list[Unknown] = Field(default_factory=list)
    freedoms: list[DesignFreedom] = Field(default_factory=list)
    relations: list[RequirementRelation] = Field(default_factory=list)
    discovery_outcomes: list[DiscoveryOutcome] = Field(default_factory=list)

    def by_id(self, rid: str) -> Requirement:
        for r in self.requirements:
            if r.id == rid:
                return r
        raise KeyError(rid)

    @property
    def quantitative(self) -> list[Requirement]:
        return [r for r in self.requirements if r.is_quantitative]

    @property
    def requirement_ids(self) -> set[str]:
        return {r.id for r in self.requirements}

    @property
    def clause_ids(self) -> set[str]:
        return {c.id for c in self.clauses}

    def clauses_with(self, disposition: ClauseDisposition) -> list[SourceClause]:
        return [c for c in self.clauses if c.disposition is disposition]


# --------------------------------------------------------------------------
# Stage 02 - Mechanical Architecture
# --------------------------------------------------------------------------
class MechanismRole(str, Enum):
    INPUT = "input"
    TRANSMISSION = "transmission"
    CONVERSION = "conversion"
    OUTPUT = "output"
    GUIDANCE = "guidance"
    RETENTION = "retention"
    STRUCTURE = "structure"


class FunctionalPart(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    role: MechanismRole
    rationale: str = ""


class MotionRelation(BaseModel):
    """A conceptual motion relationship. No geometry, no dimensions."""

    model_config = ConfigDict(extra="forbid")

    id: str
    driver: str
    driven: str
    relation: str  # "rotation->translation", "rotation->rotation", ...
    ratio_symbol: str | None = None
    dof: int = 1


class MechanicalArchitectureCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    principle: str
    parts: list[FunctionalPart] = Field(default_factory=list)
    motions: list[MotionRelation] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    serves_requirements: list[str] = Field(default_factory=list)


class MechanicalArchitecture(DomainObject):
    """Candidate set. Count is adaptive (1..N), never a fixed number."""

    candidates: list[MechanicalArchitectureCandidate] = Field(default_factory=list)
    selected_id: str | None = None
    selection_rationale: str = ""
    rejected: dict[str, str] = Field(default_factory=dict)

    @property
    def selected(self) -> MechanicalArchitectureCandidate:
        for c in self.candidates:
            if c.id == self.selected_id:
                return c
        raise ValueError("no selected mechanical architecture candidate")


# --------------------------------------------------------------------------
# Stage 03 - Product Architecture
# --------------------------------------------------------------------------
class ProductRegion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    purpose: str
    houses: list[str] = Field(default_factory=list)  # FunctionalPart ids
    external: bool = False


class ProductArchitecture(DomainObject):
    """Product-level organisation. Qualitative by design - no dimensions."""

    regions: list[ProductRegion] = Field(default_factory=list)
    housing_strategy: str = ""
    user_interaction: list[str] = Field(default_factory=list)
    assembly_strategy: str = ""
    service_strategy: str = ""
    protection_strategy: str = ""
    manufacturing_intent: str = ""
    load_paths: list[str] = Field(default_factory=list)
    proportions: str = ""
    risks: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Stage 04 - Concept Visualization
# --------------------------------------------------------------------------
class ConceptVisualization(DomainObject):
    """Spatial hypothesis only.

    Carries ``authoritative = False`` permanently. Stage 05 may reinterpret or
    ignore anything here when it conflicts with structured engineering data.
    """

    authoritative: bool = False
    image_refs: list[str] = Field(default_factory=list)
    described_layout: str = ""
    spatial_hypotheses: list[str] = Field(default_factory=list)
    review_concerns: list[str] = Field(default_factory=list)
