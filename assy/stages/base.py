"""Stage protocol.

Every stage answers exactly one engineering question (Rule A-1) and communicates
only through validated structured data (Rule A-3). Stages never read another
stage's prompt or internal state (Rule A-4).

Reasoning stages carry a ``reasoner`` seam. The vertical slice ships a
deterministic reasoner so the whole pipeline is reproducible offline
(Rule CODE-10); an LLM-backed reasoner can be substituted without touching
any stage's interface.
"""

from __future__ import annotations

import abc
from typing import Any, ClassVar

from assy.domain.common import Stage as StageId


class StageError(RuntimeError):
    """Raised when a stage cannot produce a valid output object."""

    def __init__(self, stage: str, message: str, structured: dict[str, Any] | None = None):
        super().__init__(f"[{stage}] {message}")
        self.stage = stage
        self.structured = structured or {}


class PipelineStage(abc.ABC):
    """Base class for all pipeline stages."""

    stage_id: ClassVar[StageId]
    question: ClassVar[str]
    produces: ClassVar[str]

    @abc.abstractmethod
    def run(self, **inputs: Any) -> Any:
        """Consume upstream domain objects, produce this stage's object."""

    def __repr__(self) -> str:  # pragma: no cover - display only
        return f"<{type(self).__name__} {self.stage_id.value}>"


class Reasoner(abc.ABC):
    """The LLM seam.

    Stage code depends on this interface, never on a provider SDK. Rule L-4
    requires every output to validate against a schema, which is why the return
    type is a domain object rather than free text.
    """

    @abc.abstractmethod
    def propose(self, task: str, context: dict[str, Any], options: list[Any]) -> Any:
        """Choose among structured options, or propose a new structured option."""


class DeterministicReasoner(Reasoner):
    """Offline stand-in: picks by declared score, then by stable order.

    This is a placeholder, and deliberately a transparent one - it never invents
    engineering content, so a placeholder decision can never be mistaken for
    engineering evidence (Rule L-5).
    """

    def propose(self, task: str, context: dict[str, Any], options: list[Any]) -> Any:
        if not options:
            raise StageError("reasoner", f"no options offered for task: {task}")
        scored = [o for o in options if getattr(o, "score", None) is not None]
        if scored:
            return max(scored, key=lambda o: o.score)
        return options[0]
