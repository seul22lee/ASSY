"""Stage ⑨ (Tier2) runner — G-CONV gate + P-HINGE (V-A and V-B) on a COMPILED assembly, with the
guard trio on the verdict (D-M1-6). Reuses m0's proven G-CONV and the frozen preset (R5).

Entry point `t2(parts, hints, axis, roles, modes, ...)`:
  1. emit MJCF per mode (verify.t2_physics.mjcf, D23 fixture from is_base)
  2. G9 = G-CONV: the converted model holds together (mass>0, no initial penetration, at rest 1s)
  3. P-HINGE per assigned mode (V-A declared-joint; V-B contact-only — the DoF emerges from the
     card's ring-of-wedges bore hint)
  4. verdict dict carrying decision_row + compile_hash + shape_assert (guard trio)

This is where the pipeline's OWN output first goes through physics: t0/t1 check the geometry; t2
checks it MOVES.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import mujoco
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "m0"))
from p_hinge import g_conv  # reuse M0's proven G-CONV gate  # noqa: E402

from verify.t2_physics.mjcf import build_mjcf


def _hash():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       cwd=Path(__file__).parent).decode().strip()
    except Exception:
        return "nogit"


def g9_gconv(model) -> tuple[bool, list]:
    """Gate G9 (spec §4-⑨): the converted model is physically coherent before any protocol runs.
    Delegates to M0's g_conv (mass>0; no initial penetration / no 1-step contact blow-up; at rest
    1 s under gravity)."""
    return g_conv(model, verbose=False)


def t2(parts: dict, hints: dict, axis: dict, roles: dict, modes: list, out_dir: Path,
       base_pid: str, mover_pid: str, pin_pid: str, tag: str, decision_row: str = "") -> dict:
    """Run Tier2 for the assigned modes. `parts` = {pid: build123d Solid} (⑥ output); `hints` =
    {pid: collision prims}; `axis` = {point,dir} mm; `roles` = {pid: base|mover|hardware|other}."""
    out_dir.mkdir(parents=True, exist_ok=True)
    meshdir = out_dir / "assets"
    result = {"decision_row": decision_row or "stage-⑨ t2", "compile_hash": _hash(),
              "tag": tag, "modes": {}, "shape_assert": {}}
    for mode in modes:
        xml, meta = build_mjcf(parts, hints, axis, base_pid, mover_pid, pin_pid, mode, meshdir,
                               roles, tag)
        xf = out_dir / f"t2_{tag}_{mode}.xml"; xf.write_text(xml)
        model = mujoco.MjModel.from_xml_path(str(xf))
        gok, checks = g9_gconv(model)
        entry = {"xml": xf.name, "masses_kg": meta["masses_kg"], "g9_gconv": bool(gok),
                 "g9_checks": [(c[0], bool(c[1]), c[2]) for c in checks]}
        # P-HINGE protocol runs only if G9 holds (a broken model answers nothing — M0 rule)
        if gok:
            entry["p_hinge"] = _run_p_hinge(model, meta, mode)
        else:
            entry["p_hinge"] = {"ran": False, "reason": "G9 (G-CONV) failed — model not coherent"}
        result["modes"][mode] = entry
    # guard trio: shape assertion tied to the claim (every assigned mode has a verdict)
    result["shape_assert"] = {"modes_covered": sorted(result["modes"].keys()) == sorted(modes),
                              "g9_all_pass": all(m["g9_gconv"] for m in result["modes"].values())}
    result["verdict"] = all(m["g9_gconv"] and m.get("p_hinge", {}).get("passed", False)
                            for m in result["modes"].values())
    return result


def _run_p_hinge(model, meta, mode, seed=0):
    """Force-driven P-HINGE (§6.3): a follower-force ramp opens the mover about the hinge, then
    reverses to close. Judge theta_max>=90°, penetration<=0.2mm, theta_final<=5° (M0 P-HINGE). V-A
    reads the hinge joint angle; V-B measures the mover's rotation relative to the (welded) base."""
    import mujoco as mj
    from p_hinge import F_MAX, T_END, T_RAMP, THETA_TARGET

    d = mj.MjData(model)
    rng = np.random.default_rng(seed)
    mover = mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, meta["mover"])
    base = mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, meta["base"])
    hinge_jid = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "hinge") if mode == "V-A" else -1
    # apply the follower force at the mover's far extent (its COM offset along +Y as a proxy tip)
    mj.mj_forward(model, d)
    if mode == "V-A":
        adr = model.jnt_qposadr[hinge_jid]
        d.qpos[adr] = rng.uniform(0.0, 2e-3)
    mj.mj_forward(model, d)
    R_base0 = d.xmat[base].reshape(3, 3).copy()

    def theta():
        if mode == "V-A":
            return float(d.qpos[model.jnt_qposadr[hinge_jid]])
        R = R_base0.T @ d.xmat[mover].reshape(3, 3)   # mover rotation rel base, about hinge (+X)
        return float(np.arctan2(R[2, 1], R[1, 1]))

    tip = d.xpos[mover].copy(); tip[1] += 0.03           # a point out on the mover for the moment arm
    th, pen, diverged, t_open = [], [], False, None
    while d.time < T_END:
        F = min(F_MAX, F_MAX * d.time / T_RAMP) if t_open is None else \
            F_MAX * max(-1.0, 1.0 - 2.0 * (d.time - t_open) / 1.0)
        d.qfrc_applied[:] = 0.0
        f_world = d.xmat[mover].reshape(3, 3) @ np.array([0.0, 0.0, F])
        mj.mj_applyFT(model, d, f_world, np.zeros(3), d.xpos[mover] + np.array([0, 0.03, 0]),
                      mover, d.qfrc_applied)
        mj.mj_step(model, d)
        if not np.all(np.isfinite(d.qpos)):
            diverged = True; break
        t = theta()
        if t_open is None and t >= THETA_TARGET:
            t_open = d.time
        th.append(t)
        pen.append(max([max(0.0, -d.contact[i].dist) for i in range(d.ncon)] + [0.0]))
    tha = np.array(th)
    n_tail = max(1, int(0.1 / model.opt.timestep))
    v = {"theta_max_deg": float(np.rad2deg(tha.max())) if len(tha) else 0.0,
         "theta_final_deg": float(np.rad2deg(np.abs(tha[-n_tail:]).mean())) if len(tha) else 180.0,
         "penetration_max_mm": float(max(pen) * 1e3) if pen else 0.0, "diverged": diverged}
    v["passed"] = bool(v["theta_max_deg"] >= 90 and v["penetration_max_mm"] <= 0.2
                       and v["theta_final_deg"] <= 5 and not diverged)
    v["ran"] = True
    return v
