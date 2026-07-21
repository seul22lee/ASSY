"""pawl_detent geometry + forces (MECHSYNTH — physics-discovered element #2, D-M13-4).

A spring-arm tooth-catch (a ratchet pawl) that PERMITS crank-driven lift and BLOCKS back-drive. It is
snap_hook's mechanical cousin — the SAME Bayer cantilever formulas (deflection force P, the Fig.18
factor (μ+tanα)/(1−μ·tanα), the self-locking angle atan(1/μ)) — but used ASYMMETRICALLY and with the
self-locking asymptote turned into a FEATURE:

  DRIVE-OVER (platform rises): the pawl rides over a ratchet tooth on a SHALLOW angle α_drive, so the
                               click-over force W_drive = P·fig18(α_drive) stays small (in budget).
  LOCK (back-drive): the pawl seats against a STEEP α_lock ≥ self_locking_angle(μ). There fig18
                     DIVERGES — the reaction cannot deflect the pawl out — so it SELF-LOCKS and the
                     platform cannot fall. m3 mapped α_out→90° as the permanent-lock CLIFF (a warning
                     for a separable snap); here we sit ON it deliberately (D-GEN-2 inverted).

The pawl provides NO pieces — it is a spring arm carved on the tower + fine ratchet detents on the
rack side (§ "carved into the rack side"). Physics models the catch as a unilateral stop at the
detent pitch (the ratchet resolution): released under load, the platform drops ≤ one detent, then holds.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path

from build123d import Align, Box, Location, Pos

sys.path.insert(0, str(Path(__file__).resolve().parent))
from knowledge.cards.snap_hook import (Es_secant, P_deflect, W_mate, fig18_factor,  # noqa: E402
                                  self_locking_angle, working_strain)

E_PETG = 2100.0          # PETG flexural modulus (MPa) — same material family as the snap hook
MU = 0.30                # A-PETG-1 friction (the frozen preset's μ, R5)


@dataclass
class PawlDims:
    L: float = 14.0          # spring-arm length (mm)
    b: float = 5.0           # arm width (mm)
    h: float = 1.0           # arm thickness (mm) — thin → low click-over force
    alpha_drive: float = 30.0    # shallow drive-over angle (rides over)
    alpha_lock: float = 80.0     # steep locking angle (≥ self-lock → blocks back-drive)
    detent_pitch: float = 3.0    # ratchet tooth pitch (mm) — the hold RESOLUTION
    detent_depth: float = 1.0    # ratchet tooth depth = pawl deflection (mm)


def dims_from(params: dict) -> PawlDims:
    p = params or {}
    return PawlDims(
        L=float(p.get("L_mm", 14.0)), b=float(p.get("b_mm", 5.0)), h=float(p.get("h_mm", 1.0)),
        alpha_drive=float(p.get("alpha_drive_deg", 30.0)),
        alpha_lock=float(p.get("alpha_lock_deg", 80.0)),
        detent_pitch=float(p.get("detent_pitch_mm", 3.0)),
        detent_depth=float(p.get("detent_depth_mm", 1.0)))


def forces(g: PawlDims, mu: float = MU, E: float = E_PETG) -> dict:
    """Bayer arithmetic (reused verbatim from snap_hook_cantilever): the deflection force, the
    drive-over force, and whether the lock angle self-locks. This is the pawl's FORMULA verification."""
    eps = working_strain()
    Es = Es_secant(E, eps)
    P = P_deflect(g.b, g.h, Es, eps, g.L)              # force to deflect the arm by the tooth
    w_drive = W_mate(P, mu, g.alpha_drive)             # P · fig18(α_drive) — click-over force
    sl = self_locking_angle(mu)                        # atan(1/μ)
    self_locks = g.alpha_lock >= sl                    # ≥ self-lock ⇒ back-drive cannot deflect it out
    return {"eps": round(eps, 4), "Es_MPa": round(Es, 1), "P_N": round(P, 3),
            "W_drive_N": round(w_drive, 3), "fig18_drive": round(fig18_factor(mu, g.alpha_drive), 3),
            "self_lock_angle_deg": round(sl, 1), "alpha_lock_deg": g.alpha_lock,
            "self_locks": bool(self_locks), "detent_pitch_mm": g.detent_pitch}


# --- geometry (minimal — the mechanism is the formula + the detent constraint; this is for the
#     render + collision hint). The pawl arm mounts on the tower and reaches to the rack detents. ---
def _anchor(pieces, binding) -> dict:
    tr = pieces[binding.piece_id]
    a = tr.anchors[binding.anchor]
    return {"point": a.position, "normal": a.normal}


def _solids(pieces: dict) -> dict:
    return {pid: getattr(tr, "part", tr) for pid, tr in pieces.items()}


@dataclass
class PawlCarve:
    parts: dict
    tags: dict
    dims: PawlDims


def build_pawl(g: PawlDims, base_pt) -> object:
    """A cantilever spring arm (a thin box) with a catch tooth at its tip, rooted at base_pt and
    reaching in −Y toward the rack. Kept box-only (cheap collision, like slide_rail)."""
    bx, by, bz = base_pt
    arm = Location((bx, by - g.L / 2, bz)) * Box(g.b, g.L, g.h,
                                                 align=(Align.CENTER, Align.CENTER, Align.CENTER))
    tooth = Location((bx, by - g.L, bz - g.detent_depth / 2)) * Box(
        g.b, g.detent_depth * 1.5, g.detent_depth + g.h,
        align=(Align.CENTER, Align.CENTER, Align.CENTER))
    return arm + tooth


def carve(pieces: dict, inst, bindings) -> PawlCarve:
    """Mount the pawl arm on the tower (the `pawl_mount` binding). The ratchet detents on the rack are
    the rack's own fine teeth (modelled as the detent-pitch constraint in physics), so this carve only
    adds the pawl arm — the pawl provides no pieces."""
    g = dims_from(inst.params)
    mb = next(b for b in bindings if b.port == "pawl_mount")
    anc = _anchor(pieces, mb)
    parts = dict(_solids(pieces))
    pawl = build_pawl(g, tuple(anc["point"]))
    parts[mb.piece_id] = parts[mb.piece_id] + pawl
    return PawlCarve(parts=parts, tags={"pawl": pawl}, dims=g)


def collision_primitives(inst) -> list:
    """The pawl arm + tooth as boxes (D18), source-stamped (D-M8-4). frame='world' (they sit at the
    mount point in the assembly frame). The ratchet CLICK-OVER is the intended contact class (D22)."""
    g = dims_from(inst.params)
    src = f"card:pawl_detent@{inst.id}"
    return [{"type": "box", "frame": "world", "owner": "pawl", "source": src,
             "pos": (0.0, -g.L / 2, 0.0), "size": (g.b / 2, g.L / 2, g.h / 2), "role_hint": "spring_arm"},
            {"type": "box", "frame": "world", "owner": "pawl", "source": src,
             "pos": (0.0, -g.L, -g.detent_depth / 2),
             "size": (g.b / 2, g.detent_depth * 0.75, (g.detent_depth + g.h) / 2),
             "role_hint": "catch_tooth"}]


# --- card class (M18 refactor: moved from base.py, verbatim) ---------------------------------
from knowledge.cards.base import ProvidedPiece, InteractionRule, _p  # noqa: E402
from ontology.schema import Citation, EmergentCheck  # noqa: E402
from knowledge.cards.base import MechanicalElementCard  # noqa: E402

def _pawl_imposes() -> list:
    """The pawl imposes a USE-phase ratchet click-over — an INTENDED contact (D22), not a defect: as
    the platform rises the pawl deliberately rides over each ratchet tooth. Registered per V-08."""
    from ontology.schema import Behavior, MotionSpec
    return [Behavior(id="_imposed_ratchet_clickover", phase="use", motion=MotionSpec(kind="fixed"))]


class PawlDetentCard(MechanicalElementCard):
    """Spring-arm ratchet pawl (physics-discovered element #2, D-M13-4) — snap_hook's mechanical
    cousin. PERMITS crank-driven lift (shallow drive-over angle) and BLOCKS back-drive (steep lock
    angle ≥ the self-locking asymptote atan(1/μ)). Reuses the Bayer cantilever formulas VERBATIM
    (knowledge/cards/pawl_detent.py delegates to snap_hook_cantilever). Provides no pieces — a spring
    arm carved on the tower + fine ratchet detents on the rack side."""
    card_id = "pawl_detent"
    has_functional_clearance = True   # the detent engagement clearance (D18/D21)
    taxonomy = {"working_motion": ("fixed", "regular"), "axis_relationship": "parallel",
                "connection_principle": None, "self_locking": True, "emergent_check": EmergentCheck(status="verified"),
                "compliance": "rigid", "kinematic_dof": "unilateral ratchet (reclass candidate -> compliant, m18 REVIEW §5)"}
    imposes = _pawl_imposes()
    requires = {"eps_allow_pct": (">=", 3.0)}   # the spring arm must sustain the flexure strain
    param_bounds = {"L_mm": (8.0, 25.0, "mm"), "b_mm": (4.0, 10.0, "mm"), "h_mm": (0.8, 2.0, "mm"),
                    "alpha_drive_deg": (25.0, 35.0, "deg"), "alpha_lock_deg": (74.0, 90.0, "deg"),
                    "detent_pitch_mm": (2.0, 5.0, "mm"), "detent_depth_mm": (0.6, 1.5, "mm")}
    selection_notes = (
        "Use when a transmission must HOLD a load against a back-driving force it cannot self-lock — "
        "e.g. a rack-pinion LIFT (μ·W·rp ≪ W·rp, so a plain gear back-drives; discovered at P-HOLD, "
        "D-M13-2). The pawl is asymmetric: a SHALLOW drive-over angle so the crank clicks over each "
        "ratchet tooth cheaply, and a STEEP lock angle ≥ self_locking_angle(μ)=atan(1/μ)=73.3° (at "
        "μ=0.30) so the Fig.18 factor DIVERGES and back-drive cannot deflect the pawl out — it "
        "self-locks. This is the m3 permanent-lock cliff (D-GEN-2) used DELIBERATELY, not avoided. "
        "The hold RESOLUTION is one detent pitch (the platform drops ≤ one tooth before catching).")
    citations = [Citation(doc="Bayer", section="p.14 Fig.18 factor (μ+tanα)/(1−μtanα) + self-lock asymptote"),
                 Citation(doc="DECISIONS_LOG", section="D-M13-4 (physics-discovered element #2, after the stop)")]
    ports = [_p("pawl_mount", "face"), _p("ratchet_line", "edge")]

    def carve(self, host_parts, inst, bindings):
        from knowledge.cards.pawl_detent import carve as _carve
        return _carve(host_parts, inst, bindings)

    def collision_hint(self, inst):
        from knowledge.cards.pawl_detent import collision_primitives
        return collision_primitives(inst)

    def resolve_params(self, ir, inst):
        """Snap the lock angle UP to at least the self-locking angle so the pawl actually holds."""
        from knowledge.cards.pawl_detent import dims_from, forces
        out = dict(inst.params or {})
        f = forces(dims_from(out))
        if float(out.get("alpha_lock_deg", 80.0)) < f["self_lock_angle_deg"]:
            out["alpha_lock_deg"] = round(f["self_lock_angle_deg"] + 5.0, 1)
        out.setdefault("detent_pitch_mm", 3.0)
        return out

    def verification(self, ir, inst):
        """PR-PAWL — the hold verification. Gate: back-drive ≤ one detent pitch (+margin). The FORMULA
        facts (self-locks? drive-over force in budget?) ride in the actuation, Bayer-computed."""
        from ontology.schema import Criterion, VerificationProtocol
        from knowledge.cards.pawl_detent import dims_from, forces
        hold_b = next((b for b in ir.behaviors if b.realized_by == inst.id
                       and getattr(b.phase, "value", b.phase) == "static"), None)
        if hold_b is None:
            return []
        g = dims_from(inst.params)
        f = forces(g)
        load = hold_b.load or {}
        budget_N = float(load.get("mass_kg", 0.5)) * 9.81 + 4.0   # lift force the crank already carries
        protos = [VerificationProtocol(
            id=f"PR-PAWL-{inst.id}", verifies=hold_b.id, mode="V-A", seeds=5, seed_pass=4,
            actuation={"kind": "release_and_watch", "load_kg": load.get("mass_kg", 0.5),
                       "self_locks": f["self_locks"], "W_drive_N": f["W_drive_N"],
                       "self_lock_angle_deg": f["self_lock_angle_deg"],
                       "alpha_lock_deg": f["alpha_lock_deg"], "drive_over_budget_N": round(budget_N, 2),
                       "drive_over_in_budget": bool(f["W_drive_N"] <= budget_N),
                       "note": "self-locks at alpha_lock>=atan(1/mu); catches within one detent pitch"},
            criteria=[Criterion(name="no_backdrive", observable="backdrive_mm", op="<=",
                                threshold=round(g.detent_pitch + 2.0, 2), unit="mm")], observables=[])]
        click_b = next((b for b in ir.behaviors if b.imposed_by == inst.id
                        and getattr(b.phase, "value", b.phase) == "use"), None)
        if click_b is not None:
            protos.append(VerificationProtocol(
                id=f"PR-CLICK-{inst.id}", verifies=click_b.id, mode=None,
                actuation={"kind": "formula_recheck", "source": "Bayer p.14 drive-over"},
                criteria=[Criterion(name="drive_over_in_budget", observable="pawl_drive_N", op="<=",
                                    threshold=round(budget_N, 2), unit="N")], observables=[]))
        return protos
