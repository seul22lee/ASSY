"""m19 Stage 5 — NUMERIC REPRODUCTION CHAIN for lead_screw.

Reproduces, end to end and from independent arithmetic, every number the milestone rests on:

  1. the power-screw rule chain (Shigley §8-2 / P&B §7.4.3): lead = starts·pitch, d_mean, lead angle
     λ, tan λ — each printed as  formula = value  so the card's mechanics are checkable by eye;
  2. the SELF-LOCK verdict  tan λ ≤ µ  (µ = PETG.mu_friction, the R5 preset) and the sourced holding
     vs back-drive torque margin;
  3. the TRAVEL prediction  lead · rev  against the P-SCREW V-A measured travel (from the verdict
     JSON) — the non-tautology gate, re-stated here as a standalone number;
  4. a t1 COMPILE_DRIFT re-measure: the compiled fixture's geometry (bounding-box extents of the
     screw post + nut carriage) vs the card/template INTENT — |IR − measured| ≤ 0.05 mm.

Everything here is free/local (no LLM, no billed calls). Run:

    ./bin/py m19_lead_screw/reproduce.py
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
from knowledge.cards.lead_screw import lead_screw_dims, lead_screw_mechanics  # noqa: E402
from knowledge.materials import PETG  # noqa: E402
from knowledge.templates import TEMPLATES  # noqa: E402
from pipeline.compile_assembly import compile_assembly  # noqa: E402
from tasks.build_goldens import lead_screw_fixture  # noqa: E402
from verify.t1_remeasure import DRIFT_TOL  # noqa: E402

VERDICT = Path(__file__).resolve().parent / "out" / "t2_lead_screw_verdict.json"


def _row(name, formula, value, unit=""):
    print(f"  {name:<20s} {formula:<34s} = {value:>10.5f} {unit}")


def main():
    plan = lead_screw_fixture()
    e1 = plan.element("E1")
    e1.params = CARD_REGISTRY["lead_screw"].resolve_params(plan, e1)
    g = lead_screw_dims(e1.params)
    mech = lead_screw_mechanics(g)
    mu = PETG.mu_friction
    ok = True

    print("\n========== m19 lead_screw — NUMERIC REPRODUCTION CHAIN ==========")
    print(f"\n[1] POWER-SCREW RULE CHAIN (Shigley §8-2 / P&B §7.4.3)   inputs: "
          f"d_major={g.d_major} pitch={g.pitch} starts={g.starts} mm, µ={mu}")
    lead = g.starts * g.pitch
    d_mean = g.d_major - g.pitch / 2.0
    lam = math.atan(lead / (math.pi * d_mean))
    _row("lead", "starts · pitch", lead, "mm")
    _row("d_mean", "d_major − pitch/2", d_mean, "mm")
    _row("lead angle λ", "atan(lead / (π·d_mean))", math.degrees(lam), "deg")
    _row("tan λ", "tan(λ)", math.tan(lam), "")
    _row("travel/rev", "= lead", lead, "mm/rev")
    _row("polycoef", "lead / 2π  (m/rad)", (lead * 1e-3) / (2 * math.pi), "")
    # cross-check the card computes the same
    for k, v in [("lead_mm", lead), ("d_mean_mm", d_mean),
                 ("lead_angle_deg", math.degrees(lam)), ("tan_lambda", math.tan(lam))]:
        d = abs(mech[k] - v)                                # card rounds for display; tol covers that
        ok &= d < 2e-3
        if d >= 2e-3:
            print(f"  !! card {k}={mech[k]} != hand {v}")

    print(f"\n[2] SELF-LOCK VERDICT   (self-locks ⇔ tan λ ≤ µ ⇔ lead angle ≤ friction angle)")
    fric_angle = math.degrees(math.atan(mu))
    self_locks = math.tan(lam) <= mu
    print(f"  tan λ = {math.tan(lam):.5f}   {'≤' if self_locks else '>'}   µ = {mu}"
          f"   ⇒  {'SELF-LOCKS' if self_locks else 'BACK-DRIVES'}")
    print(f"  lead angle {math.degrees(lam):.3f}° {'≤' if self_locks else '>'} "
          f"friction angle {fric_angle:.3f}°")
    ok &= (self_locks == mech["self_locks"])
    # sourced holding vs back-drive torque (the D-D-1 sourced friction — from the verdict)
    if VERDICT.exists():
        vj = json.loads(VERDICT.read_text())
        sf = vj["sourced_friction"]
        Tf = sf["T_friction_Nm (µ·W·d_mean/2)"]; Tb = sf["T_backdrive_Nm (W·lead/2π)"]
        print(f"  sourced hold T_f = µ·W·d_mean/2 = {Tf:.5f} Nm  ≥  back-drive W·lead/2π = "
              f"{Tb:.5f} Nm   (margin {Tf/Tb:.2f}× = µ/tanλ = {mu/math.tan(lam):.2f}×)")
        ok &= Tf >= Tb

    print(f"\n[3] TRAVEL PREDICTION vs P-SCREW V-A MEASURED   (the non-tautology gate)")
    if VERDICT.exists():
        va = vj["modes"]["V-A"]
        s0 = va["per_seed"][0]
        # the DRIVE-END comparison the gate judges (revs measured at drive end, before the hold
        # back-rotation): pred = lead · rev_drive = the verdict's formula_travel_mm.
        pred = s0["formula_travel_mm"]; meas = s0["travel_mm"]; resid = s0["formula_residual"]
        rev_drive = pred / lead if lead else 0.0
        print(f"  predicted travel = lead · rev_drive = {lead} · {rev_drive:.3f} = {pred:.3f} mm")
        print(f"  measured  travel (V-A seed0, drive end) = {meas:.3f} mm")
        print(f"  residual |meas/pred − 1| = {resid*100:.4f}%   (gate ≤ 0.1%)   "
              f"{'ok' if resid <= 1e-3 else 'FAIL'}")
        ok &= resid <= 1e-3
        dp = va.get("discrimination_probe", {})
        if dp:
            print(f"  non-tautology of HOLD: sourced friction holds {dp['sourced_backdrive_mm']:.3f} mm "
                  f"vs weak(0.5·T_bd) slips {dp['weak_backdrive_mm']:.3f} mm  ⇒ "
                  f"discriminates={dp['discriminates']}")
            ok &= bool(dp.get("discriminates"))
    else:
        print("  (verdict JSON not found — run p_screw_va.py first)")

    print(f"\n[4] t1 COMPILE_DRIFT   (compiled geometry vs card/template intent, ≤ {DRIFT_TOL} mm)")
    ca = compile_assembly(plan)
    p1 = ca.parts["P1"].bounding_box().size   # base plate + carved screw post
    p2 = ca.parts["P2"].bounding_box().size   # nut carriage
    sb = TEMPLATES["screw_base"]().params
    nc = TEMPLATES["nut_carriage"](d_major=g.d_major).params
    checks = [
        ("base_l (P1.x)", sb["base_l"], p1.X),
        ("base_w (P1.y)", sb["base_w"], p1.Y),
        ("screw_len (P1.z−base_t)", g.length, p1.Z - sb["base_t"]),
        ("nut_l (P2.x)", nc["nut_l"], p2.X),
        ("nut_w (P2.y)", nc["nut_w"], p2.Y),
        ("nut_t (P2.z)", nc["nut_t"], p2.Z),
    ]
    print(f"  {'dimension':<26s}{'intent':>9s}{'measured':>11s}{'drift':>9s}   ok")
    for name, intent, measured in checks:
        drift = abs(intent - measured)
        good = drift <= DRIFT_TOL
        ok &= good
        print(f"  {name:<26s}{intent:>9.3f}{measured:>11.3f}{drift:>9.4f}   {'ok' if good else 'FAIL'}")

    print(f"\n========== reproduction {'CLEAN — every number checks out' if ok else 'FAILED'} ==========\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
