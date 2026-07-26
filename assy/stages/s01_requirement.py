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

from assy.domain.common import ObjectMeta, Quantity, Stage, new_id
from assy.domain.upstream import (
    Requirement,
    RequirementKind,
    RequirementOrigin,
    RequirementSpec,
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

    def run(self, *, request: str, product_intent: str = "", clarifications: list[str] | None = None) -> RequirementSpec:
        text = request + "\n" + "\n".join(clarifications or [])
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
                    target=Quantity(value=lo, unit=unit),
                    upper=Quantity(value=hi, unit=unit),
                    comparator="between",
                    priority=1,
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
                    target=Quantity(value=val, unit=unit),
                    comparator=cmp_,
                    priority=1,
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
                        verifiable=kind in (RequirementKind.FUNCTIONAL, RequirementKind.PERFORMANCE),
                        priority=2,
                    )
                )

        return RequirementSpec(
            meta=ObjectMeta(object_id=new_id("SPEC"), producer=self.stage_id),
            source_text=request,
            product_intent=product_intent or request.strip().split(".")[0],
            requirements=reqs,
            operating_scenarios=["nominal operation", "maximum payload", "end of travel"],
            assumptions=[
                "room-temperature indoor use",
                "single user, manual actuation",
            ],
            unknowns=[
                "required service life not stated",
                "acceptable input effort not quantified",
            ],
        )
