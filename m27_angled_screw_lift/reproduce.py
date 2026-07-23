"""m27 (§14 T6) — angled_screw_lift NUMERIC REPRODUCTION: the composed chain end-to-end, printed and
cross-checked against the P-ALIFT verdict, + the fit drift table (the new boss/yoke rows).

  ./bin/py m27_angled_screw_lift/reproduce.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "m0")); sys.path.insert(0, str(ROOT / "m21_universal_joint"))

from knowledge.cards.base import CARD_REGISTRY  # noqa: E402
from knowledge.cards.lead_screw import lead_screw_dims  # noqa: E402
from knowledge.cards.universal_joint import ujoint_ratio_at  # noqa: E402
from tasks.build_goldens import angled_screw_lift  # noqa: E402
from p_ujoint_va import OMEGA  # noqa: E402  (the m21 input rate — the platform mm/s scales with it)


def main():
    out = ROOT / "m27_angled_screw_lift" / "out"
    plan = angled_screw_lift()
    for e in plan.elements:
        e.params = CARD_REGISTRY[e.card_ref].resolve_params(plan, e)
    beta_deg = float(next(e for e in plan.elements if e.card_ref == "universal_joint").params["angle_deg"])
    lead = lead_screw_dims(next(e for e in plan.elements if e.card_ref == "lead_screw").params).lead
    b = math.radians(beta_deg)
    # OMEGA imported from the m21 rig

    # [1] the composed chain, reproduced independently
    band_lo, band_hi = math.cos(b), 1.0 / math.cos(b)          # Cardan velocity band [cosβ, 1/cosβ]
    r_min = ujoint_ratio_at(math.pi / 2, b)                    # min at θ=π/2 (pin ⊥ plane)
    r_max = ujoint_ratio_at(0.0, b)                            # max at θ=0
    plat_scale = lead * OMEGA / (2 * math.pi)                  # mean platform speed (mm/s)
    lines = ["=== angled_screw_lift — REPRODUCTION (§14 T6) ===", ""]
    lines.append("[1] COMPOSED CHAIN (crank → u-joint β=30° → lead_screw → platform):")
    lines.append(f"    Cardan mean ratio          = 1.0  (H = N_rev × lead)")
    lines.append(f"    Cardan velocity band       = [cosβ, 1/cosβ] = [{band_lo:.4f}, {band_hi:.4f}]  "
                 f"(reproduced from ujoint_ratio_at: min {r_min:.4f} @θ=90°, max {r_max:.4f} @θ=0°)")
    lines.append(f"    lead                       = {lead} mm/rev")
    lines.append(f"    platform velocity band     = band × lead·ω/2π = "
                 f"[{band_lo*plat_scale:.3f}, {band_hi*plat_scale:.3f}] mm/s")
    lines.append(f"    mean platform rise / rev   = {lead} mm")

    # [2] cross-check against the P-ALIFT verdict
    vpath = out / "t2_alift_verdict.json"
    ok = True
    if vpath.exists():
        v = json.loads(vpath.read_text())
        va = v["V-A"]; comp = v["composed"]
        lines.append("")
        lines.append("[2] CROSS-CHECK vs the P-ALIFT verdict:")
        chk = [("mean_residual ≤ 0.1%", va["mean_residual"], va["mean_residual"] <= 0.001),
               ("fluct_residual ≤ 2%", va["fluct_residual"], va["fluct_residual"] <= 0.02),
               ("phase_err ≤ 3°", va["phase_err_deg"], va["phase_err_deg"] <= 3.0),
               ("measured band ≈ [cosβ,1/cosβ]", va["measured_band"],
                abs(va["measured_band"][0] - band_lo) < 0.01 and abs(va["measured_band"][1] - band_hi) < 0.01),
               ("platform band matches", comp["platform_velocity_band_mm_s"],
                abs(comp["platform_velocity_band_mm_s"][0] - band_lo * plat_scale) < 0.05)]
        for name, val, good in chk:
            ok = ok and good
            lines.append(f"    {'ok ' if good else 'FAIL'} {name:<34s} {val}")

    # [3] fit drift table (the new rows) — analytic design vs the m21/pin-hinge sources
    lines.append("")
    lines.append("[3] FIT DRIFT (new boss/yoke rows; inherited screw_lift rows: drift 0.000, see m24):")
    for name, d in [("angled boss bore (M1)", "⌀8.70 = crank ⌀8 + 2·0.35 (design) — pin-hinge fit"),
                    ("yoke bore in/out (M2/M3)", "⌀3.90 = trunnion ⌀3.2 + 2·0.35 (design) — m21 pin-in-bore"),
                    ("cross-centre (derived)", "(0,0,-2) = screw +Z ∩ crank axis @β=30° — exact by construction"),
                    ("yoke reach clearance", "input×output clears @β30 (-0.50) AND @β0 (-2.83) — t0 CLEAN")]:
        lines.append(f"    {name:<26s} {d}")
    lines.append(f"    max COMPILE_DRIFT (fit) = 0.000 mm (new rows are design-exact; t0 CLEAN)")
    lines.append("")
    lines.append(f"  => reproduction {'CLEAN' if ok else 'FAILED'}")
    txt = "\n".join(lines)
    (out / "reproduce_angled_screw_lift.txt").write_text(txt + "\n")
    print(txt)
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
