"""What R2b looks like: the SAME involute pair (n4, ideal cd, same seed) driven at the FROZEN preset
dt (5e-4) vs dt/25 (2e-5). The geometry is identical and conjugate (R2a retired) — only the timestep
differs. Frozen chatters (contact makes/breaks, force spikes) and blows up; dt/25 rolls calmly at
ratio −0.5. Produces a side-by-side HUD video + a contact-force / pinion-velocity comparison panel.

  out/r2b_frozen_vs_fine.mp4   side-by-side HUD (left frozen → blow-up, right dt/25 → calm roll)
  out/r2b_frozen_vs_fine.png   max contact force + pinion ω traces, frozen vs dt/25 (chatter vs calm)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "m0"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import imageio.v2 as imageio
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mujoco
import numpy as np

import gear_mjcf
from p_gear import FPS, KV
from vb import _hud

OUT = Path(__file__).parent / "out"
FROZEN, FINE = 5e-4, 2e-5
OMEGA, RAMP, SEED = 3.0, 0.5, 0


def _max_contact_force(model, d):
    f = 0.0
    for i in range(d.ncon):
        c6 = np.zeros(6); mujoco.mj_contactForce(model, d, i, c6)
        f = max(f, float(np.linalg.norm(c6[:3])))
    return f


def capture(model_path, dt, t_end, record=True):
    model = mujoco.MjModel.from_xml_path(str(model_path))
    model.opt.timestep = dt
    a = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, "drive")
    model.actuator_gainprm[a, 0] = KV; model.actuator_biasprm[a, 2] = -KV
    d = mujoco.MjData(model)
    rng = np.random.default_rng(SEED)
    iga = model.jnt_qposadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "gear_shaft")]
    d.qpos[iga] += rng.uniform(-1e-4, 1e-4); mujoco.mj_forward(model, d)
    r = mujoco.Renderer(model, 360, 480) if record else None
    cam = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_CAMERA, "top")

    ts, force, wp, frames = [], [], [], []
    nextf, diverged = 0.0, False
    while d.time < t_end:
        d.ctrl[0] = min(OMEGA, OMEGA * d.time / RAMP)
        mujoco.mj_step(model, d)
        if not np.all(np.isfinite(d.qpos)) or abs(d.qvel[0]) > 200:
            diverged = True
        f = _max_contact_force(model, d) if not diverged else force[-1] if force else 0.0
        ts.append(d.time); force.append(f); wp.append(float(d.qvel[0]) if not diverged else wp[-1])
        if record and d.time >= nextf:
            if not diverged:
                r.update_scene(d, camera=cam); img = r.render()
            frames.append((img.copy(), d.time, f, d.ncon, diverged))
            nextf += 1.0 / FPS
        if diverged:
            break
    if r:
        r.close()
    return {"t": ts, "force": force, "wp": wp, "frames": frames, "diverged": diverged}


def main():
    xml, meta = gear_mjcf.build("involute", 4, tag="r2b_inv_n4", op_cd=36.0)
    t_end = 0.35
    fr = capture(xml, FROZEN, t_end)
    fi = capture(xml, FINE, t_end)
    print(f"frozen dt: {len(fr['frames'])} frames, diverged={fr['diverged']} at t≈{fr['t'][-1]:.3f}, "
          f"peak force {max(fr['force']):.2e} N")
    print(f"dt/25    : {len(fi['frames'])} frames, diverged={fi['diverged']} at t≈{fi['t'][-1]:.3f}, "
          f"peak force {max(fi['force']):.2e} N")

    # side-by-side HUD video (pad frozen with its last blow-up frame to match dt/25 length)
    n = max(len(fr["frames"]), len(fi["frames"]))
    def hud_frame(fset, i, label):
        img, t, f, nc, dv = fset[min(i, len(fset) - 1)]
        tag = "DIVERGED" if dv else "OK"
        return _hud(img, [f"{label}", f"T {t:5.3f}S  {tag}", f"CONTACT F {f:6.1f}N", f"NCON {nc}"],
                    colors=[(255, 255, 255), (255, 150, 90) if dv else (140, 255, 160),
                            (255, 120, 120) if f > 50 else (200, 200, 255), (200, 200, 200)])
    vid = []
    for i in range(n):
        L = hud_frame(fr["frames"], i, f"FROZEN dt={FROZEN:.0e}")
        R = hud_frame(fi["frames"], i, f"dt/25 = {FINE:.0e}")
        vid.append(np.hstack([L, R]))
    imageio.mimsave(OUT / "r2b_frozen_vs_fine.mp4", vid, fps=FPS)

    # comparison panel
    fig, ax = plt.subplots(2, 1, figsize=(9, 6.5), sharex=True)
    ax[0].plot(fr["t"], np.maximum(fr["force"], 1e-3), color="#c53030", lw=1.2,
               label=f"frozen dt={FROZEN:.0e} (chatter → blow-up to {max(fr['force']):.0e} N)")
    ax[0].plot(fi["t"], np.maximum(fi["force"], 1e-3), color="#2f855a", lw=1.2,
               label=f"dt/25={FINE:.0e} (calm, peak {max(fi['force']):.2f} N)")
    ax[0].set_yscale("log"); ax[0].set_ylim(1e-2, 1e18)
    ax[0].set_ylabel("max contact\nforce (N, log)"); ax[0].legend(fontsize=8, loc="upper left")
    ax[0].grid(alpha=.25, which="both")
    ax[0].set_title("What R2b looks like — SAME involute pair, identical & conjugate geometry (R2a), "
                    "only dt differs", fontsize=10)
    ax[1].plot(fr["t"], fr["wp"], color="#c53030", lw=1.2)
    ax[1].plot(fi["t"], fi["wp"], color="#2f855a", lw=1.2)
    ax[1].axhline(OMEGA, ls="--", c="#888", lw=0.8, label=f"drive target ω={OMEGA}")
    ax[1].set_ylabel("pinion ω\n(rad/s)"); ax[1].set_xlabel("t (s)"); ax[1].legend(fontsize=8); ax[1].grid(alpha=.25)
    fig.tight_layout(); fig.savefig(OUT / "r2b_frozen_vs_fine.png", dpi=140); plt.close(fig)
    print("wrote r2b_frozen_vs_fine.mp4 + r2b_frozen_vs_fine.png")


if __name__ == "__main__":
    main()
