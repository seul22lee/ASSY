"""Stage 01 reasoning implementation backed by a language model.

This is *an* implementation of the Stage 01 specification, not the specification
itself. It satisfies the contract in `STAGE_01_REQUIREMENT_INTERPRETER.md`; the
deterministic placeholder in `s01_requirement.py` remains the executable baseline.

Rule L-4: every model output must validate against the schema. Structurally invalid
output is rejected and retried with the error, never repaired by hand.

The client is intentionally minimal and provider-agnostic at the call site: stage
code depends on `chat()`, not on a vendor SDK.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, ClassVar

from pydantic import ValidationError

from assy.domain.common import ObjectMeta, Stage, new_id
from assy.domain.upstream import (
    Assumption,
    DiscoveryOutcome,
    DiscoveryState,
    ClauseDisposition,
    DesignFreedom,
    FreedomKind,
    OperatingScenario,
    RelationKind,
    Requirement,
    BehaviourSpec,
    Continuity,
    QuantityKind,
    RequirementBound,
    RequirementKind,
    RequirementOrigin,
    RequirementRelation,
    RequirementSpec,
    SourceClause,
    SourceOrigin,
    Unknown,
    VerificationIntent,
    VerificationKind,
)
from assy.stages.base import PipelineStage, StageError
from assy.stages.s01_prompt import PROMPT_VERSION, build_messages

MAX_ATTEMPTS = 3


class LLMUnavailable(RuntimeError):
    """No reasoning backend could be reached."""


@dataclass
class LLMConfig:
    backend: str = field(default_factory=lambda: os.environ.get("ASSY_LLM_BACKEND", "ollama"))
    model: str = field(default_factory=lambda: os.environ.get("ASSY_LLM_MODEL", "qwen3-coder:latest"))
    host: str = field(default_factory=lambda: os.environ.get("OLLAMA_HOST", "http://localhost:11434"))
    temperature: float = 0.0
    num_ctx: int = 16384
    timeout_s: float = 900.0


@dataclass
class LLMCall:
    content: str
    prompt_tokens: int = 0
    output_tokens: int = 0
    seconds: float = 0.0


def chat(messages: list[dict[str, str]], cfg: LLMConfig) -> LLMCall:
    """One completion. Ollama-backed; JSON mode where the backend supports it."""
    if cfg.backend != "ollama":
        raise LLMUnavailable(f"backend '{cfg.backend}' is not implemented")
    payload = {
        "model": cfg.model,
        "messages": messages,
        "stream": False,
        "format": "json",
        "options": {"temperature": cfg.temperature, "num_ctx": cfg.num_ctx},
    }
    req = urllib.request.Request(
        f"{cfg.host}/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=cfg.timeout_s) as resp:
            body = json.load(resp)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise LLMUnavailable(f"{cfg.backend}/{cfg.model}: {exc}") from exc
    return LLMCall(
        content=body.get("message", {}).get("content", ""),
        prompt_tokens=int(body.get("prompt_eval_count") or 0),
        output_tokens=int(body.get("eval_count") or 0),
        seconds=time.time() - started,
    )


# --------------------------------------------------------------------------
# Mapping model output -> domain objects
# --------------------------------------------------------------------------
def _json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?|\n?```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def _enum(cls, value, default):
    try:
        return cls(str(value).strip().lower())
    except (ValueError, AttributeError):
        return default


def _bound(raw: dict[str, Any]) -> RequirementBound | None:
    """Build the bound object, or None. Never repairs an incomplete interval.

    An incomplete bound raises, the attempt is rejected, and the model is asked
    again (Rule L-4). Silently filling a missing endpoint here would recreate the
    exact defect SD-8 exists to prevent.
    """
    b = raw.get("bound")
    if not isinstance(b, dict):
        return None
    unit = str(b.get("unit") or "").strip()
    if not unit:
        return None
    def num(key):
        v = b.get(key)
        return None if v is None else float(v)
    return RequirementBound(
        comparator=str(b.get("comparator") or ">=").strip(),
        lower=num("lower"),
        upper=num("upper"),
        unit=unit,
        tolerance=num("tolerance"),
        approximate=bool(b.get("approximate", False)),
    )


def _as_list(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(x) for x in raw if x is not None]
    return []


def to_spec(data: dict[str, Any], request: str) -> RequirementSpec:
    """Map the model's JSON onto the Stage 01 domain objects.

    Deliberately faithful rather than corrective: identifiers, dispositions, and
    references are taken as produced. Repairing them here would hide exactly the
    contract violations the validators exist to surface.
    """
    clauses = [
        SourceClause(
            id=str(c.get("id") or new_id("C")),
            text=str(c.get("text", "")),
            source=_enum(SourceOrigin, c.get("source"), SourceOrigin.REQUEST),
            disposition=_enum(ClauseDisposition, c.get("disposition"), ClauseDisposition.CONTEXT),
        )
        for c in data.get("clauses", [])
        if isinstance(c, dict)
    ]

    requirements: list[Requirement] = []
    for r in data.get("requirements", []):
        if not isinstance(r, dict):
            continue
        v = r.get("verification") if isinstance(r.get("verification"), dict) else None
        verification = None
        if v:
            verification = VerificationIntent(
                kind=_enum(VerificationKind, v.get("kind"), VerificationKind.NOT_YET_VERIFIABLE),
                observable=(v.get("observable") or None),
                condition=(v.get("condition") or None),
                reason=(v.get("reason") or None),
            )
        try:
            priority = int(r.get("priority", 3))
        except (TypeError, ValueError):
            priority = 3
        bound = _bound(r)
        bh = r.get("behaviour") if isinstance(r.get("behaviour"), dict) else None
        behaviour = None
        if bh:
            behaviour = BehaviourSpec(
                actor=str(bh.get("actor", "")),
                action=str(bh.get("action", "")),
                object=str(bh.get("object", "")),
                condition=(bh.get("condition") or None),
                input_kind=_enum(QuantityKind, bh.get("input_kind"), QuantityKind.NONE),
                output_kind=_enum(QuantityKind, bh.get("output_kind"), QuantityKind.NONE),
                continuity=_enum(Continuity, bh.get("continuity"), Continuity.SINGLE_EVENT),
                reversible=bool(bh.get("reversible", False)),
            )
        requirements.append(
            Requirement(
                id=str(r.get("id") or new_id("REQ")),
                kind=_enum(RequirementKind, r.get("kind"), RequirementKind.FUNCTIONAL),
                origin=_enum(RequirementOrigin, r.get("origin"), RequirementOrigin.USER_STATED),
                statement=str(r.get("statement", "")).strip(),
                bound=bound,
                behaviour=behaviour,
                priority=priority,
                derived_from=_as_list(r.get("derived_from")),
                verification=verification,
            )
        )

    freedoms = [
        DesignFreedom(
            id=str(f.get("id") or new_id("F")),
            kind=_enum(FreedomKind, f.get("kind"), FreedomKind.UNCONSTRAINED),
            subject=str(f.get("subject", "")),
            statement=str(f.get("statement", "")),
            origin=_enum(RequirementOrigin, f.get("origin"), RequirementOrigin.USER_STATED),
            derived_from=_as_list(f.get("derived_from")),
        )
        for f in data.get("freedoms", [])
        if isinstance(f, dict)
    ]

    relations = [
        RequirementRelation(
            kind=_enum(RelationKind, rel.get("kind"), RelationKind.DEPENDS_ON),
            source=str(rel.get("source", "")),
            target=str(rel.get("target", "")),
            rationale=str(rel.get("rationale", "")),
        )
        for rel in data.get("relations", [])
        if isinstance(rel, dict)
    ]

    scenarios = [
        OperatingScenario(
            id=str(s.get("id") or new_id("SCN")),
            name=str(s.get("name", "")),
            description=str(s.get("description", "")),
            applies_to=_as_list(s.get("applies_to")),
            derived_from=_as_list(s.get("derived_from")),
        )
        for s in data.get("operating_scenarios", [])
        if isinstance(s, dict)
    ]

    assumptions = [
        Assumption(
            id=str(a.get("id") or new_id("AS")),
            statement=str(a.get("statement", "")),
            stands_in_for=(a.get("stands_in_for") or None),
            origin=_enum(RequirementOrigin, a.get("origin"), RequirementOrigin.INFERRED),
            derived_from=_as_list(a.get("derived_from")),
        )
        for a in data.get("assumptions", [])
        if isinstance(a, dict)
    ]

    unknowns = [
        Unknown(
            id=str(u.get("id") or new_id("U")),
            subject=str(u.get("subject", "")),
            reason=str(u.get("reason", "")),
            affects=_as_list(u.get("affects")),
            resolvable_by=str(u.get("resolvable_by", "")),
            derived_from=_as_list(u.get("derived_from")),
        )
        for u in data.get("unknowns", [])
        if isinstance(u, dict)
    ]

    return RequirementSpec(
        meta=ObjectMeta(object_id=new_id("SPEC"), producer=Stage.REQUIREMENT),
        source_text=request,
        product_intent=str(data.get("product_intent", "")).strip(),
        clauses=clauses,
        requirements=requirements,
        operating_scenarios=scenarios,
        assumptions=assumptions,
        unknowns=unknowns,
        freedoms=freedoms,
        relations=relations,
        user_intent_summary=str(data.get("user_intent_summary", "")).strip(),
        discovery_outcomes=[
            DiscoveryOutcome(
                discovery=str(d.get("discovery", "")),
                state=_enum(DiscoveryState, d.get("state"), DiscoveryState.EXPLICITLY_ABSENT),
                reason=str(d.get("reason", "")),
            )
            for d in (data.get("discovery_outcomes") or data.get("declared_absent") or [])
            if isinstance(d, dict)
        ],
    )


@dataclass
class RunTrace:
    """What the call cost and how many attempts it took. For repeatability metrics."""

    attempts: int = 0
    prompt_tokens: int = 0
    output_tokens: int = 0
    seconds: float = 0.0
    errors: list[str] = field(default_factory=list)
    raw: str = ""


class LLMRequirementInterpreter(PipelineStage):
    """Stage 01 implemented by reasoning rather than pattern matching."""

    stage_id: ClassVar[Stage] = Stage.REQUIREMENT
    question: ClassVar[str] = "What engineering problem is actually being asked?"
    produces: ClassVar[str] = "RequirementSpec"
    prompt_version: ClassVar[str] = PROMPT_VERSION

    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig()
        self.trace = RunTrace()

    def run(
        self,
        *,
        request: str,
        product_intent: str = "",
        clarifications: list[str] | None = None,
    ) -> RequirementSpec:
        messages = build_messages(request, clarifications)
        trace = RunTrace()
        last: Exception | None = None

        for attempt in range(1, MAX_ATTEMPTS + 1):
            trace.attempts = attempt
            call = chat(messages, self.config)
            trace.prompt_tokens += call.prompt_tokens
            trace.output_tokens += call.output_tokens
            trace.seconds += call.seconds
            trace.raw = call.content
            try:
                spec = to_spec(_json_object(call.content), request)
                if product_intent and not spec.product_intent:
                    spec.product_intent = product_intent
                self.trace = trace
                return spec
            except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
                last = exc
                trace.errors.append(f"attempt {attempt}: {type(exc).__name__}: {exc}")
                messages = messages + [
                    {"role": "assistant", "content": call.content[:2000]},
                    {
                        "role": "user",
                        "content": (
                            f"That output was not valid against the contract: {exc}. "
                            "Return corrected JSON only, in exactly the specified shape."
                        ),
                    },
                ]

        self.trace = trace
        raise StageError(
            self.stage_id.value,
            f"model output failed the schema after {MAX_ATTEMPTS} attempts: {last}",
            {"errors": trace.errors},
        )
