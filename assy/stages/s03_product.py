"""Stage 03 - Product Architecture Planner.

Question: how do the mechanisms become a coherent, usable product?

**Strict consumer of the selected Stage 02 candidate.** This stage organises one
architecture into a product. It never reads `source_text`, never parses requirement
prose, never re-ranks candidates, and never rediscovers a function Stage 02 already
declared. Everything it emits is derived from the selected candidate's typed
content: functions, element roles, interfaces, support obligations, load path and
constraints.

What Stage 03 adds is genuinely product-level and absent upstream:

  * manufactured pieces, distinct from conceptual elements
  * an owner for every support obligation
  * piece-to-piece interfaces and qualitative placement
  * moving, swept, and user-access regions
  * an assembly order and a service strategy
  * load-path ownership by region

Boundary: qualitative only. No dimensions, no coordinates, no wall thicknesses, no
tolerances, no features (STAGE_03 manufacturing boundary). Where an architecture
leaves a choice open, Stage 03 records it as unresolved rather than deciding it.
"""

from __future__ import annotations

from typing import ClassVar

from assy.domain.common import ObjectMeta, Stage, new_id
from assy.domain.upstream import (
    AssemblyStep,
    InterfaceKind,
    LoadPathOwnership,
    MechanicalArchitecture,
    MechanismRole,
    ObligationKind,
    ObligationOwnership,
    PieceKind,
    PlacementKind,
    PlacementRelation,
    ProductArchitecture,
    ProductInterface,
    ProductPiece,
    ProductRegion,
    RegionKind,
    RequirementSpec,
)
from assy.stages.base import PipelineStage

# Conceptual role -> the kind of manufactured piece that realises it.
PIECE_KIND: dict[MechanismRole, PieceKind] = {
    MechanismRole.INPUT: PieceKind.USER_ELEMENT,
    MechanismRole.RELEASE: PieceKind.USER_ELEMENT,
    MechanismRole.TRANSMISSION: PieceKind.TRANSMISSION_ELEMENT,
    MechanismRole.CONVERSION: PieceKind.TRANSMISSION_ELEMENT,
    MechanismRole.OUTPUT: PieceKind.MOVING_BODY,
    MechanismRole.GUIDANCE: PieceKind.SUPPORT_ELEMENT,
    MechanismRole.SUPPORT: PieceKind.SUPPORT_ELEMENT,
    MechanismRole.RETENTION: PieceKind.RETENTION_ELEMENT,
    MechanismRole.LIMIT: PieceKind.LIMIT_ELEMENT,
    MechanismRole.STRUCTURE: PieceKind.SHELL,
}

# Conceptual role -> the product region that houses it.
REGION_INTENT: dict[MechanismRole, tuple[str, str, RegionKind, bool]] = {
    MechanismRole.INPUT: ("user_input_region", "accessible external actuation", RegionKind.USER_ACCESS, True),
    MechanismRole.RELEASE: ("user_release_region", "accessible surface that ends a held state", RegionKind.USER_ACCESS, True),
    MechanismRole.TRANSMISSION: ("transmission_region", "enclosed power transmission", RegionKind.ENCLOSED_VOLUME, False),
    MechanismRole.CONVERSION: ("transmission_region", "enclosed motion conversion", RegionKind.ENCLOSED_VOLUME, False),
    MechanismRole.OUTPUT: ("working_volume", "the region the output element occupies and travels through", RegionKind.ENCLOSED_VOLUME, False),
    MechanismRole.GUIDANCE: ("guidance_region", "constrains the moving element", RegionKind.SUPPORT_ZONE, False),
    MechanismRole.SUPPORT: ("support_region", "locates a moving element and reacts its loads", RegionKind.SUPPORT_ZONE, False),
    MechanismRole.RETENTION: ("retention_region", "holds the mechanism in state", RegionKind.RETENTION_ZONE, False),
    MechanismRole.LIMIT: ("travel_limit_region", "bounds the motion of a moving element", RegionKind.TRAVEL_LIMIT_ZONE, False),
    MechanismRole.STRUCTURE: ("structural_shell", "carries load and encloses the mechanism", RegionKind.STRUCTURAL, False),
}

# An obligation implies a spatial relation between the bearer and its reactor.
OBLIGATION_PLACEMENT: dict[ObligationKind, tuple[PlacementKind, str]] = {
    ObligationKind.RADIAL_SUPPORT: (PlacementKind.ADJACENT, "the support must meet the element it locates"),
    ObligationKind.AXIAL_THRUST: (PlacementKind.ADJACENT, "thrust is reacted at the end of the element"),
    ObligationKind.ANTI_ROTATION: (PlacementKind.PARALLEL, "the reacting element must run alongside the travel"),
    ObligationKind.GUIDANCE: (PlacementKind.PARALLEL, "guidance runs parallel to the guided motion"),
    ObligationKind.STRUCTURAL_ROOT: (PlacementKind.ADJACENT, "the root is built into the reacting structure"),
    ObligationKind.ALIGNMENT: (PlacementKind.ADJACENT, "aligned features must meet"),
    ObligationKind.TRAVEL_LIMIT: (PlacementKind.BOUNDS, "the limit bounds the travel of the element"),
    ObligationKind.USER_ACCESS: (PlacementKind.OUTSIDE, "the surface must be reachable from outside"),
    ObligationKind.CLEARANCE: (PlacementKind.INSIDE, "the swept region must stay clear inside the product"),
}

# Assembly rank: what must exist before what. Lower is installed earlier.
ASSEMBLY_RANK: dict[PieceKind, int] = {
    PieceKind.SHELL: 0,
    PieceKind.SUPPORT_ELEMENT: 1,
    PieceKind.TRANSMISSION_ELEMENT: 2,
    PieceKind.MOVING_BODY: 3,
    PieceKind.RETENTION_ELEMENT: 4,
    PieceKind.LIMIT_ELEMENT: 5,
    PieceKind.USER_ELEMENT: 6,
    PieceKind.COVER: 7,
}

ASSEMBLY_ACTION: dict[PieceKind, str] = {
    PieceKind.SHELL: "establish the structural shell",
    PieceKind.SUPPORT_ELEMENT: "install the support element",
    PieceKind.TRANSMISSION_ELEMENT: "install and engage the transmission element",
    PieceKind.MOVING_BODY: "install the moving body onto its supports",
    PieceKind.RETENTION_ELEMENT: "install the retaining element",
    PieceKind.LIMIT_ELEMENT: "install the travel limit",
    PieceKind.USER_ELEMENT: "attach the externally accessible element",
    PieceKind.COVER: "close the service cover",
}


class ProductArchitecturePlanner(PipelineStage):
    stage_id: ClassVar[Stage] = Stage.PRODUCT
    question: ClassVar[str] = "How do the mechanisms become a coherent, usable product?"
    produces: ClassVar[str] = "ProductArchitecture"

    # -- pieces --------------------------------------------------------------
    def _pieces(self, selected) -> list[ProductPiece]:
        """One piece per conceptual element; integration is left to Stage 05."""
        pieces = [
            ProductPiece(
                id=new_id("PP"),
                name=part.name,
                kind=PIECE_KIND[part.role],
                realises_elements=[part.name],
                engineering_roles=list(part.engineering_roles),
                moving=part.moving,
                external=REGION_INTENT[part.role][3],
                rationale=f"realises the {part.role.value} element of the architecture",
            )
            for part in selected.parts
        ]
        # An enclosed mechanism that a user must never open in normal use still has
        # to be assembled and serviced. The cover is implied by enclosure, not by
        # any word in the request.
        if self._needs_service_cover(selected):
            pieces.append(
                ProductPiece(
                    id=new_id("PP"),
                    name="service_cover",
                    kind=PieceKind.COVER,
                    moving=False,
                    external=True,
                    rationale=(
                        "the mechanism is enclosed, so assembly and service require a "
                        "removable boundary rather than a permanently sealed shell"
                    ),
                )
            )
        return pieces

    def _is_enclosed(self, selected) -> bool:
        """Enclosure is declared structurally: a shell element plus a crossing."""
        has_shell = any(p.role is MechanismRole.STRUCTURE for p in selected.parts)
        crosses = any(i.crosses_boundary for i in selected.interfaces)
        return has_shell and crosses

    def _opening_element(self, selected) -> str | None:
        """The element that already opens the product, if the architecture has one.

        An output element that both moves and takes part in a boundary-crossing
        interface *is* the product's opening. Adding a separate service cover
        beside it would invent a piece the architecture does not need.
        """
        crossing = {n for i in selected.interfaces if i.crosses_boundary for n in i.between}
        return next(
            (
                p.name for p in selected.parts
                if p.moving and p.role is MechanismRole.OUTPUT and p.name in crossing
            ),
            None,
        )

    def _needs_service_cover(self, selected) -> bool:
        return self._is_enclosed(selected) and self._opening_element(selected) is None

    # -- regions -------------------------------------------------------------
    def _regions(self, selected) -> dict[str, ProductRegion]:
        regions: dict[str, ProductRegion] = {}

        def region(name, purpose, kind, external, moving=False) -> ProductRegion:
            r = regions.get(name)
            if r is None:
                r = ProductRegion(
                    id=new_id("RG"), name=name, purpose=purpose,
                    kind=kind, external=external, moving=moving,
                )
                regions[name] = r
            return r

        for part in selected.parts:
            name, purpose, kind, external = REGION_INTENT[part.role]
            region(name, purpose, kind, external).houses.append(part.name)

        # Every moving element sweeps a region that must stay clear. Derived from
        # the structured `moving` flag, never from a description of motion.
        for part in selected.parts:
            if part.moving:
                region(
                    f"{part.name}_swept_volume",
                    f"the region swept by {part.name} through its full range",
                    RegionKind.SWEPT_VOLUME,
                    external=REGION_INTENT[part.role][3],
                    moving=True,
                ).houses.append(part.name)

        # A load path that starts at something the architecture does not own is an
        # externally applied load, and it needs somewhere to sit.
        if selected.load_path:
            origin = selected.load_path[0]
            if origin not in {p.name for p in selected.parts}:
                region(
                    f"{origin}_region",
                    f"where the externally applied load ({origin}) acts on the product",
                    RegionKind.PAYLOAD,
                    external=True,
                ).houses.append(origin)

        # A user-access obligation means a surface must be reachable, whatever
        # conceptual role its element happens to carry.
        already_accessible = {
            n for r in regions.values() if r.kind is RegionKind.USER_ACCESS for n in r.houses
        }
        for o in selected.support_obligations:
            if o.kind is ObligationKind.USER_ACCESS and o.element not in already_accessible:
                region(
                    f"{o.element}_access_region",
                    f"externally reachable surface of {o.element}",
                    RegionKind.USER_ACCESS,
                    external=True,
                ).houses.append(o.element)

        if self._needs_service_cover(selected):
            region(
                "service_access_region",
                "removable boundary through which the enclosed mechanism is assembled and serviced",
                RegionKind.SERVICE_ACCESS,
                external=True,
            ).houses.append("service_cover")
        return regions

    # -- obligation ownership ------------------------------------------------
    def _ownership(self, selected, regions) -> list[ObligationOwnership]:
        by_element = {p.name: p for p in selected.parts}
        region_of = {
            name: r.name for r in regions.values() for name in r.houses
        }
        owned: list[ObligationOwnership] = []
        for o in selected.support_obligations:
            reactor = o.reacted_by
            if reactor is not None and reactor in by_element:
                owned.append(
                    ObligationOwnership(
                        element=o.element,
                        obligation=o.kind,
                        owner_piece=reactor,
                        region=region_of.get(reactor),
                    )
                )
            else:
                owned.append(
                    ObligationOwnership(
                        element=o.element,
                        obligation=o.kind,
                        unowned_reason=(
                            "the architecture names no element to react this obligation; "
                            "an owner must be chosen before geometry is synthesised"
                        ),
                    )
                )
        return owned

    # -- placement -----------------------------------------------------------
    def _placements(self, selected) -> list[PlacementRelation]:
        placements: list[PlacementRelation] = []
        names = {p.name for p in selected.parts}
        shell = next(
            (p.name for p in selected.parts if p.role is MechanismRole.STRUCTURE), None
        )

        for o in selected.support_obligations:
            relation, why = OBLIGATION_PLACEMENT[o.kind]
            reference = o.reacted_by if o.reacted_by in names else shell
            if reference is None:
                continue
            placements.append(
                PlacementRelation(
                    subject=o.element, relation=relation, reference=reference, why=why
                )
            )

        # An interface that crosses the enclosure boundary places its elements
        # on opposite sides of it.
        for i in selected.interfaces:
            if i.crosses_boundary and shell is not None:
                outer = i.between[0] if i.between[1] == shell else i.between[1]
                placements.append(
                    PlacementRelation(
                        subject=outer, relation=PlacementKind.CROSSES, reference=shell,
                        why="this interface passes through the enclosure boundary",
                    )
                )

        # The element chain runs from input to output, so the chain spans the product.
        if len(selected.element_chain) >= 2 and shell is not None:
            first, last = selected.element_chain[0], selected.element_chain[-1]
            if first in names and last in names:
                placements.append(
                    PlacementRelation(
                        subject=first, relation=PlacementKind.OPPOSITE, reference=last,
                        why="the chain runs from input to output across the product",
                    )
                )
        return placements

    # -- interfaces ----------------------------------------------------------
    def _interfaces(self, selected) -> list[ProductInterface]:
        return [
            ProductInterface(
                between=i.between,
                kind=i.kind,
                transmits=i.transmits,
                crosses_boundary=i.crosses_boundary,
                from_elements=i.between,
            )
            for i in selected.interfaces
        ]

    # -- assembly ------------------------------------------------------------
    def _assembly(self, pieces: list[ProductPiece]) -> list[AssemblyStep]:
        ordered = sorted(pieces, key=lambda p: (ASSEMBLY_RANK[p.kind], p.name))
        steps: list[AssemblyStep] = []
        for i, piece in enumerate(ordered, start=1):
            steps.append(
                AssemblyStep(
                    order=i,
                    action=f"{ASSEMBLY_ACTION[piece.kind]}: {piece.name}",
                    pieces=[piece.name],
                    enables=(
                        "closes the product"
                        if piece.kind is PieceKind.COVER
                        else "supports the pieces installed after it"
                    ),
                )
            )
        return steps

    # -- load paths ----------------------------------------------------------
    def _load_paths(self, selected, regions) -> list[LoadPathOwnership]:
        region_of = {name: r.name for r in regions.values() for name in r.houses}
        paths: list[LoadPathOwnership] = []
        if selected.load_path:
            paths.append(
                LoadPathOwnership(
                    name="primary",
                    path=list(selected.load_path),
                    owning_regions=[
                        region_of[n] for n in selected.load_path if n in region_of
                    ],
                    terminates_at=selected.load_path[-1],
                )
            )
        if len(selected.element_chain) >= 2:
            paths.append(
                LoadPathOwnership(
                    name="actuation",
                    path=list(selected.element_chain),
                    owning_regions=[
                        region_of[n] for n in selected.element_chain if n in region_of
                    ],
                    terminates_at=selected.element_chain[-1],
                )
            )
        return paths

    # -- entry point ---------------------------------------------------------
    def run(
        self, *, spec: RequirementSpec, mechanical: MechanicalArchitecture
    ) -> ProductArchitecture:
        selected = mechanical.selected
        regions = self._regions(selected)
        pieces = self._pieces(selected)
        ownership = self._ownership(selected, regions)
        enclosed = self._is_enclosed(selected)

        unowned = [o for o in ownership if o.owner_piece is None]
        advisories = [
            f"{o.element}: {o.obligation.value} has no reacting element in the architecture"
            for o in unowned
        ]
        advisories += [
            f"function '{f.function}' is declared with no element performing it"
            for f in selected.functions
            if not f.performed_by
        ]

        return ProductArchitecture(
            meta=ObjectMeta(object_id=new_id("PROD"), producer=self.stage_id),
            regions=list(regions.values()),
            pieces=pieces,
            obligation_ownership=ownership,
            interfaces=self._interfaces(selected),
            placements=self._placements(selected),
            assembly_sequence=self._assembly(pieces),
            load_path_ownership=self._load_paths(selected, regions),
            # Choices the architecture deliberately left open stay open here.
            unresolved_decisions=(
                list(selected.downstream_decisions)
                + [
                    "which conceptual elements are integrated into a single "
                    "manufactured piece, and which stay separate",
                    "housing split direction and service-panel orientation",
                    "material and manufacturing process",
                ]
            ),
            source_architecture_id=mechanical.meta.object_id,
            source_candidate_id=selected.id,
            serves_requirements=list(selected.serves_requirements),
            architecture_advisories=advisories,
            housing_strategy=(
                "Enclosing shell with a removable service boundary; only interfaces "
                "declared as boundary-crossing reach the outside"
                if enclosed
                else "Open structural frame; no element requires enclosure"
            ),
            user_interaction=[
                f"{p.name} is externally accessible ({p.role.value})"
                for p in selected.parts
                if REGION_INTENT[p.role][3]
            ],
            assembly_strategy=(
                f"{len(pieces)} pieces installed supports-first, "
                "closing with the externally accessible elements"
            ),
            service_strategy=(
                "A removable boundary exposes the enclosed elements without "
                "disturbing the output element"
                if enclosed
                else "Elements are directly reachable; no dedicated service access"
            ),
            protection_strategy=(
                "Moving elements stay within the enclosure; only declared "
                "boundary-crossing interfaces reach the user"
                if enclosed
                else "No enclosure is imposed by this architecture"
            ),
            # Process is a design freedom. Stage 03 records it rather than choosing.
            manufacturing_intent="",
            load_paths=[" -> ".join(p.path) for p in self._load_paths(selected, regions)],
            proportions="; ".join(selected.spatial_implications),
            risks=list(selected.risks),
        )
