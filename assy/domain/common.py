"""Shared domain vocabulary.

Implements DOMAIN_SPECIFICATION section 5 (common metadata) and section 18
(versioning and provenance) for every top-level engineering object.

Units are millimetres, newtons, and newton-millimetres unless a field states
otherwise. Units are never implicit on a quantity that crosses a stage boundary.
"""

from __future__ import annotations

import itertools
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

_COUNTERS: dict[str, itertools.count] = {}


def new_id(prefix: str) -> str:
    """Deterministic, monotonic identifier.

    Deterministic rather than a UUID so that identical inputs produce identical
    objects (Rule CODE-10). ``reset_ids`` restores the initial state between runs.
    """
    counter = _COUNTERS.setdefault(prefix, itertools.count(1))
    return f"{prefix}-{next(counter):03d}"


def reset_ids() -> None:
    """Clear all identifier counters so a fresh run reproduces prior ids."""
    _COUNTERS.clear()


class Stage(str, Enum):
    """The producing stage of a domain object. One owner per object (section 4.2)."""

    REQUIREMENT = "s01_requirement_interpreter"
    MECHANICAL = "s02_mechanical_architecture"
    PRODUCT = "s03_product_architecture"
    CONCEPT = "s04_concept_visualization"
    ENGINEERING = "s05_engineering_integration"
    SOLVER = "s06_parametric_solver"
    CAD = "s07_cad_builder"
    SIM_PLAN = "s08_simulation_plan"
    SIM_RUN = "s09_simulation_runner"
    METRICS = "s10_metric_extraction"
    EVALUATION = "s11_requirement_evaluation"
    REVISION = "s12_revision_routing"
    SESSION = "session_manager"


class ObjectMeta(BaseModel):
    """Common metadata carried by every persisted top-level object."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "0.1.0"
    object_id: str
    design_id: str = "design-001"
    producer: Stage
    parent_id: str | None = None
    revision_reason: str | None = None
    notes: list[str] = Field(default_factory=list)


class Provenance(BaseModel):
    """Why a piece of engineering information exists.

    Every commitment must be traceable to the requirement it serves, the problem
    it resolves, and the method that justified it (STAGE_05 section 7.5).
    """

    model_config = ConfigDict(extra="forbid")

    requirements: list[str] = Field(default_factory=list)
    problem_id: str | None = None
    resolution_id: str | None = None
    method: str | None = None
    depends_on_assumptions: list[str] = Field(default_factory=list)
    supported_by_checks: list[str] = Field(default_factory=list)


class Quantity(BaseModel):
    """A number that knows its unit. Units stay explicit across stage boundaries."""

    model_config = ConfigDict(extra="forbid")

    value: float
    unit: str

    def __str__(self) -> str:  # pragma: no cover - display only
        return f"{self.value:g} {self.unit}"


class DomainObject(BaseModel):
    """Base for every top-level object. Immutable once produced (section 4.4)."""

    model_config = ConfigDict(extra="forbid")

    meta: ObjectMeta

    def summary(self) -> dict[str, Any]:
        """Compact form for logging and for token-scoped LLM context (Rule TOK-1)."""
        return {"object_id": self.meta.object_id, "producer": self.meta.producer.value}
