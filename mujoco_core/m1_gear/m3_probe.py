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
FROZEN, RETRY = 5e-4, 2.5e-4              # RETRY = frozen/2 = the in-bounds line (D-M1-4 rule)
# clean-start operating cd (0 initial penetration, G-CONV (b) pass) + drive gain per module.
CFG = {2: dict(op_cd=36.0, kv=5e-5), 3: dict(op_cd=54.2, kv=2e-4), 4: dict(op_cd=72.6, kv=4e-4),
       5: dict(op_cd=90.7, kv=6e-4), 6: dict(op_cd=109.0, kv=9e-4)}
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


def confirm_5seed(mod, cfg, dt):
    """P-GEAR 5-seed confirmation at a specific dt (the in-bounds check for the D-M1-4 rule)."""
    xml, meta = gear_mjcf.build("involute", 4, tag=f"confirm_m{mod}", module=float(mod),
                                op_cd=cfg["op_cd"], seat_deg=0.3)
    npass = 0
    for s in range(5):
        v, _, _ = p_gear.run_gear(mujoco.MjModel.from_xml_path(str(xml)), meta, dt=dt, omega=3.0,
                                  n_rev=1.0, seed=s, kv=cfg["kv"])
        npass += v.passed()
    return npass


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
        msg = (f"max stable dt={sdt:.0e} (frozen/{FROZEN/sdt:.0f})" if sdt else "no stable dt in sweep")
        print(f"m={mod}: frozen dt diverged={v.diverged} (ratio {v.ratio:+.3f}); {msg}")

    # --- PRE-DECLARED D-M1-4 rule: the SMALLEST m<=6 stable at dt >= frozen/2 retires R2b ---
    in_bounds = sorted(m for m in CFG if rows[m]["max_stable_dt"] and rows[m]["max_stable_dt"] >= RETRY)
    decision = {"rule": "D-M1-4: smallest m<=6 with max_stable_dt >= frozen/2 (2.5e-4) retires R2b",
                "in_bounds_modules": in_bounds}
    if in_bounds:
        m_ret = in_bounds[0]
        dt_conf = rows[m_ret]["max_stable_dt"]
        npass = confirm_5seed(m_ret, CFG[m_ret], dt_conf)
        decision.update({"outcome": "R2b RETIRED (geometry-side)", "retiring_module": m_ret,
                         "confirm_dt": dt_conf, "confirm_5seed": f"{npass}/5",
                         "confirmed": npass >= 4, "module_bounds": [m_ret, 6]})
        print(f"\n==> D-M1-4: m={m_ret} stable at frozen/{FROZEN/dt_conf:.0f} (in-bounds); "
              f"5-seed confirm {npass}/5 -> {'R2b RETIRES, bounds [%d,6]' % m_ret if npass>=4 else 'NOT confirmed'}")
    else:
        decision.update({"outcome": "geometry route EXHAUSTED within usable envelope (m<=6) -> "
                         "preset-amendment procedure (R5)", "module_bounds": "provisional [3,4] holds; "
                         "no m<=6 reaches in-bounds"})
        print("\n==> D-M1-4: no m<=6 reaches frozen/2 -> geometry route EXHAUSTED; open preset route (R5)")

    # --- 5-point figure ---
    mods = sorted(CFG)
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.8))
    cmap = plt.cm.viridis(np.linspace(0, 0.85, len(mods)))
    for mod, c in zip(mods, cmap):
        s = traces[mod]
        ax[0].plot(s["t"], s["omega_pin"], color=c, lw=1.0, label=f"m={mod}")
    ax[0].axhline(3.0, ls="--", c="#888", lw=0.8)
    ax[0].set_title("Pinion ω at the FROZEN dt=5e-4 by module\n(larger module rolls conjugately "
                    "longer before blow-up)", fontsize=9.5)
    ax[0].set_xlabel("t (s)"); ax[0].set_ylabel("pinion ω (rad/s)"); ax[0].legend(fontsize=8, ncol=2); ax[0].grid(alpha=.25)
    sdts = [rows[m]["max_stable_dt"] for m in mods]
    ax[1].plot(mods, sdts, "o-", color="#2b6cb0", lw=2, ms=8)
    for m, s in zip(mods, sdts):
        ax[1].annotate(f"frozen/{FROZEN/s:.0f}", (m, s), textcoords="offset points", xytext=(5, 6), fontsize=7.5)
    ax[1].axhline(FROZEN, ls="--", c="#22543d", lw=1, label="frozen dt (fully in-bounds)")
    ax[1].axhspan(RETRY, FROZEN * 3, color="#c6f6d5", alpha=0.4)
    ax[1].axhline(RETRY, ls=":", c="#dd6b20", lw=1.2, label="in-bounds line = frozen/2 (§6.4 retry)")
    ax[1].set_yscale("log"); ax[1].set_xticks(mods); ax[1].set_ylim(1e-5, 8e-4)
    ttl = (f"R2b RETIRES at m={in_bounds[0]} (bounds [{in_bounds[0]},6])" if in_bounds
           else "geometry route EXHAUSTED (m≤6) → preset route")
    ax[1].set_title(f"Max stable dt vs module — {ttl}", fontsize=9.5)
    ax[1].set_xlabel("module m (z=12 fixed)"); ax[1].set_ylabel("max stable dt (s, log)")
    ax[1].legend(fontsize=8, loc="lower right"); ax[1].grid(alpha=.25, which="both")
    fig.suptitle("R2b bounded extrapolation probe (D-M1-4, pre-declared rule) — "
                 + ("RETIRED geometry-side" if in_bounds else "route exhausted → preset amendment"),
                 fontsize=11, y=1.01)
    fig.tight_layout(); fig.savefig(OUT / "probe_verdict.png", dpi=140, bbox_inches="tight"); plt.close(fig)

    verdict = {"rule": "D-M1-4 (pre-declared)", "per_module": rows, "decision": decision}
    (OUT / "probe_verdict.json").write_text(json.dumps(verdict, indent=2, default=float))
    print("wrote probe_verdict.png + probe_verdict.json")
    return decision


if __name__ == "__main__":
    main()
