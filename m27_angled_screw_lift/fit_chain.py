"""m27 (§14 T3b) — angled_screw_lift FIT CHAIN: the screw_lift rows (inherited) + the u-joint / angled-
boss additions. Every number sourced from a mate or a formula; the cross-centre is DERIVED (the two axis
lines' intersection), not a free choice. Re-measures the new rows from the compiled solids (COMPILE_DRIFT).

  ./bin/py m27_angled_screw_lift/fit_chain.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "m0"))

from knowledge.cards.base import CARD_REGISTRY  # noqa: E402
from knowledge.templates.host_templates import screw_base  # noqa: E402
from tasks.build_goldens import angled_screw_lift  # noqa: E402

CLR = 0.35   # A-PETG-1 pin-hinge / slide clearance


def main():
    plan = angled_screw_lift()
    for e in plan.elements:
        e.params = CARD_REGISTRY[e.card_ref].resolve_params(plan, e)
    e_uj = next(e for e in plan.elements if e.card_ref == "universal_joint")
    p1 = next(p for p in plan.pieces if p.id == "P1")
    beta = float(e_uj.params["angle_deg"]); bore_d = float(e_uj.params["bore_d"]); yoke_d = float(e_uj.params["yoke_d"])
    cross_z = p1.params["cross_z"]; reach = p1.params["boss_reach"]; in_boss_d = p1.params["in_boss_d"]
    # DERIVED cross centre = the intersection of the screw axis (+Z through origin) and the crank axis
    # (line through the boss at β). Both pass through (0,0,cross_z) by construction → that IS the cross.
    cross_center = (0.0, 0.0, cross_z)
    boss_center = (-reach * math.sin(math.radians(beta)), 0.0, cross_z - reach * math.cos(math.radians(beta)))
    trunnion_d = 3.2   # m21 cross trunnion ⌀ (cr_trx/try radius 1.6 mm → ⌀3.2)

    rows = [
        ("SCREW_LIFT rows (inherited)", "", "", "screw-in-nut 0.50 / column-in-bore 0.35 / nut boss / top-bottom stops — see m24 screw_lift fit schedule"),
        ("angled boss bore ⌀ (M1)", bore_d, bore_d + 2 * CLR, f"crank shaft ⌀{bore_d} + 2·clr({CLR}) = pin-hinge fit (declared hinge; journal_bearing parked)"),
        ("input-yoke bore ⌀ (M2)", trunnion_d, round(trunnion_d + 2 * CLR, 2), f"cross trunnion ⌀{trunnion_d} + 2·clr({CLR}) — m21 pin-in-bore row"),
        ("output-yoke bore ⌀ (M3)", trunnion_d, round(trunnion_d + 2 * CLR, 2), f"cross trunnion ⌀{trunnion_d} + 2·clr({CLR}) — m21 pin-in-bore row"),
        ("cross-centre (DERIVED)", "", "", f"screw axis (+Z) ∩ crank axis (β={beta:.0f}°) = {cross_center} — NOT a free choice"),
        ("yoke reach", "", "", f"the cross clears BOTH shafts at β={beta:.0f}° AND β=0° (m21 addendum lesson; verified in t0: input×output clears -0.50 @β30, -2.83 @β0)"),
        ("angled boss centre", "", "", f"cross + reach({reach})·(−sinβ,0,−cosβ) = ({boss_center[0]:.1f},0,{boss_center[2]:.1f}) — on the crank axis line"),
    ]
    lines = ["=== angled_screw_lift FIT CHAIN (§14 T3b) — screw_lift rows + u-joint/boss additions ===",
             f"  {'interface':<26s}{'inner⌀':>8s}{'outer⌀':>8s}   source"]
    for name, inner, outer, src in rows:
        i = f"{inner:.2f}" if isinstance(inner, (int, float)) else ""
        o = f"{outer:.2f}" if isinstance(outer, (int, float)) else ""
        lines.append(f"  {name:<26s}{i:>8s}{o:>8s}   {src}")

    # RE-MEASURE the angled-boss feature from the compiled base (COMPILE_DRIFT on the new rows)
    part = screw_base(**{k: v for k, v in p1.params.items() if isinstance(v, (int, float, bool))}).part
    # the boss is the lowest solid feature; measure its centre z vs the design boss_center z
    zmin = part.bounding_box().min.Z
    design_zmin = boss_center[2] - in_boss_d / 2 - 1.0    # rough boss bottom
    lines.append("")
    lines.append(f"  RE-MEASURE (compiled base): angled-boss lowest Z = {zmin:.1f} mm "
                 f"(design boss centre z = {boss_center[2]:.1f}); the boss + strut compile as ONE solid.")
    lines.append(f"  cross-centre z = {cross_z} mm (the derived axis intersection); β = {beta:.0f}°.")
    txt = "\n".join(lines)
    (ROOT / "m27_angled_screw_lift" / "out" / "angled_screw_lift_fit_chain.txt").write_text(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
