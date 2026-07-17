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
)


def candidates(behavior) -> list[str]:
    """Card ids that could serve this behaviour, narrowed by (motion.kind, phase).

    Returns [] when the graph knows no card for the behaviour — an HONEST empty, not a fallback to
    "everything". An empty candidate set at ④ is a real signal (the ontology cannot express what ②
    asked for) and must surface as a stage failure rather than be papered over with a guess.
    """
    kind = getattr(behavior.motion, "kind", None)
    kind = getattr(kind, "value", kind)          # tolerate str or Enum
    phase = getattr(behavior, "phase", None)
    phase = getattr(phase, "value", phase)
    out = []
    for e in EDGES:
        if e.motion_kind == kind and phase in e.phases and e.card_id not in out:
            out.append(e.card_id)
    return out


def why(card_id: str, behavior) -> list[str]:
    """The auditable reasons the graph offered this card for this behaviour."""
    kind = getattr(behavior.motion, "kind", None); kind = getattr(kind, "value", kind)
    phase = getattr(behavior, "phase", None); phase = getattr(phase, "value", phase)
    return [e.why for e in EDGES
            if e.card_id == card_id and e.motion_kind == kind and phase in e.phases]


def briefing(behavior) -> str:
    """The narrowed choice as stage ④ sees it: the surviving cards with the trade-off text and
    citations the LLM must weigh and cite (G4). This is the whole KG→LLM contract."""
    ids = candidates(behavior)
    if not ids:
        return "(no candidate cards — the knowledge graph knows no realizer for this behaviour)"
    blocks = []
    for cid in ids:
        card = CARD_REGISTRY[cid]
        cites = "; ".join(f"{c.doc} {c.section}" for c in card.citations) or "(none)"
        blocks.append(f"### card_ref: {cid}\n"
                      f"ports: {[p.name for p in card.ports]}\n"
                      f"why offered: {'; '.join(why(cid, behavior))}\n"
                      f"selection_notes:\n{card.selection_notes}\n"
                      f"citations: {cites}")
    return "\n\n".join(blocks)
