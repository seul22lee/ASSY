"""P-SLIDE (§6.3) on the compiled slide_fixture — V-A (declared prismatic joint) + V-B (contact-only).

Actuate: an axial force ramp on the carriage along the travel axis, out to the stroke then back.
Observe: s(t) (displacement along the axis), off-axis rotation (roll/pitch/yaw of the carriage),
derail (carriage leaves the rail). Judge (§6.3): s_max ≥ stroke, off-axis ≤ 3°, no derail,
back-drift ≤ 5 mm.

V-A is REQUIRED (a declared slide joint carries the motion). V-B is the TARGET — the T-rail geometry
alone must produce AND retain the slide DoF. Per the R2b precedent, if V-B jams on the frozen preset
we RECORD it and move on; nothing is tuned.

Run:  ./bin/py tasks/run_m10_slide.py [out_dir]
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "m0"))

import imageio.v2 as imageio
import mujoco as mj
import numpy as np

from knowledge.cards.base import CARD_REGISTRY
from ontology.validators import validate_all
from pipeline.compile_assembly import compile_assembly
from tasks.build_goldens import slide_fixture
from verify.t2_physics.mjcf import build_mjcf
from verify.t2_physics.runner import _hash, g9_gconv

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "m0"))
from step2mjcf import DENSITY, MM  # PETG density + mm→m (R5-frozen)  # noqa: E402
from knowledge.materials import PETG  # noqa: E402

G = 9.81


def _slide_friction_N(mover_part) -> float:
    """The V-A slide joint's Coulomb friction, PHYSICALLY SOURCED: μ·N = PETG.mu_friction × the
    carriage weight (mass·g). This is the SAME μ the frozen contact preset applies to V-B, so V-A's
    declared joint feels the friction V-B's contacts do — not an invented value chosen to pass a
    gate. mass = volume·density (the mesh mass MuJoCo will compute)."""
    vol_m3 = float(mover_part.volume) * (MM ** 3)
    mass = vol_m3 * DENSITY
    return PETG.mu_friction * mass * G

N_SEEDS, SEED_PASS, FPS = 5, 4, 60
F_MAX, T_RAMP, T_SETTLE = 0.3, 2.0, 1.5   # gentle axial ramp (avoid slamming the soft end-stop)
T_HOLD = T_REV = 0.0
T_END = T_RAMP + T_SETTLE
OFFAXIS_LIMIT, BACKDRIFT_LIMIT = 3.0, 5.0                         # deg, mm (§6.3)


def _hints(plan, ca):
    e1 = plan.element("E1")
    prims = CARD_REGISTRY["slide_rail"].collision_hint(e1, float(e1.params["stroke"]))
    owner_pid = {"rail": "P1", "carriage": "P2"}
    hints = {"P1": [], "P2": []}
    for p in prims:
        hints[owner_pid[p["owner"]]].append(p)
    return hints


def _offaxis_deg(R0, R):
    """Total off-axis rotation of the carriage relative to its start pose, in degrees."""
    Rrel = R0.T @ R
    ang = math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(Rrel) - 1) / 2))))
    return ang


def run_slide(model, meta, mode, seed=0, stroke=60.0, record=False, settle_s=0.0, label=False):
    rng = np.random.default_rng(seed)
    d = mj.MjData(model)
    mover = mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, "P2")
    base = mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, "P1")
    ax = np.array(meta["axis_m"]["dir"], float); ax /= np.linalg.norm(ax)
    slide_jid = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "slide") if mode == "V-A" else -1
    cam = mj.mj_name2id(model, mj.mjtObj.mjOBJ_CAMERA, "iso")
    box_diag = float(model.stat.extent)

    mj.mj_forward(model, d)
    # seeds perturb within the sliding clearance — robustness, not re-tuning (R5)
    if mode == "V-A":
        d.qpos[model.jnt_qposadr[slide_jid]] = rng.uniform(0.0, 2e-4)
    else:
        adr = model.jnt_qposadr[model.body_jntadr[mover]]
        d.qpos[adr:adr + 3] += rng.uniform(-2e-5, 2e-5, 3)
    mj.mj_forward(model, d)
    # optional settle-in: a drop-in assembly seats onto its rail before it is used. This is a
    # physically honest initial condition, not preset tuning — the drawer rests on the rails first.
    for _ in range(int(settle_s / model.opt.timestep)):
        mj.mj_step(model, d)
    x0 = float(d.xpos[mover] @ ax)
    R0 = d.xmat[mover].reshape(3, 3).copy()
    grip = d.xpos[mover].copy()

    # coverage (G-H): watch EVERY non-base body, not only the actuated mover. A part that falls off
    # the assembly must trip a gate even if it is not the one being pushed. base is welded (D23).
    watched = [b for b in range(1, model.nbody)
               if mj.mj_id2name(model, mj.mjtObj.mjOBJ_BODY, b) != "P1"]
    start_pos = {b: d.xpos[b].copy() for b in watched}

    renderer = mj.Renderer(model, 480, 640) if record else None
    label_opt = mj.MjvOption()
    if label:
        label_opt.label = mj.mjtLabel.mjLABEL_BODY
    ts, s_mm, off_deg, F_, frames = [], [], [], [], []
    next_frame, diverged, derailed, part_lost = 0.0, False, False, False
    s_target = stroke * 1e-3
    t_open = None

    while d.time < T_END:
        s_now = (float(d.xpos[mover] @ ax) - x0)
        if t_open is None and s_now >= s_target:
            t_open = d.time
        # §6.3: ramp an axial force until the drawer reaches the stroke, then RELEASE (F=0) and
        # watch it — "back-drift after stop" is how far a released drawer slides back on its own.
        F = min(F_MAX, F_MAX * d.time / T_RAMP) if t_open is None else 0.0
        d.qfrc_applied[:] = 0.0
        mj.mj_applyFT(model, d, ax * F, np.zeros(3), d.xpos[mover], mover, d.qfrc_applied)
        mj.mj_step(model, d)

        if (not np.all(np.isfinite(d.qpos))
                or (mode == "V-B" and np.linalg.norm(d.xpos[mover] - d.xpos[base]) > 10 * box_diag)
                or float(np.abs(d.qvel).max()) > 1e3):
            diverged = True
            break

        R = d.xmat[mover].reshape(3, 3)
        s = (float(d.xpos[mover] @ ax) - x0) * 1e3
        oa = _offaxis_deg(R0, R)
        # derail: the carriage lifts off the rail (Z) or slides off sideways (Y) beyond clearance+
        off_axis_disp = d.xpos[mover] - grip - ax * ((d.xpos[mover] - grip) @ ax)
        if mode == "V-B" and float(np.linalg.norm(off_axis_disp)) * 1e3 > 6.0:
            derailed = True
        # all-parts-retained: a watched body must not drop, nor stray off the travel axis, beyond a
        # generous bound (it may travel the stroke ALONG the axis, but not fall or wander off it).
        for b in watched:
            dv = d.xpos[b] - start_pos[b]
            off = dv - ax * (dv @ ax)                       # component off the travel axis
            if float(np.linalg.norm(off)) * 1e3 > 15.0 or dv[2] * 1e3 < -15.0:
                part_lost = True
        ts.append(d.time); s_mm.append(s); off_deg.append(oa); F_.append(F)

        if record and d.time >= next_frame:
            renderer.update_scene(d, camera=cam, scene_option=label_opt)
            frames.append(renderer.render())
            next_frame += 1.0 / FPS
    if renderer:
        renderer.close()

    s_arr = np.array(s_mm) if s_mm else np.array([0.0])
    n_tail = max(1, int(0.15 / model.opt.timestep))
    s_max = float(s_arr.max())
    s_settled = float(s_arr[-n_tail:].mean())
    back_drift = float(max(0.0, s_max - s_settled))   # §6.3: how far it slid back after release
    off_max = float(max(off_deg)) if off_deg else 999.0
    crit = {
        "reaches_stroke (s_max >= stroke)": {"value": round(s_max, 2), "threshold": stroke,
                                             "pass": bool(s_max >= stroke and not diverged)},
        "tracks_straight (off-axis <= 3 deg)": {"value": round(off_max, 3),
                                                "threshold": OFFAXIS_LIMIT,
                                                "pass": bool(off_max <= OFFAXIS_LIMIT and not diverged)},
        "no_derail": {"value": derailed, "threshold": False,
                      "pass": bool(not derailed and not diverged)},
        "all_parts_retained": {"value": part_lost, "threshold": False,
                               "pass": bool(not part_lost and not diverged)},
        "back_drift after stop <= 5 mm": {"value": round(back_drift, 2), "threshold": BACKDRIFT_LIMIT,
                               "pass": bool(back_drift <= BACKDRIFT_LIMIT and not diverged)},
    }
    v = {"ran": True, "mode": mode, "seed": seed, "diverged": diverged, "derailed": derailed,
         "part_lost": part_lost, "n_bodies_watched": len(watched),
         "s_max_mm": s_max, "s_settled_mm": s_settled, "back_drift_mm": back_drift,
         "offaxis_max_deg": off_max,
         "criteria": crit, "passed": bool(all(c["pass"] for c in crit.values()))}
    series = {"t": ts, "s_mm": s_mm, "offaxis_deg": off_deg, "force_N": F_}
    return v, series, frames


def _plot(series, v, path, title, stroke):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    t = series["t"]
    fig, axes = plt.subplots(2, 1, figsize=(8, 6), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    ax = axes[0]
    ax.plot(t, series["s_mm"], lw=2, color="#2b6cb0", label="s(t) displacement")
    ax.axhline(stroke, ls="--", c="#c53030", lw=1.2)
    ax.text(t[-1] if t else 1, stroke + 1, f" stroke = {stroke:g} mm", color="#c53030",
            ha="right", fontsize=9)
    ax.axhspan(stroke, max(stroke * 1.15, max(series["s_mm"] + [stroke]) + 2), color="#c6f6d5", alpha=.4)
    badge = "PASS" if v["passed"] else "FAIL"
    ax.set_ylabel("s (mm) along travel axis")
    ax.set_title(f"{title}   [{badge}]  s_max={v['s_max_mm']:.1f} mm, off-axis={v['offaxis_max_deg']:.2f}°",
                 color="#22543d" if v["passed"] else "#742a2a", fontsize=10)
    ax.legend(fontsize=8); ax.grid(alpha=.25)
    ax = axes[1]
    ax.plot(t, series["offaxis_deg"], lw=1.5, color="#dd6b20", label="off-axis (deg)")
    ax.axhline(OFFAXIS_LIMIT, ls="--", c="#c53030", lw=1)
    ax.set_ylabel("off-axis (°)"); ax.set_xlabel("t (s)"); ax.grid(alpha=.25); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("verify/t2_physics/out_slide")
    out.mkdir(parents=True, exist_ok=True)
    plan = slide_fixture()
    e1 = plan.element("E1")
    e1.params = CARD_REGISTRY["slide_rail"].resolve_params(plan, e1)
    stroke = float(e1.params["stroke"])
    assert not validate_all(plan), "fixture must be validator-clean"
    ca = compile_assembly(plan)
    hints = _hints(plan, ca)
    roles = {"P1": "base", "P2": "mover"}
    parts = {"P1": ca.parts["P1"], "P2": ca.parts["P2"]}

    result = {"decision_row": "D-track P-SLIDE on compiled slide_fixture", "compile_hash": _hash(),
              "stroke_mm": stroke, "modes": {}}
    for mode in ("V-A", "V-B"):
        axis = dict(ca.axes["E1"]); axis["stroke_mm"] = stroke
        fric = _slide_friction_N(ca.parts["P2"])
        xml, meta = build_mjcf(parts, hints, axis, "P1", "P2", "P2", mode,
                               out / "assets", roles, "slide", plan=plan, joint_kind="slide",
                               slide_friction_N=fric)
        xf = out / f"t2_slide_{mode}.xml"; xf.write_text(xml)
        model = mj.MjModel.from_xml_path(str(xf))
        gok, checks = g9_gconv(model)
        entry = {"xml": xf.name, "g9_gconv": bool(gok),
                 "g9_checks": [(c[0], bool(c[1]), c[2]) for c in checks]}
        if not gok:
            # G-CONV (M0\'s coherence gate) tripped — for the slide this is the settling transient
            # of a drop-in assembly meeting the stiff frozen preset (peak-v on a sub-mm drop), NOT a
            # jam. Per the R2b precedent: RECORD, do not tune the preset. But still characterise the
            # geometry with an OBSERVED (settle-first, NOT gated) slide, so the record says what the
            # T-rail actually does, not merely "G-CONV failed".
            ov, oser, ofr = run_slide(model, meta, mode, 0, stroke, record=True, settle_s=0.35, label=True)
            entry["p_slide"] = {"ran": False, "reason": "G-CONV settling transient (frozen preset; "
                                "recorded, not tuned)",
                                "observed_not_gated": {"criteria": ov["criteria"],
                                                       "s_max_mm": ov["s_max_mm"],
                                                       "offaxis_max_deg": ov["offaxis_max_deg"],
                                                       "derailed": ov["derailed"],
                                                       "passed_if_gated": ov["passed"]}}
            if oser["t"]:
                _plot(oser, ov, out / f"t2_slide_{mode}.png", f"P-SLIDE / {mode} (OBSERVED, not gated)", stroke)
                if ofr:
                    imageio.mimsave(out / f"t2_slide_{mode}.mp4", ofr, fps=FPS)
            result["modes"][mode] = entry
            print(f"{mode}: G-CONV FAILED (settling transient) — OBSERVED slide: "
                  f"s_max={ov['s_max_mm']:.1f}mm off-axis={ov['offaxis_max_deg']:.2f}° "
                  f"derail={ov['derailed']} would-gate={ov['passed']}"); continue
        per_seed, series0, frames0, v0 = [], None, None, None
        for seed in range(N_SEEDS):
            rec = seed == 0
            v, series, frames = run_slide(model, meta, mode, seed, stroke, record=rec, label=rec)
            per_seed.append(v)
            if rec:
                series0, frames0, v0 = series, frames, v
        n_pass = sum(v["passed"] for v in per_seed)
        entry["p_slide"] = {"ran": True, "n_seeds": N_SEEDS, "seeds_passed": n_pass,
                            "passed": bool(n_pass >= SEED_PASS),
                            "criteria_seed0": per_seed[0]["criteria"], "per_seed": per_seed}
        if series0:
            _plot(series0, v0, out / f"t2_slide_{mode}.png", f"P-SLIDE / {mode}", stroke)
            if frames0:
                imageio.mimsave(out / f"t2_slide_{mode}.mp4", frames0, fps=FPS)
            entry["p_slide"]["video"] = f"t2_slide_{mode}.mp4"
            entry["p_slide"]["plot"] = f"t2_slide_{mode}.png"
        result["modes"][mode] = entry
        print(f"\n=== {mode} ===  G-CONV ok   seeds {n_pass}/{N_SEEDS} => "
              f"{'PASS' if n_pass >= SEED_PASS else 'FAIL'}")
        for name, c in per_seed[0]["criteria"].items():
            print(f"   {'ok  ' if c['pass'] else 'FAIL'} {name:<40s} {c['value']} (<= {c['threshold']})")

    result["shape_assert"] = {"modes_covered": sorted(result["modes"]) == ["V-A", "V-B"]}
    result["verdict_VA"] = result["modes"].get("V-A", {}).get("p_slide", {}).get("passed", False)
    result["verdict_VB"] = result["modes"].get("V-B", {}).get("p_slide", {}).get("passed", False)
    (out / "t2_slide_verdict.json").write_text(json.dumps(result, indent=2))
    print(f"\nV-A pass: {result['verdict_VA']}   V-B pass: {result['verdict_VB']}")
    print("wrote", out / "t2_slide_verdict.json")


if __name__ == "__main__":
    main()
