"""m24 Phase A (§14 T6) — latched_drawer (bottom-clip) NUMERIC REPRODUCTION + COMPILE_DRIFT table.

Reproduces the sourced dimension chain (dim_chain) and the Bayer W_out, then RE-MEASURES the key
dimensions from the COMPILED solids and reports design-vs-measured drift. A dimension that drifts is a
carve/compile bug; ≤0.10 mm is CLEAN.

  ./bin/py m24_design_closure/reproduce_latched_drawer.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "m0")); sys.path.insert(0, str(ROOT / "m24_design_closure"))

from dim_chain import chain  # noqa: E402
from knowledge.cards.snap_hook import P_deflect, W_sep, solve_h  # noqa: E402
from knowledge.templates.host_templates import latch_design_parts  # noqa: E402


def _yspan(part):
    bb = part.bounding_box(); return bb.max.Y - bb.min.Y


def _zmax(part):
    return part.bounding_box().max.Z


def main():
    c = chain(); g = c["geom"]
    parts = latch_design_parts()
    lines = ["=== latched_drawer (bottom-clip) — REPRODUCTION (§14 T6) ===", ""]
    # 1) the sourced CLIP chain reproduced independently
    h = solve_h(0.02, g["clip_L"], g["undercut"], 2)
    P = P_deflect(g["clip_b"], h, 1815.0, 0.02, g["clip_L"])
    W = W_sep(P, g["mu"], g["alpha_out"])
    lines.append(f"[1] CLIP inverse-Bayer reproduced: solve_h={h:.3f} mm, P={P:.2f} N, "
                 f"W_out={W:.2f} N  (chain W_out={g['W_out']:.2f})  "
                 f"{'OK' if abs(W - g['W_out']) < 0.01 else 'DRIFT!'}")
    lines.append("")
    # 2) RE-MEASURE the compiled geometry vs the design chain
    meas = {
        "cabinet outer W_c": (_yspan(parts["cabinet_body"]), g["W_c"]),
        "front panel W_p": (_yspan(parts["drawer_body"]), g["W_p"]),
        "bump height": (_zmax(parts["bump"]), g["bump_h"]),
    }
    lines.append(f"[2] COMPILE_DRIFT — re-measured from the compiled solids:")
    lines.append(f"  {'quantity':<22s}{'design':>9s}{'measured':>10s}{'drift':>8s}")
    max_drift = 0.0
    for name, (m, d) in meas.items():
        drift = abs(m - d); max_drift = max(max_drift, drift)
        lines.append(f"  {name:<22s}{d:>9.3f}{m:>10.3f}{drift:>8.3f}   {'OK' if drift <= 0.10 else 'DRIFT!'}")
    lines.append("")
    lines.append(f"  max COMPILE_DRIFT = {max_drift:.3f} mm   ({'CLEAN ≤0.10' if max_drift <= 0.10 else 'DRIFT!'})")
    ok = (abs(W - g["W_out"]) < 0.01) and (max_drift <= 0.10)
    lines.append(f"  => reproduction {'CLEAN' if ok else 'FAILED'}")
    out = "\n".join(lines)
    (ROOT / "m24_design_closure" / "out" / "reproduce_latched_drawer.txt").write_text(out + "\n")
    print(out)
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
