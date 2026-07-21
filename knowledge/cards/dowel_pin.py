"""dowel_pin element card + geometry (M18 Tier-1). One element, one file.

Card class + cited formulas + carve, moved verbatim from the former base.py + m18_tier1.py
(M18 refactor — no logic change)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field  # noqa: F401

from build123d import Align, Box, Cylinder, Location, Pos  # noqa: F401

from knowledge.cards.base import ConnectionCard, ProvidedPiece  # noqa: F401
from knowledge.cards.base import _p
from knowledge.cards.carve_utils import _cit_pb
from ontology.schema import Citation, EmergentCheck  # noqa: F401
from knowledge.cards.carve_utils import CarveResult, _add, _anchor_point, _pid


@dataclass
class DowelDims:
    pin_d: float = 4.0
    length: float = 12.0
    fit_clearance: float = 0.02     # H7/g6-style locational clearance (mm)


def dowel_dims(p: dict) -> DowelDims:
    p = p or {}
    return DowelDims(pin_d=float(p.get("pin_d", 4.0)), length=float(p.get("length", 12.0)),
                     fit_clearance=float(p.get("fit_clearance", 0.02)))


def dowel_fit(g: DowelDims) -> dict:
    """FORM connection (P&B §8.1): geometric interlock, no load path through friction. A dowel LOCATES
    two parts (removes in-plane DoF) with a tight locational fit; verified STATICALLY (t0: the bore
    receives the pin with a small positive clearance, no interference)."""
    return {"bore_d_mm": round(g.pin_d + g.fit_clearance, 4), "principle": "form",
            "locates_dof": "2 in-plane translations (a single dowel); a pair also fixes rotation"}


def dowel_carve(pieces, inst, bindings) -> CarveResult:
    g = dowel_dims(getattr(inst, "params", {}) or {})
    p = _anchor_point(pieces, bindings, "location")
    pin = Location(Pos(*p)) * Cylinder(radius=g.pin_d / 2, height=g.length,
                                       align=(Align.CENTER, Align.CENTER, Align.MIN))
    return CarveResult(parts=_add(pieces, _pid(bindings, "location"), pin), tags={"dowel": pin}, dims=g)


class DowelPinCard(ConnectionCard):
    """Dowel pin (P&B §8.1, FORM connection): LOCATES two parts by geometric interlock — removes
    in-plane DoF, transmits no load through friction. Static t0 check (bore receives pin, no
    interference). Provides no separate hardware piece (the dowel IS the located feature)."""
    card_id = "dowel_pin"
    has_functional_clearance = False
    connection_principle = "form"
    taxonomy = {"working_motion": ("fixed", "regular"), "axis_relationship": "parallel",
                "connection_principle": "form", "self_locking": False, "emergent_check": EmergentCheck(status="not_applicable"),
                "compliance": "rigid", "kinematic_dof": "removes 2 in-plane translations"}
    param_bounds = {"pin_d": (2.0, 10.0, "mm"), "length": (5.0, 30.0, "mm"),
                    "fit_clearance": (0.0, 0.1, "mm")}
    ports = [_p("location", "point"), _p("mate", "point")]
    selection_notes = ("Use to LOCATE two parts precisely with no degree of freedom (align a lid to "
                       "a box, register two plates). FORM connection (geometric interlock, §8.1). A "
                       "single dowel removes 2 in-plane translations; a pair also fixes rotation. "
                       "Static — checked by t0 fit, not physics.")
    citations = [_cit_pb("§8.1", "form-closed connection")]

    def resolve_params(self, ir, inst):
        out = dict(inst.params or {})
        out.setdefault("pin_d", 4.0); out.setdefault("length", 12.0); out.setdefault("fit_clearance", 0.02)
        return out

    def carve(self, host_parts, inst, bindings):
        from knowledge.cards.dowel_pin import dowel_carve
        return dowel_carve(host_parts, inst, bindings)

    def formula_check(self, inst):
        from knowledge.cards.dowel_pin import dowel_dims, dowel_fit
        return dowel_fit(dowel_dims(getattr(inst, "params", {}) or {}))

    def verification(self, ir, inst):
        return []
