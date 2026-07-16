"""R2b mitigation probe (D-M1-2 queue item 1): does a larger module retire R2b geometry-side, at the
FROZEN preset dt? Sanctioned probe = m=3; m=2 (baseline) and m=4 (trend) added as decision input.

Verdict: **FAIL at m=3** (0/5 seeds converge at the frozen dt). BUT the module mitigation works and
scales monotonically — the max stable timestep relaxes with module (m=2: frozen/25, m=3: frozen/10,
m=4: frozen/5) — it just has not reached the in-bounds line (frozen dt, or the §6.4 retry frozen/2)
by m=4. So the geometry-side route is directionally correct and not exhausted; the recommendation is
to continue it (m=5–6) before any preset amendment. Preset UNTOUCHED (R5).

out/probe_verdict.png · out/probe_verdict.json
"""

from __future__ import annotations

import json
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

OUT = Path(__file__).parent / "out"
FROZEN, RETRY = 5e-4, 2.5e-4
# clean-start operating cd (0 initial penetration, G-CONV (b) pass) + drive gain per module.
CFG = {2: dict(op_cd=36.0, kv=5e-5), 3: dict(op_cd=54.2, kv=2e-4), 4: dict(op_cd=72.6, kv=4e-4)}
DT_SWEEP = [5e-4, 2.5e-4, 1e-4, 5e-5, 2e-5]


def max_stable_dt(xml, meta, kv):
    stable = []
    for dt in DT_SWEEP:
        v, _, _ = p_gear.run_gear(mujoco.MjModel.from_xml_path(str(xml)), meta, dt=dt, omega=3.0,
                                  n_rev=0.5, kv=kv, forward_only=True)
        if not v.diverged and abs(v.ratio_err_pct) < 5:
            stable.append(dt)
    return max(stable) if stable else None   # the COARSEST stable dt (largest that still converges)


def frozen_trace(xml, meta, kv):
    v, series, _ = p_gear.run_gear(mujoco.MjModel.from_xml_path(str(xml)), meta, dt=FROZEN,
                                   omega=3.0, n_rev=0.5, kv=kv)
    return v, series


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows, traces = {}, {}
    for mod, cfg in CFG.items():
        xml, meta = gear_mjcf.build("involute", 4, tag=f"probe_m{mod}", module=float(mod),
                                    op_cd=cfg["op_cd"], seat_deg=0.3)
        v, series = frozen_trace(xml, meta, cfg["kv"])
        sdt = max_stable_dt(xml, meta, cfg["kv"])
        rows[mod] = {"module": mod, "op_cd": cfg["op_cd"], "backlash_realised_mm": meta["backlash_realised_mm"],
                     "frozen_diverged": v.diverged, "frozen_ratio": v.ratio,
                     "max_stable_dt": sdt, "frozen_over_stable": (FROZEN / sdt) if sdt else None}
        traces[mod] = series
        print(f"m={mod}: frozen dt diverged={v.diverged} (ratio {v.ratio:+.3f}); "
              f"max stable dt={sdt:.0e} (frozen/{FROZEN/sdt:.0f})" if sdt else
              f"m={mod}: frozen diverged={v.diverged}; no stable dt in sweep")

    # --- 5-seed probe at m=3 (the sanctioned criterion) ---
    xml3, meta3 = gear_mjcf.build("involute", 4, tag="probe_m3_seeds", module=3.0,
                                  op_cd=CFG[3]["op_cd"], seat_deg=0.3)
    npass = 0
    for s in range(5):
        v, _, _ = p_gear.run_gear(mujoco.MjModel.from_xml_path(str(xml3)), meta3, dt=FROZEN,
                                  omega=3.0, n_rev=1.0, seed=s, kv=CFG[3]["kv"])
        npass += v.passed()
    m3_verdict = {"seeds_pass": npass, "n_seeds": 5, "pass": npass >= 4}
    print(f"m=3 sanctioned probe: {npass}/5 @ frozen dt -> {'PASS' if npass>=4 else 'FAIL'}")

    # --- figure ---
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
    # left: pinion ω at frozen dt, all three modules diverge
    for mod, c in zip((2, 3, 4), ("#c53030", "#dd6b20", "#805ad5")):
        s = traces[mod]
        ax[0].plot(s["t"], s["omega_pin"], color=c, lw=1.1, label=f"m={mod}")
    ax[0].axhline(3.0, ls="--", c="#888", lw=0.8)
    ax[0].set_title("At the FROZEN dt=5e-4: every module diverges\n(m=4 rolls conjugately longer, "
                    "then blows up)", fontsize=9.5)
    ax[0].set_xlabel("t (s)"); ax[0].set_ylabel("pinion ω (rad/s)"); ax[0].legend(fontsize=8); ax[0].grid(alpha=.25)
    # right: max stable dt vs module (the mitigation trend)
    mods = [2, 3, 4]; sdts = [rows[m]["max_stable_dt"] for m in mods]
    ax[1].plot(mods, sdts, "o-", color="#2b6cb0", lw=2, ms=8)
    for m, s in zip(mods, sdts):
        ax[1].annotate(f"frozen/{FROZEN/s:.0f}", (m, s), textcoords="offset points", xytext=(6, 6), fontsize=8)
    ax[1].axhline(FROZEN, ls="--", c="#22543d", lw=1, label="frozen dt (in-bounds target)")
    ax[1].axhline(RETRY, ls=":", c="#dd6b20", lw=1, label="§6.4 retry (frozen/2, still in-bounds)")
    ax[1].set_yscale("log"); ax[1].set_xticks(mods)
    ax[1].set_title("Mitigation trend: max stable dt relaxes with module\n(monotonic — but not yet "
                    "in-bounds by m=4; extrapolates to m≈5–6)", fontsize=9.5)
    ax[1].set_xlabel("module m (z=12 fixed)"); ax[1].set_ylabel("max stable dt (s, log)")
    ax[1].legend(fontsize=8, loc="lower right"); ax[1].grid(alpha=.25, which="both")
    fig.suptitle(f"R2b mitigation probe — larger module (D-M1-2/D-M1-3): m=3 sanctioned probe "
                 f"{'PASS' if m3_verdict['pass'] else 'FAILS'} ({npass}/5 at frozen dt)",
                 fontsize=11, y=1.02)
    fig.tight_layout(); fig.savefig(OUT / "probe_verdict.png", dpi=140, bbox_inches="tight"); plt.close(fig)

    verdict = {"sanctioned_probe_module": 3, "m3_5seed": m3_verdict, "per_module": rows,
               "conclusion": "FAIL at m=3 (0/5 at frozen dt); module mitigation monotonic but not "
                             "in-bounds by m=4; recommend continuing geometry-side (m=5-6) before "
                             "preset amendment; preset UNTOUCHED (R5)"}
    (OUT / "probe_verdict.json").write_text(json.dumps(verdict, indent=2, default=float))
    print("wrote probe_verdict.png + probe_verdict.json")


if __name__ == "__main__":
    main()
