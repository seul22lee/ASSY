"""m17 — the headless drive+measure loop, mirroring m1_gear/r2b_viz.capture() with NO Renderer.

The drive is a velocity servo on the pinion shaft (gain KV, bias -KV), ramped to OMEGA over RAMP;
the gear shaft is a passive journal and the ratio must EMERGE from tooth contact. Divergence =
(non-finite qpos) OR |pinion qvel| > 200. Peak contact force = max over d.ncon of |mj_contactForce|,
captured EACH step (so the blow-up spike on the diverging step is recorded before the state goes
non-finite). This is a measurement harness only — it changes no preset.
"""

from __future__ import annotations

import os

import mujoco
import numpy as np

# SDF plugins live in a single directory; the loader takes ONE string arg (no callback).
mujoco.mj_loadAllPluginLibraries(os.path.join(os.path.dirname(mujoco.__file__), "plugin"))

KV = 5e-5          # velocity-servo gain (actuation, sized to grams-scale inertia — NOT a preset)
OMEGA, RAMP, SEED = 3.0, 0.5, 0
FROZEN, FINE = 5e-4, 2e-5


def _dofadr(model, joint):
    return model.jnt_dofadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint)]


def _max_contact_force(model, d):
    f = 0.0
    for i in range(d.ncon):
        c6 = np.zeros(6)
        mujoco.mj_contactForce(model, d, i, c6)
        v = float(np.linalg.norm(c6[:3]))
        if np.isfinite(v):
            f = max(f, v)
    return f


def drive_measure(model, dt, t_end=0.35, kv=KV, omega=OMEGA, ramp=RAMP, seed=SEED,
                  settle_after=None, settle_start=None, drive_joint="pinion_shaft",
                  gear_joint="gear_shaft"):
    """Run one driven roll to t_end (or divergence). `settle_start`: hold the drive at 0 for the first
    `settle_start` seconds (let the seating penetration relax) THEN ramp — used by the dt-scale ladder
    to shed the seating transient so the CLEAN-ROLL ratio is what's judged. `settle_after`: cut the
    drive to 0 after that time. `peak_post` is the peak contact force AFTER settle_start (the clean-roll
    peak, excluding the seating transient). Returns raw numbers."""
    model.opt.timestep = dt
    a = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, "drive")
    model.actuator_gainprm[a, 0] = kv
    model.actuator_biasprm[a, 2] = -kv
    d = mujoco.MjData(model)
    pin = _dofadr(model, drive_joint)
    ig_q = model.jnt_qposadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, gear_joint)]
    ig_v = _dofadr(model, gear_joint)
    rng = np.random.default_rng(seed)
    d.qpos[ig_q] += rng.uniform(-1e-4, 1e-4)
    mujoco.mj_forward(model, d)
    ncon0 = int(d.ncon)

    ts, force, wp = [], [], []
    peak, peak_post, diverged, last_t = 0.0, 0.0, False, 0.0
    s0 = settle_start or 0.0
    while d.time < t_end:
        if settle_after is not None and d.time > settle_after:
            drive = 0.0
        elif d.time < s0:
            drive = 0.0                                    # settle: let the seating transient relax
        else:
            drive = min(omega, omega * (d.time - s0) / ramp)
        d.ctrl[0] = drive
        mujoco.mj_step(model, d)
        f = _max_contact_force(model, d)
        if np.isfinite(f):
            peak = max(peak, f)
            if d.time >= s0:
                peak_post = max(peak_post, f)
        ts.append(d.time)
        force.append(f if np.isfinite(f) else peak)
        wp.append(float(d.qvel[pin]) if np.isfinite(d.qvel[pin]) else float("nan"))
        last_t = d.time
        if not np.all(np.isfinite(d.qpos)) or abs(d.qvel[pin]) > 200:
            diverged = True
            break

    wpin = float(d.qvel[pin]) if np.isfinite(d.qvel[pin]) else float("nan")
    wgear = float(d.qvel[ig_v]) if np.isfinite(d.qvel[ig_v]) else float("nan")
    ratio = (wgear / wpin) if abs(wpin) > 1e-6 and np.isfinite(wpin) else None
    return {"dt": dt, "peak_force_N": peak, "peak_post_settle_N": peak_post,
            "diverged": bool(diverged), "t_final": round(last_t, 4),
            "omega_pinion": round(wpin, 3) if np.isfinite(wpin) else None,
            "omega_gear": round(wgear, 3) if np.isfinite(wgear) else None,
            "ratio": round(ratio, 3) if ratio is not None else None,
            "ncon0": ncon0, "t": ts, "force": force, "wp": wp}
