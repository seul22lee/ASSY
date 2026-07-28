"""Stage 05 - Engineering Integration.

Question: how must the design be engineered so it can exist, move, assemble,
manufacture, and proceed to deterministic CAD generation?

This is the architecturally novel stage: a problem-driven design loop over the
four-object working state, not a single generation call.

    seed commitments
        -> run checks (detect)
        -> pick problem
        -> propose candidates
        -> select
        -> apply (supersede, commit, close)
        -> spawn implied problems
        -> invalidate dependent checks
        -> repeat
        -> mandatory closure pass

Convergence is not guaranteed and is not claimed. The loop runs under an explicit
budget and returns a structured blocked result rather than forcing closure
(STAGE_05 section 18).
"""

from __future__ import annotations

from collections import Counter
from typing import ClassVar

from assy.domain.common import ObjectMeta, Provenance, Stage, new_id
from assy.domain.engineering import (
    BlockedReason,
    CADReadyEngineeringDefinition,
    CheckResult,
    Commitment,
    CommitmentKind,
    CommitmentStatus,
    EngineeringWorkingState,
    Problem,
    ProblemOrigin,
    ProblemType,
    ReadinessReport,
    Resolution,
    ResolutionStatus,
    Severity,
)
from assy.domain.upstream import (
    ConceptVisualization,
    AxisRelation,
    ElementClass,
    MotionKind,
    MechanicalArchitecture,
    ProductArchitecture,
    RequirementSpec,
)
from assy.knowledge import checks as K
from assy.knowledge import mechanisms as cat
from assy.knowledge import partfeatures as PF
from assy.construction import build_assembly
from assy.knowledge import resolvers as R
from assy.knowledge import spawning
from assy.stages.base import DeterministicReasoner, PipelineStage, Reasoner

SEVERITY_ORDER = {
    Severity.BLOCKING: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
    Severity.INFORMATIONAL: 4,
}


class Budget:
    """Explicit limits. Exceeding one produces a structured block, never a silent pass."""

    def __init__(self, max_iterations: int = 200, max_repeat: int = 4, max_supersession: int = 12):
        self.max_iterations = max_iterations
        self.max_repeat = max_repeat
        self.max_supersession = max_supersession


class EngineeringIntegration(PipelineStage):
    stage_id: ClassVar[Stage] = Stage.ENGINEERING
    question: ClassVar[str] = "How must this design be engineered to become CAD-ready?"
    produces: ClassVar[str] = "CADReadyEngineeringDefinition"

    def __init__(self, reasoner: Reasoner | None = None, budget: Budget | None = None):
        self.reasoner = reasoner or DeterministicReasoner()
        self.budget = budget or Budget()

    # -- seeding -----------------------------------------------------------
    def _context(self, spec: RequirementSpec, mechanical: MechanicalArchitecture) -> R.ResolveContext:
        """Derive resolver context from requirements. No benchmark branching."""
        ctx = R.ResolveContext(family_id=mechanical.selected_id or "")
        for r in spec.requirements:
            if r.target is None:
                continue
            unit, val = r.target.unit.lower(), r.target.value
            if unit == "mm":
                ctx.travel_mm = max(ctx.travel_mm, val) if r.comparator != "between" else val
                if r.upper:
                    ctx.travel_mm = (val + r.upper.value) / 2.0
            elif unit == "kg":
                ctx.payload_n = round(val * 9.81 + 5.0, 2)  # payload plus moving structure
            elif unit == "g":
                ctx.payload_n = round(val * 0.00981 + 5.0, 2)
        return ctx

    def _driven_and_host(self, pieces, a: str, b: str) -> tuple[str, str]:
        """Which side of an interface moves and which one reacts.

        Taken from the pieces' declared motion, not from the order the family
        wrote the pair in. A journal belongs on the shaft and the bore on the
        housing; getting that from declaration order would put the bore on the
        shaft whenever a family happened to name it second.
        """
        pa, pb = pieces.get(a), pieces.get(b)
        moving_a = pa is not None and pa.motion_kind is not MotionKind.FIXED
        moving_b = pb is not None and pb.motion_kind is not MotionKind.FIXED
        if moving_a and not moving_b:
            return a, b
        if moving_b and not moving_a:
            return b, a
        # Neither or both move: the element that exists to permit motion is the
        # host, since that is what a joint or a guide is for.
        if pb is not None and pb.element_class is ElementClass.JOINT:
            return a, b
        if pa is not None and pa.element_class is ElementClass.JOINT:
            return b, a
        return a, b

    def _feature(self, state, piece: str, kind: PF.FeatureKind, why: str,
                 source: str, served: list[str]) -> None:
        """Commit one feature onto one part, with the reason it has to be there."""
        subject = f"{piece}.{kind.value}"
        if any(c.subject == subject for c in state.active):
            return
        state.commit(
            Commitment(
                kind=CommitmentKind.ENTITY,
                subject=subject,
                statement=f"{piece} carries a {kind.value.replace('_', ' ')}: {why}",
                roles=[kind.value, "feature"],
                symbolic=True,
                status=CommitmentStatus.PROVISIONAL,
                provenance=Provenance(requirements=served, method=source),
            )
        )

    def _seed(
        self,
        state: EngineeringWorkingState,
        spec: RequirementSpec,
        mechanical: MechanicalArchitecture,
        product: ProductArchitecture,
        kinematic=None,
    ) -> None:
        """Seed from what the previous stages actually decided.

        Entities come from Stage 03's pieces, not from the Stage 02 catalogue:
        a piece is what gets manufactured, and Stage 03 already resolved which
        conceptual elements share one. Re-deriving them from the family here
        would silently discard that integration and re-decide it.

        Geometry, motion and constraints come from Stage 04. Stage 05 does not
        re-solve the layout; it engineers the layout it was given.
        """
        served = [r.id for r in spec.requirements]
        pieces = {p.name: p for p in product.pieces}

        for piece in product.pieces:
            state.commit(
                Commitment(
                    kind=CommitmentKind.ENTITY,
                    subject=piece.name,
                    statement=f"{piece.name}: {piece.kind.value} realising "
                              f"{', '.join(piece.realises_elements) or 'no element'}",
                    roles=list(piece.engineering_roles),
                    status=CommitmentStatus.SELECTED,
                    provenance=Provenance(requirements=served, method="product_architecture"),
                )
            )
            feats, why = PF.features_for_form(piece.form)
            for f in feats:
                self._feature(state, piece.name, f, why, "form", served)

        # An interface is not a line between two names; it is real material on
        # both parts. This is the step that turns a concept into a part topology.
        for iface in product.interfaces:
            a, b = iface.between
            rule = PF.features_for_interface(iface.kind)
            if rule is None:
                continue
            driven, host = self._driven_and_host(pieces, a, b)
            for side, feats in ((driven, rule.driven), (host, rule.host)):
                if side not in pieces:
                    continue
                for f in feats:
                    self._feature(state, side, f, rule.why,
                                  f"interface/{iface.kind.value}", served)
            if iface.crosses_boundary:
                kind, why = PF.BOUNDARY_FEATURE
                for side in (a, b):
                    if side in pieces and pieces[side].form == "shell":
                        self._feature(state, side, kind, why, "boundary_crossing", served)
            state.commit(
                Commitment(
                    kind=CommitmentKind.INTERFACE,
                    subject=f"{a}~{b}",
                    statement=f"{iface.kind.value} transmitting {iface.transmits or 'load'}; "
                              f"axes {iface.axes.value}",
                    value=iface.kind.value,
                    status=CommitmentStatus.SELECTED,
                    provenance=Provenance(requirements=served, method="product_architecture"),
                )
            )

        # Providing an obligation is material on the part that reacts it.
        for ob in product.obligation_ownership:
            feats, why = PF.features_for_obligation(ob.obligation)
            if ob.owner_piece in pieces:
                for f in feats:
                    self._feature(state, ob.owner_piece, f, why,
                                  f"obligation/{ob.obligation.value}", served)
            elif ob.owner_piece is None:
                # Stage 03 could not find a piece answerable for this. It cannot
                # become material on any part, so it stays an open problem.
                state.open_problem(
                    Problem(
                        type=ProblemType.UNDETERMINED,
                        origin=ProblemOrigin.UPSTREAM,
                        entities=[ob.element],
                        phenomenon=f"unowned_obligation_{ob.obligation.value}",
                        evaluation_domain="static",
                        statement=f"{ob.element} requires {ob.obligation.value} but no "
                                  f"piece owns it: {ob.unowned_reason or 'no reason recorded'}",
                        severity=Severity.HIGH,
                    )
                )

        self._characteristic_parameters(state, mechanical, pieces, served)

        if kinematic is not None:
            self._ifaces = list(product.interfaces)
            self._seed_from_kinematics(state, kinematic, served)
            self._check_axis_compatibility(state, product, kinematic, served)

        state.commit(
            Commitment(
                kind=CommitmentKind.ASSEMBLY,
                subject="product.housing_strategy",
                statement=product.housing_strategy,
                value=product.housing_strategy,
                status=CommitmentStatus.SELECTED,
                provenance=Provenance(method="product_architecture", requirements=served),
            )
        )

        # Spawning rules are written for parts: they ask what a part needs in order
        # to work. Running them over features, parameters and constraints as well
        # multiplied the agenda by the size of the topology - a feature is a
        # consequence of a part's interfaces, not an independent design subject
        # with needs of its own, and treating it as one buried the real problems
        # under thousands of duplicates.
        for c in list(state.active):
            if c.kind is not CommitmentKind.ENTITY or "feature" in c.roles:
                continue
            for pr in spawning.spawn_for(c):
                state.open_problem(pr)

        for r in spec.quantitative:
            state.open_problem(
                Problem(
                    type=ProblemType.UNDETERMINED,
                    origin=ProblemOrigin.REQUIREMENT,
                    entities=["product"],
                    phenomenon=f"requirement_{r.id}",
                    evaluation_domain="requirement",
                    statement=r.statement,
                    severity=Severity.LOW,
                    serves_requirements=[r.id],
                )
            )

    def _axis_of(self, km) -> dict[str, str]:
        """Each body's motion axis, propagated through rigid attachments.

        A body rigidly fixed to another turns on that one's axis - a disc keyed to
        a shaft is not free to have an axis of its own. Reading only the body's own
        joint would leave every carried element unconstrained and let the check
        pass vacuously.
        """
        published = dict(getattr(km, "axes", {}) or {})
        if published:
            # Stage 04 derived these by propagating the interface constraints. Use
            # them rather than reconstructing a second, weaker answer here.
            return published
        axis = {j.child: j.axis for j in km.joints.values() if j.type.value != "fixed"}
        for _ in range(len(km.joints) + 1):
            for j in km.joints.values():
                if j.type.value != "fixed":
                    continue
                for a, b in ((j.parent, j.child), (j.child, j.parent)):
                    if a in axis and b not in axis:
                        axis[b] = axis[a]
        return axis

    def _check_axis_compatibility(self, state, product, km, served) -> None:
        """Verify that interfaces which transmit motion join compatible axes.

        A planar pair engages only if its axes are parallel; a redirect exists to
        make them intersect. Stage 04 derives each element's axis from its own
        situation, so nothing has yet confirmed that two elements declared to drive
        each other *can*. This needs no dimension - it is the cheapest real
        mechanical check available, and a mechanism that fails it cannot move at
        any size.
        """
        axis = self._axis_of(km)
        hosts = km.feature_hosts
        for iface in product.interfaces:
            rel = iface.axes
            if rel in (AxisRelation.UNCONSTRAINED,):
                continue
            a, b = (hosts.get(n, n) for n in iface.between)
            ax, bx = axis.get(a), axis.get(b)
            if ax is None or bx is None or a == b:
                continue
            same = ax == bx
            ok = same if rel in (AxisRelation.PARALLEL, AxisRelation.COLLINEAR,
                                 AxisRelation.IDENTICAL) else not same
            if ok:
                continue
            state.open_problem(
                Problem(
                    type=ProblemType.CONFLICTING,
                    origin=ProblemOrigin.CHECK,
                    entities=[a, b],
                    phenomenon="axis_incompatibility",
                    evaluation_domain="static",
                    statement=(
                        f"{iface.kind.value} between {a} and {b} requires {rel.value} "
                        f"axes, but {a} acts about {ax} and {b} about {bx}. "
                        "As arranged the interface cannot transmit motion at any size."
                    ),
                    severity=Severity.BLOCKING,
                )
            )

    AXIS_INDEX = {"x": 0, "y": 1, "z": 2}

    def _world_extent_terms(self, body, frame) -> list[str]:
        """A body's half-extent along each world axis, as a parameter expression.

        A rotated body's world extent is a combination of its local ones, with the
        rotation supplying the coefficients: |R[k][j]| weights local axis j into
        world axis k. That makes the expression exact for the box at this
        orientation, and linear in the dimensions, which is what a solver needs.
        """
        local = body.solid.half_terms()
        out = []
        for k in range(3):
            terms = []
            for j in range(3):
                c = abs(frame.rot.m[k][j])
                if c < 1e-9 or local[j] in ("0", ""):
                    continue
                terms.append(local[j] if c > 1 - 1e-9 else f"{c:.4g}*({local[j]})")
            out.append(" + ".join(terms) if terms else "0")
        return out

    def _algebraise(self, state, km, served: list[str]) -> None:
        """Turn Stage 04's spatial predicates into inequalities over parameters.

        Stage 04 states its spatial rules over *bodies*: "separation(a,b) > 0".
        The parameters are named `a.length`, `b.wall`. Those are two different
        vocabularies, so the constraint set and the variable set never touched -
        Stage 06 would have received a bag of variables and a list of sentences
        about neither. A rule that does not name the quantities it constrains
        cannot be solved against them, and it cannot be checked either, which is
        why zero collision predicates had ever been evaluated.

        Origins are taken from the concept layout and extents stay symbolic, so
        each inequality is a linearisation about that layout rather than a
        general solution. Stage 06 re-solves it; what it no longer has to do is
        invent the relation.
        """
        for con in km.constraints:
            if con.predicate == "disjoint" and "|" in con.subject:
                a, b = con.subject.split("|", 1)
                st = con.relation.rsplit("in state ", 1)[-1].strip()
                fa, fb = km.poses.get((st, a)), km.poses.get((st, b))
                if fa is None or fb is None or a not in km.bodies or b not in km.bodies:
                    continue
                ea = self._world_extent_terms(km.bodies[a], fa)
                eb = self._world_extent_terms(km.bodies[b], fb)
                ha = km.bodies[a].solid.half().as_tuple()
                hb = km.bodies[b].solid.half().as_tuple()
                oa, ob = fa.origin.as_tuple(), fb.origin.as_tuple()
                # Separate along the axis with the most room at the concept
                # layout: that is the direction the design is already using.
                k = max(range(3), key=lambda i: abs(oa[i] - ob[i]) - (ha[i] + hb[i]))
                gap = abs(oa[k] - ob[k])
                axis = "xyz"[k]
                expr = f"({ea[k]}) + ({eb[k]}) <= {gap:.4g}"
                self._constraint(
                    state, f"disjoint.{a}.{b}.{st}", expr,
                    f"{a} and {b} must not occupy the same space in state {st}; "
                    f"separated along {axis}, their half-extents must fit the "
                    f"{gap:.4g} available at the concept layout", served)
            elif con.predicate == "axis_separation" and "|" in con.subject:
                a, b = con.subject.split("|", 1)
                if a not in km.bodies or b not in km.bodies:
                    continue
                ra = km.bodies[a].solid.half_terms()[0]
                rb = km.bodies[b].solid.half_terms()[0]
                self._constraint(
                    state, f"axis_separation.{a}.{b}",
                    f"centre_distance({a},{b}) > ({ra}) + ({rb})",
                    f"{a} and {b} turn on parallel axes; their centre distance "
                    "must exceed the radii that meet, or they interfere", served)
            elif con.relation and any(op in con.relation for op in (">=", "<=", ">", "<", "=")) \
                    and "(" not in con.relation.split("=")[0]:
                self._constraint(state, f"{con.predicate}.{con.subject}",
                                 con.relation, con.why, served)
            else:
                # Not expressible over the published parameters. Left open rather
                # than dropped: an unstated rule is one nothing can enforce.
                state.open_problem(
                    Problem(
                        type=ProblemType.UNDETERMINED,
                        origin=ProblemOrigin.UPSTREAM,
                        entities=[con.subject],
                        phenomenon=f"unalgebraic_{con.predicate}",
                        evaluation_domain="definition",
                        statement=f"'{con.relation}' constrains the design but names no "
                                  "parameter, so no solver can enforce or check it",
                        severity=Severity.MEDIUM,
                    )
                )

        self._mating_relations(state, km, served)

        # A parameter system with no objective has no preferred solution: every
        # feasible point is equally good and the solver returns an arbitrary one.
        envelope = [b.solid.half_terms()[2] for n, b in km.bodies.items()
                    if b.element_class is ElementClass.BODY]
        if envelope:
            state.commit(
                Commitment(
                    kind=CommitmentKind.OBJECTIVE,
                    subject="objective.envelope",
                    statement="minimise the enclosing envelope subject to the "
                              "clearance and travel constraints",
                    expression="minimise " + " + ".join(f"({e})" for e in envelope[:12]),
                    symbolic=True,
                    status=CommitmentStatus.PROVISIONAL,
                    provenance=Provenance(requirements=served, method="packaging_objective"),
                )
            )

    #: Which dimension mates, and only for forms where the answer is unambiguous.
    #: A plate's thickness and a shell's wall are not mating dimensions for a
    #: journal or a thread; treating them as such produced relations equating a
    #: screw diameter to a platform thickness and a housing wall to a bore.
    MATING_DIM = {"shaft": "diameter", "collar": "bore",
                  "rail": "section", "link": "section"}

    #: The form pairing each interface kind actually implies. An interface whose
    #: two sides are not these forms has no derivable mating dimension, and
    #: guessing one is worse than leaving the parameter free: a wrong relation
    #: forces the solver to an unbuildable design, a missing one leaves it open.
    MATING_FORMS = {
        "rotational_joint": ({"shaft"}, {"collar"}),
        "threaded_pair": ({"shaft"}, {"collar"}),
        "sliding_joint": ({"rail", "link"}, {"rail", "link"}),
        "toothed_mesh": ({"shaft"}, {"shaft"}),
    }

    def _mating_relations(self, state, km, served: list[str]) -> None:
        """Dimensions that two parts must agree on because they meet.

        A bore is not free of the shaft that runs in it, and a nut is not free of
        its screw. These relations are the bulk of what actually couples a
        parameter set: without them each part is sized in isolation and a solver
        can satisfy every spatial rule while producing a shaft that does not fit
        its own bearing.

        Only the unambiguous pairings are emitted. A running fit and a press fit
        are different clearances, and choosing between them is a resolution, not
        a relation - so the clearance stays a symbol here.
        """
        for iface in getattr(self, "_ifaces", []):
            a, b = iface.between
            if a not in km.bodies or b not in km.bodies:
                continue
            sa, sb = km.bodies[a].solid, km.bodies[b].solid
            fa, fb = sa.form.value, sb.form.value
            da = sa.params.get(self.MATING_DIM.get(fa, ""))
            db = sb.params.get(self.MATING_DIM.get(fb, ""))
            if da is None or db is None:
                continue
            kind = iface.kind.value
            forms = self.MATING_FORMS.get(kind)
            if forms is None:
                continue
            if not ((fa in forms[0] and fb in forms[1])
                    or (fb in forms[0] and fa in forms[1])):
                continue
            if kind == "rotational_joint":
                bore, shaft = ((da, db) if fa == "collar" else (db, da))
                if bore is shaft:
                    continue
                self._constraint(
                    state, f"fit.{a}.{b}",
                    f"{bore.name} = {shaft.name} + running_clearance",
                    "a journal turns inside its bore, so the bore is the shaft "
                    "plus a running fit, never an independent dimension", served)
            elif kind == "threaded_pair":
                self._constraint(
                    state, f"thread_fit.{a}.{b}",
                    f"{da.name} = {db.name}",
                    "both halves of a screw pair are cut on one nominal diameter",
                    served)
            elif kind == "sliding_joint":
                self._constraint(
                    state, f"slide_fit.{a}.{b}",
                    f"{da.name} = {db.name} + sliding_clearance",
                    "a slider and its guide share a mating width plus the clearance "
                    "that lets it move", served)
            elif kind == "toothed_mesh":
                self._constraint(
                    state, f"mesh.{a}.{b}",
                    f"centre_distance({a},{b}) = ({da.name} + {db.name})/2",
                    "meshing members touch on their pitch circles, which fixes the "
                    "centre distance to the sum of the pitch radii", served)

    def _constraint(self, state, subject: str, expr: str, why: str, served) -> None:
        if any(c.subject == subject for c in state.active):
            return
        state.commit(
            Commitment(
                kind=CommitmentKind.CONSTRAINT,
                subject=subject,
                statement=why,
                expression=expr,
                symbolic=True,
                status=CommitmentStatus.PROVISIONAL,
                provenance=Provenance(requirements=served, method="spatial_algebra"),
            )
        )

    def _characteristic_parameters(self, state, mechanical, pieces, served) -> None:
        """The quantities the selected principle is defined by.

        Stage 02 chose a physical principle; these are what that principle needs
        fixed before it works. They are not derivable from the layout - a bounding
        box can be sized without ever naming a hook depth or a thread lead - so
        without this step a design reaches CAD looking complete while none of the
        quantities that decide whether it functions has been raised at all.

        Each is committed undetermined and opened as a problem. That is the honest
        state: Stage 05 identifies them, Stage 06 resolves them.
        """
        family = cat.by_id(mechanical.selected_id or "")
        for spec_p in getattr(family, "parameters", ()):
            # The role may have been integrated into another piece, or be a feature
            # on one. Attach to the piece that realises it, else to the product.
            owner = spec_p.of_role
            if owner not in pieces:
                owner = next(
                    (name for name, pc in pieces.items()
                     if spec_p.of_role in (pc.realises_elements or [])),
                    "product",
                )
            subject = f"{owner}.{spec_p.name}"
            if any(c.subject == subject for c in state.active):
                continue
            state.commit(
                Commitment(
                    kind=CommitmentKind.PARAMETER,
                    subject=subject,
                    statement=f"{spec_p.name} ({spec_p.quantity}) of {owner}: {spec_p.why}",
                    symbolic=True,
                    value=None,
                    unit=spec_p.quantity,
                    status=CommitmentStatus.PROVISIONAL,
                    provenance=Provenance(
                        requirements=served,
                        method=f"mechanism_principle/{family.id}",
                    ),
                )
            )
            state.open_problem(
                Problem(
                    type=ProblemType.UNDETERMINED,
                    origin=ProblemOrigin.SPAWNED,
                    entities=[owner],
                    phenomenon=f"characteristic_{spec_p.name}",
                    evaluation_domain="definition",
                    statement=f"{subject} is required by the {family.id} principle "
                              f"and has no value: {spec_p.why}",
                    # Not HIGH: Stage 05 identifies these, Stage 06 resolves them.
                    # Raising them as urgent made the loop re-pick a problem it has
                    # no resolver for until it tripped the cycle budget.
                    severity=Severity.LOW,
                    serves_requirements=served,
                )
            )

    def _seed_from_kinematics(self, state, km, served: list[str]) -> None:
        """Carry Stage 04's motion, dimensions and open choices forward.

        Stage 04's placeholders are not failures to be hidden: each is a real
        degree of design freedom, and Stage 06 can only resolve one it has been
        told about. They become symbolic parameter commitments, which is what
        makes the parameter system a stated problem rather than an invented one.
        """
        for name, joint in sorted(km.joints.items()):
            if joint.type.value == "fixed":
                continue
            qs = [q for (st, j), q in km.coordinates.items() if j == name]
            state.commit(
                Commitment(
                    kind=CommitmentKind.MOTION,
                    subject=f"motion.{name}",
                    statement=f"{joint.parent} to {joint.child}: {joint.type.value} "
                              f"about {joint.axis}, coordinate spans "
                              f"{min(qs, default=0.0):.3f}..{max(qs, default=0.0):.3f}",
                    roles=["rotating" if joint.type.value == "revolute" else "guided"],
                    symbolic=True,
                    status=CommitmentStatus.SELECTED,
                    provenance=Provenance(requirements=served, method="concept_kinematics"),
                )
            )

        for bname, body in sorted(km.bodies.items()):
            for pname, symbol in sorted(body.solid.params.items()):
                state.commit(
                    Commitment(
                        kind=CommitmentKind.PARAMETER,
                        subject=symbol.name,
                        statement=f"{pname} of {bname}, first cut {symbol.value:g} "
                                  f"({symbol.basis.value})"
                                  + (f"; {symbol.source}" if symbol.source else ""),
                        symbolic=True,
                        value=None if symbol.is_guess else symbol.value,
                        status=(CommitmentStatus.ASSUMED if symbol.is_guess
                                else CommitmentStatus.PROVISIONAL),
                        provenance=Provenance(requirements=served,
                                              method=f"concept_estimate/{symbol.basis.value}"),
                    )
                )

        self._algebraise(state, km, served)

        # A choice Stage 04 recorded as free is an open engineering decision. It
        # must stay visible: resolving it by default here is exactly the silent
        # convention Stage 04 was rebuilt to remove.
        for name, why in sorted(km.free_choices.items()):
            state.open_problem(
                Problem(
                    type=ProblemType.UNDETERMINED,
                    origin=ProblemOrigin.UPSTREAM,
                    entities=[name],
                    phenomenon=f"free_choice_{name}",
                    evaluation_domain="definition",
                    statement=f"{name} is unresolved upstream: {why}",
                    severity=Severity.MEDIUM,
                )
            )

        for name in km.unplaced:
            state.open_problem(
                Problem(
                    type=ProblemType.UNDETERMINED,
                    origin=ProblemOrigin.UPSTREAM,
                    entities=[name],
                    phenomenon=f"unplaced_{name}",
                    evaluation_domain="definition",
                    statement=f"{name} has no derived location; CAD cannot place it",
                    severity=Severity.BLOCKING,
                )
            )

    # -- loop --------------------------------------------------------------
    def _next_problem(self, state: EngineeringWorkingState) -> Problem | None:
        candidates = [p for p in state.open_problems if p.severity != Severity.LOW]
        if not candidates:
            return None
        # Blocking first; then prefer problems whose phenomenon we can actually resolve,
        # so a knowledge gap does not stall progress on the rest of the agenda.
        return min(
            candidates,
            key=lambda p: (
                SEVERITY_ORDER[p.severity],
                0 if p.phenomenon in R.REGISTRY else 1,
                p.id,
            ),
        )

    def _run_checks(self, state: EngineeringWorkingState) -> None:
        for spec in K.CHECKS:
            existing = state.check_by_name(spec.name)
            if existing and existing.is_valid_evidence and not existing.stale:
                continue
            K.run_check(spec, state)

    def _readiness(self, state: EngineeringWorkingState) -> ReadinessReport:
        """The mandatory total closure pass (STAGE_05 section 17)."""
        for spec in K.CHECKS:
            K.run_check(spec, state)

        blocking = state.blocking_problems
        executed, passing, missing, failing = [], [], [], []
        for name in K.MANDATORY:
            k = state.check_by_name(name)
            if k is None or k.result == CheckResult.NOT_RUN:
                missing.append(name)
                continue
            executed.append(name)
            if k.is_satisfied:
                # PASS, or NOT_APPLICABLE because this product class has nothing
                # for the check to evaluate - vacuously satisfied either way.
                passing.append(name)
            else:
                failing.append(f"{name}:{k.result.value}{' (stale)' if k.stale else ''}")

        undetermined = [c.subject for c in state.active if not c.is_determined]
        solvable = state.check_by_name("system_solvable")
        structurally_solvable = bool(solvable and solvable.result == CheckResult.PASS)

        ready = (
            not blocking
            and not missing
            and not failing
            and not undetermined
            and structurally_solvable
        )
        return ReadinessReport(
            ready=ready,
            no_blocking_problems=not blocking,
            mandatory_checks_executed=not missing,
            mandatory_checks_passing=not failing,
            all_commitments_determined=not undetermined,
            system_structurally_solvable=structurally_solvable,
            undetermined=undetermined,
            missing_checks=missing,
            failing_checks=failing,
        )

    def run(
        self,
        *,
        spec: RequirementSpec,
        mechanical: MechanicalArchitecture,
        product: ProductArchitecture,
        concept: ConceptVisualization | None = None,
        kinematic=None,
    ) -> CADReadyEngineeringDefinition:
        state = EngineeringWorkingState()
        ctx = self._context(spec, mechanical)
        self._seed(state, spec, mechanical, product, kinematic)

        seen: Counter[tuple[str, str, str]] = Counter()
        supersessions = 0
        blocked: BlockedReason | None = None
        iterations = 0

        while iterations < self.budget.max_iterations:
            iterations += 1
            self._run_checks(state)

            problem = self._next_problem(state)
            if problem is None:
                break

            seen[problem.key] += 1
            if seen[problem.key] > self.budget.max_repeat:
                blocked = BlockedReason.CYCLIC_RESOLUTION
                state.trace.append(f"iter {iterations}: {problem.id} exceeded repeat budget")
                break

            candidates = R.propose(problem, state, ctx)
            if not candidates:
                # Honest signal: the knowledge base has no rule for this phenomenon.
                problem.severity = Severity.HIGH
                problem.type = ProblemType.UNKNOWN
                problem.statement += " [no resolver in knowledge base]"
                state.trace.append(
                    f"iter {iterations}: no resolver for '{problem.phenomenon}' ({problem.id})"
                )
                if all(
                    p.type == ProblemType.UNKNOWN
                    for p in state.open_problems
                    if p.severity != Severity.LOW
                ):
                    blocked = BlockedReason.INSUFFICIENT_KNOWLEDGE
                    break
                continue

            for c in candidates:
                state.propose(c)
            chosen: Resolution = self.reasoner.propose(
                task=f"resolve {problem.phenomenon} on {problem.entities}",
                context={"problem": problem.statement, "domain": problem.evaluation_domain},
                options=candidates,
            )
            for c in candidates:
                if c.id != chosen.id:
                    c.status = ResolutionStatus.REJECTED
                    c.rejection_reason = f"not selected over {chosen.id}"
            chosen.status = ResolutionStatus.SELECTED

            supersessions += len(chosen.supersedes)
            if supersessions > self.budget.max_supersession:
                blocked = BlockedReason.CYCLIC_RESOLUTION
                state.trace.append(f"iter {iterations}: supersession budget exceeded")
                break

            state.apply(chosen)
            state.trace.append(f"iter {iterations}: {problem.id} <- {chosen.id} ({chosen.approach})")

            for c in chosen.commitments:
                for sp in spawning.spawn_for(c):
                    state.open_problem(sp)
        else:
            blocked = BlockedReason.BUDGET_EXHAUSTED

        # The construction program: what each part is made of, in order, on which
        # face, at what size. Derived here because only Stage 05 has both the
        # topology and the concept poses the faces are derived from.
        characteristic = {
            c.subject: (c.value, c.unit or "length", c.statement)
            for c in state.active
            if c.kind is CommitmentKind.PARAMETER
            and c.provenance and "mechanism_principle" in (c.provenance.method or "")
        }
        self.assembly = (
            build_assembly(kinematic, product, characteristic,
                           scale=getattr(self, "_concept_scale", 1.0))
            if kinematic is not None else None
        )

        readiness = self._readiness(state)
        if blocked:
            readiness.ready = False
            readiness.blocked_reason = blocked
            readiness.recommended_restart = (
                "product_architecture"
                if blocked is BlockedReason.NO_FEASIBLE_PACKAGING
                else "engineering_integration"
            )

        risks: list[str] = [
            f"{p.id}: {p.statement}"
            for p in state.open_problems
            if p.severity in (Severity.MEDIUM, Severity.LOW, Severity.HIGH)
        ]

        return CADReadyEngineeringDefinition(
            meta=ObjectMeta(object_id=new_id("CRED"), producer=self.stage_id),
            working_state=state,
            readiness=readiness,
            iterations=iterations,
            non_blocking_risks=risks,
        )
