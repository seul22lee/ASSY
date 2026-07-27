"""Domain objects produced by Stages 06-12.

Boundaries enforced here (DOMAIN_SPECIFICATION sections 9-15):
  SolvedDesign        answers "what values satisfy the plan", not "does it work"
  CADArtifactManifest answers "what was built", not "how to test it"
  SimulationResult    answers "what did the simulator produce", not "what metric"
  MetricReport        answers "what was measured", not "is it acceptable"
  EvaluationReport    answers "which requirements passed", not "what to change"
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from assy.domain.common import DomainObject


# --------------------------------------------------------------------------
# Stage 06 - SolvedDesign
# --------------------------------------------------------------------------
class SolveStatus(str, Enum):
    SOLVED = "solved"
    INFEASIBLE = "infeasible"
    UNDERDETERMINED = "underdetermined"
    FAILED = "failed"


class SolvedParameter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    value: float
    unit: str
    commitment_id: str
    derived: bool = False


class ConstraintOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    commitment_id: str
    expression: str
    satisfied: bool
    residual: float | None = None
    margin: float | None = None


class SolvedDesign(DomainObject):
    status: SolveStatus
    parameters: list[SolvedParameter] = Field(default_factory=list)
    satisfied: list[ConstraintOutcome] = Field(default_factory=list)
    violated: list[ConstraintOutcome] = Field(default_factory=list)
    objective_values: dict[str, float] = Field(default_factory=dict)
    diagnostics: list[str] = Field(default_factory=list)
    source_definition_id: str = ""

    def value(self, name: str) -> float:
        for p in self.parameters:
            if p.name == name:
                return p.value
        raise KeyError(name)

    def as_dict(self) -> dict[str, float]:
        return {p.name: p.value for p in self.parameters}


# --------------------------------------------------------------------------
# Stage 07 - CADArtifactManifest
# --------------------------------------------------------------------------
class BuildStatus(str, Enum):
    OK = "ok"
    PARTIAL = "partial"
    FAILED = "failed"


class PartArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    part_id: str  # stable semantic identity from Stage 05
    name: str
    step_path: str | None = None
    mesh_path: str | None = None
    volume_mm3: float | None = None
    mass_g: float | None = None
    bbox_mm: list[float] = Field(default_factory=list)
    material: str | None = None
    placement_mm: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])


class CADArtifactManifest(DomainObject):
    """Records what was deterministically built.

    ``semantic_map`` is generated *by* the builder and must never become the
    authority for upstream identity (STAGE_05 section 21).
    """

    status: BuildStatus
    parts: list[PartArtifact] = Field(default_factory=list)
    assembly_path: str | None = None
    semantic_map: dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)
    source_solved_id: str = ""


# --------------------------------------------------------------------------
# Stage 08/09 - Simulation
# --------------------------------------------------------------------------
class ValidationBackend(str, Enum):
    """No single backend has universal authority (SYSTEM_ARCHITECTURE section 16).

    The correct method depends on the physics being evaluated: rigid-body contact
    goes to MuJoCo, compliant-element behaviour goes to closed-form analysis.
    """

    MUJOCO = "mujoco"
    ANALYTICAL = "analytical"


class SimTest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    backend: ValidationBackend = ValidationBackend.MUJOCO
    phenomenon: str = ""
    """The physical phenomenon under test, e.g. 'compliant_retention'."""
    validity_domain: list[str] = Field(default_factory=list)
    """What this method can legitimately conclude about. Claims outside it are invalid."""
    serves_requirements: list[str] = Field(default_factory=list)
    duration_s: float = 3.0
    timestep_s: float = 0.002
    actuation: dict[str, float] = Field(default_factory=dict)
    initial_conditions: dict[str, float] = Field(default_factory=dict)
    observables: list[str] = Field(default_factory=list)
    termination: str = "time"
    validity_conditions: list[str] = Field(default_factory=list)


class SimulationPlan(DomainObject):
    tests: list[SimTest] = Field(default_factory=list)
    model_path: str | None = None
    contact_assumptions: dict[str, float] = Field(default_factory=dict)
    source_manifest_id: str = ""
    modelling_limitations: list[str] = Field(default_factory=list)
    """Explicit statements of what the chosen models cannot represent."""

    def by_backend(self, backend: ValidationBackend) -> list[SimTest]:
        return [t for t in self.tests if t.backend is backend]


class SimRunStatus(str, Enum):
    COMPLETED = "completed"
    UNSTABLE = "unstable"
    ERROR = "error"
    NOT_RUN = "not_run"


class SimTestResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    test_id: str
    status: SimRunStatus
    backend: ValidationBackend = ValidationBackend.MUJOCO
    simulator: str = "mujoco"
    simulator_version: str = ""
    duration_s: float = 0.0
    trajectory_path: str | None = None
    events: list[str] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
    # Compact deterministic summaries. Raw arrays stay on disk (Rule TOK-4).
    series_summary: dict[str, float] = Field(default_factory=dict)


class SimulationResult(DomainObject):
    results: list[SimTestResult] = Field(default_factory=list)
    source_plan_id: str = ""


# --------------------------------------------------------------------------
# Stage 10 - MetricReport
# --------------------------------------------------------------------------
class Metric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    value: float
    unit: str
    method: str
    source_test: str
    entities: list[str] = Field(default_factory=list)
    valid: bool = True
    invalidity_reason: str | None = None


class MetricReport(DomainObject):
    metrics: list[Metric] = Field(default_factory=list)
    source_result_id: str = ""

    def by_name(self, name: str) -> Metric | None:
        for m in self.metrics:
            if m.name == name:
                return m
        return None


# --------------------------------------------------------------------------
# Stage 11 - EvaluationReport
# --------------------------------------------------------------------------
class ReqStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    INVALID_TEST = "invalid_test"
    NOT_EVALUATED = "not_evaluated"


class RequirementOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirement_id: str
    status: ReqStatus
    observed: float | None = None
    target: float | None = None
    unit: str | None = None
    margin: float | None = None
    evidence: list[str] = Field(default_factory=list)
    note: str = ""


class EvaluationReport(DomainObject):
    overall: ReqStatus
    outcomes: list[RequirementOutcome] = Field(default_factory=list)
    source_metric_id: str = ""

    @property
    def failed(self) -> list[RequirementOutcome]:
        return [o for o in self.outcomes if o.status == ReqStatus.FAIL]

    @property
    def insufficient(self) -> list[RequirementOutcome]:
        return [o for o in self.outcomes if o.status == ReqStatus.INSUFFICIENT_EVIDENCE]


# --------------------------------------------------------------------------
# Stage 12 - RevisionDirective
# --------------------------------------------------------------------------
class RestartStage(str, Enum):
    PARAMETER = "parameter"
    ENGINEERING = "engineering_integration"
    PRODUCT = "product_architecture"
    MECHANICAL = "mechanical_architecture"
    REQUIREMENT = "requirement_clarification"
    NONE = "none"


class RevisionDirective(DomainObject):
    """The smallest justified change and the earliest stage that must rerun.

    Routing is derived from the Stage 05 dependency graph; no separate hidden
    revision mechanism (STAGE_05 section 9.5).
    """

    restart: RestartStage
    diagnosis: str = ""
    evidence: list[str] = Field(default_factory=list)
    preserve: list[str] = Field(default_factory=list)
    allowed_scope: list[str] = Field(default_factory=list)
    target_commitments: list[str] = Field(default_factory=list)
    expected_effects: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    confidence: float = 0.5
    source_evaluation_id: str = ""
