"""Stage ⑥ for a MULTI-ELEMENT assembly (the Easy anchor). Compiles all of a plan's elements onto
its host pieces in the D-ONT-12 carve order — **MOTION elements before FASTENERS** — so a motion
element's geometry + axis exist before a fastener is placed and its AssemblyRules are checked
against the resulting sweep. Hardware pieces (D-ONT-11) get their geometry from the providing
element's carve (the pin from the hinge).

  compile_assembly(plan) -> CompiledAssembly(parts, tags, axes, order)

Card carve order rank (lower = earlier): pin_hinge (motion) < snap_hook_cantilever (fastener) <
passive features. Returns the compiled Solids keyed by piece id, the per-element tagged sub-solids
(for t0/t1/t2), and each motion element's world axis (for t2 and the exclusion sweep).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from knowledge.templates import TEMPLATES

# carve-order rank (D-ONT-12): motion realizers first, then fasteners, then features
CARVE_RANK = {"pin_hinge": 0, "slide_rail": 0, "rack_pinion": 0,
              "snap_hook_cantilever": 1}


@dataclass
class _Piece:
    part: object
    anchors: dict
    params: dict


@dataclass
class CompiledAssembly:
    parts: dict                    # {pid: Solid}
    tags: dict                     # {element_id: {tag: Solid}}
    axes: dict                     # {element_id: {"point","dir"}} for motion elements
    order: list                    # the element ids in carve order
    meta: dict = field(default_factory=dict)


def compile_assembly(plan) -> CompiledAssembly:
    from knowledge.cards.base import CARD_REGISTRY

    pieces = {}
    for pc in plan.pieces:
        if pc.provenance == "hardware":
            continue                               # hardware geometry comes from its source element
        tr = TEMPLATES[pc.template_ref](**{k: v for k, v in pc.params.items() if isinstance(v, (int, float))})
        pieces[pc.id] = _Piece(tr.part, tr.anchors, {**tr.params, **pc.params})

    order = sorted(plan.elements, key=lambda e: CARVE_RANK.get(e.card_ref, 5))
    tags, axes = {}, {}
    for e in order:
        binds = [b for b in plan.bindings if b.element_id == e.id]
        card = CARD_REGISTRY[e.card_ref]
        cr = card.carve(pieces, e, binds)
        # fold edited parts back; different cards return different result shapes
        cr_parts = getattr(cr, "parts", None) or cr["parts"]
        for pid, solid in cr_parts.items():
            if pid in pieces:
                pieces[pid] = _Piece(solid, pieces[pid].anchors, pieces[pid].params)
        tags[e.id] = dict(getattr(cr, "tags", None) or cr.get("tags", {}))
        # motion element: its axis + any hardware pieces it provides
        if hasattr(cr, "axis_world"):
            axes[e.id] = cr.axis_world
        if hasattr(cr, "pin_solid"):
            for pc in plan.pieces:
                if pc.provenance == "hardware" and pc.source_element == e.id:
                    pieces[pc.id] = _Piece(cr.pin_solid, {}, pc.params)

    parts = {pid: pc.part for pid, pc in pieces.items()}
    return CompiledAssembly(parts=parts, tags=tags, axes=axes,
                            order=[e.id for e in order],
                            meta={"n_elements": len(order),
                                  "hardware_pieces": [p.id for p in plan.pieces if p.provenance == "hardware"]})
