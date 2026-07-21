"""m21 Stage 5 — NUMERIC REPRODUCTION CHAIN for universal_joint.

Reproduces, from independent arithmetic, every number the milestone rests on, and checks each against
the card, the P-UJOINT verdict, and the compiled geometry:

  1. the Cardan rule chain (P&B §8.1): β, band [cos β, 1/cos β], fluctuation %, mean 1:1 — cross-checked;
  2. the FLUCTUATION AMPLITUDE + PHASE measured vs formula (from the verdict): band, overlay residual,
     and the geometric phase φ0 (predicted 90° vs measured);
  3. the DISCRIMINATION: β=0 flattens the band to ~[1,1] (the pulsation vanishes with the angle);
  4. a t1 COMPILE_DRIFT re-measure: compiled bounding-box extents (incl. the β-tilt projection of the
     output shaft) vs the card/template INTENT — |IR − measured| ≤ 0.05 mm.

Free/local (no LLM, no billed calls). Run:  ./bin/py m21_universal_joint/reproduce.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "m0"))

from knowledge.cards.base import CARD_REGISTRY  # noqa: E402
from knowledge.cards.universal_joint import ujoint_dims, ujoint_kinematics  # noqa: E402
from pipeline.compile_assembly import compile_assembly  # noqa: E402
from tasks.build_goldens import ujoint_fixture  # noqa: E402
from verify.t1_remeasure import DRIFT_TOL  # noqa: E402

VERDICT = Path(__file__).resolve().parent / "out" / "t2_ujoint_verdict.json"
_YOKE_OVERLAP_MM = 3.0   # from ujoint_carve


def main():
    plan = ujoint_fixture()
    e1 = plan.element("E1")
    e1.params = CARD_REGISTRY["universal_joint"].resolve_params(plan, e1)
    g = ujoint_dims(e1.params)
    k = ujoint_kinematics(g)
    beta = math.radians(g.angle_deg)
    ok = True

    print("\n========== m21 universal_joint — NUMERIC REPRODUCTION CHAIN ==========")
    print(f"\n[1] CARDAN RULE CHAIN (P&B §8.1)   β = {g.angle_deg}°")
    band = [math.cos(beta), 1.0 / math.cos(beta)]
    print(f"  vel ratio min   cos β            = {band[0]:.4f}")
    print(f"  vel ratio max   1/cos β          = {band[1]:.4f}")
    print(f"  fluctuation     (1/cosβ − cosβ)  = {(band[1]-band[0])*100:.2f} %")
    print(f"  mean over a rev                  = {k['mean_ratio']:.4f} (exactly 1:1)")
    for key, val in [("vel_ratio_min", band[0]), ("vel_ratio_max", band[1]), ("mean_ratio", 1.0)]:
        if abs(k[key] - val) >= 1e-2:
            print(f"  !! card {key}={k[key]} != hand {val}"); ok = False

    print(f"\n[2] FLUCTUATION measured vs formula (the discovery criterion)")
    if VERDICT.exists():
        vj = json.loads(VERDICT.read_text())
        s0 = vj["modes"]["V-A"]["per_seed"][0]
        print(f"  measured band {s0['measured_band']} vs formula [{band[0]:.4f}, {band[1]:.4f}]")
        print(f"  overlay residual max|meas−formula| = {s0['fluct_residual']*100:.3f}%   (gate ≤ 2%)   "
              f"{'ok' if s0['fluct_residual'] <= 0.02 else 'FAIL'}")
        print(f"  phase φ0 predicted {s0['phi0_predicted_deg']}° vs measured {s0['phi0_measured_deg']}°  "
              f"→ phase err {s0['phase_err_deg']}° (amplitude AND phase)")
        print(f"  mean ratio {s0['mean_ratio']} (resid {s0['mean_residual']*100:.4f}%)")
        ok &= s0["fluct_residual"] <= 0.02 and s0["mean_residual"] <= 0.001
        ok &= abs(s0["measured_band"][0] - band[0]) < 0.01 and abs(s0["measured_band"][1] - band[1]) < 0.01

        print(f"\n[3] DISCRIMINATION (β=0 flattens the pulsation)")
        dp = vj["modes"]["V-A"]["discrimination_probe"]
        print(f"  β={g.angle_deg}° band {dp['measured_band_at_angle']}  vs  β=0 band {dp['beta0_measured_band']} "
              f"(β=0 fluctuation {dp['beta0_fluctuation_pct']}%)  ⇒ discriminates={dp['discriminates']}")
        ok &= bool(dp["discriminates"])
    else:
        print("  (verdict JSON not found — run p_ujoint_va.py first)")

    print(f"\n[4] t1 COMPILE_DRIFT   (compiled geometry vs intent, incl. the β-tilt, ≤ {DRIFT_TOL} mm)")
    ca = compile_assembly(plan)
    p1 = ca.parts["P1"].bounding_box().size
    p2 = ca.parts["P2"].bounding_box().size
    ci = plan.piece("P1").params; co = plan.piece("P2").params
    jz = ci["shaft_h"]; L = co["shaft_len"]; sd = co["shaft_d"] - 2 * co["clearance"]
    yoke_top = jz - _YOKE_OVERLAP_MM + g.length
    # tilted-cylinder bbox projections (axis at β from +Z): Z = L·cosβ + d·sinβ, X = L·sinβ + d·cosβ
    out_z = L * math.cos(beta) + sd * math.sin(beta)
    out_x = L * math.sin(beta) + sd * math.cos(beta)
    checks = [
        ("base_l (P1.x)", ci["base_l"], p1.X),
        ("base_w (P1.y)", ci["base_w"], p1.Y),
        ("yoke_top (P1.z)", yoke_top, p1.Z),
        ("out_bbox_z (L·cosβ+d·sinβ)", out_z, p2.Z),
        ("out_bbox_x (L·sinβ+d·cosβ)", out_x, p2.X),
    ]
    print(f"  {'dimension':<28s}{'intent':>9s}{'measured':>11s}{'drift':>9s}   ok")
    for name, intent, measured in checks:
        drift = abs(intent - measured); good = drift <= DRIFT_TOL; ok &= good
        print(f"  {name:<28s}{intent:>9.3f}{measured:>11.3f}{drift:>9.4f}   {'ok' if good else 'FAIL'}")

    print(f"\n========== reproduction {'CLEAN — every number checks out' if ok else 'FAILED'} ==========\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
