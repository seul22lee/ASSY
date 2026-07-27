"""Stage 01 - Requirement Interpreter.

Question: what must the product accomplish?

PLACEHOLDER IMPLEMENTATION. Structured extraction over the request text stands
in for an LLM. It is generic pattern matching over quantities and functional
keywords, not benchmark branching (Rule BM-1) - but it is shallow, and richer
interpretation is exactly what the LLM-backed reasoner should replace.
"""

from __future__ import annotations

import re
from typing import ClassVar

from assy.domain.common import ObjectMeta, Stage, new_id
from assy.domain.upstream import (
    Assumption,
    ClauseDisposition,
    OperatingScenario,
    Requirement,
    RequirementBound,
    RequirementKind,
    RequirementOrigin,
    RequirementSpec,
    SourceClause,
    SourceOrigin,
    Unknown,
    VerificationIntent,
    VerificationKind,
)
from assy.stages.base import PipelineStage

# Generic functional vocabulary -> requirement templates.
CONCEPTS: list[tuple[str, RequirementKind, str]] = [
    (r"\benclos(e|ed|ure)\b", RequirementKind.FUNCTIONAL, "Mechanism is enclosed within the housing"),
    (r"\bsafe\b|\bsafety\b", RequirementKind.SAFETY, "Product is safe to operate"),
    (r"\bassembl", RequirementKind.ASSEMBLY, "Product is practical to assemble"),
    (r"\bmanufactur", RequirementKind.MANUFACTURING, "Product is practical to manufacture"),
    (r"\bcrank\b|\bhand[- ]?driven\b|\bmanual\b", RequirementKind.USABILITY, "Manual user input drives the mechanism"),
    (r"\bjam(ming)?\b|\bunstable\b", RequirementKind.PERFORMANCE, "Operation avoids jamming and instability"),
    (r"\brepeatab", RequirementKind.PERFORMANCE, "Motion is repeatable"),
    (r"\bguid(e|ance|ed)\b", RequirementKind.FUNCTIONAL, "Moving element is guided"),
    (r"\bdesktop\b|\bcompact\b", RequirementKind.USABILITY, "Product is desktop-sized"),
    (r"\bservice|maintain", RequirementKind.ASSEMBLY, "Product supports service access"),
]

FREEDOM_HINT = re.compile(
    r"\b(not prescribed|optional|acceptable|allowed|permitted|may (?:be|choose)|"
    r"only|no need|at your discretion|unspecified)\b", re.I
)
CONSTRAINT_HINT = re.compile(
    r"\b(should|must|shall|required|safe|practical|easy|avoid|within|no more than|"
    r"at least|desktop|compact|small)\b", re.I
)
BEHAVIOURAL_VERB = re.compile(
    r"\b(lift|raise|lower|rotate|turn|slide|open|clos\w*|latch\w*|releas\w*|hold\w*|"
    r"retain\w*|index\w*|advance\w*|stay\w*|remain\w*|support\w*|transmit\w*|guide\w*|"
    r"prevent\w*|enclos\w*|drive\w*|actuat\w*|engage\w*)\b", re.I
)

RANGE = re.compile(r"(\d+(?:\.\d+)?)\s*[-–to]+\s*(\d+(?:\.\d+)?)\s*(mm|cm|kg|g|N|deg|°)", re.I)
SINGLE = re.compile(r"(?:approximately\s+|about\s+|~)?(\d+(?:\.\d+)?)\s*(mm|cm|kg|g|N|deg|°)", re.I)

# What a measured quantity most likely constrains, by unit and nearby wording.
UNIT_ROLE = {
    "mm": ("travel", RequirementKind.PERFORMANCE, ">="),
    "cm": ("travel", RequirementKind.PERFORMANCE, ">="),
    "kg": ("payload", RequirementKind.PERFORMANCE, ">="),
    "g": ("payload", RequirementKind.PERFORMANCE, ">="),
    "N": ("force", RequirementKind.PERFORMANCE, "<="),
    "deg": ("angle", RequirementKind.PERFORMANCE, ">="),
    "°": ("angle", RequirementKind.PERFORMANCE, ">="),
}


class RequirementInterpreter(PipelineStage):
    stage_id: ClassVar[Stage] = Stage.REQUIREMENT
    question: ClassVar[str] = "What must the product accomplish?"
    produces: ClassVar[str] = "RequirementSpec"

    def _ledger(self, request: str, clarifications: list[str]) -> list[SourceClause]:
        """Mechanical clause split. Segmentation only - no interpretation.

        Disposition is guessed from surface patterns. This is deliberately shallow:
        where the guess is wrong or a clause goes undischarged, the Stage 01
        validators are expected to say so rather than the placeholder to hide it.
        """
        clauses: list[SourceClause] = []
        for origin, block in (
            (SourceOrigin.REQUEST, request),
            *[(SourceOrigin.CLARIFICATION, c) for c in clarifications],
        ):
            for raw in re.split(r"(?<=[.;])\s+", block.strip()):
                s = raw.strip()
                if not s:
                    continue
                if FREEDOM_HINT.search(s):
                    disp = ClauseDisposition.FREEDOM
                elif BEHAVIOURAL_VERB.search(s):
                    disp = ClauseDisposition.FUNCTION
                elif CONSTRAINT_HINT.search(s):
                    disp = ClauseDisposition.CONSTRAINT
                else:
                    disp = ClauseDisposition.CONTEXT
                clauses.append(
                    SourceClause(id=new_id("C"), text=s, source=origin, disposition=disp)
                )
        return clauses

    def _clause_for(self, clauses: list[SourceClause], fragment: str) -> list[str]:
        frag = fragment.strip().lower()
        return [c.id for c in clauses if frag and frag in c.text.lower()][:1]

    def run(self, *, request: str, product_intent: str = "", clarifications: list[str] | None = None) -> RequirementSpec:
        clarifications = clarifications or []
        text = request + "\n" + "\n".join(clarifications)
        clauses = self._ledger(request, clarifications)
        reqs: list[Requirement] = []

        for m in RANGE.finditer(text):
            lo, hi, unit = float(m.group(1)), float(m.group(2)), m.group(3)
            role, kind, cmp_ = UNIT_ROLE.get(unit, ("quantity", RequirementKind.PERFORMANCE, ">="))
            reqs.append(
                Requirement(
                    id=new_id("REQ"),
                    kind=kind,
                    origin=RequirementOrigin.USER_STATED,
                    statement=f"{role} between {lo:g} and {hi:g} {unit}",
                    bound=RequirementBound(comparator="between", lower=lo, upper=hi, unit=unit),
                    priority=1,
                    derived_from=self._clause_for(clauses, m.group(0)),
                    verification=VerificationIntent(
                        kind=VerificationKind.MEASUREMENT, observable=role,
                        condition="nominal operation",
                    ),
                )
            )

        consumed = {m.group(0) for m in RANGE.finditer(text)}
        for m in SINGLE.finditer(text):
            if any(m.group(0) in c for c in consumed):
                continue
            val, unit = float(m.group(1)), m.group(2)
            role, kind, cmp_ = UNIT_ROLE.get(unit, ("quantity", RequirementKind.PERFORMANCE, ">="))
            reqs.append(
                Requirement(
                    id=new_id("REQ"),
                    kind=kind,
                    origin=RequirementOrigin.USER_STATED,
                    statement=f"{role} {cmp_} {val:g} {unit}",
                    bound=RequirementBound(
                        comparator=cmp_,
                        lower=val if cmp_ != "<=" else None,
                        upper=val if cmp_ == "<=" else None,
                        unit=unit,
                    ),
                    priority=1,
                    derived_from=self._clause_for(clauses, m.group(0)),
                    verification=VerificationIntent(
                        kind=VerificationKind.MEASUREMENT, observable=role,
                        condition="nominal operation",
                    ),
                )
            )

        for pattern, kind, statement in CONCEPTS:
            if re.search(pattern, text, re.I):
                reqs.append(
                    Requirement(
                        id=new_id("REQ"),
                        kind=kind,
                        origin=RequirementOrigin.USER_STATED,
                        statement=statement,
                        priority=2,
                        derived_from=[
                            c.id for c in clauses if re.search(pattern, c.text, re.I)
                        ][:1],
                        verification=VerificationIntent(
                            kind=VerificationKind.NOT_YET_VERIFIABLE,
                            reason="placeholder extractor identified no observable",
                        ),
                    )
                )

        # Deliberately minimal and product-independent. The placeholder does not
        # derive scenarios from the product, does not detect design freedoms, and
        # does not identify relations. Those gaps are real; the validators report
        # them rather than the placeholder concealing them.
        unknown = Unknown(
            id=new_id("U"),
            subject="acceptable input effort",
            reason="no effort or force target appears in the request",
            affects=[r.id for r in reqs if r.kind is RequirementKind.USABILITY],
            resolvable_by="a stated maximum operating force or torque",
        )
        scenario = OperatingScenario(
            id=new_id("SCN"),
            name="nominal operation",
            description="the product operated as described in the request",
            applies_to=[r.id for r in reqs],
            derived_from=[c.id for c in clauses[:1]],
        )
        return RequirementSpec(
            meta=ObjectMeta(object_id=new_id("SPEC"), producer=self.stage_id),
            source_text=request,
            product_intent=product_intent or request.strip().split(".")[0],
            clauses=clauses,
            requirements=reqs,
            operating_scenarios=[scenario],
            assumptions=[
                Assumption(
                    id=new_id("AS"),
                    statement="single user, manual actuation",
                    stands_in_for=unknown.id,
                    origin=RequirementOrigin.INFERRED,
                )
            ],
            unknowns=[unknown],
            freedoms=[],
            relations=[],
        )
