"""Stage 02 - Mechanical Architecture Generator.

Question: what mechanical principles can realise the required functions?

PLACEHOLDER SELECTION. Candidate generation is real (drawn from the mechanism
catalogue and filtered by required conversion); candidate *ranking* is a
transparent weighted score standing in for LLM trade-off reasoning.
"""

from __future__ import annotations

import re
from typing import ClassVar

from assy.domain.common import ObjectMeta, Stage, new_id
from assy.domain.upstream import (
    FunctionalPart,
    MechanicalArchitecture,
    MechanicalArchitectureCandidate,
    MechanismRole,
    MotionRelation,
    RequirementSpec,
)
from assy.knowledge import mechanisms as cat
from assy.stages.base import PipelineStage, Reasoner, StageError

# Which conversion the requirements imply.
#
# Scored rather than first-match. A first-match list silently mis-selects when a
# noun is shared between intents: "indexing platform" contains "platform", which
# would pick a lift architecture for an indexing product and then pass. Words that
# name the *output motion* are weighted above words that merely name a part.
CONVERSIONS: list[tuple[str, str, str, int]] = [
    (r"\bindex|\bintermittent|\bdiscrete step|\bstation|\bdwell", "rotation", "intermittent_rotation", 3),
    (r"\blift|\brais|\blower|\belevat", "rotation", "translation", 3),
    (r"\blatch|\bretain|\bclos(e|ed|ure)|\blid", "displacement", "retention", 3),
    # Ambiguous nouns: supporting evidence only, never decisive on their own.
    (r"\bplatform|\btravel", "rotation", "translation", 1),
    (r"\bturntable|\brotary", "rotation", "intermittent_rotation", 1),
]


class MechanicalArchitectureGenerator(PipelineStage):
    stage_id: ClassVar[Stage] = Stage.MECHANICAL
    question: ClassVar[str] = "What mechanical principles can realise the required functions?"
    produces: ClassVar[str] = "MechanicalArchitecture"

    def __init__(self, reasoner: Reasoner | None = None):
        self.reasoner = reasoner

    def _conversion(self, spec: RequirementSpec) -> tuple[str, str]:
        text = " ".join(
            [spec.source_text, spec.product_intent] + [r.statement for r in spec.requirements]
        )
        scores: dict[tuple[str, str], int] = {}
        for pattern, src, dst, weight in CONVERSIONS:
            hits = len(re.findall(pattern, text, re.I))
            if hits:
                scores[(src, dst)] = scores.get((src, dst), 0) + hits * weight
        if not scores:
            raise StageError(self.stage_id.value, "no known conversion implied by the requirements")
        best, score = max(scores.items(), key=lambda kv: kv[1])
        runner_up = sorted(scores.values(), reverse=True)[1] if len(scores) > 1 else 0
        if score == runner_up:
            raise StageError(
                self.stage_id.value,
                f"requirements imply competing conversions with equal evidence: {scores}; "
                "requirement clarification is needed",
            )
        return best

    def _score(self, fam: cat.MechanismFamily, spec: RequirementSpec) -> float:
        """Transparent weighting. Every term is inspectable and benchmark-neutral."""
        text = " ".join(r.statement for r in spec.requirements).lower()
        score = 0.0
        score += fam.efficiency * 1.0
        score += fam.compactness * 1.0
        score -= fam.part_count * 0.12
        # Holding position without continuous effort is worth a lot for a manual device.
        if fam.self_locking:
            score += 1.4
        if "safe" in text and fam.self_locking:
            score += 0.6
        if "jam" in text:
            score += fam.efficiency * 0.3
        return round(score, 4)

    def run(self, *, spec: RequirementSpec) -> MechanicalArchitecture:
        src, dst = self._conversion(spec)
        families = cat.families_for(src, dst)
        if not families:
            raise StageError(self.stage_id.value, f"no mechanism family converts {src} -> {dst}")

        served = [r.id for r in spec.requirements if r.priority <= 2]
        candidates: list[MechanicalArchitectureCandidate] = []
        for fam in families:
            parts = [
                FunctionalPart(
                    id=new_id("FP"),
                    name=p.name,
                    role=MechanismRole(p.role),
                    rationale=f"{p.name} in the {fam.id} architecture",
                )
                for p in fam.parts
            ]
            candidates.append(
                MechanicalArchitectureCandidate(
                    id=fam.id,
                    principle=fam.principle,
                    parts=parts,
                    motions=[
                        MotionRelation(
                            id=new_id("MO"),
                            driver="crank",
                            driven="platform" if dst == "translation" else "output",
                            relation=f"{src}->{dst}",
                            ratio_symbol=fam.relation,
                        )
                    ],
                    strengths=list(fam.strengths),
                    weaknesses=list(fam.weaknesses),
                    risks=list(fam.risks),
                    open_questions=list(fam.open_questions),
                    serves_requirements=served,
                )
            )

        scores = {c.id: self._score(cat.by_id(c.id), spec) for c in candidates}
        best = max(candidates, key=lambda c: scores[c.id])
        rejected = {
            c.id: f"score {scores[c.id]:.2f} below {best.id} ({scores[best.id]:.2f}); "
            + (c.weaknesses[0] if c.weaknesses else "no distinguishing advantage")
            for c in candidates
            if c.id != best.id
        }

        return MechanicalArchitecture(
            meta=ObjectMeta(object_id=new_id("MECH"), producer=self.stage_id),
            candidates=candidates,
            selected_id=best.id,
            selection_rationale=(
                f"{best.id} selected on weighted trade-off "
                f"(efficiency, compactness, part count, holding behaviour): {scores}"
            ),
            rejected=rejected,
        )
