"""screw_boss element card + geometry (M18 Tier-1). One element, one file.

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
class ScrewBossDims:
    screw_d: float = 3.0        # nominal screw diameter (mm)
    engagement: float = 6.0     # thread engagement depth (mm)
    tau_shear: float = 30.0     # PETG shear strength (MPa, conservative)


def screwboss_dims(p: dict) -> ScrewBossDims:
    p = p or {}
    return ScrewBossDims(screw_d=float(p.get("screw_d", 3.0)),
                         engagement=float(p.get("engagement", 6.0)),
                         tau_shear=float(p.get("tau_shear", 30.0)))


def screwboss_design(g: ScrewBossDims) -> dict:
    """FORCE connection (P&B §8.1) via a self-tapping screw. BASF/Bayer boss rules (single PETG, D8):
    boss OD ~ 2.0*screw_d, self-tap pilot hole ~ 0.8*screw_d, engagement >= 2*screw_d. Pull-out force
    = thread shear area * shear strength = pi * d_pilot * engagement * tau (Shigley thread shear)."""
    boss_od = 2.0 * g.screw_d
    pilot_d = 0.8 * g.screw_d
    shear_area = math.pi * pilot_d * g.engagement            # mm^2
    pullout_N = shear_area * g.tau_shear                     # tau in MPa=N/mm^2
    return {"boss_od_mm": round(boss_od, 3), "pilot_d_mm": round(pilot_d, 3),
            "engagement_min_mm": round(2.0 * g.screw_d, 3),
            "pullout_force_N": round(pullout_N, 1), "principle": "force"}


def screwboss_carve(pieces, inst, bindings) -> CarveResult:
    g = screwboss_dims(getattr(inst, "params", {}) or {})
    d = screwboss_design(g)
    p = _anchor_point(pieces, bindings, "boss_mount")
    boss = Location(Pos(*p)) * (Cylinder(radius=d["boss_od_mm"] / 2, height=g.engagement + 4,
                                         align=(Align.CENTER, Align.CENTER, Align.MIN))
                                - Cylinder(radius=d["pilot_d_mm"] / 2, height=g.engagement + 4 + 2,
                                           align=(Align.CENTER, Align.CENTER, Align.MIN)))
    return CarveResult(parts=_add(pieces, _pid(bindings, "boss_mount"), boss),
                       tags={"boss": boss}, dims=g, extra={"provides_screw_d": g.screw_d})


class ScrewBossCard(ConnectionCard):
    """Self-tapping screw boss (P&B §8.1, FORCE connection) — the FIRST force-connection card. A boss
    receives a self-tapping screw (single PETG, D8); the clamp/preload is friction+thread interlock.
    Provides the SCREW as a hardware piece (D-ONT-11) — a ConnectionCard that is ALSO a hardware
    provider (connection-role and hardware-piece are orthogonal, m18 REVIEW §2.2). Static pull-out
    formula (BASF/Bayer boss rules)."""
    card_id = "screw_boss"
    has_functional_clearance = False
    connection_principle = "force"
    taxonomy = {"working_motion": ("fixed", "regular"), "axis_relationship": "parallel",
                "connection_principle": "force", "self_locking": False, "emergent_check": EmergentCheck(status="not_applicable"),
                "compliance": "rigid", "kinematic_dof": "fully constrains (fastened)"}
    param_bounds = {"screw_d": (2.0, 6.0, "mm"), "engagement": (3.0, 20.0, "mm"),
                    "tau_shear": (20.0, 45.0, "MPa")}
    ports = [_p("boss_mount", "face"), _p("clamped", "face")]
    provides_pieces = [ProvidedPiece("screw", ["screw_d", "screw_len"], role="fastener")]
    selection_notes = ("Use to FASTEN two parts with a self-tapping screw into a moulded/printed boss "
                       "(FORCE connection, §8.1). The screw is HARDWARE the card provides (D-ONT-11). "
                       "Bayer boss rules: boss OD≈2·screw_d, pilot≈0.8·screw_d, engagement≥2·screw_d; "
                       "pull-out = π·pilot·engagement·τ_shear. Prefer a dowel_pin if you only need to "
                       "LOCATE (no clamp), or a snap_hook if you want tool-free hand assembly.")
    citations = [_cit_pb("§8.1", "force-closed connection"),
                 Citation(doc="BASF/Bayer Snap-Fit & Boss Design Guide", section="self-tap boss rules"),
                 Citation(doc="DECISIONS_LOG", section="D8 (single-material PETG); D-ONT-11 (hardware)")]

    def resolve_params(self, ir, inst):
        out = dict(inst.params or {})
        out.setdefault("screw_d", 3.0)
        out["engagement"] = round(max(float(out.get("engagement", 0.0)), 2.0 * float(out["screw_d"])), 2)
        out.setdefault("tau_shear", 30.0)
        return out

    def resolve_piece_params(self, name, inst):
        if name != "screw":
            return {}
        d = float((inst.params or {}).get("screw_d", 3.0))
        return {"screw_d": d, "screw_len": round(float((inst.params or {}).get("engagement", 6.0)) + 4.0, 1)}

    def carve(self, host_parts, inst, bindings):
        from knowledge.cards.screw_boss import screwboss_carve
        return screwboss_carve(host_parts, inst, bindings)

    def formula_check(self, inst):
        from knowledge.cards.screw_boss import screwboss_dims, screwboss_design
        return screwboss_design(screwboss_dims(getattr(inst, "params", {}) or {}))

    def verification(self, ir, inst):
        return []
