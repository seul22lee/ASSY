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
class MotionKind(str, Enum):
    """How a conceptual element moves. Declared, never inferred from a name.

    Distinct from `engineering_roles`: a role tag says what an element *is for*
    (``moving_boundary``, ``load_bearing``, ``compliant``); the motion kind says
    how it *moves*. A lid is a moving boundary whose motion kind is rotation.
    """

    FIXED = "fixed"
    ROTATION = "rotation"
    TRANSLATION = "translation"
    ROTATION_TRANSLATION = "rotation_translation"
    COMPLIANT_DEFORMATION = "compliant_deformation"
    UNSPECIFIED = "unspecified"


class ElementClass(str, Enum):
    """What kind of thing an element is, kinematically.

    Orthogonal to `MechanismRole` (what it is *for*) and to `PieceKind` (how it is
    *made*). A hinge is a `guidance` role, a `support_element` piece, and a JOINT.

    Without this distinction a joint is indistinguishable from the members it
    joins, so it acquires bulk, a position of its own, and a swept volume - none
    of which a joint has. A hinge does not sweep a volume; the door it carries
    does.
    """

    BODY = "body"
    """Occupies volume, carries load, may move and sweep a region."""
    JOINT = "joint"
    """A relationship constraining relative motion between two bodies. It has no
    independent position: it is located where the bodies it connects meet."""
    FEATURE = "feature"
    """A local detail on a host body - a catch, a stop, a detent. It has no bulk
    of its own and moves with whatever it sits on."""


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


class AxisRelation(str, Enum):
    """How an interface constrains the two axes it joins.

    An interface that transmits motion is not free to join any two axes. A planar
    pair - a spur mesh, a pin in a slot, a cam and follower - only engages if the
    axes are parallel at a centre distance; a bevel exists precisely to make them
    intersect; a nut runs collinear with its screw. Deriving each element's axis
    independently and then declaring them coupled produces mechanisms that cannot
    move, and no dimension is needed to detect it.
    """

    IDENTICAL = "identical"
    """One axis shared, e.g. a shaft and its bearing or anything rigidly joined."""
    PARALLEL = "parallel"
    """Distinct parallel axes at a centre distance, e.g. a spur mesh or a pin pair."""
    COLLINEAR = "collinear"
    """Same line, e.g. a nut on its screw."""
    INTERSECTING = "intersecting"
    """Axes meet at an angle. This is what a redirect element is for."""
    UNCONSTRAINED = "unconstrained"
    """Genuinely free, e.g. a routed cable or a hand on a knob."""


#: What each interface kind implies when the family does not say otherwise.
#: A family overrides it where the same kind means something different - a bevel
#: and a spur mesh are both TOOTHED_MESH and constrain axes oppositely.
AXIS_RELATION_DEFAULT: dict["InterfaceKind", AxisRelation] = {}


class StateRole(str, Enum):
    """What a functional state is, mechanically.

    Named roles rather than product words so a family declares meaning, not
    vocabulary: a latch's "closed" and a drive's "retracted" are both HOLDING.
    """

    HOLDING = "holding"
    """A state the mechanism maintains without continuous input."""
    RELEASING = "releasing"
    """Retention has been broken but motion has not yet occurred."""
    MOVING = "moving"
    """In transit between held states."""
    LIMITED = "limited"
    """At a motion limit, held by a stop rather than by retention."""
    NEUTRAL = "neutral"


class FunctionalState(BaseModel):
    """One state the mechanism must be able to occupy.

    Declared by the mechanism family because which states exist is mechanism
    knowledge: a retention family has an engaged and a released state whatever
    product it sits in. Stage 04 realises these in space; it does not invent them.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    role: StateRole
    holds: list[str] = Field(default_factory=list)
    """Elements whose engagement maintains this state."""
    covers: list[str] = Field(default_factory=list)
    """Apertures or openings occluded in this state."""
    clears: list[str] = Field(default_factory=list)
    """Apertures or openings left free in this state."""
    at_limit_of: list[str] = Field(default_factory=list)
    """Joints or features resting at a motion limit in this state."""
    why: str = ""


class StateTransition(BaseModel):
    """A change between two functional states, and what drives it."""

    model_config = ConfigDict(extra="forbid")

    from_state: str
    to_state: str
    driven_by: str
    """The declared function that causes this transition."""
    moves: list[str] = Field(default_factory=list)
    why: str = ""


class SpatialRelationKind(str, Enum):
    """What a declared interface or obligation demands of relative position.

    Each value is a distinct mechanical requirement. There is deliberately no
    generic "coincident" catch-all: a threaded pair and a fixed attachment place
    genuinely different demands, and collapsing them would make the check
    unfalsifiable.
    """

    SHARED_AXIS = "shared_axis"
    """Rotational joint: one axis, with a realizable adjacency along it."""
    COMMON_TRAVEL_DIRECTION = "common_travel_direction"
    """Sliding joint: same travel direction, with overlapping guided span."""
    COAXIAL_WORKING_OVERLAP = "coaxial_working_overlap"
    """Threaded pair: coaxial, and engaged over a shared working region."""
    MATING_ADJACENCY = "mating_adjacency"
    """Fixed attachment or contact pair: the mating interfaces must meet."""
    AXIS_SURROUNDED = "axis_surrounded"
    """Radial support: the supported axis passes through the support region."""
    AXIAL_REACTION_STATION = "axial_reaction_station"
    """Thrust reaction: the reactor lies on the axis at an end station."""
    CONTACT_AT_EXTREME = "contact_at_extreme"
    """Travel limit: contact occurs at a declared extreme of the motion."""
    DISJOINT_SWEPT = "disjoint_swept"
    """Clearance: the relevant swept regions must not intersect."""
    CONTINUOUS_ROUTE = "continuous_route"
    """Flexible link: a routing path exists; remoteness is permitted."""
    EXTERIOR_REACHABLE = "exterior_reachable"
    """User contact: the surface is reachable from outside the boundary."""
    SEPARATED_ALONG_AXIS = "separated_along_axis"
    """Two reactions of the same kind on one element must act at distinct stations.

    Derived, not declared upstream: it is the mechanical reason a pair of supports
    cannot collapse onto one place, and it replaces assigning them opposite ends by
    iteration order.
    """


class ConstraintStatus(str, Enum):
    SATISFIED = "satisfied"
    VIOLATED = "violated"
    NOT_CHECKABLE = "not_checkable"
    """The placement model carries too little to decide. Never counted as a pass."""


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


class TopologyKind(str, Enum):
    """The kind of topological entity a localized relation lives on.

    A region says *which volume* something is in. Topology says *what it is
    attached to*: a face, an edge, an axis, a corridor, a shared contact surface.
    A hinge is not "somewhere in the closure region" - it is a line on an edge.
    Without this a consumer must re-derive the attachment, and two consumers will
    derive it differently.
    """

    FACE = "face"
    """A bounding surface of one host."""
    EDGE = "edge"
    """A line on a host, where two of its faces meet. Where a hinge lives."""
    AXIS = "axis"
    """A line through the product frame. Where a shaft, bearing or thread lives."""
    CORRIDOR = "corridor"
    """A prismatic path along an axis. Where a guide or a routed link lives."""
    CONTACT_SURFACE = "contact_surface"
    """The shared surface between two hosts. Where a catch or a stop acts."""
    VOLUME = "volume"
    """A bulk region, used for keep-clear rather than attachment."""
    BOUNDARY = "boundary"
    """The enclosure surface, as an access or crossing site."""


class JointType(str, Enum):
    """Kinematic pair types. Contact is deliberately absent.

    A contact is a *state-dependent interaction*, not a joint: it exists in some
    states and not others, and modelling it as a joint would assert a permanent
    freedom the mechanism does not have.
    """

    REVOLUTE = "revolute"
    PRISMATIC = "prismatic"
    HELICAL = "helical"
    FIXED = "fixed"


class KinematicJoint(BaseModel):
    """A pair between two bodies, with a symbolic coordinate.

    `q` is never a number here. It takes the values `q_min`, `between`, `q_max`,
    which is enough to distinguish canonical states without asserting an angle or
    a stroke.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    type: JointType
    parent: str
    child: str
    axis: str | None = None
    frame_on_parent: str = ""
    frame_on_child: str = ""
    why: str = ""


class CouplingKind(str, Enum):
    DIRECT = "direct"
    ROTATION_TO_TRANSLATION = "rotation_to_translation"
    ROTATION_TO_ROTATION = "rotation_to_rotation"
    INTERMITTENT = "intermittent"


class JointCoupling(BaseModel):
    """Linked motion between two joints.

    The *kind* of coupling is mechanism knowledge and is determined here; the
    ratio that governs it is not. `ratio_symbol` names the quantity Stage 05-06
    must resolve without asserting a value for it.
    """

    model_config = ConfigDict(extra="forbid")

    driver: str
    driven: str
    kind: CouplingKind
    ratio_symbol: str | None = None
    resolved_by: str = "Stage 05-06"
    why: str = ""


class InteractionKind(str, Enum):
    """A state-dependent relationship between two elements."""

    CONTACT = "contact"
    ENGAGEMENT = "engagement"
    DISENGAGEMENT = "disengagement"
    STOP_CONTACT = "stop_contact"
    CLEARANCE = "clearance"


class StateInteraction(BaseModel):
    """What two elements are doing to each other in one state."""

    model_config = ConfigDict(extra="forbid")

    state: str
    kind: InteractionKind
    between: tuple[str, str]
    why: str = ""


class PredicateKind(str, Enum):
    COVERS = "covers"
    CLEARS = "clears"
    ENGAGED = "engaged"
    RELEASED = "released"
    AT_LIMIT = "at_limit"


class StatePredicate(BaseModel):
    """One checkable claim about a state, and whether it holds."""

    model_config = ConfigDict(extra="forbid")

    state: str
    predicate: PredicateKind
    subject: str
    object: str | None = None
    holds: bool = False
    evidence: str = ""


class StatePose(BaseModel):
    """A body's qualitative extent in one state.

    The extent is an ordinal box per product axis: relative position, never a
    dimension. `via_joint` names the joint whose coordinate put it there.
    """

    model_config = ConfigDict(extra="forbid")

    state: str
    body: str
    extent: list[list[int]] = Field(default_factory=list)
    containment: str = "interior"
    via_joint: str | None = None
    joint_value: str | None = None
    why: str = ""


class TransitionEnvelope(BaseModel):
    """A conservative region a body may occupy while moving between two states.

    Conservative means it is the union of the endpoint extents plus the span
    between them - an over-estimate. It can show that two bodies **must** meet;
    it can never show that they cannot, so it is not a collision proof.
    """

    model_config = ConfigDict(extra="forbid")

    transition: str
    body: str
    extent: list[list[int]] = Field(default_factory=list)
    conservative: bool = True
    caveat: str = (
        "qualitative over-estimate: sufficient to expose a necessary overlap, "
        "never sufficient to certify clearance"
    )


class StateValidation(BaseModel):
    """Whether one transition is qualitatively feasible, and what is unresolved."""

    model_config = ConfigDict(extra="forbid")

    transition: str
    feasible: bool = False
    predicates: list[str] = Field(default_factory=list)
    unresolved_risks: list[str] = Field(default_factory=list)
    why: str = ""


class Containment(str, Enum):
    """Where a body sits relative to the enclosure boundary."""

    INTERIOR = "interior"
    BOUNDARY = "boundary"
    EXTERIOR = "exterior"
    SPANNING = "spanning"
    """Present on both sides - a shaft entering an enclosure."""


class RadialPosition(str, Enum):
    ON_AXIS = "on_axis"
    OFF_AXIS = "off_axis"


class BodyPlacement(BaseModel):
    """A body's qualitative position, derived from mechanical relationships.

    `span` is an ordinal interval on the principal axis: a relative position, not
    a coordinate and not a dimension. Two bodies sharing a slot are at the same
    place along the axis; nothing is said about how far apart anything is.
    """

    model_config = ConfigDict(extra="forbid")

    body: str
    containment: Containment
    radial: RadialPosition
    axis: str
    span: list[int] = Field(default_factory=list)
    derived_from: list[str] = Field(default_factory=list)
    """The mechanical facts that forced this placement, in the order applied."""


class UnresolvedLayoutChoice(BaseModel):
    """A position the mechanism constrains but does not fix.

    Recorded rather than silently resolved: a reader must be able to see that the
    layout is one of several equally valid ones.
    """

    model_config = ConfigDict(extra="forbid")

    subject: str
    question: str
    options: list[str] = Field(default_factory=list)
    blocks_stage05: bool = False
    why: str = ""


class LayoutConflict(BaseModel):
    """A relation the synthesized layout cannot satisfy.

    A conflict is never repaired by inventing a placement; it blocks Stage 05.
    """

    model_config = ConfigDict(extra="forbid")

    between: tuple[str, str]
    relation: str
    detail: str = ""
    why: str = ""


class LocationBasis(str, Enum):
    """The mechanical fact that determines where a localized feature sits.

    A feature is not placed and then labelled. It exists at a place *because* of a
    relationship, and the basis names which relationship put it there. If a
    feature cannot cite a basis, its location was assigned rather than derived.
    """

    SHARED_BOUNDARY = "shared_boundary"
    """Where two bodies meet - the closure line between a moving and a fixed one."""
    COMMON_AXIS = "common_axis"
    """The line two members share when one turns about the other."""
    COAXIAL_OVERLAP = "coaxial_overlap"
    """The span over which two coaxial members are simultaneously engaged."""
    MOTION_CORRIDOR = "motion_corridor"
    """The path a constrained body sweeps through its full travel."""
    MOTION_EXTREME = "motion_extreme"
    """An end of a body's travel, where a limit can act."""
    REACTION_SITE = "reaction_site"
    """Where a reaction force is transferred out of a moving element."""
    ENGAGED_STATE_CONTACT = "engaged_state_contact"
    """Where a retained and a retaining member meet in the state that is held."""
    ACCESS_CROSSING = "access_crossing"
    """Where an external agent crosses the enclosure boundary."""


class LocationDerivation(BaseModel):
    """Why a feature is where it is, and what about that is still free.

    `determined` distinguishes a location the mechanism fixes from one it merely
    constrains. Two bearings on one shaft must occupy distinct stations; which is
    at which end the mechanism does not say. Recording that as free is the honest
    answer - resolving it by declaration order asserts an engineering fact that
    was never derived.
    """

    model_config = ConfigDict(extra="forbid")

    basis: LocationBasis
    from_relationship: str
    participants: list[str] = Field(default_factory=list)
    determined: bool = True
    free_parameters: list[str] = Field(default_factory=list)
    alternatives: str | None = None
    why: str = ""


class TopologicalAnchor(BaseModel):
    """Where a relation or a local element is attached, topologically.

    Deliberately allows *partial* resolution. Narrowing "attached to the closure"
    down to "an edge of its +Z face" is real information even when which of the
    four edges remains a downstream freedom. Recording the freedom is honest;
    picking an edge here would be deciding geometry Stage 04 has no basis for.
    """

    model_config = ConfigDict(extra="forbid")

    kind: TopologyKind
    hosts: list[str] = Field(default_factory=list)
    axis: str | None = None
    faces: list[str] = Field(default_factory=list)
    station: str | None = None
    span: list[str] = Field(default_factory=list)
    resolved: bool = True
    """False when a free parameter remains - which edge, which side."""
    open_parameter: str | None = None
    derivation: LocationDerivation | None = None
    """The mechanical relationship this location follows from."""
    why: str = ""


class ArchitectureBound(BaseModel):
    """A quantitative bound, carried to the stages that must respect it."""

    model_config = ConfigDict(extra="forbid")

    requirement_id: str
    comparator: str
    lower: float | None = None
    upper: float | None = None
    unit: str
    precision: str = ""


class SpatialConstraint(BaseModel):
    """What a declared relationship demands of relative position.

    Emitted by Stage 02 because the demand is mechanical knowledge - a threaded
    pair is coaxial whatever product it sits in. Checked by Stage 04, which is the
    first stage holding a placement to check it against.

    Architecture level only: satisfaction here means the arrangement is not
    self-contradictory, never that the geometry closes.
    """

    model_config = ConfigDict(extra="forbid")

    between: tuple[str, str]
    relation: SpatialRelationKind
    source: str
    """The interface or obligation this came from, e.g. `interface:threaded_pair`."""
    axis: str | None = None
    at_station: str | None = None
    anchor: TopologicalAnchor | None = None
    """Where this relation is attached. Stage 05 must not have to re-derive it."""
    rationale: str = ""
    status: ConstraintStatus = ConstraintStatus.NOT_CHECKABLE
    detail: str = ""


class ArchitecturalInterface(BaseModel):
    """Where two conceptual elements meet, and what crosses."""

    model_config = ConfigDict(extra="forbid")

    between: tuple[str, str]
    kind: InterfaceKind
    transmits: str = ""
    crosses_boundary: bool = False
    """True when this interface passes through the enclosure boundary."""
    axis_relation: AxisRelation | None = None
    """How this interface constrains the two axes it joins.

    None means take the default for the kind. Stated explicitly where a family
    means something the kind alone does not say, e.g. a bevel mesh.
    """

    @property
    def axes(self) -> AxisRelation:
        return self.axis_relation or AXIS_RELATION_DEFAULT.get(
            self.kind, AxisRelation.UNCONSTRAINED)


AXIS_RELATION_DEFAULT.update({
    InterfaceKind.ROTATIONAL_JOINT: AxisRelation.IDENTICAL,
    InterfaceKind.FIXED_ATTACHMENT: AxisRelation.IDENTICAL,
    InterfaceKind.SLIDING_JOINT: AxisRelation.PARALLEL,
    InterfaceKind.THREADED_PAIR: AxisRelation.COLLINEAR,
    InterfaceKind.TOOTHED_MESH: AxisRelation.PARALLEL,
    InterfaceKind.CONTACT_PAIR: AxisRelation.PARALLEL,
    InterfaceKind.FLEXIBLE_LINK: AxisRelation.UNCONSTRAINED,
    InterfaceKind.USER_CONTACT: AxisRelation.UNCONSTRAINED,
})


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
    """Engineering role tags, e.g. load_bearing, moving_boundary, compliant.

    Carried so a consumer never has to re-query the knowledge base by mechanism id
    to learn what an element is for. Orthogonal to `motion_kind`.
    """
    motion_kind: MotionKind = MotionKind.UNSPECIFIED
    """How this element moves. `motions` declares one relation for the whole chain,
    so it can never say how an individual element moves."""
    element_class: ElementClass = ElementClass.BODY
    """Body, joint or feature. Determines whether it has bulk and can sweep."""
    form: str = "block"
    """Which solid realizes this element. Form and function are inseparable."""
    permits_motion: MotionKind = MotionKind.FIXED
    """For a JOINT: the relative motion it allows between the bodies it connects.

    This is where a motion axis is anchored. A body's `motion_kind` says how it
    moves; the joint says what allows it, so a declared motion with no permitting
    joint is ungrounded rather than merely undrawn.
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
    spatial_constraints: list[SpatialConstraint] = Field(default_factory=list)
    """What the declared interfaces and obligations demand of relative position."""
    states: list[FunctionalState] = Field(default_factory=list)
    """The functional states this architecture must be able to occupy."""
    transitions: list[StateTransition] = Field(default_factory=list)
    """How the mechanism moves between those states."""
    constrained_by: list[str] = Field(default_factory=list)
    """Requirements whose quantitative bounds constrain this architecture."""
    bounds: list["ArchitectureBound"] = Field(default_factory=list)
    """The bounds themselves. Recording only the ids left every downstream stage
    knowing that a dimension was constrained but not by what, so nothing could be
    sized from a requirement."""
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
    undecided_between: list[str] = Field(default_factory=list)
    """Candidates the available criteria cannot separate.

    Non-empty means `selected_id` was not derived. Every criterion Stage 02 has
    ranked these equal, so the one named is a recorded arbitrary pick, not a
    decision, and downstream stages must not present it as one. Resolving it
    needs a discriminating requirement, not a re-weighting.
    """

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
    motion_kind: MotionKind = MotionKind.UNSPECIFIED
    element_class: ElementClass = ElementClass.BODY
    permits_motion: MotionKind = MotionKind.FIXED
    form: str = "block"
    moving: bool = False
    external: bool = False
    rationale: str = ""


class AccessAgent(str, Enum):
    """Who or what must reach an internal target."""

    USER_HAND = "user_hand"
    PAYLOAD = "payload"
    SERVICE_TOOL = "service_tool"
    ASSEMBLY_TOOL = "assembly_tool"
    CONSUMABLE = "consumable"
    STORED_CONTENT = "stored_content"


class AccessMode(str, Enum):
    REACH = "reach"
    ACTUATE = "actuate"
    INSERT = "insert"
    REMOVE = "remove"
    LOAD = "load"
    VIEW = "view"


class AccessPath(BaseModel):
    """A route an external subject must take to reach something inside.

    Required paths are derived from structured facts - an access obligation on an
    internal element, an externally originating load path, a piece installed after
    the boundary closes. A required path with no boundary interface is reported,
    never resolved by inventing an opening.
    """

    model_config = ConfigDict(extra="forbid")

    agent: AccessAgent
    mode: AccessMode
    target: str
    source_region: str | None = None
    boundary_interface: str | None = None
    destination_region: str | None = None
    required: bool = True
    required_direction: str | None = None
    clearance_need: str | None = None
    satisfied: bool = False
    unmet_reason: str | None = None


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
    axis_relation: AxisRelation | None = None
    """Carried from the architectural interface; None takes the kind's default.

    Dropped here previously, which meant the constraint an interface places on
    two axes existed in Stage 02 and was gone by Stage 04 - the stage that
    actually assigns axes.
    """

    @property
    def axes(self) -> AxisRelation:
        return self.axis_relation or AXIS_RELATION_DEFAULT.get(
            self.kind, AxisRelation.UNCONSTRAINED)


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
    access_paths: list[AccessPath] = Field(default_factory=list)
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
class ProductAxis(str, Enum):
    """An axis of the *product* frame. Carries no world orientation.

    Nothing here means up, down, front or back. The frame is a labelling of the
    product's own three directions; which one points at gravity is a later
    decision and may differ per instance.
    """

    X = "x"
    Y = "y"
    Z = "z"


class SignedFace(str, Enum):
    """A face of the product envelope, named by the product-frame axis it faces."""

    X_POS = "+X"
    X_NEG = "-X"
    Y_POS = "+Y"
    Y_NEG = "-Y"
    Z_POS = "+Z"
    Z_NEG = "-Z"

    @property
    def axis(self) -> ProductAxis:
        return ProductAxis(self.value[1].lower())

    @property
    def opposite(self) -> "SignedFace":
        return SignedFace(("-" if self.value[0] == "+" else "+") + self.value[1])


class FaceRole(str, Enum):
    """What a face is for. A role never forces a face to be exclusive.

    Two roles may share one face - a box opened and loaded through the same
    aperture is normal. Sharing is recorded explicitly so it is a decision rather
    than an accident.
    """

    OPERATING = "operating"
    LOADING = "loading"
    SERVICE = "service"
    SEATING = "seating"
    UNASSIGNED = "unassigned"


class AxisStation(str, Enum):
    """Where along an axis something sits. Geometric, not functional.

    Deliberately not chain-start / chain-end: the two physical ends of an axis are
    what a limit, a bearing or a stop acts at, and those are independent of which
    end the input happens to enter.
    """

    NEGATIVE_END = "negative_end"
    MID_SPAN = "mid_span"
    POSITIVE_END = "positive_end"
    RANGE_MIN = "range_min"
    RANGE_MAX = "range_max"


class SweptShape(str, Enum):
    """The qualitative shape of a swept region. Never a dimension."""

    CYLINDRICAL = "cylindrical"
    PRISMATIC = "prismatic"
    HELICAL = "helical"
    DEFORMATION = "deformation"
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
    ASSEMBLY_UNREACHABLE = "assembly_unreachable"
    CONSTRAINT_VIOLATION = "constraint_violation"
    UNGROUNDED_MOTION = "ungrounded_motion"
    UNHOSTED_ELEMENT = "unhosted_element"
    ACCESS_PATH_UNMET = "access_path_unmet"
    MOTION_UNSPECIFIED = "motion_unspecified"
    INVALID_STATE_TRANSITION = "invalid_state_transition"
    """The declared motion does not carry the mechanism between its states."""
    BROKEN_MOTION_CHAIN = "broken_motion_chain"
    """Motion cannot propagate from the input to the output."""


class ProductReferenceFrame(BaseModel):
    """Three signed product axes, plus what each one means.

    The primary axis is the one the principal motion runs along. The frame states
    that relationship; it never states which way the product faces in the world.
    """

    model_config = ConfigDict(extra="forbid")

    primary_axis: ProductAxis = ProductAxis.Z
    secondary_axis: ProductAxis = ProductAxis.Y
    lateral_axis: ProductAxis = ProductAxis.X
    primary_motion: MotionKind = MotionKind.UNSPECIFIED
    primary_element: str | None = None
    derived_from: str = ""
    axis_meaning: dict[str, str] = Field(default_factory=dict)


class BoundaryFace(BaseModel):
    """One face of the envelope, its roles, and what sits on it."""

    model_config = ConfigDict(extra="forbid")

    face: SignedFace
    roles: list[FaceRole] = Field(default_factory=list)
    hosts: list[str] = Field(default_factory=list)
    shared: bool = False
    """True when more than one role was deliberately assigned to this face."""
    rationale: str = ""


class RegionPlacement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    region: str
    zone: SpatialZone
    relative_to: str | None = None
    why: str = ""
    axis_station: AxisStation | None = None
    face: SignedFace | None = None
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
    motion_kind: MotionKind = MotionKind.UNSPECIFIED
    element_class: ElementClass = ElementClass.BODY
    permits_motion: MotionKind = MotionKind.FIXED
    attached_to: list[str] = Field(default_factory=list)
    """Bodies this joint connects, or the host body this feature sits on.

    A joint and a feature have no independent position; this is what locates them.
    """
    anchor: TopologicalAnchor | None = None
    """Which topological entity of its hosts this element is attached to."""
    engineering_roles: list[str] = Field(default_factory=list)
    axis_station: AxisStation | None = None
    face: SignedFace | None = None


class SweptVolumeSpec(BaseModel):
    """A moving element's swept region, classified by how it moves."""

    model_config = ConfigDict(extra="forbid")

    region: str
    element: str
    motion: MotionKind
    shape: SweptShape
    axis: ProductAxis | None = None
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

    reference_frame: ProductReferenceFrame | None = None
    boundary_faces: list[BoundaryFace] = Field(default_factory=list)
    spatial_constraints: list[SpatialConstraint] = Field(default_factory=list)
    kinematic_joints: list[KinematicJoint] = Field(default_factory=list)
    joint_couplings: list[JointCoupling] = Field(default_factory=list)
    state_poses: list[StatePose] = Field(default_factory=list)
    state_interactions: list[StateInteraction] = Field(default_factory=list)
    state_predicates: list[StatePredicate] = Field(default_factory=list)
    transition_envelopes: list[TransitionEnvelope] = Field(default_factory=list)
    state_validations: list[StateValidation] = Field(default_factory=list)
    body_placements: list[BodyPlacement] = Field(default_factory=list)
    unresolved_layout_choices: list[UnresolvedLayoutChoice] = Field(default_factory=list)
    layout_conflicts: list[LayoutConflict] = Field(default_factory=list)
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
