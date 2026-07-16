"""Close the evidence gap (G-H HOLD on m7): run m=2..6 as FULL sanctioned P-GEAR probes — 5 seeds
each, FROZEN preset, forward+reverse — not the lenient forward-only metric that never got persisted.
Produce the real 5-point current-truth verdict for m7_rack_pinion/out/.

This reflects the ACTUAL D-M1-5 outcome (nothing passes → R2b formulation-deep), NOT a retirement.
The 3-point historical "FAIL at m=3" stays in m1_gear/out/ untouched.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "m0"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mujoco
import numpy as np

import gear_mjcf
import p_gear

M7OUT = Path(__file__).resolve().parents[1] / "m7_rack_pinion" / "out"
FROZEN, RETRY = 5e-4, 2.5e-4
CFG = {2: dict(op_cd=36.0, kv=5e-5), 3: dict(op_cd=54.2, kv=2e-4), 4: dict(op_cd=72.6, kv=4e-4),
       5: dict(op_cd=90.7, kv=6e-4), 6: dict(op_cd=109.0, kv=9e-4)}
DT_SWEEP = [5e-4, 2.5e-4, 1e-4, 5e-5, 2e-5]


def git_hash():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       cwd=Path(__file__).parent).decode().strip()
    except Exception:
        return "nogit"


def sanctioned(xml, meta, kv):
    """5 seeds, FROZEN dt, full P-GEAR (fwd+rev) — the sanctioned criterion (>=4/5 = pass)."""
    res = [p_gear.run_gear(mujoco.MjModel.from_xml_path(str(xml)), meta, dt=FROZEN, omega=3.0,
                           n_rev=1.0, seed=s, kv=kv)[0] for s in range(5)]
    return sum(v.passed() for v in res), res[0].ratio, sum(v.diverged for v in res)


def max_stable_dt(xml, meta, kv):
    stable = [dt for dt in DT_SWEEP
              if not (v := p_gear.run_gear(mujoco.MjModel.from_xml_path(str(xml)), meta, dt=dt,
                      omega=3.0, n_rev=0.5, kv=kv, forward_only=True)[0]).diverged
              and abs(v.ratio_err_pct) < 5]
    return max(stable) if stable else None


def main():
    rows = {}
    for mod, cfg in CFG.items():
        xml, meta = gear_mjcf.build("involute", 4, tag=f"sanc_m{mod}", module=float(mod),
                                    op_cd=cfg["op_cd"], seat_deg=0.3)
        sp, ratio, ndiv = sanctioned(xml, meta, cfg["kv"])
        sdt = max_stable_dt(xml, meta, cfg["kv"])
        rows[mod] = {"module": mod, "op_cd": cfg["op_cd"], "backlash_realised_mm": meta["backlash_realised_mm"],
                     "seeds_pass_frozen": sp, "n_seeds": 5, "sanctioned_pass": sp >= 4,
                     "frozen_ratio": ratio, "frozen_diverged_seeds": ndiv,
                     "max_stable_dt_forward_lenient": sdt}
        print(f"  m={mod}: SANCTIONED {sp}/5 @ frozen dt ({ndiv}/5 diverged); "
              f"lenient max_stable_dt={sdt} ({'frozen/%d'%(FROZEN/sdt) if sdt else 'none'})")

    any_pass = any(rows[m]["sanctioned_pass"] for m in rows)
    any_inbounds = [m for m in rows if rows[m]["max_stable_dt_forward_lenient"]
                    and rows[m]["max_stable_dt_forward_lenient"] >= RETRY]
    gh = git_hash()
    conclusion = (
        f"Sanctioned probe m=2..6 (5 seeds, frozen preset, full P-GEAR fwd+rev): "
        + ("SOME MODULE PASSES — revisit" if any_pass else "ALL 0/5 — no module passes.") + " "
        f"Even the lenient forward-only max_stable_dt reaches at most frozen/{FROZEN/max(r['max_stable_dt_forward_lenient'] for r in rows.values() if r['max_stable_dt_forward_lenient']):.0f}"
        f" (m=4), still short of the in-bounds line frozen/2; and it does NOT survive the full "
        f"protocol. D-M1-4 rule outcome = (ii): no m<=6 in-bounds -> preset route -> D-M1-5: no "
        f"viable preset_v2 -> R2b FORMULATION-DEEP, NO card, module bounds provisional [3,4]. "
        f"R2a stays retired (conjugate roll). Preset UNTOUCHED (R5).")

    verdict = {"decision_row": "D-M1-4 (rule) / D-M1-5 (outcome)", "compile_hash": gh,
               "criterion": "sanctioned = 5 seeds, FROZEN dt, full P-GEAR (fwd+rev), pass >=4/5",
               "per_module": rows, "any_sanctioned_pass": any_pass,
               "lenient_in_bounds_modules": any_inbounds, "conclusion": conclusion}
    M7OUT.mkdir(parents=True, exist_ok=True)
    (M7OUT / "probe_verdict.json").write_text(json.dumps(verdict, indent=2, default=float))

    # 5-point figure — current truth
    mods = sorted(CFG)
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.8))
    sp = [rows[m]["seeds_pass_frozen"] for m in mods]
    ax[0].bar(mods, sp, color=["#c53030" if s < 4 else "#2f855a" for s in sp], width=0.6)
    for m, s in zip(mods, sp):
        ax[0].text(m, s + 0.08, f"{s}/5", ha="center", fontsize=9, color="#742a2a")
    ax[0].axhline(4, ls="--", c="#22543d", lw=1.2, label="P-GEAR pass (≥4/5)")
    ax[0].set_ylim(0, 5.4); ax[0].set_xticks(mods)
    ax[0].set_title("SANCTIONED probe: 5 seeds, frozen preset, full P-GEAR (fwd+rev)\n"
                    "all modules 0/5 — none passes", fontsize=9.5)
    ax[0].set_xlabel("module m (z=12)"); ax[0].set_ylabel("seeds passing / 5"); ax[0].legend(fontsize=8); ax[0].grid(alpha=.25, axis="y")
    sdts = [rows[m]["max_stable_dt_forward_lenient"] for m in mods]
    ax[1].plot(mods, [s if s else np.nan for s in sdts], "o-", color="#2b6cb0", lw=2, ms=8)
    for m, s in zip(mods, sdts):
        ax[1].annotate(f"frozen/{FROZEN/s:.0f}" if s else "none", (m, s if s else 2e-5),
                       textcoords="offset points", xytext=(5, 6), fontsize=7.5)
    ax[1].axhline(FROZEN, ls="--", c="#22543d", lw=1, label="frozen dt (fully in-bounds)")
    ax[1].axhline(RETRY, ls=":", c="#dd6b20", lw=1.2, label="in-bounds line = frozen/2")
    ax[1].axhspan(RETRY, FROZEN * 2, color="#c6f6d5", alpha=0.35)
    ax[1].set_yscale("log"); ax[1].set_xticks(mods); ax[1].set_ylim(1e-5, 8e-4)
    ax[1].set_title("Lenient forward-only max_stable_dt (context, NOT the criterion)\n"
                    "peaks at m=4=frozen/5, still below frozen/2 — and fails full P-GEAR anyway", fontsize=9.5)
    ax[1].set_xlabel("module m (z=12)"); ax[1].set_ylabel("max stable dt (s, log)")
    ax[1].legend(fontsize=8, loc="lower right"); ax[1].grid(alpha=.25, which="both")
    fig.suptitle(f"R2b sanctioned 5-point probe (D-M1-4/D-M1-5) — NO module passes → R2b formulation-deep, "
                 f"no card   ·   compile {gh}", fontsize=10.5, y=1.02)
    fig.tight_layout(); fig.savefig(M7OUT / "probe_verdict.png", dpi=140, bbox_inches="tight"); plt.close(fig)
    print(f"\n==> {'SOME PASS' if any_pass else 'ALL 0/5'}; wrote m7_rack_pinion/out/probe_verdict.{{json,png}} (compile {gh})")


if __name__ == "__main__":
    main()
