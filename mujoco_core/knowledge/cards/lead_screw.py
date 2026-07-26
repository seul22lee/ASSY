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
    pitch: float = 2.0          # thread pitch (axial distance between adjacent threads, mm)
    starts: int = 1             # thread starts
    lead: float = 2.0           # axial advance per revolution (mm) = starts * pitch  (rule chain)
    length: float = 60.0        # threaded length (mm) — bounds the stroke
    stroke: float = 40.0        # design travel (mm)
    mu: float = 0.30            # thread friction (A-PETG-1, R5 preset value)


def lead_screw_dims(p: dict) -> LeadScrewDims:
    """RULE CHAIN (Shigley §8-2): lead = starts × pitch. `lead` may be given directly (m18 back-compat)
    or DERIVED from starts×pitch; pitch is inferred from lead/starts when only lead is supplied."""
    p = p or {}
    starts = int(p.get("starts", 1))
    lead = p.get("lead")
    pitch = p.get("pitch")
    if lead is None:                                        # derive lead from the rule chain
        lead = starts * float(pitch if pitch is not None else 2.0)
    lead = float(lead)
    if pitch is None:                                       # infer pitch when only lead was given
        pitch = lead / starts
    return LeadScrewDims(d_major=float(p.get("d_major", 8.0)), pitch=float(pitch), starts=starts,
                         lead=lead, length=float(p.get("length", 60.0)),
                         stroke=float(p.get("stroke", 40.0)), mu=float(p.get("mu", 0.30)))


def lead_screw_mechanics(g: LeadScrewDims) -> dict:
    """Shigley §8-2 power screw rule chain:
      lead          = starts × pitch                         (advance per revolution)
      travel_per_rev = lead                                  (the transmission the IR carries, mm/rev)
      d_mean        = d_major − pitch/2                      (single-thread mean diameter)
      lead angle λ  = atan(lead / (π · d_mean))
      friction angle φ = atan(µ)
      SELF-LOCKS iff tan(λ) ≤ µ  ⇔  λ ≤ φ                    (P&B §7.4.3 self-help)
      efficiency η  = tan(λ) / tan(λ+φ)
    A self-locking screw HOLDS a released load with no brake (the axis-4 discriminator vs rack_pinion)."""
    d_mean = g.d_major - g.pitch / 2.0
    lam = math.atan(g.lead / (math.pi * d_mean))            # lead angle (rad)
    phi = math.atan(g.mu)                                   # friction angle (rad)
    self_locks = math.tan(lam) <= g.mu                      # tan(λ) ≤ µ (Shigley self-lock criterion)
    eta = math.tan(lam) / math.tan(lam + phi) if (lam + phi) > 0 else 0.0
    return {"lead_mm": round(g.lead, 4), "travel_per_rev_mm": round(g.lead, 4),
            "d_mean_mm": round(d_mean, 4), "lead_angle_deg": round(math.degrees(lam), 3),
            "friction_angle_deg": round(math.degrees(phi), 3), "tan_lambda": round(math.tan(lam), 5),
            "self_locks": bool(self_locks), "efficiency": round(eta, 4)}


# --- REQUIREMENT-DRIVEN SIZING (⑤ designs from the declared load, not a default lookup) --------------
# Design shear stress for a SUSTAINED-load FDM PETG screw. Bulk shear yield ≈ 0.5·σ_y = 25 MPa (Tresca,
# σ_y=50), but a printed screw HOLDING a load long-term is limited by INTERLAYER adhesion + CREEP, both
# large knockdowns for FDM — a design shear ~ σ_y/12 ≈ 4 MPa is the sustained-load allowable. ASSUMPTION
# (gate G-S4, parallels EPS_PERM/Es_secant): replace with a PETG shear-creep datasheet.
TAU_DESIGN_MPA = 4.0
SIZING_SF = 2.0


def size_d_major_from_load(W_N: float, mu: float = 0.30, tau: float = TAU_DESIGN_MPA,
                           sf: float = SIZING_SF) -> float:
    """Size the screw major diameter from the axial load W by the DRIVE-TORQUE torsional shear on the
    core (the honest failure path for a plastic jack screw):
        raise torque   T = (W·d_mean/2)·(tan λ + µ)/(1 − µ·tan λ)              [Shigley §8-1]
        at self-lock   (tan λ → µ)   the factor F = 2µ/(1 − µ²)               (worst self-locking case)
        core torsion   τ = 16·T/(π·d³) ≤ τ_design/SF                           [Shigley §3-12]
    Substituting d_mean ≈ d and solving:  d = sqrt( 16·(F/2)·W·SF / (π·τ) ).  Returns d_major in mm.
    (Inverse of the m19 forward mechanics; the SAME requirement→dimension move as the m24 snap CLIP,
    which inverted the Bayer chain to a target W_out — D-M24-5.)"""
    F = 2.0 * mu / (1.0 - mu * mu)
    return math.sqrt(16.0 * (F / 2.0) * W_N * sf / (math.pi * tau))


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


def _lead_screw_imposes() -> list:
    """The lead screw imposes an ASSEMBLY threading path: the nut is threaded onto the screw along
    the screw axis (an axial insertion), so that axis must stay open for assembly (§8-2 / like the
    rack_pinion mesh-insertion, pin_hinge pin-path). Registered + attributed to the element (V-08)."""
    from ontology.schema import Behavior, MotionSpec
    return [Behavior(id="_imposed_thread_path", phase="assembly",
                     motion=MotionSpec(kind="translation"))]


class LeadScrewCard(MechanicalElementCard):
    """Power lead screw (P&B §7.4.3, Shigley §8-2): converts rotation to translation and — unlike a
    plain rack_pinion — SELF-LOCKS when the lead angle ≤ the friction angle (holds a load with no
    added brake). Resolves the ontology gap D-M13-3: 'holds under load' is now the axis-4
    self_locking field. V-A only: the helical thread flank is CURVED contact, V-B deferred (cite m17
    / D-M1-7), exactly as rack_pinion defers its tooth contact."""
    card_id = "lead_screw"
    has_functional_clearance = True   # thread flank backlash (curved) — V-B deferred, cite m17
    taxonomy = {"working_motion": ("rot_to_trans", "regular"), "axis_relationship": "parallel",
                "connection_principle": None, "self_locking": True, "emergent_check": EmergentCheck(status="deferred", reason="EMERGENT thread-flank contact is curved; rigid-body V-B limit (R2b class, m17). The DECLARED-PAIR self-lock IS physics-verified (m19 P-SCREW V-A): sourced friction µ·W·d_mean/2 holds the released load to 0.08 mm back-drive, and a sub-back-drive friction slips 18 mm (non-tautology probe) — but that is the declared kinematic pair, not the emergent flank contact", risk="thread-flank effects the declared pair cannot see (flank-normal load distribution, backlash, wear, off-axis binding) are unverified until V-B; the self-lock CRITERION (tan λ ≤ µ) and the sourced holding torque ARE now physics-backed, so this is narrower than pre-m19"),
                "compliance": "rigid", "kinematic_dof": "1 rot coupled to 1 trans (reserved axis-7)"}
    param_bounds = {"d_major": (5.0, 20.0, "mm"), "pitch": (0.5, 4.0, "mm"),
                    "starts": (1.0, 2.0, "count"), "lead": (0.5, 8.0, "mm"),
                    "length": (20.0, 200.0, "mm"), "stroke": (10.0, 180.0, "mm")}
    ports = [_p("screw_axis", "axis"), _p("nut_mount", "face"), _p("travel_axis", "axis")]
    imposes = _lead_screw_imposes()   # §8-2: the assembly threading path (V-08)
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
        from knowledge.cards.lead_screw import (lead_screw_dims, lead_screw_mechanics,
                                                size_d_major_from_load, TAU_DESIGN_MPA, SIZING_SF)
        out = dict(inst.params or {})
        b = next((x for x in ir.behaviors if x.realized_by == inst.id
                  and getattr(x.motion.kind, "value", x.motion.kind) == "rot_to_trans"), None)
        if b is not None and getattr(b.motion, "range_value", None):
            out["stroke"] = float(b.motion.range_value)
        out.setdefault("stroke", 40.0)
        out.setdefault("starts", 1)               # FIX (m18 audit): starts now RESOLVES (bound 1..2)
        # REQUIREMENT-DRIVEN SIZING (⑤ resolves UNSPECIFIED dimensions from requirements): an EXPLICIT
        # d_major is a fixed design decision — honoured. If d_major is UNSET and the IR declares a LOAD,
        # SIZE it from that load (drive-torque torsional shear, τ_design/SF); else the 8.0 no-load default.
        lo, hi = self.param_bounds["d_major"][0], self.param_bounds["d_major"][1]
        lb = next((x for x in ir.behaviors if x.realized_by == inst.id
                   and isinstance(getattr(x, "load", None), dict) and x.load.get("mass_kg")), None)
        if "d_major" in out:
            pass                                  # explicit — respect the designed value
        elif lb is not None:
            W_N = float(lb.load["mass_kg"]) * 9.81
            d_req = size_d_major_from_load(W_N, mu=out.get("mu", 0.30))
            out["d_major"] = round(min(max(d_req, lo), hi), 2)
            out["_sized"] = {"from": "declared load W (shear)", "W_N": round(W_N, 2),
                             "d_shear_mm": round(d_req, 2), "tau_design_MPa": TAU_DESIGN_MPA, "SF": SIZING_SF,
                             "governed": ("min_bound" if d_req < lo else "max_bound" if d_req > hi else "shear")}
        else:
            out["d_major"] = 8.0                   # no-load fallback (default)
        out.setdefault("pitch", 2.0)
        # RULE CHAIN — lead = starts × pitch (DERIVED, never a free param; the card owns the formula)
        out["lead"] = round(int(out["starts"]) * float(out["pitch"]), 3)
        out.setdefault("length", round(float(out["stroke"]) + 20.0, 1))
        # pitch UPPER bound = self-lock (tan λ ≤ µ): if the behaviour demands hold-under-load, shrink the
        # pitch (hence the lead) until tan(λ) ≤ µ. LOWER bound = a declared drive-speed (min mm/rev): if
        # present and self-lock would force the lead below it, that is a CONFLICT (recorded, not patched).
        min_lead = None
        if b is not None and getattr(b.motion, "transmission", None):
            min_lead = b.motion.transmission.get("min_mm_per_rev")
        if b is not None and getattr(b, "self_locking", False):
            while not lead_screw_mechanics(lead_screw_dims(out))["self_locks"] and out["pitch"] > 0.5:
                out["pitch"] = round(out["pitch"] - 0.5, 2)
                out["lead"] = round(int(out["starts"]) * float(out["pitch"]), 3)
            if min_lead is not None and out["lead"] < float(min_lead):
                out["_pitch_conflict"] = {"self_lock_lead_mm": out["lead"], "required_min_lead_mm": float(min_lead),
                                          "note": "self-lock caps the lead BELOW the declared drive-speed floor — DRAFT (multi-start or a brake is the fix)"}
        # record the self-lock pitch ceiling (the upper bound the demo table cites)
        d_mean = out["d_major"] - out["pitch"] / 2.0
        out["_pitch_selflock_max_mm"] = round(out.get("mu", 0.30) * math.pi * d_mean / int(out["starts"]), 3)
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
