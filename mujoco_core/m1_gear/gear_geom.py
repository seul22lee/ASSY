"""M1: hand-built spur-gear geometry (no pipeline, no cards). Risk-retirement for R2.

The question M1 answers is the tooth-profile analog of M0's bore: does a TOOTH PROFILE survive
hint-approximation and MESH — no slip, no jam — at backlash scale, in a rigid-body contact solver?

DESIGN DECISION — gear PAIR (z1=12 pinion, z2=24 gear), not rack-and-pinion.
  The P-GEAR protocol runs 3 full revolutions forward + 3 reverse. A rack meshing a z=12 pinion
  through 3 revs must span 3·π·d = 226 mm (36+ teeth) and gives a panning video with a tiny pinion.
  A compact rotating pair instead yields the clean, fixed-frame HUD mesh video that is the core
  evidence (D15); it is also the STRICTER test — both flanks are the trapezoidal/involute
  approximation, so a passing pair retires rack-and-pinion (one exact flank) transitively; and it
  is the canonical "gear-pair standalone". The rack is closer to the Hard anchor and its straight
  flank is the exact generating profile — noted as the easier, transitively-covered sub-case.

Two profiles (ladder rungs L1/L2 vs L3):
  * trapezoidal (v0, MECHSYNTH §3.6): straight flanks inclined at the pressure angle, rounded tip.
    An APPROXIMATION — constant-slope flanks cannot give exact conjugate action, so transmission
    error is expected; the experiment asks whether it still meshes at backlash scale.
  * involute (upgrade): the true conjugate profile; the flank from base to tip is the involute of
    the base circle. The reference the trapezoid is measured against.

Standard proportions (module m, tooth count z, pressure angle α):
  pitch r = m·z/2 · addendum a = m · dedendum b = 1.25m · base r = r·cosα
  circular pitch = πm · tooth thickness at pitch t = πm/2 − backlash/2  (backlash split both gears)
Units mm; build123d Solids in mm (converted to m at MJCF time, like m0/step2mjcf).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from build123d import Location, Polygon, Pos, extrude


@dataclass
class GearSpec:
    z: int
    m: float = 2.0
    face_width: float = 8.0
    pressure_angle_deg: float = 20.0
    backlash: float = 0.20          # total backlash (mm), split half to each gear's tooth thickness
    profile: str = "trapezoid"      # "trapezoid" | "involute"
    tip_frac: float = 0.9           # fraction of the way to full addendum before the tip flat/round

    @property
    def rp(self) -> float: return self.m * self.z / 2.0

    @property
    def ra(self) -> float: return self.rp + self.m               # addendum = m

    @property
    def rf(self) -> float: return self.rp - 1.25 * self.m        # dedendum = 1.25 m

    @property
    def rb(self) -> float: return self.rp * math.cos(math.radians(self.pressure_angle_deg))

    @property
    def t_pitch(self) -> float:                                  # tooth thickness at pitch circle
        return math.pi * self.m / 2.0 - self.backlash / 2.0


def _rot(pt, a):
    c, s = math.cos(a), math.sin(a)
    return (c * pt[0] - s * pt[1], s * pt[0] + c * pt[1])


def _arc(r, a0, a1, n):
    return [(r * math.cos(a), r * math.sin(a)) for a in np.linspace(a0, a1, n)]


def _trapezoid_flank(g: GearSpec):
    """Right-flank root & tip points for a tooth centred on +X. Straight flank inclined at the
    pressure angle to the radial through the pitch point — the tooth narrows from root to tip."""
    a = math.radians(g.pressure_angle_deg)
    rp = g.rp
    psi = (g.t_pitch / 2.0) / rp                    # half angular thickness at pitch
    phi = -psi                                      # right flank sits below the +X bisector
    r_hat = (math.cos(phi), math.sin(phi))
    t_hat = (-math.sin(phi), math.cos(phi))         # +θ (toward tooth centre)
    u = (math.cos(a) * r_hat[0] + math.sin(a) * t_hat[0],
         math.cos(a) * r_hat[1] + math.sin(a) * t_hat[1])
    P = (rp * r_hat[0], rp * r_hat[1])
    ra_eff = rp + g.tip_frac * (g.ra - rp)          # stop a touch short of full addendum -> tip flat
    s_tip = -rp * math.cos(a) + math.sqrt(ra_eff ** 2 - rp ** 2 * math.sin(a) ** 2)
    s_root = -rp * math.cos(a) + math.sqrt(g.rf ** 2 - rp ** 2 * math.sin(a) ** 2)
    root = (P[0] + s_root * u[0], P[1] + s_root * u[1])
    tip = (P[0] + s_tip * u[0], P[1] + s_tip * u[1])
    return root, tip


def _involute_flank(g: GearSpec, n=10):
    """Right-flank points root→tip along the involute of the base circle, through the pitch point."""
    a = math.radians(g.pressure_angle_deg)
    psi = (g.t_pitch / 2.0) / g.rp
    inv = lambda x: math.tan(x) - x
    inv_p = inv(a)                                   # involute function at the pitch pressure angle
    r_lo = max(g.rb + 1e-4, g.rf)                    # involute only exists at r >= base radius
    r_hi = g.rp + g.tip_frac * (g.ra - g.rp)
    pts = []
    for r in np.linspace(r_lo, r_hi, n):
        ar = math.acos(min(1.0, g.rb / r))
        th = -psi + (inv(ar) - inv_p)                # angular half-thickness shrinks with r (thins
        pts.append((r * math.cos(th), r * math.sin(th)))  # toward the tip — the involute relation)
    # below the base circle, drop radially to the root circle
    if r_lo > g.rf + 1e-6:
        th0 = -psi + (inv(math.acos(min(1.0, g.rb / r_lo))) - inv_p)
        pts.insert(0, (g.rf * math.cos(th0), g.rf * math.sin(th0)))
    return pts


def tooth_outline(g: GearSpec) -> list:
    """Full 2D gear outline (CCW point list) for all z teeth, ready to extrude."""
    pitch = 2 * math.pi / g.z
    if g.profile == "trapezoid":
        root_r, tip_r = _trapezoid_flank(g)
        right = [root_r, tip_r]
    else:
        right = _involute_flank(g)
    left = [(x, -y) for (x, y) in reversed(right)]   # mirror across +X -> left flank, tip->root
    tip_r, tip_l = right[-1], left[0]
    ang = lambda p: math.atan2(p[1], p[0])
    pts = []
    for i in range(g.z):
        c = i * pitch
        seg = [_rot(p, c) for p in right]                                  # up the right flank
        seg += [_rot(p, c) for p in _arc(g.ra, ang(tip_r), ang(tip_l), 4)] # rounded tip @ ra
        seg += [_rot(p, c) for p in left]                                  # down the left flank
        # root arc from this tooth's left root to the next tooth's right root
        a_from = c + ang(left[-1])
        a_to = (i + 1) * pitch + ang(right[0])
        seg += _arc(g.rf, a_from, a_to, 4)
        pts += seg
    return pts


def tooth_flanks(g: GearSpec):
    """The two working flanks of a tooth centred on +X, each as a polyline root→tip. Used to place
    collision wedges (the drive/coast contact surfaces). right = below +X, left = mirror above."""
    if g.profile == "trapezoid":
        root_r, tip_r = _trapezoid_flank(g)
        right = [root_r, tip_r]
    else:
        right = _involute_flank(g)
    left = [(x, -y) for (x, y) in right]
    return right, left


def build_gear(g: GearSpec):
    """Extruded spur gear Solid, axis = +Z, centred at origin, bottom face at z=0."""
    face = Polygon(*tooth_outline(g), align=None)
    return extrude(face, amount=g.face_width)


def mesh_centres(g1: GearSpec, g2: GearSpec) -> float:
    """Ideal centre distance for two meshing gears (same module): (z1+z2)·m/2 = rp1+rp2."""
    return g1.rp + g2.rp


if __name__ == "__main__":
    import sys
    prof = sys.argv[1] if len(sys.argv) > 1 else "trapezoid"
    p = GearSpec(z=12, profile=prof)
    w = GearSpec(z=24, profile=prof)
    gp, gw = build_gear(p), build_gear(w)
    print(f"profile={prof}")
    print(f"  pinion z=12: rp={p.rp} ra={p.ra} rf={p.rf} rb={p.rb:.3f}  vol={gp.volume:.1f} mm³  "
          f"solids={len(gp.solids())}")
    print(f"  gear   z=24: rp={w.rp} ra={w.ra} rf={w.rf} rb={w.rb:.3f}  vol={gw.volume:.1f} mm³  "
          f"solids={len(gw.solids())}")
    print(f"  centre distance = {mesh_centres(p, w)} mm ; module {p.m}, backlash {p.backlash} mm")
