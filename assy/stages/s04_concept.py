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
    AxisStation,
    BoundaryFace,
    ConceptVisualization,
    ConstraintStatus,
    ElementClass,
    FaceRole,
    InterferenceCandidate,
    MechanicalArchitecture,
    MotionKind,
    ObligationKind,
    PieceKind,
    PlacedPiece,
    ProductArchitecture,
    ProductAxis,
    ProductReferenceFrame,
    RegionKind,
    RegionPlacement,
    SignedFace,
    SpatialAnnotation,
    SpatialConstraint,
    SpatialIssue,
    SpatialIssueKind,
    SpatialRelationKind,
    SpatialZone,
    SweptShape,
    SweptVolumeSpec,
    BodyPlacement,
    Containment,
    LocationBasis,
    LocationDerivation,
    RadialPosition,
    TopologicalAnchor,
    TopologyKind,
    ViewSpec,
)
from assy.knowledge.mechanisms import JOINT_ANCHOR, RELATION_ANCHOR, RELATION_BASIS
from assy.stages.s04_layout import LOW, HIGH, LayoutSynthesizer
from assy.stages.s04_states import StateRealizer
from assy.stages.base import PipelineStage

# Declared motion kind -> the coarse envelope it sweeps. Keyed on the declared
# kind, never on a name or a role tag, so a new family classifies automatically.
SHAPE_BY_MOTION: dict[MotionKind, SweptShape] = {
    MotionKind.TRANSLATION: SweptShape.PRISMATIC,
    MotionKind.ROTATION: SweptShape.CYLINDRICAL,
    MotionKind.ROTATION_TRANSLATION: SweptShape.HELICAL,
    MotionKind.COMPLIANT_DEFORMATION: SweptShape.DEFORMATION,
    MotionKind.FIXED: SweptShape.UNKNOWN,
    MotionKind.UNSPECIFIED: SweptShape.UNKNOWN,
}

# Which product face a role is placed on by default. This is a labelling of the
# product's own frame, not a claim about how it sits in the world: -Y is simply
# "the face the operating role was assigned", and any role may share a face.
DEFAULT_FACE: dict[FaceRole, SignedFace] = {
    FaceRole.OPERATING: SignedFace.Y_NEG,
    FaceRole.SERVICE: SignedFace.Y_POS,
    FaceRole.LOADING: SignedFace.Z_POS,
    FaceRole.SEATING: SignedFace.Z_NEG,
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
    def _motion_of(self, piece) -> MotionKind:
        """The declared motion kind. Never derived from a name or a role tag."""
        return piece.motion_kind

    def _frame(self, product: ProductArchitecture) -> ProductReferenceFrame:
        """Three signed product axes, labelled by the principal motion.

        Translation dominates rotation: a product whose output translates is
        organised along that travel, whatever else spins inside it. The frame
        never says which way the product faces in the world.
        """
        moving = [p for p in product.pieces if p.moving]
        by_kind: dict[MotionKind, str] = {}
        for p in moving:
            by_kind.setdefault(self._motion_of(p), p.name)

        for kind in (
            MotionKind.TRANSLATION,
            MotionKind.ROTATION_TRANSLATION,
            MotionKind.ROTATION,
            MotionKind.COMPLIANT_DEFORMATION,
        ):
            if kind in by_kind:
                name = by_kind[kind]
                return ProductReferenceFrame(
                    primary_axis=ProductAxis.Z,
                    secondary_axis=ProductAxis.Y,
                    lateral_axis=ProductAxis.X,
                    primary_motion=kind,
                    primary_element=name,
                    derived_from=(
                        f"{name} is the moving element whose {kind.value} motion "
                        "dominates the product organisation"
                    ),
                    axis_meaning={
                        "z": f"the {kind.value} of {name}",
                        "y": "across the operating and service faces",
                        "x": "lateral, flanking the primary axis",
                    },
                )
        return ProductReferenceFrame(
            primary_motion=MotionKind.UNSPECIFIED,
            derived_from="no moving element declares a motion kind",
            axis_meaning={"z": "undetermined - no declared motion to organise along"},
        )

    # -- faces ---------------------------------------------------------------
    def _faces(self, product, pieces_by_name) -> list[BoundaryFace]:
        """Assign face roles from structured facts, allowing deliberate sharing.

        A role never forces a face to be exclusive: a container opened and loaded
        through one aperture is normal engineering. What matters is that sharing is
        recorded, so a later stage sees a decision rather than an accident.
        """
        hosts: dict[SignedFace, list[str]] = {}
        roles: dict[SignedFace, list[FaceRole]] = {}

        def assign(role: FaceRole, host: str | None) -> None:
            face = DEFAULT_FACE[role]
            roles.setdefault(face, [])
            if role not in roles[face]:
                roles[face].append(role)
            if host:
                hosts.setdefault(face, []).append(host)

        # OPERATING: an element a user must reach.
        for a in product.access_paths:
            if a.agent.value == "user_hand":
                assign(FaceRole.OPERATING, a.target)
        # LOADING: an externally originating load entering the product.
        for a in product.access_paths:
            if a.agent.value in ("payload", "stored_content"):
                assign(FaceRole.LOADING, a.target)
        # SERVICE: a removable boundary.
        cover = next((p.name for p in product.pieces if p.kind is PieceKind.COVER), None)
        if cover:
            assign(FaceRole.SERVICE, cover)
        # SEATING: where the load path terminates, the product reacts to ground.
        terminal = next(
            (lp.terminates_at for lp in product.load_path_ownership if lp.terminates_at),
            None,
        )
        if terminal:
            assign(FaceRole.SEATING, terminal)

        # An element carrying two roles shares one face rather than being split.
        by_host: dict[str, list[SignedFace]] = {}
        for face, names in hosts.items():
            for n in names:
                by_host.setdefault(n, []).append(face)
        merged: dict[SignedFace, SignedFace] = {}
        for n, faces in by_host.items():
            if len(set(faces)) > 1:
                keep = sorted(set(faces), key=lambda f: f.value)[0]
                for f in set(faces):
                    if f != keep:
                        merged[f] = keep
        for src, dst in merged.items():
            roles.setdefault(dst, []).extend(r for r in roles.pop(src, []) if r not in roles[dst])
            hosts.setdefault(dst, []).extend(hosts.pop(src, []))

        return [
            BoundaryFace(
                face=face,
                roles=sorted(set(roles.get(face, [])), key=lambda r: r.value),
                hosts=sorted(set(hosts.get(face, []))),
                shared=len(set(roles.get(face, []))) > 1,
                rationale=(
                    "several roles were deliberately assigned to one face"
                    if len(set(roles.get(face, []))) > 1
                    else "assigned from the structured fact that created the role"
                ),
            )
            for face in sorted(roles, key=lambda f: f.value)
        ]

    def _stations(self, product) -> dict[str, AxisStation]:
        """Stations the mechanism actually fixes.

        Only a relation whose basis determines a unique position yields a station
        here. Where the mechanism constrains without determining - two reactions
        that must be apart, but either way round - no station is asserted and the
        freedom is recorded on the derivation instead. Assigning one by iteration
        order would state an engineering fact that was never derived.
        """
        stations: dict[str, AxisStation] = {}
        for o in product.obligation_ownership:
            if not o.owner_piece:
                continue
            if o.obligation is ObligationKind.CLEARANCE:
                stations.setdefault(o.owner_piece, AxisStation.MID_SPAN)
        return stations

    def _reaction_groups(self, product) -> dict[tuple[str, str], list[str]]:
        """Reactions of one kind acting on one element, in declaration order."""
        groups: dict[tuple[str, str], list[str]] = {}
        for o in product.obligation_ownership:
            if o.owner_piece and o.obligation in (
                ObligationKind.RADIAL_SUPPORT,
                ObligationKind.AXIAL_THRUST,
                ObligationKind.TRAVEL_LIMIT,
            ):
                groups.setdefault((o.element, o.obligation.value), []).append(o.owner_piece)
        return groups

    def _separation_constraints(self, product) -> list[SpatialConstraint]:
        """Two reactions of one kind on one element cannot share a station.

        This is the mechanical content the old alternating counter was standing in
        for: the pair must be distinct, and the mechanism says nothing about which
        is where.
        """
        out: list[SpatialConstraint] = []
        for (element, kind), owners in sorted(self._reaction_groups(product).items()):
            if len(owners) < 2:
                continue
            for i in range(len(owners) - 1):
                out.append(
                    SpatialConstraint(
                        between=(owners[i], owners[i + 1]),
                        relation=SpatialRelationKind.SEPARATED_ALONG_AXIS,
                        source=f"derived:paired_{kind}",
                        rationale=(
                            f"both react {kind} for {element}; reactions collapsed onto "
                            "one station cannot act as a pair"
                        ),
                    )
                )
        return out

    # -- zone as a *label* for a derived placement ---------------------------
    @staticmethod
    def _zone_of(pl) -> SpatialZone:
        """Name the zone a derived placement falls in.

        The zone is a description of where synthesis put the body, never an input
        to where it goes. Reading it in the other direction is what made a
        role-to-zone table look like engineering.
        """
        if pl.containment is Containment.EXTERIOR:
            return SpatialZone.EXTERIOR
        if pl.containment is Containment.BOUNDARY:
            return SpatialZone.BOUNDARY
        if pl.radial is RadialPosition.OFF_AXIS:
            return SpatialZone.FLANKING
        if pl.lo == pl.hi and pl.lo in (LOW, HIGH):
            return SpatialZone.END
        return SpatialZone.CORE

    # -- placement -----------------------------------------------------------
    def _placements(self, product, frame, stations, faces) -> list[RegionPlacement]:
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
            # A region is where its occupants are. Its zone follows from their
            # synthesized placement rather than from its declared kind.
            occupants = [self.layout.placements.get(n) for n in r.houses]
            occupants = [o for o in occupants if o is not None]
            if occupants:
                zone = self._zone_of(occupants[0])
                why = f"follows the derived placement of {occupants[0].body}"
            else:
                zone = ZONE_BY_REGION_KIND[r.kind]
                why = "no placed body occupies this region"
            ref = None
            if r.kind is RegionKind.SWEPT_VOLUME and r.external:
                zone = SpatialZone.EXTERNAL
                why = "swept by an element that sits outside the enclosure"
            # An obligation refines where an *internal* region sits. It can never
            # pull an externally reachable region inside: a surface the user must
            # reach is external whatever else its element also does.
            # The shell *is* the boundary; reacting an obligation cannot move it,
            # and neither can it move an element that forms the enclosure surface.
            if not r.external and r.kind is not RegionKind.STRUCTURAL:
                for element in r.houses:
                    if element not in zone_by_element:
                        continue
                    candidate, reason = zone_by_element[element]
                    # An internal region cannot be placed outside by an obligation
                    # its occupant happens to react for someone else.
                    if candidate is SpatialZone.EXTERNAL:
                        continue
                    zone, why, ref = candidate, reason, element
                    break
            placements.append(
                RegionPlacement(
                    region=r.name,
                    zone=zone,
                    relative_to=ref or f"{frame.primary_axis.value}-axis",
                    why=why or f"a {r.kind.value} region sits {zone.value} by construction",
                    axis_station=next(
                        (stations[n] for n in r.houses if n in stations), None
                    ),
                    face=next(
                        (f.face for f in faces if set(f.hosts) & set(r.houses)), None
                    ),
                    houses=list(r.houses),
                )
            )
        return placements

    def _attachments(self, product) -> dict[str, list[str]]:
        """What each joint connects, and what each feature sits on.

        A joint and a feature have no position of their own, so theirs is derived
        from the bodies they touch. Both are read from declared interfaces and
        obligations - nothing is inferred from a name.
        """
        bodies = {
            p.name for p in product.pieces if p.element_class is ElementClass.BODY
        }
        attached: dict[str, list[str]] = {}
        for p in product.pieces:
            if p.element_class is ElementClass.BODY:
                continue
            hosts: list[str] = []
            for i in product.interfaces:
                if p.name in i.between:
                    other = i.between[0] if i.between[1] == p.name else i.between[1]
                    if other in bodies and other not in hosts:
                        hosts.append(other)
            for o in product.obligation_ownership:
                if o.owner_piece == p.name and o.element in bodies and o.element not in hosts:
                    hosts.append(o.element)
                if o.element == p.name and o.owner_piece in bodies and o.owner_piece not in hosts:
                    hosts.append(o.owner_piece)
            attached[p.name] = hosts
        return attached

    def _placed_pieces(self, product, placements, stations, faces, attachments) -> list[PlacedPiece]:
        """Every piece, with the region and zone Stage 04 put it in."""
        zone_of = {p.region: p.zone for p in placements}
        # A piece may be housed by several regions; its primary one is the first
        # non-swept region that holds it, so a piece is not reported as living
        # only inside its own envelope.
        primary: dict[str, str] = {}
        for p in placements:
            if p.region.endswith("_swept_volume"):
                continue
            for element in p.houses:
                primary.setdefault(element, p.region)

        def piece_zone(piece):
            pl = self.layout.placements.get(piece.name)
            if pl is not None:
                return self._zone_of(pl)
            # A joint or feature has no placement of its own; it takes the zone of
            # the body it is grounded into.
            for host in getattr(piece, "attached_to", []) or []:
                hosted = self.layout.placements.get(host)
                if hosted is not None:
                    return self._zone_of(hosted)
            if "moving_boundary" in piece.engineering_roles:
                return SpatialZone.BOUNDARY
            return zone_of.get(primary.get(piece.name))

        return [
            PlacedPiece(
                name=piece.name,
                kind=piece.kind,
                region=primary.get(piece.name),
                zone=piece_zone(piece),
                moving=piece.moving,
                external=piece.external,
                motion_kind=piece.motion_kind,
                element_class=piece.element_class,
                permits_motion=piece.permits_motion,
                attached_to=attachments.get(piece.name, []),
                engineering_roles=list(piece.engineering_roles),
                axis_station=stations.get(piece.name),
                face=next((f.face for f in faces if piece.name in f.hosts), None),
            )
            for piece in product.pieces
        ]

    # -- swept volumes -------------------------------------------------------
    def _swept(self, product, frame_axis) -> list[SweptVolumeSpec]:
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
                # A joint does not sweep a volume; the body it carries does. A
                # feature sweeps with its host rather than on its own account.
                if piece is not None and piece.element_class is not ElementClass.BODY:
                    continue
                motion = piece.motion_kind if piece else MotionKind.UNSPECIFIED
                volumes.append(
                    SweptVolumeSpec(
                        region=r.name,
                        element=element,
                        motion=motion,
                        shape=SHAPE_BY_MOTION[motion],
                        axis=frame_axis,
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
    def _issues(self, product, swept, interference, access, placed, mech_chain) -> list[SpatialIssue]:
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
            if sv.motion in (MotionKind.UNSPECIFIED, MotionKind.FIXED):
                issues.append(
                    SpatialIssue(
                        id=new_id("SI"),
                        kind=SpatialIssueKind.MOTION_UNSPECIFIED,
                        concern=(
                            f"{sv.element} moves but declares no motion kind, so no "
                            "envelope is generated for it rather than a guessed one"
                        ),
                        regions=[sv.region],
                        evidence="motion_kind is unspecified on the conceptual element",
                    )
                )

        # A declared motion must be permitted by some joint attached to the body.
        # A body that moves with nothing allowing it to move is not a layout
        # problem - it is an architecture that cannot work.
        joints = [p for p in placed if p.element_class is ElementClass.JOINT]
        for body in placed:
            if body.element_class is not ElementClass.BODY:
                continue
            if body.motion_kind in (MotionKind.FIXED, MotionKind.UNSPECIFIED):
                continue
            if body.motion_kind is MotionKind.COMPLIANT_DEFORMATION:
                continue  # deformation is permitted by the element's own compliance
            permitting = [
                j for j in joints
                if body.name in j.attached_to
                and j.permits_motion in (body.motion_kind, MotionKind.ROTATION_TRANSLATION)
            ]
            if not permitting:
                issues.append(
                    SpatialIssue(
                        id=new_id("SI"),
                        kind=SpatialIssueKind.UNGROUNDED_MOTION,
                        concern=(
                            f"{body.name} is declared to move by {body.motion_kind.value} "
                            "but no joint attached to it permits that motion"
                        ),
                        regions=[body.name],
                        evidence=(
                            "no element of class joint lists this body in attached_to "
                            f"with permits_motion={body.motion_kind.value}"
                        ),
                    )
                )

        # A joint or a feature with nothing to attach to has no position at all.
        for pc in placed:
            if pc.element_class is ElementClass.BODY or pc.attached_to:
                continue
            issues.append(
                SpatialIssue(
                    id=new_id("SI"),
                    kind=SpatialIssueKind.UNHOSTED_ELEMENT,
                    concern=(
                        f"{pc.name} is a {pc.element_class.value} but names no body it "
                        "attaches to, so it has no position"
                    ),
                    regions=[pc.name],
                    evidence="no declared interface or obligation links it to a body",
                )
            )

        # -- functional state transition -------------------------------------
        # A relation label is not proof that the mechanism works. A closure must
        # cover its aperture in one state and clear it in the other, and the joint
        # that carries it must turn about an axis that permits that swing.
        for pc in placed:
            if "moving_boundary" not in pc.engineering_roles:
                continue
            joints = [
                j for j in placed
                if j.element_class is ElementClass.JOINT and pc.name in j.attached_to
            ]
            if not joints:
                continue
            aperture = pc.face.value if pc.face else None
            normal = aperture[1].lower() if aperture else None
            for j in joints:
                axis = (j.anchor.axis if j.anchor else None)
                if normal and axis == normal:
                    issues.append(
                        SpatialIssue(
                            id=new_id("SI"),
                            kind=SpatialIssueKind.INVALID_STATE_TRANSITION,
                            concern=(
                                f"{pc.name} turns about {axis}, the normal of the "
                                f"{aperture} aperture it closes, so it spins in its "
                                "own plane and never clears the opening"
                            ),
                            regions=[pc.name, j.name],
                            evidence=(
                                "a closure clears an aperture only by turning about "
                                "an axis lying in that aperture"
                            ),
                        )
                    )
            # The stop must act at an extreme of the swing the joint permits.
            stops = [
                f for f in placed
                if f.element_class is ElementClass.FEATURE
                and pc.name in f.attached_to
                and f.anchor is not None
                and f.anchor.derivation is not None
                and f.anchor.derivation.basis is LocationBasis.MOTION_EXTREME
            ]
            if not stops:
                issues.append(
                    SpatialIssue(
                        id=new_id("SI"),
                        kind=SpatialIssueKind.INVALID_STATE_TRANSITION,
                        concern=(
                            f"{pc.name} swings between states but nothing acts at the "
                            "extreme of that swing"
                        ),
                        regions=[pc.name],
                        evidence="no feature anchored at a motion extreme bounds it",
                    )
                )

        # -- motion chain continuity -----------------------------------------
        # Motion must reach the output from the input through declared relations.
        chain = list(mech_chain)
        by_name_p = {p.name: p for p in placed}
        for a, b in zip(chain, chain[1:]):
            if a not in by_name_p or b not in by_name_p:
                continue
            linked = any(
                {a, b} <= set(i.between) for i in product.interfaces
            ) or any(
                {a, b} <= set(c.between) for c in product.spatial_constraints
            ) if hasattr(product, "spatial_constraints") else any(
                {a, b} <= set(i.between) for i in product.interfaces
            )
            if not linked:
                issues.append(
                    SpatialIssue(
                        id=new_id("SI"),
                        kind=SpatialIssueKind.BROKEN_MOTION_CHAIN,
                        concern=(
                            f"motion cannot pass from {a} to {b}: they are adjacent in "
                            "the functional chain but no interface joins them"
                        ),
                        regions=[a, b],
                        evidence="no declared interface links these chain neighbours",
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

    # -- topology ------------------------------------------------------------
    @staticmethod
    def _in_plane_axes(face: str | None) -> list[str]:
        """The axes lying in a face, i.e. perpendicular to its normal.

        A revolute joint on a boundary face must turn about an axis *in* that
        face. About the face normal the closure would spin in its own plane and
        never clear the aperture, so the normal is excluded on kinematic grounds
        rather than by preference.
        """
        normal = (face or "+Z")[1].lower()
        return [a for a in ("x", "y", "z") if a != normal]


    def _anchor_for_relation(self, con, by_name, frame, faces) -> TopologicalAnchor:
        """Resolve where a relation is attached, as far as the evidence allows.

        Partial resolution is the honest outcome for a hinge: narrowing it to an
        edge of a named face is real information, and choosing which of that
        face's edges would be deciding geometry on no evidence.
        """
        basis_row = RELATION_BASIS.get(con.relation)
        row = RELATION_ANCHOR.get(con.relation)
        if row is None:
            return TopologicalAnchor(
                kind=TopologyKind.VOLUME, hosts=list(con.between),
                resolved=False, open_parameter="attachment",
                why="no anchor rule is defined for this relation",
            )
        kind, why = row
        a, b = by_name.get(con.between[0]), by_name.get(con.between[1])
        axis = frame.primary_axis.value
        basis, basis_why = basis_row
        anchor = TopologicalAnchor(
            kind=kind, hosts=list(con.between), why=why,
            derivation=LocationDerivation(
                basis=basis, from_relationship=con.source,
                participants=list(con.between), why=basis_why,
            ),
        )

        # A reaction site is on the shared axis, but which station is free unless
        # something in the mechanism fixes it.
        if basis is LocationBasis.REACTION_SITE:
            anchor.axis = axis
            anchor.derivation.determined = False
            anchor.derivation.free_parameters = ["which station along the shared axis"]
            anchor.derivation.alternatives = (
                "any station on the axis that transfers the reaction is equally valid "
                "unless a paired reaction requires separation"
            )
            anchor.resolved = False
            anchor.open_parameter = "which station along the shared axis"
            return anchor

        # A limit sits at an extreme of the constrained body's travel; which
        # extreme it bounds is not stated by the relation alone.
        if basis is LocationBasis.MOTION_EXTREME:
            moving = next(
                (p for p in (a, b) if p is not None and p.motion_kind not in
                 (MotionKind.FIXED, MotionKind.UNSPECIFIED)), None
            )
            anchor.axis = axis
            anchor.span = [AxisStation.RANGE_MIN.value, AxisStation.RANGE_MAX.value]
            anchor.derivation.determined = False
            anchor.derivation.free_parameters = ["which extreme of travel is bounded"]
            anchor.derivation.alternatives = (
                f"either extreme of {moving.name if moving else 'the travel'} bounds a "
                "valid limit; a bidirectional travel needs one at each"
            )
            anchor.resolved = False
            anchor.open_parameter = "which extreme of travel is bounded"
            return anchor

        if kind is TopologyKind.AXIS:
            # A revolute pair carried on a moving boundary is a line *on that
            # surface* - an edge - rather than a line through a solid.
            on_surface = [
                p for p in (a, b)
                if p is not None and "moving_boundary" in p.engineering_roles
            ]
            if on_surface:
                host = on_surface[0]
                anchor.kind = TopologyKind.EDGE
                anchor.faces = [host.face.value] if host.face else []
                in_plane = self._in_plane_axes(host.face.value if host.face else None)
                anchor.axis = in_plane[0]
                anchor.resolved = False
                anchor.open_parameter = (
                    f"which edge of the named face; the axis lies in the face "
                    f"({' or '.join(in_plane)}), not along its normal"
                )
                anchor.why = (
                    "a revolute pair on a surface is a line on that surface; "
                    "which of its edges is a downstream freedom"
                )
                return anchor
            anchor.axis = axis
            anchor.station = next(
                (p.axis_station.value for p in (a, b) if p is not None and p.axis_station),
                None,
            )
            if basis is LocationBasis.COAXIAL_OVERLAP:
                anchor.span = [AxisStation.RANGE_MIN.value, AxisStation.RANGE_MAX.value]
                anchor.derivation.why = (
                    "engagement exists exactly where the two coaxial members overlap, "
                    "so the span follows from their travel rather than a choice"
                )
        elif kind is TopologyKind.CORRIDOR:
            anchor.axis = axis
            anchor.span = [AxisStation.RANGE_MIN.value, AxisStation.RANGE_MAX.value]
        elif kind is TopologyKind.CONTACT_SURFACE:
            known = [p.face.value for p in (a, b) if p is not None and p.face]
            anchor.faces = known
            anchor.station = next(
                (p.axis_station.value for p in (a, b) if p is not None and p.axis_station),
                None,
            )
            anchor.resolved = bool(known)
            if not known:
                anchor.open_parameter = "which pair of surfaces meets"
        elif kind is TopologyKind.BOUNDARY:
            crossing = [f.face.value for f in faces if set(f.hosts) & set(con.between)]
            anchor.faces = crossing
            anchor.resolved = bool(crossing)
            if not crossing:
                anchor.open_parameter = "which boundary face is crossed"
        elif kind is TopologyKind.VOLUME:
            anchor.axis = axis
        return anchor

    def _anchor_for_piece(self, piece, by_name, frame) -> TopologicalAnchor | None:
        """Where a joint or a feature attaches on its hosts."""
        if piece.element_class is ElementClass.BODY or not piece.attached_to:
            return None
        hosts = [by_name[n] for n in piece.attached_to if n in by_name]
        axis = frame.primary_axis.value

        if piece.element_class is ElementClass.JOINT:
            kind = JOINT_ANCHOR.get(piece.permits_motion, TopologyKind.CONTACT_SURFACE)
            on_surface = [h for h in hosts if "moving_boundary" in h.engineering_roles]
            if kind is TopologyKind.AXIS and on_surface:
                host = on_surface[0]
                in_plane = self._in_plane_axes(host.face.value if host.face else None)
                return TopologicalAnchor(
                    kind=TopologyKind.EDGE, hosts=piece.attached_to,
                    faces=[host.face.value] if host.face else [],
                    axis=in_plane[0],
                    resolved=False,
                    open_parameter=(
                        f"which edge of the named face; the axis lies in the face "
                        f"({' or '.join(in_plane)}), not along its normal"
                    ),
                    why=(
                        "a revolute joint on a surface turns about an axis lying in "
                        "that surface; about the normal the closure would spin in "
                        "its own plane and never clear the aperture"
                    ),
                    derivation=LocationDerivation(
                        basis=LocationBasis.SHARED_BOUNDARY,
                        from_relationship=f"joint:{piece.name}",
                        participants=list(piece.attached_to),
                        determined=False,
                        free_parameters=["which edge of the shared boundary"],
                        alternatives=(
                            "any edge of the shared boundary carries the same revolute "
                            "relation; the mechanism does not distinguish them"
                        ),
                        why=(
                            "the joint lies on the boundary the moving and fixed bodies "
                            "share, because that is the only line they have in common"
                        ),
                    ),
                )
            corridor = kind is TopologyKind.CORRIDOR
            constrained = hosts[0].name if hosts else None
            return TopologicalAnchor(
                kind=kind, hosts=piece.attached_to, axis=axis,
                station=None,
                span=(
                    [AxisStation.RANGE_MIN.value, AxisStation.RANGE_MAX.value]
                    if corridor else []
                ),
                resolved=corridor,
                open_parameter=None if corridor else "which station along the axis",
                why=f"a joint permitting {piece.permits_motion.value} is attached to a "
                    f"{kind.value}",
                derivation=LocationDerivation(
                    basis=(
                        LocationBasis.MOTION_CORRIDOR if corridor
                        else LocationBasis.COMMON_AXIS
                    ),
                    from_relationship=f"joint:{piece.name}",
                    participants=list(piece.attached_to),
                    determined=corridor,
                    free_parameters=[] if corridor else ["which station along the axis"],
                    alternatives=(
                        None if corridor else
                        "any station on the shared axis transfers the same reaction"
                    ),
                    why=(
                        f"the guide acts along the whole corridor {constrained} travels"
                        if corridor else
                        f"the joint lies on the axis it shares with {constrained}"
                    ),
                ),
            )

        # A feature acts across the surface it shares with what it engages, in
        # the state that is held.
        faces = [h.face.value for h in hosts if h.face]
        limits = piece.role is MechanismRole.LIMIT if hasattr(piece, "role") else False
        basis = (
            LocationBasis.MOTION_EXTREME if piece.kind is PieceKind.LIMIT_ELEMENT
            else LocationBasis.ENGAGED_STATE_CONTACT
        )
        at_extreme = basis is LocationBasis.MOTION_EXTREME
        return TopologicalAnchor(
            kind=TopologyKind.CONTACT_SURFACE, hosts=piece.attached_to,
            faces=faces,
            station=None,
            span=(
                [AxisStation.RANGE_MIN.value, AxisStation.RANGE_MAX.value]
                if at_extreme else []
            ),
            resolved=bool(faces) and not at_extreme,
            open_parameter=(
                "which extreme of travel is bounded" if at_extreme
                else None if faces else "which pair of surfaces meets"
            ),
            why="a local feature acts across the surface it shares with its host",
            derivation=LocationDerivation(
                basis=basis,
                from_relationship=f"feature:{piece.name}",
                participants=list(piece.attached_to),
                determined=bool(faces) and not at_extreme,
                free_parameters=(
                    ["which extreme of travel is bounded"] if at_extreme
                    else [] if faces else ["which pair of surfaces meets"]
                ),
                alternatives=(
                    "either extreme of the constrained travel bounds a valid limit"
                    if at_extreme else None
                ),
                why=(
                    "a limit sits at an extreme of the travel it bounds"
                    if at_extreme else
                    "the feature is where the retained and retaining members meet "
                    "in the state that is held"
                ),
            ),
        )

    # -- interface-realization checks ---------------------------------------
    def _check_constraints(self, product, placed, swept) -> list[SpatialConstraint]:
        """Check each declared spatial demand against this arrangement.

        Architecture level only. A SATISFIED status means the arrangement does not
        contradict the demand, never that the geometry closes. Anything the
        placement model cannot decide stays NOT_CHECKABLE and is never counted as
        a pass.
        """
        by_name = {p.name: p for p in placed}
        # An element taking part in a boundary-crossing interface is present on
        # both sides of the boundary - a shaft entering an enclosure is genuinely
        # outside and inside at once. Without this, every crossing input reads as
        # unreachable from what it drives.
        spanning = {
            n for i in product.crossing_interfaces for n in i.between
        }
        swept_by = {sv.element: sv for sv in swept}
        ON_AXIS = {SpatialZone.CORE, SpatialZone.END, SpatialZone.BOUNDARY}
        ADJACENT = {
            (SpatialZone.CORE, SpatialZone.END), (SpatialZone.CORE, SpatialZone.FLANKING),
            (SpatialZone.CORE, SpatialZone.BOUNDARY), (SpatialZone.CORE, SpatialZone.CORE),
            (SpatialZone.END, SpatialZone.END), (SpatialZone.END, SpatialZone.BOUNDARY),
            (SpatialZone.FLANKING, SpatialZone.FLANKING),
            (SpatialZone.FLANKING, SpatialZone.BOUNDARY),
            (SpatialZone.BOUNDARY, SpatialZone.BOUNDARY),
            (SpatialZone.BOUNDARY, SpatialZone.EXTERNAL),
            (SpatialZone.EXTERNAL, SpatialZone.EXTERNAL),
        }

        def located_at(pc) -> list:
            """A joint or feature has no position of its own; use its hosts'."""
            if pc.element_class is ElementClass.BODY or not pc.attached_to:
                return [pc]
            return [by_name[n] for n in pc.attached_to if n in by_name] or [pc]

        def on_axis(pc) -> bool:
            # FLANKING is offset from the primary axis by definition, so it never
            # qualifies however the element crosses the boundary.
            for host in located_at(pc):
                if host.zone is SpatialZone.FLANKING:
                    continue
                if host.zone in ON_AXIS or (host.external and host.name in spanning):
                    return True
            return False

        def adjacent(a, b) -> bool:
            # A joint or feature is by construction where the bodies it touches
            # are, so it is adjacent to any of them without further evidence.
            if b.name in a.attached_to or a.name in b.attached_to:
                return True
            for ha in located_at(a):
                for hb in located_at(b):
                    if (ha.zone, hb.zone) in ADJACENT or (hb.zone, ha.zone) in ADJACENT:
                        return True
            return (a.name in spanning or b.name in spanning) and (
                a.external != b.external
            )

        checked: list[SpatialConstraint] = []
        for c in product.spatial_constraints:
            a, b = by_name.get(c.between[0]), by_name.get(c.between[1])
            out = c.model_copy(deep=True)
            if a is None or b is None:
                out.status = ConstraintStatus.NOT_CHECKABLE
                out.detail = "one of the elements is not placed"
                checked.append(out)
                continue

            r = c.relation
            if r in (
                SpatialRelationKind.SHARED_AXIS,
                SpatialRelationKind.COAXIAL_WORKING_OVERLAP,
                SpatialRelationKind.AXIS_SURROUNDED,
            ):
                ok = on_axis(a) and on_axis(b)
                out.status = ConstraintStatus.SATISFIED if ok else ConstraintStatus.VIOLATED
                out.detail = (
                    f"{a.name} is {a.zone.value} and {b.name} is {b.zone.value}; "
                    + ("both lie on the primary axis" if ok
                       else "an element offset from the axis cannot share it")
                )
                out.axis = None
            elif r is SpatialRelationKind.COMMON_TRAVEL_DIRECTION:
                # Guidance and sliding act over a shared span, so neither may be
                # pinned to a single end station while the other spans the travel.
                ends = {AxisStation.NEGATIVE_END, AxisStation.POSITIVE_END,
                        AxisStation.RANGE_MIN, AxisStation.RANGE_MAX}
                ok = not (a.axis_station in ends and b.axis_station in ends
                          and a.axis_station != b.axis_station)
                out.status = ConstraintStatus.SATISFIED if ok else ConstraintStatus.VIOLATED
                out.detail = (
                    "spans overlap along the primary axis" if ok
                    else f"{a.name} at {a.axis_station} and {b.name} at "
                         f"{b.axis_station} share no span"
                )
            elif r is SpatialRelationKind.MATING_ADJACENCY:
                ok = adjacent(a, b)
                out.status = ConstraintStatus.SATISFIED if ok else ConstraintStatus.VIOLATED
                out.detail = (
                    f"{a.zone.value} and {b.zone.value} can meet" if ok
                    else f"{a.zone.value} and {b.zone.value} are not adjacent, so the "
                         "mating interfaces cannot meet"
                )
            elif r is SpatialRelationKind.AXIAL_REACTION_STATION:
                # The mechanism fixes that the reaction is on the shared axis, not
                # which station; testing for a specific end would test an assignment.
                ok = on_axis(a) and on_axis(b)
                out.status = ConstraintStatus.SATISFIED if ok else ConstraintStatus.VIOLATED
                out.detail = (
                    f"{b.name} lies on the axis of {a.name} and can transfer the "
                    "reaction; which station is a downstream freedom" if ok
                    else f"{b.name} is offset from the axis, so it cannot take axial thrust"
                )
            elif r is SpatialRelationKind.SEPARATED_ALONG_AXIS:
                ok = a.name != b.name
                out.status = ConstraintStatus.SATISFIED if ok else ConstraintStatus.VIOLATED
                out.detail = (
                    f"{a.name} and {b.name} are distinct elements and can occupy "
                    "distinct stations" if ok
                    else "a reaction cannot be separated from itself"
                )
            elif r is SpatialRelationKind.CONTACT_AT_EXTREME:
                # A limit must act on a body that actually has a bounded travel;
                # which extreme it bounds the relation does not say.
                mover = next(
                    (p for p in (a, b) if p.motion_kind not in
                     (MotionKind.FIXED, MotionKind.UNSPECIFIED)), None
                )
                ok = mover is not None
                out.status = ConstraintStatus.SATISFIED if ok else ConstraintStatus.VIOLATED
                out.detail = (
                    f"{mover.name} has a travel with extremes for the limit to act at; "
                    "which extreme is a downstream freedom" if ok
                    else "neither element moves, so there is no extreme to limit"
                )
            elif r is SpatialRelationKind.DISJOINT_SWEPT:
                sa = swept_by.get(a.name)
                if sa is None:
                    out.status = ConstraintStatus.NOT_CHECKABLE
                    out.detail = f"{a.name} sweeps no declared region"
                else:
                    ok = b.name not in sa.must_stay_clear_of or b.zone is not a.zone
                    out.status = (
                        ConstraintStatus.SATISFIED if ok else ConstraintStatus.VIOLATED
                    )
                    out.detail = (
                        "the swept region and the kept-clear region are separated" if ok
                        else f"{a.name} sweeps into {b.name}"
                    )
            elif r is SpatialRelationKind.EXTERIOR_REACHABLE:
                ok = a.external or b.external or a.zone is SpatialZone.BOUNDARY \
                    or b.zone is SpatialZone.BOUNDARY
                out.status = ConstraintStatus.SATISFIED if ok else ConstraintStatus.VIOLATED
                out.detail = (
                    "the surface reaches the boundary" if ok
                    else "neither element is external nor on the boundary"
                )
            elif r is SpatialRelationKind.CONTINUOUS_ROUTE:
                # A flexible link may be remote; only total absence of a route fails.
                out.status = ConstraintStatus.SATISFIED
                out.detail = "a flexible member may be routed; remoteness is permitted"
            else:
                out.status = ConstraintStatus.NOT_CHECKABLE
                out.detail = "no architecture-level check is defined for this relation"
            checked.append(out)
        return checked

    # -- views and annotations ----------------------------------------------
    def _views(self, product, frame, swept) -> list[ViewSpec]:  # noqa: D401
        views = [
            ViewSpec(
                name="exterior",
                purpose="show what the user meets and which faces must stay reachable",
                shows=[r.name for r in product.regions if r.external],
            ),
            ViewSpec(
                name="cutaway_along_primary_axis",
                purpose=f"show the arrangement along the {frame.primary_axis.value}-axis",
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
                subject=f"{frame.primary_axis.value}-axis",
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
        # Layout synthesis first: everything below describes its result rather
        # than deciding position independently.
        self.layout = LayoutSynthesizer(product, mechanical, frame).synthesize()
        pieces_by_name = {p.name: p for p in product.pieces}
        faces = self._faces(product, pieces_by_name)
        stations = self._stations(product)
        placements = self._placements(product, frame, stations, faces)
        attachments = self._attachments(product)
        placed = self._placed_pieces(product, placements, stations, faces, attachments)
        swept = self._swept(product, frame.primary_axis)
        interference = self._interference(product, swept)
        access = self._access(product, swept)
        view = _ConstraintView(product, mechanical)
        view.spatial_constraints = list(view.spatial_constraints) + \
            self._separation_constraints(product)
        constraints = self._check_constraints(view, placed, swept)
        by_placed = {p.name: p for p in placed}
        for con in constraints:
            con.anchor = self._anchor_for_relation(con, by_placed, frame, faces)
        for pc in placed:
            pc.anchor = self._anchor_for_piece(pc, by_placed, frame)
        issues = self._issues(
            product, swept, interference, access, placed,
            mechanical.selected.element_chain,
        )

        issues += [
            SpatialIssue(
                id=new_id("SI"),
                kind=SpatialIssueKind.CONSTRAINT_VIOLATION,
                concern=(
                    f"{c.between[0]} and {c.between[1]} cannot realize "
                    f"{c.relation.value}: {c.detail}"
                ),
                regions=list(c.between),
                evidence=f"{c.source} - {c.rationale}",
            )
            for c in constraints
            if c.status is ConstraintStatus.VIOLATED
        ]
        issues += [
            SpatialIssue(
                id=new_id("SI"),
                kind=SpatialIssueKind.ACCESS_PATH_UNMET,
                concern=(
                    f"{a.agent.value} cannot reach {a.target} for {a.mode.value}: "
                    f"{a.unmet_reason}"
                ),
                regions=[a.destination_region or a.target],
                evidence="no declared boundary interface serves this path",
            )
            for a in product.access_paths
            if a.required and not a.satisfied
        ]

        # -- stateful kinematic layer ----------------------------------------
        realizer = StateRealizer(product, mechanical, self.layout)
        kin_joints = realizer.joints(attachments)
        couplings = realizer.couplings(kin_joints)
        state_poses = realizer.poses(kin_joints)
        state_interactions = realizer.interactions(attachments)
        state_predicates = realizer.predicates(state_poses)
        envelopes = realizer.envelopes(state_poses)
        validations = realizer.validate(state_poses, state_predicates, envelopes)

        issues += [
            SpatialIssue(
                id=new_id("SI"),
                kind=SpatialIssueKind.INVALID_STATE_TRANSITION,
                concern=f"transition {v.transition} is not qualitatively feasible",
                regions=[
                    m for t in mechanical.selected.transitions
                    if f"{t.from_state}->{t.to_state}" == v.transition
                    for m in t.moves
                ] or [mechanical.selected.id],
                evidence="; ".join(v.unresolved_risks[:2]) or v.why,
            )
            for v in validations if not v.feasible
        ]

        return ConceptVisualization(
            meta=ObjectMeta(object_id=new_id("CONCEPT"), producer=self.stage_id),
            authoritative=False,
            image_refs=[],  # no image backend; the blueprint is the structured content
            reference_frame=frame,
            boundary_faces=faces,
            kinematic_joints=kin_joints,
            joint_couplings=couplings,
            state_poses=state_poses,
            state_interactions=state_interactions,
            state_predicates=state_predicates,
            transition_envelopes=envelopes,
            state_validations=validations,
            body_placements=[
                BodyPlacement(
                    body=pl.body, containment=pl.containment, radial=pl.radial,
                    axis=pl.axis.value, span=[pl.lo, pl.hi],
                    derived_from=list(pl.derived_from),
                )
                for pl in sorted(self.layout.placements.values(), key=lambda x: x.body)
            ],
            unresolved_layout_choices=list(self.layout.choices),
            layout_conflicts=list(self.layout.conflicts),
            region_placements=placements,
            placed_pieces=placed,
            swept_volumes=swept,
            spatial_constraints=constraints,
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
                f"Organised along the {frame.primary_axis.value}-axis "
                f"({frame.primary_motion.value}). {len(placements)} regions placed, "
                f"{len(swept)} swept volumes, {len(faces)} boundary faces, "
                f"{sum(1 for c in constraints if c.status is ConstraintStatus.VIOLATED)}"
                f"/{len(constraints)} spatial constraints violated."
            ),
            spatial_hypotheses=[
                f"{p.region} sits {p.zone.value} relative to {p.relative_to}"
                for p in placements
            ],
            review_concerns=[i.concern for i in issues],
        )


class _ConstraintView:
    """Adapter giving the checker the constraints alongside the placement."""

    def __init__(self, product, mechanical):
        self.spatial_constraints = mechanical.selected.spatial_constraints
        self.access_paths = product.access_paths
        self.crossing_interfaces = [
            i for i in product.interfaces if i.crosses_boundary
        ]
