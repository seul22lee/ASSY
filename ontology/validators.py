"""Consistency rules (MECHSYNTH_SPEC §2.5). Every violation raises IRValidationError.

validate(plan) runs all rules and raises on the first failure with the rule id in the message,
so the pipeline's rollback (spec §4) can route on it. validate_all(plan) collects every
violation (used by tests and by a future report view).

Rule set:
  V-01..V-10  per spec §2.5
  V-11        snap_event motion requires an event_force_window_N   (M-S extension)
  V-12        RESERVED (keepout) — stub; see note at the bottom
"""

from __future__ import annotations

from dataclasses import dataclass

from knowledge.cards.base import CARD_REGISTRY
from knowledge.materials import MATERIALS
from ontology.schema import DesignPlan, PhaseE


class IRValidationError(ValueError):
    def __init__(self, rule: str, detail: str):
        self.rule = rule
        self.detail = detail
        super().__init__(f"[{rule}] {detail}")


@dataclass
class Violation:
    rule: str
    detail: str


# --------------------------------------------------------------------------------------
# Individual rules. Each returns a list of Violation (empty = pass).
# --------------------------------------------------------------------------------------
def v01(plan: DesignPlan) -> list[Violation]:
    """Every use-phase Behavior has a verified_by protocol."""
    out = []
    for b in plan.behaviors:
        if b.phase == PhaseE.use and not b.verified_by:
            out.append(Violation("V-01", f"use-phase behavior '{b.id}' has no verified_by"))
        elif b.phase == PhaseE.use and plan.protocol(b.verified_by) is None:
            out.append(Violation("V-01",
                                 f"behavior '{b.id}' verified_by '{b.verified_by}' not found"))
    return out


def v02(plan: DesignPlan) -> list[Violation]:
    """Every Binding's anchor exists in the anchors declared by the target Piece's template."""
    out = []
    for bd in plan.bindings:
        piece = plan.piece(bd.piece_id)
        if piece is None:
            out.append(Violation("V-02", f"binding references unknown piece '{bd.piece_id}'"))
            continue
        tpl = plan.template(piece.template_ref)
        if tpl is None:
            out.append(Violation("V-02",
                                 f"piece '{piece.id}' template '{piece.template_ref}' not in "
                                 f"plan.templates (needed to check anchor '{bd.anchor}')"))
            continue
        names = {a.name for a in tpl.anchors}
        if bd.anchor not in names:
            out.append(Violation("V-02",
                                 f"binding anchor '{bd.anchor}' not declared by template "
                                 f"'{tpl.template_ref}' (has: {sorted(names)})"))
    return out


def v03(plan: DesignPlan) -> list[Violation]:
    """Every Binding's port exists in the ports declared by the (element OR feature) card."""
    out = []
    for bd in plan.bindings:
        inst = plan.instance(bd.element_id)  # element or passive feature (D-ONT-4)
        if inst is None:
            out.append(Violation("V-03",
                                 f"binding references unknown element/feature '{bd.element_id}'"))
            continue
        card = CARD_REGISTRY.get(inst.card_ref)
        if card is None:
            out.append(Violation("V-03", f"'{inst.id}' card '{inst.card_ref}' not registered"))
            continue
        names = {p.name for p in card.ports}
        if bd.port not in names:
            out.append(Violation("V-03",
                                 f"binding port '{bd.port}' not declared by card "
                                 f"'{inst.card_ref}' (has: {sorted(names)})"))
    return out


def v04(plan: DesignPlan) -> list[Violation]:
    """Every Parameter satisfies lo <= value <= hi (after resolution)."""
    out = []
    for p in plan.parameters:
        if p.value is None:
            continue  # unresolved; G5 checks resolution completeness separately
        if not (p.lo <= p.value <= p.hi):
            out.append(Violation("V-04",
                                 f"parameter '{p.name}' value {p.value} outside [{p.lo},{p.hi}]"))
    return out


def v05(plan: DesignPlan) -> list[Violation]:
    """The current Material satisfies each element's card `requires` predicates."""
    out = []
    mat = MATERIALS.get(plan.material)
    if mat is None:
        return [Violation("V-05", f"material '{plan.material}' not in MATERIALS registry")]
    ops = {">=": lambda a, b: a >= b, ">": lambda a, b: a > b,
           "<=": lambda a, b: a <= b, "<": lambda a, b: a < b, "==": lambda a, b: a == b}
    for el in list(plan.elements) + list(plan.features):  # both card classes
        card = CARD_REGISTRY.get(el.card_ref)
        if card is None:
            continue  # reported by V-03
        for prop, (op, threshold) in card.requires.items():
            have = getattr(mat, prop, None)
            if have is None:
                out.append(Violation("V-05",
                                     f"card '{el.card_ref}' requires material.{prop} but "
                                     f"'{mat.name}' has no such property"))
            elif not ops[op](have, threshold):
                out.append(Violation("V-05",
                                     f"card '{el.card_ref}' requires {prop} {op} {threshold}, "
                                     f"but {mat.name}.{prop} = {have}"))
    return out


def v06(plan: DesignPlan) -> list[Violation]:
    """Every rot_to_trans Behavior has a transmission dict."""
    out = []
    for b in plan.behaviors:
        if b.motion.kind == "rot_to_trans" and not b.motion.transmission:
            out.append(Violation("V-06", f"rot_to_trans behavior '{b.id}' has no transmission"))
    return out


def v07(plan: DesignPlan) -> list[Violation]:
    """Every Piece participates in >=1 Binding, or is the base (role=='base' or is_base), OR is a
    HARDWARE piece (D-ONT-11: bound-by-construction to its source element, not via a Binding)."""
    out = []
    bound = {bd.piece_id for bd in plan.bindings}
    for p in plan.pieces:
        if p.id in bound or p.role == "base" or p.is_base or p.provenance == "hardware":
            continue
        out.append(Violation("V-07", f"orphan piece '{p.id}' (no binding, not a base)"))
    return out


def v08(plan: DesignPlan) -> list[Violation]:
    """Behaviors imposed by element/feature cards are registered in the IR, AND passive features
    realize nothing.

    Spans both card classes (D-ONT-4): a MechanicalElement (e.g. snap_hook_cantilever → the lid-sweep
    clearance) or a PassiveFeature (stop_flange → the rotation limit) that imposes a constraint
    declares it, and the IR must contain a matching behaviour tagged imposed_by that instance,
    so the constraint cannot be silently dropped.

    Also enforces the class rule (D-ONT-4): a Behavior.realized_by must point to a
    MechanicalElement, never a PassiveFeature — a passive feature has no `realizes`."""
    out = []
    for inst in list(plan.elements) + list(plan.features):
        card = CARD_REGISTRY.get(inst.card_ref)
        if card is None or not card.imposes:
            continue
        for tmpl in card.imposes:
            match = [b for b in plan.behaviors
                     if b.imposed_by == inst.id and b.phase == tmpl.phase
                     and b.motion.kind == tmpl.motion.kind]
            if not match:
                out.append(Violation("V-08",
                                     f"card '{inst.card_ref}' ('{inst.id}') imposes a "
                                     f"{tmpl.phase.value}/{tmpl.motion.kind} behaviour that is "
                                     f"not registered in the IR"))

    # class rule: realized_by must be a mechanical element, never a passive feature
    feature_ids = {f.id for f in plan.features}
    for b in plan.behaviors:
        if b.realized_by and b.realized_by in feature_ids:
            out.append(Violation("V-08",
                                 f"behaviour '{b.id}' is realized_by '{b.realized_by}', which is "
                                 f"a PassiveFeature — passive features constrain/support but "
                                 f"realize nothing (D-ONT-4). Use imposed_by."))
    return out


def v09(plan: DesignPlan) -> list[Violation]:
    """If mate is on_face_uv, offset_params contains u,v in [0,1]."""
    out = []
    for bd in plan.bindings:
        if bd.mate.value != "on_face_uv":
            continue
        op = bd.offset_params
        for k in ("u", "v"):
            if k not in op:
                out.append(Violation("V-09", f"on_face_uv binding missing offset_params['{k}']"))
            elif not (0.0 <= op[k] <= 1.0):
                out.append(Violation("V-09", f"on_face_uv offset_params['{k}']={op[k]} not in [0,1]"))
    return out


def v10(plan: DesignPlan) -> list[Violation]:
    """DesignPlan JSON serialization round-trips losslessly."""
    try:
        js = plan.model_dump_json()
        back = DesignPlan.model_validate_json(js)
        if back.model_dump() != plan.model_dump():
            return [Violation("V-10", "round-trip changed the model (non-lossless)")]
    except Exception as e:  # noqa: BLE001 — any failure is a V-10 failure
        return [Violation("V-10", f"round-trip raised {type(e).__name__}: {e}")]
    return []


def v11(plan: DesignPlan) -> list[Violation]:
    """M-S: every snap_event motion carries an event_force_window_N (mate/separate window)."""
    out = []
    for b in plan.behaviors:
        if b.motion.kind == "snap_event" and b.motion.event_force_window_N is None:
            out.append(Violation("V-11",
                                 f"snap_event behavior '{b.id}' has no event_force_window_N"))
    return out


def v13(plan: DesignPlan) -> list[Violation]:
    """D-ONT-6: every criterion.observable and observable.measured key is in the measurement
    registry. A criterion whose measured quantity is a free-typed string nobody produces is not
    checkable (the D13 lesson, one level up). The registry is the harness's output contract."""
    from ontology.measurements import is_registered
    out = []
    for proto in plan.protocols:
        for c in proto.criteria:
            if not is_registered(c.observable):
                out.append(Violation("V-13",
                                     f"protocol '{proto.id}' criterion '{c.name}' measures "
                                     f"'{c.observable}', not in the measurement registry"))
        for o in proto.observables:
            if not is_registered(o.measured):
                out.append(Violation("V-13",
                                     f"protocol '{proto.id}' observable '{o.name}' measures "
                                     f"'{o.measured}', not in the measurement registry"))
    return out


def v12(plan: DesignPlan) -> list[Violation]:
    """RESERVED — keepout. Stub.

    Intended: every functional clearance (a bore, a groove) has a declared keep-out region that
    no other piece's geometry may enter, and V-12 will check the IR declares it. This is the
    schema-level home of the M0 bore keep-out finding (a lug ran through the pin's bore). It
    needs a keepout declaration on templates/cards that does not exist yet, so it is a
    deliberate no-op this session, present so the rule number is reserved and the intent is on
    record. See DRAFT decision D-ONT-3.
    """
    return []


def v14(plan: DesignPlan) -> list[Violation]:
    """D-GEN-5 (④ hard constraint): window_catch is legal only on an OWNED, mutable host. A card
    carves only pieces it hosts, and a foreign/RETAINED component is immutable — so a `catch_window`
    binding (a window catch cuts the receiver) may not target a piece with role='retained'. Such a
    host needs an `edge_overhang` catch instead. This is the earliest guard; it is defense-in-depth
    with the ⑥ retained-cut refusal (GEOM_INFEASIBLE) and Tier0 (d) positive_retention. ④ must not
    emit the illegal choice in the first place.

    Negative-test fixture: the board-clip golden (snap_panel: catch_window → retained board B1) is
    rejected here."""
    role = {p.id: p.role for p in plan.pieces}
    out = []
    for b in plan.bindings:
        if b.port == "catch_window" and role.get(b.piece_id) == "retained":
            out.append(Violation(
                "V-14",
                f"element '{b.element_id}' binds a window catch (port 'catch_window') to piece "
                f"'{b.piece_id}', which is RETAINED — a foreign, immutable part. A window catch cuts "
                f"the receiver; a retained component may not be carved. Select an edge_overhang catch "
                f"(D-GEN-5); ④ must not emit a window_catch against a non-owned host."))
    return out


def v15(plan: DesignPlan) -> list[Violation]:
    """D-ONT-11: element ↔ hardware-piece consistency. (a) NO ORPHAN HARDWARE — every hardware
    piece's `source_element` is a real element whose card provides that role; (b) every element
    whose card declares `provides_pieces` has a matching hardware piece instantiated. This is what
    keeps the pin first-class in the IR (D13) while tying it to the element that chose it (④)."""
    from knowledge.cards.base import CARD_REGISTRY
    out = []
    elem_by_id = {e.id: e for e in plan.elements}
    hw = [p for p in plan.pieces if p.provenance == "hardware"]
    for p in hw:                                   # (a) no orphan hardware
        e = elem_by_id.get(p.source_element)
        if e is None:
            out.append(Violation("V-15", f"hardware piece '{p.id}' source_element "
                                          f"'{p.source_element}' is not an element"))
            continue
        card = CARD_REGISTRY.get(e.card_ref)
        roles = {pp.role for pp in getattr(card, "provides_pieces", [])} if card else set()
        if p.role not in roles:
            out.append(Violation("V-15", f"hardware piece '{p.id}' role '{p.role}' is not provided "
                                          f"by element '{e.id}' (card '{e.card_ref}')"))
    for e in plan.elements:                        # (b) every provided piece is instantiated
        card = CARD_REGISTRY.get(e.card_ref)
        for pp in (getattr(card, "provides_pieces", []) if card else []):
            if not any(p.source_element == e.id and p.role == pp.role for p in hw):
                out.append(Violation("V-15", f"element '{e.id}' (card '{e.card_ref}') provides "
                                              f"'{pp.role}' but no hardware piece instantiates it"))
    return out


ALL_RULES = [v01, v02, v03, v04, v05, v06, v07, v08, v09, v10, v11, v12, v13, v14, v15]


def validate_all(plan: DesignPlan) -> list[Violation]:
    """Every violation across all rules (order = rule order). Empty list = valid."""
    out: list[Violation] = []
    for rule in ALL_RULES:
        out.extend(rule(plan))
    return out


def validate(plan: DesignPlan) -> None:
    """Raise IRValidationError on the first violation; return None if the plan is valid."""
    for v in validate_all(plan):
        raise IRValidationError(v.rule, v.detail)
