"""Stage 03 - Product Architecture Planner.

Question: how do the mechanisms become a coherent, usable, manufacturable product?

PLACEHOLDER IMPLEMENTATION. Regions are derived from the selected architecture's
part roles. Output stays deliberately qualitative - no dimensions, no clearances,
no wall thicknesses (STAGE_03 manufacturing boundary).
"""

from __future__ import annotations

from typing import ClassVar

from assy.domain.common import ObjectMeta, Stage, new_id
from assy.domain.upstream import (
    MechanicalArchitecture,
    MechanismRole,
    ProductArchitecture,
    ProductRegion,
    RequirementSpec,
)
from assy.stages.base import PipelineStage

# Role -> product region intent. Qualitative by construction.
REGION_INTENT: dict[MechanismRole, tuple[str, str, bool]] = {
    MechanismRole.INPUT: ("user_input_region", "accessible external actuation", True),
    MechanismRole.TRANSMISSION: ("drive_compartment", "enclosed power transmission", False),
    MechanismRole.CONVERSION: ("drive_compartment", "enclosed motion conversion", False),
    MechanismRole.OUTPUT: ("working_volume", "the region the output element occupies and travels through", False),
    MechanismRole.GUIDANCE: ("guidance_region", "constrains the moving element", False),
    MechanismRole.RETENTION: ("retention_region", "holds the mechanism in state", False),
    MechanismRole.STRUCTURE: ("structural_shell", "carries load and encloses the mechanism", False),
    MechanismRole.SUPPORT: ("support_region", "locates a moving element and reacts its loads", False),
    MechanismRole.LIMIT: ("travel_limit_region", "bounds the motion of a moving element", False),
    MechanismRole.RELEASE: ("user_release_region", "accessible surface that ends a held state", True),
}


class ProductArchitecturePlanner(PipelineStage):
    stage_id: ClassVar[Stage] = Stage.PRODUCT
    question: ClassVar[str] = "How do the mechanisms become a coherent, usable product?"
    produces: ClassVar[str] = "ProductArchitecture"

    def run(self, *, spec: RequirementSpec, mechanical: MechanicalArchitecture) -> ProductArchitecture:
        selected = mechanical.selected
        regions: dict[str, ProductRegion] = {}

        for part in selected.parts:
            name, purpose, external = REGION_INTENT[part.role]
            region = regions.get(name)
            if region is None:
                region = ProductRegion(
                    id=new_id("RG"), name=name, purpose=purpose, external=external
                )
                regions[name] = region
            region.houses.append(part.name)

        text = " ".join(r.statement.lower() for r in spec.requirements)
        wants_service = "service" in text or "maintain" in text
        wants_enclosure = "enclos" in text

        return ProductArchitecture(
            meta=ObjectMeta(object_id=new_id("PROD"), producer=self.stage_id),
            regions=list(regions.values()),
            housing_strategy=(
                "Two-piece shell with a removable access panel"
                if wants_enclosure
                else "Open frame with a structural base"
            ),
            user_interaction=[
                f"{p.name} is the external user interface"
                for p in selected.parts
                if p.role is MechanismRole.INPUT
            ],
            assembly_strategy=(
                "Insert the mechanism through one open face, then close with a "
                "removable panel that carries part of the bearing support"
            ),
            service_strategy=(
                "Removable panel exposes the drive compartment without disturbing the output element"
                if wants_service
                else "No dedicated service access"
            ),
            protection_strategy="Moving elements are enclosed; only the user input crosses the boundary",
            manufacturing_intent="Additive-friendly organisation: flat split, no captive geometry",
            load_paths=[
                "payload -> output element -> guidance -> structural shell -> base",
                "user input -> transmission -> conversion -> output element",
            ],
            proportions="Wide stable base, output travel along the tall axis, drive to one side",
            risks=list(selected.risks),
        )
