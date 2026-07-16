"""M0: G-CONV gate + P-HINGE protocol (spec 6.2, 6.3, 6.4).

G-CONV -- does the converted model even hold together?
    (a) every body has mass > 0
    (b) no initial penetration (no contact-force blow-up after one step)
    (c) under gravity alone the assembly stays at rest for 1 s

P-HINGE -- actuate, observe, judge (spec 6.3):
    actuate  force ramp 0 -> F_max at the midpoint of the lid's free edge, then reversed
    observe  hinge angle theta(t), max contact penetration
    judge    theta_max >= 90 deg;  sweep penetration <= 0.2 mm;  theta_final <= 5 deg

On the force direction -- a finding, not a liberty. Spec 6.3 says the ramp acts in the
"vertical opening direction". Taken literally (world +Z) that protocol is *unsatisfiable*:
the torque a world-vertical tip force exerts about the hinge scales with cos(theta), so it
vanishes at 90 deg and *inverts* beyond it. A lid that opens past 90 deg goes over-centre --
gravity then holds it open and reversing the vertical force pushes it further open, so
theta_final <= 5 deg can never be met. Both force modes are implemented and both are run:
`world_z` reproduces the spec as written (and fails), `follower` presses normal to the lid
face -- what a finger actually does -- and gives constant control authority in both
directions. See FINDINGS.md; spec 6.3 should be amended.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

import imageio.v2 as imageio
import mujoco
import numpy as np

VARIANT = os.environ.get("M0_VARIANT", "nostop")
OUT = Path(__file__).parent / "out" / VARIANT

# --- protocol constants ---------------------------------------------------------------
F_MAX = 0.15  # N. ~1.6x the lid's gravity torque at the tip -> quasi-static open.
T_RAMP, T_HOLD, T_REV, T_SETTLE = 1.0, 1.0, 1.0, 1.0
T_END = T_RAMP + T_HOLD + T_REV + T_SETTLE
FPS = 60

# --- judge thresholds (spec 6.3 P-HINGE) ----------------------------------------------
THETA_OPEN_MIN = np.deg2rad(90.0)
PENETRATION_MAX = 0.2e-3  # m
THETA_CLOSED_MAX = np.deg2rad(5.0)

N_SEEDS = 5
SEED_PASS = 4  # verdict = pass on >= 4 of 5 (spec 6.4)


THETA_TARGET = np.deg2rad(95.0)  # "open" -- a little past the 90 deg criterion


def force_schedule(t: float, t_open: float | None = None) -> float:
    """Ramp 0 -> F_max to open; once the lid is *observed* open, ramp through to -F_max to
    close. Force-driven throughout: no position or velocity is ever imposed (spec D3).

    Why the reversal is triggered by the observable rather than by the clock: a follower
    force has a constant moment arm, so it never loses authority -- it is a motor. With no
    end stop it does not open the lid, it *spins* it: in V-B the lid went round past 180 deg
    and hit the floor. V-A only looked fine because the joint's `range` quietly acted as an
    end stop that the real geometry does not have. Driving until the goal is met, then
    releasing, is also what a hand does. See FINDINGS 3.6.
    """
    if t_open is None:  # not yet open: keep ramping up (capped at F_max)
        return min(F_MAX, F_MAX * t / T_RAMP)
    u = (t - t_open) / T_REV
    return F_MAX * max(-1.0, 1.0 - 2.0 * u)  # +F_max -> -F_max, then hold


@dataclass
class Verdict:
    theta_max_deg: float
    theta_final_deg: float
    penetration_max_mm: float
    diverged: bool

    def criteria(self) -> dict[str, dict]:
        return {
            "theta_max >= 90 deg": {
                "value": round(self.theta_max_deg, 2), "threshold": 90.0,
                "pass": bool(self.theta_max_deg >= 90.0 and not self.diverged),
            },
            "sweep penetration <= 0.2 mm": {
                "value": round(self.penetration_max_mm, 4), "threshold": 0.2,
                "pass": bool(self.penetration_max_mm <= 0.2 and not self.diverged),
            },
            "theta_final <= 5 deg (returns closed)": {
                "value": round(self.theta_final_deg, 2), "threshold": 5.0,
                "pass": bool(self.theta_final_deg <= 5.0 and not self.diverged),
            },
        }

    @property
    def passed(self) -> bool:
        return all(c["pass"] for c in self.criteria().values())


def max_penetration(d: mujoco.MjData) -> float:
    """Deepest contact penetration this step, in metres. MuJoCo's contact.dist is negative
    when the geoms overlap."""
    if d.ncon == 0:
        return 0.0
    return max(0.0, float(-min(d.contact[i].dist for i in range(d.ncon))))


# --- G-CONV ---------------------------------------------------------------------------


def g_conv(model: mujoco.MjModel, verbose: bool = True) -> tuple[bool, list]:
    checks = []
    d = mujoco.MjData(model)

    # (a) mass
    for b in range(1, model.nbody):
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, b)
        mass = float(model.body_mass[b])
        checks.append((f"(a) {name}: mass > 0", mass > 0, f"{mass*1000:.2f} g"))

    # (b) no initial penetration / no contact-force blow-up after one step
    mujoco.mj_forward(model, d)
    pen0 = max_penetration(d)
    checks.append(("(b) no initial penetration", pen0 <= 1e-6, f"{pen0*1e3:.4f} mm at t=0"))
    mujoco.mj_step(model, d)
    f1 = float(np.abs(d.qfrc_constraint).max()) if d.qfrc_constraint.size else 0.0
    checks.append(("(b) no contact-force blow-up after 1 step", f1 < 1e3 and np.isfinite(f1),
                   f"max constraint force {f1:.3e} N"))

    # (c) at rest for 1 s under gravity alone
    d = mujoco.MjData(model)
    mujoco.mj_forward(model, d)
    q0 = d.qpos.copy()
    n = int(1.0 / model.opt.timestep)
    peak_v = 0.0
    for _ in range(n):
        mujoco.mj_step(model, d)
        peak_v = max(peak_v, float(np.abs(d.qvel).max()) if d.qvel.size else 0.0)
        if not np.all(np.isfinite(d.qpos)):
            break
    finite = bool(np.all(np.isfinite(d.qpos)))
    drift = float(np.abs(d.qpos - q0).max()) if finite and d.qpos.size else float("inf")
    at_rest = finite and drift < 5e-3 and peak_v < 0.5
    checks.append(("(c) at rest 1 s under gravity", at_rest,
                   f"max drift {drift*1e3:.3f} mm/mrad, peak |v| {peak_v:.4f}"))

    ok = all(c[1] for c in checks)
    if verbose:
        w = max(len(c[0]) for c in checks)
        print("\n  G-CONV")
        for label, passed, detail in checks:
            print(f"    {'PASS' if passed else 'FAIL':4s}  {label:<{w}}  {detail}")
    return ok, checks


# --- P-HINGE --------------------------------------------------------------------------


def run_p_hinge(model, meta, force_mode="follower", seed=0, record=False):
    d = mujoco.MjData(model)
    rng = np.random.default_rng(seed)

    lid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "lid_panel")
    hinge_adr = model.jnt_qposadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "hinge")]
    # The force acts on a *material point of the lid*, so its application point moves with
    # the lid. Reading the site's current world position each step is what makes the moment
    # arm shrink as the lid approaches vertical -- which is the whole physics of the
    # over-centre problem below. (Applying at a fixed world point instead silently turns
    # any force mode into a constant-moment-arm actuator.)
    tip_site = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, "lid_tip")

    # Seeds perturb the initial state within the joint's own clearance -- they probe
    # robustness, they do not re-tune the model (spec 6.4 / R5).
    d.qpos[hinge_adr] = rng.uniform(0.0, 2e-3)
    mujoco.mj_forward(model, d)

    renderer = mujoco.Renderer(model, 480, 640) if record else None
    cam = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_CAMERA, "iso")

    ts, thetas, forces, pens = [], [], [], []
    frames = []
    next_frame = 0.0
    diverged = False
    t_open: float | None = None

    while d.time < T_END:
        F = force_schedule(d.time, t_open)
        if force_mode == "follower":
            # Normal to the lid face: constant moment arm about the hinge in both
            # directions. Body +Z is the panel normal by construction.
            f_world = d.xmat[lid].reshape(3, 3) @ np.array([0.0, 0.0, F])
        else:  # "world_z" -- spec 6.3 read literally
            f_world = np.array([0.0, 0.0, F])

        d.qfrc_applied[:] = 0.0
        mujoco.mj_applyFT(model, d, f_world, np.zeros(3), d.site_xpos[tip_site], lid,
                          d.qfrc_applied)
        mujoco.mj_step(model, d)

        if not np.all(np.isfinite(d.qpos)):
            diverged = True
            break

        theta_now = float(d.qpos[hinge_adr])
        if t_open is None and theta_now >= THETA_TARGET:
            t_open = d.time

        ts.append(d.time)
        thetas.append(theta_now)
        forces.append(F)
        pens.append(max_penetration(d))

        if record and d.time >= next_frame:
            renderer.update_scene(d, camera=cam)
            frames.append(renderer.render())
            next_frame += 1.0 / FPS

    if renderer:
        renderer.close()

    theta = np.array(thetas)
    v = Verdict(
        theta_max_deg=float(np.rad2deg(theta.max())) if len(theta) else 0.0,
        # "returns closed" = where it settles at the end, not an instantaneous sample
        theta_final_deg=float(np.rad2deg(theta[-int(0.1 / model.opt.timestep):].mean()))
        if len(theta) else 180.0,
        penetration_max_mm=float(max(pens) * 1e3) if pens else 0.0,
        diverged=diverged,
    )
    series = {"t": ts, "theta_deg": list(np.rad2deg(theta)), "force_N": forces,
              "penetration_mm": [p * 1e3 for p in pens]}
    return v, series, frames


def plot(series, v: Verdict, path: Path, title: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(3, 1, figsize=(8, 7), sharex=True,
                             gridspec_kw={"height_ratios": [3, 1, 1]})
    t = series["t"]

    ax = axes[0]
    ax.plot(t, series["theta_deg"], lw=2, color="#2b6cb0")
    ax.axhline(90, ls="--", c="#c53030", lw=1)
    ax.axhspan(90, max(120, max(series["theta_deg"] + [95]) + 5), color="#c6f6d5", alpha=.5)
    ax.axhspan(-5, 5, color="#bee3f8", alpha=.6)
    ax.text(t[-1], 91, " theta_max >= 90", color="#c53030", va="bottom", ha="right", fontsize=8)
    ax.set_ylabel("hinge angle theta (deg)")
    badge = "PASS" if v.passed else "FAIL"
    ax.set_title(f"{title}   [{badge}]  theta_max={v.theta_max_deg:.1f} deg, "
                 f"theta_final={v.theta_final_deg:.1f} deg, pen={v.penetration_max_mm:.3f} mm",
                 color="#22543d" if v.passed else "#742a2a", fontsize=10)
    ax.grid(alpha=.25)

    ax = axes[1]
    ax.plot(t, series["force_N"], lw=1.5, color="#805ad5")
    ax.axhline(0, c="k", lw=.5)
    ax.set_ylabel("F (N)")
    ax.grid(alpha=.25)

    ax = axes[2]
    ax.plot(t, series["penetration_mm"], lw=1.5, color="#dd6b20")
    ax.axhline(0.2, ls="--", c="#c53030", lw=1)
    ax.set_ylabel("penetration (mm)")
    ax.set_xlabel("t (s)")
    ax.grid(alpha=.25)

    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "V-A"
    xml = OUT / f"hinge_{mode}.xml"
    meta = json.loads((OUT / f"hinge_{mode}_meta.json").read_text())
    model = mujoco.MjModel.from_xml_path(str(xml))

    print(f"\n=== M0  {mode}  ({xml.name}) ===")
    ok, _ = g_conv(model)
    if not ok:
        raise SystemExit("\nG-CONV FAILED -- the converted model is broken. "
                         "Do not trust anything downstream.")

    report = {"mode": mode, "contact_preset": meta["contact_preset"], "runs": {}}

    for force_mode in ("follower", "world_z"):
        print(f"\n  P-HINGE  force_mode={force_mode}   ({N_SEEDS} seeds)")
        verdicts = []
        for seed in range(N_SEEDS):
            rec = seed == 0
            v, series, frames = run_p_hinge(model, meta, force_mode, seed, record=rec)
            verdicts.append(v)
            if rec:
                plot(series, v, OUT / f"t2_P-HINGE_{force_mode}.png",
                     f"P-HINGE / {mode} / {force_mode}")
                if frames:
                    imageio.mimsave(OUT / f"t2_P-HINGE_{force_mode}.mp4", frames, fps=FPS)
                (OUT / f"t2_P-HINGE_{force_mode}.csv").write_text(
                    "t,theta_deg,force_N,penetration_mm\n"
                    + "\n".join(
                        f"{a:.5f},{b:.5f},{c:.5f},{e:.6f}"
                        for a, b, c, e in zip(series["t"], series["theta_deg"],
                                              series["force_N"], series["penetration_mm"])
                    )
                )
            print(f"    seed {seed}: {'PASS' if v.passed else 'FAIL'}  "
                  f"theta_max {v.theta_max_deg:6.1f}  theta_final {v.theta_final_deg:6.1f}  "
                  f"pen {v.penetration_max_mm:.3f} mm" + ("  DIVERGED" if v.diverged else ""))

        n_pass = sum(v.passed for v in verdicts)
        verdict = n_pass >= SEED_PASS
        print(f"    -> {n_pass}/{N_SEEDS} seeds pass  =>  {'PASS' if verdict else 'FAIL'}")
        for name, c in verdicts[0].criteria().items():
            print(f"       {'ok  ' if c['pass'] else 'FAIL'} {name:<40s} {c['value']}")

        report["runs"][force_mode] = {
            "seeds_passed": n_pass, "n_seeds": N_SEEDS, "verdict": verdict,
            "criteria_seed0": verdicts[0].criteria(),
            "per_seed": [asdict(v) for v in verdicts],
        }

    (OUT / "t2_verdict.json").write_text(json.dumps(report, indent=2))
    print(f"\nwrote {OUT/'t2_verdict.json'}")


if __name__ == "__main__":
    main()
