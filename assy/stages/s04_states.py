"""Stateful kinematic realization for Stage 04.

Stage 02 declares *which* states a mechanism must occupy and what each means.
This module realizes them in space: it builds kinematic joints from the declared
pairs, couples them where motion is transmitted, computes a pose per body per
state, records what elements do to each other in each state, and evaluates the
state predicates.

Three deliberate limits:

  * **Contact is not a joint.** A contact exists in some states and not others.
    Modelling it as a pair would assert a permanent freedom the mechanism has not
    got. Contacts appear as `StateInteraction`, indexed by state.
  * **No forward-kinematics solver.** Poses are computed for discrete canonical
    states only, from the joint that carries each body. A symbolic solver would be
    a much larger commitment and is not needed to distinguish "closed" from
    "open".
  * **Envelopes are conservative.** The region between two states is the union of
    the endpoint extents. That can show two bodies *must* meet; it can never show
    that they cannot, so nothing here is a collision proof.
"""

from __future__ import annotations

from assy.domain.upstream import (
    CouplingKind,
    ElementClass,
    InteractionKind,
    JointCoupling,
    JointType,
    KinematicJoint,
    MotionKind,
    PredicateKind,
    StateInteraction,
    StatePose,
    StatePredicate,
    StateRole,
    StateValidation,
    TransitionEnvelope,
)

# The ordinal axis, shared with layout synthesis.
LOW, HIGH = 0, 7

JOINT_TYPE = {
    MotionKind.ROTATION: JointType.REVOLUTE,
    MotionKind.TRANSLATION: JointType.PRISMATIC,
    MotionKind.ROTATION_TRANSLATION: JointType.HELICAL,
    MotionKind.FIXED: JointType.FIXED,
}

COUPLING = {
    (MotionKind.ROTATION, MotionKind.TRANSLATION): (
        CouplingKind.ROTATION_TO_TRANSLATION, "lead per revolution"),
    (MotionKind.ROTATION, MotionKind.ROTATION): (
        CouplingKind.ROTATION_TO_ROTATION, "transmission ratio"),
    (MotionKind.TRANSLATION, MotionKind.TRANSLATION): (CouplingKind.DIRECT, None),
    (MotionKind.ROTATION_TRANSLATION, MotionKind.TRANSLATION): (
        CouplingKind.ROTATION_TO_TRANSLATION, "helical lead"),
}


def _tip(extent: list[list[int]], fraction: float) -> list[list[int]]:
    """Rotate a plate about its hinge edge, preserving its size.

    A rigid body does not change size when it moves. Seen in projection a closed
    plate is deep and thin; fully tipped it is thin and deep, so the depth and
    thickness spans exchange. A partial tip takes the intermediate spans. The
    hinge edge stays put: the body pivots about it rather than sliding.
    """
    (xlo, xhi), (ylo, yhi), (zlo, zhi) = (list(iv) for iv in extent)
    depth, thick = yhi - ylo, zhi - zlo
    new_depth = round(depth + (thick - depth) * fraction)
    new_thick = round(thick + (depth - thick) * fraction)
    hinge_y, hinge_z = yhi, zhi          # the far edge at the aperture
    ny_hi = min(HIGH, hinge_y + new_depth)
    ny_lo = max(LOW, ny_hi - new_depth)
    nz_hi = min(HIGH, hinge_z)
    nz_lo = max(LOW, nz_hi - new_thick)
    return [[xlo, xhi], [ny_lo, ny_hi], [nz_lo, nz_hi]]


class StateRealizer:
    """Builds the kinematic and state layers for one selected architecture."""

    def __init__(self, product, mechanical, layout):
        self.product = product
        self.selected = mechanical.selected
        self.layout = layout
        self.pieces = {p.name: p for p in product.pieces}
        self.bodies = {
            n: p for n, p in self.pieces.items() if p.element_class is ElementClass.BODY
        }
        self.states = list(self.selected.states)
        self.transitions = list(self.selected.transitions)

    # -- joints --------------------------------------------------------------
    def joints(self, attachments: dict[str, list[str]]) -> list[KinematicJoint]:
        """One kinematic pair per declared joint element.

        A joint element with two hosts becomes a pair between them; the parent is
        the body that does not move, so the coordinate describes the child.
        """
        out: list[KinematicJoint] = []
        for name, piece in sorted(self.pieces.items()):
            if piece.element_class is not ElementClass.JOINT:
                continue
            hosts = [h for h in attachments.get(name, []) if h in self.bodies]
            if len(hosts) < 2:
                continue
            moving = [h for h in hosts if self.bodies[h].moving]
            fixed = [h for h in hosts if not self.bodies[h].moving]
            child = moving[0] if moving else hosts[0]
            parent = fixed[0] if fixed else hosts[1 if hosts[0] == child else 0]
            jtype = JOINT_TYPE.get(piece.permits_motion, JointType.FIXED)
            out.append(
                KinematicJoint(
                    name=name, type=jtype, parent=parent, child=child,
                    axis=None,
                    frame_on_parent=f"{parent} at its interface with {name}",
                    frame_on_child=f"{child} at its interface with {name}",
                    why=(
                        f"{name} permits {piece.permits_motion.value} between "
                        f"{parent} and {child}"
                    ),
                )
            )
        return out

    def couplings(self, joints: list[KinematicJoint]) -> list[JointCoupling]:
        """Where one body's motion drives another's, and by what kind of ratio.

        Read off the functional chain: consecutive members transmit motion, and
        the pair of motion kinds names the coupling. The ratio itself stays
        unresolved - a lead or a transmission ratio is Stage 05-06's to fix.
        """
        out: list[JointCoupling] = []
        chain = [n for n in self.selected.element_chain if n in self.bodies]
        for a, b in zip(chain, chain[1:]):
            ka = self.bodies[a].motion_kind
            kb = self.bodies[b].motion_kind
            if MotionKind.FIXED in (ka, kb) or MotionKind.UNSPECIFIED in (ka, kb):
                continue
            kind, ratio = COUPLING.get(
                (ka, kb), (CouplingKind.DIRECT, None)
            )
            out.append(
                JointCoupling(
                    driver=a, driven=b, kind=kind, ratio_symbol=ratio,
                    why=(
                        f"{a} moves by {ka.value} and drives {b}, which moves by "
                        f"{kb.value}"
                    ),
                )
            )
        return out

    # -- poses ---------------------------------------------------------------
    def _base_extent(self, body: str, carried_by=None) -> list[list[int]]:
        """The body's own extent, which is not its travel range.

        A translating member occupies a slab that moves *within* the corridor its
        layout span describes; equating the two would draw a platform filling the
        chamber it travels through.
        """
        pl = self.layout.placements.get(body)
        if pl is None:
            return [[LOW, HIGH], [LOW, HIGH], [LOW, HIGH]]
        lateral = [2, 5] if pl.radial.value == "on_axis" else [0, 2]
        lo, hi = pl.lo, pl.hi
        if carried_by is not None and carried_by.type is JointType.PRISMATIC:
            thickness = max(1, (hi - lo) // 3)
            lo, hi = pl.lo, min(hi, pl.lo + thickness)
        return [lateral, [2, 5], [lo, hi]]

    def poses(self, joints: list[KinematicJoint]) -> list[StatePose]:
        """A pose per body per state, consistent with the joint that carries it.

        A body a joint carries takes the joint's extreme coordinate in a limited
        or holding state and its opposite in the cleared state. A body no joint
        carries keeps its base extent in every state - it does not move.
        """
        carried = {j.child: j for j in joints if j.type is not JointType.FIXED}
        # Canonical ordering: the declared state sequence runs from one extreme of
        # the motion to the other, so the first bounded state is q_min and the last
        # is q_max. This covers drives, whose states differ by travel position
        # rather than by what they cover.
        bounded = [
            st.name for st in self.states
            if st.role in (StateRole.HOLDING, StateRole.LIMITED)
        ]
        first_bound = bounded[0] if bounded else None
        last_bound = bounded[-1] if len(bounded) > 1 else None
        out: list[StatePose] = []
        for st in self.states:
            for body in sorted(self.bodies):
                joint = carried.get(body)
                extent = [list(iv) for iv in self._base_extent(body, joint)]
                value, why = None, "no joint carries this body, so it does not move"
                if joint is not None:
                    # A revolute joint displaces its child only when that child is
                    # a boundary being swung aside. A shaft on a bearing turns in
                    # place: its coordinate changes, its position does not.
                    swings = (
                        joint.type is JointType.REVOLUTE
                        and "moving_boundary" in (self.bodies[body].engineering_roles or [])
                    )
                    spins = joint.type is JointType.REVOLUTE and not swings
                    travels = joint.type in (JointType.PRISMATIC, JointType.HELICAL)
                    if spins:
                        value = (
                            "q_min" if st.name == first_bound
                            else "q_max" if st.name == last_bound else "between"
                        )
                        why = f"{body} turns in place on {joint.name}"
                    elif st.role is StateRole.MOVING:
                        if swings:
                            extent = _tip(extent, fraction=0.5)
                        elif travels:
                            extent[2] = [min(HIGH - 1, extent[2][0] + 2),
                                         min(HIGH, extent[2][1] + 2)]
                        value = "between"
                        why = (
                            f"{body} is mid-swing on {joint.name}" if swings
                            else f"{body} is mid-travel on {joint.name}"
                        )
                    elif body in st.clears:
                        if swings:
                            extent = _tip(extent, fraction=1.0)
                        else:
                            extent[2] = [min(HIGH - 1, extent[2][0] + 4),
                                         min(HIGH, extent[2][1] + 4)]
                        value = "q_max"
                        why = f"{joint.name} has carried {body} clear of its covered region"
                    elif body in st.covers:
                        value = "q_min"
                        why = f"{joint.name} holds {body} at its covering position"
                    elif st.name == first_bound:
                        value = "q_min"
                        why = f"{body} rests at the first bound of {joint.name}"
                    elif st.name == last_bound:
                        if travels:
                            extent[2] = [min(HIGH - 1, extent[2][0] + 4),
                                         min(HIGH, extent[2][1] + 4)]
                        elif swings:
                            extent = _tip(extent, fraction=1.0)
                        value = "q_max"
                        why = f"{body} has travelled to the far bound of {joint.name}"
                    else:
                        if travels:
                            extent[2] = [min(HIGH - 1, extent[2][0] + 2),
                                         min(HIGH, extent[2][1] + 2)]
                        value = "between"
                        why = f"{body} is in transit on {joint.name}"
                out.append(
                    StatePose(
                        state=st.name, body=body, extent=extent,
                        containment=(
                            self.layout.placements[body].containment.value
                            if body in self.layout.placements else "interior"
                        ),
                        via_joint=joint.name if joint else None,
                        joint_value=value, why=why,
                    )
                )
        return out

    # -- interactions --------------------------------------------------------
    def interactions(self, attachments) -> list[StateInteraction]:
        """What elements do to each other in each state. Never joints."""
        out: list[StateInteraction] = []
        for st in self.states:
            for held in st.holds:
                partner = next(
                    (h for h in attachments.get(held, []) if h in self.bodies), held
                )
                out.append(
                    StateInteraction(
                        state=st.name, kind=InteractionKind.ENGAGEMENT,
                        between=(held, partner),
                        why=f"{held} is engaged and maintains the {st.name} state",
                    )
                )
            if st.role is StateRole.RELEASING:
                for prev in self.states:
                    for held in prev.holds:
                        partner = next(
                            (h for h in attachments.get(held, []) if h in self.bodies),
                            held,
                        )
                        out.append(
                            StateInteraction(
                                state=st.name, kind=InteractionKind.DISENGAGEMENT,
                                between=(held, partner),
                                why=f"{held} has been disengaged to leave {prev.name}",
                            )
                        )
                    break
            for limiter in st.at_limit_of:
                partner = next(
                    (h for h in attachments.get(limiter, []) if h in self.bodies),
                    limiter,
                )
                out.append(
                    StateInteraction(
                        state=st.name, kind=InteractionKind.STOP_CONTACT,
                        between=(limiter, partner),
                        why=f"{limiter} bounds the motion in the {st.name} state",
                    )
                )
            for cleared in st.clears:
                out.append(
                    StateInteraction(
                        state=st.name, kind=InteractionKind.CLEARANCE,
                        between=(cleared, "aperture"),
                        why=f"{cleared} has left the opening free in the {st.name} state",
                    )
                )
        return out

    # -- predicates ----------------------------------------------------------
    def predicates(self, poses: list[StatePose]) -> list[StatePredicate]:
        by_state: dict[str, dict[str, StatePose]] = {}
        for p in poses:
            by_state.setdefault(p.state, {})[p.body] = p
        out: list[StatePredicate] = []
        for st in self.states:
            for body in st.covers:
                pose = by_state.get(st.name, {}).get(body)
                out.append(
                    StatePredicate(
                        state=st.name, predicate=PredicateKind.COVERS, subject=body,
                        object="aperture",
                        holds=pose is not None and pose.joint_value == "q_min",
                        evidence=(
                            f"{body} sits at the covering extreme of its joint"
                            if pose and pose.joint_value == "q_min"
                            else f"{body} is not at a covering position"
                        ),
                    )
                )
            for body in st.clears:
                pose = by_state.get(st.name, {}).get(body)
                out.append(
                    StatePredicate(
                        state=st.name, predicate=PredicateKind.CLEARS, subject=body,
                        object="aperture",
                        holds=pose is not None and pose.joint_value in ("between", "q_max"),
                        evidence=(
                            f"{body} has left the covering extreme of its joint"
                            if pose and pose.joint_value in ("between", "q_max")
                            else f"{body} has not left the covered region"
                        ),
                    )
                )
            for held in st.holds:
                out.append(
                    StatePredicate(
                        state=st.name, predicate=PredicateKind.ENGAGED, subject=held,
                        holds=True,
                        evidence=f"the family declares {held} engaged in {st.name}",
                    )
                )
            if st.role is StateRole.RELEASING:
                prior = next((s for s in self.states if s.holds), None)
                for held in (prior.holds if prior else []):
                    out.append(
                        StatePredicate(
                            state=st.name, predicate=PredicateKind.RELEASED,
                            subject=held, holds=True,
                            evidence=f"{held} is no longer engaged in {st.name}",
                        )
                    )
            for limiter in st.at_limit_of:
                present = limiter in self.pieces
                out.append(
                    StatePredicate(
                        state=st.name, predicate=PredicateKind.AT_LIMIT,
                        subject=limiter, holds=present,
                        evidence=(
                            f"{limiter} is a declared element that bounds the motion"
                            if present else f"{limiter} is not present in the architecture"
                        ),
                    )
                )
        return out

    # -- conservative envelopes ----------------------------------------------
    def envelopes(self, poses: list[StatePose]) -> list[TransitionEnvelope]:
        by_state: dict[str, dict[str, StatePose]] = {}
        for p in poses:
            by_state.setdefault(p.state, {})[p.body] = p
        out: list[TransitionEnvelope] = []
        for t in self.transitions:
            a, b = by_state.get(t.from_state, {}), by_state.get(t.to_state, {})
            for body in sorted(set(a) & set(b)):
                pa, pb = a[body].extent, b[body].extent
                if pa == pb:
                    continue
                union = [
                    [min(pa[i][0], pb[i][0]), max(pa[i][1], pb[i][1])]
                    for i in range(3)
                ]
                out.append(
                    TransitionEnvelope(
                        transition=f"{t.from_state}->{t.to_state}",
                        body=body, extent=union,
                    )
                )
        return out

    # -- validation ----------------------------------------------------------
    def validate(self, poses, predicates, envelopes) -> list[StateValidation]:
        by_state_pred: dict[str, list[StatePredicate]] = {}
        for p in predicates:
            by_state_pred.setdefault(p.state, []).append(p)
        out: list[StateValidation] = []
        for t in self.transitions:
            checked = by_state_pred.get(t.from_state, []) + by_state_pred.get(
                t.to_state, []
            )
            failed = [p for p in checked if not p.holds]
            moved = [e for e in envelopes
                     if e.transition == f"{t.from_state}->{t.to_state}"]
            risks: list[str] = []
            sa = next((x for x in self.states if x.name == t.from_state), None)
            sb = next((x for x in self.states if x.name == t.to_state), None)
            # Motion is required only where the two states differ in what the body
            # covers, clears, or bounds. Two states that both clear the aperture
            # need no travel between them - only the limit contact changes.
            differs = bool(sa and sb) and (
                set(sa.covers) != set(sb.covers)
                or set(sa.clears) != set(sb.clears)
                or set(sa.at_limit_of) != set(sb.at_limit_of)
            )
            jointed = {j.child for j in
                       [x for x in getattr(self, "_joints", [])]}
            if differs and not moved and any(m in self.bodies for m in t.moves):
                risks.append(
                    f"{', '.join(t.moves)} should move during this transition but no "
                    "pose changes, so the motion is not realized spatially"
                )
            for f in failed:
                risks.append(f"{f.predicate.value}({f.subject}) does not hold: {f.evidence}")
            if moved:
                risks.append(
                    "envelope overlap is a conservative over-estimate and cannot "
                    "certify clearance; interference must be re-checked with geometry"
                )
            out.append(
                StateValidation(
                    transition=f"{t.from_state}->{t.to_state}",
                    feasible=not failed and (bool(moved) or not differs),
                    predicates=[
                        f"{p.predicate.value}({p.subject})={p.holds}" for p in checked
                    ],
                    unresolved_risks=risks,
                    why=t.why,
                )
            )
        return out
