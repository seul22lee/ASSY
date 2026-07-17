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
from snap_hook_cantilever import (Es_secant, P_deflect, W_mate, fig18_factor,  # noqa: E402
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
