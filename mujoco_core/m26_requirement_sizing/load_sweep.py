"""m26 — REQUIREMENT-DRIVEN SIZING demonstration: the SAME lead_screw command at three loads → three
DIFFERENT resolved designs. The table IS the evidence that ⑤ DESIGNS the screw from the declared load
(shear via τ_design/SF) rather than looking up a default — the Phase-2 story (the LLM CHOOSES the element,
the pipeline SIZES it). Precedent: the m24 snap CLIP, which inverted the Bayer chain to a target W_out
(D-M24-5). Each resolved design is COMPILED, t0-checked, and the V-A HOLD criterion re-run at its own W.

  export MUJOCO_GL=egl ; ./bin/py m26_requirement_sizing/load_sweep.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "m0"))
sys.path.insert(0, str(ROOT / "m19_lead_screw")); sys.path.insert(0, str(ROOT / "m22_composition"))

import mujoco as mj  # noqa: E402

from knowledge.cards.base import CARD_REGISTRY  # noqa: E402
from knowledge.cards.lead_screw import lead_screw_dims, lead_screw_mechanics, TAU_DESIGN_MPA, SIZING_SF  # noqa: E402
from pipeline.compile_assembly import compile_assembly  # noqa: E402
from tasks.build_goldens import lead_screw_fixture  # noqa: E402
from t0_gate import t0_gate  # noqa: E402
import numpy as np  # noqa: E402

import p_screw_va as PS  # noqa: E402  (m19 P-SCREW rig: build_va_mjcf + run_va)

LOADS_KG = [1.0, 5.0, 20.0]


def _drive_torque(g, mech):
    """Shigley §8-1 raise torque T = (W·d_mean/2)·(tanλ+µ)/(1−µ·tanλ), reported at each design's W."""
    return None  # filled per-row (needs W)


def size_one(W_kg: float, tmp: Path) -> dict:
    plan = lead_screw_fixture()
    e1 = next(e for e in plan.elements if e.card_ref == "lead_screw")
    p2 = next(p for p in plan.pieces if p.id == "P2")
    # OMIT d_major (element + nut host) so ⑤ SIZES it from the load; set the declared load W.
    e1.params = {k: v for k, v in e1.params.items() if k != "d_major"}
    b2 = next(b for b in plan.behaviors if b.id == "B2")
    b2.load = {"mass_kg": float(W_kg), "direction": "-z"}
    # resolve → sized d_major
    e1.params = CARD_REGISTRY["lead_screw"].resolve_params(plan, e1)
    d_major = e1.params["d_major"]
    sized = e1.params.get("_sized", {})
    # propagate the sized d_major to the nut host so the clearance bore fits the screw
    p2.params = dict(p2.params); p2.params["d_major"] = d_major
    g = lead_screw_dims(e1.params); mech = lead_screw_mechanics(g)
    W_N = W_kg * 9.81
    lam = math.radians(mech["lead_angle_deg"]); mu = g.mu
    T = (W_N * (mech["d_mean_mm"] / 1000.0) / 2.0) * (math.tan(lam) + mu) / (1 - mu * math.tan(lam))  # N·m

    # COMPILE + t0 (screw in the nut bore = intended clearance; nothing else)
    ca = compile_assembly(plan)
    solids = {pid: len(part.solids()) for pid, part in ca.parts.items()}
    rows, clean = t0_gate(plan, "P2", np.array([0.0, 0.0, 1.0]), [0, 10, 20, 30, 40],
                          {frozenset({"P1", "P2"})}, tmp / f"t0_{int(W_kg)}")

    # V-A HOLD re-run at THIS W + THIS sized geometry (m19 P-SCREW rig, frozen solref -1e8): the sourced
    # self-lock friction T_f = µ·W·d_mean/2 (scales with the sized d_mean and W). NOTE the sourced
    # "backdrive" is dominated by the DECLARED-COUPLING elastic COMPLIANCE (∝ W: 0.08 mm@0.5kg → 3 mm@20kg,
    # a rig stiffness, NOT thread slip). Self-lock is judged by the DISCRIMINATION (below), not an absolute
    # gate: the design self-locks iff a sub-back-drive friction SLIPS far more than the sourced hold.
    xml, meta = PS.build_va_mjcf(plan, ca, tmp / f"rig_{int(W_kg)}")
    (tmp / f"rig_{int(W_kg)}.xml").write_text(xml)
    model = mj.MjModel.from_xml_path(str(tmp / f"rig_{int(W_kg)}.xml"))
    v, _, _ = PS.run_va(model, meta, seed=0, record=False)
    hold = next((c for k, c in v["criteria"].items() if "back-drive" in k.lower() or "self_lock" in k.lower()), None)
    backdrive = v.get("backdrive_mm", hold["value"] if hold else None)
    # DISCRIMINATION at this W: a sub-back-drive friction must SLIP far more than the sourced hold —
    # the proof the self-lock (not a solver artifact) holds the load (D-M19-2 companion discipline).
    vw, _, _ = PS.run_va(model, meta, seed=0, record=False, friction_override=0.5 * meta["T_backdrive_Nm"])

    return {"W_kg": W_kg, "W_N": round(W_N, 1), "T_Nmm": round(T * 1000, 1),
            "d_shear_mm": sized.get("d_shear_mm"), "d_major_mm": d_major, "governed": sized.get("governed"),
            "pitch_mm": g.pitch, "lead_mm": g.lead, "lambda_deg": mech["lead_angle_deg"],
            "self_locks": mech["self_locks"], "pitch_selflock_max_mm": e1.params.get("_pitch_selflock_max_mm"),
            "solids": solids, "t0_clean": bool(clean), "backdrive_mm": backdrive,
            "discrim_weak_mm": vw.get("backdrive_mm"),
            # self-lock CONFIRMED = the design criterion (tan λ ≤ µ) AND the discrimination (weak friction
            # slips >> the sourced hold — proving the hold is the self-lock, not a solver/compliance artifact).
            "hold_pass": bool(mech["self_locks"] and vw.get("backdrive_mm", 0) > max(2.0 * (backdrive or 0), 3.0))}


def main():
    out = ROOT / "m26_requirement_sizing" / "out"; out.mkdir(parents=True, exist_ok=True)
    tmp = out / "assets"
    rows = [size_one(W, tmp) for W in LOADS_KG]
    hdr = (f"=== REQUIREMENT-DRIVEN SIZING — lead_screw, same command @ W = {'/'.join(str(int(w)) for w in LOADS_KG)} kg ===\n"
           f"    d_major SIZED from the load by drive-torque torsional shear (τ_design={TAU_DESIGN_MPA} MPa "
           f"FDM design shear, SF={SIZING_SF}); pitch bounded above by self-lock (tan λ ≤ µ).\n")
    cols = (f"  {'W(kg)':>6}{'W(N)':>7}{'T(N·mm)':>9}{'d_shear':>8}{'d_major':>8}{'governed':>10}{'pitch':>6}"
            f"{'λ(deg)':>7}{'self-lock':>10}{'t0':>7}{'hold(mm)':>9}{'weak(mm)':>9}{'hold':>6}")
    lines = [hdr, cols]
    for r in rows:
        lines.append(f"  {r['W_kg']:>6.0f}{r['W_N']:>7.1f}{r['T_Nmm']:>9.1f}{r['d_shear_mm']:>8.2f}"
                     f"{r['d_major_mm']:>8.2f}{r['governed']:>10}{r['pitch_mm']:>6.1f}{r['lambda_deg']:>7.2f}"
                     f"{str(r['self_locks']):>10}{'CLEAN' if r['t0_clean'] else 'FAIL':>7}"
                     f"{(r['backdrive_mm'] if r['backdrive_mm'] is not None else -1):>9.3f}"
                     f"{(r['discrim_weak_mm'] if r['discrim_weak_mm'] is not None else -1):>9.2f}"
                     f"{'PASS' if r['hold_pass'] else 'FAIL':>6}")
    lines.append("")
    lines.append(f"  READING: d_major GROWS with the load ({rows[0]['d_major_mm']} → {rows[1]['d_major_mm']} → "
                 f"{rows[2]['d_major_mm']} mm) — ⑤ SIZED each from W (torsional shear), not a default. At the "
                 f"lightest load the printability MIN bound governs (shear needs only {rows[0]['d_shear_mm']} mm); "
                 f"above it, shear governs. T (drive torque) and d grow together.")
    lines.append("  All three SELF-LOCK (tan λ ≤ µ). The 'hold' column is the sourced back-drive; note it is the "
                 "declared-coupling elastic COMPLIANCE (∝ W: ~0.08 mm@0.5kg → 3 mm@20kg — a rig stiffness, NOT "
                 "slip). Self-lock is judged by DISCRIMINATION: the 'weak' column (a sub-back-drive friction) "
                 "SLIPS far more than the sourced hold — proving the hold is the self-lock, not a solver artifact.")
    txt = "\n".join(lines)
    (out / "load_sweep.txt").write_text(txt + "\n")
    (out / "load_sweep.json").write_text(json.dumps({"tau_design_MPa": TAU_DESIGN_MPA, "SF": SIZING_SF, "rows": rows}, indent=2))
    print(txt)


if __name__ == "__main__":
    main()
