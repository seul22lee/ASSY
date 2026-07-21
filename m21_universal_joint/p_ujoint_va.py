"""P-UJOINT (MECHSYNTH §6.3) on the compiled ujoint_fixture — V-A (m21 D-track).

WHAT V-A VERIFIES, and why it is non-tautological BY CONSTRUCTION. A Cardan joint transmits rotation
across two axes intersecting at a bend β, through a rigid cross. Its output speed PULSATES twice per
rev (cos β … 1/cos β) — an EMERGENT property of the geometry, not a declared ratio. The rig models
that geometry honestly (NO polycoef=cos β constant, which would declare the average and erase the
physics): a serial chain input(hinge A) → cross(hinge pin1) → output(hinge pin2), the loop closed by
pinning the output-shaft TIP to a world anchor on axis B (one connect; nv=3, the connect nets −2 DoF,
leaving the single Cardan mobility). The fluctuation then EMERGES and is measured.

THREE parts (the m21 brief):
  (a) TRANSMISSION — the output completes the revolutions the input drives; the MEAN ratio over a rev
      is 1:1 to ≤0.1% (it lags then leads, but nets 1:1).
  (b) FLUCTUATION MATCH (the discovery criterion) — measured ω_out/ω_in over one rev OVERLAYS the
      Cardan formula cos β/(1−sin²β sin²θ) at the fixture's β, amplitude AND phase (the phase φ0 is the
      geometric location of the min-speed point, PREDICTED from the assembly, not fit). The element's
      speed pulsation, verified as physics.
  (c) DISCRIMINATION — β=0 (straight) flattens the ratio to 1.0: the pulsation appears with the angle
      and only with the angle. Recorded as discrimination_probe.

CLOCK dt=1e-4 (D-M19-2, contact-free rig; R5 contact preset does not apply). 5 seeds; guard trio +
G-CONV + all_parts_retained. VIDEO per the standing rule (D-M20 REVIEW): markers on input/cross/output,
side view perpendicular to the bend plane, full criterion window; a β=0 clip for the contrast.

  export MUJOCO_GL=egl ; ./bin/py m21_universal_joint/p_ujoint_va.py [out_dir]
"""

from __future__ import annotations

import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "m0"))

import imageio.v2 as imageio  # noqa: E402
import mujoco as mj  # noqa: E402
import numpy as np  # noqa: E402

from knowledge.cards.base import CARD_REGISTRY  # noqa: E402
from knowledge.cards.universal_joint import ujoint_dims, ujoint_kinematics, ujoint_ratio_at  # noqa: E402
from ontology.validators import validate_all  # noqa: E402
from pipeline.compile_assembly import compile_assembly  # noqa: E402
from tasks.build_goldens import ujoint_fixture  # noqa: E402
from verify.t2_physics.runner import _hash, g9_gconv  # noqa: E402

from step2mjcf import MM, SOLIMP, SOLREF  # FROZEN preset (R5, contact only)  # noqa: E402

VA_DT = 1e-4
ARMATURE = 1e-5
JOINT_DAMPING = 1e-5
CAPTURE_HZ = 240
OUT_FPS = 60
N_SEEDS, SEED_PASS = 5, 4
OMEGA = 8.0           # rad/s input drive (moderate — a clean fluctuation sample over the rev)
RAMP = 0.15
KV = 0.5
N_REV = 3.0
MEAN_TOL = 0.001      # ≤0.1% mean-ratio (transmission gate)
FLUCT_TOL = 0.02      # ≤2% max|measured − formula| ratio (fluctuation overlay gate)
L_OUT = 0.040         # output shaft length (m); its tip is pinned to axis B (the loop closure)


def _v(a):
    return " ".join(f"{float(x):.9f}" for x in a)


def build_va_mjcf(plan, meshdir: Path, beta_deg, markers=True):
    """Serial-chain Cardan (joint centre at world origin): input(hinge Z) → cross(hinge pin1=X) →
    output(hinge pin2=Y), loop-closed by a connect pinning the output tip to a world anchor on axis B.
    beta_deg is the bend (the fixture's β, or 0 for the discrimination clip)."""
    meshdir.mkdir(parents=True, exist_ok=True)
    e1 = plan.element("E1")
    g = ujoint_dims(e1.params)
    b = math.radians(beta_deg)
    B = np.array([math.sin(b), 0.0, math.cos(b)])
    tip = L_OUT * B
    br = g.bore_d / 2 * MM          # shaft radius (m)
    yr = g.yoke_d / 2 * MM          # yoke radius (m)
    Hs = 0.026                      # input shaft length below the joint (m)

    root = ET.Element("mujoco", model="t2_ujoint_VA")
    ET.SubElement(root, "compiler", angle="radian", autolimits="true")
    ET.SubElement(root, "option", timestep=f"{VA_DT}", integrator="implicitfast",
                  cone="elliptic", impratio="10", gravity="0 0 0")
    vis = ET.SubElement(root, "visual")
    ET.SubElement(vis, "headlight", ambient="0.5 0.5 0.5", diffuse="0.6 0.6 0.6", specular="0.2 0.2 0.2")
    ET.SubElement(vis, "global", offwidth="1280", offheight="960")
    dflt = ET.SubElement(root, "default")
    ET.SubElement(dflt, "geom", density="0", contype="0", conaffinity="0", group="2")
    asset = ET.SubElement(root, "asset")
    for name, rgba in [("base", "0.35 0.65 0.85 1"), ("input", "0.95 0.62 0.25 1"),
                       ("cross", "0.75 0.75 0.80 1"), ("output", "0.55 0.78 0.55 1"),
                       ("mk_in", "0.90 0.10 0.10 1"), ("mk_cross", "0.10 0.85 0.90 1"),
                       ("mk_out", "0.85 0.10 0.80 1")]:
        ET.SubElement(asset, "material", name=name, rgba=rgba)
    world = ET.SubElement(root, "worldbody")
    ET.SubElement(world, "light", pos="0.1 -0.2 0.3", dir="-0.2 0.4 -1", directional="true",
                  diffuse="0.5 0.5 0.5")
    # SIDE camera: look along +Y (perpendicular to the XZ bend plane) so β AND both marker sweeps show
    ET.SubElement(world, "camera", name="side", pos="0 -0.16 0.0", xyaxes="1 0 0 0 0 1")
    # static base plate (cosmetic; the joint centre is the world origin)
    ET.SubElement(world, "geom", name="base", type="box", pos=f"0 0 {-Hs-0.004}",
                  size="0.022 0.022 0.002", material="base")
    ET.SubElement(world, "site", name="wtip", pos=_v(tip), size="0.0012")

    def _marker(parent, name, mat, pos, size):
        if markers:
            ET.SubElement(parent, "geom", name=name, type="box", pos=_v(pos), size=_v(size), material=mat)

    binp = ET.SubElement(world, "body", name="input", pos="0 0 0")
    ET.SubElement(binp, "joint", name="jin", type="hinge", axis="0 0 1", pos="0 0 0",
                  damping=f"{JOINT_DAMPING}", armature=f"{ARMATURE}")
    ET.SubElement(binp, "geom", name="in_shaft", type="cylinder", fromto=f"0 0 {-Hs} 0 0 0",
                  size=f"{br}", material="input", mass="0.01")
    ET.SubElement(binp, "geom", name="in_yoke", type="cylinder", fromto="0 0 -0.003 0 0 0.014",
                  size=f"{yr}", material="input", mass="0.006")
    _marker(binp, "mk_in", "mk_in", (yr + 0.002, 0, 0.006), (0.003, 0.001, 0.004))

    bcross = ET.SubElement(binp, "body", name="cross", pos="0 0 0")
    ET.SubElement(bcross, "joint", name="pin1", type="hinge", axis="1 0 0", pos="0 0 0",
                  damping=f"{JOINT_DAMPING}", armature=f"{ARMATURE}")
    ET.SubElement(bcross, "geom", name="cross_x", type="box", size="0.012 0.002 0.002",
                  material="cross", mass="0.001")
    ET.SubElement(bcross, "geom", name="cross_y", type="box", size="0.002 0.012 0.002",
                  material="cross", mass="0.001")
    _marker(bcross, "mk_cross", "mk_cross", (0, 0.013, 0), (0.0015, 0.003, 0.0015))

    bout = ET.SubElement(bcross, "body", name="output", pos="0 0 0")
    ET.SubElement(bout, "joint", name="pin2", type="hinge", axis="0 1 0", pos="0 0 0",
                  damping=f"{JOINT_DAMPING}", armature=f"{ARMATURE}")
    ET.SubElement(bout, "geom", name="out_shaft", type="cylinder", fromto=f"0 0 0 {tip[0]} {tip[1]} {tip[2]}",
                  size=f"{br}", material="output", mass="0.01")
    ET.SubElement(bout, "site", name="otip", pos=_v(tip), size="0.0012")
    ET.SubElement(bout, "site", name="omark", pos="0 0.012 0", size="0.0012")
    # output marker: a radial tab perpendicular to B (in the ⊥B plane, along +Y at assembly)
    _marker(bout, "mk_out", "mk_out", (0, 0.013, 0.020 * math.sin(b) + 0.0), (0.0015, 0.004, 0.0015))

    eq = ET.SubElement(root, "equality")
    ET.SubElement(eq, "connect", body1="output", body2="world", anchor=_v(tip),
                  solref="0.0002 1", solimp="0.99 0.999 1e-4 0.5 2")
    act = ET.SubElement(root, "actuator")
    ET.SubElement(act, "velocity", name="drive", joint="jin", kv=f"{KV}")

    xml = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
    e1par = ujoint_kinematics(g)
    meta = {"beta_deg": beta_deg, "bore_d_mm": g.bore_d, "yoke_d_mm": g.yoke_d,
            "vel_ratio_min": round(math.cos(b), 4), "vel_ratio_max": round(1 / math.cos(b), 4) if b else 1.0,
            "fluctuation_pct": e1par["fluctuation_pct"], "n_rev": N_REV, "L_out_m": L_OUT,
            "B": list(B)}
    return xml, meta


def _theta_out(sp, e1, e2):
    return math.atan2(float(np.dot(sp, e2)), float(np.dot(sp, e1)))


def run_va(model, meta, seed=0, record=False):
    """Drive the input N_REV; measure θ_in (jin) and θ_out (omark angle in the ⊥B plane). Compute the
    mean ratio + the fluctuation overlay residual vs the Cardan formula. Returns (verdict, series, frames)."""
    d = mj.MjData(model)
    rng = np.random.default_rng(seed)
    ji = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "jin")
    iia = model.jnt_qposadr[ji]; idi = model.jnt_dofadr[ji]
    a = mj.mj_name2id(model, mj.mjtObj.mjOBJ_ACTUATOR, "drive")
    sid = mj.mj_name2id(model, mj.mjtObj.mjOBJ_SITE, "omark")
    cam = mj.mj_name2id(model, mj.mjtObj.mjOBJ_CAMERA, "side")
    b = math.radians(meta["beta_deg"]); B = np.array(meta["B"])
    e1 = np.array([0.0, 1.0, 0.0]); e2 = np.cross(B, e1)
    ne = np.linalg.norm(e2); e2 = e2 / ne if ne > 1e-9 else np.array([1.0, 0.0, 0.0])

    d.qpos[iia] += rng.uniform(-1e-3, 1e-3)
    mj.mj_forward(model, d)
    r0 = float(np.max(np.abs(d.efc_pos[:d.nefc]))) if d.nefc > 0 else 0.0
    renderer = mj.Renderer(model, 480, 640) if record else None

    theta_target = meta["n_rev"] * 2 * math.pi
    thi0 = float(d.qpos[iia]); tho0 = _theta_out(d.site_xpos[sid], e1, e2)
    ts, thi, tho, res, frames, nextf = [], [], [], [], [], 0.0
    diverged = False
    t_wall = theta_target / OMEGA + 6 * RAMP + 2.0
    while True:
        d.ctrl[0] = min(OMEGA, OMEGA * d.time / RAMP)
        mj.mj_step(model, d)
        if not np.all(np.isfinite(d.qpos)) or abs(d.qvel[idi]) > 2000:
            diverged = True; break
        ai = float(d.qpos[iia]) - thi0
        ao = _theta_out(d.site_xpos[sid], e1, e2)
        ts.append(d.time); thi.append(ai); tho.append(ao)
        res.append(float(np.max(np.abs(d.efc_pos[:d.nefc]))) if d.nefc > 0 else 0.0)
        if record and d.time >= nextf:
            renderer.update_scene(d, camera=cam)
            frames.append((renderer.render(), d.time, ai))
            nextf += 1.0 / CAPTURE_HZ
        if ai >= theta_target or d.time > t_wall:
            break
    if renderer:
        renderer.close()

    thi = np.array(thi); tho = np.unwrap(np.array(tho)); tho = tho - (tho[0] - 0.0)
    max_res = float(np.max(res)) if res else 0.0
    revs_in = thi[-1] / (2 * math.pi) if len(thi) else 0.0
    reaches = thi[-1] >= theta_target - 0.05 if len(thi) else False

    # take ONE clean revolution (skip the ramp): θ_in ∈ [0.5, 0.5+2π]
    mask = (thi > 0.5) & (thi < 0.5 + 2 * math.pi)
    T, O = thi[mask], tho[mask]
    mean_ratio = (O[-1] - O[0]) / (T[-1] - T[0]) if len(T) > 5 else 0.0
    mean_residual = abs(mean_ratio - 1.0)
    # velocity ratio measured vs Cardan formula. phase φ0 = the θ_in of the measured minimum (the
    # geometric min-speed point); PREDICTED to be 0 or π/2 — reported, not free-fit.
    w = np.gradient(O, T) if len(T) > 5 else np.array([1.0])
    # φ0 is PREDICTED from the assembly geometry, NOT fit: the input yoke pin is along X (in the bend
    # plane at θ_in=0), so the min-speed point (pin ⊥ plane) is at θ_in = π/2. Overlay uses this fixed
    # constant; the measured min location is reported separately to VERIFY the phase.
    phi0_geom = math.pi / 2 if meta["beta_deg"] > 0 else 0.0
    formula = np.array([ujoint_ratio_at(t - phi0_geom, b) for t in T])
    fluct_residual = float(np.max(np.abs(w - formula))) if len(T) > 5 else 0.0
    phi0_meas = float(T[int(np.argmin(w))] % math.pi) if (meta["beta_deg"] > 0 and len(T) > 5) else 0.0
    phase_err = abs(phi0_meas - phi0_geom); phase_err = min(phase_err, math.pi - phase_err)
    meas_band = [float(w.min()), float(w.max())]
    all_retained = bool(np.all(np.isfinite(d.qpos)))

    crit = {
        "reaches_drive (input ≥ N_rev)": {"value": round(revs_in, 3), "threshold": meta["n_rev"],
                                          "pass": bool(reaches and not diverged)},
        "transmits_mean_1to1 (|mean−1| ≤ 0.1%)": {"value": round(mean_residual, 5), "threshold": MEAN_TOL,
                                                  "pass": bool(mean_residual <= MEAN_TOL and not diverged)},
        "cardan_fluctuation_matches (max|meas−formula| ≤ 2%)": {"value": round(fluct_residual, 4),
                                                               "threshold": FLUCT_TOL,
                                                               "pass": bool(fluct_residual <= FLUCT_TOL and not diverged)},
        "converged (no blow-up)": {"value": diverged, "threshold": False, "pass": bool(not diverged)},
        "all_parts_retained": {"value": all_retained, "threshold": True, "pass": all_retained},
    }
    v = {"ran": True, "mode": "V-A", "seed": seed, "diverged": diverged, "beta_deg": meta["beta_deg"],
         "revs_in": round(revs_in, 3), "mean_ratio": round(mean_ratio, 5),
         "mean_residual": round(mean_residual, 5), "fluct_residual": round(fluct_residual, 4),
         "measured_band": [round(x, 4) for x in meas_band],
         "phi0_predicted_deg": round(math.degrees(phi0_geom), 1),
         "phi0_measured_deg": round(math.degrees(phi0_meas), 1),
         "phase_err_deg": round(math.degrees(phase_err), 2),
         "loop_residual_t0": r0, "loop_residual_max": max_res, "criteria": crit,
         "passed": bool(all(c["pass"] for c in crit.values()))}
    # overlay series (one clean rev) for the centerpiece plot
    series = {"theta_in_deg": [math.degrees(x) for x in T], "ratio_meas": list(map(float, w)),
              "ratio_formula": list(map(float, formula)),
              "theta_out_deg": [math.degrees(x) for x in O]}
    return v, series, frames


def _hud(img, lines, colors):
    from PIL import Image, ImageDraw
    im = Image.fromarray(img.copy()); dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, 470, 14 * len(lines) + 6], fill=(0, 0, 0))
    for i, (t, c) in enumerate(zip(lines, colors)):
        dr.text((5, 3 + 14 * i), t, fill=c)
    return np.asarray(im)


def _save_video(frames, meta, path):
    slow = f"{CAPTURE_HZ // OUT_FPS}x slow-mo"
    tag = f"β={meta['beta_deg']:.0f}° (STRAIGHT — no pulsation)" if meta["beta_deg"] == 0 else \
          f"β={meta['beta_deg']:.0f}°  band [{meta['vel_ratio_min']:.3f},{meta['vel_ratio_max']:.3f}]"
    vid = []
    for img, t, ai in frames:
        vid.append(_hud(img, [f"P-UJOINT V-A  Cardan   {tag}   [{slow}]",
                              f"T {t:5.2f}s   input {ai/(2*math.pi):5.2f} rev",
                              "markers: red=input  cyan=cross  magenta=output",
                              "output SPEED pulsates (leads/lags) — a single Cardan is NOT CV"
                              if meta["beta_deg"] > 0 else "output tracks at CONSTANT speed (β=0)"],
                        [(255, 255, 255), (150, 220, 255), (220, 220, 220),
                         (255, 200, 120) if meta["beta_deg"] > 0 else (200, 255, 200)]))
    imageio.mimsave(path, vid, fps=OUT_FPS, macro_block_size=1)


def _plot(series, v, meta, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(2, 1, figsize=(8, 7), sharex=True)
    th = series["theta_in_deg"]
    ax[0].plot(th, series["ratio_meas"], lw=2.2, color="#2b6cb0", label="measured ω_out/ω_in [physics]")
    ax[0].plot(th, series["ratio_formula"], ls="--", lw=1.5, color="#c53030",
               label="Cardan formula  cosβ/(1−sin²β·sin²θ)")
    ax[0].axhline(meta["vel_ratio_min"], color="#999", ls=":", lw=1)
    ax[0].axhline(meta["vel_ratio_max"], color="#999", ls=":", lw=1, label=f"band [cosβ,1/cosβ]")
    badge = "PASS" if v["passed"] else "FAIL"
    ax[0].set_ylabel("velocity ratio ω_out/ω_in")
    ax[0].set_title(f"P-UJOINT / V-A  universal_joint  β={meta['beta_deg']:.0f}°  [{badge}]   "
                    f"fluctuation overlay resid={v['fluct_residual']*100:.2f}%,  mean ratio="
                    f"{v['mean_ratio']:.4f}", fontsize=9, color="#22543d" if v["passed"] else "#742a2a")
    ax[0].legend(fontsize=8, loc="upper right"); ax[0].grid(alpha=.25)
    ax[1].plot(th, series["theta_out_deg"], lw=2, color="#6b46c1", label="θ_out(θ_in) [measured]")
    ax[1].plot(th, th, ls=":", lw=1, color="#888", label="1:1 reference")
    ax[1].set_xlabel("input angle θ_in (deg)"); ax[1].set_ylabel("output angle θ_out (deg)")
    ax[1].set_title("output position lags then leads — net 1:1 over the rev (mean ratio 1.0)", fontsize=8.5)
    ax[1].legend(fontsize=8); ax[1].grid(alpha=.25)
    fig.tight_layout(); fig.savefig(path, dpi=130)
    import matplotlib.pyplot as _p; _p.close(fig)


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "out"
    out.mkdir(parents=True, exist_ok=True)
    plan = ujoint_fixture()
    e1 = plan.element("E1")
    e1.params = CARD_REGISTRY["universal_joint"].resolve_params(plan, e1)
    assert not validate_all(plan), "fixture must be validator-clean"
    compile_assembly(plan)   # compile check (the yoke fuses to the input shaft — one solid)
    beta_fix = float(e1.params["angle_deg"])

    xml, meta = build_va_mjcf(plan, out / "assets", beta_fix)
    xf = out / "t2_ujoint_VA.xml"; xf.write_text(xml)
    model = mj.MjModel.from_xml_path(str(xf))
    gok, checks = g9_gconv(model)

    result = {
        "decision_row": "D-M21-1 P-UJOINT V-A on compiled ujoint_fixture (Cardan fluctuation verified)",
        "compile_hash": _hash(), "card": "universal_joint", "element": "E1",
        "rule_chain": {"beta_deg": beta_fix, "vel_ratio_min (cosβ)": meta["vel_ratio_min"],
                       "vel_ratio_max (1/cosβ)": meta["vel_ratio_max"], "fluctuation_pct": meta["fluctuation_pct"],
                       "formula": "ω_out/ω_in = cosβ/(1−sin²β·sin²θ)"},
        "rig": {"option": "(i) serial chain input→cross→output + one tip-connect closing the loop on axis B",
                "note": "NO polycoef=cosβ — the fluctuation EMERGES from the cross geometry",
                "nv": int(model.nv)},
        "g9_gconv": bool(gok), "g9_checks": [(c[0], bool(c[1]), c[2]) for c in checks], "modes": {},
    }
    if not gok:
        result["modes"]["V-A"] = {"ran": False, "reason": "G-CONV failed"}
    else:
        per_seed, series0, frames0, v0 = [], None, None, None
        for seed in range(N_SEEDS):
            rec = seed == 0
            v, series, frames = run_va(model, meta, seed, record=rec)
            per_seed.append(v)
            if rec:
                series0, frames0, v0 = series, frames, v
        n_pass = sum(v["passed"] for v in per_seed)
        result["modes"]["V-A"] = {"ran": True, "n_seeds": N_SEEDS, "seeds_passed": n_pass,
                                  "passed": bool(n_pass >= SEED_PASS),
                                  "criteria_seed0": per_seed[0]["criteria"], "per_seed": per_seed}
        # DISCRIMINATION: β=0 (straight) — the fluctuation must VANISH (band flat at 1.0)
        xml0, meta0 = build_va_mjcf(plan, out / "assets", 0.0)
        (out / "t2_ujoint_VA_beta0.xml").write_text(xml0)
        model0 = mj.MjModel.from_xml_path(str(out / "t2_ujoint_VA_beta0.xml"))
        v0b, series0b, frames0b = run_va(model0, meta0, seed=0, record=True)
        result["modes"]["V-A"]["discrimination_probe"] = {
            "beta_deg_at_angle": beta_fix, "fluct_residual_at_angle": per_seed[0]["fluct_residual"],
            "measured_band_at_angle": per_seed[0]["measured_band"],
            "beta0_measured_band": v0b["measured_band"],
            "beta0_fluctuation_pct": round((v0b["measured_band"][1] - v0b["measured_band"][0]) * 100, 3),
            "discriminates": bool(per_seed[0]["fluct_residual"] <= FLUCT_TOL
                                  and (v0b["measured_band"][1] - v0b["measured_band"][0]) < 0.01),
            "note": "the pulsation appears WITH the bend angle and only with it — β=0 flattens ω_out/ω_in to 1.0"}
        if series0:
            _plot(series0, v0, meta, out / "t2_ujoint_VA.png")
            result["modes"]["V-A"]["plot"] = "t2_ujoint_VA.png"
            if frames0:
                _save_video(frames0, meta, out / "t2_ujoint_VA.mp4")
                result["modes"]["V-A"]["video"] = "t2_ujoint_VA.mp4"
            if frames0b:
                _save_video(frames0b, meta0, out / "t2_ujoint_VA_beta0.mp4")
                result["modes"]["V-A"]["discrimination_video"] = "t2_ujoint_VA_beta0.mp4"
        print(f"\n=== P-UJOINT V-A ===  G-CONV {'ok' if gok else 'FAIL'}   seeds {n_pass}/{N_SEEDS} => "
              f"{'PASS' if n_pass >= SEED_PASS else 'FAIL'}   (nv={model.nv}, rig option i)")
        for name, c in per_seed[0]["criteria"].items():
            print(f"   {'ok  ' if c['pass'] else 'FAIL'} {name:<52s} {c['value']} (<= {c['threshold']})")
        s0 = per_seed[0]; dp = result["modes"]["V-A"]["discrimination_probe"]
        print(f"   fluctuation: measured band {s0['measured_band']} vs formula "
              f"[{meta['vel_ratio_min']},{meta['vel_ratio_max']}]  (φ0 predicted {s0['phi0_predicted_deg']}° "
              f"vs measured {s0['phi0_measured_deg']}°, phase err {s0['phase_err_deg']}°; overlay resid "
              f"{s0['fluct_residual']*100:.2f}%); loop residual max {s0['loop_residual_max']:.1e} m")
        print(f"   discrimination: β={beta_fix:.0f}° band {dp['measured_band_at_angle']} vs β=0 band "
              f"{dp['beta0_measured_band']} => discriminates={dp['discriminates']}")

    result["verdict_VA"] = result["modes"].get("V-A", {}).get("passed", False)
    result["emergent_check_resolution"] = {
        "status": "deferred",
        "argued": "the declared angled-pair KINEMATICS incl. the emergent Cardan fluctuation IS verified "
                  "(this rig); the cross-TRUNNION BEARING contact (pin-in-bore, pin_hinge-class) is "
                  "idealized as frictionless revolutes and NOT tested — a pin-class V-B, earnable later, "
                  "NOT an m17/R2b-curved limit (so neither m20's 'verified' nor lead_screw's R2b 'deferred')"}
    (out / "t2_ujoint_verdict.json").write_text(json.dumps(result, indent=2))
    print(f"\nV-A pass: {result['verdict_VA']}   emergent_check: kinematics verified, trunnion contact deferred (pin-class)")
    print("wrote", out / "t2_ujoint_verdict.json")


if __name__ == "__main__":
    main()
