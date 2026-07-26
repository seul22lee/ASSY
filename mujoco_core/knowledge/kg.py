"""Mini knowledge graph (MECHSYNTH §3.7) — the narrowing step in front of the LLM at stage ④.

Query API: `candidates(behavior) -> list[card_id]`.

Why it exists: stage ④ must not be "here are all the cards, pick one" — that hands the LLM an open
choice over knowledge it has no grounds to weigh. The KG narrows by the ONE thing the behaviour
objectively states (its phase + motion kind), and the LLM then chooses among the survivors by
reading their `selection_notes` trade-offs and citing them (G4). Narrow-then-justify: the graph
owns what is mechanically possible; the LLM owns which trade-off the task wants.

Gate **G3.2** (§3.7): for every behaviour in both anchor tasks, candidates() must contain the
correct card — pinned by tests/test_kg_candidates.py. If the graph cannot even offer the right
answer, no amount of LLM skill at ④ can recover it.

Edges are (motion kind, phase) → card, each carrying the reason it exists, so a narrowing decision
is auditable the same way a selection is.
"""

from __future__ import annotations

from dataclasses import dataclass

from knowledge.cards.base import CARD_REGISTRY


@dataclass(frozen=True)
class Edge:
    card_id: str
    motion_kind: str          # MotionSpec.kind this card can serve
    phases: tuple[str, ...]   # behaviour phases it is applicable in
    relation: str             # "realizes" | "imposes" | "constrains"
    why: str                  # auditable reason this edge exists


# The graph. Deliberately small and hand-curated: it is knowledge, not a heuristic.
EDGES: tuple[Edge, ...] = (
    Edge("pin_hinge", "rotation", ("use",), "realizes",
         "a pin in a bore is the canonical realizer of a bounded rotation about a fixed axis (§3.3)"),
    Edge("pin_hinge", "translation", ("assembly",), "imposes",
         "the pin-insertion path along the axis is an assembly constraint the hinge imposes (§3.3)"),
    Edge("stop_flange", "rotation", ("use",), "constrains",
         "caps a rotation at a set angle; only meaningful where a rotation already exists (§3.3)"),
    Edge("snap_hook_cantilever", "snap_event", ("assembly", "static", "use"), "realizes",
         "a cantilever beam over a catch is the canonical hand-fastening snap (§3.4, Bayer p.5)"),
    Edge("snap_hook_cantilever", "fixed", ("static", "use"), "realizes",
         "the engaged hook holds two pieces in a fixed relation (retention)"),
    Edge("snap_hook_cantilever", "translation", ("assembly",), "imposes",
         "the hook insertion path must be open — an assembly constraint the latch imposes (§3.4)"),
    Edge("slide_rail", "translation", ("use",), "realizes",
         "a rail/carriage pair is the canonical realizer of straight-line travel (§3.5)"),
    Edge("rack_pinion", "rot_to_trans", ("use",), "realizes",
         "converts rotation to translation at a defined ratio (§3.6); R2b-open — V-A only (D-M1-7)"),
    # --- M18 Tier-1 (D-M18-1/-2/-3) ---------------------------------------------------------------
    Edge("lead_screw", "rot_to_trans", ("use",), "realizes",
         "a power screw converts rotation to translation and SELF-LOCKS when lead angle <= friction "
         "angle (P&B §7.4.3) — the self-locking alternative to rack_pinion (which back-drives)"),
    Edge("coupling", "rotation", ("use",), "realizes",
         "a rigid coupling transmits rotation 1:1 between coaxial/parallel shafts (P&B §8.1)"),
    Edge("universal_joint", "rotation", ("use",), "realizes",
         "a Cardan joint transmits rotation across INTERSECTING axes at an angle (P&B §8.1)"),
    Edge("journal_bearing", "rotation", ("use",), "supports",
         "a journal bearing SUPPORTS a rotating shaft at low friction (P&B §8.2); realizes nothing"),
    Edge("bushing", "rotation", ("use",), "supports",
         "a bushing sleeve supports a rotating/sliding shaft (P&B §8.2); realizes nothing"),
    Edge("dowel_pin", "fixed", ("assembly", "static"), "connects",
         "a dowel LOCATES two parts by FORM interlock (P&B §8.1); removes DoF, realizes none"),
    Edge("screw_boss", "fixed", ("assembly", "static"), "connects",
         "a self-tapping screw boss FASTENS two parts by FORCE (P&B §8.1); provides the screw"),
    Edge("press_fit", "fixed", ("assembly", "static"), "connects",
         "a press-fit FASTENS by interference/FORCE (P&B §8.1); no separate part"),
)


def candidates(behavior, connection_principle: str | None = None) -> list[str]:
    """Card ids that could serve this behaviour, narrowed by (motion.kind, phase), then by the M18
    MORPHOLOGICAL AXES (P&B §3.2.3, Zwicky box): the behaviour's declared axis_relationship /
    self_locking, and an optional connection_principle. This is the morphological-matrix step — a
    requirement is a set of axis values and the matrix keeps the elements that carry them:
        rot_to_trans + self_locking  -> lead_screw (not rack_pinion, which back-drives)
        rotation + intersecting-axis -> universal_joint (not a coupling/hinge)
        fixed + connection_principle=form -> dowel_pin (a form CONNECTION, no DoF)

    Returns [] when the graph knows no card — an HONEST empty (not a fallback to "everything"): an
    empty set at ④ means the ontology cannot express what ② asked for, and must surface as a failure.
    """
    kind = getattr(behavior.motion, "kind", None)
    kind = getattr(kind, "value", kind)          # tolerate str or Enum
    phase = getattr(behavior, "phase", None)
    phase = getattr(phase, "value", phase)
    base = []
    for e in EDGES:
        if e.motion_kind == kind and phase in e.phases and e.card_id not in base:
            base.append(e.card_id)

    # --- M18 morphological narrowing (only fires on a NON-default axis request) -------------------
    req_axis = getattr(behavior, "axis_relationship", "parallel")
    req_axis = getattr(req_axis, "value", req_axis)
    req_lock = bool(getattr(behavior, "self_locking", False))
    cp = connection_principle if connection_principle is not None \
        else getattr(behavior, "connection_principle", None)

    def keep(cid: str) -> bool:
        tax = CARD_REGISTRY[cid].taxonomy or {}
        if req_axis and req_axis != "parallel" and tax.get("axis_relationship", "parallel") != req_axis:
            return False
        if req_lock and not tax.get("self_locking", False):
            return False
        if cp is not None:                       # a connection of a specific principle (form/force/material)
            if CARD_REGISTRY[cid].card_class != "connection" or tax.get("connection_principle") != cp:
                return False
        return True

    return [c for c in base if keep(c)]


def why(card_id: str, behavior) -> list[str]:
    """The auditable reasons the graph offered this card for this behaviour."""
    kind = getattr(behavior.motion, "kind", None); kind = getattr(kind, "value", kind)
    phase = getattr(behavior, "phase", None); phase = getattr(phase, "value", phase)
    return [e.why for e in EDGES
            if e.card_id == card_id and e.motion_kind == kind and phase in e.phases]


def card_brief(cid: str, why_text: str | None = None) -> str:
    """One card's full selection knowledge — ports, an optional 'why offered' line, its
    selection_notes and citations. Behaviour-independent so ④ can emit each distinct card ONCE
    (a catalogue) instead of re-emitting it per behaviour that offers it (D-M16-4 prompt diet)."""
    card = CARD_REGISTRY[cid]
    cites = "; ".join(f"{c.doc} {c.section}" for c in card.citations) or "(none)"
    why_line = f"why offered: {why_text}\n" if why_text else ""
    return (f"### card_ref: {cid}\n"
            f"ports: {[p.name for p in card.ports]}\n"
            f"{why_line}"
            f"selection_notes:\n{card.selection_notes}\n"
            f"citations: {cites}")


def briefing(behavior) -> str:
    """The narrowed choice as stage ④ sees it: the surviving cards with the trade-off text and
    citations the LLM must weigh and cite (G4). This is the whole KG→LLM contract."""
    ids = candidates(behavior)
    if not ids:
        return "(no candidate cards — the knowledge graph knows no realizer for this behaviour)"
    return "\n\n".join(card_brief(cid, "; ".join(why(cid, behavior))) for cid in ids)
