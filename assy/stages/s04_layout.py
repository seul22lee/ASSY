"""Qualitative layout synthesis for Stage 04.

Stage 04 does not check a layout that arrived from somewhere else. It **derives**
one, in the order the mechanism itself imposes:

    function -> state -> moving/fixed bodies -> axes and corridors
    -> interfaces and engagement -> supports and reaction sites
    -> boundary crossings and access -> constraint-satisfying placement

Every position here follows from a typed mechanical relationship. There is no
role-to-zone table, no default face, no declaration-order alternation: those made
a placement as defensible as any other, which is the same as not deriving it.

The output is a set of qualitative placements over an ordinal axis. A slot is a
*relative* position - "further along the travel than", "at the end of" - not a
coordinate and not a dimension. Two bodies in the same slot are at the same place
along the axis; nothing is said about how far apart anything is.

Where the mechanism constrains a position without fixing it, the choice is made
deterministically **and recorded** as an `UnresolvedLayoutChoice`, so a reader can
see that the layout is one of several equally valid ones rather than the only one.
Where the mechanism contradicts itself, no placement is invented: the conflict is
returned and blocks Stage 05.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

from assy.domain.upstream import (
    Containment,
    ElementClass,
    LayoutConflict,
    MotionKind,
    ObligationKind,
    ProductAxis,
    RadialPosition,
    SpatialRelationKind,
    UnresolvedLayoutChoice,
)

# The ordinal axis. Slot 0 and SLOTS-1 are the extremes of the principal motion;
# everything else is placed relative to them. The count is a resolution, not a
# dimension: it only has to be fine enough to order what the mechanism orders.
SLOTS = 8
LOW, HIGH = 0, SLOTS - 1


@dataclass
class Placement:
    body: str
    containment: Containment = Containment.INTERIOR
    radial: RadialPosition = RadialPosition.ON_AXIS
    lo: int = LOW
    hi: int = HIGH
    axis: ProductAxis = ProductAxis.Z
    derived_from: list[str] = field(default_factory=list)

    @property
    def span(self) -> tuple[int, int]:
        return (self.lo, self.hi)

    def note(self, why: str) -> None:
        if why not in self.derived_from:
            self.derived_from.append(why)


@dataclass
class LayoutResult:
    placements: dict[str, Placement]
    choices: list[UnresolvedLayoutChoice]
    conflicts: list[LayoutConflict]

    @property
    def consistent(self) -> bool:
        return not self.conflicts


class LayoutSynthesizer:
    """Derives a qualitative placement for every body of one architecture."""

    def __init__(self, product, mechanical, frame):
        self.product = product
        self.selected = mechanical.selected
        self.frame = frame
        self.bodies = {
            p.name: p for p in product.pieces if p.element_class is ElementClass.BODY
        }
        self.locals = {
            p.name: p for p in product.pieces if p.element_class is not ElementClass.BODY
        }
        self.constraints = list(self.selected.spatial_constraints)
        self.choices: list[UnresolvedLayoutChoice] = []
        self.conflicts: list[LayoutConflict] = []

    # -- step 3: moving and fixed bodies ------------------------------------
    def _reference_body(self) -> str | None:
        """The body whose motion the product is organised along."""
        if self.frame.primary_element in self.bodies:
            return self.frame.primary_element
        moving = sorted(
            n for n, p in self.bodies.items()
            if p.motion_kind not in (MotionKind.FIXED, MotionKind.UNSPECIFIED)
        )
        return moving[0] if moving else None

    # -- step 7: containment, from crossings and enclosure -------------------
    def _containment(self, placements: dict[str, Placement]) -> None:
        crossing = {
            n for i in self.product.interfaces if i.crosses_boundary for n in i.between
        }
        enclosing = {
            p.name for p in self.bodies.values()
            if "enclosure" in p.engineering_roles
            or "moving_boundary" in p.engineering_roles
            or p.kind.value == "cover"
        }
        user_reached = {
            o.element for o in self.selected.support_obligations
            if o.kind is ObligationKind.USER_ACCESS
        }
        for name, pl in placements.items():
            if name in enclosing:
                pl.containment = Containment.BOUNDARY
                pl.note("carries the enclosure role, so it forms the boundary")
            elif name in crossing:
                pl.containment = Containment.SPANNING
                pl.note("takes part in a boundary-crossing interface")
            elif name in user_reached:
                pl.containment = Containment.EXTERIOR
                pl.note("a user must reach it, so it cannot be sealed inside")
            else:
                pl.containment = Containment.INTERIOR
                pl.note("no crossing or access obligation places it outside")

    # -- steps 4-6: axes, corridors, engagement, reaction sites --------------
    def _propagate(self, placements: dict[str, Placement], reference: str) -> None:
        """Place every body relative to the reference, following the relations.

        Breadth-first from the reference body so a placement is always derived
        from something already placed, never from an ordering of the input.
        """
        placed = {reference}
        frontier = [reference]
        by_pair: dict[tuple[str, str], list] = {}
        for c in self.constraints:
            by_pair.setdefault(tuple(sorted(c.between)), []).append(c)
        # Product-level interfaces are propagation edges too. Stage 03 derives
        # pieces of its own - an aperture, a cover - and a piece reachable only
        # through a product interface would otherwise never be placed.
        for i in self.product.interfaces:
            key = tuple(sorted(i.between))
            if key not in by_pair:
                by_pair[key] = [
                    SimpleNamespace(
                        between=i.between,
                        relation=(
                            SpatialRelationKind.EXTERIOR_REACHABLE
                            if i.crosses_boundary
                            else SpatialRelationKind.MATING_ADJACENCY
                        ),
                        rationale=f"product interface: {i.kind.value}",
                    )
                ]

        # A support of the same kind on one element must not collapse onto its
        # partner. Each successive one takes the opposite free extreme, and the
        # choice is recorded because the mechanism does not distinguish them.
        used_ends: dict[str, list[int]] = {}

        while frontier:
            current = frontier.pop(0)
            neighbours = sorted(
                (k, cs) for k, cs in by_pair.items() if current in k
            )
            for pair, cons in neighbours:
                other = pair[0] if pair[1] == current else pair[1]
                target = self._resolve_body(other, exclude=current)
                if target is None or target in placed:
                    continue
                anchor_pl = placements[current]
                pl = placements[target]
                for c in cons:
                    self._apply(c, current, target, anchor_pl, pl, used_ends)
                placed.add(target)
                frontier.append(target)

        for name, pl in placements.items():
            if name not in placed and name != reference:
                # No derived placement: mark it rather than leave a full-span
                # default that reads as a deliberate position.
                pl.lo, pl.hi = LOW, LOW
                pl.note("UNPLACED: no relation reaches this body from the reference")
                self.choices.append(
                    UnresolvedLayoutChoice(
                        subject=name,
                        question="where does this body sit relative to the mechanism?",
                        options=["anywhere consistent with the enclosure"],
                        blocks_stage05=True,
                        why=(
                            "no declared interface or obligation connects it to the "
                            "chain the reference body belongs to, so no position "
                            "follows from the mechanism"
                        ),
                    )
                )

    def _resolve_body(self, name: str, exclude: str | None = None) -> str | None:
        """A relation naming a joint or feature places the body it grounds into.

        The body on the *far* side of the joint is the one being placed; returning
        the body we came from would make the relation vacuous.
        """
        if name in self.bodies:
            return name
        if name not in self.locals:
            return None
        candidates = []
        for i in self.product.interfaces:
            if name in i.between:
                other = i.between[0] if i.between[1] == name else i.between[1]
                if other in self.bodies and other != exclude:
                    candidates.append(other)
        if not candidates:
            return None
        # Every joint is grounded to the structure, so the structure is always a
        # candidate. Resolving to it would let a guide relation place the shell
        # instead of the member the guide constrains, so a working member wins.
        working = [c for c in candidates if not self._encloses(c)]
        return sorted(working or candidates)[0]

    def _encloses(self, name: str) -> bool:
        body = self.bodies.get(name)
        return bool(body) and "enclosure" in (body.engineering_roles or [])

    def _apply(self, c, source, target, src: Placement, dst: Placement, used_ends) -> None:
        # The structure contains everything, so it spans the whole axis and no
        # pairwise relation may move it. A shell pushed to one end by a mating
        # relation would no longer enclose what it is required to enclose.
        if self._encloses(target):
            dst.lo, dst.hi = LOW, HIGH
            dst.radial = RadialPosition.ON_AXIS
            dst.note("encloses the mechanism, so it spans the whole axis")
            return
        r = c.relation
        if r is SpatialRelationKind.COAXIAL_WORKING_OVERLAP:
            dst.lo, dst.hi = src.lo, src.hi
            dst.radial = RadialPosition.ON_AXIS
            dst.note(f"engaged coaxially with {source} over its working span")
        elif r is SpatialRelationKind.COMMON_TRAVEL_DIRECTION:
            dst.lo, dst.hi = src.lo, src.hi
            dst.radial = RadialPosition.OFF_AXIS
            dst.note(
                f"guides {source} along its whole travel, so it spans the corridor "
                "and sits beside the axis it constrains"
            )
        elif r in (
            SpatialRelationKind.AXIS_SURROUNDED,
            SpatialRelationKind.AXIAL_REACTION_STATION,
        ):
            end = self._free_end(source, used_ends)
            dst.lo = dst.hi = end
            dst.radial = RadialPosition.ON_AXIS
            dst.note(f"transfers a reaction from {source} at an end of its span")
        elif r is SpatialRelationKind.CONTACT_AT_EXTREME:
            end = self._free_end(source, used_ends)
            dst.lo = dst.hi = end
            dst.note(f"acts at an extreme of {source}'s travel")
        elif r is SpatialRelationKind.SHARED_AXIS:
            dst.radial = RadialPosition.ON_AXIS
            dst.lo, dst.hi = src.lo, src.hi
            dst.note(f"shares an axis with {source}")
        elif r is SpatialRelationKind.MATING_ADJACENCY:
            crossing = any(
                i.crosses_boundary and target in i.between
                for i in self.product.interfaces
            )
            if crossing:
                # A member entering through the boundary reaches inward from that
                # end to what it drives; it is not a point at the wall.
                end = self._free_end(source, used_ends)
                if end == LOW:
                    dst.lo, dst.hi = LOW, max(LOW, src.lo)
                else:
                    dst.lo, dst.hi = min(HIGH, src.hi), HIGH
                dst.note(
                    f"enters through the enclosure boundary and reaches in to meet "
                    f"{source}"
                )
            else:
                dst.lo, dst.hi = src.lo, src.hi
                dst.note(f"mates with {source}, so it meets its span")
        elif r is SpatialRelationKind.EXTERIOR_REACHABLE:
            # A boundary opening sits on the surface it breaches, spanning the
            # extent of what it must admit.
            dst.lo, dst.hi = src.lo, src.hi
            dst.note(f"forms the boundary opening through which {source} is reached")
        elif r is SpatialRelationKind.DISJOINT_SWEPT:
            if "enclosure" in (self.bodies[target].engineering_roles or []):
                dst.note(f"encloses {source}'s swept corridor rather than avoiding it")
            else:
                dst.radial = RadialPosition.OFF_AXIS
                dst.note(f"must stay clear of {source}'s swept corridor")

    def _free_end(self, element: str, used_ends: dict[str, list[int]]) -> int:
        """An end of the element's span. Which end the mechanism does not say."""
        used = used_ends.setdefault(element, [])
        end = LOW if LOW not in used else HIGH
        used.append(end)
        if len(used) == 1:
            self.choices.append(
                UnresolvedLayoutChoice(
                    subject=element,
                    question=f"which end of {element}'s span carries this reaction?",
                    options=["the low extreme", "the high extreme"],
                    blocks_stage05=False,
                    why=(
                        "the mechanism requires the reaction to act at an end of the "
                        "span but does not distinguish the two; a further reaction of "
                        "the same kind takes the opposite end"
                    ),
                )
            )
        return end

    # -- step 8: verification ------------------------------------------------
    def _verify(self, placements: dict[str, Placement]) -> None:
        for c in self.constraints:
            a_name = self._resolve_body(c.between[0])
            b_name = self._resolve_body(c.between[1])
            if a_name is None or b_name is None or a_name == b_name:
                continue
            a, b = placements[a_name], placements[b_name]
            ok, detail = True, ""
            if c.relation is SpatialRelationKind.COAXIAL_WORKING_OVERLAP:
                ok = not (a.hi < b.lo or b.hi < a.lo)
                detail = "coaxial members do not overlap on the axis"
            elif c.relation is SpatialRelationKind.COMMON_TRAVEL_DIRECTION:
                ok = b.lo <= a.lo and b.hi >= a.hi or a.lo <= b.lo and a.hi >= b.hi
                detail = "the guide does not span the travel it constrains"
            elif c.relation is SpatialRelationKind.MATING_ADJACENCY:
                ok = not (a.hi < b.lo - 1 or b.hi < a.lo - 1)
                detail = "mating members are separated along the axis"
            elif c.relation is SpatialRelationKind.EXTERIOR_REACHABLE:
                ok = any(
                    p.containment in (Containment.EXTERIOR, Containment.SPANNING,
                                      Containment.BOUNDARY)
                    for p in (a, b)
                )
                detail = "neither element reaches the boundary"
            if not ok:
                self.conflicts.append(
                    LayoutConflict(
                        between=(a_name, b_name),
                        relation=c.relation.value,
                        detail=detail,
                        why=c.rationale,
                    )
                )

    # -- entry point ---------------------------------------------------------
    def synthesize(self) -> LayoutResult:
        placements = {
            name: Placement(body=name, axis=self.frame.primary_axis)
            for name in sorted(self.bodies)
        }
        reference = self._reference_body()
        if reference is None:
            for pl in placements.values():
                pl.note("no moving body defines a principal axis")
            self.choices.append(
                UnresolvedLayoutChoice(
                    subject="product",
                    question="what does the layout organise along?",
                    options=["any axis"],
                    blocks_stage05=True,
                    why="no body declares a motion, so no axis is derivable",
                )
            )
            return LayoutResult(placements, self.choices, self.conflicts)

        ref = placements[reference]
        ref.radial = RadialPosition.ON_AXIS
        body = self.bodies[reference]
        # A body's own extent is not its travel corridor. A translating member
        # occupies the corridor it moves through; a closure swinging about an edge
        # occupies the aperture it covers and sweeps an arc outside it.
        if "moving_boundary" in (body.engineering_roles or []):
            ref.lo = ref.hi = HIGH
            ref.note(
                "closes an aperture, so it occupies that aperture rather than the "
                "corridor it sweeps through when opening"
            )
        else:
            ref.lo, ref.hi = LOW + 1, HIGH - 1
            ref.note(
                f"its {body.motion_kind.value} motion defines the principal axis, "
                "and the corridor it travels is its own extent"
            )
        ref.note(f"its {body.motion_kind.value} motion defines the principal axis")

        self._propagate(placements, reference)
        self._containment(placements)
        self._verify(placements)
        return LayoutResult(placements, self.choices, self.conflicts)
