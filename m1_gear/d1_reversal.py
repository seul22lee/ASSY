"""D1 — reversal isolation probe (R2b routing, D-M1-6). Is the REVERSAL the killer, or steady
meshing? At m=4, the best-lenient dt (frozen/5 = 1e-4, where forward-only is lenient-stable), frozen
CONTACT preset, 5 seeds x four actuation protocols:

  fwd3     forward-only, 3 rev
  rev3     reverse-only, 3 rev
  instant  fwd 1 rev, INSTANT velocity flip, rev 1 rev   (the current P-GEAR reversal)
  dwell    fwd 1 rev, 0.5 s zero-velocity DWELL at reversal, rev 1 rev  (a real actuator's stop-and-
           reverse, vs the step flip)

Plus a context point: fwd3 at the FROZEN dt (5e-4) — does steady forward meshing already fail at the
sanctioned dt? Routing (pre-declared): if `dwell` passes while `instant` fails -> reversal MODEL is
the killer (P-GEAR step-reverse is unphysical, D16) -> D2. If `dwell` still fails -> D3.

out/d1_reversal.png · out/d1_reversal.json  (guard trio: decision_row, compile_hash, shape assert)
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

OUT = Path(__file__).parent / "out"
M7OUT = Path(__file__).resolve().parents[1] / "m7_rack_pinion" / "out"
RAMP = 0.5
TOOTH_PITCH_DEG = 360.0 / 12


def git_hash():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       cwd=Path(__file__).parent).decode().strip()
    except Exception:
        return "nogit"


def run_protocol(xml, meta, dt, kv, protocol, seed, omega=3.0, n=1.0, dwell=0.5):
    m = mujoco.MjModel.from_xml_path(str(xml))
    m.opt.timestep = dt
    a = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_ACTUATOR, "drive")
    m.actuator_gainprm[a, 0] = kv; m.actuator_biasprm[a, 2] = -kv
    d = mujoco.MjData(m)
    rng = np.random.default_rng(seed)
    ipa = m.jnt_qposadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, "pinion_shaft")]
    iga = m.jnt_qposadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, "gear_shaft")]
    d.qpos[iga] += rng.uniform(-1e-4, 1e-4); mujoco.mj_forward(m, d)

    nturn = n * 2 * np.pi
    fwd_target = (3 if protocol in ("fwd3",) else 1) * 2 * np.pi
    rev_turns = (3 if protocol == "rev3" else 1) * 2 * np.pi
    phase, t_mark = "run", None
    ts, thp, thg = [], [], []
    diverged = completed = False
    tmax = 40.0
    while d.time < tmax:
        tp = float(d.qpos[ipa])
        if protocol == "fwd3":
            ctrl = min(omega, omega * d.time / RAMP)
            if tp >= fwd_target:
                completed = True; break
        elif protocol == "rev3":
            ctrl = -min(omega, omega * d.time / RAMP)
            if tp <= -rev_turns:
                completed = True; break
        elif protocol == "instant":
            if phase == "run":
                ctrl = min(omega, omega * d.time / RAMP)
                if tp >= fwd_target:
                    phase, t_mark = "rev", d.time
            else:
                ctrl = -min(omega, omega * (d.time - t_mark) / RAMP)
                if tp <= 0.0:
                    completed = True; break
        else:  # dwell
            if phase == "run":
                ctrl = min(omega, omega * d.time / RAMP)
                if tp >= fwd_target:
                    phase, t_mark = "dwell", d.time
            elif phase == "dwell":
                ctrl = 0.0                                  # zero-velocity target -> settle to rest
                if d.time >= t_mark + dwell:
                    phase, t_mark = "rev", d.time
            else:
                ctrl = -min(omega, omega * (d.time - t_mark) / RAMP)
                if tp <= 0.0:
                    completed = True; break
        d.ctrl[0] = ctrl
        mujoco.mj_step(m, d)
        if not np.all(np.isfinite(d.qpos)) or abs(d.qvel[0]) > 150 or abs(d.qvel[1]) > 150:
            diverged = True; break
        ts.append(d.time); thp.append(float(d.qpos[ipa])); thg.append(float(d.qpos[iga]))

    thp_a, thg_a = np.array(thp), np.array(thg)
    ratio = 0.0
    if len(thp_a) > 20:
        mask = np.abs(thp_a) > 0.3
        if mask.sum() > 10:
            ratio = float(np.polyfit(thp_a[mask], thg_a[mask], 1)[0])
    ratio_err = abs((ratio + 0.5) / 0.5) * 100 if ratio else 100.0
    te = thg_a + 0.5 * thp_a
    slip = bool(len(te) > 1 and np.rad2deg(np.abs(np.diff(te))).max() > TOOTH_PITCH_DEG / 2)
    ok = bool(completed and not diverged and ratio_err <= 5.0 and not slip)
    return {"pass": ok, "diverged": diverged, "completed": completed,
            "ratio": round(ratio, 3), "ratio_err_pct": round(ratio_err, 1), "slip": slip,
            "t_end": round(ts[-1], 3) if ts else 0.0, "trace": (ts, list(np.rad2deg(thp_a)))}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    xml, meta = gear_mjcf.build("involute", 4, tag="d1_m4", module=4.0, op_cd=72.6, seat_deg=0.3)
    kv = 4e-4
    DT = 1e-4          # best lenient dt for m=4 (frozen/5) — where forward-only is lenient-stable
    protocols = ["fwd3", "rev3", "instant", "dwell"]
    results, traces = {}, {}
    for pr in protocols:
        seeds = [run_protocol(xml, meta, DT, kv, pr, s) for s in range(5)]
        npass = sum(r["pass"] for r in seeds); ndiv = sum(r["diverged"] for r in seeds)
        results[pr] = {"seeds_pass": npass, "diverged": ndiv,
                       "ratios": [r["ratio"] for r in seeds], "per_seed": seeds}
        traces[pr] = seeds[0]["trace"]
        print(f"  {pr:8s} @ dt={DT:.0e}: {npass}/5 pass, {ndiv}/5 diverged, ratio~{seeds[0]['ratio']:+.2f}")

    # context: does steady forward meshing already fail at the FROZEN dt (5e-4)?
    fwd_frozen = [run_protocol(xml, meta, 5e-4, kv, "fwd3", s) for s in range(5)]
    ctx = {"fwd3_at_frozen_dt": {"seeds_pass": sum(r["pass"] for r in fwd_frozen),
                                 "diverged": sum(r["diverged"] for r in fwd_frozen)}}
    print(f"  [context] fwd3 @ FROZEN dt=5e-4: {ctx['fwd3_at_frozen_dt']['seeds_pass']}/5 pass, "
          f"{ctx['fwd3_at_frozen_dt']['diverged']}/5 diverged")

    # routing (pre-declared)
    dwell_pass = results["dwell"]["seeds_pass"] >= 4
    instant_pass = results["instant"]["seeds_pass"] >= 4
    if dwell_pass and not instant_pass:
        route = "D2 — reversal MODEL is the killer (dwell passes, instant fails): amend P-GEAR actuation (step-reverse is unphysical, D16); R2b re-probes under the amended protocol before any preset talk"
    elif dwell_pass and instant_pass:
        route = "AMBIGUOUS — both reversal protocols pass; the earlier 0/5 was not the reversal. Re-examine (likely the frozen-dt forward failure dominates); lean D3"
    else:
        route = "D3 — dwell still fails: do NOT open the preset procedure. FREEZE R2b (gear contact-only verification pending preset v2 — deferred); downgrade P-GEAR Hard-anchor requirement to V-A with the V-B gap documented; STOP"

    gh = git_hash()
    verdict = {"decision_row": "D-M1-6 routing / D1 reversal isolation", "compile_hash": gh,
               "config": {"module": 4, "dt": DT, "frozen_contact_preset": True, "kv": kv, "seeds": 5},
               "protocols_probed": protocols, "results": {k: {kk: vv for kk, vv in v.items() if kk != "per_seed"} for k, v in results.items()},
               "context": ctx, "routing": route,
               "shape_assert": {"protocols_covered": sorted(results.keys()) == sorted(protocols)}}
    for dst in (OUT / "d1_reversal.json", M7OUT / "d1_reversal.json"):
        dst.write_text(json.dumps(verdict, indent=2, default=float))

    # figure: pinion angle traces (seed 0) per protocol — where does it diverge?
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
    cols = {"fwd3": "#2f855a", "rev3": "#2b6cb0", "instant": "#c53030", "dwell": "#dd6b20"}
    for pr in protocols:
        t, th = traces[pr]
        ax[0].plot(t, th, color=cols[pr], lw=1.3, label=f"{pr} ({results[pr]['seeds_pass']}/5)")
    ax[0].set_xlabel("t (s)"); ax[0].set_ylabel("pinion angle (deg)")
    ax[0].set_title(f"D1 reversal isolation — m=4, dt=frozen/5, frozen contact (seed 0 traces)", fontsize=9.5)
    ax[0].legend(fontsize=8); ax[0].grid(alpha=.25)
    y = np.arange(len(protocols)); sp = [results[p]["seeds_pass"] for p in protocols]
    ax[1].barh(y, sp, color=[cols[p] for p in protocols])
    for yi, s in zip(y, sp):
        ax[1].text(s + 0.06, yi, f"{s}/5", va="center", fontsize=9)
    ax[1].axvline(4, ls="--", c="#22543d", lw=1.2, label="pass (≥4/5)")
    ax[1].set_yticks(y); ax[1].set_yticklabels(protocols); ax[1].invert_yaxis(); ax[1].set_xlim(0, 5.4)
    ax[1].set_xlabel("seeds passing / 5"); ax[1].set_title("Which protocol survives?", fontsize=9.5)
    ax[1].legend(fontsize=8, loc="lower right"); ax[1].grid(alpha=.2, axis="x")
    fig.suptitle(f"D1 → {route.split(' — ')[0]}   ·   compile {gh}", fontsize=10.5, y=1.02)
    fig.tight_layout()
    for dst in (OUT / "d1_reversal.png", M7OUT / "d1_reversal.png"):
        fig.savefig(dst, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"\n==> ROUTING: {route}")
    print(f"    wrote d1_reversal.{{json,png}} (compile {gh})")


if __name__ == "__main__":
    main()
