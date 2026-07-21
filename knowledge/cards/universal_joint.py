"""universal_joint element card + geometry (M18 Tier-1; completed to the m19/m20 D-track standard
in m21). One element, one file.

A CARDAN (Hooke) universal joint: transmits rotation between two shafts whose axes INTERSECT at a
bend angle β, through a rigid cross (spider) with two orthogonal pins. It is NOT constant-velocity —
the output speed pulsates twice per revolution; that pulsation is the element's defining EMERGENT
behaviour, and m21 verifies it as physics (P-UJOINT V-A fluctuation overlay), not just formula.
"""

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
    yoke_d: float = 16.0        # yoke outer diameter (mm)
    bore_d: float = 8.0         # shaft bore (mm)
    length: float = 20.0        # yoke axial length (mm)
    angle_deg: float = 20.0     # operating misalignment β between input/output axes (deg)


def ujoint_dims(p: dict) -> UJointDims:
    p = p or {}
    return UJointDims(yoke_d=float(p.get("yoke_d", 16.0)), bore_d=float(p.get("bore_d", 8.0)),
                      length=float(p.get("length", 20.0)), angle_deg=float(p.get("angle_deg", 20.0)))


def ujoint_ratio_at(theta_in: float, beta: float) -> float:
    """Cardan velocity ratio at input angle θ (rad), bend β (rad):
        ω_out/ω_in = cos β / (1 − sin²β · sin²θ)      (Shigley §; P&B §8.1 Hooke joint)
    Min cos β at θ=0,π (yokes in the bend plane), max 1/cos β at θ=π/2,3π/2."""
    return math.cos(beta) / (1.0 - (math.sin(beta) ** 2) * (math.sin(theta_in) ** 2))


def ujoint_position(theta_in: float, beta: float) -> float:
    """Output angle: tan θ_out = cos β · tan θ_in  (quadrant-correct)."""
    return math.atan2(math.cos(beta) * math.sin(theta_in), math.cos(theta_in))


def ujoint_kinematics(g: UJointDims) -> dict:
    """Cardan joint rule chain. For bend β the velocity ratio ω_out/ω_in = cos β/(1−sin²β sin²θ)
    sweeps the band [cos β, 1/cos β] twice per revolution — a single U-joint is NOT constant-velocity
    (this is the element's defining behaviour, recorded + physics-verified in m21, NOT a defect).
    axis_relationship = intersecting (the axis-2 discriminator vs coupling's parallel)."""
    beta = math.radians(g.angle_deg)
    ratio_min, ratio_max = math.cos(beta), 1.0 / math.cos(beta)
    return {"beta_deg": g.angle_deg, "vel_ratio_min": round(ratio_min, 4),
            "vel_ratio_max": round(ratio_max, 4),
            "fluctuation_pct": round((ratio_max - ratio_min) * 100.0, 2),
            "mean_ratio": 1.0}   # mean over a full revolution is exactly 1:1 (it lags then leads)


def ujoint_carve(pieces, inst, bindings) -> CarveResult:
    g = ujoint_dims(getattr(inst, "params", {}) or {})
    p = _anchor_point(pieces, bindings, "shaft_in")
    yoke = Location(Pos(*p)) * (Cylinder(radius=g.yoke_d / 2, height=g.length,
                                         align=(Align.CENTER, Align.CENTER, Align.MIN))
                                - Cylinder(radius=g.bore_d / 2, height=g.length + 2,
                                           align=(Align.CENTER, Align.CENTER, Align.MIN)))
    return CarveResult(parts=_add(pieces, _pid(bindings, "shaft_in"), yoke), tags={"yoke": yoke}, dims=g)


def ujoint_collision(inst) -> list:
    """The input yoke as a coarse cylinder proxy, source-stamped (D-M8-4). The cross/trunnion bearing
    contact (4 pins in bores) is pin-in-bore (pin_hinge class), NOT curved conjugate contact — so the
    emergent gap is a pin-class V-B, not an m17/R2b-curved one (see the card's emergent_check)."""
    g = ujoint_dims(getattr(inst, "params", {}) or {})
    return [{"type": "cylinder", "frame": "world", "owner": "yoke",
             "source": f"card:universal_joint@{getattr(inst,'id','?')}",
             "r": g.yoke_d / 2.0, "h": g.length,
             "note": "coarse yoke proxy; cross-trunnion bearing contact is pin-in-bore (pin_hinge class), "
                     "idealized as frictionless revolutes by the kinematic rig -> pin-class V-B deferred"}]


def _ujoint_imposes() -> list:
    """The U-joint imposes an ASSEMBLY shaft-insertion path (each shaft into its yoke bore along the
    shaft axis), like coupling / lead_screw. Registered + attributed to the element (V-08)."""
    from ontology.schema import Behavior, MotionSpec
    return [Behavior(id="_imposed_shaft_insert", phase="assembly",
                     motion=MotionSpec(kind="translation"))]


class UniversalJointCard(MechanicalElementCard):
    """Cardan universal joint (P&B §8.1, Hooke): transmits rotation across INTERSECTING axes at a bend
    angle β through a rigid cross. NON-constant-velocity — the velocity ratio pulsates cos β … 1/cos β
    twice per rev (the defining emergent behaviour, m21-verified as physics, not a defect). The
    axis_relationship=intersecting field (axis-2) is the discriminator vs coupling (parallel)."""
    card_id = "universal_joint"
    has_functional_clearance = False
    taxonomy = {"working_motion": ("rotation", "regular"), "axis_relationship": "intersecting",
                "connection_principle": None, "self_locking": False,
                "emergent_check": EmergentCheck(status="deferred",
                    reason="the declared angled-pair KINEMATICS — including the emergent Cardan velocity "
                           "fluctuation cos β…1/cos β — IS physics-verified (m21 P-UJOINT V-A: measured "
                           "ω_out/ω_in overlays the formula, and β=0 flattens it). What remains deferred "
                           "is the cross-TRUNNION BEARING CONTACT (4 pins in bores), which the kinematic "
                           "rig idealizes as frictionless revolutes",
                    risk="trunnion bearing friction / backlash / load capacity are untested. NOTE this is "
                         "a PIN-IN-BORE (pin_hinge-class) contact — verifiable in principle (unlike "
                         "lead_screw/rack_pinion's R2b-curved gap); it is 'not run this milestone', "
                         "earnable in a future D-track, NOT a fundamental contact-formulation limit"),
                "compliance": "rigid", "kinematic_dof": "2 revolute (cross) — reserved axis-7"}
    param_bounds = {"yoke_d": (10.0, 30.0, "mm"), "bore_d": (4.0, 16.0, "mm"),
                    "length": (10.0, 50.0, "mm"), "angle_deg": (0.0, 35.0, "deg")}
    ports = [_p("shaft_in", "axis"), _p("shaft_out", "axis"), _p("cross_pivot", "axis")]
    imposes = _ujoint_imposes()      # §8.1: the assembly shaft-insertion path (V-08)
    selection_notes = (
        "Use to transmit rotation between shafts whose axes INTERSECT at an angle β "
        "(axis_relationship=intersecting — the discriminator vs coupling, which joins PARALLEL/coaxial "
        "axes). NOT constant-velocity: a single Cardan joint's output speed fluctuates by the band "
        "[cos β, 1/cos β] twice per rev (P&B §8.1); pair two joints phase-aligned at equal angles to "
        "cancel it (a constant-velocity drive — a future assembly, D-M21-2). V-A verifies the declared "
        "angled pair AND the fluctuation as physics.")
    citations = [_cit_pb("§8.1", "connections / intersecting-axis transmission (Hooke joint)"),
                 Citation(doc="Shigley's Mechanical Engineering Design", section="§ universal joints"),
                 Citation(doc="DECISIONS_LOG", section="D-M21-1 (D-track); D-M20-0b (card-vs-param)")]

    def resolve_params(self, ir, inst):
        from knowledge.cards.universal_joint import ujoint_dims
        out = dict(inst.params or {})
        # β from the behaviour's declared bend, if any (the fixture's intersecting angle)
        b = next((x for x in ir.behaviors if x.realized_by == inst.id
                  and getattr(x, "axis_relationship", "parallel") == "intersecting"), None)
        if b is not None and getattr(b.motion, "transmission", None):
            ang = b.motion.transmission.get("bend_deg")
            if ang is not None:
                out.setdefault("angle_deg", float(ang))
        out.setdefault("angle_deg", 20.0)
        out.setdefault("bore_d", 8.0)
        # FIX (m18 audit): yoke_d used to resolve to None — now every param resolves. Hub proportion:
        # yoke_d ≥ 2·bore (wall to carry the trunnions), enforced.
        bore = float(out["bore_d"])
        out.setdefault("yoke_d", round(max(16.0, 2.0 * bore), 1))
        out["yoke_d"] = round(max(float(out["yoke_d"]), 2.0 * bore), 3)
        out.setdefault("length", 20.0)
        return out

    def carve(self, host_parts, inst, bindings):
        from knowledge.cards.universal_joint import ujoint_carve
        return ujoint_carve(host_parts, inst, bindings)

    def collision_hint(self, inst):
        from knowledge.cards.universal_joint import ujoint_collision
        return ujoint_collision(inst)

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
            actuation={"kind": "shaft_velocity", "n_rev": 3.0,
                       "note": "single Cardan is NOT constant-velocity — the fluctuation is verified as "
                               "physics (measured ω_out/ω_in overlays the formula), not treated as error"},
            criteria=[Criterion(name="transmits_mean_1to1", observable="mean_ratio_residual", op="<=",
                                threshold=0.001, unit=""),
                      Criterion(name="cardan_fluctuation_matches_formula", observable="cardan_fluctuation_residual",
                                op="<=", threshold=0.02, unit="")],
            observables=[Observable(name="cv_fluctuation", measured="cardan_fluctuation_residual",
                                    note="the emergent Cardan pulsation cos β..1/cos β, verified vs formula")])]
