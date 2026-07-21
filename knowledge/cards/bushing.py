"""bushing element card + geometry (M18 Tier-1). One element, one file.

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


class BushingCard(PassiveFeatureCard):
    """Bushing (P&B §8.2): a low-friction SLEEVE support — a shorter journal, often press-inserted as
    a wear surface. Realizes nothing. Same fit knowledge as the journal_bearing."""
    card_id = "bushing"
    has_functional_clearance = True
    taxonomy = {"working_motion": ("rotation", "regular"), "axis_relationship": "parallel",
                "connection_principle": None, "self_locking": False, "emergent_check": EmergentCheck(status="not_applicable"),
                "compliance": "rigid", "kinematic_dof": "supports 1 revolute (realizes none)"}
    param_bounds = {"bore_d": (3.0, 24.0, "mm"), "wall": (1.0, 4.0, "mm"), "length": (3.0, 24.0, "mm")}
    ports = [_p("bore_mount", "face"), _p("shaft_axis", "axis")]
    selection_notes = ("Use as a low-friction sleeve support / wear surface for a shaft or a sliding "
                       "pin. Realizes nothing (imposed_by). A shorter journal_bearing.")
    citations = [_cit_pb("§8.2", "bearings / guides")]

    def resolve_params(self, ir, inst):
        out = dict(inst.params or {})
        out.setdefault("bore_d", 6.0); out.setdefault("wall", 2.0); out.setdefault("length", 8.0)
        return out

    def carve(self, host_parts, inst, bindings):
        from knowledge.cards.journal_bearing import bearing_carve
        return bearing_carve(host_parts, inst, bindings)

    def collision_hint(self, inst):
        from knowledge.cards.journal_bearing import bearing_collision
        return bearing_collision(inst, cid="bushing")

    def formula_check(self, inst):
        from knowledge.cards.journal_bearing import bearing_dims, bearing_fit
        return bearing_fit(bearing_dims(getattr(inst, "params", {}) or {}))

    def verification(self, ir, inst):
        return []


# --- ConnectionCards (fasten/fix; realize nothing, support no DoF) --------------------
