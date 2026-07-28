"""Synthetic tests for the spatial contract abstractions.

Every case here is built from hand-authored objects for products that are **not**
BM-001 or BM-002 and use mechanisms not in the catalogue. The point is to prove
the reference frame, access paths, motion kinds and interface-realization
constraints work on arbitrary products, not that they happen to fit two fixtures.

    ./mujoco_core/bin/py -m unittest tests.test_spatial_contract
"""

from __future__ import annotations

import unittest

from assy.domain.common import ObjectMeta, Stage, new_id, reset_ids
from assy.domain.upstream import (
    AccessAgent,
    ElementClass,
    LocationBasis,
    TopologyKind,
    AccessMode,
    AccessPath,
    ArchitecturalInterface,
    AssemblyStep,
    AxisStation,
    ConstraintStatus,
    FaceRole,
    FunctionalPart,
    InterfaceKind,
    LoadPathOwnership,
    MechanicalArchitecture,
    MechanicalArchitectureCandidate,
    MechanismRole,
    MotionKind,
    ObligationKind,
    ObligationOwnership,
    PieceKind,
    ProductArchitecture,
    ProductAxis,
    ProductInterface,
    ProductPiece,
    ProductRegion,
    RegionKind,
    SignedFace,
    SpatialConstraint,
    SpatialIssueKind,
    SpatialRelationKind,
    SpatialZone,
    SweptShape,
)
from assy.stages.s04_concept import ConceptVisualizer


def piece(name, kind, *, motion=MotionKind.FIXED, moving=False, external=False,
          roles=(), element_class=ElementClass.BODY, permits=MotionKind.FIXED):
    return ProductPiece(
        id=new_id("PP"), name=name, kind=kind, realises_elements=[name],
        engineering_roles=list(roles), motion_kind=motion,
        element_class=element_class, permits_motion=permits,
        moving=moving, external=external,
    )


def joint(name, permits):
    return piece(name, PieceKind.SUPPORT_ELEMENT,
                 element_class=ElementClass.JOINT, permits=permits)


def feature(name):
    return piece(name, PieceKind.LIMIT_ELEMENT, element_class=ElementClass.FEATURE)


def region(name, kind, *, houses=(), external=False, moving=False):
    return ProductRegion(
        id=new_id("RG"), name=name, purpose=name, houses=list(houses),
        kind=kind, external=external, moving=moving,
    )


def product(*, pieces, regions, ownership=(), interfaces=(), access=(), assembly=(),
            load_paths=(), candidate="synthetic"):
    return ProductArchitecture(
        meta=ObjectMeta(object_id=new_id("PROD"), producer=Stage.PRODUCT),
        pieces=list(pieces), regions=list(regions),
        obligation_ownership=list(ownership), interfaces=list(interfaces),
        access_paths=list(access), assembly_sequence=list(assembly),
        load_path_ownership=list(load_paths), source_candidate_id=candidate,
    )


def architecture(constraints=(), parts=()):
    cand = MechanicalArchitectureCandidate(
        id="synthetic", principle="a mechanism not in the catalogue",
        parts=list(parts), spatial_constraints=list(constraints),
    )
    return MechanicalArchitecture(
        meta=ObjectMeta(object_id=new_id("MECH"), producer=Stage.MECHANICAL),
        candidates=[cand], selected_id="synthetic",
    )


def concept(prod, mech):
    reset_ids()
    return ConceptVisualizer().run(product=prod, mechanical=mech)


# ---------------------------------------------------------------------------
# 1. reference frame, boundary faces, axis stations
# ---------------------------------------------------------------------------
class SyntheticReferenceFrame(unittest.TestCase):
    """A peristaltic dosing head - a product with no benchmark counterpart."""

    def build(self, rotor_motion=MotionKind.ROTATION):
        pieces = [
            piece("rotor", PieceKind.TRANSMISSION_ELEMENT, motion=rotor_motion, moving=True),
            piece("casing", PieceKind.SHELL),
            piece("knob", PieceKind.USER_ELEMENT, motion=MotionKind.ROTATION,
                  moving=True, external=True),
        ]
        regions = [
            region("pumping_chamber", RegionKind.ENCLOSED_VOLUME, houses=["rotor"]),
            region("shell", RegionKind.STRUCTURAL, houses=["casing"]),
            region("knob_zone", RegionKind.USER_ACCESS, houses=["knob"], external=True),
            region("rotor_swept_volume", RegionKind.SWEPT_VOLUME, houses=["rotor"], moving=True),
        ]
        return product(pieces=pieces, regions=regions,
                       load_paths=[LoadPathOwnership(name="p", path=["fluid", "rotor", "casing"],
                                                     terminates_at="casing")])

    def test_frame_declares_three_signed_axes_without_world_orientation(self):
        c = concept(self.build(), architecture())
        f = c.reference_frame
        self.assertEqual(
            {f.primary_axis, f.secondary_axis, f.lateral_axis},
            {ProductAxis.X, ProductAxis.Y, ProductAxis.Z},
            "the frame must name three distinct product axes",
        )
        text = (f.derived_from + " " + " ".join(f.axis_meaning.values())).lower()
        for world_word in ("up", "down", "vertical", "horizontal", "gravity", "floor"):
            self.assertNotIn(world_word, text, f"the frame assumed '{world_word}'")

    def test_frame_reports_unspecified_rather_than_guessing(self):
        c = concept(self.build(rotor_motion=MotionKind.UNSPECIFIED), architecture())
        # The knob still declares rotation, so the frame uses it rather than inventing one.
        self.assertIsNot(c.reference_frame.primary_motion, MotionKind.UNSPECIFIED)
        self.assertTrue(
            any(i.kind is SpatialIssueKind.MOTION_UNSPECIFIED for i in c.issues),
            "an unspecified motion must be reported, not guessed",
        )

    def test_faces_are_signed_product_faces(self):
        c = concept(self.build(), architecture())
        for f in c.boundary_faces:
            with self.subTest(face=f.face):
                self.assertIsInstance(f.face, SignedFace)
                self.assertIn(f.face.value[0], "+-")
                self.assertIn(f.face.axis, (ProductAxis.X, ProductAxis.Y, ProductAxis.Z))

    def test_face_opposites_are_well_formed(self):
        for f in SignedFace:
            self.assertIs(f.opposite.opposite, f)
            self.assertIs(f.opposite.axis, f.axis)

    def test_roles_may_share_one_face_when_one_element_carries_both(self):
        """Sharing must be possible and explicit, never forced apart."""
        pieces = [
            piece("hatch", PieceKind.MOVING_BODY, motion=MotionKind.ROTATION,
                  moving=True, roles=("moving_boundary",)),
            piece("body", PieceKind.SHELL),
        ]
        regions = [
            region("interior", RegionKind.ENCLOSED_VOLUME, houses=["hatch"]),
            region("shell", RegionKind.STRUCTURAL, houses=["body"]),
            region("hatch_swept_volume", RegionKind.SWEPT_VOLUME, houses=["hatch"], moving=True),
        ]
        prod = product(
            pieces=pieces, regions=regions,
            access=[
                AccessPath(agent=AccessAgent.USER_HAND, mode=AccessMode.ACTUATE,
                           target="hatch", satisfied=True),
                AccessPath(agent=AccessAgent.STORED_CONTENT, mode=AccessMode.LOAD,
                           target="hatch", satisfied=True),
            ],
        )
        c = concept(prod, architecture())
        shared = [f for f in c.boundary_faces if f.shared]
        self.assertTrue(shared, "one element carrying two roles must share a face")
        self.assertEqual(
            {FaceRole.OPERATING, FaceRole.LOADING} & set(shared[0].roles),
            {FaceRole.OPERATING, FaceRole.LOADING},
        )

    def test_paired_reactions_demand_separation_without_assigning_ends(self):
        """The mechanism says the pair must be apart, not which is where.

        Assigning one to each end by declaration order asserts an engineering fact
        the mechanism never states.
        """
        pieces = [
            piece("spindle", PieceKind.TRANSMISSION_ELEMENT, motion=MotionKind.ROTATION,
                  moving=True),
            joint("bearing_a", MotionKind.ROTATION),
            joint("bearing_b", MotionKind.ROTATION),
            piece("frame", PieceKind.SHELL),
        ]
        regions = [
            region("core", RegionKind.ENCLOSED_VOLUME, houses=["spindle"]),
            region("supports", RegionKind.SUPPORT_ZONE, houses=["bearing_a", "bearing_b"]),
            region("shell", RegionKind.STRUCTURAL, houses=["frame"]),
            region("spindle_swept_volume", RegionKind.SWEPT_VOLUME, houses=["spindle"], moving=True),
        ]
        prod = product(
            pieces=pieces, regions=regions,
            interfaces=[
                ProductInterface(between=("spindle", "bearing_a"),
                                 kind=InterfaceKind.ROTATIONAL_JOINT),
                ProductInterface(between=("spindle", "bearing_b"),
                                 kind=InterfaceKind.ROTATIONAL_JOINT),
            ],
            ownership=[
                ObligationOwnership(element="spindle", obligation=ObligationKind.RADIAL_SUPPORT,
                                    owner_piece="bearing_a", region="supports"),
                ObligationOwnership(element="spindle", obligation=ObligationKind.RADIAL_SUPPORT,
                                    owner_piece="bearing_b", region="supports"),
            ],
        )
        c = concept(prod, architecture())
        separations = [
            x for x in c.spatial_constraints
            if x.relation is SpatialRelationKind.SEPARATED_ALONG_AXIS
        ]
        self.assertTrue(separations, "a pair of like reactions demands separation")
        self.assertEqual(set(separations[0].between), {"bearing_a", "bearing_b"})
        # Neither is assigned an end: the mechanism does not distinguish them.
        stations = {p.name: p.axis_station for p in c.placed_pieces}
        self.assertIsNone(stations["bearing_a"])
        self.assertIsNone(stations["bearing_b"])
        for name in ("bearing_a", "bearing_b"):
            anchor = next(p.anchor for p in c.placed_pieces if p.name == name)
            self.assertFalse(anchor.derivation.determined)
            self.assertTrue(anchor.derivation.free_parameters)

    def test_the_shell_never_consumes_an_axis_station(self):
        c = concept(self.build(), architecture())
        shell = next(p for p in c.placed_pieces if p.kind is PieceKind.SHELL)
        self.assertIsNone(shell.axis_station)


# ---------------------------------------------------------------------------
# 2. access paths
# ---------------------------------------------------------------------------
class SyntheticAccessPaths(unittest.TestCase):
    """A sealed instrument with a consumable cartridge inside."""

    def build(self, *, crossing: bool):
        pieces = [
            piece("cartridge", PieceKind.MOVING_BODY, motion=MotionKind.TRANSLATION, moving=True),
            piece("case", PieceKind.SHELL),
        ]
        regions = [
            region("bay", RegionKind.ENCLOSED_VOLUME, houses=["cartridge"]),
            region("shell", RegionKind.STRUCTURAL, houses=["case"]),
            region("cartridge_swept_volume", RegionKind.SWEPT_VOLUME,
                   houses=["cartridge"], moving=True),
        ]
        path = AccessPath(
            agent=AccessAgent.CONSUMABLE, mode=AccessMode.INSERT, target="cartridge",
            boundary_interface="port:case" if crossing else None,
            satisfied=crossing,
            unmet_reason=None if crossing else "no declared interface crosses the boundary",
        )
        return product(pieces=pieces, regions=regions, access=[path])

    def test_an_unmet_required_path_becomes_a_typed_issue(self):
        c = concept(self.build(crossing=False), architecture())
        unmet = [i for i in c.issues if i.kind is SpatialIssueKind.ACCESS_PATH_UNMET]
        self.assertTrue(unmet, "an unreachable target must be reported")
        self.assertIn("cartridge", unmet[0].concern)

    def test_a_met_path_raises_no_issue_and_no_opening_is_invented(self):
        c = concept(self.build(crossing=True), architecture())
        self.assertFalse(
            [i for i in c.issues if i.kind is SpatialIssueKind.ACCESS_PATH_UNMET]
        )

    def test_every_agent_kind_is_representable(self):
        for agent in AccessAgent:
            with self.subTest(agent=agent):
                p = AccessPath(agent=agent, mode=AccessMode.REACH, target="x")
                self.assertIs(p.agent, agent)
                self.assertTrue(p.required)

    def test_a_path_carries_direction_and_clearance_when_known(self):
        p = AccessPath(
            agent=AccessAgent.SERVICE_TOOL, mode=AccessMode.REMOVE, target="filter",
            required_direction="+Y", clearance_need="tool swing must clear the case",
        )
        self.assertEqual(p.required_direction, "+Y")
        self.assertTrue(p.clearance_need)


# ---------------------------------------------------------------------------
# 3. motion kinds
# ---------------------------------------------------------------------------
class SyntheticMotionKinds(unittest.TestCase):
    def envelope_for(self, motion):
        pieces = [
            piece("mover", PieceKind.MOVING_BODY, motion=motion, moving=True),
            piece("frame", PieceKind.SHELL),
        ]
        regions = [
            region("core", RegionKind.ENCLOSED_VOLUME, houses=["mover"]),
            region("shell", RegionKind.STRUCTURAL, houses=["frame"]),
            region("mover_swept_volume", RegionKind.SWEPT_VOLUME, houses=["mover"], moving=True),
        ]
        c = concept(product(pieces=pieces, regions=regions), architecture())
        return next(s for s in c.swept_volumes if s.element == "mover")

    def test_each_motion_kind_maps_to_its_own_envelope(self):
        expected = {
            MotionKind.ROTATION: SweptShape.CYLINDRICAL,
            MotionKind.TRANSLATION: SweptShape.PRISMATIC,
            MotionKind.ROTATION_TRANSLATION: SweptShape.HELICAL,
            MotionKind.COMPLIANT_DEFORMATION: SweptShape.DEFORMATION,
        }
        for motion, shape in expected.items():
            with self.subTest(motion=motion):
                sv = self.envelope_for(motion)
                self.assertIs(sv.motion, motion)
                self.assertIs(sv.shape, shape)

    def test_unspecified_motion_yields_no_guessed_geometry(self):
        sv = self.envelope_for(MotionKind.UNSPECIFIED)
        self.assertIs(sv.shape, SweptShape.UNKNOWN, "an envelope was guessed")

    def test_motion_kind_is_independent_of_engineering_role_tags(self):
        """A moving boundary that rotates keeps both facts, separately."""
        p = piece("lid", PieceKind.MOVING_BODY, motion=MotionKind.ROTATION,
                  moving=True, roles=("moving_boundary", "user_contact"))
        self.assertIs(p.motion_kind, MotionKind.ROTATION)
        self.assertIn("moving_boundary", p.engineering_roles)
        self.assertNotIn("rotation", p.engineering_roles)

    def test_motion_survives_the_stage_02_to_04_handoff(self):
        part = FunctionalPart(
            id="FP-1", name="vane", role=MechanismRole.OUTPUT,
            moving=True, motion_kind=MotionKind.ROTATION_TRANSLATION,
        )
        carried = piece("vane", PieceKind.MOVING_BODY, motion=part.motion_kind, moving=True)
        regions = [
            region("core", RegionKind.ENCLOSED_VOLUME, houses=["vane"]),
            region("vane_swept_volume", RegionKind.SWEPT_VOLUME, houses=["vane"], moving=True),
        ]
        c = concept(product(pieces=[carried], regions=regions), architecture())
        self.assertIs(c.swept_volumes[0].motion, MotionKind.ROTATION_TRANSLATION)


# ---------------------------------------------------------------------------
# 4. interface-realization constraints
# ---------------------------------------------------------------------------
class SyntheticInterfaceRealization(unittest.TestCase):
    """The checker is exercised by forcing *relationships*, not zones.

    Zones are outputs of layout synthesis now, so a test that sets one is testing
    nothing. Each case here builds a mechanism whose relations put the elements
    where the case needs them.
    """

    def build(self, relation, *, offset=False, external=False, crossing=False,
              moving_target=False):
        """a is the reference body; b is placed by its relation to a."""
        pieces = [
            piece("a", PieceKind.MOVING_BODY, motion=MotionKind.TRANSLATION, moving=True),
            piece("b", PieceKind.TRANSMISSION_ELEMENT,
                  motion=MotionKind.TRANSLATION if moving_target else MotionKind.FIXED,
                  moving=moving_target, external=external),
            piece("frame", PieceKind.SHELL, roles=("enclosure",)),
        ]
        regions = [
            region("core", RegionKind.ENCLOSED_VOLUME, houses=["a", "b"]),
            region("shell", RegionKind.STRUCTURAL, houses=["frame"]),
            region("a_swept_volume", RegionKind.SWEPT_VOLUME, houses=["a"], moving=True),
        ]
        interfaces = [
            ProductInterface(between=("a", "b"), kind=InterfaceKind.FIXED_ATTACHMENT,
                             crosses_boundary=crossing)
        ]
        ownership = []
        if offset:
            # A guide is pushed off the axis because it constrains motion about it.
            ownership.append(ObligationOwnership(
                element="a", obligation=ObligationKind.GUIDANCE,
                owner_piece="b", region="core"))
        if external:
            ownership.append(ObligationOwnership(
                element="b", obligation=ObligationKind.USER_ACCESS,
                owner_piece="frame", region="shell"))
        prod = product(pieces=pieces, regions=regions, interfaces=interfaces,
                       ownership=ownership)
        constraints = [SpatialConstraint(
            between=("a", "b"), relation=relation, source="synthetic",
            rationale="synthetic case")]
        if offset:
            constraints.append(SpatialConstraint(
                between=("a", "b"),
                relation=SpatialRelationKind.COMMON_TRAVEL_DIRECTION,
                source="obligation:guidance", rationale="guides a"))
        c = concept(prod, architecture(constraints=constraints))
        return c, c.spatial_constraints[0]

    def test_each_relation_kind_has_its_own_check(self):
        """No generic rule: distinct relations must decide differently."""
        _, shared = self.build(SpatialRelationKind.SHARED_AXIS, offset=True)
        _, mating = self.build(SpatialRelationKind.MATING_ADJACENCY, offset=True)
        _, route = self.build(SpatialRelationKind.CONTINUOUS_ROUTE, offset=True)
        self.assertIs(shared.status, ConstraintStatus.VIOLATED)
        self.assertIs(mating.status, ConstraintStatus.SATISFIED)
        self.assertIs(route.status, ConstraintStatus.SATISFIED)

    def test_shared_axis_rejects_an_element_the_layout_puts_off_axis(self):
        _, off = self.build(SpatialRelationKind.SHARED_AXIS, offset=True)
        _, on = self.build(SpatialRelationKind.SHARED_AXIS)
        self.assertIs(off.status, ConstraintStatus.VIOLATED)
        self.assertIs(on.status, ConstraintStatus.SATISFIED)

    def test_a_boundary_crossing_interface_spans_the_boundary(self):
        """An external element reaching an internal one is realizable if it crosses."""
        _, crossing = self.build(SpatialRelationKind.MATING_ADJACENCY,
                                 external=True, crossing=True)
        self.assertIs(crossing.status, ConstraintStatus.SATISFIED)

    def test_axial_reaction_requires_the_reactor_on_the_axis(self):
        _, on_axis = self.build(SpatialRelationKind.AXIAL_REACTION_STATION)
        _, offset = self.build(SpatialRelationKind.AXIAL_REACTION_STATION, offset=True)
        self.assertIs(on_axis.status, ConstraintStatus.SATISFIED)
        self.assertIs(offset.status, ConstraintStatus.VIOLATED)
        self.assertFalse(on_axis.anchor.derivation.determined)

    def test_travel_limit_requires_a_body_with_a_travel_to_bound(self):
        _, movable = self.build(SpatialRelationKind.CONTACT_AT_EXTREME)
        self.assertIs(movable.status, ConstraintStatus.SATISFIED)
        self.assertFalse(movable.anchor.derivation.determined)

    def test_an_undecidable_constraint_is_not_counted_as_a_pass(self):
        mech = architecture(constraints=[
            SpatialConstraint(between=("ghost", "phantom"),
                              relation=SpatialRelationKind.SHARED_AXIS,
                              source="synthetic", rationale="neither element exists")])
        c = concept(product(pieces=[piece("frame", PieceKind.SHELL, roles=("enclosure",))],
                            regions=[region("shell", RegionKind.STRUCTURAL,
                                            houses=["frame"])]), mech)
        self.assertIs(c.spatial_constraints[0].status, ConstraintStatus.NOT_CHECKABLE)

    def test_a_violation_becomes_a_typed_traceable_issue(self):
        c, _ = self.build(SpatialRelationKind.SHARED_AXIS, offset=True)
        violations = [
            i for i in c.issues if i.kind is SpatialIssueKind.CONSTRAINT_VIOLATION
        ]
        self.assertTrue(violations)
        self.assertIn("synthetic", violations[0].evidence)


class SyntheticStateTransition(unittest.TestCase):
    """A closure must actually clear the aperture it covers."""

    def build(self, *, hinge_axis_in_plane=True, with_stop=True):
        pieces = [
            piece("panel", PieceKind.MOVING_BODY, motion=MotionKind.ROTATION,
                  moving=True, roles=("moving_boundary",)),
            joint("panel_pivot", MotionKind.ROTATION),
            piece("cabinet", PieceKind.SHELL, roles=("enclosure",)),
        ]
        if with_stop:
            pieces.append(feature("swing_stop"))
        regions = [
            region("interior", RegionKind.ENCLOSED_VOLUME, houses=["panel"]),
            region("shell", RegionKind.STRUCTURAL, houses=["cabinet"]),
            region("panel_swept_volume", RegionKind.SWEPT_VOLUME,
                   houses=["panel"], moving=True),
        ]
        interfaces = [
            ProductInterface(between=("panel", "panel_pivot"),
                             kind=InterfaceKind.ROTATIONAL_JOINT),
            ProductInterface(between=("panel_pivot", "cabinet"),
                             kind=InterfaceKind.FIXED_ATTACHMENT),
            ProductInterface(between=("panel", "cabinet"),
                             kind=InterfaceKind.USER_CONTACT, crosses_boundary=True),
        ]
        if with_stop:
            interfaces.append(ProductInterface(
                between=("panel", "swing_stop"), kind=InterfaceKind.CONTACT_PAIR))
        access = [AccessPath(agent=AccessAgent.USER_HAND, mode=AccessMode.ACTUATE,
                             target="panel", satisfied=True)]
        prod = product(pieces=pieces, regions=regions, interfaces=interfaces,
                       access=access)
        c = concept(prod, architecture())
        if not hinge_axis_in_plane:
            # Force the degenerate case: turning about the aperture normal.
            pivot = next(p for p in c.placed_pieces if p.name == "panel_pivot")
            panel = next(p for p in c.placed_pieces if p.name == "panel")
            pivot.anchor.axis = panel.face.value[1].lower() if panel.face else "z"
        return c

    def test_the_hinge_axis_lies_in_the_aperture_it_opens(self):
        c = self.build()
        pivot = next(p for p in c.placed_pieces if p.name == "panel_pivot")
        panel = next(p for p in c.placed_pieces if p.name == "panel")
        self.assertIsNotNone(panel.face)
        self.assertNotEqual(
            pivot.anchor.axis, panel.face.value[1].lower(),
            "turning about the aperture normal would spin the panel in its own plane",
        )

    def test_a_valid_closure_raises_no_transition_issue(self):
        c = self.build()
        self.assertFalse(
            [i for i in c.issues
             if i.kind is SpatialIssueKind.INVALID_STATE_TRANSITION]
        )

    def test_a_closure_with_no_stop_cannot_bound_its_swing(self):
        c = self.build(with_stop=False)
        bad = [i for i in c.issues
               if i.kind is SpatialIssueKind.INVALID_STATE_TRANSITION]
        self.assertTrue(bad, "an unbounded swing was accepted")
        self.assertIn("extreme", bad[0].concern)


# ---------------------------------------------------------------------------
# 6. topological anchors - where a relation or local element is attached
# ---------------------------------------------------------------------------
class SyntheticTopologicalAnchors(unittest.TestCase):
    """A rotary airlock valve: not a benchmark, not a catalogued family."""

    def build(self, *, permits=MotionKind.ROTATION, on_surface=False):
        roles = ("moving_boundary",) if on_surface else ()
        pieces = [
            piece("vane", PieceKind.MOVING_BODY, motion=MotionKind.ROTATION,
                  moving=True, roles=roles),
            joint("vane_bearing", permits),
            piece("body", PieceKind.SHELL),
        ]
        regions = [
            region("core", RegionKind.ENCLOSED_VOLUME, houses=["vane", "vane_bearing"]),
            region("shell", RegionKind.STRUCTURAL, houses=["body"]),
            region("vane_swept_volume", RegionKind.SWEPT_VOLUME, houses=["vane"], moving=True),
        ]
        interfaces = [ProductInterface(
            between=("vane", "vane_bearing"), kind=InterfaceKind.ROTATIONAL_JOINT)]
        return product(pieces=pieces, regions=regions, interfaces=interfaces)

    def test_a_revolute_joint_on_a_solid_anchors_to_an_axis(self):
        c = concept(self.build(), architecture())
        bearing = next(p for p in c.placed_pieces if p.name == "vane_bearing")
        self.assertIsNotNone(bearing.anchor)
        self.assertIs(bearing.anchor.kind, TopologyKind.AXIS)
        self.assertIsNotNone(bearing.anchor.axis)

    def test_a_revolute_joint_on_a_surface_anchors_to_an_edge(self):
        """A line on a surface is an edge, not a line through a solid."""
        c = concept(self.build(on_surface=True), architecture())
        bearing = next(p for p in c.placed_pieces if p.name == "vane_bearing")
        self.assertIs(bearing.anchor.kind, TopologyKind.EDGE)

    def test_a_prismatic_joint_anchors_to_a_corridor_spanning_the_travel(self):
        c = concept(self.build(permits=MotionKind.TRANSLATION), architecture())
        bearing = next(p for p in c.placed_pieces if p.name == "vane_bearing")
        self.assertIs(bearing.anchor.kind, TopologyKind.CORRIDOR)
        self.assertEqual(bearing.anchor.span, ["range_min", "range_max"])

    def test_a_partial_anchor_is_marked_unresolved_with_the_open_parameter(self):
        c = concept(self.build(on_surface=True), architecture())
        bearing = next(p for p in c.placed_pieces if p.name == "vane_bearing")
        self.assertFalse(bearing.anchor.resolved)
        self.assertTrue(
            bearing.anchor.open_parameter,
            "an unresolved anchor must name what is still free",
        )

    def test_a_feature_anchors_to_a_contact_surface(self):
        pieces = [
            piece("plate", PieceKind.MOVING_BODY, motion=MotionKind.TRANSLATION, moving=True),
            feature("bump"),
            piece("frame", PieceKind.SHELL),
        ]
        regions = [
            region("core", RegionKind.ENCLOSED_VOLUME, houses=["plate", "bump"]),
            region("shell", RegionKind.STRUCTURAL, houses=["frame"]),
            region("plate_swept_volume", RegionKind.SWEPT_VOLUME, houses=["plate"], moving=True),
        ]
        prod = product(pieces=pieces, regions=regions, interfaces=[
            ProductInterface(between=("plate", "bump"), kind=InterfaceKind.CONTACT_PAIR)])
        c = concept(prod, architecture())
        bump = next(p for p in c.placed_pieces if p.name == "bump")
        self.assertIs(bump.anchor.kind, TopologyKind.CONTACT_SURFACE)
        self.assertIn("plate", bump.anchor.hosts)

    def test_every_relation_kind_resolves_to_an_anchor(self):
        """No relation may leave a consumer to rediscover where it lives."""
        from assy.knowledge.mechanisms import RELATION_ANCHOR

        for relation in SpatialRelationKind:
            with self.subTest(relation=relation):
                self.assertIn(relation, RELATION_ANCHOR)

    def test_a_constraint_carries_its_anchor(self):
        mech = architecture(constraints=[
            SpatialConstraint(between=("vane", "vane_bearing"),
                              relation=SpatialRelationKind.SHARED_AXIS,
                              source="synthetic", rationale="synthetic")])
        c = concept(self.build(), mech)
        con = c.spatial_constraints[0]
        self.assertIsNotNone(con.anchor, "a relation with no anchor must be rediscovered")
        self.assertTrue(con.anchor.why)

    def test_an_anchor_never_invents_a_resolution_it_lacks(self):
        c = concept(self.build(on_surface=True), architecture())
        bearing = next(p for p in c.placed_pieces if p.name == "vane_bearing")
        # It narrows to a face; it does not pick one of that face's four edges.
        self.assertTrue(bearing.anchor.faces or not bearing.anchor.resolved)
        self.assertIsNone(bearing.anchor.station)


class EveryFeatureCanJustifyItsLocation(unittest.TestCase):
    """The three questions a derived placement must answer.

    Why is it here?  -> derivation.basis and derivation.why
    Which relationship determined it?  -> derivation.from_relationship, participants
    Could another placement be valid?  -> determined / free_parameters / alternatives
    """

    def all_anchors(self, c):
        return [p.anchor for p in c.placed_pieces if p.anchor] + [
            x.anchor for x in c.spatial_constraints if x.anchor
        ]

    def build(self):
        pieces = [
            piece("carrier", PieceKind.MOVING_BODY, motion=MotionKind.TRANSLATION,
                  moving=True),
            joint("way", MotionKind.TRANSLATION),
            feature("hard_stop"),
            piece("frame", PieceKind.SHELL),
        ]
        regions = [
            region("core", RegionKind.ENCLOSED_VOLUME,
                   houses=["carrier", "way", "hard_stop"]),
            region("shell", RegionKind.STRUCTURAL, houses=["frame"]),
            region("carrier_swept_volume", RegionKind.SWEPT_VOLUME,
                   houses=["carrier"], moving=True),
        ]
        interfaces = [
            ProductInterface(between=("carrier", "way"), kind=InterfaceKind.SLIDING_JOINT),
            ProductInterface(between=("carrier", "hard_stop"),
                             kind=InterfaceKind.CONTACT_PAIR),
        ]
        return product(pieces=pieces, regions=regions, interfaces=interfaces)

    def test_every_anchor_answers_why_it_is_here(self):
        c = concept(self.build(), architecture())
        for a in self.all_anchors(c):
            with self.subTest(kind=a.kind.value):
                self.assertIsNotNone(a.derivation, "an anchor with no derivation was assigned")
                self.assertTrue(a.derivation.why, "the basis is unexplained")

    def test_every_anchor_names_the_relationship_that_determined_it(self):
        c = concept(self.build(), architecture())
        for a in self.all_anchors(c):
            with self.subTest(kind=a.kind.value):
                self.assertTrue(a.derivation.from_relationship)
                self.assertTrue(a.derivation.participants)

    def test_an_undetermined_location_declares_its_alternatives(self):
        c = concept(self.build(), architecture())
        undetermined = [a for a in self.all_anchors(c) if not a.derivation.determined]
        self.assertTrue(undetermined, "the mechanism fixes nothing freely - implausible")
        for a in undetermined:
            with self.subTest(kind=a.kind.value):
                self.assertTrue(
                    a.derivation.free_parameters,
                    "an undetermined location must say what is free",
                )

    def test_a_determined_location_declares_no_freedom(self):
        c = concept(self.build(), architecture())
        for a in self.all_anchors(c):
            if a.derivation.determined:
                with self.subTest(kind=a.kind.value):
                    self.assertEqual(
                        a.derivation.free_parameters, [],
                        "a determined location must not also be free",
                    )

    def test_a_guide_is_determined_because_the_corridor_is(self):
        """The one case the mechanism fully fixes: a guide spans the whole travel."""
        c = concept(self.build(), architecture())
        way = next(p.anchor for p in c.placed_pieces if p.name == "way")
        self.assertIs(way.derivation.basis, LocationBasis.MOTION_CORRIDOR)
        self.assertTrue(way.derivation.determined)
        self.assertEqual(way.span, ["range_min", "range_max"])

    def test_a_stop_is_undetermined_because_either_extreme_is_valid(self):
        c = concept(self.build(), architecture())
        stop = next(p.anchor for p in c.placed_pieces if p.name == "hard_stop")
        self.assertIs(stop.derivation.basis, LocationBasis.MOTION_EXTREME)
        self.assertFalse(stop.derivation.determined)
        self.assertTrue(stop.derivation.alternatives)

    def test_no_location_depends_on_declaration_order(self):
        """Reversing the order of equivalent elements must not move anything."""
        forward = concept(self.build(), architecture())
        prod = self.build()
        prod.pieces = list(reversed(prod.pieces))
        prod.obligation_ownership = list(reversed(prod.obligation_ownership))
        reversed_run = concept(prod, architecture())

        def stamp(c):
            return sorted(
                (p.name, p.anchor.kind.value, p.anchor.station,
                 tuple(p.anchor.span), p.anchor.derivation.determined)
                for p in c.placed_pieces if p.anchor
            )

        self.assertEqual(stamp(forward), stamp(reversed_run))


if __name__ == "__main__":
    unittest.main()
