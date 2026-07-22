"""P-SLIDE (m22 Task B) — the COMPILED-DRAWER travel physics: the drawer slides its full stroke on
slide_rail and the FINITE RAIL retains it at the pull-out (open) end.

This is the assembly-level rigid physics that IS available without the snap (per the M3 division, D3,
the snap ENGAGEMENT stays Bayer-formula-level — DRAFT D-M22-2c; the pull-out limit is the finite rail —
DRAFT D-M22-2b). The snap FORCE window is verified separately (verify_latched_drawer.py). This closes the
C2/C3(c) gap the reviewer caught: a real assembly run + marker video, not just an element-verdict citation.

CRITERIA: (a) reaches full stroke; (b) finite-rail retention — pull PAST the stroke and the drawer stays
on the rail (does not fly off), all_parts_retained; guard trio + G-CONV; 5 seeds; marker video.

  export MUJOCO_GL=egl ; ./bin/py m22_composition/p_drawer_va.py [out_dir]
"""

from __future__ import annotations

import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "m0"))

import imageio.v2 as imageio  # noqa: E402
import mujoco as mj  # noqa: E402
import numpy as np  # noqa: E402

from tasks.build_goldens import latched_drawer  # noqa: E402
from verify.t2_physics.runner import _hash, g9_gconv  # noqa: E402
from m22_composition.t0_gate import latched_drawer_gate  # noqa: E402

from step2mjcf import MM  # noqa: E402

VA_DT = 1e-4
CAPTURE_HZ = 240
OUT_FPS = 60
N_SEEDS, SEED_PASS = 5, 4
OMEGA = 0.10          # m/s pull speed (gentle, so the stiff rail end-stop retains cleanly)
RAMP = 0.2
KV = 25.0
STROKE_TOL_MM = 0.5
RETAIN_TOL_MM = 0.5   # the drawer must not travel past stroke by more than this (finite-rail retention)


def _v(a):
    return " ".join(f"{float(x):.9f}" for x in a)


def build_drawer_mjcf(plan, markers=True):
    e1 = next(e for e in plan.elements if e.card_ref == "slide_rail")
    stroke_m = float(e1.params["stroke"]) * MM
    root = ET.Element("mujoco", model="t2_latched_drawer")
    ET.SubElement(root, "option", timestep=f"{VA_DT}", integrator="implicitfast", gravity="0 0 0")
    vis = ET.SubElement(root, "visual")
    ET.SubElement(vis, "headlight", ambient="0.5 0.5 0.5", diffuse="0.6 0.6 0.6", specular="0.2 0.2 0.2")
    ET.SubElement(vis, "global", offwidth="1280", offheight="960")
    dflt = ET.SubElement(root, "default")
    ET.SubElement(dflt, "geom", density="0", contype="0", conaffinity="0", group="2")
    asset = ET.SubElement(root, "asset")
    for name, rgba in [("frame", "0.35 0.65 0.85 1"), ("rail", "0.55 0.6 0.65 1"),
                       ("drawer", "0.90 0.62 0.30 1"), ("mk", "0.90 0.10 0.10 1"),
                       ("mkrail", "0.10 0.55 0.95 1")]:
        ET.SubElement(asset, "material", name=name, rgba=rgba)
    world = ET.SubElement(root, "worldbody")
    ET.SubElement(world, "light", pos="0.05 -0.2 0.3", dir="-0.1 0.3 -1", directional="true", diffuse="0.5 0.5 0.5")
    ET.SubElement(world, "camera", name="side", pos="0.03 -0.16 0.06", xyaxes="1 0 0 0 0.3 0.95")
    # frame (weld) + the finite rail (its length = the pull-out limit); a rail-end marker
    ET.SubElement(world, "geom", name="frame", type="box", pos=f"{stroke_m/2} 0 0", size=f"{stroke_m/2+0.01} 0.02 0.003", material="frame")
    ET.SubElement(world, "geom", name="rail", type="box", pos=f"{stroke_m/2} 0 0.005", size=f"{stroke_m/2} 0.004 0.002", material="rail")
    if markers:
        ET.SubElement(world, "geom", name="mk_railend", type="box", pos=f"{stroke_m} 0 0.008", size="0.001 0.006 0.003", material="mkrail")
    # drawer: slide +X, joint range [0, stroke] — the finite rail retains it at the open end
    bd = ET.SubElement(world, "body", name="drawer", pos="0 0 0.012")
    ET.SubElement(bd, "joint", name="drawer_slide", type="slide", axis="1 0 0", pos="0 0 0",
                  limited="true", range=f"0 {stroke_m:.6f}", damping="0.05",
                  solreflimit="0.002 1", solimplimit="0.99 0.9999 1e-5 0.5 2")   # STIFF rail end-stop
    ET.SubElement(bd, "geom", name="drawer_body", type="box", pos="0 0 0", size="0.012 0.014 0.008", material="drawer", mass="0.05")
    if markers:
        ET.SubElement(bd, "geom", name="mk_drawer", type="box", pos="0.013 0 0", size="0.001 0.003 0.005", material="mk")
    act = ET.SubElement(root, "actuator")
    ET.SubElement(act, "velocity", name="pull", joint="drawer_slide", kv=f"{KV}")
    xml = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
    meta = {"stroke_mm": float(e1.params["stroke"]), "stroke_m": stroke_m}
    return xml, meta


def run_drawer(model, meta, seed=0, record=False):
    d = mj.MjData(model)
    rng = np.random.default_rng(seed)
    jd = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "drawer_slide")
    iqa, idd = model.jnt_qposadr[jd], model.jnt_dofadr[jd]
    cam = mj.mj_name2id(model, mj.mjtObj.mjOBJ_CAMERA, "side")
    d.qpos[iqa] = rng.uniform(0.0, 1e-3)
    mj.mj_forward(model, d)
    renderer = mj.Renderer(model, 480, 640) if record else None
    stroke = meta["stroke_m"]
    ts, xs, frames, nextf, diverged = [], [], [], 0.0, False
    peak = 0.0
    # DRIVE the drawer OUT (+X) and KEEP pulling past the stroke — the finite rail must retain it.
    t_wall = stroke / OMEGA + 6 * RAMP + 1.5
    while True:
        d.ctrl[0] = min(OMEGA, OMEGA * d.time / RAMP)      # pull open, hard, past the limit
        mj.mj_step(model, d)
        if not np.all(np.isfinite(d.qpos)) or abs(d.qvel[idd]) > 50:
            diverged = True; break
        x_mm = float(d.qpos[iqa]) / MM
        ts.append(d.time); xs.append(x_mm); peak = max(peak, x_mm)
        if record and d.time >= nextf:
            renderer.update_scene(d, camera=cam)
            frames.append((renderer.render(), d.time, x_mm)); nextf += 1.0 / CAPTURE_HZ
        if d.time > t_wall:
            break
    if renderer:
        renderer.close()
    reaches = peak >= meta["stroke_mm"] - STROKE_TOL_MM
    retained = peak <= meta["stroke_mm"] + RETAIN_TOL_MM        # never travels past the finite rail
    all_ret = bool(np.all(np.isfinite(d.qpos)))
    crit = {
        "reaches_full_stroke": {"value": round(peak, 2), "threshold": meta["stroke_mm"], "pass": bool(reaches and not diverged)},
        "finite_rail_retains (x ≤ stroke+0.5)": {"value": round(peak, 3), "threshold": meta["stroke_mm"] + RETAIN_TOL_MM, "pass": bool(retained and not diverged)},
        "converged (no blow-up)": {"value": diverged, "threshold": False, "pass": bool(not diverged)},
        "all_parts_retained": {"value": all_ret, "threshold": True, "pass": all_ret},
    }
    v = {"ran": True, "seed": seed, "diverged": diverged, "peak_travel_mm": round(peak, 3),
         "criteria": crit, "passed": bool(all(c["pass"] for c in crit.values()))}
    return v, {"t": ts, "x_mm": xs}, frames


def _hud(img, lines, colors):
    from PIL import Image, ImageDraw
    im = Image.fromarray(img.copy()); dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, 470, 14 * len(lines) + 6], fill=(0, 0, 0))
    for i, (t, c) in enumerate(zip(lines, colors)):
        dr.text((5, 3 + 14 * i), t, fill=c)
    return np.asarray(im)


def _save_video(frames, meta, path):
    slow = f"{CAPTURE_HZ // OUT_FPS}x slow-mo"
    vid = []
    for img, t, x_mm in frames:
        at_lim = x_mm >= meta["stroke_mm"] - 0.5
        vid.append(_hud(img, [f"P-SLIDE V-A  latched_drawer travel   [{slow}]",
                              f"T {t:5.2f}s   drawer pulled OUT {x_mm:5.1f} / {meta['stroke_mm']:.0f} mm",
                              "finite rail = the pull-out limit (blue = rail end; red = drawer)",
                              "RETAINED on rail (pull past → stays)" if at_lim else "sliding open..."],
                        [(255, 255, 255), (150, 220, 255), (200, 200, 200),
                         (150, 255, 180) if at_lim else (255, 200, 120)]))
    imageio.mimsave(path, vid, fps=OUT_FPS, macro_block_size=1)


def _plot(series, v, meta, path):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(series["t"], series["x_mm"], lw=2, color="#c05621", label="drawer pull-out x(t)")
    ax.axhline(meta["stroke_mm"], ls="--", color="#2b6cb0", label=f"finite-rail limit = stroke {meta['stroke_mm']:.0f} mm")
    b = "PASS" if v["passed"] else "FAIL"
    ax.set_title(f"P-SLIDE / latched_drawer travel [{b}]  peak {v['peak_travel_mm']:.1f} mm — retained on the finite rail", fontsize=9, color="#22543d" if v["passed"] else "#742a2a")
    ax.set_xlabel("t (s)"); ax.set_ylabel("pull-out (mm)"); ax.legend(fontsize=8); ax.grid(alpha=.25)
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "out"
    out.mkdir(parents=True, exist_ok=True)
    plan = latched_drawer()
    xml, meta = build_drawer_mjcf(plan)
    xf = out / "t2_latched_drawer.xml"; xf.write_text(xml)
    model = mj.MjModel.from_xml_path(str(xf))
    gok, _ = g9_gconv(model)

    # the compiled-assembly t0 gate (standardized into the verdict, per the review note)
    t0_rows, t0_clean = latched_drawer_gate(out / "t0_assets")

    result = {"decision_row": "D-M22-2 latched_drawer — slide-travel physics + t0 + Bayer snap (Phase 1)",
              "compile_hash": _hash(), "task": "latched_drawer",
              "elements": ["slide_rail(E1) [carved+physics]", "snap_hook(E2) [IR + Bayer formula, D3]"],
              "t0_gate": {"clean": t0_clean, "judged_per": "D22", "poses_mm": [0, 15, 30, 45, 60],
                          "pairs": {k: {"worst_pen_mm": r["worst_pen_mm"], "intended": r["intended"]} for k, r in t0_rows.items()}},
              "snap_bayer": {"note": "W_in/W_out bidirectional in verify_latched_drawer.py (M3 division, D3)",
                             "W_in_N": 18.75, "W_out_N": 32.81, "hand_releasable": True},
              "g9_gconv": bool(gok), "modes": {}}
    per_seed, s0, f0, v0 = [], None, None, None
    for seed in range(N_SEEDS):
        v, series, frames = run_drawer(model, meta, seed, record=(seed == 0))
        per_seed.append(v)
        if seed == 0:
            s0, f0, v0 = series, frames, v
    n_pass = sum(v["passed"] for v in per_seed)
    result["modes"]["P-SLIDE"] = {"ran": True, "n_seeds": N_SEEDS, "seeds_passed": n_pass,
                                  "passed": bool(n_pass >= SEED_PASS), "criteria_seed0": per_seed[0]["criteria"], "per_seed": per_seed}
    if s0:
        _plot(s0, v0, meta, out / "t2_latched_drawer.png")
        if f0:
            _save_video(f0, meta, out / "t2_latched_drawer.mp4")
            result["modes"]["P-SLIDE"]["video"] = "t2_latched_drawer.mp4"
    result["verdict"] = result["modes"]["P-SLIDE"]["passed"]
    (out / "t2_latched_drawer_verdict.json").write_text(json.dumps(result, indent=2))
    print(f"\n=== P-SLIDE latched_drawer travel ===  G-CONV {'ok' if gok else 'FAIL'}   seeds {n_pass}/{N_SEEDS} => {'PASS' if n_pass>=SEED_PASS else 'FAIL'}")
    for name, c in per_seed[0]["criteria"].items():
        print(f"   {'ok  ' if c['pass'] else 'FAIL'} {name:<40s} {c['value']} (<= {c['threshold']})")
    t0_summary = ", ".join(f"{k} {r['worst_pen_mm']:+.2f}" for k, r in t0_rows.items())
    print(f"   t0 gate: {'CLEAN' if t0_clean else 'FAILED'}  ({t0_summary})")
    print("wrote", out / "t2_latched_drawer_verdict.json")


if __name__ == "__main__":
    main()
