"""M1: P-GEAR protocol (MECHSYNTH §6.3) on the hand-built gear pair. V-B for the teeth (meshing
must emerge from contact); the shafts are declared hinge fixtures (D23).

  actuate   velocity actuator on the pinion shaft: ramp to omega_in, N revolutions forward,
            then N reverse (mesh must work both ways).
  observe   transmission error TE = theta_gear + theta_pinion*z1/z2 (0 for perfect conjugate
            action); ratio; contact force; backlash via reversal lash.
  judge     |ratio error| <= 5%; no slip (TE jump > half a tooth pitch); no jam (actuator not
            saturating against contact); divergence = fail. Preset FROZEN (R5); §6.4 allows ONE
            retry at half the timestep.

The frozen contact preset (dt=5e-4) is imported via gear_mjcf from m0. A ladder rung sets its own
dt only through the §6.4 retry; going finer than that is recorded as a preset violation (a FAIL of
the rung under the rules), never silently taken.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "m0"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import imageio.v2 as imageio
import mujoco
import numpy as np

from p_hinge import g_conv
from vb import _hud

OUT = Path(__file__).parent / "out"
FPS = 60
FROZEN_DT = 5e-4
KV = 5e-5          # velocity-servo gain, sized to the grams-scale inertia (actuation, not preset)
RAMP = 0.5         # s to reach omega_in


def _set_kv(model, kv):
    a = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, "drive")
    model.actuator_gainprm[a, 0] = kv
    model.actuator_biasprm[a, 2] = -kv     # force = kv*(ctrl - qvel); BOTH terms (or it's a damper)


@dataclass
class GearVerdict:
    dt: float
    diverged: bool
    theta_pin_deg: float
    theta_gear_deg: float
    ratio: float
    ratio_err_pct: float
    te_max_deg: float           # peak transmission error
    slip: bool
    jammed: bool
    backlash_meas_mm: float
    backlash_design_mm: float
    revs_done: float

    def criteria(self) -> dict:
        return {
            "|ratio error| <= 5%": {"value": round(self.ratio_err_pct, 2), "threshold": 5.0,
                                    "pass": bool(abs(self.ratio_err_pct) <= 5.0 and not self.diverged)},
            "no slip (TE jump < half tooth pitch)": {"value": self.slip, "threshold": False,
                                                     "pass": bool(not self.slip and not self.diverged)},
            "no jam (actuator tracks, gear turns)": {"value": self.jammed, "threshold": False,
                                                     "pass": bool(not self.jammed and not self.diverged)},
            "converged (no blow-up)": {"value": self.diverged, "threshold": False,
                                       "pass": bool(not self.diverged)},
        }

    def passed(self) -> bool:
        return all(c["pass"] for c in self.criteria().values())


def run_gear(model, meta, dt=FROZEN_DT, omega=3.0, n_rev=1.0, seed=0, record=False,
             forward_only=False, kv=None):
    model.opt.timestep = dt
    _set_kv(model, kv if kv is not None else KV)
    d = mujoco.MjData(model)
    rng = np.random.default_rng(seed)
    ipa = model.jnt_qposadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "pinion_shaft")]
    iga = model.jnt_qposadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "gear_shaft")]
    z1, z2 = meta["z1"], meta["z2"]
    ratio_ideal = -z1 / z2
    tooth_pitch_deg = 360.0 / z1
    rp1 = meta["pitch_r1_mm"]

    # seeds perturb the gear's start angle within the backlash — robustness, not re-tuning (R5)
    d.qpos[iga] += rng.uniform(-1e-4, 1e-4)
    mujoco.mj_forward(model, d)

    renderer = mujoco.Renderer(model, 480, 640) if record else None
    cam = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_CAMERA, "top") if record else 0

    target_rev = n_rev
    total_angle = 2 * np.pi * n_rev
    ts, thp, thg, te, force, wp = [], [], [], [], [], []
    frames, next_frame = [], 0.0
    phase, t_rev, reversed_at_angle = "fwd", None, None
    diverged = False
    lash_pin0 = None; backlash_meas = 0.0

    while True:
        # phase machine: ramp+fwd until pinion has done n_rev, then reverse until back n_rev
        if phase == "fwd":
            ctrl = min(omega, omega * d.time / RAMP)
            if d.qpos[ipa] >= total_angle:
                if forward_only:
                    break
                phase, t_rev, lash_pin0 = "rev", d.time, d.qpos[ipa]
                gear_at_rev = d.qpos[iga]
        else:
            ctrl = -min(omega, omega * (d.time - t_rev) / RAMP)
        d.ctrl[0] = ctrl
        mujoco.mj_step(model, d)

        if not np.all(np.isfinite(d.qpos)) or abs(d.qvel[0]) > 200 or abs(d.qvel[1]) > 200:
            diverged = True
            break

        tp, tg = float(d.qpos[ipa]), float(d.qpos[iga])
        te_now = tg - ratio_ideal * tp          # transmission error (rad): 0 = perfect conjugate
        fmax = max([abs(d.contact[i].dist) for i in range(d.ncon)] + [0.0])
        ts.append(d.time); thp.append(tp); thg.append(tg); te.append(te_now)
        force.append(d.ncon); wp.append(float(d.qvel[0]))

        # backlash via reversal lash: after reversing, the pinion rotates while the gear is still
        # (drive flank disengaged) until the coast flank takes up — that pinion travel is the lash.
        if phase == "rev" and lash_pin0 is not None and backlash_meas == 0.0:
            if abs(d.qpos[iga] - gear_at_rev) > np.deg2rad(0.5):     # gear has started to move back
                lash_angle = abs(d.qpos[ipa] - lash_pin0)
                backlash_meas = float(lash_angle * rp1)              # arc length at pitch radius
        if record and d.time >= next_frame:
            renderer.update_scene(d, camera=cam)
            fr = renderer.render()
            fr = _hud(fr, [f"T {d.time:4.2f}S  {phase.upper()}",
                           f"PIN {np.rad2deg(tp):6.0f}  GEAR {np.rad2deg(tg):6.0f}",
                           f"RATIO {tg/tp if abs(tp)>1e-3 else 0:+5.2f}  IDEAL {ratio_ideal:+.2f}",
                           f"TE {np.rad2deg(te_now):+5.2f}  NCON {d.ncon}"],
                      colors=[(220, 220, 220), (120, 200, 255), (140, 255, 160), (255, 200, 120)])
            frames.append(fr); next_frame += 1.0 / FPS

        if phase == "rev" and d.qpos[ipa] <= 0.0:
            break
        if d.time > (2 * n_rev * 2 * np.pi / omega + 4 * RAMP + 2.0):   # safety wall-clock bound
            break

    if renderer:
        renderer.close()

    thp_a, thg_a, te_a = np.array(thp), np.array(thg), np.array(te)
    revs_done = float(thp_a.max() / (2 * np.pi)) if len(thp_a) else 0.0
    # ratio over the steady forward portion (after ramp, before reversal)
    if len(thp_a) > 10 and thp_a.max() > np.deg2rad(30):
        mask = (thp_a > np.deg2rad(20))
        ratio = float(np.polyfit(thp_a[mask], thg_a[mask], 1)[0]) if mask.sum() > 5 else 0.0
    else:
        ratio = 0.0
    ratio_err = (ratio - ratio_ideal) / abs(ratio_ideal) * 100 if ratio else 100.0
    te_max = float(np.rad2deg(np.abs(te_a)).max()) if len(te_a) else 999.0
    # slip = a TE jump larger than half a tooth pitch between consecutive samples
    slip = bool(len(te_a) > 1 and np.rad2deg(np.abs(np.diff(te_a))).max() > tooth_pitch_deg / 2)
    # jam = pinion never tracked a meaningful fraction of the target speed (actuator saturated)
    jammed = bool(len(wp) and np.percentile(np.abs(wp), 90) < 0.2 * omega and not diverged)

    v = GearVerdict(dt=dt, diverged=diverged, theta_pin_deg=float(np.rad2deg(thp_a.max()) if len(thp_a) else 0),
                    theta_gear_deg=float(np.rad2deg(np.abs(thg_a).max()) if len(thg_a) else 0),
                    ratio=round(ratio, 4), ratio_err_pct=round(ratio_err, 2),
                    te_max_deg=round(te_max, 3), slip=slip, jammed=jammed,
                    backlash_meas_mm=round(backlash_meas, 3),
                    backlash_design_mm=meta["backlash_design_mm"], revs_done=round(revs_done, 2))
    series = {"t": ts, "theta_pin_deg": list(np.rad2deg(thp_a)),
              "theta_gear_deg": list(np.rad2deg(thg_a)), "te_deg": list(np.rad2deg(te_a)),
              "ncon": force, "omega_pin": wp}
    return v, series, frames


def run_rung(tag, model_path, meta_path, dt_ladder, omega=3.0, n_rev=1.0, record=False):
    """Run one ladder rung: G-CONV, then P-GEAR at the frozen dt; on divergence, the §6.4 retry at
    half dt. Any dt below the retry is OUT OF BOUNDS (preset violation) — recorded, not scored as a
    pass. dt_ladder lists the dts to try IN ORDER; entries past index 1 are labelled out-of-bounds."""
    model = mujoco.MjModel.from_xml_path(str(model_path))
    meta = json.loads(Path(meta_path).read_text())
    print(f"\n=== rung {tag}  profile={meta['profile']} n_wedge={meta['n_wedge']} "
          f"op_cd={meta['center_distance_mm']} backlash_real={meta['backlash_realised_mm']} ===")
    gok, _ = g_conv(model, verbose=True)
    result = {"tag": tag, "meta": {k: meta[k] for k in
              ("profile", "n_wedge", "center_distance_mm", "backlash_realised_mm", "z1", "z2")},
              "g_conv": bool(gok), "attempts": []}
    if not gok:
        result["verdict"] = False
        result["note"] = "G-CONV failed — model does not hold together; not simulating."
        return result, None, None

    best = None
    for i, dt in enumerate(dt_ladder):
        in_bounds = i <= 1     # frozen dt (i=0) + the single §6.4 half-step retry (i=1)
        v, series, frames = run_gear(mujoco.MjModel.from_xml_path(str(model_path)), meta,
                                     dt=dt, omega=omega, n_rev=n_rev, record=(record and in_bounds))
        ok = v.passed()
        result["attempts"].append({"dt": dt, "in_bounds": in_bounds, "passed": ok,
                                   **asdict(v)})
        print(f"  dt={dt:.1e} {'(frozen)' if i==0 else '(§6.4 retry)' if i==1 else '(OUT OF BOUNDS)'}"
              f"  {'PASS' if ok else 'FAIL'}  ratio={v.ratio:+.3f} err={v.ratio_err_pct:+.1f}% "
              f"TE={v.te_max_deg:.2f}° slip={v.slip} jam={v.jammed} "
              f"backlash={v.backlash_meas_mm:.2f}mm {'DIVERGED' if v.diverged else ''}")
        if ok and best is None:
            best = (v, series, frames, dt, in_bounds)
        if ok and in_bounds:
            break
    # rung passes ONLY if it converged within the frozen dt + single retry (R5 / §6.4)
    passed_in_bounds = any(a["passed"] and a["in_bounds"] for a in result["attempts"])
    result["verdict"] = bool(passed_in_bounds)
    result["stable_only_below_preset"] = bool(best is not None and not best[4])
    return result, (best[1] if best else series), (best[2] if best else frames)


if __name__ == "__main__":
    print("use run_ladder.py")
