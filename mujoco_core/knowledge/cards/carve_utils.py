"""Shared carve helpers for the element cards (M18 refactor). Moved verbatim from the former
m18_tier1.py so per-element files import them once instead of duplicating."""

from __future__ import annotations

from dataclasses import dataclass, field

from ontology.schema import Citation


@dataclass
class CarveResult:
    parts: dict                     # piece_id -> build123d solid (host + grown element)
    tags: dict                      # named sub-solids (the element's own geometry)
    dims: object
    extra: dict = field(default_factory=dict)


def _anchor_point(pieces, bindings, port, default=(0.0, 0.0, 0.0)):
    """Best-effort world point of the element's primary anchor; origin if the fixture omits it.
    Tolerant so carve() is testable with a minimal host fixture (Tier-1 needs no deep integration)."""
    b = next((x for x in (bindings or []) if getattr(x, "port", None) == port), None)
    if b is None:
        return default
    pc = (pieces or {}).get(b.piece_id)
    if pc is None:
        return default
    anchors = getattr(pc, "anchors", {}) or {}
    a = anchors.get(b.anchor) if isinstance(anchors, dict) else None
    pos = getattr(a, "position", None) if a is not None else None
    return tuple(pos) if pos is not None else default


def _host_solid(pieces, pid):
    pc = (pieces or {}).get(pid)
    return getattr(pc, "part", pc) if pc is not None else None


def _add(pieces, pid, solid):
    """Add `solid` to host `pid` if present, else return a parts dict with just the element solid."""
    host = _host_solid(pieces, pid)
    out = {k: _host_solid(pieces, k) for k in (pieces or {})}
    out[pid] = (host + solid) if host is not None else solid
    return out


def _pid(bindings, port, default="P1"):
    b = next((x for x in (bindings or []) if getattr(x, "port", None) == port), None)
    return b.piece_id if b is not None else default


def _cit_pb(section, note=""):
    return Citation(doc="Pahl & Beitz, Engineering Design", section=section + (f" — {note}" if note else ""))
