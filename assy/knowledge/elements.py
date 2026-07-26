"""Deterministic machine-element sizing functions.

Rule L-2: an LLM must never perform these computations. Each function is a pure
function of its arguments (Rule CODE-4) and names the relation it implements so
the resolution that uses it can record a method (STAGE_05 section 7.5).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# --------------------------------------------------------------------------
# Lead screw
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ScrewResult:
    lead_angle_deg: float
    torque_raise_nmm: float
    torque_lower_nmm: float
    self_locking: bool
    efficiency: float
    method: str = "power_screw_square_thread"


def lead_screw(
    load_n: float, pitch_diameter_mm: float, lead_mm: float, friction: float
) -> ScrewResult:
    """Square-thread power screw.

    tan(lambda) = L / (pi * d_m);  self-locking when mu > tan(lambda).
    """
    dm = pitch_diameter_mm
    lam = math.atan2(lead_mm, math.pi * dm)
    t_raise = load_n * dm / 2.0 * (
        (math.cos(0.0) * math.tan(lam) + friction) / (math.cos(0.0) - friction * math.tan(lam))
    )
    t_lower = load_n * dm / 2.0 * (
        (friction - math.tan(lam)) / (1.0 + friction * math.tan(lam))
    )
    eff = (load_n * lead_mm) / (2.0 * math.pi * t_raise) if t_raise > 0 else 0.0
    return ScrewResult(
        lead_angle_deg=math.degrees(lam),
        torque_raise_nmm=t_raise,
        torque_lower_nmm=t_lower,
        self_locking=friction > math.tan(lam),
        efficiency=eff,
    )


# --------------------------------------------------------------------------
# Shafts
# --------------------------------------------------------------------------
def shaft_deflection_simply_supported(
    load_n: float, span_mm: float, diameter_mm: float, e_mpa: float
) -> float:
    """Midspan deflection of a centrally loaded simply supported shaft: PL^3/48EI."""
    i = math.pi * diameter_mm**4 / 64.0
    return load_n * span_mm**3 / (48.0 * e_mpa * i)


def shaft_deflection_cantilever(
    load_n: float, length_mm: float, diameter_mm: float, e_mpa: float
) -> float:
    """Tip deflection of an end-loaded cantilever: PL^3/3EI."""
    i = math.pi * diameter_mm**4 / 64.0
    return load_n * length_mm**3 / (3.0 * e_mpa * i)


def shaft_torsional_stress(torque_nmm: float, diameter_mm: float) -> float:
    """Max shear stress in a solid round shaft: 16T/(pi d^3)."""
    return 16.0 * torque_nmm / (math.pi * diameter_mm**3)


# --------------------------------------------------------------------------
# Gears
# --------------------------------------------------------------------------
def gear_centre_distance(module_mm: float, teeth_a: int, teeth_b: int) -> float:
    """Standard centre distance: m (z1 + z2) / 2."""
    return module_mm * (teeth_a + teeth_b) / 2.0


def gear_ratio(teeth_driver: int, teeth_driven: int) -> float:
    return teeth_driven / teeth_driver


def undercut_limit(pressure_angle_deg: float = 20.0) -> int:
    """Minimum teeth without undercut: 2 / sin^2(alpha)."""
    a = math.radians(pressure_angle_deg)
    return math.ceil(2.0 / (math.sin(a) ** 2))


# --------------------------------------------------------------------------
# Rack and pinion
# --------------------------------------------------------------------------
def rack_travel_per_turn(module_mm: float, teeth: int) -> float:
    """One pinion revolution advances the rack by the pitch circumference."""
    return math.pi * module_mm * teeth


# --------------------------------------------------------------------------
# Linear guides
# --------------------------------------------------------------------------
def jamming_ratio(overhang_mm: float, bearing_span_mm: float, friction: float) -> float:
    """Jamming index. Binding when overhang/span exceeds 1/(2 mu)."""
    if bearing_span_mm <= 0:
        return float("inf")
    limit = 1.0 / (2.0 * friction) if friction > 0 else float("inf")
    return (overhang_mm / bearing_span_mm) / limit


# --------------------------------------------------------------------------
# Compliant beams (snap fits)
# --------------------------------------------------------------------------
def cantilever_snap_deflection_force(
    deflection_mm: float, length_mm: float, width_mm: float, thickness_mm: float, e_mpa: float
) -> float:
    """Force to deflect a rectangular cantilever: 3EIy/L^3."""
    i = width_mm * thickness_mm**3 / 12.0
    return 3.0 * e_mpa * i * deflection_mm / length_mm**3


def cantilever_snap_strain(
    deflection_mm: float, length_mm: float, thickness_mm: float
) -> float:
    """Peak outer-fibre strain at the beam root: 3 t y / (2 L^2)."""
    return 1.5 * thickness_mm * deflection_mm / length_mm**2


# --------------------------------------------------------------------------
# Tolerance
# --------------------------------------------------------------------------
def stack_worst_case(tolerances: list[float]) -> float:
    return sum(abs(t) for t in tolerances)


def stack_rss(tolerances: list[float]) -> float:
    return math.sqrt(sum(t * t for t in tolerances))
