"""DesignSession and IterationRecord.

The session is the authoritative index of a design process. It must never be
sent wholesale to an LLM (Rule TOK-2); ``llm_slice`` builds a minimal view.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from assy.domain.common import DomainObject


class SessionStatus(str, Enum):
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"
    BUDGET_EXHAUSTED = "budget_exhausted"


class IterationRecord(BaseModel):
    """Compact history of one iteration. Immutable; never holds raw arrays."""

    model_config = ConfigDict(extra="forbid")

    index: int
    parent: int | None = None
    applied_revision: str | None = None
    changed_objects: list[str] = Field(default_factory=list)
    metric_summary: dict[str, float] = Field(default_factory=dict)
    evaluation_summary: dict[str, str] = Field(default_factory=dict)
    outcome: str = ""
    is_best: bool = False
    artifacts: list[str] = Field(default_factory=list)


class DesignSession(DomainObject):
    status: SessionStatus = SessionStatus.RUNNING
    current_iteration: int = 0
    objects: dict[str, str] = Field(default_factory=dict)  # object type -> id
    iterations: list[IterationRecord] = Field(default_factory=list)
    best_iteration: int | None = None
    blocked_directions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    artifact_dir: str = "out"

    def register(self, obj: DomainObject) -> None:
        self.objects[type(obj).__name__] = obj.meta.object_id

    def llm_slice(self) -> dict[str, Any]:
        """Minimal context view. Never the whole session (Rule TOK-2/TOK-7)."""
        recent = self.iterations[-2:]
        best = (
            self.iterations[self.best_iteration]
            if self.best_iteration is not None and self.best_iteration < len(self.iterations)
            else None
        )
        return {
            "status": self.status.value,
            "iteration": self.current_iteration,
            "recent": [r.model_dump(include={"index", "outcome", "metric_summary"}) for r in recent],
            "best": best.model_dump(include={"index", "outcome"}) if best else None,
            "blocked": self.blocked_directions,
        }
