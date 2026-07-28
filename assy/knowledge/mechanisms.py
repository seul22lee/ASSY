"""Mechanism family catalogue, keyed on transformation signature.

Families are indexed by what they transform — ``(input_kind, output_kind,
continuity)`` — taken from a Stage 01 `BehaviourSpec`. **No family is selected by
matching words.** A benchmark name, a product noun, or a term the user happened to
use can never reach this lookup.

Each entry carries the conceptual content Stage 03 and later need: the functions
that must be performed, the elements that perform them, what must be supported and
by what, where load goes, which elements meet and how, and what the arrangement
implies spatially.

Obligations and interfaces are **typed**, not prose. A downstream stage must be
able to act on "the travelling member needs anti-rotation, reacted by the guide"
without parsing an English sentence to find out. Prose survives only in the `why`
field, as explanation.

It carries no dimensions, no placements, and no tolerances — those are later
stages' work.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from assy.geometry import FormClass as FC
from assy.domain.upstream import (
    ArchitecturalFunction as Fn,
    ArchitecturalInterface as If,
    Continuity,
    InterfaceKind as IK,
    InterfaceKind as IK,
    ElementClass as EC,
    AxisRelation,
    MotionKind as MK,
    ObligationKind as OK,
    QuantityKind as Q,
    SpatialRelationKind as SRK,
    StateRole as SR,
    StateTransition as ST,
    FunctionalState as FS,
    LocationBasis as LB,
    TopologyKind as TK,
    SupportObligation as Ob,
)


@dataclass(frozen=True)
class RoleTemplate:
    name: str
    role: str          # MechanismRole value
    moving: bool
    roles: tuple[str, ...]
    """Engineering role tags - what the element is *for*."""
    motion: MK = MK.FIXED
    """How the element moves. Declared here, never inferred from a name or a tag."""
    element_class: EC = EC.BODY
    """Body, joint or feature. A joint has no bulk and no independent position;
    a feature is a local detail on a host body."""
    permits: MK = MK.FIXED
    """For a joint: the relative motion it allows between the bodies it connects.
    This is what grounds a body's declared motion."""
    form: FC = FC.BLOCK
    """Which solid realizes this element. Form and function are inseparable: a
    screw is a shaft on an axis, a closure is a plate with a normal, a housing is
    a shell with a cavity."""


class HoldingCapability(str, Enum):
    """What a mechanism's own geometry resists when input is removed.

    Holding was a prose string tested with `bool()`, which made every family that
    documented having *no* holding - "none inherent; tension is lost when input is
    released" - count as a holding mechanism, because the sentence saying so is
    itself non-empty. The distinction is also directional, and a boolean cannot
    carry a direction: a ratchet resists one way and a locking geometry both, and
    which of those a requirement needs is a real engineering question.
    """

    NONE = "none"
    """No inherent holding; position is lost when input is removed."""
    SINGLE_DIRECTION = "single_direction"
    """Resists disturbance one way only, e.g. a pawl or a catch."""
    BIDIRECTIONAL = "bidirectional"
    """Resists disturbance either way, e.g. friction or a locking geometry."""


@dataclass(frozen=True)
class Param:
    """A parameter a mechanism family needs in order to work at all.

    Distinct from the form parameters Stage 04 estimates. Those say how big a body
    is; these say what makes the mechanism function - a hook depth, a thread lead,
    a station count. A bounding box can be sized without any of them, which is why
    a design could reach CAD looking complete while none of the quantities that
    decide whether it works had ever been named.

    The family is the only thing that knows them: they follow from the physical
    principle chosen at Stage 02, not from the shape that principle happens to take.
    They were previously written as `downstream_decisions` prose - real knowledge,
    stated in a form nothing could act on.
    """

    name: str
    of_role: str
    """The element that carries it, by role name."""
    quantity: str
    """length, angle, count, force, ratio - what kind of number this is."""
    why: str
    """What fails if it is wrong. This is what makes it a parameter and not a note."""


@dataclass(frozen=True)
class MechanismFamily:
    id: str
    principle: str
    input_kind: Q
    output_kind: Q
    continuity: Continuity
    reversible: bool
    roles: tuple[RoleTemplate, ...]
    element_chain: tuple[str, ...]
    """Ordered element path from input to output."""
    functions: tuple[Fn, ...] = ()
    """What the architecture must do, each bound to the elements that do it."""
    state_relations: tuple[str, ...] = ()
    holding_principle: str | None = None
    holds: HoldingCapability = HoldingCapability.NONE
    """What the holding principle actually resists. Typed, because the prose is
    not machine-readable and `bool(holding_principle)` reads "none inherent" as
    a holding mechanism."""
    support_obligations: tuple[Ob, ...] = ()
    load_path: tuple[str, ...] = ()
    interfaces: tuple[If, ...] = ()
    spatial_implications: tuple[str, ...] = ()
    motion_envelopes: tuple[str, ...] = ()
    strengths: tuple[str, ...] = ()
    weaknesses: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    tradeoffs: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    downstream_decisions: tuple[str, ...] = ()
    parameters: tuple[Param, ...] = ()
    """The quantities this principle is defined by. Stage 05 instantiates them."""
    states: tuple[FS, ...] = ()
    transitions: tuple[ST, ...] = ()

    @property
    def part_count(self) -> int:
        """Derived, never asserted: a hand-set count drifts from the role list."""
        return len(self.roles)

    @property
    def body_count(self) -> int:
        """Independent rigid bodies. The granularity-invariant measure of size.

        Ranking on `part_count` measured how finely a family had been described,
        not how complicated the mechanism is. Saying that two turning bodies drive
        each other through a pin - which is where the contact physically occurs -
        added a role and made the family score worse, so every improvement in
        describing an interaction was penalised as if it were added complexity.

        Bodies are the invariant: a feature is a region of a body and a joint is a
        consequence of two bodies meeting, so neither can be added or removed by
        describing the same mechanism more carefully.
        """
        return sum(1 for r in self.roles if r.element_class is EC.BODY)

    @property
    def unassigned_functions(self) -> tuple[str, ...]:
        """Functions this architecture requires but does not itself perform.

        A declared function with no element behind it is a real incompleteness, and
        being structural it is checkable rather than a matter of wording.
        """
        return tuple(f.function for f in self.functions if not f.performed_by)

    @property
    def signature(self) -> tuple[Q, Q, Continuity]:
        return (self.input_kind, self.output_kind, self.continuity)


_HOUSING = RoleTemplate("housing", "structure", False, ("enclosure", "load_bearing", "manufactured"), form=FC.SHELL, motion=MK.FIXED, element_class=EC.BODY)
_INPUT = RoleTemplate("input_member", "input", True, ("rotating", "user_contact", "manufactured"), form=FC.SHAFT, motion=MK.ROTATION, element_class=EC.BODY)
_INPUT_SUPPORT = RoleTemplate("input_support", "support", False, ("load_bearing", "manufactured"), form=FC.COLLAR, motion=MK.FIXED, element_class=EC.JOINT, permits=MK.ROTATION)
_TRAVEL_STOP = RoleTemplate("travel_stop", "limit", False, ("load_bearing", "manufactured"), form=FC.BLOCK, motion=MK.FIXED, element_class=EC.FEATURE)
_OPENING_INTERFACE = RoleTemplate(
    "opening_interface", "support", False,
    ("hinged", "load_bearing", "manufactured"),
    form=FC.RAIL, motion=MK.FIXED, element_class=EC.JOINT, permits=MK.ROTATION,
)
# Four completions every rotation-to-translation drive requires. Each states a
# general mechanical necessity that the families previously left implicit, and
# each was reported by the spatial model before it was declared here:
#
#   * the two motions must meet somewhere - a conversion element
#   * a non-collinear input needs an element that redirects the axis
#   * guidance reacting a moment needs a couple, so two separated guides
#   * a bidirectional bounded travel needs a limit at each reachable extreme
_CONVERSION_NUT = RoleTemplate(
    "travelling_nut", "conversion", True,
    ("translating", "threaded_pair", "load_bearing", "manufactured"),
    form=FC.COLLAR, motion=MK.TRANSLATION, element_class=EC.BODY,
)
_AXIS_REDIRECT = RoleTemplate(
    "redirect_member", "transmission", True,
    ("rotating", "gear_pair", "load_bearing", "manufactured"),
    form=FC.SHAFT, motion=MK.ROTATION, element_class=EC.BODY,
)
_GUIDE_OPPOSED = RoleTemplate(
    "guide_member_opposed", "guidance", False, ("load_bearing", "manufactured"),
    form=FC.RAIL, motion=MK.FIXED, element_class=EC.JOINT, permits=MK.TRANSLATION,
)
_TRAVEL_STOP_FAR = RoleTemplate(
    "travel_stop_far", "limit", False, ("load_bearing", "manufactured"),
    form=FC.BLOCK, motion=MK.FIXED, element_class=EC.FEATURE,
)


def _drive_completion(conversion_driver: str) -> tuple:
    """Interfaces the four completion elements require."""
    return (
        If(between=(conversion_driver, "travelling_nut"), kind=IK.THREADED_PAIR,
           transmits="the conversion of rotation into translation"),
        If(between=("travelling_nut", "travelling_member"), kind=IK.FIXED_ATTACHMENT,
           transmits="the converted travel and the payload reaction"),
        If(between=("travelling_member", "guide_member_opposed"), kind=IK.SLIDING_JOINT,
           transmits="the opposing half of the guidance couple"),
        If(between=("guide_member_opposed", "housing"), kind=IK.FIXED_ATTACHMENT,
           transmits="reaction into the structure"),
        If(between=("travelling_member", "travel_stop_far"), kind=IK.CONTACT_PAIR,
           transmits="end-of-travel reaction at the far extreme"),
        If(between=("travel_stop_far", "housing"), kind=IK.FIXED_ATTACHMENT,
           transmits="reaction into the structure"),
    )


def _axis_redirect(conversion_driver: str) -> tuple:
    """Interfaces that carry torque across a change of axis.

    Separate from travel completion because it is a different question. A drive
    needs a redirect only when its input axis and its conversion axis differ; a
    routed flexible member changes direction without one. Bundling the two put
    interfaces naming a redirect element into families that never declare one.
    """
    return (
        If(between=("transmission_shaft", "redirect_member"), kind=IK.TOOTHED_MESH,
           transmits="torque across a change of axis",
           axis_relation=AxisRelation.INTERSECTING),
        If(between=("redirect_member", conversion_driver), kind=IK.FIXED_ATTACHMENT,
           transmits="torque on the redirected axis"),
    )


def _drive_completion_obligations(constrained: str) -> tuple:
    return (
        Ob(element=constrained, kind=OK.ANTI_ROTATION, reacted_by="guide_member_opposed",
           why="a moment cannot be reacted at one station; guidance needs a couple"),
        Ob(element=constrained, kind=OK.TRAVEL_LIMIT, reacted_by="travel_stop_far",
           why="a bidirectional travel needs a limit at each reachable extreme"),
    )


_OUTPUT_SUPPORT = RoleTemplate(
    "output_support", "support", False, ("load_bearing", "manufactured"),
    form=FC.COLLAR, motion=MK.FIXED, element_class=EC.JOINT, permits=MK.ROTATION,
)


def _output_bearing(output: str) -> tuple:
    """A rotating output needs a joint that permits its rotation.

    The families declared the output turned and gave it a radial-support
    obligation, but no joint - so the motion was ungrounded and the body had no
    pose at all. The obligation says a reaction is required; the joint is what
    lets the thing move.
    """
    return (
        If(between=(output, "output_support"), kind=IK.ROTATIONAL_JOINT,
           transmits="the output's rotation about its own axis"),
        If(between=("output_support", "housing"), kind=IK.FIXED_ATTACHMENT,
           transmits="reaction into the structure"),
    )


_OPENING_STOP = RoleTemplate("opening_stop", "limit", False, ("load_bearing", "manufactured"), form=FC.BLOCK, motion=MK.FIXED, element_class=EC.FEATURE)

def _catch_states(retainer: str, release: str) -> tuple[tuple[FS, ...], tuple[ST, ...]]:
    """The four states any retained closure passes through.

    Stated once because the sequence is a property of retention, not of a
    product: something is held, the hold is broken, it moves, and its travel ends.
    """
    states = (
        FS(name="closed", role=SR.HOLDING, holds=[retainer],
           covers=["closure_member"],
           why="the retaining pair is engaged and the closure occludes the opening"),
        FS(name="released", role=SR.RELEASING, covers=["closure_member"],
           why="retention has been broken but the closure has not yet moved"),
        FS(name="open", role=SR.MOVING, clears=["closure_member"],
           why="the closure has swung clear of the opening it covered"),
        FS(name="stopped", role=SR.LIMITED, clears=["closure_member"],
           at_limit_of=["opening_stop"],
           why="the swing has reached the limit that bounds it"),
    )
    transitions = (
        ST(from_state="closed", to_state="released", driven_by="release retention",
           moves=[release], why="a deliberate input breaks the retaining engagement"),
        ST(from_state="released", to_state="open",
           driven_by="move the closure between open and closed",
           moves=["closure_member"],
           why="with retention broken the closure is free to swing clear"),
        ST(from_state="open", to_state="stopped", driven_by="limit opening travel",
           moves=["closure_member"],
           why="the swing continues until the stop bounds it"),
    )
    return states, transitions


def _drive_states(output: str, stop: str) -> tuple[tuple[FS, ...], tuple[ST, ...]]:
    """The states any bounded linear drive passes through."""
    states = (
        FS(name="retracted", role=SR.LIMITED, at_limit_of=[stop],
           why="the output rests against one limit of its travel"),
        FS(name="travelling", role=SR.MOVING,
           why="input is being converted into output motion"),
        FS(name="extended", role=SR.LIMITED, at_limit_of=[stop],
           why="the output has reached the opposite limit of its travel"),
    )
    transitions = (
        ST(from_state="retracted", to_state="travelling",
           driven_by="convert rotation to translation", moves=[output],
           why="input motion is transmitted to the output"),
        ST(from_state="travelling", to_state="extended", driven_by="limit travel",
           moves=[output], why="travel continues until the limit bounds it"),
    )
    return states, transitions


def _engagement_element(driver: str) -> RoleTemplate:
    """The element through which one turning body drives another.

    Two bodies turning on their own axes cannot transmit anything through those
    axes: at the axis the surface speed is zero and the moment arm is zero. The
    transfer happens at a radius, through a distinct element the driver carries -
    a pin, a tooth, a lobe, a cam rise. Declaring the driver alone leaves the
    family with a contact that has nowhere to occur.
    """
    return RoleTemplate(
        f"{driver}_engagement", "conversion", True,
        ("intermittent_pair", "load_bearing", "manufactured"),
        form=FC.BLOCK, element_class=EC.FEATURE)


def _index_states(output: str) -> tuple[tuple[FS, ...], tuple[ST, ...]]:
    """The states any intermittent indexer passes through."""
    states = (
        FS(name="dwell", role=SR.HOLDING, holds=[output],
           why="the output is locked between advances"),
        FS(name="advancing", role=SR.MOVING,
           why="the driver is carrying the output through one station"),
        FS(name="indexed", role=SR.HOLDING, holds=[output],
           why="the output has reached the next station and is locked again"),
    )
    transitions = (
        ST(from_state="dwell", to_state="advancing",
           driven_by="advance the output by one discrete station", moves=[output],
           why="engagement begins and the output is driven"),
        ST(from_state="advancing", to_state="indexed",
           driven_by="hold the output stationary between advances", moves=[output],
           why="engagement ends and the locking geometry resumes"),
    )
    return states, transitions


# Functions every enclosed powered architecture must perform. Stated once so a new
# family inherits them rather than relying on an author to remember each one.
def _drive_functions(conv: str, out: str) -> tuple[Fn, ...]:
    return (
        Fn(function="receive manual input", performed_by=["input_member"]),
        Fn(function="support the rotating input", performed_by=["input_support"]),
        Fn(function="transmit input across the enclosure boundary",
           performed_by=["input_member", "housing"]),
        Fn(function="convert rotation to translation", performed_by=[conv]),
        Fn(function="move the output", performed_by=[out]),
        Fn(function="guide the output", performed_by=["guide_member"]),
        Fn(function="support the payload", performed_by=[out, "guide_member"]),
        Fn(function="control reverse motion", performed_by=[conv]),
        Fn(function="limit travel", performed_by=["travel_stop"]),
        Fn(function="transfer loads into the structure", performed_by=["housing"]),
    )


def _catch_functions(retainer: str, release: str) -> tuple[Fn, ...]:
    return (
        Fn(function="provide an enclosure opening", performed_by=["housing", "closure_member"]),
        Fn(function="move the closure between open and closed",
           performed_by=["closure_member", "opening_interface"]),
        Fn(function="retain the closure in the closed state", performed_by=[retainer]),
        Fn(function="resist accidental release", performed_by=[retainer]),
        Fn(function="receive intentional user input", performed_by=[release]),
        Fn(function="release retention", performed_by=[release, retainer]),
        Fn(function="permit repeated cycling", performed_by=["closure_member", retainer]),
        Fn(function="limit opening travel", performed_by=["opening_stop"]),
        Fn(function="transfer retention loads into the structure", performed_by=["housing"]),
    )


# Obligations shared by every closure architecture.
def _catch_obligations(retainer: str, release: str) -> tuple[Ob, ...]:
    return (
        Ob(element="closure_member", kind=OK.GUIDANCE, reacted_by="opening_interface",
           why="opening motion needs a defined rotational or translational interface"),
        Ob(element="closure_member", kind=OK.TRAVEL_LIMIT, reacted_by="opening_stop",
           why="opening travel must stop before the closure or its interface is overloaded"),
        Ob(element=release, kind=OK.USER_ACCESS, reacted_by="housing",
           why="the release surface must stay reachable from outside the closed product"),
        Ob(element=retainer, kind=OK.CLEARANCE, reacted_by="housing",
           why="retention and release features must not obstruct the usable internal volume"),
    )


FAMILIES: tuple[MechanismFamily, ...] = (
    # ---- rotation -> translation, continuous ----------------------------
    MechanismFamily(
        id="screw_drive",
        principle="Threaded pair converting continuous rotation to translation",
        input_kind=Q.ROTATION, output_kind=Q.TRANSLATION, continuity=Continuity.CONTINUOUS,
        reversible=True,
        roles=(_INPUT, _INPUT_SUPPORT,
               RoleTemplate("transmission_shaft", "transmission", True, ("rotating", "load_bearing", "manufactured"), form=FC.SHAFT, motion=MK.ROTATION, element_class=EC.BODY),
               RoleTemplate("threaded_member", "conversion", True, ("rotating", "threaded_pair", "load_bearing", "manufactured"), form=FC.SHAFT, motion=MK.ROTATION, element_class=EC.BODY),
               RoleTemplate("thrust_support", "support", False, ("load_bearing", "manufactured"), form=FC.COLLAR, motion=MK.FIXED, element_class=EC.JOINT, permits=MK.ROTATION),
               RoleTemplate("travelling_member", "output", True, ("translating", "load_bearing", "manufactured"), form=FC.PLATE, motion=MK.TRANSLATION, element_class=EC.BODY),
               RoleTemplate("guide_member", "guidance", False, ("load_bearing", "manufactured"), form=FC.RAIL, motion=MK.FIXED, element_class=EC.JOINT, permits=MK.TRANSLATION),
               _TRAVEL_STOP, _TRAVEL_STOP_FAR, _HOUSING,
               _CONVERSION_NUT, _AXIS_REDIRECT, _GUIDE_OPPOSED),
        element_chain=("input_member", "transmission_shaft", "redirect_member",
                       "threaded_member", "travelling_nut", "travelling_member"),
        functions=_drive_functions("threaded_member", "travelling_member"),
        state_relations=("travel is proportional to input revolutions",),
        holding_principle="friction within the threaded pair can hold position without input",
        holds=HoldingCapability.BIDIRECTIONAL,
        support_obligations=(
            Ob(element="input_member", kind=OK.RADIAL_SUPPORT, reacted_by="input_support",
               why="a hand-driven input shaft must be located against side load"),
            Ob(element="threaded_member", kind=OK.RADIAL_SUPPORT, reacted_by="housing",
               why="the rotating threaded member must run on a fixed axis"),
            Ob(element="threaded_member", kind=OK.AXIAL_THRUST, reacted_by="thrust_support",
               why="the payload reacts as axial thrust along the screw and must be taken out"),
            Ob(element="travelling_member", kind=OK.ANTI_ROTATION, reacted_by="guide_member",
               why="without anti-rotation the nut turns with the screw and no travel results"),
            Ob(element="travelling_member", kind=OK.GUIDANCE, reacted_by="guide_member",
               why="guidance must not depend on the thread, which cannot carry moment"),
            Ob(element="travelling_member", kind=OK.TRAVEL_LIMIT, reacted_by="travel_stop",
               why="travel must end positively without driving the nut off the thread"),
            Ob(element="travelling_member", kind=OK.CLEARANCE, reacted_by="housing",
               why="the full swept volume of the output must stay clear"),
            Ob(element="input_member", kind=OK.USER_ACCESS, reacted_by="housing",
               why="the input must remain reachable while the mechanism stays enclosed"),
            *_drive_completion_obligations("travelling_member"),
        ),
        load_path=("payload", "travelling_member", "threaded_member", "thrust_support", "housing"),
        interfaces=(
            If(between=("input_member", "transmission_shaft"), kind=IK.FIXED_ATTACHMENT,
               transmits="torque", crosses_boundary=True),
            If(between=("travelling_member", "guide_member"), kind=IK.SLIDING_JOINT,
               transmits="reaction moment and side load"),
            If(between=("threaded_member", "travelling_member"), kind=IK.THREADED_PAIR,
               transmits="axial force and torque"),
            If(between=("threaded_member", "thrust_support"), kind=IK.ROTATIONAL_JOINT,
               transmits="axial thrust"),
            If(between=("input_member", "input_support"), kind=IK.ROTATIONAL_JOINT,
               transmits="radial load"),
            If(between=("travelling_member", "travel_stop"), kind=IK.CONTACT_PAIR,
               transmits="end-of-travel reaction"),
            If(between=("input_support", "housing"), kind=IK.FIXED_ATTACHMENT,
               transmits="reaction into the structure"),
            If(between=("thrust_support", "housing"), kind=IK.FIXED_ATTACHMENT,
               transmits="reaction into the structure"),
            If(between=("guide_member", "housing"), kind=IK.FIXED_ATTACHMENT,
               transmits="reaction into the structure"),
            If(between=("travel_stop", "housing"), kind=IK.FIXED_ATTACHMENT,
               transmits="reaction into the structure"),
            *_drive_completion("threaded_member"),
            *_axis_redirect("threaded_member"),
        ),
        spatial_implications=("the threaded member spans the full travel and sets product height",
                              "the guide runs parallel to travel",
                              "the input member crosses the enclosure boundary"),
        motion_envelopes=("travelling member sweeps a prism along the travel axis",
                          "input member sweeps a disc outside the enclosure"),
        strengths=("high mechanical advantage", "compact along the travel axis", "may hold without input"),
        weaknesses=("low efficiency", "slow travel per input revolution"),
        risks=("thread wear over repeated cycles", "travelling member tilts if guidance is weak",
               "binding if the guide and screw axes are not parallel",
               "screw buckling under compressive load"),
        tradeoffs=("holding capability against input effort and speed",),
        assumptions=("continuous rotary input is available at the boundary",),
        downstream_decisions=("thread lead", "guide count and spacing", "member proportions"),
        parameters=(
            Param("thread_lead", "threaded_member", "length",
                  "travel per turn; it sets the input turns for the required stroke and whether the pair back-drives"),
            Param("pitch_diameter", "threaded_member", "length",
                  "the radius torque acts at, so it sets both the input effort and the thread stress"),
            Param("helix_angle", "threaded_member", "angle",
                  "with friction it decides self-locking, which is how the load is held with no input"),
            Param("guide_spacing", "guide_member", "length",
                  "the couple arm reacting the moment on the travelling member; too short and it binds"),
        ),

        states=_drive_states("travelling_member", "travel_stop")[0],
        transitions=_drive_states("travelling_member", "travel_stop")[1],    ),
    MechanismFamily(
        id="toothed_linear_drive",
        principle="Toothed rotary member engaging a linear toothed member",
        input_kind=Q.ROTATION, output_kind=Q.TRANSLATION, continuity=Continuity.CONTINUOUS,
        reversible=True,
        roles=(_INPUT, _INPUT_SUPPORT,
               RoleTemplate("transmission_shaft", "transmission", True, ("rotating", "load_bearing", "manufactured"), form=FC.SHAFT, motion=MK.ROTATION, element_class=EC.BODY),
               RoleTemplate("rotary_toothed_member", "conversion", True, ("rotating", "gear_pair", "load_bearing", "manufactured"), form=FC.SHAFT, motion=MK.ROTATION, element_class=EC.BODY),
               RoleTemplate("linear_toothed_member", "conversion", True, ("translating", "gear_pair", "load_bearing", "manufactured"), form=FC.RAIL, motion=MK.TRANSLATION, element_class=EC.BODY),
               RoleTemplate("travelling_member", "output", True, ("translating", "load_bearing", "manufactured"), form=FC.PLATE, motion=MK.TRANSLATION, element_class=EC.BODY),
               RoleTemplate("guide_member", "guidance", False, ("load_bearing", "manufactured"), form=FC.RAIL, motion=MK.FIXED, element_class=EC.JOINT, permits=MK.TRANSLATION),
               _TRAVEL_STOP, _TRAVEL_STOP_FAR, _HOUSING,
               _CONVERSION_NUT, _AXIS_REDIRECT, _GUIDE_OPPOSED),
        element_chain=("input_member", "transmission_shaft", "rotary_toothed_member",
                       "linear_toothed_member", "travelling_member"),
        functions=_drive_functions("rotary_toothed_member", "travelling_member") + (
            Fn(function="maintain tooth engagement across the travel",
               performed_by=["rotary_toothed_member", "linear_toothed_member", "guide_member"]),
            Fn(function="provide a holding function", performed_by=[]),
        ),
        state_relations=("travel is proportional to input rotation through the toothed pitch",),
        holding_principle="none inherent; a separate holding function is required to keep position",
        holds=HoldingCapability.NONE,
        support_obligations=(
            Ob(element="input_member", kind=OK.RADIAL_SUPPORT, reacted_by="input_support",
               why="a hand-driven input shaft must be located against side load"),
            Ob(element="rotary_toothed_member", kind=OK.RADIAL_SUPPORT, reacted_by="housing",
               why="the rotary member must run on a fixed axis for the mesh to hold"),
            Ob(element="linear_toothed_member", kind=OK.GUIDANCE, reacted_by="guide_member",
               why="the linear member must be guided along its travel"),
            Ob(element="linear_toothed_member", kind=OK.ALIGNMENT, reacted_by="guide_member",
               why="separation force at the mesh must not open the engagement"),
            Ob(element="travelling_member", kind=OK.TRAVEL_LIMIT, reacted_by="travel_stop",
               why="travel must end before the toothed members disengage"),
            Ob(element="travelling_member", kind=OK.CLEARANCE, reacted_by="housing",
               why="the full swept volume of the output must stay clear"),
            Ob(element="input_member", kind=OK.USER_ACCESS, reacted_by="housing",
               why="the input must remain reachable while the mechanism stays enclosed"),
            *_drive_completion_obligations("travelling_member"),
        ),
        load_path=("payload", "travelling_member", "linear_toothed_member", "rotary_toothed_member", "housing"),
        interfaces=(
            If(between=("input_member", "transmission_shaft"), kind=IK.FIXED_ATTACHMENT,
               transmits="torque", crosses_boundary=True),
            If(between=("rotary_toothed_member", "linear_toothed_member"), kind=IK.TOOTHED_MESH,
               transmits="tangential force"),
            If(between=("linear_toothed_member", "travelling_member"), kind=IK.FIXED_ATTACHMENT,
               transmits="travel force"),
            If(between=("travelling_member", "guide_member"), kind=IK.SLIDING_JOINT,
               transmits="reaction moment and side load"),
            If(between=("input_member", "input_support"), kind=IK.ROTATIONAL_JOINT,
               transmits="radial load"),
            If(between=("travelling_member", "travel_stop"), kind=IK.CONTACT_PAIR,
               transmits="end-of-travel reaction"),
            If(between=("input_support", "housing"), kind=IK.FIXED_ATTACHMENT,
               transmits="reaction into the structure"),
            If(between=("guide_member", "housing"), kind=IK.FIXED_ATTACHMENT,
               transmits="reaction into the structure"),
            If(between=("travel_stop", "housing"), kind=IK.FIXED_ATTACHMENT,
               transmits="reaction into the structure"),
            *_drive_completion("rotary_toothed_member"),
        ),
        spatial_implications=("the linear member spans the full travel plus engagement run-out",
                              "the rotary member sits beside the travel axis, widening the product"),
        motion_envelopes=("linear member sweeps its own length plus travel",
                          "rotary member sweeps a disc at the engagement plane"),
        strengths=("high efficiency", "fast travel per input revolution"),
        weaknesses=("does not hold position unaided", "engagement must be maintained"),
        risks=("output moves under load when input is released",
               "mesh separation if alignment is lost", "tooth loading concentrated at one contact"),
        tradeoffs=("speed and efficiency against the need for a separate holding function",),
        assumptions=("continuous rotary input is available at the boundary",),
        downstream_decisions=("tooth proportions", "engagement geometry", "guide arrangement",
                              "holding function"),

        states=_drive_states("travelling_member", "travel_stop")[0],
        transitions=_drive_states("travelling_member", "travel_stop")[1],    ),
    MechanismFamily(
        id="flexible_tension_drive",
        principle="Winding a flexible tension member onto a rotating spool",
        input_kind=Q.ROTATION, output_kind=Q.TRANSLATION, continuity=Continuity.CONTINUOUS,
        reversible=True,
        roles=(_INPUT, _INPUT_SUPPORT,
               RoleTemplate("spool", "conversion", True, ("rotating", "load_bearing", "manufactured"), form=FC.SHAFT, motion=MK.ROTATION, element_class=EC.BODY),
               RoleTemplate("tension_member", "transmission", True, ("load_bearing",), form=FC.FLEXIBLE, motion=MK.TRANSLATION, element_class=EC.BODY),
               RoleTemplate("travelling_member", "output", True, ("translating", "load_bearing", "manufactured"), form=FC.PLATE, motion=MK.TRANSLATION, element_class=EC.BODY),
               RoleTemplate("guide_member", "guidance", False, ("load_bearing", "manufactured"), form=FC.RAIL, motion=MK.FIXED, element_class=EC.JOINT, permits=MK.TRANSLATION),
               _TRAVEL_STOP, _TRAVEL_STOP_FAR, _HOUSING,
               _CONVERSION_NUT, _AXIS_REDIRECT, _GUIDE_OPPOSED),
        element_chain=("input_member", "spool", "tension_member", "travelling_member"),
        functions=_drive_functions("spool", "travelling_member") + (
            Fn(function="route and tension the flexible member",
               performed_by=["tension_member", "guide_member"]),
            Fn(function="provide a holding function", performed_by=[]),
        ),
        state_relations=("travel is proportional to wound length",),
        holding_principle="none inherent; tension is lost when input is released",
        holds=HoldingCapability.NONE,
        support_obligations=(
            Ob(element="input_member", kind=OK.RADIAL_SUPPORT, reacted_by="input_support",
               why="a hand-driven input shaft must be located against side load"),
            Ob(element="spool", kind=OK.RADIAL_SUPPORT, reacted_by="housing",
               why="the spool must run on a fixed axis for winding to stay regular"),
            Ob(element="tension_member", kind=OK.ALIGNMENT, reacted_by="guide_member",
               why="the tension path must be routed or it will slacken and jump"),
            Ob(element="travelling_member", kind=OK.GUIDANCE, reacted_by="guide_member",
               why="a tension member carries no moment, so the output needs its own guidance"),
            Ob(element="travelling_member", kind=OK.TRAVEL_LIMIT, reacted_by="travel_stop",
               why="travel must end before the tension member fully unwinds"),
            Ob(element="travelling_member", kind=OK.CLEARANCE, reacted_by="housing",
               why="the full swept volume of the output must stay clear"),
            Ob(element="input_member", kind=OK.USER_ACCESS, reacted_by="housing",
               why="the input must remain reachable while the mechanism stays enclosed"),
            *_drive_completion_obligations("travelling_member"),
        ),
        load_path=("payload", "travelling_member", "tension_member", "spool", "housing"),
        interfaces=(
            If(between=("input_member", "spool"), kind=IK.FIXED_ATTACHMENT,
               transmits="torque", crosses_boundary=True),
            If(between=("spool", "tension_member"), kind=IK.FLEXIBLE_LINK, transmits="tension"),
            If(between=("tension_member", "travelling_member"), kind=IK.FLEXIBLE_LINK,
               transmits="tension"),
            If(between=("travelling_member", "guide_member"), kind=IK.SLIDING_JOINT,
               transmits="reaction moment and side load"),
            If(between=("input_member", "input_support"), kind=IK.ROTATIONAL_JOINT,
               transmits="radial load"),
            If(between=("travelling_member", "travel_stop"), kind=IK.CONTACT_PAIR,
               transmits="end-of-travel reaction"),
            If(between=("input_support", "housing"), kind=IK.FIXED_ATTACHMENT,
               transmits="reaction into the structure"),
            If(between=("guide_member", "housing"), kind=IK.FIXED_ATTACHMENT,
               transmits="reaction into the structure"),
            If(between=("travel_stop", "housing"), kind=IK.FIXED_ATTACHMENT,
               transmits="reaction into the structure"),
            *_drive_completion("spool"),
        ),
        spatial_implications=("the tension member needs a routing path of at least the travel length",
                              "the spool width grows with wound length"),
        motion_envelopes=("travelling member sweeps along the travel axis",
                          "the tension path sweeps a plane during winding"),
        strengths=("very low friction", "tolerant of misalignment"),
        weaknesses=("carries tension only", "requires a separate holding function"),
        risks=("uncontrolled descent if holding fails", "spooling irregularity",
               "slack accumulating on unloaded return"),
        tradeoffs=("low friction against the need for holding and routing discipline",),
        assumptions=("the load acts along one direction so tension is sufficient",),
        downstream_decisions=("spool proportions", "routing path", "holding function"),

        states=_drive_states("travelling_member", "travel_stop")[0],
        transitions=_drive_states("travelling_member", "travel_stop")[1],    ),
    # ---- rotation -> rotation, intermittent ------------------------------
    MechanismFamily(
        id="intermittent_indexing_pair",
        principle="Driver and driven pair producing discrete advance with dwell",
        input_kind=Q.ROTATION, output_kind=Q.ROTATION, continuity=Continuity.INTERMITTENT,
        reversible=False,
        roles=(_INPUT, _INPUT_SUPPORT,
               RoleTemplate("driver_member", "conversion", True, ("rotating", "intermittent_pair", "load_bearing", "manufactured"), form=FC.SHAFT, motion=MK.ROTATION, element_class=EC.BODY),
               _engagement_element("driver_member"),
               _engagement_element("indexed_member"),
               RoleTemplate("indexed_member", "output", True, ("rotating", "intermittent_pair", "load_bearing", "manufactured"), form=FC.SHAFT, motion=MK.ROTATION, element_class=EC.BODY),
               _OUTPUT_SUPPORT, _HOUSING),
        element_chain=("input_member", "driver_member", "indexed_member"),
        functions=(
            Fn(function="receive manual input", performed_by=["input_member"]),
            Fn(function="support the rotating input", performed_by=["input_support"]),
            Fn(function="transmit input across the enclosure boundary",
               performed_by=["input_member", "housing"]),
            Fn(function="advance the output by one discrete station",
               performed_by=["driver_member", "indexed_member"]),
            Fn(function="hold the output stationary between advances",
               performed_by=["driver_member"]),
            Fn(function="maintain the axis separation that sets engagement",
               performed_by=["housing"]),
            Fn(function="transfer loads into the structure", performed_by=["housing"]),
        ),
        state_relations=("one input revolution advances the output by one station",
                         "the output is stationary for the remainder of the input cycle"),
        holding_principle="the driver geometry locks the output during dwell",
        holds=HoldingCapability.BIDIRECTIONAL,
        support_obligations=(
            Ob(element="input_member", kind=OK.RADIAL_SUPPORT, reacted_by="input_support",
               why="a hand-driven input shaft must be located against side load"),
            Ob(element="driver_member", kind=OK.RADIAL_SUPPORT, reacted_by="housing",
               why="the driver must run on a fixed axis"),
            Ob(element="indexed_member", kind=OK.RADIAL_SUPPORT, reacted_by="housing",
               why="the indexed member must run on a fixed parallel axis"),
            Ob(element="indexed_member", kind=OK.ALIGNMENT, reacted_by="housing",
               why="axis separation fixes the engagement and must be held"),
            Ob(element="indexed_member", kind=OK.CLEARANCE, reacted_by="housing",
               why="the swept circle of the indexed member bounds the internal volume"),
            Ob(element="input_member", kind=OK.USER_ACCESS, reacted_by="housing",
               why="the input must remain reachable while the mechanism stays enclosed"),
        ),
        load_path=("indexed load", "indexed_member", "driver_member", "housing"),
        interfaces=(
            If(between=("input_member", "driver_member"), kind=IK.FIXED_ATTACHMENT,
               transmits="torque", crosses_boundary=True),
            If(between=("driver_member", "driver_member_engagement"),
               kind=IK.FIXED_ATTACHMENT, transmits="drive torque out to a radius"),
            If(between=("indexed_member", "indexed_member_engagement"),
               kind=IK.FIXED_ATTACHMENT, transmits="output torque out to a radius"),
            If(between=("driver_member_engagement", "indexed_member_engagement"),
               kind=IK.CONTACT_PAIR,
               transmits="advance force and locking reaction"),
            If(between=("input_member", "input_support"), kind=IK.ROTATIONAL_JOINT,
               transmits="radial load"),
            If(between=("indexed_member", "housing"), kind=IK.ROTATIONAL_JOINT,
               transmits="radial load"),
            If(between=("input_support", "housing"), kind=IK.FIXED_ATTACHMENT,
               transmits="reaction into the structure"),
            *_output_bearing("indexed_member"),
        ),
        spatial_implications=("two parallel axes at a fixed separation set the product footprint",
                              "the indexed member's swept circle bounds the internal volume"),
        motion_envelopes=("indexed member sweeps a full disc",
                          "driver sweeps a disc overlapping it at the engagement region"),
        strengths=("positive station location", "dwell arises from the geometry itself"),
        weaknesses=("engagement clearance varies through the cycle",
                    "entry and exit conditions are phase-dependent"),
        risks=("locking geometry interfering with the engagement features",
               "impact at engagement if entry is not tangential"),
        tradeoffs=("dwell fraction against advance duration",),
        assumptions=("the output advances in one direction only",),
        downstream_decisions=("station count", "axis separation", "engagement and locking geometry"),
        parameters=(
            Param("station_count", "indexed_member", "count",
                  "how many stations one cycle divides into; it fixes the index angle and the whole geometry of the pair"),
            Param("crank_radius", "driver_member_engagement", "length",
                  "the radius the driving element engages at, which with the centre distance sets the motion law"),
            Param("centre_distance", "driver_member", "length",
                  "the two parallel axes are fixed by it; engagement is impossible if it is wrong"),
            Param("slot_width", "indexed_member_engagement", "length",
                  "the engaging element must enter with clearance but without backlash at the station"),
            Param("locking_arc", "driver_member", "angle",
                  "the arc over which the output is held during dwell, which is what makes indexing stable"),
        ),

        states=_index_states("indexed_member")[0],
        transitions=_index_states("indexed_member")[1],    ),
    MechanismFamily(
        id="pawl_advance_pair",
        principle="Reciprocating driver engaging a toothed wheel to advance one step",
        input_kind=Q.ROTATION, output_kind=Q.ROTATION, continuity=Continuity.INTERMITTENT,
        reversible=False,
        roles=(_INPUT, _INPUT_SUPPORT,
               RoleTemplate("driving_pawl", "conversion", True, ("compliant", "intermittent_pair", "load_bearing", "manufactured"), form=FC.LINK, motion=MK.COMPLIANT_DEFORMATION, element_class=EC.BODY),
               RoleTemplate("toothed_wheel", "output", True, ("rotating", "intermittent_pair", "load_bearing", "manufactured"), form=FC.SHAFT, motion=MK.ROTATION, element_class=EC.BODY),
               RoleTemplate("holding_pawl", "retention", True, ("compliant", "retention_interface", "manufactured"), form=FC.LINK, motion=MK.COMPLIANT_DEFORMATION, element_class=EC.BODY),
               _OUTPUT_SUPPORT, _HOUSING),
        element_chain=("input_member", "driving_pawl", "toothed_wheel"),
        functions=(
            Fn(function="receive manual input", performed_by=["input_member"]),
            Fn(function="support the rotating input", performed_by=["input_support"]),
            Fn(function="transmit input across the enclosure boundary",
               performed_by=["input_member", "housing"]),
            Fn(function="advance the output by one discrete station",
               performed_by=["driving_pawl", "toothed_wheel"]),
            Fn(function="prevent reverse motion between strokes", performed_by=["holding_pawl"]),
            Fn(function="return the driving element to its rest position",
               performed_by=["driving_pawl"]),
            Fn(function="transfer loads into the structure", performed_by=["housing"]),
        ),
        state_relations=("each input stroke advances the wheel by one tooth",
                         "a holding element prevents reverse motion between strokes"),
        holding_principle="a separate holding element blocks reverse rotation during dwell",
        holds=HoldingCapability.SINGLE_DIRECTION,
        support_obligations=(
            Ob(element="input_member", kind=OK.RADIAL_SUPPORT, reacted_by="input_support",
               why="a hand-driven input shaft must be located against side load"),
            Ob(element="toothed_wheel", kind=OK.RADIAL_SUPPORT, reacted_by="housing",
               why="the wheel must run on a fixed axis"),
            Ob(element="driving_pawl", kind=OK.STRUCTURAL_ROOT, reacted_by="housing",
               why="a compliant engaging element needs a fixed root and a defined rest position"),
            Ob(element="holding_pawl", kind=OK.STRUCTURAL_ROOT, reacted_by="housing",
               why="the holding element reacts reverse load and must be rooted"),
            Ob(element="toothed_wheel", kind=OK.CLEARANCE, reacted_by="housing",
               why="the wheel diameter dominates the internal volume"),
            Ob(element="input_member", kind=OK.USER_ACCESS, reacted_by="housing",
               why="the input must remain reachable while the mechanism stays enclosed"),
        ),
        load_path=("indexed load", "toothed_wheel", "holding_pawl", "housing"),
        interfaces=(
            If(between=("input_member", "driving_pawl"), kind=IK.FIXED_ATTACHMENT,
               transmits="stroke motion", crosses_boundary=True),
            If(between=("driving_pawl", "toothed_wheel"), kind=IK.CONTACT_PAIR,
               transmits="advance force"),
            If(between=("holding_pawl", "toothed_wheel"), kind=IK.CONTACT_PAIR,
               transmits="reverse blocking force"),
            If(between=("input_member", "input_support"), kind=IK.ROTATIONAL_JOINT,
               transmits="radial load"),
            If(between=("input_support", "housing"), kind=IK.FIXED_ATTACHMENT,
               transmits="reaction into the structure"),
            *_output_bearing("toothed_wheel"),
        ),
        spatial_implications=("engaging elements sit tangentially around the wheel, "
                              "so the wheel diameter dominates the internal volume",),
        motion_envelopes=("wheel sweeps a full disc",
                          "engaging elements sweep small arcs at its periphery"),
        strengths=("station count set by tooth count", "simple one-way behaviour"),
        weaknesses=("compliant elements are strain-limited", "position accuracy depends on holding"),
        risks=("reverse motion if the holding element disengages",
               "compliant element fatigue at the root"),
        tradeoffs=("advance force against holding security",),
        assumptions=("one-way advance is acceptable",),
        downstream_decisions=("tooth count", "engagement angles", "compliant element proportions"),

        states=_index_states("toothed_wheel")[0],
        transitions=_index_states("toothed_wheel")[1],    ),
    # ---- force -> held state (retention with intentional release) --------
    MechanismFamily(
        id="compliant_catch",
        principle="Elastic element deflecting over a feature and springing back to retain",
        input_kind=Q.FORCE, output_kind=Q.STATE, continuity=Continuity.HELD,
        reversible=True,
        roles=(RoleTemplate("closure_member", "output", True, ("moving_boundary", "user_contact", "manufactured"), form=FC.PLATE, motion=MK.ROTATION, element_class=EC.BODY),
               _OPENING_INTERFACE,
               RoleTemplate("compliant_element", "retention", True, ("compliant", "retention_interface", "user_release", "precision_interface", "manufactured"), form=FC.PLATE, motion=MK.COMPLIANT_DEFORMATION, element_class=EC.BODY),
               RoleTemplate("catch_feature", "retention", False, ("retention_interface", "load_bearing", "manufactured"), form=FC.BLOCK, motion=MK.FIXED, element_class=EC.FEATURE),
               _OPENING_STOP, _HOUSING),
        element_chain=("user input", "compliant_element", "catch_feature", "closure_member"),
        functions=_catch_functions("compliant_element", "compliant_element"),
        state_relations=("closed state is held until a deliberate input deflects the element",
                         "the same element re-engages on closing"),
        holding_principle="elastic deflection and re-engagement; released by deflecting the element clear",
        holds=HoldingCapability.SINGLE_DIRECTION,
        support_obligations=_catch_obligations("compliant_element", "compliant_element") + (
            Ob(element="compliant_element", kind=OK.STRUCTURAL_ROOT, reacted_by="housing",
               why="a deflecting element needs a structurally supported root to react bending"),
            Ob(element="catch_feature", kind=OK.ALIGNMENT, reacted_by="closure_member",
               why="the catch must resist the retaining force and stay aligned with the element"),
            Ob(element="compliant_element", kind=OK.CLEARANCE, reacted_by="housing",
               why="deflection space must stay clear behind the element through its full travel"),
        ),
        load_path=("disturbance", "closure_member", "catch_feature", "compliant_element", "housing"),
        interfaces=(
            If(between=("compliant_element", "catch_feature"), kind=IK.CONTACT_PAIR,
               transmits="retention force"),
            If(between=("compliant_element", "housing"), kind=IK.FIXED_ATTACHMENT,
               transmits="bending reaction at the root"),
            If(between=("closure_member", "opening_interface"), kind=IK.ROTATIONAL_JOINT,
               transmits="opening motion and closure weight"),
            If(between=("closure_member", "opening_stop"), kind=IK.CONTACT_PAIR,
               transmits="end-of-opening reaction"),
            If(between=("compliant_element", "housing"), kind=IK.USER_CONTACT,
               transmits="release input", crosses_boundary=True),
            If(between=("opening_interface", "housing"), kind=IK.FIXED_ATTACHMENT,
               transmits="reaction into the structure"),
            If(between=("catch_feature", "housing"), kind=IK.FIXED_ATTACHMENT,
               transmits="reaction into the structure"),
            If(between=("opening_stop", "housing"), kind=IK.FIXED_ATTACHMENT,
               transmits="reaction into the structure"),
        ),
        spatial_implications=("the actuation surface must be reachable from outside",
                              "the retaining pair sits at the closure boundary",
                              "deflection space must stay clear behind the element"),
        motion_envelopes=("the compliant element sweeps its deflection during engagement and release",
                          "the closure member sweeps its opening path"),
        strengths=("no separate fastener required", "tool-free repeated operation",
                   "low part count", "compact"),
        weaknesses=("strain-limited", "may relax over many cycles"),
        risks=("permanent deformation if over-deflected", "retention weakening with cycling",
               "root fatigue", "insertion or release force outside a usable range",
               "sensitivity to tolerance and material"),
        tradeoffs=("retention security against ease of intentional release",),
        assumptions=("the retaining element may be integral to a moulded or printed part",),
        downstream_decisions=("element proportions", "engagement angles", "actuation surface form"),
        parameters=(
            Param("beam_length", "compliant_member", "length",
                  "a cantilever's stiffness goes as the cube of its length, so this dominates both insertion force and strain"),
            Param("root_thickness", "compliant_member", "length",
                  "the root carries the peak bending stress and is where a snap fit fails"),
            Param("tip_thickness", "compliant_member", "length",
                  "tapering the tip evens the strain along the beam instead of concentrating it at the root"),
            Param("hook_depth", "compliant_member", "length",
                  "the undercut is what retains; it also sets how far the beam must deflect to engage"),
            Param("insertion_angle", "compliant_member", "angle",
                  "the lead-in angle converts insertion force into deflection and decides the assembly effort"),
            Param("retention_angle", "compliant_member", "angle",
                  "the return angle decides whether the catch releases when pulled or locks"),
            Param("max_strain", "compliant_member", "ratio",
                  "peak strain at full deflection against the material limit is the check that the snap survives assembly"),
        ),

        states=_catch_states("compliant_element", "compliant_element")[0],
        transitions=_catch_states("compliant_element", "compliant_element")[1],    ),
    MechanismFamily(
        id="over_centre_catch",
        principle="Linkage passing through an over-centre position to hold a closure",
        input_kind=Q.FORCE, output_kind=Q.STATE, continuity=Continuity.HELD,
        reversible=True,
        roles=(RoleTemplate("closure_member", "output", True, ("moving_boundary", "user_contact", "manufactured"), form=FC.PLATE, motion=MK.ROTATION, element_class=EC.BODY),
               _OPENING_INTERFACE,
               RoleTemplate("actuating_lever", "release", True, ("rotating", "user_contact", "user_release", "manufactured"), form=FC.LINK, motion=MK.ROTATION, element_class=EC.BODY),
               RoleTemplate("tension_link", "retention", True, ("retention_interface", "load_bearing", "manufactured"), form=FC.LINK, motion=MK.ROTATION_TRANSLATION, element_class=EC.BODY),
               RoleTemplate("catch_feature", "retention", False, ("retention_interface", "load_bearing", "manufactured"), form=FC.BLOCK, motion=MK.FIXED, element_class=EC.FEATURE),
               _OPENING_STOP, _HOUSING),
        element_chain=("user input", "actuating_lever", "tension_link", "catch_feature", "closure_member"),
        functions=_catch_functions("tension_link", "actuating_lever"),
        state_relations=("past the over-centre position the closure is held without further input",
                         "the state changes only when the lever is driven back"),
        holding_principle="geometric over-centre lock; released by reversing the lever",
        holds=HoldingCapability.BIDIRECTIONAL,
        support_obligations=_catch_obligations("tension_link", "actuating_lever") + (
            Ob(element="actuating_lever", kind=OK.RADIAL_SUPPORT, reacted_by="housing",
               why="the lever needs a located pivot to define the over-centre position"),
            Ob(element="tension_link", kind=OK.ALIGNMENT, reacted_by="catch_feature",
               why="the link needs defined attachment at both ends or the lock is lost"),
            Ob(element="actuating_lever", kind=OK.CLEARANCE, reacted_by="housing",
               why="the lever swings outside the closure boundary and needs external clearance"),
        ),
        load_path=("disturbance", "closure_member", "catch_feature", "tension_link", "housing"),
        interfaces=(
            If(between=("actuating_lever", "housing"), kind=IK.ROTATIONAL_JOINT,
               transmits="lever pivot reaction"),
            If(between=("actuating_lever", "tension_link"), kind=IK.ROTATIONAL_JOINT,
               transmits="clamping force"),
            If(between=("tension_link", "catch_feature"), kind=IK.CONTACT_PAIR,
               transmits="retention force"),
            If(between=("closure_member", "opening_interface"), kind=IK.ROTATIONAL_JOINT,
               transmits="opening motion and closure weight"),
            If(between=("closure_member", "opening_stop"), kind=IK.CONTACT_PAIR,
               transmits="end-of-opening reaction"),
            If(between=("actuating_lever", "housing"), kind=IK.USER_CONTACT,
               transmits="release input", crosses_boundary=True),
            If(between=("opening_interface", "housing"), kind=IK.FIXED_ATTACHMENT,
               transmits="reaction into the structure"),
            If(between=("catch_feature", "housing"), kind=IK.FIXED_ATTACHMENT,
               transmits="reaction into the structure"),
            If(between=("opening_stop", "housing"), kind=IK.FIXED_ATTACHMENT,
               transmits="reaction into the structure"),
        ),
        spatial_implications=("the lever swings outside the closure boundary and needs external clearance",
                              "the linkage occupies a plane across the closure line"),
        motion_envelopes=("the lever sweeps an arc outside the product",
                          "the link sweeps a plane through the over-centre position"),
        strengths=("high and adjustable retaining force", "unambiguous open and closed states",
                   "good transport security"),
        weaknesses=("more parts", "protrudes beyond the closure boundary"),
        risks=("snagging on the protruding lever", "over-centre position lost if geometry shifts",
               "larger envelope and higher assembly cost"),
        tradeoffs=("retention force against part count and protrusion",),
        assumptions=("external clearance is available for the lever swing",),
        downstream_decisions=("lever proportions", "link geometry", "over-centre offset"),

        states=_catch_states("tension_link", "actuating_lever")[0],
        transitions=_catch_states("tension_link", "actuating_lever")[1],    ),
    MechanismFamily(
        id="friction_detent_catch",
        principle="Interference between mating features held by friction or light preload",
        input_kind=Q.FORCE, output_kind=Q.STATE, continuity=Continuity.HELD,
        reversible=True,
        roles=(RoleTemplate("closure_member", "output", True, ("moving_boundary", "user_contact", "user_release", "manufactured"), form=FC.PLATE, motion=MK.ROTATION, element_class=EC.BODY),
               _OPENING_INTERFACE,
               RoleTemplate("detent_feature", "retention", False, ("retention_interface", "manufactured"), form=FC.BLOCK, motion=MK.FIXED, element_class=EC.FEATURE),
               _OPENING_STOP, _HOUSING),
        element_chain=("user input", "detent_feature", "closure_member"),
        functions=_catch_functions("detent_feature", "closure_member"),
        state_relations=("the closed state is held by interference until a deliberate pull exceeds it",),
        holding_principle="frictional or interference preload; released by exceeding it",
        holds=HoldingCapability.SINGLE_DIRECTION,
        support_obligations=_catch_obligations("detent_feature", "closure_member") + (
            Ob(element="detent_feature", kind=OK.ALIGNMENT, reacted_by="closure_member",
               why="the mating features must stay aligned across repeated cycles"),
            Ob(element="detent_feature", kind=OK.STRUCTURAL_ROOT, reacted_by="housing",
               why="the interference feature reacts the retaining force into the structure"),
        ),
        load_path=("disturbance", "closure_member", "detent_feature", "housing"),
        interfaces=(
            If(between=("closure_member", "detent_feature"), kind=IK.CONTACT_PAIR,
               transmits="interference retention force"),
            If(between=("closure_member", "opening_interface"), kind=IK.ROTATIONAL_JOINT,
               transmits="opening motion and closure weight"),
            If(between=("closure_member", "opening_stop"), kind=IK.CONTACT_PAIR,
               transmits="end-of-opening reaction"),
            If(between=("closure_member", "housing"), kind=IK.USER_CONTACT,
               transmits="release input", crosses_boundary=True),
            If(between=("opening_interface", "housing"), kind=IK.FIXED_ATTACHMENT,
               transmits="reaction into the structure"),
            If(between=("detent_feature", "housing"), kind=IK.FIXED_ATTACHMENT,
               transmits="reaction into the structure"),
            If(between=("opening_stop", "housing"), kind=IK.FIXED_ATTACHMENT,
               transmits="reaction into the structure"),
        ),
        spatial_implications=("no protrusion beyond the closure boundary",
                              "the interference pair sits on the closure line itself"),
        motion_envelopes=("the closure member sweeps its opening path; no separate element moves",),
        strengths=("fewest parts", "nothing protrudes"),
        weaknesses=("retention force is least predictable", "wears with cycling"),
        risks=("retention decaying with repeated use", "accidental opening if preload is low",
               "release force rising if the interference is set high"),
        tradeoffs=("simplicity against retention predictability",),
        assumptions=("moderate retention is sufficient for the stated handling",),
        downstream_decisions=("interference amount", "feature form", "material pairing"),
        parameters=(
            Param("interference", "detent_feature", "length",
                  "the preload holding the catch closed is the interference between the mating features; too little and it releases on its own, too much and it cannot be opened by hand"),
            Param("engagement_depth", "detent_feature", "length",
                  "how far the features overlap sets the retention force and the travel needed to release"),
            Param("release_force", "closure_member", "force",
                  "a catch a person cannot open has failed, and this is the quantity that says so"),
            Param("friction_coefficient", "detent_feature", "ratio",
                  "retention by friction depends on the material pairing; the self-release check is written against it"),
        ),

        states=_catch_states("detent_feature", "closure_member")[0],
        transitions=_catch_states("detent_feature", "closure_member")[1],    ),
)


def families_for(input_kind: Q, output_kind: Q, continuity: Continuity) -> list[MechanismFamily]:
    """Exact signature match. No text, no product identity, no fallback."""
    return [f for f in FAMILIES
            if f.input_kind is input_kind
            and f.output_kind is output_kind
            and f.continuity is continuity]


def families_for_transform(input_kind: Q, output_kind: Q) -> list[MechanismFamily]:
    """Signature match ignoring continuity, for when Stage 01 left it unstated."""
    return [f for f in FAMILIES if f.input_kind is input_kind and f.output_kind is output_kind]


def by_id(fid: str) -> MechanismFamily:
    for f in FAMILIES:
        if f.id == fid:
            return f
    raise KeyError(fid)


# ---------------------------------------------------------------------------
# What a declared relationship demands of relative position.
#
# Every row is statics or kinematics, not product knowledge: "a threaded pair is
# coaxial" holds in any product that contains one. A row that exists because a
# benchmark needed it would make this table benchmark-specific knowledge wearing
# a general name, so each is stated as the mechanical fact it encodes.
# ---------------------------------------------------------------------------
INTERFACE_RELATION: dict[IK, tuple[SRK, str]] = {
    IK.ROTATIONAL_JOINT: (
        SRK.SHARED_AXIS,
        "a revolute pair turns about one axis, so both members must lie on it",
    ),
    IK.SLIDING_JOINT: (
        SRK.COMMON_TRAVEL_DIRECTION,
        "a prismatic pair slides along one direction over a shared span",
    ),
    IK.THREADED_PAIR: (
        SRK.COAXIAL_WORKING_OVERLAP,
        "a helical pair is coaxial and must stay engaged over its working length",
    ),
    IK.TOOTHED_MESH: (
        SRK.MATING_ADJACENCY,
        "teeth transmit only in contact, so the mesh must be held",
    ),
    IK.FIXED_ATTACHMENT: (
        SRK.MATING_ADJACENCY,
        "a rigid attachment transmits through a shared interface",
    ),
    IK.CONTACT_PAIR: (
        SRK.MATING_ADJACENCY,
        "a contact pair transmits only where the surfaces meet",
    ),
    IK.FLEXIBLE_LINK: (
        SRK.CONTINUOUS_ROUTE,
        "a tension member needs a continuous route, not adjacency; remoteness is fine",
    ),
    IK.USER_CONTACT: (
        SRK.EXTERIOR_REACHABLE,
        "a surface a user acts on must be reachable from outside the boundary",
    ),
}

OBLIGATION_RELATION: dict[OK, tuple[SRK, str]] = {
    OK.RADIAL_SUPPORT: (
        SRK.AXIS_SURROUNDED,
        "a radial reaction acts around the axis it locates",
    ),
    OK.AXIAL_THRUST: (
        SRK.AXIAL_REACTION_STATION,
        "an axial reaction acts along the axis at one of its ends",
    ),
    OK.GUIDANCE: (
        SRK.COMMON_TRAVEL_DIRECTION,
        "guidance acts along the guided motion over a shared span",
    ),
    OK.ANTI_ROTATION: (
        SRK.COMMON_TRAVEL_DIRECTION,
        "the reacting element must run alongside the travel to hold the couple",
    ),
    OK.STRUCTURAL_ROOT: (
        SRK.MATING_ADJACENCY,
        "a root reacts bending through the structure it is built into",
    ),
    OK.ALIGNMENT: (
        SRK.MATING_ADJACENCY,
        "features held in alignment must meet",
    ),
    OK.TRAVEL_LIMIT: (
        SRK.CONTACT_AT_EXTREME,
        "a limit acts only where the motion reaches its extreme",
    ),
    OK.CLEARANCE: (
        SRK.DISJOINT_SWEPT,
        "a region kept clear must not be entered by the swept volume",
    ),
    OK.USER_ACCESS: (
        SRK.EXTERIOR_REACHABLE,
        "a surface a user must reach cannot be sealed inside the boundary",
    ),
}


# ---------------------------------------------------------------------------
# Where a relation of each kind is *attached*, topologically.
#
# This is mechanical knowledge, not layout: a revolute pair lives on a line, a
# prismatic pair lives along a path, a bolted joint lives on a shared surface.
# The statement holds in any product containing one, so it sits beside the
# relation table rather than in the stage that resolves it.
# ---------------------------------------------------------------------------
RELATION_ANCHOR: dict[SRK, tuple[TK, str]] = {
    SRK.SHARED_AXIS: (
        TK.AXIS,
        "a revolute pair turns about a line, so the relation lives on that line",
    ),
    SRK.COAXIAL_WORKING_OVERLAP: (
        TK.AXIS,
        "a helical pair engages along a span of its common axis",
    ),
    SRK.COMMON_TRAVEL_DIRECTION: (
        TK.CORRIDOR,
        "guidance acts along the whole path the guided element travels",
    ),
    SRK.MATING_ADJACENCY: (
        TK.CONTACT_SURFACE,
        "a rigid or contacting joint transmits across the surface the parts share",
    ),
    SRK.AXIS_SURROUNDED: (
        TK.AXIS,
        "a radial reaction acts around the line it locates",
    ),
    SRK.AXIAL_REACTION_STATION: (
        TK.AXIS,
        "an axial reaction acts at a station on the axis",
    ),
    SRK.CONTACT_AT_EXTREME: (
        TK.CONTACT_SURFACE,
        "a limit acts on the surfaces that meet when travel ends",
    ),
    SRK.DISJOINT_SWEPT: (
        TK.VOLUME,
        "a keep-clear demand is about a volume, not an attachment",
    ),
    SRK.EXTERIOR_REACHABLE: (
        TK.BOUNDARY,
        "reachability is a property of the enclosure surface that is crossed",
    ),
    SRK.CONTINUOUS_ROUTE: (
        TK.CORRIDOR,
        "a flexible member occupies a routed path rather than a joint",
    ),
    SRK.SEPARATED_ALONG_AXIS: (
        TK.AXIS,
        "distinct reaction stations are positions on one shared axis",
    ),
}

# What mechanical fact fixes the location of a relation of each kind.
#
# This is the answer to "why is it here?". A revolute pair is on the axis the two
# members share because that is what a revolute pair is; a stop is at a travel
# extreme because that is what a limit does. None of it is a layout preference.
RELATION_BASIS: dict[SRK, tuple[LB, str]] = {
    SRK.SHARED_AXIS: (
        LB.COMMON_AXIS,
        "a revolute pair lies on the axis its two members share",
    ),
    SRK.COAXIAL_WORKING_OVERLAP: (
        LB.COAXIAL_OVERLAP,
        "a helical pair acts only where its two members overlap on their axis",
    ),
    SRK.COMMON_TRAVEL_DIRECTION: (
        LB.MOTION_CORRIDOR,
        "a guide acts along the whole corridor the constrained body travels",
    ),
    SRK.MATING_ADJACENCY: (
        LB.ENGAGED_STATE_CONTACT,
        "a contacting pair is located where its members meet when engaged",
    ),
    SRK.AXIS_SURROUNDED: (
        LB.REACTION_SITE,
        "a radial reaction is transferred where the support surrounds the axis",
    ),
    SRK.AXIAL_REACTION_STATION: (
        LB.REACTION_SITE,
        "an axial reaction is transferred at a station on the shared axis",
    ),
    SRK.CONTACT_AT_EXTREME: (
        LB.MOTION_EXTREME,
        "a limit is located at the extreme of travel it bounds",
    ),
    SRK.DISJOINT_SWEPT: (
        LB.MOTION_CORRIDOR,
        "what must stay clear is the corridor the moving element sweeps",
    ),
    SRK.EXTERIOR_REACHABLE: (
        LB.ACCESS_CROSSING,
        "reachability is located where the agent crosses the boundary",
    ),
    SRK.CONTINUOUS_ROUTE: (
        LB.MOTION_CORRIDOR,
        "a flexible member occupies the corridor it is routed along",
    ),
    SRK.SEPARATED_ALONG_AXIS: (
        LB.REACTION_SITE,
        "two reactions of one kind on one element act at distinct stations",
    ),
}

# Where a local element sits on its host, by the motion it permits. A joint on a
# *surface* is a line on that surface; a joint on a body is a line through it.
JOINT_ANCHOR: dict[MK, TK] = {
    MK.ROTATION: TK.AXIS,
    MK.TRANSLATION: TK.CORRIDOR,
    MK.ROTATION_TRANSLATION: TK.AXIS,
}
