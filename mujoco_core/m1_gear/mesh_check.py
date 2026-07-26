"""M1 Tier0-lite: check the mesh geometry BEFORE blaming the physics engine (the analog of
m0/sweep_check.py). If the teeth cannot roll through engagement in exact B-rep — interfering by
more than backlash, or gapping out — no contact tuning will save it in MuJoCo.

  C1  each gear is a single positive-volume solid
  C2  meshed at the ideal centre distance with the drive flanks in contact, the two solids do not
      interfere by more than a numerical tolerance (a backlash clearance fit, not a jam)
  C3  rolling the pinion through one full tooth engagement (conjugate rotation of the gear), the
      peak interference stays bounded — the profiles roll, they do not gouge
  render: top-down outline overlay (drive flank contact), saved to out/mesh_check_<profile>.png
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from build123d import Pos, Rot

from gear_geom import GearSpec, build_gear, mesh_centres, tooth_outline

OUT = Path(__file__).parent / "out"


def _placed_outline(g: GearSpec, cx, cy, rot_deg):
    a = math.radians(rot_deg)
    c, s = math.cos(a), math.sin(a)
    return [(cx + c * x - s * y, cy + s * x + c * y) for (x, y) in tooth_outline(g)]


def _interf_volume(gp, gw, cd, phase_deg):
    """Intersection volume of pinion (origin) and gear (at +X, rotated by phase) — 0 = clearance."""
    pin = gp
    gear = Pos(cd, 0, 0) * Rot(0, 0, phase_deg) * gw
    inter = pin & gear
    return inter.volume if inter.solids() else 0.0


def check(profile="trapezoid"):
    p, w = GearSpec(z=12, profile=profile), GearSpec(z=24, profile=profile)
    gp, gw = build_gear(p), build_gear(w)
    cd = mesh_centres(p, w)
    results = []

    # C1
    for nm, g in (("pinion", gp), ("gear", gw)):
        ok = len(g.solids()) == 1 and g.volume > 0
        results.append((f"C1 {nm} single positive solid", ok, f"{len(g.solids())} solid(s)"))

    # meshing phase: the gear gap must face the pinion. Sweep phase to find the contact with the
    # least (but touching) interference — the drive-flank seating point.
    half_pitch_w = 360.0 / w.z / 2.0
    phases = np.linspace(-half_pitch_w, half_pitch_w, 41)
    vols = [_interf_volume(gp, gw, cd, ph) for ph in phases]
    k = int(np.argmin(vols))
    phase0, v0 = float(phases[k]), vols[k]
    results.append(("C2 meshed interference ~ 0 (clearance fit)", v0 < 2.0,
                    f"min {v0:.3f} mm³ at phase {phase0:+.2f}° (backlash gives a touching fit)"))

    # C3 roll through one full tooth engagement: rotate pinion by ±half a pinion pitch, rotate the
    # gear conjugately (−θ·z1/z2), track peak interference.
    half_pitch_p = 360.0 / p.z / 2.0
    peak = 0.0
    for dth in np.linspace(-half_pitch_p, half_pitch_p, 21):
        pin = Rot(0, 0, dth) * gp
        gear = Pos(cd, 0, 0) * Rot(0, 0, phase0 - dth * p.z / w.z) * gw
        inter = pin & gear
        peak = max(peak, inter.volume if inter.solids() else 0.0)
    results.append(("C3 roll-through peak interference bounded", peak < 12.0,
                    f"peak {peak:.3f} mm³ over one tooth engagement"))

    # render
    fig, ax = plt.subplots(figsize=(7, 5))
    po = _placed_outline(p, 0, 0, 0)
    wo = _placed_outline(w, cd, 0, phase0)
    ax.fill(*zip(*po), facecolor="#7fb2e5", edgecolor="#1a365d", lw=0.6, alpha=0.75, label="pinion z=12")
    ax.fill(*zip(*wo), facecolor="#f6c453", edgecolor="#7b341e", lw=0.6, alpha=0.75, label="gear z=24")
    for r, cx in [(p.rp, 0), (w.rp, cd)]:
        ax.add_patch(plt.Circle((cx, 0), r, fill=False, ls="--", ec="#888", lw=0.7))
    ax.plot([p.rp], [0], "kx"); ax.plot([cd - w.rp], [0], "k+")  # pitch point ~ contact
    ax.set_aspect("equal"); ax.set_title(f"gear pair mesh — {profile}  (centre {cd} mm, "
                                         f"backlash {p.backlash} mm)", fontsize=10)
    ax.legend(fontsize=8, loc="upper right"); ax.grid(alpha=0.2)
    ax.set_xlim(-16, cd + 28); ax.set_ylim(-28, 28)
    fig.tight_layout(); fig.savefig(OUT / f"mesh_check_{profile}.png", dpi=130); plt.close(fig)

    print(f"\n=== M1 mesh-check  profile={profile} ===")
    ok_all = True
    for name, ok, det in results:
        ok_all &= ok
        print(f"  {'PASS' if ok else 'FAIL'}  {name:<44s} {det}")
    print(f"  -> {'ALL PASS' if ok_all else 'FAIL'}   (render: out/mesh_check_{profile}.png)")
    return ok_all, phase0


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    check(sys.argv[1] if len(sys.argv) > 1 else "trapezoid")
