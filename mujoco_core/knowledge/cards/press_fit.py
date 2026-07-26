"""press_fit element card + geometry (M18 Tier-1). One element, one file.

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
class PressFitDims:
    d_nom: float = 8.0          # nominal interface diameter (mm)
    interference: float = 0.05  # radial interference (mm) — the "compliance boundary" quantity
    length: float = 10.0        # engagement length (mm)
    E: float = 2100.0           # PETG modulus (MPa)
    mu: float = 0.30


def pressfit_dims(p: dict) -> PressFitDims:
    p = p or {}
    return PressFitDims(d_nom=float(p.get("d_nom", 8.0)), interference=float(p.get("interference", 0.05)),
                        length=float(p.get("length", 10.0)), E=float(p.get("E", 2100.0)),
                        mu=float(p.get("mu", 0.30)))


def pressfit_holding(g: PressFitDims) -> dict:
    """FORCE connection via interference (Shigley §3-56 / Roark). Simplified thick-wall-into-rigid
    contact pressure p = E * delta / d (delta = diametral interference = 2*radial); holding (push-out)
    force F = pi * d * L * p * mu. NOTE axis-6 boundary case: this is STATIC interference verified by
    FORMULA, NOT full compliant behaviour — a real PETG press-fit CREEPS (stress relaxation), so the
    formula is an UPPER bound on long-term hold. Flagged honestly (compliance='static_interference')."""
    delta = 2.0 * g.interference                             # diametral interference (mm)
    pressure = g.E * delta / g.d_nom                         # MPa (approx; rigid-hub bound)
    area = math.pi * g.d_nom * g.length                      # mm^2
    holding_N = area * pressure * g.mu
    return {"pressure_MPa": round(pressure, 3), "holding_force_N": round(holding_N, 1),
            "principle": "force", "compliance_note": "static_interference (creeps in PETG — upper bound)"}


def pressfit_carve(pieces, inst, bindings) -> CarveResult:
    g = pressfit_dims(getattr(inst, "params", {}) or {})
    p = _anchor_point(pieces, bindings, "interface")
    plug = Location(Pos(*p)) * Cylinder(radius=g.d_nom / 2, height=g.length,
                                        align=(Align.CENTER, Align.CENTER, Align.MIN))
    return CarveResult(parts=_add(pieces, _pid(bindings, "interface"), plug), tags={"plug": plug}, dims=g)


class PressFitCard(ConnectionCard):
    """Press (interference) fit (P&B §8.1, FORCE connection): holds by radial interference pressure ×
    friction. axis-6 BOUNDARY CASE — this is STATIC INTERFERENCE verified by FORMULA (Shigley §3-56),
    not full compliant behaviour; a real PETG press-fit CREEPS (stress relaxation), so the holding
    formula is an UPPER bound on long-term hold. Flagged honestly (compliance='rigid' at the field;
    the creep caveat lives in the formula + selection_notes, since a P-SPRING protocol isn't built)."""
    card_id = "press_fit"
    has_functional_clearance = False
    connection_principle = "force"
    taxonomy = {"working_motion": ("fixed", "regular"), "axis_relationship": "parallel",
                "connection_principle": "force", "self_locking": False, "emergent_check": EmergentCheck(status="not_applicable"),
                "compliance": "rigid", "kinematic_dof": "fully constrains (interference)",
                "caveat": "static_interference — creeps in PETG (upper-bound hold)"}
    param_bounds = {"d_nom": (3.0, 30.0, "mm"), "interference": (0.01, 0.15, "mm"),
                    "length": (3.0, 30.0, "mm")}
    ports = [_p("interface", "face"), _p("mate", "face")]
    selection_notes = ("Use to FASTEN a pin/bore or shaft/hub by INTERFERENCE (FORCE connection, "
                       "§8.1) — no separate part, no tool. Holding = π·d·L·p·μ with p=E·δ/d "
                       "(Shigley §3-56). CAVEAT (honest): a PETG press-fit CREEPS under sustained "
                       "load (stress relaxation), so the formula is an UPPER bound on long-term hold — "
                       "prefer a screw_boss where a durable clamp matters. axis-6 boundary case: "
                       "static-interference, verified by formula not physics.")
    citations = [_cit_pb("§8.1", "force-closed connection"),
                 Citation(doc="Shigley's", section="§3-56 (interference fits); Roark Table 13.1")]

    def resolve_params(self, ir, inst):
        out = dict(inst.params or {})
        out.setdefault("d_nom", 8.0); out.setdefault("interference", 0.05); out.setdefault("length", 10.0)
        return out

    def carve(self, host_parts, inst, bindings):
        from knowledge.cards.press_fit import pressfit_carve
        return pressfit_carve(host_parts, inst, bindings)

    def formula_check(self, inst):
        from knowledge.cards.press_fit import pressfit_dims, pressfit_holding
        return pressfit_holding(pressfit_dims(getattr(inst, "params", {}) or {}))

    def verification(self, ir, inst):
        return []
