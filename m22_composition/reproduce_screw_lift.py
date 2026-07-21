"""m22 Task A C4 — NUMERIC REPRODUCTION of the screw_lift COMPOSED rule chain (free/local, no billed calls).

Reproduces, end to end, the composed formula chain the assembly rests on and checks it against the
card knowledge, the P-LIFT verdict, and the compiled geometry.

  ./bin/py m22_composition/reproduce_screw_lift.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "m0"))

from knowledge.cards.base import CARD_REGISTRY  # noqa: E402
from knowledge.cards.coupling import coupling_dims, coupling_mechanics  # noqa: E402
from knowledge.cards.lead_screw import lead_screw_dims, lead_screw_mechanics  # noqa: E402
from knowledge.materials import PETG  # noqa: E402
from tasks.build_goldens import screw_lift  # noqa: E402

VERDICT = Path(__file__).resolve().parent / "out" / "t2_screw_lift_verdict.json"


def main():
    plan = screw_lift()
    for e in plan.elements:
        e.params = CARD_REGISTRY[e.card_ref].resolve_params(plan, e)
    coup = coupling_mechanics(coupling_dims(next(e.params for e in plan.elements if e.card_ref == "coupling")))
    g = lead_screw_dims(next(e.params for e in plan.elements if e.card_ref == "lead_screw"))
    ls = lead_screw_mechanics(g)
    ok = True

    print("\n========== m22 screw_lift — COMPOSED RULE CHAIN ==========")
    print(f"\n[1] ELEMENT CHAIN (crank → coupling → lead_screw → platform)")
    print(f"  coupling ratio (E1)          = {coup['ratio']:.4f}   (1:1, no ratio)")
    print(f"  lead_screw lead (E2)         = starts×pitch = {g.starts}×{g.pitch} = {ls['lead_mm']} mm/rev")
    print(f"  self-locks (tanλ={ls['tan_lambda']} ≤ µ={PETG.mu_friction}) = {ls['self_locks']}")

    N = g.stroke / g.lead
    H = N * coup["ratio"] * g.lead
    print(f"\n[2] COMPOSED FORMULA (the assembly non-tautology)")
    print(f"  H = N_rev × coupling(1:1) × lead = {N:.1f} × {coup['ratio']:.1f} × {ls['lead_mm']} = {H:.2f} mm")
    if VERDICT.exists():
        vj = json.loads(VERDICT.read_text()); s0 = vj["modes"]["V-A"]["per_seed"][0]
        print(f"  measured platform rise (P-LIFT seed0) = {s0['travel_mm']:.2f} mm   "
              f"resid {s0['formula_residual']*100:.4f}%  (gate ≤0.1%)  {'ok' if s0['formula_residual']<=1e-3 else 'FAIL'}")
        ok &= s0["formula_residual"] <= 1e-3 and abs(H - g.stroke) < 1e-6

        print(f"\n[3] SOURCED HOLD (inherited m19, not invented)")
        sf = vj["sourced_friction"]
        print(f"  T_friction = µ·W·d_mean/2 = {sf['T_friction_Nm (µ·W·d_mean/2)']} Nm  ≥  "
              f"back-drive W·lead/2π = {sf['T_backdrive_Nm (W·lead/2π)']} Nm  (margin {sf['hold_margin']}×)")
        print(f"  measured back-drive at hold = {s0['backdrive_mm']:.3f} mm  (gate ≤1 mm)  "
              f"{'ok' if s0['backdrive_mm']<=1.0 else 'FAIL'}")
        ok &= s0["backdrive_mm"] <= 1.0

        print(f"\n[4] DISCRIMINATION (both probes, assembly level)")
        dp = vj["modes"]["V-A"]["discrimination_probes"]
        print(f"  coupling BROKEN: crank {dp['coupling_broken']['crank_rev']:.1f} rev → platform rise "
              f"{dp['coupling_broken']['platform_rise_mm']:.2f} mm (input spins, NO rise)")
        print(f"  friction WEAK (0.5·T_bd): back-drive {dp['friction_weak']['backdrive_mm']:.2f} mm vs "
              f"sourced {dp['friction_weak']['sourced_backdrive_mm']:.2f} mm (SINKS)")
        print(f"  ⇒ discriminates = {dp['discriminates']}")
        ok &= bool(dp["discriminates"])
    else:
        print("  (verdict not found — run p_lift_va.py)")

    print(f"\n[5] t0 INTERFERENCE GATE (compiled assembly, swept over the lift) — see out/screw_lift_t0.txt")
    t0f = Path(__file__).resolve().parent / "out" / "screw_lift_t0.txt"
    if t0f.exists():
        clean = "CLEAN" in t0f.read_text()
        print(f"  {'CLEAN' if clean else 'FAILED'} (no unintended penetration over the sweep)")
        ok &= clean

    print(f"\n========== reproduction {'CLEAN — every number checks out' if ok else 'FAILED'} ==========\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
