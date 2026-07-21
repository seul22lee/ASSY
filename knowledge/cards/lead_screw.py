"""lead_screw element card + geometry (M18 Tier-1). One element, one file.

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
class LeadScrewDims:
    d_major: float = 8.0        # screw major diameter (mm)
    lead: float = 2.0           # axial advance per revolution (mm)
    starts: int = 1             # thread starts
    length: float = 60.0        # threaded length (mm) — bounds the stroke
    stroke: float = 40.0        # design travel (mm)
    mu: float = 0.30            # thread friction (A-PETG-1, R5)


def lead_screw_dims(p: dict) -> LeadScrewDims:
    p = p or {}
    return LeadScrewDims(d_major=float(p.get("d_major", 8.0)), lead=float(p.get("lead", 2.0)),
                         starts=int(p.get("starts", 1)), length=float(p.get("length", 60.0)),
                         stroke=float(p.get("stroke", 40.0)), mu=float(p.get("mu", 0.30)))


def lead_screw_mechanics(g: LeadScrewDims) -> dict:
    """Shigley §8-2 power screw: pitch diameter d_p = d_major - lead/2 (single-start ISO approx);
    lead angle lambda = atan(lead / (pi d_p)); friction angle phi = atan(mu). SELF-LOCKS iff
    lambda <= phi (P&B §7.4.3 self-help). Efficiency eta = tan(lambda)/tan(lambda+phi)."""
    d_p = g.d_major - g.lead / 2.0
    lam = math.atan(g.lead / (math.pi * d_p))               # lead angle (rad)
    phi = math.atan(g.mu)                                    # friction angle (rad)
    self_locks = lam <= phi
    eta = math.tan(lam) / math.tan(lam + phi) if (lam + phi) > 0 else 0.0
    return {"pitch_d_mm": round(d_p, 4), "lead_angle_deg": round(math.degrees(lam), 3),
            "friction_angle_deg": round(math.degrees(phi), 3), "self_locks": bool(self_locks),
            "efficiency": round(eta, 4)}


def lead_screw_carve(pieces, inst, bindings) -> CarveResult:
    g = lead_screw_dims(getattr(inst, "params", {}) or {})
    p = _anchor_point(pieces, bindings, "screw_axis")
    screw = Location(Pos(*p)) * Cylinder(radius=g.d_major / 2.0, height=g.length,
                                         align=(Align.CENTER, Align.CENTER, Align.MIN))
    return CarveResult(parts=_add(pieces, _pid(bindings, "screw_axis"), screw),
                       tags={"screw": screw}, dims=g)


def lead_screw_collision(inst) -> list:
    g = lead_screw_dims(getattr(inst, "params", {}) or {})
    return [{"type": "cylinder", "frame": "world", "owner": "screw",
             "source": f"card:lead_screw@{getattr(inst,'id','?')}",
             "r": g.d_major / 2.0, "h": g.length,
             "note": "coarse cylinder proxy; helical thread flank contact is CURVED -> V-B deferred "
                     "(vb_verifiable=False, cite m17/D-M1-7), like rack_pinion"}]


class LeadScrewCard(MechanicalElementCard):
    """Power lead screw (P&B §7.4.3, Shigley §8-2): converts rotation to translation and — unlike a
    plain rack_pinion — SELF-LOCKS when the lead angle ≤ the friction angle (holds a load with no
    added brake). Resolves the ontology gap D-M13-3: 'holds under load' is now the axis-4
    self_locking field. V-A only: the helical thread flank is CURVED contact, V-B deferred (cite m17
    / D-M1-7), exactly as rack_pinion defers its tooth contact."""
    card_id = "lead_screw"
    has_functional_clearance = True   # thread flank backlash (curved) — V-B deferred, cite m17
    taxonomy = {"working_motion": ("rot_to_trans", "regular"), "axis_relationship": "parallel",
                "connection_principle": None, "self_locking": True, "emergent_check": EmergentCheck(status="deferred", reason="thread contact is curved; rigid-body V-B limit (R2b class, m17)", risk="self-lock verified by formula only (tan(lead)<=mu); actual hold under load not physics-verified — cf. m13 where pawl self-lock needed physics to trust"),
                "compliance": "rigid", "kinematic_dof": "1 rot coupled to 1 trans (reserved axis-7)"}
    param_bounds = {"d_major": (5.0, 20.0, "mm"), "lead": (1.0, 6.0, "mm"), "starts": (1.0, 2.0, "count"),
                    "length": (20.0, 200.0, "mm"), "stroke": (10.0, 180.0, "mm")}
    ports = [_p("screw_axis", "axis"), _p("nut_mount", "face")]
    selection_notes = (
        "Use when ROTATION must become TRANSLATION and the load must HOLD when released without a "
        "brake (a screw-jack, a vice, a leadscrew stage). Realizes a use-phase rot_to_trans that "
        "SELF-LOCKS (axis-4) — the discriminator vs rack_pinion, which back-drives and needs a "
        "pawl_detent (D-M13-4). Self-locks iff lead angle λ=atan(lead/πd_p) ≤ friction angle "
        "φ=atan(μ) (P&B §7.4.3); the cost is low efficiency (η≈0.2 at self-lock).\n"
        "V-A only: the thread flank is curved contact — bidirectional V-B is deferred behind a "
        "preset_v2 (m17/D-M1-7), like rack_pinion. Prefer rack_pinion for fast travel that need not "
        "hold; prefer lead_screw when self-locking hold matters more than speed.")
    citations = [_cit_pb("§7.4.3", "self-help / self-locking"),
                 Citation(doc="Shigley's Mechanical Engineering Design", section="§8-2 Power Screws"),
                 Citation(doc="DECISIONS_LOG", section="D-M13-3 (holds-under-load, now axis-4); m17 (V-B deferred)")]

    def resolve_params(self, ir, inst):
        from knowledge.cards.lead_screw import lead_screw_dims, lead_screw_mechanics
        out = dict(inst.params or {})
        b = next((x for x in ir.behaviors if x.realized_by == inst.id
                  and getattr(x.motion.kind, "value", x.motion.kind) == "rot_to_trans"), None)
        if b is not None and getattr(b.motion, "range_value", None):
            out["stroke"] = float(b.motion.range_value)
        out.setdefault("stroke", 40.0); out.setdefault("d_major", 8.0); out.setdefault("lead", 2.0)
        out.setdefault("length", round(float(out["stroke"]) + 20.0, 1))
        # keep it self-locking if the behaviour asked for it: shrink the lead until λ ≤ φ
        if b is not None and getattr(b, "self_locking", False):
            while not lead_screw_mechanics(lead_screw_dims(out))["self_locks"] and out["lead"] > 1.0:
                out["lead"] = round(out["lead"] - 0.5, 2)
        return out

    def carve(self, host_parts, inst, bindings):
        from knowledge.cards.lead_screw import lead_screw_carve
        return lead_screw_carve(host_parts, inst, bindings)

    def collision_hint(self, inst):
        from knowledge.cards.lead_screw import lead_screw_collision
        return lead_screw_collision(inst)

    def formula_check(self, inst):
        from knowledge.cards.lead_screw import lead_screw_dims, lead_screw_mechanics
        return lead_screw_mechanics(lead_screw_dims(getattr(inst, "params", {}) or {}))

    def verification(self, ir, inst):
        from ontology.schema import Criterion, VerificationProtocol
        b = next((x for x in ir.behaviors if x.realized_by == inst.id
                  and getattr(x.phase, "value", x.phase) == "use"
                  and getattr(x.motion.kind, "value", x.motion.kind) == "rot_to_trans"), None)
        if b is None:
            return []
        stroke = float((inst.params or {}).get("stroke", 40.0))
        return [VerificationProtocol(
            id=f"P-SCREW-VA-{inst.id}", verifies=b.id, mode="V-A", seeds=5, seed_pass=4,
            actuation={"kind": "shaft_velocity", "n_rev": 3.0,
                       "v_b_gap": "helical thread flank is CURVED contact — bidirectional V-B "
                                  "deferred to preset_v2 (m17/D-M1-7), like rack_pinion"},
            criteria=[Criterion(name="reaches_stroke", observable="stroke_mm", op=">=",
                                threshold=stroke, unit="mm"),
                      Criterion(name="self_locks_holds", observable="backdrive_mm", op="<=",
                                threshold=1.0, unit="mm")], observables=[])]
