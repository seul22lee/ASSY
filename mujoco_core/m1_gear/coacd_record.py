"""M1: CoACD-once on the pinion, for the record (MECHSYNTH §6.2 strategy (b); the D18 analog).

CoACD is the general convex-decomposition fallback for a part with no collision hint. Spec 6.2
ranks it BELOW primitive/wedge hints precisely because, like it did to M0's bore, it tends to fill
the concave features a mechanism is made of — here the tooth valleys. We run it once and measure how
much of the tooth-valley depth it preserves, then drop it (the wedge hint is the pathway we use).

Metric: cast rays from the pitch circle inward at each tooth valley and compare the CoACD hull wall
to the true root circle. A decomposition that fills the valley reports a wall at ~the pitch/outside
radius — the valley (working depth) is gone, so a mating tooth cannot enter = the mesh is lost.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "m0"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import trimesh

import gear_mjcf
from gear_geom import GearSpec, build_gear
from step2mjcf import MM, coacd_parts

OUT = Path(__file__).parent / "out"


def record():
    p = GearSpec(z=12, profile="involute")
    mesh = gear_mjcf._b123d_to_trimesh(build_gear(p))   # mm
    print(f"pinion mesh: {len(mesh.vertices)} verts, watertight={mesh.is_watertight}")
    parts = coacd_parts(mesh)
    hull = trimesh.util.concatenate(parts)
    print(f"CoACD -> {len(parts)} convex parts")

    # working depth check: at each tooth valley (mid-angle between two teeth), how deep does the
    # decomposition let a mating tooth reach? Sample the hull's radial extent at valley angles.
    # Everything here is in MILLIMETRES (the hull mesh from build123d is mm — no MM scaling).
    valley_ok, samples = 0, []
    for i in range(p.z):
        ang = 2 * np.pi * (i + 0.5) / p.z           # a tooth valley (between teeth)
        d = np.array([np.cos(ang), np.sin(ang)])
        # ray from outside inward along -d; first hit = outer wall; we want it to reach ~root radius
        origin = np.array([d[0] * (p.ra + 5), d[1] * (p.ra + 5), p.face_width / 2])   # mm
        locs, _, _ = hull.ray.intersects_location([origin], [[-d[0], -d[1], 0]])
        if len(locs):
            r_hit = float(np.hypot(locs[:, 0], locs[:, 1]).min())
        else:
            r_hit = p.ra + 5                          # no hit at this valley angle
        # valley preserved if the hull lets a ray reach near the true root (within a tooth's addendum)
        preserved = r_hit <= p.rp                    # reached at least the pitch line inward
        valley_ok += preserved
        samples.append(round(float(r_hit), 2))
    frac = valley_ok / p.z
    print(f"tooth valleys reaching >= pitch line: {valley_ok}/{p.z}  (root r={p.rf}, pitch r={p.rp})")
    print(f"  valley wall radii (mm): {samples}")
    rec = {"n_parts": len(parts), "root_r_mm": p.rf, "pitch_r_mm": p.rp, "tip_r_mm": p.ra,
           "valleys_preserved": int(valley_ok), "z": p.z, "valley_wall_r_mm": samples,
           "verdict": ("valleys open — CoACD kept the working depth"
                       if frac > 0.8 else
                       "CLEARANCE-RETENTION FAILURE — CoACD filled the tooth valleys (expected, "
                       "spec 6.2 / D18): a mating tooth cannot enter, so the mesh is lost. The wedge "
                       "hint is used instead.")}
    (OUT / "coacd_pinion.json").write_text(json.dumps(rec, indent=2))
    print(f"\n{rec['verdict']}")
    return rec


if __name__ == "__main__":
    record()
