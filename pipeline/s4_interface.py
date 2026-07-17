"""Stage ④ Interface design (MECHSYNTH §4-④) — **precedes ⑤ (D6)** — KG query + LLM.

procedure: per behaviour, `kg.candidates()` → LLM selects citing selection_notes → Bindings fixed
(port ↦ anchor + mate + offset_params).

Gate **G4**: V-02, V-03, V-05, V-08; every use behaviour has realized_by; the selection rationale
contains ≥1 citation (auditable design).

This is the stage the whole thesis rests on. The LLM is never asked "how should this be built" — the
KG has already narrowed the field to cards that CAN serve each behaviour, and the model's only job
is to pick among them and say WHY, in the cards' own cited words. Its output is a set of discrete
references (card_ref, port, anchor, mate); not one number, not one coordinate. Everything
dimensional is ⑤'s and ⑥'s.
"""

from __future__ import annotations

from knowledge.cards.base import CARD_REGISTRY
from knowledge.kg import briefing, candidates
from knowledge.templates import TEMPLATES
from ontology.schema import Anchor, Binding, ElementInstance, FeatureInstance, HostTemplate
from ontology.validators import validate_all
from pipeline.fewshot import assert_no_leakage, tsl_interface_example
from pipeline.llm_client import call_structured

MATES = ("coincident_axis", "flush_face", "offset_face", "on_face_uv")

SCHEMA = {
    "type": "object",
    "properties": {
        "elements": {"type": "array", "items": {"type": "object", "properties": {
            "id": {"type": "string"}, "card_ref": {"type": "string"},
            "host_pieces": {"type": "array", "items": {"type": "string"}}},
            "required": ["id", "card_ref", "host_pieces"]}},
        "bindings": {"type": "array", "items": {"type": "object", "properties": {
            "element_id": {"type": "string"}, "port": {"type": "string"},
            "piece_id": {"type": "string"}, "anchor": {"type": "string"},
            "mate": {"type": "string", "enum": list(MATES)},
            "u": {"type": "number"}, "v": {"type": "number"}},
            "required": ["element_id", "port", "piece_id", "anchor", "mate"]}},
        "attributions": {"type": "array", "items": {"type": "object", "properties": {
            "behavior_id": {"type": "string"}, "realized_by": {"type": "string"},
            "imposed_by": {"type": "string"}}, "required": ["behavior_id"]}},
        "rationale": {"type": "string"},
    },
    "required": ["elements", "bindings", "attributions", "rationale"],
}


def _anchor_table(ir) -> str:
    rows = []
    for p in ir.pieces:
        tr = TEMPLATES.get(p.template_ref)
        anchors = list(tr().anchors) if tr else []
        rows.append(f"  {p.id} ({p.role}, {p.template_ref}): {anchors}")
    return "\n".join(rows)


def _kg_block(ir) -> str:
    out = []
    for b in ir.behaviors:
        ph = getattr(b.phase, "value", b.phase)
        k = getattr(b.motion.kind, "value", b.motion.kind)
        out.append(f"## behaviour {b.id} (phase={ph}, motion={k})\n"
                   f"candidate cards (the knowledge graph offers ONLY these): {candidates(b)}\n"
                   f"{briefing(b)}")
    return "\n\n".join(out)


def _prompt(ir) -> str:
    return f"""You choose the MECHANICAL ELEMENTS that realize each behaviour, and bind them to the
pieces' anchors.

# The pieces you must bind to, and the ONLY anchors each one has
{_anchor_table(ir)}

# For each behaviour: the knowledge graph has already narrowed the choice.
You may ONLY use a card_ref from that behaviour's candidate list. Read each card's
selection_notes and choose by its TRADE-OFFS.
{_kg_block(ir)}

# Rules
- One element per behaviour that needs a mechanism. Reuse one element for several behaviours it
  serves (a hinge realizes the opening AND imposes the pin-insertion path — one element, two
  attributions).
- `host_pieces`: the pieces the element touches.
- bindings: one per PORT of each element. `anchor` MUST be one of the target piece's anchors listed
  above — an anchor that is not listed does not exist.
- `mate`: coincident_axis (an axis onto an edge/axis anchor) | flush_face | offset_face | on_face_uv
  If and only if mate=on_face_uv, also give `u` and `v` in [0,1] — where on the face (0.5,0.5 = centre).
- attributions: for every behaviour say which element `realized_by` it (an active mechanism) or
  `imposed_by` it (a constraint the element forces on the design). A behaviour the element MAKES
  HAPPEN is realized_by; one it merely CONSTRAINS is imposed_by.
- `rationale`: why you chose each card over its alternatives. You MUST quote or cite at least one
  citation string from the selection_notes/citations above (e.g. a doc + section).
- element ids are E1, E2, ...; passive-feature ids are F1, F2, ...

# Worked example (a DIFFERENT task)
{tsl_interface_example()}

# Now solve this one
command: "{ir.command}"
Answer with the JSON object only."""


def _all_citation_strings() -> list[str]:
    out = []
    for c in CARD_REGISTRY.values():
        for cit in c.citations:
            out += [cit.doc, cit.section]
    return [s for s in out if s and len(s) > 5]


G4_RULES = ("V-02", "V-03", "V-05", "V-08")     # §4-④ names exactly these



def _build(ir, d):
    """Assemble the LLM's discrete choices into a candidate DesignPlan. Pure structure — not one
    dimension is set here; ⑤ owns every number."""
    out = ir.model_copy(deep=True)
    out.stage_log = ir.stage_log
    tpls = {}
    for p in out.pieces:
        if p.template_ref in TEMPLATES and p.template_ref not in tpls:
            tr = TEMPLATES[p.template_ref]()
            tpls[p.template_ref] = HostTemplate(
                template_ref=p.template_ref, params=dict(tr.params),
                anchors=[Anchor(name=a.name, kind=a.kind) for a in tr.anchors.values()])
    out.templates = list(tpls.values())
    for p in out.pieces:
        if p.template_ref in tpls and not p.params:
            p.params = dict(tpls[p.template_ref].params)
    els, feats = [], []
    for e in d["elements"]:
        card = CARD_REGISTRY.get(e["card_ref"])
        cls = getattr(card, "card_class", "element")
        kw = dict(id=e["id"], card_ref=e["card_ref"], host_pieces=list(e.get("host_pieces", [])),
                  params={})
        (feats if cls == "feature" else els).append(
            FeatureInstance(**kw) if cls == "feature" else ElementInstance(**kw))
    out.elements, out.features = els, feats
    out.bindings = [Binding(element_id=b["element_id"], port=b["port"], piece_id=b["piece_id"],
                            anchor=b["anchor"], mate=b["mate"], offset_params=_offsets(b))
                    for b in d.get("bindings", [])]
    card_of = {e["id"]: e["card_ref"] for e in d["elements"]}
    for a in d.get("attributions", []):
        b = next((x for x in out.behaviors if x.id == a["behavior_id"]), None)
        if not b:
            continue
        if a.get("realized_by"):
            b.realized_by = a["realized_by"]
        if a.get("imposed_by"):
            b.imposed_by = a["imposed_by"]
            b.imposed_by_card = card_of.get(a["imposed_by"])
    _register_imposed(out)
    _provide_hardware(out)
    return out



def _offsets(b: dict) -> dict:
    """offset_params for a binding (§4-④: ④ fixes port ↦ anchor + mate + offset_params).
    V-09 requires u,v in [0,1] for on_face_uv; the face CENTRE is the deterministic default when
    the model does not say, since 'where on the face' is a placement ④ owns and ⑤ may refine."""
    if b.get("mate") != "on_face_uv":
        return {}
    u, v = b.get("u"), b.get("v")
    u = 0.5 if not isinstance(u, (int, float)) or not 0.0 <= u <= 1.0 else float(u)
    v = 0.5 if not isinstance(v, (int, float)) or not 0.0 <= v <= 1.0 else float(v)
    return {"u": u, "v": v}


def _provide_hardware(plan) -> list[str]:
    """D-ONT-11, at ④ exactly as the ruling specifies: "④ instantiates a card's provides_pieces
    into plan.pieces (provenance='hardware', source_element set)".

    Same principle as _register_imposed: the pin exists BECAUSE the LLM chose a hinge, so it is an
    entailment of that choice, not a choice of its own. ③ must not anticipate it (it does not yet
    know a hinge will be picked) and the LLM must not invent it (V-15 would catch an orphan). Code
    derives it from the card's own declaration; ⑤ resolves its params.
    """
    from ontology.schema import Piece
    added = []
    have = {(p.source_element, p.role) for p in plan.pieces if p.provenance == "hardware"}
    n = len(plan.pieces)
    for inst in list(plan.elements):
        card = CARD_REGISTRY.get(inst.card_ref)
        for pp in getattr(card, "provides_pieces", []) or []:
            if (inst.id, pp.role) in have:
                continue
            n += 1
            pid = f"P{n}"
            plan.pieces.append(Piece(id=pid, role=pp.role, provenance="hardware",
                                     source_element=inst.id, params={}))
            added.append(f"{pid} ({pp.role}) hardware <- {inst.id} [{inst.card_ref}]")
    return added


def _register_imposed(plan) -> list[str]:
    """D-E-4: instantiate every card's DECLARED `imposes` constraints as IR behaviours.

    Deterministic, not an LLM decision — and it belongs at ④ specifically. V-08 requires that a card
    which imposes a constraint has a matching behaviour registered "so the constraint cannot be
    silently dropped", but ② cannot produce those behaviours: it does not yet know which cards will
    be chosen (that is ④'s job, and D6 puts ④ after ②). The LLM must not invent them either — they
    are not a choice, they are a MECHANICAL CONSEQUENCE of the card the LLM picked. The card knows
    what it imposes; selecting the card registers it. Picking is the model's; entailment is code's.

    Returns the ids of behaviours added (audited into the stage log).
    """
    from ontology.schema import Behavior, MotionSpec
    added = []
    n = len(plan.behaviors)
    for inst in list(plan.elements) + list(plan.features):
        card = CARD_REGISTRY.get(inst.card_ref)
        if card is None or not card.imposes:
            continue
        for tmpl in card.imposes:
            ph = getattr(tmpl.phase, "value", tmpl.phase)
            kd = getattr(tmpl.motion.kind, "value", tmpl.motion.kind)
            if any(b.imposed_by == inst.id
                   and getattr(b.phase, "value", b.phase) == ph
                   and getattr(b.motion.kind, "value", b.motion.kind) == kd
                   for b in plan.behaviors):
                continue                      # the LLM already attributed one — leave it alone
            n += 1
            bid = f"B{n}"
            plan.behaviors.append(Behavior(
                id=bid, phase=ph,
                motion=MotionSpec(**{k: v for k, v in
                                     tmpl.motion.model_dump().items() if v is not None}),
                imposed_by=inst.id, imposed_by_card=inst.card_ref))
            added.append(f"{bid} ({ph}/{kd}) imposed_by {inst.id} [{inst.card_ref}]")
    return added


def run(ir, ctx=None):
    """④ — returns a copy with elements/features/bindings/templates + behaviour attributions.
    Raises StageFailure('s4','G4').

    The gate calls the REAL validators (V-02/V-03/V-05/V-08 per §4-④) on a candidate plan rather
    than re-implementing their rules here. Re-implementing them was a mistake worth naming: a
    hand-written "V-08" check rejected a behaviour for carrying both realized_by and imposed_by —
    a rule V-08 does not contain — so the model was failed for breaking an invented constraint that
    wore a real rule's name. Validators are the authority on validity; a stage that paraphrases them
    can only drift from them.
    """
    prompt = _prompt(ir)
    assert_no_leakage(prompt)
    allowed = {b.id: set(candidates(b)) for b in ir.behaviors}
    piece_anchors = {p.id: set(TEMPLATES[p.template_ref]().anchors) if p.template_ref in TEMPLATES
                     else set() for p in ir.pieces}

    def parse(d):
        _build(ir, d)          # must be assemblable into a plan at all (pydantic types etc.)
        return d

    def validate(d):
        errs = []
        els = {e["id"]: e for e in d.get("elements", [])}
        if not els:
            return ["no elements produced; every behaviour needing a mechanism must get one"]
        # --- structural checks that must pass before a plan can even be assembled -----------
        offered = set().union(*allowed.values()) if allowed else set()
        for eid, e in els.items():
            if e["card_ref"] not in CARD_REGISTRY:
                errs.append(f"element {eid} uses card_ref={e['card_ref']!r}, which is not a card. "
                            f"Choose from the candidate lists given.")
            elif e["card_ref"] not in offered:
                errs.append(f"element {eid} uses card_ref={e['card_ref']!r}, which the knowledge "
                            f"graph did not offer for ANY behaviour of this task. Allowed: "
                            f"{sorted(offered)}.")
            for pid in e.get("host_pieces", []):
                if pid not in piece_anchors:
                    errs.append(f"element {eid} hosts on {pid!r}, which is not a piece.")
        for b in d.get("bindings", []):
            if b["element_id"] not in els:
                errs.append(f"binding references element {b['element_id']!r} which was not declared.")
        for eid, e in els.items():
            card = CARD_REGISTRY.get(e["card_ref"])
            if not card:
                continue
            bound = {b["port"] for b in d.get("bindings", []) if b["element_id"] == eid}
            missing = [p.name for p in card.ports if p.name not in bound]
            if missing:
                errs.append(f"element {eid} ({e['card_ref']}) has unbound ports {missing}; every "
                            f"port must be bound to an anchor.")
        for a in d.get("attributions", []):
            for key in ("realized_by", "imposed_by"):
                v = a.get(key)
                if v and v not in els:
                    errs.append(f"behaviour {a['behavior_id']}.{key}={v!r} is not a declared element.")
        if errs:
            return errs      # can't build a plan yet; report these first

        # --- the REAL validators, on the assembled candidate plan (G4 = V-02/V-03/V-05/V-08) --
        cand = _build(ir, d)
        for v in validate_all(cand):
            if v.rule in G4_RULES:
                errs.append(f"{v.rule}: {v.detail}")

        # --- the two G4 clauses that are not validator rules ---------------------------------
        attr = {a["behavior_id"]: a for a in d.get("attributions", [])}
        for b in ir.behaviors:
            if getattr(b.phase, "value", b.phase) != "use":
                continue
            a = attr.get(b.id, {})
            if not a.get("realized_by") and not a.get("imposed_by"):
                errs.append(f"G4: use-phase behaviour {b.id} has no realized_by — every use "
                            f"behaviour must be realized by an element.")
        rat = d.get("rationale", "") or ""
        if not any(c.lower() in rat.lower() for c in _all_citation_strings()):
            errs.append("G4: the rationale cites nothing. It must quote at least one citation "
                        "string from the selection_notes/citations shown above (a doc + section), "
                        "so the design decision is auditable.")
        return errs

    d = call_structured(ir=ir, stage="s4", gate="G4", prompt=prompt, schema=SCHEMA,
                        parse=parse, validate=validate)

    out = _build(ir, d)
    out.stage_log.append({"stage": "s4", "attempt": -1, "rationale": d.get("rationale", ""),
                          "kg_candidates": {k: sorted(v) for k, v in allowed.items()},
                          "note": "selection rationale (G4 auditable design)"})
    return out


def viz(ir) -> str:
    """s4_rationale.md — choices + citations (§4-④ viz requirement)."""
    rat = next((r.get("rationale") for r in reversed(ir.stage_log)
                if r.get("stage") == "s4" and r.get("rationale")), "")
    kg = next((r.get("kg_candidates") for r in reversed(ir.stage_log)
               if r.get("stage") == "s4" and r.get("kg_candidates")), {})
    L = ["# Stage ④ — interface design: choices + citations", "",
         "## KG narrowing (what the LLM was allowed to pick from)", "",
         "| behaviour | candidates offered |", "|---|---|"]
    for b, c in (kg or {}).items():
        L.append(f"| {b} | {', '.join(c) or '(none)'} |")
    L += ["", "## Elements chosen", "", "| id | card_ref | host pieces |", "|---|---|---|"]
    for e in list(ir.elements) + list(ir.features):
        L.append(f"| {e.id} | `{e.card_ref}` | {', '.join(e.host_pieces)} |")
    L += ["", "## Bindings (port ↦ anchor)", "",
          "| element | port | piece | anchor | mate |", "|---|---|---|---|---|"]
    for b in ir.bindings:
        L.append(f"| {b.element_id} | {b.port} | {b.piece_id} | {b.anchor} | {b.mate} |")
    L += ["", "## Selection rationale (G4: must cite)", "", rat or "_(none recorded)_"]
    return "\n".join(L) + "\n"
