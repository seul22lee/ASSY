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

from assy.domain.upstream import (
    ArchitecturalFunction as Fn,
    ArchitecturalInterface as If,
    Continuity,
    InterfaceKind as IK,
    ObligationKind as OK,
    QuantityKind as Q,
    SupportObligation as Ob,
)


@dataclass(frozen=True)
class RoleTemplate:
    name: str
    role: str          # MechanismRole value
    moving: bool
    roles: tuple[str, ...]   # engineering roles for downstream spawning


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

    @property
    def part_count(self) -> int:
        """Derived, never asserted: a hand-set count drifts from the role list."""
        return len(self.roles)

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


_HOUSING = RoleTemplate("housing", "structure", False, ("enclosure", "load_bearing", "manufactured"))
_INPUT = RoleTemplate("input_member", "input", True, ("rotating", "user_contact", "manufactured"))
_INPUT_SUPPORT = RoleTemplate("input_support", "support", False, ("load_bearing", "manufactured"))
_TRAVEL_STOP = RoleTemplate("travel_stop", "limit", False, ("load_bearing", "manufactured"))
_OPENING_INTERFACE = RoleTemplate(
    "opening_interface", "support", True, ("hinged", "load_bearing", "manufactured")
)
_OPENING_STOP = RoleTemplate("opening_stop", "limit", False, ("load_bearing", "manufactured"))

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
               RoleTemplate("transmission_shaft", "transmission", True, ("rotating", "load_bearing", "manufactured")),
               RoleTemplate("threaded_member", "conversion", True, ("rotating", "threaded_pair", "load_bearing", "manufactured")),
               RoleTemplate("thrust_support", "support", False, ("load_bearing", "manufactured")),
               RoleTemplate("travelling_member", "output", True, ("translating", "load_bearing", "manufactured")),
               RoleTemplate("guide_member", "guidance", False, ("load_bearing", "manufactured")),
               _TRAVEL_STOP, _HOUSING),
        element_chain=("input_member", "transmission_shaft", "threaded_member", "travelling_member"),
        functions=_drive_functions("threaded_member", "travelling_member"),
        state_relations=("travel is proportional to input revolutions",),
        holding_principle="friction within the threaded pair can hold position without input",
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
        ),
        load_path=("payload", "travelling_member", "threaded_member", "thrust_support", "housing"),
        interfaces=(
            If(between=("input_member", "transmission_shaft"), kind=IK.FIXED_ATTACHMENT,
               transmits="torque", crosses_boundary=True),
            If(between=("transmission_shaft", "threaded_member"), kind=IK.FIXED_ATTACHMENT,
               transmits="torque"),
            If(between=("threaded_member", "travelling_member"), kind=IK.THREADED_PAIR,
               transmits="axial force and torque"),
            If(between=("travelling_member", "guide_member"), kind=IK.SLIDING_JOINT,
               transmits="reaction moment and side load"),
            If(between=("threaded_member", "thrust_support"), kind=IK.ROTATIONAL_JOINT,
               transmits="axial thrust"),
            If(between=("input_member", "input_support"), kind=IK.ROTATIONAL_JOINT,
               transmits="radial load"),
            If(between=("travelling_member", "travel_stop"), kind=IK.CONTACT_PAIR,
               transmits="end-of-travel reaction"),
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
    ),
    MechanismFamily(
        id="toothed_linear_drive",
        principle="Toothed rotary member engaging a linear toothed member",
        input_kind=Q.ROTATION, output_kind=Q.TRANSLATION, continuity=Continuity.CONTINUOUS,
        reversible=True,
        roles=(_INPUT, _INPUT_SUPPORT,
               RoleTemplate("transmission_shaft", "transmission", True, ("rotating", "load_bearing", "manufactured")),
               RoleTemplate("rotary_toothed_member", "conversion", True, ("rotating", "gear_pair", "load_bearing", "manufactured")),
               RoleTemplate("linear_toothed_member", "conversion", True, ("translating", "gear_pair", "load_bearing", "manufactured")),
               RoleTemplate("travelling_member", "output", True, ("translating", "load_bearing", "manufactured")),
               RoleTemplate("guide_member", "guidance", False, ("load_bearing", "manufactured")),
               _TRAVEL_STOP, _HOUSING),
        element_chain=("input_member", "transmission_shaft", "rotary_toothed_member",
                       "linear_toothed_member", "travelling_member"),
        functions=_drive_functions("rotary_toothed_member", "travelling_member") + (
            Fn(function="maintain tooth engagement across the travel",
               performed_by=["rotary_toothed_member", "linear_toothed_member", "guide_member"]),
            Fn(function="provide a holding function", performed_by=[]),
        ),
        state_relations=("travel is proportional to input rotation through the toothed pitch",),
        holding_principle="none inherent; a separate holding function is required to keep position",
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
    ),
    MechanismFamily(
        id="flexible_tension_drive",
        principle="Winding a flexible tension member onto a rotating spool",
        input_kind=Q.ROTATION, output_kind=Q.TRANSLATION, continuity=Continuity.CONTINUOUS,
        reversible=True,
        roles=(_INPUT, _INPUT_SUPPORT,
               RoleTemplate("spool", "conversion", True, ("rotating", "load_bearing", "manufactured")),
               RoleTemplate("tension_member", "transmission", True, ("load_bearing",)),
               RoleTemplate("travelling_member", "output", True, ("translating", "load_bearing", "manufactured")),
               RoleTemplate("guide_member", "guidance", False, ("load_bearing", "manufactured")),
               _TRAVEL_STOP, _HOUSING),
        element_chain=("input_member", "spool", "tension_member", "travelling_member"),
        functions=_drive_functions("spool", "travelling_member") + (
            Fn(function="route and tension the flexible member",
               performed_by=["tension_member", "guide_member"]),
            Fn(function="provide a holding function", performed_by=[]),
        ),
        state_relations=("travel is proportional to wound length",),
        holding_principle="none inherent; tension is lost when input is released",
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
    ),
    # ---- rotation -> rotation, intermittent ------------------------------
    MechanismFamily(
        id="intermittent_indexing_pair",
        principle="Driver and driven pair producing discrete advance with dwell",
        input_kind=Q.ROTATION, output_kind=Q.ROTATION, continuity=Continuity.INTERMITTENT,
        reversible=False,
        roles=(_INPUT, _INPUT_SUPPORT,
               RoleTemplate("driver_member", "conversion", True, ("rotating", "intermittent_pair", "load_bearing", "manufactured")),
               RoleTemplate("indexed_member", "output", True, ("rotating", "intermittent_pair", "load_bearing", "manufactured")),
               _HOUSING),
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
            If(between=("driver_member", "indexed_member"), kind=IK.CONTACT_PAIR,
               transmits="advance force and locking reaction"),
            If(between=("input_member", "input_support"), kind=IK.ROTATIONAL_JOINT,
               transmits="radial load"),
            If(between=("indexed_member", "housing"), kind=IK.ROTATIONAL_JOINT,
               transmits="radial load"),
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
    ),
    MechanismFamily(
        id="pawl_advance_pair",
        principle="Reciprocating driver engaging a toothed wheel to advance one step",
        input_kind=Q.ROTATION, output_kind=Q.ROTATION, continuity=Continuity.INTERMITTENT,
        reversible=False,
        roles=(_INPUT, _INPUT_SUPPORT,
               RoleTemplate("driving_pawl", "conversion", True, ("compliant", "intermittent_pair", "load_bearing", "manufactured")),
               RoleTemplate("toothed_wheel", "output", True, ("rotating", "intermittent_pair", "load_bearing", "manufactured")),
               RoleTemplate("holding_pawl", "retention", True, ("compliant", "retention_interface", "manufactured")),
               _HOUSING),
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
    ),
    # ---- force -> held state (retention with intentional release) --------
    MechanismFamily(
        id="compliant_catch",
        principle="Elastic element deflecting over a feature and springing back to retain",
        input_kind=Q.FORCE, output_kind=Q.STATE, continuity=Continuity.HELD,
        reversible=True,
        roles=(RoleTemplate("closure_member", "output", True, ("moving_boundary", "user_contact", "manufactured")),
               _OPENING_INTERFACE,
               RoleTemplate("compliant_element", "retention", True, ("compliant", "retention_interface", "user_release", "precision_interface", "manufactured")),
               RoleTemplate("catch_feature", "retention", False, ("retention_interface", "load_bearing", "manufactured")),
               _OPENING_STOP, _HOUSING),
        element_chain=("user input", "compliant_element", "catch_feature", "closure_member"),
        functions=_catch_functions("compliant_element", "compliant_element"),
        state_relations=("closed state is held until a deliberate input deflects the element",
                         "the same element re-engages on closing"),
        holding_principle="elastic deflection and re-engagement; released by deflecting the element clear",
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
    ),
    MechanismFamily(
        id="over_centre_catch",
        principle="Linkage passing through an over-centre position to hold a closure",
        input_kind=Q.FORCE, output_kind=Q.STATE, continuity=Continuity.HELD,
        reversible=True,
        roles=(RoleTemplate("closure_member", "output", True, ("moving_boundary", "user_contact", "manufactured")),
               _OPENING_INTERFACE,
               RoleTemplate("actuating_lever", "release", True, ("rotating", "user_contact", "user_release", "manufactured")),
               RoleTemplate("tension_link", "retention", True, ("retention_interface", "load_bearing", "manufactured")),
               RoleTemplate("catch_feature", "retention", False, ("retention_interface", "load_bearing", "manufactured")),
               _OPENING_STOP, _HOUSING),
        element_chain=("user input", "actuating_lever", "tension_link", "catch_feature", "closure_member"),
        functions=_catch_functions("tension_link", "actuating_lever"),
        state_relations=("past the over-centre position the closure is held without further input",
                         "the state changes only when the lever is driven back"),
        holding_principle="geometric over-centre lock; released by reversing the lever",
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
    ),
    MechanismFamily(
        id="friction_detent_catch",
        principle="Interference between mating features held by friction or light preload",
        input_kind=Q.FORCE, output_kind=Q.STATE, continuity=Continuity.HELD,
        reversible=True,
        roles=(RoleTemplate("closure_member", "output", True, ("moving_boundary", "user_contact", "user_release", "manufactured")),
               _OPENING_INTERFACE,
               RoleTemplate("detent_feature", "retention", False, ("retention_interface", "manufactured")),
               _OPENING_STOP, _HOUSING),
        element_chain=("user input", "detent_feature", "closure_member"),
        functions=_catch_functions("detent_feature", "closure_member"),
        state_relations=("the closed state is held by interference until a deliberate pull exceeds it",),
        holding_principle="frictional or interference preload; released by exceeding it",
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
    ),
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
