"""Mechanism family catalogue, keyed on transformation signature.

Families are indexed by what they transform — ``(input_kind, output_kind,
continuity)`` — taken from a Stage 01 `BehaviourSpec`. **No family is selected by
matching words.** A benchmark name, a product noun, or a term the user happened to
use can never reach this lookup.

Each entry carries the conceptual content Stage 03 and later need: the functional
chain, what must be supported, where load goes, what interfaces exist, and what
the arrangement implies spatially. It carries no dimensions, no placements, and no
tolerances — those are later stages' work.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from assy.domain.upstream import Continuity, QuantityKind as Q


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
    functional_chain: tuple[str, ...]
    state_relations: tuple[str, ...] = ()
    holding_principle: str | None = None
    support_obligations: tuple[str, ...] = ()
    load_path: tuple[str, ...] = ()
    interfaces: tuple[str, ...] = ()
    spatial_implications: tuple[str, ...] = ()
    motion_envelopes: tuple[str, ...] = ()
    strengths: tuple[str, ...] = ()
    weaknesses: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    tradeoffs: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    downstream_decisions: tuple[str, ...] = ()
    part_count: int = 4

    @property
    def signature(self) -> tuple[Q, Q, Continuity]:
        return (self.input_kind, self.output_kind, self.continuity)


_HOUSING = RoleTemplate("housing", "structure", False, ("enclosure", "load_bearing", "manufactured"))
_INPUT = RoleTemplate("input_member", "input", True, ("rotating", "user_contact", "manufactured"))

FAMILIES: tuple[MechanismFamily, ...] = (
    # ---- rotation -> translation, continuous ----------------------------
    MechanismFamily(
        id="screw_drive",
        principle="Threaded pair converting continuous rotation to translation",
        input_kind=Q.ROTATION, output_kind=Q.TRANSLATION, continuity=Continuity.CONTINUOUS,
        reversible=True, part_count=6,
        roles=(_INPUT,
               RoleTemplate("transmission_shaft", "transmission", True, ("rotating", "load_bearing", "manufactured")),
               RoleTemplate("threaded_member", "conversion", True, ("rotating", "threaded_pair", "load_bearing", "manufactured")),
               RoleTemplate("travelling_member", "output", True, ("translating", "load_bearing", "manufactured")),
               RoleTemplate("guide_member", "guidance", False, ("load_bearing", "manufactured")),
               _HOUSING),
        functional_chain=("input_member", "transmission_shaft", "threaded_member", "travelling_member"),
        state_relations=("travel is proportional to input revolutions",),
        holding_principle="friction within the threaded pair can hold position without input",
        support_obligations=("the rotating threaded member must be located and axially retained",
                             "the travelling member must be guided against rotation"),
        load_path=("payload", "travelling_member", "threaded_member", "housing"),
        interfaces=("input member to transmission", "threaded pair", "travelling member to guide"),
        spatial_implications=("the threaded member spans the full travel and sets product height",
                              "the guide runs parallel to travel",
                              "the input member crosses the enclosure boundary"),
        motion_envelopes=("travelling member sweeps a prism along the travel axis",
                          "input member sweeps a disc outside the enclosure"),
        strengths=("high mechanical advantage", "compact along the travel axis", "may hold without input"),
        weaknesses=("low efficiency", "slow travel per input revolution"),
        risks=("thread wear over repeated cycles", "travelling member tilts if guidance is weak"),
        tradeoffs=("holding capability against input effort and speed",),
        assumptions=("continuous rotary input is available at the boundary",),
        downstream_decisions=("thread lead", "guide count and spacing", "member proportions"),
    ),
    MechanismFamily(
        id="toothed_linear_drive",
        principle="Toothed rotary member engaging a linear toothed member",
        input_kind=Q.ROTATION, output_kind=Q.TRANSLATION, continuity=Continuity.CONTINUOUS,
        reversible=True, part_count=7,
        roles=(_INPUT,
               RoleTemplate("transmission_shaft", "transmission", True, ("rotating", "load_bearing", "manufactured")),
               RoleTemplate("rotary_toothed_member", "conversion", True, ("rotating", "gear_pair", "load_bearing", "manufactured")),
               RoleTemplate("linear_toothed_member", "conversion", True, ("translating", "gear_pair", "load_bearing", "manufactured")),
               RoleTemplate("travelling_member", "output", True, ("translating", "load_bearing", "manufactured")),
               RoleTemplate("guide_member", "guidance", False, ("load_bearing", "manufactured")),
               _HOUSING),
        functional_chain=("input_member", "transmission_shaft", "rotary_toothed_member",
                          "linear_toothed_member", "travelling_member"),
        state_relations=("travel is proportional to input rotation through the toothed pitch",),
        holding_principle="none inherent; a separate holding function is required to keep position",
        support_obligations=("the rotary member must be located on a fixed axis",
                             "the linear member must be guided along its travel",
                             "engagement must be maintained across the travel"),
        load_path=("payload", "travelling_member", "linear_toothed_member", "rotary_toothed_member", "housing"),
        interfaces=("toothed engagement", "rotary member to shaft", "linear member to travelling member"),
        spatial_implications=("the linear member spans the full travel plus engagement run-out",
                              "the rotary member sits beside the travel axis, widening the product"),
        motion_envelopes=("linear member sweeps its own length plus travel",
                          "rotary member sweeps a disc at the engagement plane"),
        strengths=("high efficiency", "fast travel per input revolution"),
        weaknesses=("does not hold position unaided", "engagement must be maintained"),
        risks=("output moves under load when input is released",),
        tradeoffs=("speed and efficiency against the need for a separate holding function",),
        assumptions=("continuous rotary input is available at the boundary",),
        downstream_decisions=("tooth proportions", "engagement geometry", "guide arrangement"),
    ),
    MechanismFamily(
        id="flexible_tension_drive",
        principle="Winding a flexible tension member onto a rotating spool",
        input_kind=Q.ROTATION, output_kind=Q.TRANSLATION, continuity=Continuity.CONTINUOUS,
        reversible=True, part_count=6,
        roles=(_INPUT,
               RoleTemplate("spool", "conversion", True, ("rotating", "load_bearing", "manufactured")),
               RoleTemplate("tension_member", "transmission", True, ("load_bearing",)),
               RoleTemplate("travelling_member", "output", True, ("translating", "load_bearing", "manufactured")),
               RoleTemplate("guide_member", "guidance", False, ("load_bearing", "manufactured")),
               _HOUSING),
        functional_chain=("input_member", "spool", "tension_member", "travelling_member"),
        state_relations=("travel is proportional to wound length",),
        holding_principle="none inherent; tension is lost when input is released",
        support_obligations=("the spool must be located on a fixed axis",
                             "the tension member must be routed and kept in tension"),
        load_path=("payload", "travelling_member", "tension_member", "spool", "housing"),
        interfaces=("spool to tension member", "tension member to travelling member"),
        spatial_implications=("the tension member needs a routing path of at least the travel length",
                              "the spool width grows with wound length"),
        motion_envelopes=("travelling member sweeps along the travel axis",
                          "the tension path sweeps a plane during winding"),
        strengths=("very low friction", "tolerant of misalignment"),
        weaknesses=("carries tension only", "requires a separate holding function"),
        risks=("uncontrolled descent if holding fails", "spooling irregularity"),
        tradeoffs=("low friction against the need for holding and routing discipline",),
        assumptions=("the load acts along one direction so tension is sufficient",),
        downstream_decisions=("spool proportions", "routing path", "holding function"),
    ),
    # ---- rotation -> rotation, intermittent ------------------------------
    MechanismFamily(
        id="intermittent_indexing_pair",
        principle="Driver and driven pair producing discrete advance with dwell",
        input_kind=Q.ROTATION, output_kind=Q.ROTATION, continuity=Continuity.INTERMITTENT,
        reversible=False, part_count=4,
        roles=(_INPUT,
               RoleTemplate("driver_member", "conversion", True, ("rotating", "intermittent_pair", "load_bearing", "manufactured")),
               RoleTemplate("indexed_member", "output", True, ("rotating", "intermittent_pair", "load_bearing", "manufactured")),
               _HOUSING),
        functional_chain=("input_member", "driver_member", "indexed_member"),
        state_relations=("one input revolution advances the output by one station",
                         "the output is stationary for the remainder of the input cycle"),
        holding_principle="the driver geometry locks the output during dwell",
        support_obligations=("both rotating members must be located on fixed parallel axes",
                             "the axis separation fixes the engagement and must be held"),
        load_path=("indexed load", "indexed_member", "driver_member", "housing"),
        interfaces=("driver to indexed engagement", "locking surfaces active during dwell"),
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
        reversible=False, part_count=5,
        roles=(_INPUT,
               RoleTemplate("driving_pawl", "conversion", True, ("compliant", "intermittent_pair", "load_bearing", "manufactured")),
               RoleTemplate("toothed_wheel", "output", True, ("rotating", "intermittent_pair", "load_bearing", "manufactured")),
               RoleTemplate("holding_pawl", "retention", True, ("compliant", "retention_interface", "manufactured")),
               _HOUSING),
        functional_chain=("input_member", "driving_pawl", "toothed_wheel"),
        state_relations=("each input stroke advances the wheel by one tooth",
                         "a holding element prevents reverse motion between strokes"),
        holding_principle="a separate holding element blocks reverse rotation during dwell",
        support_obligations=("the wheel must be located on a fixed axis",
                             "both engaging elements need a defined rest position"),
        load_path=("indexed load", "toothed_wheel", "holding_pawl", "housing"),
        interfaces=("driving engagement", "holding engagement"),
        spatial_implications=("engaging elements sit tangentially around the wheel, "
                              "so the wheel diameter dominates the internal volume"),
        motion_envelopes=("wheel sweeps a full disc",
                          "engaging elements sweep small arcs at its periphery"),
        strengths=("station count set by tooth count", "simple one-way behaviour"),
        weaknesses=("compliant elements are strain-limited", "position accuracy depends on holding"),
        risks=("reverse motion if the holding element disengages",),
        tradeoffs=("advance force against holding security",),
        assumptions=("one-way advance is acceptable",),
        downstream_decisions=("tooth count", "engagement angles", "compliant element proportions"),
    ),
    # ---- force -> held state (retention with intentional release) --------
    MechanismFamily(
        id="compliant_catch",
        principle="Elastic element deflecting over a feature and springing back to retain",
        input_kind=Q.FORCE, output_kind=Q.STATE, continuity=Continuity.HELD,
        reversible=True, part_count=4,
        roles=(RoleTemplate("closure_member", "output", True, ("moving_boundary", "user_contact", "manufactured")),
               RoleTemplate("compliant_element", "retention", True, ("compliant", "retention_interface", "user_release", "precision_interface", "manufactured")),
               RoleTemplate("catch_feature", "retention", False, ("retention_interface", "load_bearing", "manufactured")),
               _HOUSING),
        functional_chain=("user input", "compliant_element", "catch_feature", "closure_member"),
        state_relations=("closed state is held until a deliberate input deflects the element",
                         "the same element re-engages on closing"),
        holding_principle="elastic deflection and re-engagement; released by deflecting the element clear",
        support_obligations=("the compliant element needs a fixed root",
                             "the catch feature must resist the retaining force"),
        load_path=("disturbance", "closure_member", "catch_feature", "compliant_element", "housing"),
        interfaces=("compliant element to catch feature", "user actuation surface"),
        spatial_implications=("the actuation surface must be reachable from outside",
                              "the retaining pair sits at the closure boundary",
                              "deflection space must stay clear behind the element"),
        motion_envelopes=("the compliant element sweeps its deflection during engagement and release",
                          "the closure member sweeps its opening path"),
        strengths=("no separate fastener required", "tool-free repeated operation"),
        weaknesses=("strain-limited", "may relax over many cycles"),
        risks=("permanent deformation if over-deflected", "retention weakening with cycling"),
        tradeoffs=("retention security against ease of intentional release",),
        assumptions=("the retaining element may be integral to a moulded or printed part",),
        downstream_decisions=("element proportions", "engagement angles", "actuation surface form"),
    ),
    MechanismFamily(
        id="over_centre_catch",
        principle="Linkage passing through an over-centre position to hold a closure",
        input_kind=Q.FORCE, output_kind=Q.STATE, continuity=Continuity.HELD,
        reversible=True, part_count=5,
        roles=(RoleTemplate("closure_member", "output", True, ("moving_boundary", "user_contact", "manufactured")),
               RoleTemplate("actuating_lever", "input", True, ("rotating", "user_contact", "manufactured")),
               RoleTemplate("tension_link", "retention", True, ("retention_interface", "load_bearing", "manufactured")),
               RoleTemplate("catch_feature", "retention", False, ("retention_interface", "load_bearing", "manufactured")),
               _HOUSING),
        functional_chain=("user input", "actuating_lever", "tension_link", "catch_feature", "closure_member"),
        state_relations=("past the over-centre position the closure is held without further input",
                         "the state changes only when the lever is driven back"),
        holding_principle="geometric over-centre lock; released by reversing the lever",
        support_obligations=("the lever needs a located pivot",
                             "the link needs defined attachment at both ends"),
        load_path=("disturbance", "closure_member", "catch_feature", "tension_link", "housing"),
        interfaces=("lever pivot", "link attachments", "catch engagement"),
        spatial_implications=("the lever swings outside the closure boundary and needs external clearance",
                              "the linkage occupies a plane across the closure line"),
        motion_envelopes=("the lever sweeps an arc outside the product",
                          "the link sweeps a plane through the over-centre position"),
        strengths=("high and adjustable retaining force", "unambiguous open and closed states"),
        weaknesses=("more parts", "protrudes beyond the closure boundary"),
        risks=("snagging on the protruding lever", "over-centre position lost if geometry shifts"),
        tradeoffs=("retention force against part count and protrusion",),
        assumptions=("external clearance is available for the lever swing",),
        downstream_decisions=("lever proportions", "link geometry", "over-centre offset"),
    ),
    MechanismFamily(
        id="friction_detent_catch",
        principle="Interference between mating features held by friction or light preload",
        input_kind=Q.FORCE, output_kind=Q.STATE, continuity=Continuity.HELD,
        reversible=True, part_count=3,
        roles=(RoleTemplate("closure_member", "output", True, ("moving_boundary", "user_contact", "manufactured")),
               RoleTemplate("detent_feature", "retention", False, ("retention_interface", "manufactured")),
               _HOUSING),
        functional_chain=("user input", "detent_feature", "closure_member"),
        state_relations=("the closed state is held by interference until a deliberate pull exceeds it",),
        holding_principle="frictional or interference preload; released by exceeding it",
        support_obligations=("the mating features must stay aligned across repeated cycles",),
        load_path=("disturbance", "closure_member", "detent_feature", "housing"),
        interfaces=("mating interference pair",),
        spatial_implications=("no protrusion beyond the closure boundary",
                              "the interference pair sits on the closure line itself"),
        motion_envelopes=("the closure member sweeps its opening path; no separate element moves",),
        strengths=("fewest parts", "nothing protrudes"),
        weaknesses=("retention force is least predictable", "wears with cycling"),
        risks=("retention decaying with repeated use", "accidental opening if preload is low"),
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
