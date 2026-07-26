"""journal_bearing element card + geometry (M18 Tier-1). One element, one file.

Card class + cited formulas + carve, moved verbatim from the former base.py + m18_tier1.py
(M18 refactor — no logic change)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field  # noqa: F401

from build123d import Align, Box, Cylinder, Location, Pos  # noqa: F401

from knowledge.cards.base import PassiveFeatureCard, ProvidedPiece  # noqa: F401
from knowledge.cards.base import _p
from knowledge.cards.carve_utils import _cit_pb
from ontology.schema import Citation, EmergentCheck  # noqa: F401
from knowledge.cards.carve_utils import CarveResult, _add, _anchor_point, _pid


@dataclass
class BearingDims:
    bore_d: float = 8.0         # shaft diameter it supports (mm)
    wall: float = 3.0           # bearing wall (mm)
    length: float = 10.0        # axial length (mm)
    clearance: float = 0.0      # running clearance (mm) — resolved from bore


def bearing_dims(p: dict) -> BearingDims:
    p = p or {}
    return BearingDims(bore_d=float(p.get("bore_d", 8.0)), wall=float(p.get("wall", 3.0)),
                       length=float(p.get("length", 10.0)), clearance=float(p.get("clearance", 0.0)))


def bearing_fit(g: BearingDims) -> dict:
    """Shigley §12 rule of thumb: a running (journal) clearance ~ d/1000, floored at the PETG print
    clearance so the fit is printable. The bearing SUPPORTS a rotation; it realizes nothing."""
    from knowledge.materials import PETG
    c = max(g.bore_d / 1000.0, PETG.print_clearance_mm)
    return {"running_clearance_mm": round(c, 4), "bore_id_mm": round(g.bore_d + c, 4),
            "outer_d_mm": round(g.bore_d + c + 2 * g.wall, 4)}


def bearing_carve(pieces, inst, bindings, port="bore_mount") -> CarveResult:
    g = bearing_dims(getattr(inst, "params", {}) or {})
    f = bearing_fit(g)
    p = _anchor_point(pieces, bindings, port)
    tube = Location(Pos(*p)) * (Cylinder(radius=f["outer_d_mm"] / 2, height=g.length,
                                         align=(Align.CENTER, Align.CENTER, Align.MIN))
                                - Cylinder(radius=f["bore_id_mm"] / 2, height=g.length + 2,
                                           align=(Align.CENTER, Align.CENTER, Align.MIN)))
    return CarveResult(parts=_add(pieces, _pid(bindings, port), tube), tags={"sleeve": tube}, dims=g)


def bearing_collision(inst, cid="journal_bearing", port="bore_mount") -> list:
    g = bearing_dims(getattr(inst, "params", {}) or {})
    f = bearing_fit(g)
    return [{"type": "cylinder", "frame": "world", "owner": "sleeve",
             "source": f"card:{cid}@{getattr(inst,'id','?')}",
             "r": f["outer_d_mm"] / 2, "h": g.length, "bore_r": f["bore_id_mm"] / 2,
             "note": "running-clearance bore; convex tube (exact, no swallow) — D18/D21"}]


class JournalBearingCard(PassiveFeatureCard):
    """Journal (plain) bearing (P&B §8.2): a low-friction bore that SUPPORTS a rotating shaft. It
    realizes nothing (V-08). Generalises pin_hinge's bore. Static/optional-V-A; running clearance is
    a functional clearance → collision_hint (D18/D21), an exact convex tube."""
    card_id = "journal_bearing"
    has_functional_clearance = True
    taxonomy = {"working_motion": ("rotation", "regular"), "axis_relationship": "parallel",
                "connection_principle": None, "self_locking": False, "emergent_check": EmergentCheck(status="not_applicable"),
                "compliance": "rigid", "kinematic_dof": "supports 1 revolute (realizes none)"}
    param_bounds = {"bore_d": (3.0, 30.0, "mm"), "wall": (1.5, 6.0, "mm"), "length": (4.0, 40.0, "mm")}
    ports = [_p("bore_mount", "face"), _p("shaft_axis", "axis")]
    selection_notes = ("Use to SUPPORT a rotating shaft at low friction (a journal). Realizes "
                       "nothing (imposed_by, never realized_by). Running clearance ≈ d/1000, floored "
                       "at the print clearance so it is printable (Shigley §12).")
    citations = [_cit_pb("§8.2", "bearings / guides"), Citation(doc="Shigley's", section="§12 (journal bearings)")]

    def resolve_params(self, ir, inst):
        out = dict(inst.params or {})
        out.setdefault("bore_d", 8.0); out.setdefault("wall", 3.0); out.setdefault("length", 10.0)
        return out

    def carve(self, host_parts, inst, bindings):
        from knowledge.cards.journal_bearing import bearing_carve
        return bearing_carve(host_parts, inst, bindings)

    def collision_hint(self, inst):
        from knowledge.cards.journal_bearing import bearing_collision
        return bearing_collision(inst, cid="journal_bearing")

    def formula_check(self, inst):
        from knowledge.cards.journal_bearing import bearing_dims, bearing_fit
        return bearing_fit(bearing_dims(getattr(inst, "params", {}) or {}))

    def verification(self, ir, inst):
        return []   # a passive support realizes nothing → no protocol of its own (like stop_flange)
