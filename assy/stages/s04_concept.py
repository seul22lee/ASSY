"""Stage 04 - Spatial Concept Analysis.

Question: how does the product organisation arrange in space, and where does it
contradict itself?

**Strict consumer of the Stage 03 product architecture.** Stage 03 says what the
pieces are, which region houses each, who owns each obligation and in what order
things assemble. It says nothing about *arrangement*. Stage 04 is the first stage
to place regions relative to one another, and therefore the first that can notice
two of them wanting the same space.

It produces the spatial hypothesis Stage 05 would otherwise have to solve:

  * a reference frame - what the principal motion runs along, which faces open
  * a zone for every region, expressed relative to that frame
  * every swept volume classified by how its element actually moves
  * the region pairs that must be kept disjoint, and which are already governed
  * access routes and what obstructs them
  * a structured issue list

The output stays ``authoritative = False`` permanently (SYSTEM_ARCHITECTURE §8):
a spatial hypothesis is not mechanical proof, and Stage 05 may reinterpret or
discard any of it. Non-authoritative does not mean unstructured - an issue Stage 05
must act on is useless as a paragraph.

Boundary: no dimensions, no coordinates, no clearances, no geometry, no CAD.
"""

from __future__ import annotations

from typing import ClassVar

from assy.domain.common import ObjectMeta, Stage, new_id
from assy.domain.upstream import (
    AccessPurpose,
    AccessRoute,
    ConceptVisualization,
    InterferenceCandidate,
    MechanicalArchitecture,
    MotionClass,
    ObligationKind,
    PieceKind,
    ProductArchitecture,
    ReferenceFrame,
    RegionKind,
    RegionPlacement,
    SpatialAnnotation,
    SpatialIssue,
    SpatialIssueKind,
    SpatialZone,
    SweptShape,
    SweptVolumeSpec,
    ViewSpec,
)
from assy.stages.base import PipelineStage

# Engineering role tag -> how that element sweeps space. Keyed on the tag rather
# than on an element name, so a new mechanism family classifies automatically.
MOTION_BY_ROLE: dict[str, MotionClass] = {
    "translating": MotionClass.TRANSLATIONAL,
    "rotating": MotionClass.ROTATIONAL,
    "hinged": MotionClass.HINGED_ARC,
    "moving_boundary": MotionClass.HINGED_ARC,
}

SHAPE_BY_MOTION: dict[MotionClass, SweptShape] = {
    MotionClass.TRANSLATIONAL: SweptShape.PRISM,
    MotionClass.ROTATIONAL: SweptShape.DISC,
    MotionClass.HINGED_ARC: SweptShape.ARC_SECTOR,
    MotionClass.COMPOUND: SweptShape.COMPOUND,
    MotionClass.UNCLASSIFIED: SweptShape.UNKNOWN,
}

# Which obligation places its bearer where, relative to the primary axis.
ZONE_BY_OBLIGATION: dict[ObligationKind, SpatialZone] = {
    ObligationKind.GUIDANCE: SpatialZone.FLANKING,
    ObligationKind.ANTI_ROTATION: SpatialZone.FLANKING,
    ObligationKind.RADIAL_SUPPORT: SpatialZone.END,
    ObligationKind.AXIAL_THRUST: SpatialZone.END,
    ObligationKind.TRAVEL_LIMIT: SpatialZone.END,
    ObligationKind.STRUCTURAL_ROOT: SpatialZone.BOUNDARY,
    ObligationKind.USER_ACCESS: SpatialZone.EXTERNAL,
    ObligationKind.ALIGNMENT: SpatialZone.CORE,
    ObligationKind.CLEARANCE: SpatialZone.CORE,
}

ZONE_BY_REGION_KIND: dict[RegionKind, SpatialZone] = {
    RegionKind.ENCLOSED_VOLUME: SpatialZone.CORE,
    RegionKind.SWEPT_VOLUME: SpatialZone.CORE,
    RegionKind.SUPPORT_ZONE: SpatialZone.FLANKING,
    RegionKind.TRAVEL_LIMIT_ZONE: SpatialZone.END,
    RegionKind.RETENTION_ZONE: SpatialZone.BOUNDARY,
    RegionKind.STRUCTURAL: SpatialZone.BOUNDARY,
    RegionKind.USER_ACCESS: SpatialZone.EXTERNAL,
    RegionKind.SERVICE_ACCESS: SpatialZone.BOUNDARY,
    RegionKind.PAYLOAD: SpatialZone.EXTERNAL,
}

ACCESS_PURPOSE: dict[RegionKind, AccessPurpose] = {
    RegionKind.USER_ACCESS: AccessPurpose.USER_OPERATION,
    RegionKind.SERVICE_ACCESS: AccessPurpose.SERVICE,
    RegionKind.PAYLOAD: AccessPurpose.PAYLOAD,
}


class ConceptVisualizer(PipelineStage):
    stage_id: ClassVar[Stage] = Stage.CONCEPT
    question: ClassVar[str] = "How does the product organisation arrange in space?"
    produces: ClassVar[str] = "ConceptVisualization"

    # -- frame ---------------------------------------------------------------
    def _motion_of(self, piece) -> MotionClass:
        classes = {
            MOTION_BY_ROLE[tag] for tag in piece.engineering_roles if tag in MOTION_BY_ROLE
        }
        if not classes:
            return MotionClass.UNCLASSIFIED
        if len(classes) > 1:
            return MotionClass.COMPOUND
        return classes.pop()

    def _frame(self, product: ProductArchitecture) -> ReferenceFrame:
        """The principal motion defines the frame.

        Translation dominates rotation: a product whose output translates is
        organised along that travel, whatever else spins inside it.
        """
        faces = [r.name for r in product.regions if r.external]
        moving = [p for p in product.pieces if p.moving]
        by_class: dict[MotionClass, str] = {}
        for p in moving:
            by_class.setdefault(self._motion_of(p), p.name)

        for cls in (
            MotionClass.TRANSLATIONAL,
            MotionClass.HINGED_ARC,
            MotionClass.ROTATIONAL,
            MotionClass.COMPOUND,
        ):
            if cls in by_class:
                name = by_class[cls]
                return ReferenceFrame(
                    primary_axis=f"{name}_axis",
                    primary_motion=cls,
                    derived_from=(
                        f"{name} is the moving element whose {cls.value} motion "
                        "dominates the product organisation"
                    ),
                    access_faces=faces,
                )
        return ReferenceFrame(
            primary_axis="unresolved",
            derived_from="no moving element declares how it moves",
            access_faces=faces,
        )

    # -- placement -----------------------------------------------------------
    def _placements(self, product, frame) -> list[RegionPlacement]:
        # An obligation is stronger evidence of position than a region's kind:
        # it names the element the region must sit against.
        zone_by_element: dict[str, tuple[SpatialZone, str]] = {}
        for o in product.obligation_ownership:
            if o.owner_piece and o.obligation in ZONE_BY_OBLIGATION:
                zone_by_element.setdefault(
                    o.owner_piece,
                    (
                        ZONE_BY_OBLIGATION[o.obligation],
                        f"reacts the {o.obligation.value} obligation of {o.element}",
                    ),
                )

        placements: list[RegionPlacement] = []
        for r in product.regions:
            zone = ZONE_BY_REGION_KIND[r.kind]
            why, ref = "", None
            if r.kind is RegionKind.SWEPT_VOLUME and r.external:
                zone = SpatialZone.EXTERNAL
                why = "swept by an element that sits outside the enclosure"
            # An obligation refines where an *internal* region sits. It can never
            # pull an externally reachable region inside: a surface the user must
            # reach is external whatever else its element also does.
            if not r.external:
                for element in r.houses:
                    if element in zone_by_element:
                        zone, why = zone_by_element[element]
                        ref = element
                        break
            placements.append(
                RegionPlacement(
                    region=r.name,
                    zone=zone,
                    relative_to=ref or frame.primary_axis,
                    why=why or f"a {r.kind.value} region sits {zone.value} by construction",
                )
            )
        return placements

    # -- swept volumes -------------------------------------------------------
    def _swept(self, product) -> list[SweptVolumeSpec]:
        by_name = {p.name: p for p in product.pieces}
        clearance_region = {
            o.element: o.region
            for o in product.obligation_ownership
            if o.obligation is ObligationKind.CLEARANCE and o.region
        }
        static = [
            r.name for r in product.regions
            if not r.moving and r.kind is not RegionKind.STRUCTURAL
        ]

        volumes: list[SweptVolumeSpec] = []
        for r in product.regions:
            if r.kind is not RegionKind.SWEPT_VOLUME:
                continue
            for element in r.houses:
                piece = by_name.get(element)
                motion = self._motion_of(piece) if piece else MotionClass.UNCLASSIFIED
                volumes.append(
                    SweptVolumeSpec(
                        region=r.name,
                        element=element,
                        motion=motion,
                        shape=SHAPE_BY_MOTION[motion],
                        external=r.external,
                        must_stay_clear_of=(
                            [clearance_region[element]]
                            if element in clearance_region
                            else [n for n in static if n != r.name]
                        ),
                    )
                )
        return volumes

    # -- interference --------------------------------------------------------
    def _interference(self, product, swept) -> list[InterferenceCandidate]:
        """Region pairs that could occupy the same space.

        A pair the architecture already governs is reported as *addressed*, not
        dropped: Stage 05 still has to honour it, and silently removing it would
        hide a constraint rather than discharge it.
        """
        governed = {
            (o.element, o.owner_piece): o.obligation.value
            for o in product.obligation_ownership if o.owner_piece
        }
        # Two elements joined by a declared interface are *designed* to meet.
        # Reporting that as interference would bury the real conflicts in noise.
        for i in product.interfaces:
            governed.setdefault(tuple(i.between), f"{i.kind.value} interface")

        def relation(a: str, b: str) -> str | None:
            return governed.get((a, b)) or governed.get((b, a))

        candidates: list[InterferenceCandidate] = []
        seen: set[tuple[str, str]] = set()

        def add(a: str, b: str, why: str, addressed: str | None = None) -> None:
            key = tuple(sorted((a, b)))
            if a != b and key not in seen:
                seen.add(key)
                candidates.append(
                    InterferenceCandidate(between=key, why=why, addressed_by=addressed)
                )

        for sv in swept:
            for other in product.regions:
                if other.name == sv.region or other.kind is RegionKind.STRUCTURAL:
                    continue
                if other.external != sv.external:
                    continue  # opposite sides of the boundary cannot collide
                if sv.element in other.houses:
                    continue  # an element does not interfere with its own region
                addressed = next(
                    (r for r in (relation(sv.element, e) for e in other.houses) if r),
                    None,
                )
                add(
                    sv.region,
                    other.name,
                    f"the {sv.shape.value} swept by {sv.element} shares containment "
                    f"with {other.name}",
                    addressed,
                )

        for i, a in enumerate(swept):
            for b in swept[i + 1:]:
                if a.external == b.external:
                    add(
                        a.region,
                        b.region,
                        f"{a.element} and {b.element} both sweep on the same side of "
                        "the enclosure boundary",
                        relation(a.element, b.element),
                    )
        return candidates

    # -- access --------------------------------------------------------------
    def _access(self, product, swept) -> list[AccessRoute]:
        routes: list[AccessRoute] = []
        for r in product.regions:
            purpose = ACCESS_PURPOSE.get(r.kind)
            if purpose is None:
                continue
            # An external swept volume is a hand or a lever moving through the
            # space an external access route needs.
            obstructions = [
                sv.region
                for sv in swept
                if sv.external and r.external and sv.element not in r.houses
            ]
            routes.append(
                AccessRoute(region=r.name, purpose=purpose, obstructed_by=obstructions)
            )

        service = next(
            (r for r in product.regions if r.kind is RegionKind.SERVICE_ACCESS), None
        )
        if service is not None:
            routes.append(
                AccessRoute(
                    region=service.name,
                    purpose=AccessPurpose.ASSEMBLY,
                    obstructed_by=[sv.region for sv in swept if sv.external],
                )
            )
        return routes

    # -- issues --------------------------------------------------------------
    def _issues(self, product, swept, interference, access) -> list[SpatialIssue]:
        issues: list[SpatialIssue] = []

        for c in interference:
            if c.addressed_by is None:
                issues.append(
                    SpatialIssue(
                        id=new_id("SI"),
                        kind=SpatialIssueKind.INTERFERENCE,
                        concern=(
                            f"{c.between[0]} and {c.between[1]} may occupy the same "
                            "space and nothing in the architecture separates them"
                        ),
                        regions=list(c.between),
                        evidence=c.why,
                    )
                )

        for route in access:
            if route.obstructed_by:
                issues.append(
                    SpatialIssue(
                        id=new_id("SI"),
                        kind=SpatialIssueKind.ACCESS_BLOCKED,
                        concern=(
                            f"{route.region} must be reachable for "
                            f"{route.purpose.value} but "
                            f"{', '.join(route.obstructed_by)} sweeps across it"
                        ),
                        regions=[route.region] + route.obstructed_by,
                        evidence="both lie outside the enclosure boundary",
                    )
                )

        for sv in swept:
            if sv.motion is MotionClass.UNCLASSIFIED:
                issues.append(
                    SpatialIssue(
                        id=new_id("SI"),
                        kind=SpatialIssueKind.ENVELOPE_CONFLICT,
                        concern=(
                            f"{sv.element} moves but declares no motion kind, so its "
                            "swept envelope cannot be bounded"
                        ),
                        regions=[sv.region],
                        evidence="no engineering role tag classifies the motion",
                    )
                )

        supported = {
            o.element
            for o in product.obligation_ownership
            if o.obligation is ObligationKind.RADIAL_SUPPORT and o.owner_piece
        }
        for sv in swept:
            if sv.motion is MotionClass.ROTATIONAL and sv.element not in supported:
                issues.append(
                    SpatialIssue(
                        id=new_id("SI"),
                        kind=SpatialIssueKind.UNSUPPORTED_SPAN,
                        concern=(
                            f"{sv.element} rotates but no radial support is assigned "
                            "to it"
                        ),
                        regions=[sv.region],
                        evidence="no radial_support obligation names this element",
                    )
                )

        order = {s.pieces[0]: s.order for s in product.assembly_sequence if s.pieces}
        cover = next(
            (p.name for p in product.pieces if p.kind is PieceKind.COVER), None
        )
        if cover is not None and cover in order:
            late = sorted(n for n, o in order.items() if o > order[cover])
            if late:
                issues.append(
                    SpatialIssue(
                        id=new_id("SI"),
                        kind=SpatialIssueKind.ASSEMBLY_UNREACHABLE,
                        concern=(
                            f"{', '.join(late)} are installed after the boundary closes"
                        ),
                        regions=[cover],
                        evidence="the assembly order places them after the cover",
                    )
                )
        return issues

    # -- views and annotations ----------------------------------------------
    def _views(self, product, frame, swept) -> list[ViewSpec]:
        views = [
            ViewSpec(
                name="exterior",
                purpose="show what the user meets and which faces must stay reachable",
                shows=[r.name for r in product.regions if r.external],
            ),
            ViewSpec(
                name="cutaway_along_primary_axis",
                purpose=f"show the arrangement along {frame.primary_axis}",
                shows=[r.name for r in product.regions if not r.external],
            ),
            ViewSpec(
                name="exploded_assembly",
                purpose="show the installation order and the direction each piece enters",
                shows=[s.pieces[0] for s in product.assembly_sequence if s.pieces],
            ),
        ]
        views += [
            ViewSpec(
                name=f"envelope_{sv.element}",
                purpose=f"show the {sv.shape.value} swept by {sv.element} at its extremes",
                shows=[sv.region] + sv.must_stay_clear_of,
            )
            for sv in swept
        ]
        return views

    def _annotations(self, product, frame, swept) -> list[SpatialAnnotation]:
        notes = [
            SpatialAnnotation(
                subject=frame.primary_axis,
                note=f"principal axis; {frame.primary_motion.value} motion",
            )
        ]
        notes += [
            SpatialAnnotation(
                subject=sv.element,
                note=(
                    f"sweeps a {sv.shape.value}, "
                    f"{'outside' if sv.external else 'inside'} the enclosure"
                ),
            )
            for sv in swept
        ]
        notes += [
            SpatialAnnotation(
                subject=o.owner_piece or o.element,
                note=f"reacts {o.obligation.value} for {o.element}",
            )
            for o in product.obligation_ownership
            if o.owner_piece
        ]
        notes += [
            SpatialAnnotation(
                subject=i.between[0],
                note=f"{i.kind.value} to {i.between[1]}, crossing the enclosure boundary",
            )
            for i in product.interfaces
            if i.crosses_boundary
        ]
        return notes

    # -- entry point ---------------------------------------------------------
    def run(
        self, *, product: ProductArchitecture, mechanical: MechanicalArchitecture
    ) -> ConceptVisualization:
        frame = self._frame(product)
        placements = self._placements(product, frame)
        swept = self._swept(product)
        interference = self._interference(product, swept)
        access = self._access(product, swept)
        issues = self._issues(product, swept, interference, access)

        return ConceptVisualization(
            meta=ObjectMeta(object_id=new_id("CONCEPT"), producer=self.stage_id),
            authoritative=False,
            image_refs=[],  # no image backend; the blueprint is the structured content
            reference_frame=frame,
            region_placements=placements,
            swept_volumes=swept,
            interference_candidates=interference,
            access_routes=access,
            issues=issues,
            views=self._views(product, frame, swept),
            annotations=self._annotations(product, frame, swept),
            source_product_id=product.meta.object_id,
            source_candidate_id=product.source_candidate_id,
            # Upstream gaps pass through; Stage 04 never resolves them.
            product_advisories=list(product.architecture_advisories),
            described_layout=(
                f"Organised along {frame.primary_axis} "
                f"({frame.primary_motion.value}). {len(placements)} regions placed, "
                f"{len(swept)} swept volumes, {len(interference)} interference candidates."
            ),
            spatial_hypotheses=[
                f"{p.region} sits {p.zone.value} relative to {p.relative_to}"
                for p in placements
            ],
            review_concerns=[i.concern for i in issues],
        )
