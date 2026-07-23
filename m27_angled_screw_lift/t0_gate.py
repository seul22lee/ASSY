"""m27 (§14 T4) — angled_screw_lift t0 GATE: the m24 assembly gate + the m21 u-joint pairs.

Two parts, both per D22 (intended contact pairs report clearance; every unintended inter-body pair reports
ZERO penetration): (1) the COMPILED ASSEMBLY swept over the lift (screw-in-nut, columns, angled boss);
(2) the U-JOINT declared-pair rig (yokes / cross / shafts) swept over a FULL input revolution at β=30° AND
β=0° — the m21 addendum pair set, now at assembly level. No verdict ships over geometry that failed.

  ./bin/py m27_angled_screw_lift/t0_gate.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "m0"))
sys.path.insert(0, str(ROOT / "m21_universal_joint")); sys.path.insert(0, str(ROOT / "m22_composition"))

import numpy as np  # noqa: E402
import mujoco as mj  # noqa: E402

from knowledge.cards.base import CARD_REGISTRY  # noqa: E402
from tasks.build_goldens import angled_screw_lift  # noqa: E402
from t0_gate import t0_gate  # noqa: E402  (m22 assembly gate)
import p_ujoint_va as UJ  # noqa: E402  (m21 u-joint t0)


def assembly_gate(tmp: Path):
    plan = angled_screw_lift()
    for e in plan.elements:
        e.params = CARD_REGISTRY[e.card_ref].resolve_params(plan, e)
    # the platform (P2) rises +Z over the lift; intended pairs: P1×P2 (screw thread + guide columns),
    # P1×P3 (the crank in the angled boss / at the u-joint region). P2×P3 is unintended (must clear).
    intended = {frozenset({"P1", "P2"}), frozenset({"P1", "P3"})}
    rows, clean = t0_gate(plan, "P2", np.array([0.0, 0.0, 1.0]), [0, 10, 20, 30, 40], intended, tmp)
    return rows, clean


def ujoint_gate(beta, tmp: Path):
    plan = angled_screw_lift()
    for e in plan.elements:
        e.params = CARD_REGISTRY[e.card_ref].resolve_params(plan, e)
    xml, meta = UJ.build_va_mjcf(plan, tmp, beta_deg=beta)
    (tmp / f"uj_b{int(beta)}.xml").write_text(xml)
    model = mj.MjModel.from_xml_path(str(tmp / f"uj_b{int(beta)}.xml"))
    # sweep the input over a FULL revolution (m21 t0 table, D22 split: cross↔input/output + base↔input
    # are the intended pin-in-bore pairs; everything else zero-pen). Returns {pair: (pen_mm, intended)}.
    tbl = UJ.t0_interference_table(model, poses_deg=(0, 45, 90, 135, 180, 225, 270, 315))
    rows = {f"{k[0]}×{k[1]}": {"worst_pen_mm": v[0], "intended": v[1]} for k, v in tbl.items()}
    clean = all(v[1] or v[0] <= 0.05 for v in tbl.values())
    return rows, clean


def main():
    out = ROOT / "m27_angled_screw_lift" / "out"
    lines = ["=== angled_screw_lift t0 GATE (§14 T4, per D22) ===", ""]
    arows, aclean = assembly_gate(out / "t0_asm")
    lines.append("[1] COMPILED ASSEMBLY (swept over the lift): screw-in-nut, guide columns, angled boss")
    for pair, r in arows.items():
        kind = "INTENDED" if r["intended"] else "unintended"
        lines.append(f"    {pair:<12s}{r['worst_pen_mm']:>10.3f} m   {kind}  {'PENETRATE!' if (not r['intended'] and r['worst_pen_mm'] > 5e-5) else 'clear'}")
    lines.append(f"    => assembly t0 {'CLEAN' if aclean else 'FAILED'}")
    lines.append("")
    overall = aclean
    for beta in (30.0, 0.0):
        rows, clean = ujoint_gate(beta, out / f"t0_uj_b{int(beta)}")
        lines.append(f"[2] U-JOINT declared-pair rig @ β={beta:.0f}° (swept over a full input rev):")
        for pair, r in rows.items():
            lines.append(f"    {pair:<20s}{r['worst_pen_mm']:>9.3f} mm   {'INTENDED' if r['intended'] else 'unintended'}  {'PENETRATE!' if (not r['intended'] and r['worst_pen_mm'] > 0.05) else 'clear'}")
        lines.append(f"    => u-joint t0 @ β={beta:.0f}° {'CLEAN' if clean else 'FAILED'}")
        lines.append("")
        overall = overall and clean
    lines.append(f"=> angled_screw_lift t0 GATE: {'CLEAN' if overall else 'FAILED'}")
    txt = "\n".join(lines)
    (out / "angled_screw_lift_t0.txt").write_text(txt + "\n")
    print(txt)
    return overall


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
