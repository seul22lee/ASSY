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
    SUPPORT = "support"
    """Locates a moving element without being part of the transformation."""
    LIMIT = "limit"
    """Bounds travel or motion range."""
    RELEASE = "release"
    """The surface a user acts on to end a held state."""


class ObligationKind(str, Enum):
    """What an element structurally requires in order to work.

    Typed so Stage 03 can *act* on the obligation. A prose sentence such as
    "the travelling member must be guided against rotation" is unusable to a
    downstream stage without re-reading it as language.
    """

    RADIAL_SUPPORT = "radial_support"
    AXIAL_THRUST = "axial_thrust"
    ANTI_ROTATION = "anti_rotation"
    GUIDANCE = "guidance"
    STRUCTURAL_ROOT = "structural_root"
    ALIGNMENT = "alignment"
    TRAVEL_LIMIT = "travel_limit"
    USER_ACCESS = "user_access"
    CLEARANCE = "clearance"


class InterfaceKind(str, Enum):
    """How two conceptual elements meet."""

    ROTATIONAL_JOINT = "rotational_joint"
    SLIDING_JOINT = "sliding_joint"
    THREADED_PAIR = "threaded_pair"
    TOOTHED_MESH = "toothed_mesh"
    FLEXIBLE_LINK = "flexible_link"
    CONTACT_PAIR = "contact_pair"
    FIXED_ATTACHMENT = "fixed_attachment"
    USER_CONTACT = "user_contact"


class SupportObligation(BaseModel):
    """One structural obligation an architecture places on the product.

    Stage 03 must be able to satisfy this without inferring it from prose.
    """

    model_config = ConfigDict(extra="forbid")

    element: str
    """The conceptual element that carries the obligation."""
    kind: ObligationKind
    reacted_by: str | None = None
    """Which element is expected to react it, when the architecture implies one."""
    why: str = ""
    """Engineering reason. Explanation only - never the machine-readable content."""


class ArchitecturalInterface(BaseModel):
    """Where two conceptual elements meet, and what crosses."""

    model_config = ConfigDict(extra="forbid")

    between: tuple[str, str]
    kind: InterfaceKind
    transmits: str = ""
    crosses_boundary: bool = False
    """True when this interface passes through the enclosure boundary."""


class ArchitecturalFunction(BaseModel):
    """One function the architecture must perform.

    This is the golden "functional chain": a sequence of *functions*, each bound
    to the element(s) that perform it. An element sequence alone cannot tell
    Stage 03 that a function exists but has no element yet assigned to it.
    """

    model_config = ConfigDict(extra="forbid")

    function: str
    performed_by: list[str] = Field(default_factory=list)
    serves_requirements: list[str] = Field(default_factory=list)


class FunctionalPart(BaseModel):
    model_config = ConfigDict(extra="forbid")

    moving: bool = False
    """Whether this element moves in operation.

    Structured because Stage 03 must derive swept volumes from it. It previously
    survived only inside the prose `rationale`, which is not consumable.
    """
    engineering_roles: list[str] = Field(default_factory=list)
    """Engineering role tags, e.g. rotating, translating, moving_boundary, compliant.

    Carried so a consumer never has to re-query the knowledge base by mechanism id
    to learn how an element behaves. `motions` declares one relation for the whole
    chain, so it cannot say how each individual element moves.
    """

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

    # -- conceptual content consumed by product architecture and geometry --
    functions: list[ArchitecturalFunction] = Field(default_factory=list)
    """The functions this architecture must perform, each bound to its elements."""
    element_chain: list[str] = Field(default_factory=list)
    """Ordered path from input to output, in element names."""
    state_relations: list[str] = Field(default_factory=list)
    holding_principle: str | None = None
    """How a maintained state is held, and how it is released. Conceptual only."""
    support_obligations: list[SupportObligation] = Field(default_factory=list)
    """What must be located or retained, without saying where or by what part."""
    constrained_by: list[str] = Field(default_factory=list)
    """Requirements whose quantitative bounds constrain this architecture."""
    load_path: list[str] = Field(default_factory=list)
    interfaces: list[ArchitecturalInterface] = Field(default_factory=list)
    spatial_implications: list[str] = Field(default_factory=list)
    """Arrangement consequences: what must be inside, outside, adjacent, or aligned."""
    motion_envelopes: list[str] = Field(default_factory=list)
    """Qualitative swept regions. No dimensions."""
    tradeoffs: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    downstream_decisions: list[str] = Field(default_factory=list)
    """Geometry decisions deliberately left to later stages."""


class DeficiencyItem(BaseModel):
    """One piece of structured information Stage 02 needs and did not receive."""

    model_config = ConfigDict(extra="forbid")

    missing_field: str
    """The structured field that is absent, e.g. `requirement.behaviour.input_kind`."""
    requirement_id: str | None = None
    why_stage02_needs_it: str = ""
    """What mechanical or geometric synthesis cannot proceed without it."""
    remedy: str = ""
    blocking: bool = True
    """True only when geometric synthesis genuinely cannot proceed.

    A gap that does not materially affect downstream shape, motion, arrangement,
    or packaging is reported as an advisory and does not stop the stage."""


class Stage01ContractDeficiency(DomainObject):
    """Stage 02 refuses to proceed rather than re-reading the request.

    Falling back to natural-language interpretation would hide the deficiency and
    reintroduce the coupling this rewrite removes. A deficiency is a typed result,
    not an exception to be swallowed.
    """

    items: list[DeficiencyItem] = Field(default_factory=list)
    source_spec_id: str = ""

    @property
    def blocking(self) -> bool:
        return bool(self.items)


class MechanicalArchitecture(DomainObject):
    """Candidate set. Count is adaptive (1..N), never a fixed number."""

    candidates: list[MechanicalArchitectureCandidate] = Field(default_factory=list)
    selected_id: str | None = None
    selection_rationale: str = ""
    rejected: dict[str, str] = Field(default_factory=dict)
    contract_advisories: list[str] = Field(default_factory=list)
    """Non-blocking Stage 01 gaps, carried forward rather than silently dropped."""

    @property
    def selected(self) -> MechanicalArchitectureCandidate:
        for c in self.candidates:
            if c.id == self.selected_id:
                return c
        raise ValueError("no selected mechanical architecture candidate")


# --------------------------------------------------------------------------
# Stage 03 - Product Architecture
# --------------------------------------------------------------------------
class RegionKind(str, Enum):
    """What a product region is for. Typed so Stage 04 can review it spatially."""

    ENCLOSED_VOLUME = "enclosed_volume"
    USER_ACCESS = "user_access"
    SWEPT_VOLUME = "swept_volume"
    SUPPORT_ZONE = "support_zone"
    RETENTION_ZONE = "retention_zone"
    TRAVEL_LIMIT_ZONE = "travel_limit_zone"
    SERVICE_ACCESS = "service_access"
    PAYLOAD = "payload"
    STRUCTURAL = "structural"


class PieceKind(str, Enum):
    """What a manufactured product piece is, structurally."""

    SHELL = "shell"
    COVER = "cover"
    MOVING_BODY = "moving_body"
    TRANSMISSION_ELEMENT = "transmission_element"
    SUPPORT_ELEMENT = "support_element"
    LIMIT_ELEMENT = "limit_element"
    RETENTION_ELEMENT = "retention_element"
    USER_ELEMENT = "user_element"


class PlacementKind(str, Enum):
    """A qualitative spatial relation. Never a coordinate."""

    INSIDE = "inside"
    OUTSIDE = "outside"
    ADJACENT = "adjacent"
    OPPOSITE = "opposite"
    PARALLEL = "parallel"
    ALONG = "along"
    SPANS = "spans"
    CROSSES = "crosses"
    BOUNDS = "bounds"


class ProductRegion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    purpose: str
    houses: list[str] = Field(default_factory=list)  # FunctionalPart ids
    external: bool = False
    kind: RegionKind = RegionKind.STRUCTURAL
    moving: bool = False
    """True when the region is swept by a moving element rather than static."""


class ProductPiece(BaseModel):
    """A manufactured or procured piece of the product.

    Distinct from a Stage 02 conceptual element: several elements may later be
    integrated into one piece. That integration is a decision, so it is recorded
    as unresolved rather than assumed here.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    kind: PieceKind
    realises_elements: list[str] = Field(default_factory=list)
    """Stage 02 conceptual element names this piece realises."""
    engineering_roles: list[str] = Field(default_factory=list)
    moving: bool = False
    external: bool = False
    rationale: str = ""


class ObligationOwnership(BaseModel):
    """Which product piece is answerable for a Stage 02 support obligation.

    An unowned obligation is an open problem, not a silent omission.
    """

    model_config = ConfigDict(extra="forbid")

    element: str
    obligation: ObligationKind
    owner_piece: str | None = None
    region: str | None = None
    unowned_reason: str | None = None


class ProductInterface(BaseModel):
    """A Stage 02 element interface, resolved onto product pieces."""

    model_config = ConfigDict(extra="forbid")

    between: tuple[str, str]
    kind: InterfaceKind
    transmits: str = ""
    crosses_boundary: bool = False
    from_elements: tuple[str, str] | None = None


class PlacementRelation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str
    relation: PlacementKind
    reference: str
    why: str = ""


class AssemblyStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order: int
    action: str
    pieces: list[str] = Field(default_factory=list)
    enables: str = ""


class LoadPathOwnership(BaseModel):
    """One load path, with the region that owns each hop."""

    model_config = ConfigDict(extra="forbid")

    name: str
    path: list[str] = Field(default_factory=list)
    owning_regions: list[str] = Field(default_factory=list)
    terminates_at: str | None = None


class ProductArchitecture(DomainObject):
    """Product-level organisation. Qualitative by design - no dimensions."""

    regions: list[ProductRegion] = Field(default_factory=list)
    pieces: list[ProductPiece] = Field(default_factory=list)
    obligation_ownership: list[ObligationOwnership] = Field(default_factory=list)
    interfaces: list[ProductInterface] = Field(default_factory=list)
    placements: list[PlacementRelation] = Field(default_factory=list)
    assembly_sequence: list[AssemblyStep] = Field(default_factory=list)
    load_path_ownership: list[LoadPathOwnership] = Field(default_factory=list)
    unresolved_decisions: list[str] = Field(default_factory=list)

    # -- traceability back to the architecture this organises ---------------
    source_architecture_id: str = ""
    source_candidate_id: str = ""
    serves_requirements: list[str] = Field(default_factory=list)
    architecture_advisories: list[str] = Field(default_factory=list)
    """Stage 02 gaps Stage 03 could not resolve, reported rather than compensated."""

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
class MotionClass(str, Enum):
    """How a moving element sweeps space."""

    ROTATIONAL = "rotational"
    TRANSLATIONAL = "translational"
    HINGED_ARC = "hinged_arc"
    COMPOUND = "compound"
    UNCLASSIFIED = "unclassified"


class SweptShape(str, Enum):
    """The qualitative shape of a swept region. Never a dimension."""

    DISC = "disc"
    PRISM = "prism"
    ARC_SECTOR = "arc_sector"
    COMPOUND = "compound"
    UNKNOWN = "unknown"


class SpatialZone(str, Enum):
    """Where a region sits in the coarse frame. Relative, never coordinates."""

    CORE = "core"
    """On the primary axis, where the principal motion happens."""
    FLANKING = "flanking"
    """Beside the primary axis - guides, supports."""
    END = "end"
    """At one end of the primary axis - thrust, limits."""
    OFFSET = "offset"
    """Displaced from the primary axis - transmission compartments."""
    BOUNDARY = "boundary"
    """Forming or breaching the enclosure surface."""
    EXTERNAL = "external"
    """Outside the enclosure."""


class AccessPurpose(str, Enum):
    USER_OPERATION = "user_operation"
    SERVICE = "service"
    ASSEMBLY = "assembly"
    PAYLOAD = "payload"


class SpatialIssueKind(str, Enum):
    INTERFERENCE = "interference"
    ACCESS_BLOCKED = "access_blocked"
    ENVELOPE_CONFLICT = "envelope_conflict"
    UNSUPPORTED_SPAN = "unsupported_span"
    ASSEMBLY_UNREACHABLE = "assembly_unreachable"


class ReferenceFrame(BaseModel):
    """The coarse frame every placement is expressed in.

    Qualitative: it names axes and says what defined them. It never fixes an
    origin, a direction cosine, or a dimension.
    """

    model_config = ConfigDict(extra="forbid")

    primary_axis: str
    """What the principal motion runs along, named after the element defining it."""
    primary_motion: MotionClass = MotionClass.UNCLASSIFIED
    derived_from: str = ""
    access_faces: list[str] = Field(default_factory=list)
    """Faces that must remain reachable, named by the region requiring them."""


class RegionPlacement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    region: str
    zone: SpatialZone
    relative_to: str | None = None
    why: str = ""
    houses: list[str] = Field(default_factory=list)
    """Elements arranged in this region. Carried so the blueprint stands alone."""


class PlacedPiece(BaseModel):
    """A product piece, with where Stage 04 put it.

    The blueprint arranges these, so it carries them: a consumer of the blueprint
    - a renderer, a reviewer, Stage 05 - must not have to re-join with Stage 03 to
    learn what is being arranged.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    kind: PieceKind
    region: str | None = None
    zone: SpatialZone | None = None
    moving: bool = False
    external: bool = False
    motion: "MotionClass | None" = None


class SweptVolumeSpec(BaseModel):
    """A moving element's swept region, classified by how it moves."""

    model_config = ConfigDict(extra="forbid")

    region: str
    element: str
    motion: MotionClass
    shape: SweptShape
    external: bool = False
    must_stay_clear_of: list[str] = Field(default_factory=list)


class InterferenceCandidate(BaseModel):
    """A region pair that could collide and must be kept disjoint."""

    model_config = ConfigDict(extra="forbid")

    between: tuple[str, str]
    why: str = ""
    addressed_by: str | None = None
    """The obligation or placement that already governs this pair, if any."""


class AccessRoute(BaseModel):
    model_config = ConfigDict(extra="forbid")

    region: str
    purpose: AccessPurpose
    obstructed_by: list[str] = Field(default_factory=list)


class SpatialIssue(BaseModel):
    """A structured concern for Stage 05. Not a rendering artefact."""

    model_config = ConfigDict(extra="forbid")

    id: str
    kind: SpatialIssueKind
    concern: str
    regions: list[str] = Field(default_factory=list)
    evidence: str = ""


class ViewSpec(BaseModel):
    """A view that would have to be produced to review this layout visually."""

    model_config = ConfigDict(extra="forbid")

    name: str
    purpose: str
    shows: list[str] = Field(default_factory=list)


class SpatialAnnotation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str
    note: str


class ConceptVisualization(DomainObject):
    """Spatial hypothesis only.

    Carries ``authoritative = False`` permanently. Stage 05 may reinterpret or
    ignore anything here when it conflicts with structured engineering data.

    Non-authoritative does not mean unstructured: the blueprint is expressed as
    typed placements, swept volumes, interference candidates and issues so Stage 05
    consumes a spatial hypothesis rather than re-deriving one from a paragraph.
    """

    authoritative: bool = False
    image_refs: list[str] = Field(default_factory=list)

    reference_frame: ReferenceFrame | None = None
    region_placements: list[RegionPlacement] = Field(default_factory=list)
    placed_pieces: list[PlacedPiece] = Field(default_factory=list)
    swept_volumes: list[SweptVolumeSpec] = Field(default_factory=list)
    interference_candidates: list[InterferenceCandidate] = Field(default_factory=list)
    access_routes: list[AccessRoute] = Field(default_factory=list)
    issues: list[SpatialIssue] = Field(default_factory=list)
    views: list[ViewSpec] = Field(default_factory=list)
    annotations: list[SpatialAnnotation] = Field(default_factory=list)

    source_product_id: str = ""
    source_candidate_id: str = ""
    product_advisories: list[str] = Field(default_factory=list)

    described_layout: str = ""
    spatial_hypotheses: list[str] = Field(default_factory=list)
    review_concerns: list[str] = Field(default_factory=list)
