"""universal_joint element card + geometry (M18 Tier-1). One element, one file.

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
class UJointDims:
    yoke_d: float = 16.0
    bore_d: float = 8.0
    length: float = 20.0
    angle_deg: float = 20.0     # operating misalignment beta between input/output axes


def ujoint_dims(p: dict) -> UJointDims:
    p = p or {}
    return UJointDims(yoke_d=float(p.get("yoke_d", 16.0)), bore_d=float(p.get("bore_d", 8.0)),
                      length=float(p.get("length", 20.0)), angle_deg=float(p.get("angle_deg", 20.0)))


def ujoint_kinematics(g: UJointDims) -> dict:
    """Cardan joint: for input angle theta and shaft misalignment beta, the output angle obeys
    tan(theta_out) = tan(theta_in)/cos(beta). Velocity ratio fluctuates between cos(beta) and
    1/cos(beta) over a revolution — a single U-joint is NOT constant-velocity (recorded, not a
    defect). axis_relationship = intersecting."""
    beta = math.radians(g.angle_deg)
    ratio_min, ratio_max = math.cos(beta), 1.0 / math.cos(beta)
    return {"beta_deg": g.angle_deg, "vel_ratio_min": round(ratio_min, 4),
            "vel_ratio_max": round(ratio_max, 4),
            "fluctuation_pct": round((ratio_max - ratio_min) * 100.0, 2)}


def ujoint_carve(pieces, inst, bindings) -> CarveResult:
    g = ujoint_dims(getattr(inst, "params", {}) or {})
    p = _anchor_point(pieces, bindings, "shaft_in")
    yoke = Location(Pos(*p)) * (Cylinder(radius=g.yoke_d / 2, height=g.length,
                                         align=(Align.CENTER, Align.CENTER, Align.MIN))
                                - Cylinder(radius=g.bore_d / 2, height=g.length + 2,
                                           align=(Align.CENTER, Align.CENTER, Align.MIN)))
    return CarveResult(parts=_add(pieces, _pid(bindings, "shaft_in"), yoke), tags={"yoke": yoke}, dims=g)


class UniversalJointCard(MechanicalElementCard):
    """Cardan universal joint (P&B §8.1): transmits rotation across INTERSECTING axes at an angle β.
    Not constant-velocity (velocity ratio fluctuates cos β … 1/cos β over a rev — recorded, not a
    defect). V-A verifies the declared angled pair."""
    card_id = "universal_joint"
    has_functional_clearance = False
    taxonomy = {"working_motion": ("rotation", "regular"), "axis_relationship": "intersecting",
                "connection_principle": None, "self_locking": False,
                "emergent_check": EmergentCheck(status="deferred",
                    reason="declared-pair V-A protocol not yet implemented (no rig)",
                    risk="intersecting-axis transmission unverified; the Cardan velocity fluctuation "
                         "(cos beta .. 1/cos beta) is computed by formula but UNOBSERVED in physics; "
                         "D-track pending (D-M19-0)"),
                "compliance": "rigid", "kinematic_dof": "2 revolute (cross) — reserved axis-7"}
    param_bounds = {"yoke_d": (10.0, 30.0, "mm"), "bore_d": (4.0, 16.0, "mm"),
                    "length": (10.0, 50.0, "mm"), "angle_deg": (5.0, 35.0, "deg")}
    ports = [_p("shaft_in", "axis"), _p("shaft_out", "axis")]
    selection_notes = ("Use to transmit rotation between shafts whose axes INTERSECT at an angle "
                       "(axis_relationship=intersecting). Not constant-velocity — a single Cardan "
                       "joint's output speed fluctuates by ±(1/cosβ−cosβ); pair two to cancel it. "
                       "V-A verifies the declared angled pair.")
    citations = [_cit_pb("§8.1", "connections / intersecting-axis transmission")]

    def resolve_params(self, ir, inst):
        out = dict(inst.params or {})
        out.setdefault("angle_deg", 20.0); out.setdefault("bore_d", 8.0); out.setdefault("length", 20.0)
        return out

    def carve(self, host_parts, inst, bindings):
        from knowledge.cards.universal_joint import ujoint_carve
        return ujoint_carve(host_parts, inst, bindings)

    def formula_check(self, inst):
        from knowledge.cards.universal_joint import ujoint_dims, ujoint_kinematics
        return ujoint_kinematics(ujoint_dims(getattr(inst, "params", {}) or {}))

    def verification(self, ir, inst):
        from ontology.schema import Criterion, Observable, VerificationProtocol
        b = next((x for x in ir.behaviors if x.realized_by == inst.id
                  and getattr(x.phase, "value", x.phase) == "use"
                  and getattr(x.motion.kind, "value", x.motion.kind) == "rotation"), None)
        if b is None:
            return []
        return [VerificationProtocol(
            id=f"P-UJOINT-VA-{inst.id}", verifies=b.id, mode="V-A", seeds=5, seed_pass=4,
            actuation={"kind": "shaft_velocity", "n_rev": 3.0},
            criteria=[Criterion(name="transmits_rotation", observable="transmission_residual", op="<=",
                                threshold=0.2, unit="")],   # looser: single Cardan fluctuates by design
            observables=[Observable(name="cv_fluctuation", measured="transmission_residual",
                                    note="single Cardan is NOT constant-velocity (cosβ..1/cosβ)")])]


# --- PassiveFeatureCards (support a DoF; realize nothing) ------------------------------
