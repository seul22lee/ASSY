"""snap_hook_cantilever — governing formulas (Bayer "Snap-Fit Joints for Plastics", the PDF in
knowledge/refs/). Formulas ONLY this session; carve()/templates/Tier0 are out of scope.

SOURCE OF TRUTH IS THE PDF, verified page-by-page (not SNAPFIT §2.1's mapping table, which is a
guide). Every formula below is transcribed from the cited page/table and checked against
Calculation Example I (p.16); `tests/test_golden_bayer.py` reproduces that example to ±1–2%.

Verified transcription (all from the PDF, cross-section shape A = rectangle):
  Table 1, p.9   permissible deflection y = C · ε · l² / h,  C = 0.67 (design 1), 1.09 (design 2),
                 0.86 (design 3); deflection force P = (b·h²/6) · (Es·ε / l).
  Symbols, p.9   ε is used as the ABSOLUTE value = percentage/100 (2% → 0.02); l = arm length,
                 h = root thickness, b = root width, Es = secant modulus (Fig.16), y = undercut.
  p.11           single brief snap-fit: amorphous plastics ~70% of yield strain.
  p.12 Table 2   permissible short-term strain (Bayer resins); footnote: for frequent separation
                 and rejoining use ~60% of these values. Design 2 raises y >60% over design 1.
  p.14           mating force W = P · (μ + tanα)/(1 − μ·tanα); SEPARATION uses the return angle α′.
  Fig.18, p.15   the factor (μ + tanα)/(1 − μ·tanα) read graphically (μ=0.6, α=30° → 1.8).
  p.16           Example I: PC, l=19, b=9.5, y=2.4, α=30°, ε_perm=4% → ε=½·4%=2%, Es=1815, μ=0.6
                 ⇒ h=3.28 mm, P=32.5 N, W=58.5 N.

Assumptions (PETG is NOT in the PDF's tables/curves — flagged, see DECISIONS_LOG D-BAYER rows):
  Es_petg ≈ 0.75·E   (Fig.16 carries Bayer PC resins only; PC drops to ~60–75% of E near 2%).
  EPS_PERM_PETG      (PETG amorphous → ~70% yield strain, p.11; a datasheet value is needed).
  MU_PETG ≈ 0.35     (Table 3 has no PETG; extrapolated). Gate: replace all three with data.
"""

from __future__ import annotations

import math

# --- Table 1 (p.9), cross-section shape A (rectangle) — the permissible-deflection coefficient.
# Design 2 (thickness tapering root→h/2) permits >60% more deflection than design 1 (p.12), which
# is why the p.16 example uses it. Design 3 tapers width root→b/4.
SHAPE_A_COEFF = {1: 0.67, 2: 1.09, 3: 0.86}  # Bayer Table 1, p.9

# --- PETG material handling — ASSUMPTIONS (no PETG in the PDF). Gate G-S4: replace with data.
DEFAULT_SAFETY = 0.5      # p.16: working strain ε = ½ · ε_perm
FREQ_FACTOR = 0.60        # Table 2 footnote, p.12: frequent separation/rejoining → ~60%
EPS_PERM_PETG = 0.04      # ASSUMPTION: PETG amorphous ~70% yield strain (p.11); PC 4% stand-in
MU_PETG = 0.35            # ASSUMPTION: Table 3 has no PETG (extrapolated from PC 0.45–0.55)


# --- permissible deflection & its inversion ------------------------------------------------
def y_perm(eps: float, l: float, h: float, design_type: int = 2) -> float:
    """Permissible deflection (= undercut) y for a rectangular cantilever [Bayer Table 1, p.9].

        y = C · ε · l² / h        (C from SHAPE_A_COEFF)

    ε is the ABSOLUTE strain (percentage/100), e.g. 0.02 for 2% (p.9 symbols)."""
    return SHAPE_A_COEFF[design_type] * eps * l**2 / h


def solve_h(eps: float, l: float, y: float, design_type: int = 2) -> float:
    """Root thickness h that makes deflection to undercut y induce exactly strain ε — the p.16
    inversion of the Table 1 deflection equation:

        h = C · ε · l² / y

    Example I (design 2): 1.09 · 0.02 · 19² / 2.4 = 3.28 mm."""
    return SHAPE_A_COEFF[design_type] * eps * l**2 / y


# --- deflection force ----------------------------------------------------------------------
def P_deflect(b: float, h: float, Es: float, eps: float, l: float) -> float:
    """Deflection force P to bend the finger to strain ε [Bayer Table 1 bottom row, p.9]:

        P = (b · h² / 6) · (Es · ε / l)

    b·h²/6 is the rectangular section modulus Z. Es in N/mm² (MPa), lengths in mm → P in N.
    Example I: (9.5 · 3.28² / 6) · (1815 · 0.02 / 19) = 32.5 N."""
    return (b * h**2 / 6.0) * (Es * eps / l)


# --- mating / separation force -------------------------------------------------------------
def fig18_factor(mu: float, alpha_deg: float) -> float:
    """The dimensionless force factor (μ + tanα)/(1 − μ·tanα) [Bayer p.14; graph Fig.18, p.15].
    Example I: μ=0.6, α=30° → 1.80. Diverges as μ·tanα → 1 (self-locking); caller keeps α sane."""
    t = math.tan(math.radians(alpha_deg))
    denom = 1.0 - mu * t
    if denom <= 0:
        raise ValueError(f"self-locking geometry: mu*tan(alpha) >= 1 (mu={mu}, alpha={alpha_deg})")
    return (mu + t) / denom


# --- self-locking placement rule (D-GEN-2 resolution) --------------------------------------
SELF_LOCK_MARGIN_DEG = 10.0


def self_locking_angle(mu: float) -> float:
    """The retract angle at which the separation force diverges: μ·tanα′ = 1 ⇒ α′ = atan(1/μ)
    [Bayer p.14 / Fig.18 asymptote]. Beyond it the joint is permanent (cannot be pulled open)."""
    return math.degrees(math.atan(1.0 / mu))


def max_retract_angle(mu: float, margin_deg: float = SELF_LOCK_MARGIN_DEG) -> float:
    """Placement cap on α_out: stay margin° below the self-locking asymptote. A design that sits
    right at the asymptote is one μ-assumption away from a permanent lock, and μ for PETG is
    itself ASSUMPTION A-PETG-1 — so the margin is a hard rule, not a nicety (D-GEN-2)."""
    return self_locking_angle(mu) - margin_deg


def W_mate(P: float, mu: float, alpha_in_deg: float) -> float:
    """Mating (insertion) force [Bayer p.14]: W = P · (μ + tanα)/(1 − μ·tanα), α = insertion angle.
    Example I: 32.5 · 1.80 = 58.5 N."""
    return P * fig18_factor(mu, alpha_in_deg)


def W_sep(P: float, mu: float, alpha_out_deg: float) -> float:
    """Separation force [Bayer p.14]: same form as W_mate but with the RETURN angle α′ (the
    retraction/retract angle). α′ = 90° ⇒ self-locking (permanent joint)."""
    return P * fig18_factor(mu, alpha_out_deg)


# --- material helpers (ASSUMPTIONS) --------------------------------------------------------
def Es_secant(E: float, eps: float) -> float:
    """Strain-dependent secant modulus Es(ε) [Bayer Fig.16 defines it as σ/ε at the working
    strain]. Fig.16 carries Bayer PC resins only — NO PETG curve — so v0 uses a conservative
    flat approximation Es ≈ 0.75·E (PC falls to ~60–75% of E by ε≈2%). **ASSUMPTION** (G-S4:
    replace with a PETG secant curve or datasheet). `eps` accepted for interface stability /
    a future table lookup; unused in the flat approximation."""
    return 0.75 * E


def working_strain(eps_perm: float = EPS_PERM_PETG, frequent: bool = False,
                   safety: float = DEFAULT_SAFETY) -> float:
    """Working strain ε for dimensioning: ε_perm × (0.60 if frequent re-join else 1) × safety.
    The p.16 example is ε = ½ · ε_perm (single operation, safety 0.5)."""
    return eps_perm * (FREQ_FACTOR if frequent else 1.0) * safety
