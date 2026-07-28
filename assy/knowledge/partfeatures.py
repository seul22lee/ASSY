"""What a part must actually have on it to perform the interfaces it is in.

Stage 04 hands over bodies: a shaft, a shell, a plate, jointed and posed. Those
are not parts. A shaft that turns in a housing is not a cylinder next to a box -
it is a journal with a locating shoulder, running in a bore with a bearing seat,
in a boss thick enough to carry the reaction. None of that is dimensioning; it is
knowing what a rotational interface *is made of*, and it has to exist before any
solver can be asked for a number, because the numbers are dimensions **of** these
features.

The rules are keyed on typed interface and obligation kinds, never on part names,
so a family that declares a `ROTATIONAL_JOINT` gets journals and bearing seats
whatever the mechanism is called. Each feature records the interface or obligation
it came from, so a part's topology is traceable rather than asserted: nothing here
may appear on a part that has no declared reason to carry it.

What this module deliberately does not do is decide sizes, fits, or fastener
counts. A `BEARING_SEAT` is committed here; whether it takes a bush or a ball race,
and how big, is a resolution and a dimension respectively.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from assy.domain.upstream import InterfaceKind as IK
from assy.domain.upstream import ObligationKind as OK


class FeatureKind(str, Enum):
    """A named region of a part that exists for a stated engineering reason."""

    # rotation
    JOURNAL = "journal"
    """The running surface of a shaft where it is radially supported."""
    BORE = "bore"
    """The mating hole a journal runs in."""
    BEARING_SEAT = "bearing_seat"
    """The located pocket a bearing element sits in."""
    SHOULDER = "shoulder"
    """A step that locates something axially and reacts thrust."""
    THRUST_FACE = "thrust_face"

    # translation
    SLIDE_FACE = "slide_face"
    RAIL_FACE = "rail_face"
    STOP_FACE = "stop_face"
    ANTI_ROTATION_FLAT = "anti_rotation_flat"

    # transmission
    THREAD = "thread"
    TOOTH_FORM = "tooth_form"
    CONTACT_FACE = "contact_face"
    ANCHOR = "anchor"

    # attachment and structure
    MOUNT_PAD = "mount_pad"
    """A flat, reachable face two pieces are fastened at."""
    FASTENER_FEATURE = "fastener_feature"
    BOSS = "boss"
    """Locally thickened material where a reaction enters a thin wall."""
    RIB = "rib"
    ROOT_FILLET = "root_fillet"
    """Where a cantilevered element meets its root; the stress concentration."""

    # enclosure
    CAVITY = "cavity"
    WALL = "wall"
    FOOT = "foot"
    OPENING = "opening"
    CLEARANCE_RECESS = "clearance_recess"
    THROUGH_BORE = "through_bore"
    """A bore through the enclosure boundary, where something drives in or out."""

    # assembly
    LEAD_IN = "lead_in"
    RETENTION = "retention"
    GRIP = "grip"


class FeatureEffect(str, Enum):
    """What a feature does to the material of the part that carries it.

    A part topology is not a list of separate solids. A bore is material taken
    *out* of its part and a boss is material added *to* it; a journal is neither,
    it is a named region of a surface that already exists. Building every feature
    as its own body produces a pile of primitives where the assembly should be,
    and loses the only thing the topology was for.
    """

    ADD = "add"
    """Material added: a boss, a rib, a foot."""
    CUT = "cut"
    """Material removed: a bore, an opening, a recess."""
    FACE = "face"
    """No material change - a designated region of an existing surface."""


#: What each feature does. Faces dominate: most of what an interface needs is a
#: surface with a requirement on it, not extra material.
FEATURE_EFFECT: dict["FeatureKind", FeatureEffect] = {}


@dataclass(frozen=True)
class FeatureRule:
    """Features an interface requires, on each of the two elements it joins.

    `driven` is the element that moves or is transmitted to; `host` is the one
    that supports or reacts. Which is which comes from the element's motion, not
    from the order the family happened to write the pair in.
    """

    driven: tuple[FeatureKind, ...]
    host: tuple[FeatureKind, ...]
    why: str


#: What each kind of interface is physically made of.
INTERFACE_FEATURES: dict[IK, FeatureRule] = {
    IK.ROTATIONAL_JOINT: FeatureRule(
        driven=(FeatureKind.JOURNAL, FeatureKind.SHOULDER),
        host=(FeatureKind.BORE, FeatureKind.BEARING_SEAT, FeatureKind.BOSS),
        why="a turning element needs a running surface and an axial location; "
            "its support needs a located bore and material to react into",
    ),
    IK.SLIDING_JOINT: FeatureRule(
        driven=(FeatureKind.SLIDE_FACE,),
        host=(FeatureKind.RAIL_FACE, FeatureKind.BOSS),
        why="a guided element and its guide meet on mating faces, and the guide "
            "reaction has to enter the structure somewhere",
    ),
    IK.THREADED_PAIR: FeatureRule(
        driven=(FeatureKind.THREAD,),
        host=(FeatureKind.THREAD,),
        why="both halves of a screw pair carry the same helix",
    ),
    IK.TOOTHED_MESH: FeatureRule(
        driven=(FeatureKind.TOOTH_FORM,),
        host=(FeatureKind.TOOTH_FORM,),
        why="a mesh is two tooth forms on a common pitch",
    ),
    IK.CONTACT_PAIR: FeatureRule(
        driven=(FeatureKind.CONTACT_FACE,),
        host=(FeatureKind.CONTACT_FACE,),
        why="contact happens on real faces, which must exist on both sides",
    ),
    IK.FIXED_ATTACHMENT: FeatureRule(
        driven=(FeatureKind.MOUNT_PAD, FeatureKind.FASTENER_FEATURE),
        host=(FeatureKind.MOUNT_PAD, FeatureKind.FASTENER_FEATURE, FeatureKind.BOSS),
        why="two pieces joined rigidly meet on a prepared face and are held there",
    ),
    IK.FLEXIBLE_LINK: FeatureRule(
        driven=(FeatureKind.ANCHOR,),
        host=(FeatureKind.ANCHOR,),
        why="a flexible member has to be terminated at both ends",
    ),
    IK.USER_CONTACT: FeatureRule(
        driven=(FeatureKind.GRIP,),
        host=(),
        why="a surface a person operates is a designed surface",
    ),
}

#: What an obligation requires on the element that reacts it. An obligation is a
#: statement that something must be provided; this is what providing it looks like.
OBLIGATION_FEATURES: dict[OK, tuple[tuple[FeatureKind, ...], str]] = {
    OK.RADIAL_SUPPORT: (
        (FeatureKind.BORE, FeatureKind.BOSS),
        "radial reaction needs a located bore and material around it",
    ),
    OK.AXIAL_THRUST: (
        (FeatureKind.THRUST_FACE, FeatureKind.SHOULDER),
        "axial load needs a face square to the axis to push against",
    ),
    OK.ANTI_ROTATION: (
        (FeatureKind.ANTI_ROTATION_FLAT,),
        "a moment is reacted by a non-circular engagement, not by friction",
    ),
    OK.GUIDANCE: (
        (FeatureKind.RAIL_FACE,),
        "guidance is a bearing surface along the travel",
    ),
    OK.STRUCTURAL_ROOT: (
        (FeatureKind.ROOT_FILLET, FeatureKind.BOSS),
        "a rooted element concentrates stress where it meets its root",
    ),
    OK.ALIGNMENT: (
        (FeatureKind.LEAD_IN,),
        "parts that must align on assembly need a feature that aligns them",
    ),
    OK.TRAVEL_LIMIT: (
        (FeatureKind.STOP_FACE,),
        "an end of travel is a face that is actually struck",
    ),
    OK.USER_ACCESS: (
        (FeatureKind.OPENING,),
        "access through an enclosure is an opening in it",
    ),
    OK.CLEARANCE: (
        (FeatureKind.CLEARANCE_RECESS,),
        "space reserved for something to move through is a recess in what surrounds it",
    ),
}

#: Features implied by what a piece *is*, independent of what it connects to.
FORM_FEATURES: dict[str, tuple[tuple[FeatureKind, ...], str]] = {
    "shell": (
        (FeatureKind.CAVITY, FeatureKind.WALL, FeatureKind.FOOT),
        "an enclosure is a wall around a cavity, and it has to stand on something",
    ),
}

#: An interface that crosses the enclosure boundary needs a way through it.
BOUNDARY_FEATURE = (
    FeatureKind.THROUGH_BORE,
    "something that drives through a wall needs a passage and a place to seal or run",
)


def features_for_interface(kind: IK) -> FeatureRule | None:
    return INTERFACE_FEATURES.get(kind)


def features_for_obligation(kind: OK) -> tuple[tuple[FeatureKind, ...], str]:
    return OBLIGATION_FEATURES.get(kind, ((), ""))


def features_for_form(form: str) -> tuple[tuple[FeatureKind, ...], str]:
    return FORM_FEATURES.get(form, ((), ""))


FEATURE_EFFECT.update({
    # removed material
    FeatureKind.BORE: FeatureEffect.CUT,
    FeatureKind.THROUGH_BORE: FeatureEffect.CUT,
    FeatureKind.CAVITY: FeatureEffect.CUT,
    FeatureKind.OPENING: FeatureEffect.CUT,
    FeatureKind.CLEARANCE_RECESS: FeatureEffect.CUT,
    FeatureKind.BEARING_SEAT: FeatureEffect.CUT,
    FeatureKind.RETENTION: FeatureEffect.CUT,
    FeatureKind.LEAD_IN: FeatureEffect.CUT,
    FeatureKind.ANTI_ROTATION_FLAT: FeatureEffect.CUT,
    # added material
    FeatureKind.BOSS: FeatureEffect.ADD,
    FeatureKind.RIB: FeatureEffect.ADD,
    FeatureKind.FOOT: FeatureEffect.ADD,
    FeatureKind.SHOULDER: FeatureEffect.ADD,
    FeatureKind.ANCHOR: FeatureEffect.ADD,
    FeatureKind.GRIP: FeatureEffect.ADD,
    FeatureKind.STOP_FACE: FeatureEffect.ADD,
    FeatureKind.FASTENER_FEATURE: FeatureEffect.CUT,
    FeatureKind.ROOT_FILLET: FeatureEffect.ADD,
    FeatureKind.WALL: FeatureEffect.ADD,
})


def effect_of(kind: "FeatureKind") -> FeatureEffect:
    """A feature with no declared effect designates a surface, it does not add to it."""
    return FEATURE_EFFECT.get(kind, FeatureEffect.FACE)
