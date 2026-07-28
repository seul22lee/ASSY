"""Stage 04 - kinematic concept model.

Rebuilt. The previous model ordered bodies along one axis in ordinal slots, which
could not express a second axis, a lateral pair, a face's edges, a cavity, or a
rotation. This one carries **solids with symbolic dimensions, frames, and real
transforms**, and proves state transitions by composing them.

    solids -> frames -> kinematic tree -> pose per state
           -> swept regions -> predicates -> parameter constraints

Dimensions are never resolved here. A predicate whose truth depends on a dimension
is not answered; it is **emitted as the inequality that dimension must satisfy**,
for Stage 06 to solve. That is what lets Stage 04 prove spatial feasibility without
doing geometry: it decides the topology and hands down the algebra.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from assy.domain.upstream import (
    AxisRelation,
    ElementClass,
    JointType,
    MotionKind,
    StateRole,
)
from assy.geometry import (
    AXES,
    EstimateBasis,
    FormClass,
    Frame,
    Rot,
    Solid,
    Vec3,
    aabb,
    overlaps,
    world_corners,
)

# Nominal proportions used to instantiate a solid. Drawing and indicative
# evaluation only: every one is a Sym whose value Stage 06 resolves.
NOMINAL: dict[FormClass, dict[str, float]] = {
    FormClass.SHELL: {"length": 2.0, "width": 1.6, "height": 2.4, "wall": 0.12},
    FormClass.PLATE: {"length": 1.9, "width": 1.5, "thickness": 0.10},
    FormClass.SHAFT: {"length": 1.9, "diameter": 0.16},
    FormClass.RAIL: {"length": 1.9, "section": 0.12},
    FormClass.COLLAR: {"length": 0.20, "bore": 0.22},
    FormClass.BLOCK: {"length": 0.26, "width": 0.22, "height": 0.14},
    FormClass.LINK: {"length": 0.7, "section": 0.10},
    FormClass.FLEXIBLE: {"length": 1.6, "section": 0.06},
}

# Full travel of a joint coordinate, as a nominal for drawing. The *range* is a
# symbol Stage 06 resolves; only its display value lives here.
FULL_SWING = math.radians(105.0)


@dataclass
class Body:
    name: str
    solid: Solid
    element_class: ElementClass
    motion: MotionKind
    roles: list[str] = field(default_factory=list)
    parent: str | None = None
    joint: str | None = None


@dataclass
class Joint:
    name: str
    type: JointType
    parent: str
    child: str
    axis: str                    # product axis the coordinate acts about/along
    frame_on_parent: Frame       # where it sits on the parent
    why: str = ""


@dataclass
class ParameterConstraint:
    """An inequality the dimensions must satisfy for a predicate to hold."""

    predicate: str
    subject: str
    relation: str
    symbols: list[str]
    why: str
    indicative: bool = True
    """True when the nominal values satisfy it; never a proof, only a hint."""


@dataclass
class KinematicModel:
    bodies: dict[str, Body]
    joints: dict[str, Joint]
    poses: dict[tuple[str, str], Frame]      # (state, body) -> world frame
    coordinates: dict[tuple[str, str], float]  # (state, joint) -> q at nominal
    constraints: list[ParameterConstraint]
    contradictions: list[str]
    unplaced: list[str]
    free_choices: dict[str, str] = field(default_factory=dict)
    feature_hosts: dict[str, str] = field(default_factory=dict)
    feature_seats: dict[str, float] = field(default_factory=dict)
    radial_features: set = field(default_factory=set)
    chain: tuple = ()
    axes: dict = field(default_factory=dict)
    """Each body's derived motion axis. Published because Stage 04 owns spatial
    derivation: a later stage re-deriving it from the joint list gets a different
    answer for anything positioned through a rigid attachment, and then the two
    stages disagree about the same mechanism."""


AXIS_NAMES = ("x", "y", "z")


def _perpendicular(*axes: str) -> str:
    """An axis perpendicular to all the ones given. Deterministic, not chosen."""
    used = {a for a in axes if a}
    for a in AXIS_NAMES:
        if a not in used:
            return a
    return "z"


class KinematicBuilder:
    """Builds the concept-level kinematic model for one selected architecture."""

    def __init__(self, product, mechanical):
        self.product = product
        self.selected = mechanical.selected
        self.pieces = {p.name: p for p in product.pieces}
        self.states = list(self.selected.states)
        self.transitions = list(self.selected.transitions)
        self._body_cache: dict = {}
        self.free_axes: dict[str, str] = {}
        self.constraints: list[ParameterConstraint] = []
        self.contradictions: list[str] = []

    # -- solids --------------------------------------------------------------
    def _form_of(self, piece) -> FormClass:
        raw = getattr(piece, "form", None)
        if raw is not None:
            return FormClass(raw) if not isinstance(raw, FormClass) else raw
        return FormClass.BLOCK

    def _travel(self) -> tuple[float, str] | None:
        """Travel taken from a stated length bound, if one reaches this stage.

        This is the difference between a proportion that is *derived* and one that
        is guessed: an 80-100 mm travel sizes the corridor, the screw that spans
        it and the chamber that contains it.
        """
        for b in self.selected.bounds:
            if b.unit in ("mm", "cm", "m") and b.lower is not None:
                mid = (b.lower + (b.upper if b.upper is not None else b.lower)) / 2
                scale = {"mm": 0.001, "cm": 0.01, "m": 1.0}[b.unit]
                return mid * scale, f"{b.requirement_id} {b.comparator} " \
                                    f"{b.lower}-{b.upper} {b.unit}"
        return None

    def _sizing(self, name: str, form: FormClass, piece):
        """Nominal proportions and the basis for each, per body."""
        nominal = dict(NOMINAL[form])
        basis: dict[str, tuple[EstimateBasis, str]] = {}
        travel = self._travel()
        if travel is None:
            return nominal, basis
        metres, source = travel
        # One display unit is one decimetre, so a 90 mm travel is 0.9 units.
        t = metres * 10.0
        moving_out = piece.motion_kind is MotionKind.TRANSLATION
        if form is FormClass.SHELL:
            nominal["height"] = t * 2.1
            basis["height"] = (EstimateBasis.FROM_REQUIREMENT,
                               f"must contain the travel: {source}")
        elif form is FormClass.SHAFT and not moving_out:
            nominal["length"] = t * 1.5
            basis["length"] = (EstimateBasis.PROPORTION_OF,
                               f"spans the travel plus its supports: {source}")
        elif form is FormClass.RAIL:
            nominal["length"] = t * 1.7
            basis["length"] = (EstimateBasis.PROPORTION_OF,
                               f"guides the whole travel: {source}")
        return nominal, basis

    def _bodies(self) -> dict[str, Body]:
        out: dict[str, Body] = {}
        self._body_cache = out
        self._axes: dict[str, str] = getattr(self, '_axes', {})
        for name, piece in sorted(self.pieces.items()):
            form = self._form_of(piece)
            nominal, basis = self._sizing(name, form, piece)
            out[name] = Body(
                name=name,
                solid=Solid.of(name, form, nominal, basis),
                element_class=piece.element_class,
                motion=piece.motion_kind,
                roles=list(piece.engineering_roles or []),
            )
        return out

    # -- kinematic tree ------------------------------------------------------
    def _layout_axis(self, bodies) -> str:
        """The axis the transmission chain lays out along.

        It is the axis of the *output's* motion: a lift stacks along its travel, a
        horizontal slide lays out along its slide. Assuming z would make every
        product a tower.
        """
        chain = [n for n in self.selected.element_chain if n in bodies]
        for name in reversed(chain):
            if bodies[name].motion is MotionKind.TRANSLATION:
                self.free_axes.setdefault(
                    "organising_axis",
                    f"{name} travels along an axis the mechanism does not fix; "
                    f"{self.ORGANISING_AXIS} is taken as the default and any axis "
                    "is equally valid until an orientation is stated",
                )
                return self.ORGANISING_AXIS
        return self.ORGANISING_AXIS

    def _motion_axis(self, bodies, name: str) -> str:
        """Which axis a body's own motion acts on, from the joint that permits it."""
        for jn, piece in self.pieces.items():
            if piece.element_class is not ElementClass.JOINT:
                continue
            if piece.permits_motion is not bodies[name].motion:
                continue
            partners = {
                o for i in self.product.interfaces if jn in i.between
                for o in i.between
            }
            if name in partners:
                return self._aperture_normal(bodies)
        return "z"

    # The direction the product is organised along is a **free parameter**.
    # Nothing in the mechanism fixes it: a lift could travel along any axis, and
    # what would settle it - gravity, a mounting face, a stated orientation - is
    # not represented. A default is taken so the model is drawable, and the
    # freedom is recorded rather than disguised as a derivation. Choosing it from
    # shell proportions was a guess dressed as a rule, and it silently reoriented
    # a product whose housing happened to be wider than it was tall.
    ORGANISING_AXIS = "z"

    def _aperture_normal(self, bodies) -> str:
        """The axis a closure opens along: the organising axis of the product."""
        return self.ORGANISING_AXIS

    def _ground(self, bodies) -> str | None:
        shell = [n for n, b in bodies.items() if "enclosure" in b.roles]
        return shell[0] if shell else next(iter(sorted(bodies)), None)

    def _axis_map(self, bodies) -> dict[str, str]:
        """Every body's motion axis, derived by propagating interface constraints.

        Deciding each element's axis from its own local situation and then
        declaring elements coupled produces mechanisms that cannot move: a pin and
        the slot it drives were being given perpendicular axes, and nothing
        noticed, because no step ever compared them.

        An interface that transmits motion constrains the two axes it joins, so
        the axes are not independent and cannot be derived independently. Bodies
        joined by an identical, parallel or collinear relation share a direction;
        a redirect element exists precisely to intersect, so it flips. Solving to
        a fixpoint over the interface graph is what makes the drive train
        consistent by construction rather than by luck.

        Only two things are seeded, and both are genuine local derivations: a
        translating body moves along the layout axis, and something driven in
        through the enclosure wall enters across it. Everything else follows from
        what it is connected to, which is the point.
        """
        layout = self._layout_axis(bodies)
        DRIVE = ("fixed_attachment", "rotational_joint", "toothed_mesh",
                 "threaded_pair", "sliding_joint", "contact_pair")
        # Ground has no motion axis. Propagating one into the structure and then
        # requiring everything bolted to it to share that axis is meaningless -
        # a housing is not turning about anything.
        def _ground(n: str, b) -> bool:
            piece = self.pieces.get(n)
            return (
                b.element_class is ElementClass.BODY
                and b.motion is MotionKind.FIXED
                and (piece is None or piece.permits_motion is MotionKind.FIXED)
            )

        # Everything except structural ground. A feature carries no motion of its
        # own but rides a host that does, so excluding features breaks the chain
        # exactly where an engagement is described most carefully.
        movers = {n for n, b in bodies.items() if not _ground(n, b)}
        axes: dict[str, str] = {}
        for name, body in bodies.items():
            if name not in movers:
                continue
            piece = self.pieces.get(name)
            if body.motion is MotionKind.TRANSLATION:
                axes[name] = layout
            elif "moving_boundary" in (body.roles or []):
                axes[name] = _perpendicular(self._aperture_normal(bodies))
        for i in self.product.interfaces:
            if not (i.crosses_boundary and i.kind.value in DRIVE):
                continue
            for n in i.between:
                if n in movers and n not in axes:
                    axes[n] = _perpendicular(layout)

        SAME = (AxisRelation.IDENTICAL, AxisRelation.PARALLEL, AxisRelation.COLLINEAR)
        edges = [
            (a, b, i.axes) for i in self.product.interfaces
            for a, b in (i.between,)
            if a in movers and b in movers and i.axes is not AxisRelation.UNCONSTRAINED
        ]
        # Resolve along the declared input-to-output path before anything else.
        # Several interfaces can reach the same body, and whichever happened to be
        # visited first would otherwise fix its axis - a redirect only redirects if
        # the drive train is followed in the order the drive train runs.
        order = {n: i for i, n in enumerate(self.selected.element_chain)}
        edges.sort(key=lambda e: (min(order.get(e[0], 99), order.get(e[1], 99)),
                                  max(order.get(e[0], 99), order.get(e[1], 99)),
                                  e[0], e[1]))
        for _ in range(len(bodies) + 2):
            changed = False
            for a, b, rel in edges:
                for src, dst in ((a, b), (b, a)):
                    if src not in axes or dst in axes:
                        continue
                    if rel in SAME:
                        axes[dst] = axes[src]
                    else:
                        # A redirect turns the drive onto the axis the rest of the
                        # mechanism needs; prefer the layout axis when it is one of
                        # the perpendicular options rather than taking the first.
                        axes[dst] = (layout if layout != axes[src]
                                     else _perpendicular(axes[src]))
                    changed = True
            if not changed:
                break

        for a, b, rel in edges:
            if a not in axes or b not in axes:
                continue
            same = axes[a] == axes[b]
            if same is not (rel in SAME):
                self.contradictions.append(
                    f"{a} about {axes[a]} and {b} about {axes[b]} cannot satisfy the "
                    f"{rel.value} relation their interface requires"
                )
        return axes

    def _joint_axis(self, joint_piece, child: Body, host: Body) -> str:
        """The axis the joint acts about or along.

        A revolute joint on a boundary turns about an axis **lying in** that
        boundary, never its normal - about the normal the closure would spin in
        its own plane. A prismatic joint acts along the principal axis. Anything
        driven through the enclosure wall acts about the axis it enters on.
        """
        layout = self._layout_axis(self._body_cache)
        if joint_piece.permits_motion is MotionKind.TRANSLATION:
            return layout
        # The child's axis is a property of the whole drive train, not of this
        # joint: whatever the body is coupled to has already constrained it.
        derived = self._axes.get(child.name)
        if derived is not None:
            return derived
        if "moving_boundary" in (child.roles or []):
            # A revolute joint on a surface turns about an axis lying *in* that
            # surface, so it is perpendicular to the surface normal. Which of the
            # two remains free and is recorded as such.
            normal = self._aperture_normal(self._body_cache)
            return _perpendicular(normal)
        DRIVE = ("fixed_attachment", "rotational_joint", "toothed_mesh",
                 "threaded_pair", "sliding_joint")
        crossing = any(
            i.crosses_boundary and i.kind.value in DRIVE
            and (joint_piece.name in i.between or child.name in i.between)
            for i in self.product.interfaces
        )
        # An input driven in through the wall turns about an axis across the
        # layout direction; anything else turns about the layout axis itself.
        return _perpendicular(layout) if crossing else layout

    def _tree(self, bodies) -> dict[str, Joint]:
        joints: dict[str, Joint] = {}
        for name, piece in sorted(self.pieces.items()):
            if piece.element_class is not ElementClass.JOINT:
                continue
            hosts = [
                other
                for i in self.product.interfaces if name in i.between
                for other in i.between
                if other != name and other in bodies
                and bodies[other].element_class is ElementClass.BODY
            ]
            hosts = sorted(dict.fromkeys(hosts))
            if len(hosts) < 2:
                self.contradictions.append(
                    f"{name} is a joint but connects fewer than two bodies"
                )
                continue
            moving = [h for h in hosts if bodies[h].motion not in
                      (MotionKind.FIXED, MotionKind.UNSPECIFIED)]
            fixed = [h for h in hosts if h not in moving]
            child = moving[0] if moving else hosts[0]
            parent = fixed[0] if fixed else [h for h in hosts if h != child][0]
            jtype = {
                MotionKind.ROTATION: JointType.REVOLUTE,
                MotionKind.TRANSLATION: JointType.PRISMATIC,
                MotionKind.ROTATION_TRANSLATION: JointType.HELICAL,
            }.get(piece.permits_motion, JointType.FIXED)
            axis = self._joint_axis(piece, bodies[child], bodies[parent])
            joints[name] = Joint(
                name=name, type=jtype, parent=parent, child=child, axis=axis,
                frame_on_parent=self._mount(bodies[parent], bodies[child], axis,
                                            jtype, name),
                why=f"{name} permits {piece.permits_motion.value} between "
                    f"{parent} and {child}",
            )
            bodies[child].parent = parent
            bodies[child].joint = name

        # A body rigidly attached to a placed body still needs a frame. Without a
        # fixed joint it has no pose at all, which is how a transmission shaft
        # ended up unplaced despite being bolted to the screw it drives.
        changed = True
        while changed:
            changed = False
            for i in self.product.interfaces:
                if i.kind.value not in ("fixed_attachment", "toothed_mesh",
                                        "threaded_pair"):
                    continue
                a, b = i.between
                for child, parent in ((a, b), (b, a)):
                    if child not in bodies or parent not in bodies:
                        continue
                    if bodies[child].element_class is not ElementClass.BODY:
                        continue
                    if bodies[child].parent is not None or child == self._ground(bodies):
                        continue
                    if bodies[parent].parent is None and parent != self._ground(bodies):
                        continue
                    jname = f"{parent}~{child}:fixed"
                    joints[jname] = Joint(
                        name=jname, type=JointType.FIXED, parent=parent, child=child,
                        axis="z",
                        frame_on_parent=Frame(Vec3(0.0, 0.0,
                                                   bodies[parent].solid.half().z * 0.5)),
                        why=f"{child} is rigidly attached to {parent} by a "
                            f"{i.kind.value}",
                    )
                    bodies[child].parent = parent
                    bodies[child].joint = jname
                    changed = True
        return joints

    def _peer_index(self, name: str, kind: str) -> tuple[int, int]:
        """Position of this element among the peers doing the same job.

        Two guides reacting one couple, or two stops bounding one travel, are a
        *pair*: they only work separated. Drawing them coincident would make the
        very rule that requires two of them invisible.
        """
        peers = sorted(
            n for n, pc in self.pieces.items()
            if getattr(pc, "permits_motion", None) is not None
            and pc.element_class.value == kind
            and self._peer_key(pc) == self._peer_key(self.pieces[name])
        )
        return (peers.index(name) if name in peers else 0), max(len(peers), 1)

    @staticmethod
    def _peer_key(piece) -> tuple:
        return (piece.element_class.value, getattr(piece, "permits_motion", None),
                piece.kind.value)

    def _elevation(self, body: str) -> float:
        """Where along the primary axis an element sits, from the power flow.

        A drive is stratified: the input stage sits at one end, the conversion
        spans the middle, and the output travels above it. That ordering is the
        functional chain, so elevation follows chain position rather than a fixed
        fraction. Without it every element mounts at one height and the machine
        draws as a cross rather than as levels.
        """
        chain = [n for n in self.selected.element_chain if n in self.pieces]
        if body in chain and len(chain) > 1:
            i = chain.index(body)
            return -0.85 + 1.35 * (i / (len(chain) - 1))
        # Not in the chain: sit where the element it serves sits.
        for o in self.selected.support_obligations:
            if o.reacted_by == body and o.element in chain:
                return self._elevation(o.element)
        for i in self.product.interfaces:
            if body in i.between:
                other = i.between[0] if i.between[1] == body else i.between[1]
                if other in chain:
                    return self._elevation(other)
        return 0.0

    def _meshed_with(self, name: str) -> list[str]:
        """Bodies this one drives by contact or mesh rather than by attachment.

        Two members that transmit motion by meeting - a toothed pair, an indexing
        pair, a cam and its follower - turn about *separate* axes held at a fixed
        centre distance. That separation is the joint of the pair: collapse it and
        the mechanism cannot work.
        """
        out = []
        for i in self.product.interfaces:
            if i.kind.value not in ("toothed_mesh", "contact_pair"):
                continue
            if name in i.between:
                other = i.between[0] if i.between[1] == name else i.between[1]
                if other in self.pieces and \
                        self.pieces[other].element_class is ElementClass.BODY:
                    out.append(other)
        return sorted(out)

    def _mount(self, parent: Body, child: Body, axis: str, jtype: JointType,
               name: str = "") -> Frame:
        """Where the joint sits on the parent solid.

        A hinge sits on an edge of the aperture face; a bearing on the axis at the
        elevation of what it supports; a guide alongside the corridor, at the base
        of the travel it guides.
        """
        h = parent.solid.half()
        if jtype is JointType.REVOLUTE and "moving_boundary" in child.roles:
            # An edge of the +z face: the hinge line. Which edge stays free.
            return Frame(Vec3(0.0, h.y, h.z))

        layout_axis = self._layout_axis(self._body_cache)
        elev = self._elevation(child.name) * {"x": h.x, "y": h.y, "z": h.z}[layout_axis]
        if jtype is JointType.PRISMATIC:
            stated = self._travel()
            if stated is not None:
                # Base of the corridor: the stroke rises from here and must end
                # inside the cavity.
                elev = -h.z + parent.solid.params.get("wall", None).value * 2 \
                    if parent.solid.form is FormClass.SHELL else elev
            # Guides of a pair flank the axis on opposite sides; a lone guide sits
            # to one side and the missing couple is a reported gap, not a drawing.
            idx, total = self._peer_index(name, "joint") if name else (0, 1)
            side = 1.0 if total < 2 else (1.0 if idx % 2 == 0 else -1.0)
            flank = _perpendicular(layout_axis)
            mag = {"x": h.x, "y": h.y, "z": h.z}[flank] * 0.62 * side
            return Frame(AXES[flank].scaled(mag) + AXES[layout_axis].scaled(elev))
        # An element whose axis crosses the layout direction is offset along the
        # axis perpendicular to both, which is what keeps it clear of the corridor
        # the output travels through.
        layout = self._layout_axis(self._body_cache)
        offset = Vec3()
        if axis != layout:
            side = _perpendicular(axis, layout)
            mag = {"x": h.x, "y": h.y, "z": h.z}[side] * 0.55
            offset = AXES[side].scaled(mag)

        # A member that drives another by meeting it turns about a separate,
        # parallel axis. The separation is a real parameter, so it is offset here
        # and emitted as a centre distance for Stage 06 to resolve.
        partners = self._meshed_with(child.name)
        if partners:
            side = _perpendicular(axis)
            mag = {"x": h.x, "y": h.y, "z": h.z}[side] * 0.42
            offset = offset + AXES[side].scaled(mag)
            for other in partners:
                self.constraints.append(
                    ParameterConstraint(
                        predicate="axis_separation",
                        subject=f"{child.name}|{other}",
                        relation=(
                            f"centre_distance({child.name},{other}) = "
                            f"f({child.name}.radius, {other}.radius) and must exceed 0"
                        ),
                        symbols=[f"{child.name}.diameter", f"{other}.diameter"],
                        why=(
                            "the pair transmits by meeting, so their axes are "
                            "parallel and held at a centre distance; collapsing it "
                            "would make the engagement impossible"
                        ),
                        indicative=True,
                    )
                )
        return Frame(offset + AXES[layout].scaled(elev))

    # -- poses ---------------------------------------------------------------
    def _q(self, state, joint: Joint, bodies) -> float:
        """The joint coordinate in one state, at nominal.

        Canonical states only: a bounded state sits at an extreme, a moving state
        between them. The *magnitude* is a symbol; this is its display value.
        """
        child = bodies[joint.child]
        bounded = [s.name for s in self.states
                   if s.role in (StateRole.HOLDING, StateRole.LIMITED)]
        first = bounded[0] if bounded else None
        last = bounded[-1] if len(bounded) > 1 else None

        if joint.type is JointType.REVOLUTE and "moving_boundary" in child.roles:
            if child.name in state.clears:
                return FULL_SWING if state.role is not StateRole.MOVING else FULL_SWING * 0.5
            return 0.0
        if joint.type is JointType.PRISMATIC:
            # The stroke is the stated travel, not a fraction of the housing. This
            # is what makes the corridor the requirement's corridor: if the stroke
            # will not fit the cavity, that is a real contradiction rather than a
            # drawing that silently rescales.
            stated = self._travel()
            travel = (stated[0] * 10.0) if stated else \
                bodies[joint.parent].solid.half().z * 0.9
            if state.role is StateRole.MOVING:
                return travel * 0.5
            if state.name == last:
                return travel
            return 0.0
        # A body turning on a bearing advances its coordinate without moving its
        # origin. How far it advances between two bounded states depends on what
        # the transmission does with a cycle:
        #
        #   continuous   - a full revolution, so the bounded states coincide
        #   intermittent - one station, so they are genuinely different positions
        #
        # Assuming a full turn made every intermittent output look unchanged
        # between dwell and index, which is the one thing such a mechanism must
        # show. The station count itself is a free parameter.
        advance = self._output_advance(child.name)
        if state.role is StateRole.MOVING:
            return advance * 0.5
        return advance if state.name == last else 0.0

    def _output_advance(self, body: str) -> float:
        """Coordinate change per cycle for a body turning in place.

        The driver completes a full cycle; the driven side of an intermittent
        coupling advances by one station. Which side a body is on is its position
        in the functional chain, so a crank still turns once per index while the
        thing it indexes moves one step.
        """
        intermittent = any(
            (mo.ratio_symbol or "") == "intermittent" for mo in self.selected.motions
        )
        chain = [n for n in self.selected.element_chain if n in self.pieces]
        driven = bool(chain) and body == chain[-1]
        if not intermittent or not driven:
            return 2 * math.pi
        self.free_axes.setdefault(
            "station_count",
            "the output advances one station per input cycle; how many stations "
            f"the cycle is divided into is not stated, so {self.STATIONS} is taken "
            "as a first cut and any count is equally valid",
        )
        return 2 * math.pi / self.STATIONS

    # Divisions of one intermittent cycle. A first-cut estimate, recorded as free.
    STATIONS = 6

    @staticmethod
    def _align_to(axis: str) -> Rot:
        """Orient a body's long axis onto the axis of the joint that carries it.

        A shaft on a horizontal bearing lies horizontal. Without this every body
        keeps its local z and the whole product draws as one vertical column,
        which is how a right-angle drive came to look like a straight one.
        """
        if axis == "y":
            return Rot.about("x", -math.pi / 2)
        if axis == "x":
            return Rot.about("y", math.pi / 2)
        return Rot()

    def _pose(self, state, bodies, joints) -> dict[str, Frame]:
        """World frame per body, by composing the tree for this state."""
        world: dict[str, Frame] = {}
        ground = self._ground(bodies)

        def resolve(name: str, seen: frozenset[str]) -> Frame:
            if name in world:
                return world[name]
            body = bodies[name]
            if body.parent is None or name in seen:
                world[name] = Frame()
                return world[name]
            joint = joints[body.joint]
            parent_frame = resolve(body.parent, seen | {name})
            mount = parent_frame.compose(joint.frame_on_parent)
            q = self._q(state, joint, bodies)
            if joint.type is JointType.REVOLUTE:
                if "moving_boundary" in body.roles:
                    # Hinged: rotate about the mount, then offset so the plate
                    # hangs off the hinge line rather than through it.
                    swung = Frame(mount.origin, mount.rot.then(Rot.about(joint.axis, -q)))
                    local = Vec3(0.0, -body.solid.half().y, 0.0)
                    world[name] = Frame(swung.place(local), swung.rot)
                else:
                    world[name] = Frame(
                        mount.origin,
                        mount.rot.then(self._align_to(joint.axis)).then(
                            Rot.about(joint.axis, q)),
                    )
            elif joint.type in (JointType.PRISMATIC, JointType.HELICAL):
                d = AXES[joint.axis].scaled(q)
                world[name] = Frame(mount.origin + d, mount.rot)
            else:
                # A rigidly attached body keeps its parent's orientation, so a
                # shaft bolted to a horizontal crank stays horizontal.
                world[name] = mount
            return world[name]

        for name in sorted(bodies):
            if bodies[name].element_class is not ElementClass.BODY:
                continue
            if name == ground:
                world[name] = Frame()
            else:
                resolve(name, frozenset())
        return world

    # -- predicates ----------------------------------------------------------
    def _check(self, state, bodies, world) -> None:
        """Predicates over real transformed solids.

        Anything whose truth depends on a dimension is emitted as the inequality
        rather than answered, because answering it would fix a dimension this
        stage does not own.
        """
        ground = self._ground(bodies)
        shell = bodies.get(ground)
        if shell is None or shell.solid.form is not FormClass.SHELL:
            return
        cavity = shell.solid.cavity_half()
        aperture_z = shell.solid.half().z

        for name in state.covers + state.clears:
            body = bodies.get(name)
            if body is None or name not in world:
                continue
            box = aabb(world_corners(body.solid, world[name]))
            covering = box[0].z < aperture_z + 0.05 and box[1].z > aperture_z - 0.25
            wants_cover = name in state.covers
            self.constraints.append(
                ParameterConstraint(
                    predicate="covers" if wants_cover else "clears",
                    subject=name,
                    relation=(
                        f"{name}.length >= {shell.name}.length - 2*{shell.name}.wall"
                        if wants_cover else
                        f"swing({name}) places it beyond the aperture plane of {shell.name}"
                    ),
                    symbols=[f"{name}.length", f"{shell.name}.length",
                             f"{shell.name}.wall"],
                    why=(
                        "a closure occludes an aperture only if it is at least as "
                        "large as the opening it covers" if wants_cover else
                        "a closure clears an aperture only if its swing carries it "
                        "past the aperture plane"
                    ),
                    indicative=covering if wants_cover else not covering,
                )
            )

        # Interference between every pair of placed solids in this state.
        placed = sorted(n for n in world if bodies[n].element_class is ElementClass.BODY)
        for i, a in enumerate(placed):
            for b in placed[i + 1:]:
                if bodies[a].solid.form is FormClass.SHELL or \
                        bodies[b].solid.form is FormClass.SHELL:
                    continue
                if bodies[a].parent == b or bodies[b].parent == a:
                    continue  # a joint pair is meant to meet
                box_a = aabb(world_corners(bodies[a].solid, world[a]))
                box_b = aabb(world_corners(bodies[b].solid, world[b]))
                if overlaps(box_a, box_b):
                    self.constraints.append(
                        ParameterConstraint(
                            predicate="disjoint",
                            subject=f"{a}|{b}",
                            relation=f"separation({a},{b}) > 0 in state {state.name}",
                            symbols=[f"{a}.length", f"{b}.length"],
                            why=(
                                "two bodies with no declared interface occupy the "
                                "same region at nominal proportions"
                            ),
                            indicative=False,
                        )
                    )

    # -- entry point ---------------------------------------------------------
    def build(self) -> KinematicModel:
        bodies = self._bodies()
        self._axes = self._axis_map(bodies)
        joints = self._tree(bodies)
        poses: dict[tuple[str, str], Frame] = {}
        coords: dict[tuple[str, str], float] = {}

        for state in self.states:
            world = self._pose(state, bodies, joints)
            for name, frame in world.items():
                poses[(state.name, name)] = frame
            for jname, joint in joints.items():
                coords[(state.name, jname)] = self._q(state, joint, bodies)
            self._check(state, bodies, world)

        unplaced = sorted(
            n for n, b in bodies.items()
            if b.element_class is ElementClass.BODY
            and b.parent is None and "enclosure" not in b.roles
            and n != self._ground(bodies)
        )
        hosts: dict[str, str] = {}
        limits: list[str] = []
        for name, body in bodies.items():
            if body.element_class is not ElementClass.FEATURE:
                continue
            # A limit is grounded to the structure, never to the body it bounds:
            # a stop that travels with what it stops does not stop anything. Any
            # other feature rides the member it acts on.
            is_limit = any(
                i.kind.value == "fixed_attachment" and name in i.between
                and self._ground(bodies) in i.between
                for i in self.product.interfaces
            ) and any(
                i.kind.value == "contact_pair" and name in i.between
                for i in self.product.interfaces
            )
            if is_limit:
                hosts[name] = self._ground(bodies)
                limits.append(name)
                continue
            for i in self.product.interfaces:
                if name in i.between:
                    other = i.between[0] if i.between[1] == name else i.between[1]
                    if other in bodies and bodies[other].element_class is ElementClass.BODY \
                            and "enclosure" not in bodies[other].roles:
                        hosts[name] = other
                        break
            hosts.setdefault(name, self._ground(bodies))

        # A feature on a body that turns in place must sit at a radius from that
        # body's axis. At the axis it barely moves however far the body turns, so
        # neither the rotation nor the engagement it forms would be visible.
        radial = {
            n for n in hosts
            if hosts[n] in bodies
            and bodies[hosts[n]].motion is MotionKind.ROTATION
        }

        # Two limits bounding one travel act at opposite extremes; which is which
        # the mechanism does not say, so the pairing is what is asserted here.
        seats = {
            n: (1.0 if i % 2 == 0 else -1.0) for i, n in enumerate(sorted(limits))
        }
        return KinematicModel(
            bodies=bodies, joints=joints, poses=poses, coordinates=coords,
            constraints=self.constraints, contradictions=self.contradictions,
            unplaced=unplaced, feature_hosts=hosts, feature_seats=seats,
            radial_features=radial, chain=tuple(self.selected.element_chain),
            axes=dict(self._axes),
            free_choices=dict(self.free_axes),
        )
