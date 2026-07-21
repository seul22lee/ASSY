"""coupling element card + geometry (M18 Tier-1). One element, one file.

Card class + cited formulas + carve, moved verbatim from the former base.py + m18_tier1.py
(M18 refactor — no logic change)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field  # noqa: F401

from build123d import Align, Box, Cylinder, Location, Pos  # noqa: F401

from knowledge.cards.base import MechanicalElementCard, ProvidedPiece  # noqa: F401
from knowledge.cards.base import _p
from knowledge.cards.carve_utils import _cit_pb
from ontology.schema import Citation, EmergentCheck  # noqa: F401
from knowledge.cards.carve_utils import CarveResult, _add, _anchor_point, _pid


@dataclass
class CouplingDims:
    bore_d: float = 8.0         # shaft bore (mm)
    body_d: float = 20.0        # coupling OD (mm)
    length: float = 24.0        # axial length (mm)
    tau_allow: float = 25.0     # allowable shear (MPa, PETG conservative)


def coupling_dims(p: dict) -> CouplingDims:
    p = p or {}
    return CouplingDims(bore_d=float(p.get("bore_d", 8.0)), body_d=float(p.get("body_d", 20.0)),
                        length=float(p.get("length", 24.0)), tau_allow=float(p.get("tau_allow", 25.0)))


def coupling_torque(g: CouplingDims) -> dict:
    """Shigley §3-12 torsion: a shaft of diameter d carries T = tau * pi d^3 / 16 at surface shear
    tau. The coupling's capacity is bounded by the smaller (bore) shaft. 1:1, axis_relationship
    parallel/coaxial — input speed = output speed (a coupling adds no ratio)."""
    T = g.tau_allow * math.pi * (g.bore_d ** 3) / 16.0      # N·mm  (tau in MPa=N/mm^2, d in mm)
    return {"torque_capacity_Nmm": round(T, 2), "ratio": 1.0}


def coupling_carve(pieces, inst, bindings) -> CarveResult:
    g = coupling_dims(getattr(inst, "params", {}) or {})
    p = _anchor_point(pieces, bindings, "shaft_in")
    body = Location(Pos(*p)) * (Cylinder(radius=g.body_d / 2, height=g.length,
                                         align=(Align.CENTER, Align.CENTER, Align.MIN))
                                - Cylinder(radius=g.bore_d / 2, height=g.length + 2,
                                           align=(Align.CENTER, Align.CENTER, Align.MIN)))
    return CarveResult(parts=_add(pieces, _pid(bindings, "shaft_in"), body), tags={"coupling": body}, dims=g)


class CouplingCard(MechanicalElementCard):
    """Rigid shaft coupling (P&B §8.1, Shigley §3-12): transmits rotation 1:1 between two COAXIAL /
    parallel shafts, no ratio. A rigid connection between shaft ends — V-A verifies the declared 1:1
    pair (no curved contact)."""
    card_id = "coupling"
    has_functional_clearance = False
    taxonomy = {"working_motion": ("rotation", "regular"), "axis_relationship": "parallel",
                "connection_principle": None, "self_locking": False, "emergent_check": EmergentCheck(status="verified"),
                "compliance": "rigid", "kinematic_dof": "1 revolute (through-transmitted)"}
    param_bounds = {"bore_d": (4.0, 20.0, "mm"), "body_d": (10.0, 40.0, "mm"), "length": (10.0, 60.0, "mm")}
    ports = [_p("shaft_in", "axis"), _p("shaft_out", "axis")]
    selection_notes = ("Use to join two coaxial shafts and transmit rotation 1:1 (no ratio). "
                       "axis_relationship=parallel/coaxial. V-A verifies the declared 1:1 pair.")
    citations = [_cit_pb("§8.1", "connections"), Citation(doc="Shigley's", section="§3-12 (shaft torsion)")]

    def resolve_params(self, ir, inst):
        out = dict(inst.params or {})
        out.setdefault("bore_d", 8.0); out.setdefault("body_d", 20.0); out.setdefault("length", 24.0)
        return out

    def carve(self, host_parts, inst, bindings):
        from knowledge.cards.coupling import coupling_carve
        return coupling_carve(host_parts, inst, bindings)

    def formula_check(self, inst):
        from knowledge.cards.coupling import coupling_dims, coupling_torque
        return coupling_torque(coupling_dims(getattr(inst, "params", {}) or {}))

    def verification(self, ir, inst):
        from ontology.schema import Criterion, VerificationProtocol
        b = next((x for x in ir.behaviors if x.realized_by == inst.id
                  and getattr(x.phase, "value", x.phase) == "use"
                  and getattr(x.motion.kind, "value", x.motion.kind) == "rotation"), None)
        if b is None:
            return []
        return [VerificationProtocol(
            id=f"P-COUPLING-VA-{inst.id}", verifies=b.id, mode="V-A", seeds=5, seed_pass=4,
            actuation={"kind": "shaft_velocity", "n_rev": 3.0, "ratio_expected": 1.0},
            criteria=[Criterion(name="transmits_1to1", observable="transmission_residual", op="<=",
                                threshold=0.05, unit="")], observables=[])]
