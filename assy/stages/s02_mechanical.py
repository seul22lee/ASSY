"""Stage 02 - Mechanical Architecture Generator.

Question: what mechanical principles could realize the required functions?

**Strict consumer of the Stage 01 contract.** This stage reads only structured
fields. It never reads `source_text`, never pattern-matches over requirement
prose, and never infers a mechanism from a word. `product_intent` is carried
forward as a summary and is not parsed.

If the structured information a geometric synthesis needs is absent, the stage
returns a typed `Stage01ContractDeficiency` naming the missing field and why it is
needed. It does not fall back to reading the request: a silent fallback would hide
the deficiency and rebuild the coupling this rewrite removes.

Boundary: this stage produces *conceptual* architecture only. No dimensions, no
placements, no tolerances, no feature sequences, no CAD.
"""

from __future__ import annotations

from typing import ClassVar

from assy.domain.common import ObjectMeta, Stage, new_id
from assy.domain.upstream import (
    Continuity,
    DeficiencyItem,
    FunctionalPart,
    MechanicalArchitecture,
    MechanicalArchitectureCandidate,
    MechanismRole,
    MotionRelation,
    QuantityKind,
    ArchitectureBound,
    SpatialConstraint,
    Requirement,
    RequirementKind,
    RequirementSpec,
    Stage01ContractDeficiency,
)
from assy.knowledge import mechanisms as cat
from assy.stages.base import PipelineStage

BEHAVIOURAL = (RequirementKind.FUNCTIONAL, RequirementKind.PERFORMANCE)


class MechanicalArchitectureGenerator(PipelineStage):
    stage_id: ClassVar[Stage] = Stage.MECHANICAL
    question: ClassVar[str] = "What mechanical principles could realize the required functions?"
    produces: ClassVar[str] = "MechanicalArchitecture"

    # -- contract inspection ------------------------------------------------
    def _deficiencies(self, spec: RequirementSpec) -> list[DeficiencyItem]:
        """What Stage 02 needs for mechanical and geometric synthesis, and lacks."""
        items: list[DeficiencyItem] = []
        behavioural = [r for r in spec.requirements if r.kind in BEHAVIOURAL]

        if not behavioural:
            items.append(
                DeficiencyItem(
                    missing_field="requirements[kind=functional|performance]",
                    why_stage02_needs_it=(
                        "a mechanism is selected to realize a behaviour; with no behavioural "
                        "requirement there is nothing to realize and no functional chain to build"
                    ),
                    remedy="Stage 01 must record what the product must do (RD-2)",
                )
            )
            return items

        for r in behavioural:
            if r.behaviour is None:
                # Advisory, not blocking: a performance requirement that QUANTIFIES
                # another behaviour (a travel range, a payload) legitimately has no
                # transformation of its own. Its bound still reaches Stage 02, so
                # geometry is unaffected. Blocking here would stop progress for a
                # gap that costs no geometric information.
                quantifies = r.bound is not None
                items.append(
                    DeficiencyItem(
                        missing_field="requirement.behaviour",
                        requirement_id=r.id,
                        why_stage02_needs_it=(
                            "a quantitative bound without a transformation cannot be attached to a "
                            "functional chain; the value is usable but its role is unstated"
                            if quantifies else
                            "the transformation a behaviour performs determines which physical "
                            "principles can realize it and how elements must be arranged"
                        ),
                        remedy="Stage 01 should populate BehaviourSpec, or record this as a constraint",
                        blocking=False,
                    )
                )
                continue
            b = r.behaviour
            if b.input_kind is QuantityKind.NONE and b.output_kind is QuantityKind.NONE:
                items.append(
                    DeficiencyItem(
                        missing_field="requirement.behaviour.input_kind/output_kind",
                        requirement_id=r.id,
                        why_stage02_needs_it=(
                            "both sides of the transformation are unstated, so the behaviour "
                            "constrains no mechanism family and cannot inform arrangement"
                        ),
                        remedy="Stage 01 must state what enters and what results",
                        blocking=False,
                    )
                )

        # BLOCKING condition: no usable transformation anywhere. The product's
        # mechanical purpose is then unknowable from structured output, and no
        # amount of downstream reasoning can recover it.
        usable = [
            r for r in behavioural
            if r.behaviour is not None
            and not (r.behaviour.input_kind is QuantityKind.NONE
                     and r.behaviour.output_kind is QuantityKind.NONE)
        ]
        if not usable:
            items.append(
                DeficiencyItem(
                    missing_field="requirement.behaviour (all behavioural requirements)",
                    why_stage02_needs_it=(
                        "no requirement declares a transformation, so the product's mechanical "
                        "purpose cannot be determined without re-reading the request"
                    ),
                    remedy="Stage 01 must state at least one input->output transformation",
                    blocking=True,
                )
            )
        return items

    # -- candidate construction --------------------------------------------
    def _signature_targets(self, spec: RequirementSpec) -> list[tuple[Requirement, tuple]]:
        """Transformations the product must realize, from structured behaviour only."""
        out = []
        for r in spec.requirements:
            if r.kind in BEHAVIOURAL and r.behaviour is not None:
                b = r.behaviour
                if b.input_kind is QuantityKind.NONE and b.output_kind is QuantityKind.NONE:
                    continue
                out.append((r, (b.input_kind, b.output_kind, b.continuity)))
        return out

    def _candidate(
        self,
        fam: cat.MechanismFamily,
        served: list[str],
        spec: RequirementSpec,
    ) -> MechanicalArchitectureCandidate:
        parts = [
            FunctionalPart(
                id=new_id("FP"),
                name=t.name,
                role=MechanismRole(t.role),
                moving=t.moving,
                engineering_roles=list(t.roles),
                motion_kind=t.motion,
                element_class=t.element_class,
                form=t.form.value,
                permits_motion=t.permits,
                rationale=f"{'moving' if t.moving else 'fixed'} element in the {fam.id} chain",
            )
            for t in fam.roles
        ]
        motions = [
            MotionRelation(
                id=new_id("MO"),
                driver=fam.element_chain[0],
                driven=fam.element_chain[-1],
                relation=f"{fam.input_kind.value}->{fam.output_kind.value}",
                ratio_symbol=fam.continuity.value,
                dof=1,
            )
        ]

        # Freedoms and unknowns are consumed structurally, never parsed for meaning.
        assumptions = list(fam.assumptions)
        if spec.freedoms:
            assumptions.append(
                f"{len(spec.freedoms)} solution choice(s) were left open by the user and are "
                "treated as available to this candidate"
            )
        downstream = list(fam.downstream_decisions)
        for u in spec.unknowns:
            downstream.append(f"unresolved at Stage 01: {u.subject}")

        return MechanicalArchitectureCandidate(
            id=fam.id,
            principle=fam.principle,
            parts=parts,
            motions=motions,
            strengths=list(fam.strengths),
            weaknesses=list(fam.weaknesses),
            risks=list(fam.risks),
            open_questions=list(fam.downstream_decisions),
            serves_requirements=served,
            functions=[
                f.model_copy(deep=True, update={"serves_requirements": served})
                for f in fam.functions
            ],
            element_chain=list(fam.element_chain),
            state_relations=list(fam.state_relations),
            holding_principle=fam.holding_principle,
            support_obligations=[o.model_copy(deep=True) for o in fam.support_obligations],
            spatial_constraints=self._constraints(fam),
            states=[st.model_copy(deep=True) for st in fam.states],
            transitions=[t.model_copy(deep=True) for t in fam.transitions],
            constrained_by=[
                r.id for r in spec.requirements if r.bound is not None
            ],
            bounds=[
                ArchitectureBound(
                    requirement_id=r.id, comparator=r.bound.comparator,
                    lower=r.bound.lower, upper=r.bound.upper,
                    unit=r.bound.unit, precision=r.bound.precision,
                )
                for r in spec.requirements if r.bound is not None
            ],
            load_path=list(fam.load_path),
            interfaces=[i.model_copy(deep=True) for i in fam.interfaces],
            spatial_implications=list(fam.spatial_implications),
            motion_envelopes=list(fam.motion_envelopes),
            tradeoffs=list(fam.tradeoffs),
            assumptions=assumptions,
            downstream_decisions=downstream,
        )

    def _constraints(self, fam: cat.MechanismFamily) -> list[SpatialConstraint]:
        """What the declared interfaces and obligations demand of relative position.

        The demand is mechanical, so it is stated here; whether an arrangement
        honours it is Stage 04's to check.
        """
        out: list[SpatialConstraint] = []
        for i in fam.interfaces:
            row = cat.INTERFACE_RELATION.get(i.kind)
            if row is None:
                continue
            relation, why = row
            out.append(
                SpatialConstraint(
                    between=i.between,
                    relation=relation,
                    source=f"interface:{i.kind.value}",
                    rationale=why,
                )
            )
        for o in fam.support_obligations:
            row = cat.OBLIGATION_RELATION.get(o.kind)
            if row is None or o.reacted_by is None:
                continue
            relation, why = row
            out.append(
                SpatialConstraint(
                    between=(o.element, o.reacted_by),
                    relation=relation,
                    source=f"obligation:{o.kind.value}",
                    rationale=why,
                )
            )
        return out

    def _rank_key(self, fam: cat.MechanismFamily, spec: RequirementSpec) -> tuple:
        """Ordered ranking criteria, most significant first. Higher is better.

        Lexicographic, not a weighted sum. A weighted sum has no tiebreakers: a
        term called one still trades against every term above it, so a candidate
        that satisfies a stated requirement can lose to one that does not simply
        by declaring enough extra elements. Element count now cannot move a
        candidate past anything it is genuinely worse at - it applies only where
        every criterion above is exactly equal, which is what a tiebreaker means.

        The order is the order the criteria are answerable in:

          1. does it do what the requirement asks (holding, reversibility);
          2. can it perform everything it itself declares;
          3. does it need fewer elements to do so.

        Requirement satisfaction outranks self-completeness because a mechanism
        that cannot hold when holding is required has failed the request, whereas
        an unassigned function is an incomplete description of one that has not.

        Requirement priority is deliberately absent: it is a property of the spec,
        identical for every candidate, so it can only inflate scores, never
        discriminate between them.
        """
        needs_hold = any(
            r.behaviour is not None and r.behaviour.continuity is Continuity.HELD
            for r in spec.requirements
        )
        needs_reverse = any(
            r.behaviour is not None and r.behaviour.reversible for r in spec.requirements
        )
        holds = fam.holds is not cat.HoldingCapability.NONE
        return (
            holds if needs_hold else True,
            bool(fam.reversible) if needs_reverse else True,
            -len(fam.unassigned_functions),
            -fam.body_count,
        )

    #: Typed family properties a requirement could discriminate on. Extending the
    #: catalogue with a new engineering property extends this automatically.
    DISCRIMINATING_FIELDS = ("holds", "reversible", "input_kind", "output_kind",
                             "continuity", "body_count")

    def _undecided_fields(self, tied: list[str]) -> list[str]:
        """Typed properties on which equally-ranked candidates genuinely differ.

        Reported rather than resolved. Choosing between them needs a requirement
        that states which property matters; picking one here would be a preference
        presented as a derivation, and re-weighting the ranking until the intended
        candidate wins is the same thing with more arithmetic.
        """
        fams = [cat.by_id(f) for f in tied]
        out = []
        for fld in self.DISCRIMINATING_FIELDS:
            vals = {getattr(f, fld, None) for f in fams}
            if len(vals) > 1:
                shown = ", ".join(
                    f"{f.id}={getattr(getattr(f, fld), 'value', getattr(f, fld))}"
                    for f in fams
                )
                out.append(f"{fld} ({shown})")
        return out

    # -- entry point --------------------------------------------------------
    def run(
        self, *, spec: RequirementSpec
    ) -> MechanicalArchitecture | Stage01ContractDeficiency:
        deficiencies = self._deficiencies(spec)
        if any(d.blocking for d in deficiencies):
            return Stage01ContractDeficiency(
                meta=ObjectMeta(object_id=new_id("DEFICIT"), producer=self.stage_id),
                items=deficiencies,
                source_spec_id=spec.meta.object_id,
            )

        targets = self._signature_targets(spec)
        by_family: dict[str, list[str]] = {}
        for req, (ik, ok, cont) in targets:
            fams = cat.families_for(ik, ok, cont) or cat.families_for_transform(ik, ok)
            for fam in fams:
                by_family.setdefault(fam.id, []).append(req.id)

        if not by_family:
            sigs = sorted({f"{ik.value}->{ok.value}/{c.value}" for _, (ik, ok, c) in targets})
            return Stage01ContractDeficiency(
                meta=ObjectMeta(object_id=new_id("DEFICIT"), producer=self.stage_id),
                items=[
                    DeficiencyItem(
                        missing_field="mechanism family for the declared transformation",
                        why_stage02_needs_it=(
                            f"no catalogued family realizes {', '.join(sigs)}; the knowledge "
                            "base cannot answer the engineering question for this behaviour"
                        ),
                        remedy="extend the mechanism catalogue, or correct the declared transformation",
                    )
                ],
                source_spec_id=spec.meta.object_id,
            )

        candidates = [
            self._candidate(cat.by_id(fid), sorted(set(served)), spec)
            for fid, served in by_family.items()
        ]
        keys = {c.id: self._rank_key(cat.by_id(c.id), spec) for c in candidates}
        # Sorted by id under the key so the arbitrary case is at least stable and
        # never depends on the order families happen to appear in the catalogue.
        ordered = sorted(candidates, key=lambda c: (keys[c.id], c.id), reverse=True)
        best = ordered[0]
        # Candidates the criteria rank exactly equal are not ranked at all. Naming
        # one of them is a pick, and it has to say so rather than borrow the
        # authority of the ranking that did not separate them.
        tied = sorted(c.id for c in candidates if keys[c.id] == keys[best.id])
        undecided = tied if len(tied) > 1 else []
        # A tie is not a scoring problem to be weighted away. These candidates are
        # mechanically different and the requirement does not say which difference
        # matters, so the missing discriminator is a requirement field. Name the
        # typed properties they actually differ on: that is precisely what the
        # requirement would have to state for the choice to become derivable.
        discriminators = self._undecided_fields(undecided) if undecided else []

        return MechanicalArchitecture(
            meta=ObjectMeta(object_id=new_id("MECH"), producer=self.stage_id),
            candidates=candidates,
            selected_id=best.id,
            selection_rationale=(
                "selected from structured behaviour signatures "
                + ", ".join(sorted({f"{ik.value}->{ok.value}/{c.value}" for _, (ik, ok, c) in targets}))
                + "; ranked lexicographically on holding need, reversibility, "
                + f"unperformed functions and element count: {keys}"
                + (
                    "; NOT DERIVED - these rank exactly equal on every criterion "
                    f"and {best.id} is an arbitrary stable pick among them: "
                    + ", ".join(undecided)
                    if undecided else ""
                )
            ),
            undecided_between=undecided,
            rejected={
                c.id: f"ranks {keys[c.id]} below {best.id} ({keys[best.id]})"
                + (
                    "; does not itself perform: "
                    + ", ".join(cat.by_id(c.id).unassigned_functions)
                    if cat.by_id(c.id).unassigned_functions
                    else (f"; {c.weaknesses[0]}" if c.weaknesses else "")
                )
                for c in candidates
                if c.id != best.id
            },
            contract_advisories=[
                f"{d.requirement_id or '-'}: {d.missing_field} — {d.why_stage02_needs_it}"
                for d in deficiencies
            ] + [
                f"-: {fld} — candidates {', '.join(undecided)} rank equal on every "
                "criterion but differ here; the requirement does not state which "
                "is needed, so the selection is a pick rather than a derivation"
                for fld in discriminators
            ],
        )
