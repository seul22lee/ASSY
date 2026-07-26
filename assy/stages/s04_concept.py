"""Stage 04 - Concept Visualization.

Question: how might the product architecture be spatially interpreted?

PLACEHOLDER IMPLEMENTATION. No image model is wired in; this emits a textual
spatial hypothesis. That is deliberate and harmless, because the output is
non-authoritative by contract: a concept image is not mechanical proof, not a
geometry definition, and not CAD specification (SYSTEM_ARCHITECTURE section 8).

Stage 05 may reinterpret or ignore anything here.
"""

from __future__ import annotations

from typing import ClassVar

from assy.domain.common import ObjectMeta, Stage, new_id
from assy.domain.upstream import ConceptVisualization, MechanicalArchitecture, ProductArchitecture
from assy.stages.base import PipelineStage


class ConceptVisualizer(PipelineStage):
    stage_id: ClassVar[Stage] = Stage.CONCEPT
    question: ClassVar[str] = "How might this product architecture appear spatially?"
    produces: ClassVar[str] = "ConceptVisualization"

    def run(
        self, *, product: ProductArchitecture, mechanical: MechanicalArchitecture
    ) -> ConceptVisualization:
        regions = ", ".join(r.name for r in product.regions)
        return ConceptVisualization(
            meta=ObjectMeta(object_id=new_id("CONCEPT"), producer=self.stage_id),
            authoritative=False,
            image_refs=[],  # no image backend in the vertical slice
            described_layout=(
                f"Upright rectangular product. Regions: {regions}. "
                f"{product.proportions}. Housing: {product.housing_strategy}."
            ),
            spatial_hypotheses=[
                "user input sits on a side face at comfortable desktop height",
                "the drive compartment occupies one vertical side channel",
                "the working volume is centred so the payload does not overhang",
                "the access panel is on the drive side, away from the output element",
            ],
            review_concerns=[
                "image cannot confirm support spacing or bearing placement",
                "image cannot confirm clearance through the full motion domain",
                "proportions are a hypothesis, not an engineering result",
            ],
        )
