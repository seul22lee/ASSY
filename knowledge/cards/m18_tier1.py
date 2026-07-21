"""M18 Tier-1 element geometry + formulas (schema/ontology expansion, no new physics).

Eight Tier-1 cards, grouped by category. Each provides: a Dims dataclass, dims_from(params), the
CITED design formula(s) (formula_check reproduces them), and carve() → one build123d solid. The
three cards with a running/locational clearance also provide collision_primitives (D18/D21).

Formula sources (cited per function; the machine-design analogue of Bayer for snaps):
  - power screw lead angle / self-locking : Shigley §8-2 "Power Screws"; P&B §7.4.3 (self-help)
  - press-fit interference pressure/holding: Shigley §3-56 (interference fits); Roark Table 13.1
  - self-tapping boss pull-out            : BASF/Bayer boss & self-tap guidelines; Shigley thread shear
  - shaft torsion (coupling capacity)     : Shigley §3-12 (torsion, tau = 16 T / pi d^3)
  - Cardan (universal joint) angle law    : standard kinematics theta_out = atan(tan(theta_in)/cos(beta))
  - journal running clearance             : Shigley §12 (rule of thumb c ~ d/1000)

Geometry note: Tier-1 carves are SIMPLE standalone primitives (a boss is a cylinder, a bushing is a
tube) placed at the element's primary anchor — appropriate for V-A/static verification. If a future
Tier-2 adds contact V-B to any of these, it revisits the carve + collision hint.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from build123d import Align, Box, Cylinder, Location, Pos  # noqa: F401


@dataclass
class CarveResult:
    parts: dict                     # piece_id -> build123d solid (host + grown element)
    tags: dict                      # named sub-solids (the element's own geometry)
    dims: object
    extra: dict = field(default_factory=dict)


def _anchor_point(pieces, bindings, port, default=(0.0, 0.0, 0.0)):
    """Best-effort world point of the element's primary anchor; origin if the fixture omits it.
    Tolerant so carve() is testable with a minimal host fixture (Tier-1 needs no deep integration)."""
    b = next((x for x in (bindings or []) if getattr(x, "port", None) == port), None)
    if b is None:
        return default
    pc = (pieces or {}).get(b.piece_id)
    if pc is None:
        return default
    anchors = getattr(pc, "anchors", {}) or {}
    a = anchors.get(b.anchor) if isinstance(anchors, dict) else None
    pos = getattr(a, "position", None) if a is not None else None
    return tuple(pos) if pos is not None else default


def _host_solid(pieces, pid):
    pc = (pieces or {}).get(pid)
    return getattr(pc, "part", pc) if pc is not None else None


def _add(pieces, pid, solid):
    """Add `solid` to host `pid` if present, else return a parts dict with just the element solid."""
    host = _host_solid(pieces, pid)
    out = {k: _host_solid(pieces, k) for k in (pieces or {})}
    out[pid] = (host + solid) if host is not None else solid
    return out


# ======================================================================================
# MECHANICAL ELEMENTS
# ======================================================================================
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


# ======================================================================================
# PASSIVE FEATURES (supports; realize nothing)
# ======================================================================================
@dataclass
class BearingDims:
    bore_d: float = 8.0         # shaft diameter it supports (mm)
    wall: float = 3.0           # bearing wall (mm)
    length: float = 10.0        # axial length (mm)
    clearance: float = 0.0      # running clearance (mm) — resolved from bore


def bearing_dims(p: dict) -> BearingDims:
    p = p or {}
    return BearingDims(bore_d=float(p.get("bore_d", 8.0)), wall=float(p.get("wall", 3.0)),
                       length=float(p.get("length", 10.0)), clearance=float(p.get("clearance", 0.0)))


def bearing_fit(g: BearingDims) -> dict:
    """Shigley §12 rule of thumb: a running (journal) clearance ~ d/1000, floored at the PETG print
    clearance so the fit is printable. The bearing SUPPORTS a rotation; it realizes nothing."""
    from knowledge.materials import PETG
    c = max(g.bore_d / 1000.0, PETG.print_clearance_mm)
    return {"running_clearance_mm": round(c, 4), "bore_id_mm": round(g.bore_d + c, 4),
            "outer_d_mm": round(g.bore_d + c + 2 * g.wall, 4)}


def bearing_carve(pieces, inst, bindings, port="bore_mount") -> CarveResult:
    g = bearing_dims(getattr(inst, "params", {}) or {})
    f = bearing_fit(g)
    p = _anchor_point(pieces, bindings, port)
    tube = Location(Pos(*p)) * (Cylinder(radius=f["outer_d_mm"] / 2, height=g.length,
                                         align=(Align.CENTER, Align.CENTER, Align.MIN))
                                - Cylinder(radius=f["bore_id_mm"] / 2, height=g.length + 2,
                                           align=(Align.CENTER, Align.CENTER, Align.MIN)))
    return CarveResult(parts=_add(pieces, _pid(bindings, port), tube), tags={"sleeve": tube}, dims=g)


def bearing_collision(inst, cid="journal_bearing", port="bore_mount") -> list:
    g = bearing_dims(getattr(inst, "params", {}) or {})
    f = bearing_fit(g)
    return [{"type": "cylinder", "frame": "world", "owner": "sleeve",
             "source": f"card:{cid}@{getattr(inst,'id','?')}",
             "r": f["outer_d_mm"] / 2, "h": g.length, "bore_r": f["bore_id_mm"] / 2,
             "note": "running-clearance bore; convex tube (exact, no swallow) — D18/D21"}]


# ======================================================================================
# CONNECTIONS (fasten/fix parts; realize nothing, support no DoF)
# ======================================================================================
@dataclass
class DowelDims:
    pin_d: float = 4.0
    length: float = 12.0
    fit_clearance: float = 0.02     # H7/g6-style locational clearance (mm)


def dowel_dims(p: dict) -> DowelDims:
    p = p or {}
    return DowelDims(pin_d=float(p.get("pin_d", 4.0)), length=float(p.get("length", 12.0)),
                     fit_clearance=float(p.get("fit_clearance", 0.02)))


def dowel_fit(g: DowelDims) -> dict:
    """FORM connection (P&B §8.1): geometric interlock, no load path through friction. A dowel LOCATES
    two parts (removes in-plane DoF) with a tight locational fit; verified STATICALLY (t0: the bore
    receives the pin with a small positive clearance, no interference)."""
    return {"bore_d_mm": round(g.pin_d + g.fit_clearance, 4), "principle": "form",
            "locates_dof": "2 in-plane translations (a single dowel); a pair also fixes rotation"}


def dowel_carve(pieces, inst, bindings) -> CarveResult:
    g = dowel_dims(getattr(inst, "params", {}) or {})
    p = _anchor_point(pieces, bindings, "location")
    pin = Location(Pos(*p)) * Cylinder(radius=g.pin_d / 2, height=g.length,
                                       align=(Align.CENTER, Align.CENTER, Align.MIN))
    return CarveResult(parts=_add(pieces, _pid(bindings, "location"), pin), tags={"dowel": pin}, dims=g)


@dataclass
class ScrewBossDims:
    screw_d: float = 3.0        # nominal screw diameter (mm)
    engagement: float = 6.0     # thread engagement depth (mm)
    tau_shear: float = 30.0     # PETG shear strength (MPa, conservative)


def screwboss_dims(p: dict) -> ScrewBossDims:
    p = p or {}
    return ScrewBossDims(screw_d=float(p.get("screw_d", 3.0)),
                         engagement=float(p.get("engagement", 6.0)),
                         tau_shear=float(p.get("tau_shear", 30.0)))


def screwboss_design(g: ScrewBossDims) -> dict:
    """FORCE connection (P&B §8.1) via a self-tapping screw. BASF/Bayer boss rules (single PETG, D8):
    boss OD ~ 2.0*screw_d, self-tap pilot hole ~ 0.8*screw_d, engagement >= 2*screw_d. Pull-out force
    = thread shear area * shear strength = pi * d_pilot * engagement * tau (Shigley thread shear)."""
    boss_od = 2.0 * g.screw_d
    pilot_d = 0.8 * g.screw_d
    shear_area = math.pi * pilot_d * g.engagement            # mm^2
    pullout_N = shear_area * g.tau_shear                     # tau in MPa=N/mm^2
    return {"boss_od_mm": round(boss_od, 3), "pilot_d_mm": round(pilot_d, 3),
            "engagement_min_mm": round(2.0 * g.screw_d, 3),
            "pullout_force_N": round(pullout_N, 1), "principle": "force"}


def screwboss_carve(pieces, inst, bindings) -> CarveResult:
    g = screwboss_dims(getattr(inst, "params", {}) or {})
    d = screwboss_design(g)
    p = _anchor_point(pieces, bindings, "boss_mount")
    boss = Location(Pos(*p)) * (Cylinder(radius=d["boss_od_mm"] / 2, height=g.engagement + 4,
                                         align=(Align.CENTER, Align.CENTER, Align.MIN))
                                - Cylinder(radius=d["pilot_d_mm"] / 2, height=g.engagement + 4 + 2,
                                           align=(Align.CENTER, Align.CENTER, Align.MIN)))
    return CarveResult(parts=_add(pieces, _pid(bindings, "boss_mount"), boss),
                       tags={"boss": boss}, dims=g, extra={"provides_screw_d": g.screw_d})


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


def _pid(bindings, port, default="P1"):
    b = next((x for x in (bindings or []) if getattr(x, "port", None) == port), None)
    return b.piece_id if b is not None else default
