"""m20 Stage 5 — NUMERIC REPRODUCTION CHAIN for coupling.

Reproduces, from independent arithmetic, every number the milestone rests on, and checks each against
the card, the P-COUPLING verdict, and the compiled geometry:

  1. the rule chain (Shigley §3-12 + hub proportions): T_rated = τ·π·bore³/16, hub OD ≥ 2·bore,
     hub length ≥ 1.5·bore, ratio 1.0 — each printed as formula = value, cross-checked vs the card;
  2. the SOURCED load: T_load = load_fraction · T_rated (N·mm → N·m) — the resisting torque is a design
     fraction of the rated torque, NOT invented (the D-D-1 lesson);
  3. the V-A measured numbers (from the verdict): ratio residual (≤0.1%), torque-transmission residual
     (≤5% — the non-tautology), and the discrimination (intact tracks vs broken stalls);
  4. a t1 COMPILE_DRIFT re-measure: compiled bounding-box extents vs the card/template INTENT
     — |IR − measured| ≤ 0.05 mm.

Free/local (no LLM, no billed calls). Run:  ./bin/py m20_coupling/reproduce.py
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
from knowledge.cards.coupling import coupling_dims, coupling_mechanics  # noqa: E402
from knowledge.templates import TEMPLATES  # noqa: E402
from pipeline.compile_assembly import compile_assembly  # noqa: E402
from tasks.build_goldens import coupling_fixture  # noqa: E402
from verify.t1_remeasure import DRIFT_TOL  # noqa: E402

VERDICT = Path(__file__).resolve().parent / "out" / "t2_coupling_verdict.json"


def _row(name, formula, value, unit=""):
    print(f"  {name:<22s} {formula:<30s} = {value:>10.4f} {unit}")


def main():
    plan = coupling_fixture()
    e1 = plan.element("E1")
    e1.params = CARD_REGISTRY["coupling"].resolve_params(plan, e1)
    g = coupling_dims(e1.params)
    mech = coupling_mechanics(g)
    ok = True

    print("\n========== m20 coupling — NUMERIC REPRODUCTION CHAIN ==========")
    print(f"\n[1] RULE CHAIN (Shigley §3-12 + hub proportions)   inputs: bore_d={g.bore_d} "
          f"τ_allow={g.tau_allow} MPa, body_d={g.body_d}, length={g.length} mm")
    T = g.tau_allow * math.pi * (g.bore_d ** 3) / 16.0
    _row("rated torque", "τ·π·bore³/16", T, "N·mm")
    _row("hub OD (min)", "2·bore", 2 * g.bore_d, "mm")
    _row("hub length (min)", "1.5·bore", 1.5 * g.bore_d, "mm")
    _row("ratio", "1 (no ratio)", mech["ratio"], "")
    for k, v in [("torque_capacity_Nmm", T), ("hub_od_min_mm", 2 * g.bore_d),
                 ("hub_len_min_mm", 1.5 * g.bore_d), ("ratio", 1.0)]:
        d = abs(mech[k] - v)
        ok &= d < 1e-2
        if d >= 1e-2:
            print(f"  !! card {k}={mech[k]} != hand {v}")
    print(f"  hub proportions hold: body_d {g.body_d} ≥ {2*g.bore_d} ({mech['body_d_ok']}) ; "
          f"length {g.length} ≥ {1.5*g.bore_d} ({mech['length_ok']})")
    ok &= mech["body_d_ok"] and mech["length_ok"]

    print(f"\n[2] SOURCED LOAD   (resisting torque = a design fraction of RATED — not invented)")
    if VERDICT.exists():
        vj = json.loads(VERDICT.read_text())
        sl = vj["sourced_load"]
        print(f"  T_rated = {sl['T_rated_Nm']} N·m ( = {T:.2f} N·mm / 1000 )")
        print(f"  T_load  = load_fraction · T_rated = {sl['load_fraction']} · {sl['T_rated_Nm']} "
              f"= {sl['T_load_Nm (0.5·T_rated)']} N·m")
        ok &= abs(sl["T_rated_Nm"] - T * 1e-3) < 1e-4

    print(f"\n[3] P-COUPLING V-A MEASURED   (the non-tautology: ratio is weak, TORQUE transmission is real)")
    if VERDICT.exists():
        va = vj["modes"]["V-A"]; s0 = va["per_seed"][0]
        print(f"  ratio out/in = {s0['ratio']:.5f}   residual {s0['ratio_residual']*100:.4f}%   "
              f"(gate ≤ 0.1%)   {'ok' if s0['ratio_residual'] <= 1e-3 else 'FAIL'}")
        print(f"  torque transmitted {s0['T_meas_Nm']:.4f} vs applied {vj['sourced_load']['T_load_Nm (0.5·T_rated)']} "
              f"N·m   residual {s0['torque_residual']*100:.2f}%   (gate ≤ 5%)   "
              f"{'ok' if s0['torque_residual'] <= 0.05 else 'FAIL'}")
        ok &= s0["ratio_residual"] <= 1e-3 and s0["torque_residual"] <= 0.05
        dp = va["discrimination_probe"]
        print(f"  discrimination: coupled output {dp['intact_out_rev']:.2f} rev  vs  BROKEN output "
              f"{dp['broken_out_rev']:.2f} rev (input {dp['broken_in_rev']:.2f}) ⇒ "
              f"discriminates={dp['discriminates']}")
        ok &= bool(dp["discriminates"])
    else:
        print("  (verdict JSON not found — run p_coupling_va.py first)")

    print(f"\n[4] t1 COMPILE_DRIFT   (compiled geometry vs card/template intent, ≤ {DRIFT_TOL} mm)")
    ca = compile_assembly(plan)
    p1 = ca.parts["P1"].bounding_box().size    # base plate + input stub + hub
    p2 = ca.parts["P2"].bounding_box().size    # output shaft (undersized)
    ci = TEMPLATES["shaft_carrier_in"](**{k: v for k, v in plan.piece("P1").params.items()
                                          if isinstance(v, (int, float))}).params
    co = TEMPLATES["shaft_carrier_out"](**{k: v for k, v in plan.piece("P2").params.items()
                                          if isinstance(v, (int, float))}).params
    hub_top = ci["shaft_h"] - 4.0 + g.length   # overlap 4 (carve): hub top = shaft_h − overlap + length
    checks = [
        ("base_l (P1.x)", ci["base_l"], p1.X),
        ("base_w (P1.y)", ci["base_w"], p1.Y),
        ("hub_top (P1.z)", hub_top, p1.Z),
        ("out_len (P2.z)", co["shaft_len"], p2.Z),
        ("out_shaft_d (P2.x)", co["shaft_d"] - 2 * co["clearance"], p2.X),
    ]
    print(f"  {'dimension':<24s}{'intent':>9s}{'measured':>11s}{'drift':>9s}   ok")
    for name, intent, measured in checks:
        drift = abs(intent - measured)
        good = drift <= DRIFT_TOL
        ok &= good
        print(f"  {name:<24s}{intent:>9.3f}{measured:>11.3f}{drift:>9.4f}   {'ok' if good else 'FAIL'}")

    print(f"\n========== reproduction {'CLEAN — every number checks out' if ok else 'FAILED'} ==========\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
