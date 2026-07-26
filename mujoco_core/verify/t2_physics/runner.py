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


# --- protocol constants (M0 P-HINGE, R5-frozen) ---------------------------------------------
N_SEEDS, SEED_PASS, FPS = 5, 4, 60
F_MAX, T_RAMP, T_HOLD, T_REV, T_SETTLE = 0.15, 1.0, 1.0, 1.0, 1.0
T_END = T_RAMP + T_HOLD + T_REV + T_SETTLE          # 4 s: open, hold, reverse, settle (M0)
THETA_TARGET = np.deg2rad(95.0)
# penetration stratification (D22): a stray travel contact is a defect; the closing seat, the
# pin/bore interface, and the low-angle latch-release window are INTENDED contacts.
SEAT_BAND_DEG = 10.0        # |theta| <= this → lid<->box contact is the closing seat OR the latch
STOP_BAND_DEG = 14.0       # within this of the open-stop angle → intended end-stop contact (D22)
CLOSED_DEG = 3.0           # |theta| <= this → fully closed (bounce detection)
TRAVEL_PEN_LIMIT = 0.2     # mm — non-intended travel contact = defect
SEAT_PEN_LIMIT = 0.3       # mm — intended closing-seat compliance (observable, not a gate)


def t2(parts: dict, hints: dict, axis: dict, roles: dict, modes: list, out_dir: Path,
       base_pid: str, mover_pid: str, pin_pid: str, tag: str, tip_point=None, latch_point=None,
       clearance: float = 0.2, protrusion: float = 3.0, stop_angle_deg: float = float("inf"),
       decision_row: str = "", record: bool = True, plan=None, expected_fail: str = "") -> dict:
    """Run Tier2 for the assigned modes on a COMPILED assembly. `parts` = {pid: Solid} (⑥ output);
    `hints` = {pid: collision prims}; `axis` = {point,dir} mm; `roles` = {pid: base|mover|hardware}.
    `tip_point` = the mover's free-edge point (mm, mover frame) where the follower force acts;
    `latch_point` = the front latch point (release tracking). 5 seeds/mode, ≥4/5 → PASS (spec 6.4);
    seed0 is recorded with the D15 HUD. Guard trio (D-M1-6) on the verdict."""
    out_dir.mkdir(parents=True, exist_ok=True)
    meshdir = out_dir / "assets"
    result = {"decision_row": decision_row or "stage-⑨ t2", "compile_hash": _hash(),
              "tag": tag, "clearance_mm": clearance, "protrusion_mm": protrusion,
              "modes": {}, "shape_assert": {}}
    if expected_fail:
        # the snap_panel EXPECTED_FAIL pattern, one tier down: a legal IR whose VERDICT must fail,
        # kept as a live regression target rather than deleted.
        result["expected_fail"] = expected_fail
    for mode in modes:
        xml, meta = build_mjcf(parts, hints, axis, base_pid, mover_pid, pin_pid, mode, meshdir,
                               roles, tag, tip_point=tip_point, latch_point=latch_point, plan=plan)
        xf = out_dir / f"t2_{tag}_{mode}.xml"; xf.write_text(xml)
        model = mujoco.MjModel.from_xml_path(str(xf))
        gok, checks = g9_gconv(model)
        entry = {"xml": xf.name, "masses_kg": meta["masses_kg"], "g9_gconv": bool(gok),
                 "g9_checks": [(c[0], bool(c[1]), c[2]) for c in checks]}
        if not gok:
            entry["p_hinge"] = {"ran": False, "reason": "G9 (G-CONV) failed — model not coherent"}
            result["modes"][mode] = entry
            continue
        # P-HINGE: N seeds, seed0 recorded (video + plot + csv). Aggregate ≥4/5 (spec 6.4).
        per_seed, series0, frames0 = [], None, None
        for seed in range(N_SEEDS):
            rec = record and seed == 0
            # V-A's stop is the declared joint range; only V-B leans on the geometric open-stop
            sa = stop_angle_deg if mode == "V-B" else float("inf")
            v, series, frames = _run_p_hinge(model, meta, mode, seed, clearance, protrusion, rec,
                                             stop_angle_deg=sa)
            per_seed.append(v)
            if rec:
                series0, frames0 = series, frames
        n_pass = sum(v["passed"] for v in per_seed)
        verdict = n_pass >= SEED_PASS
        entry["p_hinge"] = {"ran": True, "n_seeds": N_SEEDS, "seeds_passed": n_pass,
                            "passed": bool(verdict), "criteria_seed0": per_seed[0]["criteria"],
                            "per_seed": per_seed}
        if series0 is not None:
            _write_media(out_dir, tag, mode, series0, frames0, per_seed[0])
            entry["p_hinge"]["video"] = f"t2_{tag}_{mode}.mp4"
            entry["p_hinge"]["plot"] = f"t2_{tag}_{mode}.png"
        result["modes"][mode] = entry
    # guard trio: decision_row (top) + compile_hash (top) + shape assertion tied to the claim
    result["shape_assert"] = {
        "modes_covered": sorted(result["modes"].keys()) == sorted(modes),
        "g9_all_pass": all(m["g9_gconv"] for m in result["modes"].values()),
        "seeds_per_mode": {m: e.get("p_hinge", {}).get("n_seeds") for m, e in result["modes"].items()}}
    result["verdict"] = all(m["g9_gconv"] and m.get("p_hinge", {}).get("passed", False)
                            for m in result["modes"].values())
    return result


def _classify(theta_deg, stop_angle_deg=float("inf")):
    """Which contact-intent bucket a lid<->box contact at this instant belongs to (D22). The 0–10°
    opening band is where both the closing seat and the latch-release (AR1's 0–10° finding) live;
    within STOP_BAND of the design open-stop angle is the intended end stop. Contact in either band
    is INTENDED; anything else during travel is a defect."""
    if abs(theta_deg) <= SEAT_BAND_DEG:
        return "seat"
    if abs(theta_deg - stop_angle_deg) <= STOP_BAND_DEG:
        return "stop"
    return "travel"


def _run_p_hinge(model, meta, mode, seed=0, clearance=0.2, protrusion=3.0, record=False,
                 stop_angle_deg=float("inf")):
    """Force-driven P-HINGE (§6.3, M0-faithful): a follower force at the mover's free edge ramps it
    open past 95°, releases (coast), then reverses to pull it closed; the lid seats under gravity.
    V-A reads the declared hinge joint angle (pin visual-only); V-B measures the mover's rotation
    relative to the free, welded-at-origin base and tracks pin radial/axial drift in the base frame.
    Penetration is stratified by contact intent (travel defect | seat | pin/bore | latch-release)."""
    import mujoco as mj
    from vb import _hud  # M0 per-frame HUD (D15): the scored values burned into the video

    d = mj.MjData(model)
    rng = np.random.default_rng(seed)
    B = lambda n: mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, n)
    S = lambda n: mj.mj_name2id(model, mj.mjtObj.mjOBJ_SITE, n)
    mover, base, pin = B(meta["mover"]), B(meta["base"]), B(meta["pin"])
    s_tip = S("tip")
    s_axis = S("axis_ref") if mode == "V-B" else -1
    s_pin = S("pin_center") if mode == "V-B" else -1
    hinge_jid = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "hinge") if mode == "V-A" else -1
    cam = mj.mj_name2id(model, mj.mjtObj.mjOBJ_CAMERA, "iso")
    box_diag = float(model.stat.extent)

    mj.mj_forward(model, d)
    # seeds perturb the initial state within the joint's own clearance — probing robustness, not
    # re-tuning (R5). V-A jitters the hinge angle; V-B jitters the free bodies' positions.
    if mode == "V-A":
        d.qpos[model.jnt_qposadr[hinge_jid]] = rng.uniform(0.0, 2e-3)
    else:
        for b in (mover, pin):
            adr = model.jnt_qposadr[model.body_jntadr[b]]
            d.qpos[adr:adr + 3] += rng.uniform(-2e-5, 2e-5, 3)
    mj.mj_forward(model, d)
    R_base0 = d.xmat[base].reshape(3, 3).copy()

    def theta_of(R_base):
        if mode == "V-A":
            return float(d.qpos[model.jnt_qposadr[hinge_jid]])
        R = R_base.T @ d.xmat[mover].reshape(3, 3)     # mover rel base, about the hinge (+X)
        return float(np.arctan2(R[2, 1], R[1, 1]))

    renderer = mj.Renderer(model, 480, 640) if record else None
    ts, th, F_, pr, pa = [], [], [], [], []
    p_travel, p_seat, p_iface, p_stop = [], [], [], []   # stratified penetration (D22)
    pr_op, pr_imp, pi_op, pi_imp = [], [], [], []        # pin drift/interface: operation vs stop-impact
    frames, next_frame = [], 0.0
    diverged, t_open, theta_prev, turns = False, None, 0.0, 0.0
    seated_after_open, bounce_open = False, 0.0

    while d.time < T_END:
        # M0 run_p_hinge follower schedule: ramp 0→F_MAX to open; once the lid is *observed* at the
        # target, ramp F_MAX→−F_MAX over T_REV and then HOLD −F_MAX. The constant-moment-arm follower
        # never loses authority, so held −F_MAX drives the over-centre lid firmly back to closed —
        # no coast (a coast lets gravity fling an over-centre lid round past 180°). The open-side end
        # stop is the declared joint range (V-A) or the designed hinge stop (V-B).
        if t_open is None:
            F = min(F_MAX, F_MAX * d.time / T_RAMP)
        else:
            F = F_MAX * max(-1.0, 1.0 - 2.0 * (d.time - t_open) / T_REV)
        f_world = d.xmat[mover].reshape(3, 3) @ np.array([0.0, 0.0, F])   # follower: lid +Z normal
        d.qfrc_applied[:] = 0.0
        mj.mj_applyFT(model, d, f_world, np.zeros(3), d.site_xpos[s_tip], mover, d.qfrc_applied)
        mj.mj_step(model, d)

        if (not np.all(np.isfinite(d.qpos))
                or (mode == "V-B" and float(np.linalg.norm(d.xpos[pin] - d.xpos[base])) > 10 * box_diag)
                or float(np.abs(d.qvel).max()) > 1e3):
            diverged = True
            break

        R_base = d.xmat[base].reshape(3, 3)
        raw = theta_of(R_base)
        if raw - theta_prev > np.pi: turns -= 2 * np.pi         # unwrap the atan2 branch cut
        elif raw - theta_prev < -np.pi: turns += 2 * np.pi
        theta_prev = raw
        theta = raw + turns
        theta_deg = np.rad2deg(theta)
        if t_open is None and theta >= THETA_TARGET:
            t_open = d.time

        # pin drift in the base frame (V-B only — in V-A the joint carries the pin, visual-only).
        # Stratified like penetration (D22): the retention gate reads drift during OPERATION; the
        # transient jolt as the lid slams the designed open-stop is impact dynamics at an intended
        # contact — an observable, not a retention failure (the seat-impact ruling, applied to the pin).
        radial = axial = 0.0
        in_stop = abs(theta_deg - stop_angle_deg) <= STOP_BAND_DEG
        if mode == "V-B":
            delta = R_base.T @ (d.site_xpos[s_pin] - d.site_xpos[s_axis])
            radial, axial = float(np.hypot(delta[1], delta[2]) * 1e3), float(abs(delta[0]) * 1e3)

        # stratified penetration (D22): pin/bore + seat/latch (0–10°) + open-stop (~107°) are the
        # INTENDED contacts; anything else lid<->box is a travel defect.
        travel = seat = iface = stop = 0.0
        for i in range(d.ncon):
            c = d.contact[i]
            bodies = {model.geom_bodyid[c.geom1], model.geom_bodyid[c.geom2]}
            pv = max(0.0, -float(c.dist))
            if pin in bodies:
                iface = max(iface, pv)
            elif bodies == {base, mover}:
                kind = _classify(theta_deg, stop_angle_deg)
                if kind == "seat":
                    seat = max(seat, pv)
                elif kind == "stop":
                    stop = max(stop, pv)          # intended end-stop contact (observable, D22)
                else:
                    travel = max(travel, pv)

        if t_open is not None and theta_deg <= CLOSED_DEG:
            seated_after_open = True
        if seated_after_open:
            bounce_open = max(bounce_open, theta_deg)

        ts.append(d.time); th.append(theta); F_.append(F)
        pr.append(radial); pa.append(axial)
        p_travel.append(travel * 1e3); p_seat.append(seat * 1e3); p_iface.append(iface * 1e3)
        p_stop.append(stop * 1e3)
        (pr_imp if in_stop else pr_op).append(radial)
        (pi_imp if in_stop else pi_op).append(iface * 1e3)

        if record and d.time >= next_frame:
            renderer.update_scene(d, camera=cam)
            frame = renderer.render()
            pen_now = max(travel, seat, iface) * 1e3
            frame = _hud(frame, [f"T {d.time:4.2f}S", f"ANGLE {theta_deg:5.0f}",
                                 f"PIN R {radial:4.2f} A {axial:4.2f}",
                                 f"PEN {pen_now:4.2f} TRAV {travel*1e3:4.2f}"],
                         colors=[(220, 220, 220), (120, 200, 255), (140, 255, 160),
                                 (255, 150, 90) if travel > 1e-4 else (255, 200, 120)])
            frames.append(frame)
            next_frame += 1.0 / FPS

    if renderer:
        renderer.close()

    tha = np.array(th)
    n_tail = max(1, int(0.1 / model.opt.timestep))
    theta_max = float(np.rad2deg(tha.max())) if len(tha) else 0.0
    theta_final = float(np.rad2deg(np.abs(tha[-n_tail:]).mean())) if len(tha) else 180.0
    pin_axial = float(max(pa)) if pa else 999.0
    # retention gate = drift/interface during OPERATION (outside the stop-impact band); the impact
    # peaks are reported as observables (D22 — impact severity at an intended contact is not a gate).
    pin_radial = float(max(pr_op)) if pr_op else (float(max(pr)) if pr else 999.0)
    pen_iface = float(max(pi_op)) if pi_op else (float(max(p_iface)) if p_iface else 0.0)
    pin_radial_impact = float(max(pr_imp)) if pr_imp else 0.0
    pen_iface_impact = float(max(pi_imp)) if pi_imp else 0.0
    pen_travel = float(max(p_travel)) if p_travel else 0.0
    pen_seat = float(max(p_seat)) if p_seat else 0.0
    pen_stop = float(max(p_stop)) if p_stop else 0.0

    # criteria — stratified (D22). Travel interference gates; seat compliance is an observable.
    crit = {
        "theta_max >= 90 deg": {"value": round(theta_max, 2), "threshold": 90.0,
                                "pass": bool(theta_max >= 90.0 and not diverged)},
        "travel interference (non-intended) <= 0.2 mm": {
            "value": round(pen_travel, 4), "threshold": TRAVEL_PEN_LIMIT,
            "pass": bool(pen_travel <= TRAVEL_PEN_LIMIT and not diverged)},
        "settles closed: theta_final <= 5 deg, no bounce-open": {
            "value": round(max(theta_final, bounce_open), 2), "threshold": 5.0,
            "pass": bool(theta_final <= 5.0 and bounce_open <= 5.0 and not diverged)},
    }
    if mode == "V-B":
        crit["pin retention: radial <= clearance+0.1"] = {
            "value": round(pin_radial, 4), "threshold": round(clearance + 0.1, 3),
            "pass": bool(pin_radial <= clearance + 0.1 and not diverged)}
        crit["pin retention: axial <= protrusion"] = {
            "value": round(pin_axial, 4), "threshold": round(protrusion, 3),
            "pass": bool(pin_axial <= protrusion and not diverged)}
        crit["pin/bore interface <= clearance"] = {
            "value": round(pen_iface, 4), "threshold": round(clearance, 3),
            "pass": bool(pen_iface <= clearance and not diverged)}

    v = {"ran": True, "mode": mode, "seed": seed, "diverged": diverged,
         "theta_max_deg": theta_max, "theta_final_deg": theta_final,
         "pin_radial_max_mm": pin_radial, "pin_axial_max_mm": pin_axial,
         "pen_travel_mm": pen_travel, "pen_seat_mm": pen_seat, "pen_interface_mm": pen_iface,
         "pen_stop_mm": pen_stop, "bounce_open_deg": float(bounce_open),
         "pin_radial_impact_mm": pin_radial_impact, "pen_interface_impact_mm": pen_iface_impact,
         "criteria": crit, "passed": bool(all(c["pass"] for c in crit.values()))}
    series = {"t": ts, "theta_deg": list(np.rad2deg(tha)), "force_N": F_,
              "pin_radial_mm": pr, "pin_axial_mm": pa, "pen_travel_mm": p_travel,
              "pen_seat_mm": p_seat, "pen_interface_mm": p_iface, "pen_stop_mm": p_stop}
    return v, series, frames


def _write_media(out_dir, tag, mode, series, frames, v):
    """seed-0 artefacts: the HUD video (D15 — the scored run, provably), the θ/F/pen plot, and a
    csv of the exact scored series."""
    import imageio.v2 as imageio
    if frames:
        imageio.mimsave(out_dir / f"t2_{tag}_{mode}.mp4", frames, fps=FPS)
    _plot(series, v, out_dir / f"t2_{tag}_{mode}.png", f"P-HINGE / {tag} / {mode}")
    rows = ["t,theta_deg,force_N,pen_travel_mm,pen_seat_mm,pen_interface_mm"]
    for i in range(len(series["t"])):
        rows.append(f"{series['t'][i]:.5f},{series['theta_deg'][i]:.4f},{series['force_N'][i]:.5f},"
                    f"{series['pen_travel_mm'][i]:.6f},{series['pen_seat_mm'][i]:.6f},"
                    f"{series['pen_interface_mm'][i]:.6f}")
    (out_dir / f"t2_{tag}_{mode}.csv").write_text("\n".join(rows))


def _plot(series, v, path, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    t = series["t"]
    fig, axes = plt.subplots(3, 1, figsize=(8, 7), sharex=True,
                             gridspec_kw={"height_ratios": [3, 1, 1]})
    ax = axes[0]
    ax.plot(t, series["theta_deg"], lw=2, color="#2b6cb0")
    ax.axhline(90, ls="--", c="#c53030", lw=1)
    ax.axhspan(90, max(120, max(series["theta_deg"] + [95]) + 5), color="#c6f6d5", alpha=.5)
    ax.axhspan(-5, 5, color="#bee3f8", alpha=.6)
    badge = "PASS" if v["passed"] else "FAIL"
    ax.set_ylabel("hinge angle θ (deg)")
    ax.set_title(f"{title}   [{badge}]  θmax={v['theta_max_deg']:.1f}°, "
                 f"θfinal={v['theta_final_deg']:.1f}°, travel-pen={v['pen_travel_mm']:.3f} mm",
                 color="#22543d" if v["passed"] else "#742a2a", fontsize=10)
    ax.grid(alpha=.25)
    ax = axes[1]
    ax.plot(t, series["force_N"], lw=1.5, color="#805ad5"); ax.axhline(0, c="k", lw=.5)
    ax.set_ylabel("F (N)"); ax.grid(alpha=.25)
    ax = axes[2]
    ax.plot(t, series["pen_travel_mm"], lw=1.5, color="#dd6b20", label="travel (defect)")
    ax.plot(t, series["pen_seat_mm"], lw=1.2, color="#38a169", label="seat (intended)")
    ax.plot(t, series["pen_interface_mm"], lw=1.2, color="#3182ce", label="pin/bore (intended)")
    if any(series.get("pen_stop_mm", [])):
        ax.plot(t, series["pen_stop_mm"], lw=1.2, color="#9f7aea", label="open-stop (intended)")
    ax.axhline(0.2, ls="--", c="#c53030", lw=1)
    ax.set_ylabel("pen (mm)"); ax.set_xlabel("t (s)"); ax.legend(fontsize=7, loc="upper right")
    ax.grid(alpha=.25)
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)
