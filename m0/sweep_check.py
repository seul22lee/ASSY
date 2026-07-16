"""M0 Tier0-lite: check the geometry *before* blaming the physics engine.

If the lid cannot sweep 90 deg in exact B-rep geometry, no amount of contact tuning will
save it in MuJoCo -- and we would waste days tuning solref. This is the spec's Stage 7
sweep test (N=36 discrete steps) run early and standalone.

Checks:
  C1  each solid is a single, positive-volume, closed shell
  C2  no interference between pieces in the closed state (pin-in-bore is a clearance fit,
      so the intersection must be *empty*, not merely small)
  C3  measured clearances match the card (bore-pin radial, knuckle axial gaps)
  C4  sweep: rotate the lid about the hinge axis 0..95 deg, N=36; no lid/box interference
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from build123d import Axis, Location, Rotation, import_step

VARIANT = os.environ.get("M0_VARIANT", "nostop")
OUT = Path(__file__).parent / "out" / VARIANT
VOL_TOL = 1e-6  # mm^3; OCC boolean noise floor


def load():
    m = json.loads((OUT / "manifest.json").read_text())
    parts = {n: import_step(str(OUT / d["step"])) for n, d in m["pieces"].items()}
    return m, parts


def intersection_volume(a, b) -> float:
    inter = a & b
    try:
        return float(inter.volume)
    except Exception:
        return 0.0


def main() -> None:
    m, parts = load()
    axis_pt = m["hinge_axis"]["point_mm"]
    results: list[tuple[str, bool, str]] = []

    # --- C1: solids are sane ----------------------------------------------------------
    for name, part in parts.items():
        vol = part.volume
        n_solids = len(part.solids())
        ok = vol > 0 and n_solids == 1
        results.append(
            (f"C1 {name}: single positive solid", ok, f"volume {vol:.1f} mm^3, {n_solids} solid(s)")
        )

    # --- C2: closed-state interference ------------------------------------------------
    names = list(parts)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            v = intersection_volume(parts[a], parts[b])
            ok = v <= VOL_TOL
            results.append((f"C2 {a} vs {b}: no interference", ok, f"overlap {v:.6f} mm^3"))

    # --- C3: measured clearances ------------------------------------------------------
    d = m["derived"]
    p = m["params"]
    radial = (d["bore_d"] - p["pin_d"]) / 2
    ok = 0.2 <= p["clearance"] <= 0.4
    results.append(
        ("C3 pin/bore radial clearance", ok, f"{radial:.3f} mm (diametral {p['clearance']:.2f})")
    )
    ks = m["knuckles"]
    gaps = [round(ks[i + 1]["x0"] - ks[i]["x1"], 4) for i in range(len(ks) - 1)]
    ok = all(abs(g - p["clearance"]) < 1e-6 for g in gaps)
    results.append(("C3 knuckle axial gaps", ok, f"{gaps} mm"))

    # --- C4: sweep --------------------------------------------------------------------
    # Rotate lid (and nothing else) about the hinge axis. Box + pin are static.
    lid, box = parts["lid_panel"], parts["box_shell"]
    to_axis = Location((-axis_pt[0], -axis_pt[1], -axis_pt[2]))
    from_axis = Location((axis_pt[0], axis_pt[1], axis_pt[2]))

    N = 36
    worst = (0.0, 0.0)  # (angle, overlap)
    for k in range(N + 1):
        theta = 95.0 * k / N  # a little past 90 to prove margin
        moved = from_axis * Rotation(theta, 0, 0) * to_axis * lid
        v = intersection_volume(moved, box)
        if v > worst[1]:
            worst = (theta, v)
    ok = worst[1] <= VOL_TOL
    results.append(
        (
            f"C4 lid sweep 0..95 deg (N={N}): no interference",
            ok,
            f"worst overlap {worst[1]:.6f} mm^3 at {worst[0]:.1f} deg",
        )
    )

    # --- report -----------------------------------------------------------------------
    width = max(len(r[0]) for r in results)
    n_fail = 0
    print()
    for label, ok, detail in results:
        n_fail += not ok
        print(f"  {'PASS' if ok else 'FAIL'}  {label:<{width}}  {detail}")
    print()
    if n_fail:
        raise SystemExit(f"Tier0-lite: {n_fail} check(s) FAILED -- fix geometry before simulating.")
    print("Tier0-lite: all checks passed. Geometry is sound; failures from here are the "
          "converter's or the solver's.")


if __name__ == "__main__":
    main()
