"""Domain objects produced by Stages 01-04.

These are the authoritative engineering inputs to Stage 05. The authority order
is RequirementSpec > MechanicalArchitecture > ProductArchitecture > Concept
(STAGE_05 section 3); the concept visualisation is explicitly non-authoritative.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

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


class Requirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    kind: RequirementKind
    origin: RequirementOrigin
    statement: str
    target: Quantity | None = None
    tolerance: Quantity | None = None
    comparator: str | None = None  # ">=", "<=", "==", "between"
    upper: Quantity | None = None
    priority: int = 3  # 1 highest
    verifiable: bool = True

    @property
    def is_quantitative(self) -> bool:
        return self.target is not None


class RequirementSpec(DomainObject):
    """Structured engineering meaning of the user's request."""

    source_text: str
    product_intent: str
    requirements: list[Requirement] = Field(default_factory=list)
    operating_scenarios: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)

    def by_id(self, rid: str) -> Requirement:
        for r in self.requirements:
            if r.id == rid:
                return r
        raise KeyError(rid)

    @property
    def quantitative(self) -> list[Requirement]:
        return [r for r in self.requirements if r.is_quantitative]


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
