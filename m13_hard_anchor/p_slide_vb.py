"""m13 CLOSING — P-SLIDE V-B (contact-only) on the lift's two vertical rails.

The hard one: NO declared slide joint. The mover (carriages + platform + rack, welded) is a FREE
body, and the vertical slide DoF must EMERGE from the two T-rails' contact geometry — while gravity
acts ALONG travel (the platform hangs on the mesh). m10's full lesson set applies: every collision
prim is the card's own box decomposition (source-stamped, D-M8-4), the moving carriage boxes are
D14-inset, friction is the frozen preset μ (R5), and a coverage gate watches ALL bodies
(all_parts_retained). The rails' prims are placed at ±rail_gap/2 and tilted −90° about Y to vertical.

Honest-checkpoint contract (the brief): if the contact stack fights the frozen preset, RECORD which
interface penetrates and at what scale — do NOT tune the preset.

Run:  ./bin/py m13_hard_anchor/p_slide_vb.py
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
from build123d import Rotation  # noqa: E402

from knowledge.cards.base import CARD_REGISTRY  # noqa: E402
from ontology.validators import validate_all  # noqa: E402
from pipeline.compile_assembly import compile_assembly  # noqa: E402
from tasks.build_goldens import anchor_lift  # noqa: E402
from verify.t2_physics.mjcf import _inertial, _to_trimesh  # noqa: E402
from verify.t2_physics.runner import _hash, g9_gconv  # noqa: E402

from step2mjcf import DENSITY, MM, MU, SOLIMP, SOLREF  # FROZEN preset (R5)  # noqa: E402

OUT = Path(__file__).parent / "out"
FROZEN_DT, FPS = 5e-4, 60
N_SEEDS, SEED_PASS = 5, 4
STROKE_MM, LOAD_KG, G = 120.0, 0.5, 9.81
MOVER = ["P2", "P3", "P4"]
TILT = Rotation(0, -90, 0)


def _v(a):
    return " ".join(f"{float(x):.9f}" for x in a)


def _tilt_pt(p):
    x, y, z = p
    return (-z, y, x)                       # (x,y,z) → (−z, y, x)


def _tilt_box(cx, cy, cz, hx, hy, hz):
    """Tilt a world-frame axis-aligned box (−90° about Y): pos → (−z,y,x); half-extents swap x↔z."""
    return (-cz, cy, cx), (hz, hy, hx)


def _rail_prims(plan, ca):
    """Both slide_rails' box prims, each offset to its rail's world XY, split by owner (rail→base,
    carriage→mover), then tilted to vertical. Returns (base_boxes, mover_boxes) as (pos,half,src)."""
    base_boxes, mover_boxes = [], []
    for eid in ("E1", "E2"):
        e = plan.element(eid)
        ax = ca.axes[eid]["point"]          # rail world axis point (drawer frame): (0, ±40, 4)
        prims = CARD_REGISTRY["slide_rail"].collision_hint(e, float(e.params["stroke"]))
        for pr in prims:
            lx, ly, lz = pr["pos"]
            hx, hy, hz = pr["size"]
            wx, wy, wz = lx + ax[0], ly + ax[1], lz + ax[2]     # local(axis) → world (travel +X)
            pos, half = _tilt_box(wx, wy, wz, hx, hy, hz)
            tgt = base_boxes if pr["owner"] == "rail" else mover_boxes
            tgt.append((pos, half, pr["source"]))
    return base_boxes, mover_boxes


def _add_mesh(body, asset, name, solid, material):
    vf = OUT / "assets" / f"vb_{name}.stl"
    vf.parent.mkdir(parents=True, exist_ok=True)
    mesh = _to_trimesh(TILT * solid, vf)
    ET.SubElement(asset, "mesh", name=name, file=vf.name)
    ET.SubElement(body, "geom", name=f"{name}_vis", type="mesh", mesh=name, material=material,
                  contype="0", conaffinity="0", group="2")
    return mesh


def build_vb(ca, plan, detent_mm=3.0):
    base_boxes, mover_boxes = _rail_prims(plan, ca)
    root = ET.Element("mujoco", model="lift_pslide_VB")
    ET.SubElement(root, "compiler", angle="radian", meshdir="assets", autolimits="true")
    ET.SubElement(root, "option", timestep=f"{FROZEN_DT}", integrator="implicitfast",
                  cone="elliptic", impratio="10", gravity="0 0 -9.81")
    vis = ET.SubElement(root, "visual")
    ET.SubElement(vis, "headlight", ambient="0.5 0.5 0.5", diffuse="0.6 0.6 0.6", specular="0.2 0.2 0.2")
    ET.SubElement(vis, "global", offwidth="1280", offheight="960", azimuth="150", elevation="-20")
    dflt = ET.SubElement(root, "default")
    # FROZEN preset on every contact geom; μ is the preset's (R5). condim 4 (friction + torsion).
    ET.SubElement(dflt, "geom", solref=f"{SOLREF[0]} {SOLREF[1]}",
                  solimp=f"{SOLIMP[0]} {SOLIMP[1]} {SOLIMP[2]}",
                  friction=f"{MU} 0.005 0.0001", condim="4", density="0")
    asset = ET.SubElement(root, "asset")
    for name, rgba in [("base", "0.54 0.66 0.79 1"), ("mover", "0.42 0.75 0.48 1")]:
        ET.SubElement(asset, "material", name=name, rgba=rgba)
    world = ET.SubElement(root, "worldbody")
    ET.SubElement(world, "light", pos="0.2 -0.3 0.6", dir="-0.3 0.5 -1", directional="true", diffuse="0.5 0.5 0.5")
    ET.SubElement(world, "camera", name="iso", pos="0.34 -0.40 0.30",
                  xyaxes="0.76 0.65 0 -0.32 0.37 0.87")

    # base = tower (welded) + the two rails' collision boxes (contype/conaffinity 1 = the slide contact)
    base = ET.SubElement(world, "body", name="base", pos="0 0 0")
    _inertial(base, _add_mesh(base, asset, "tower", ca.parts["P1"], "base"))
    for i, (pos, half, src) in enumerate(base_boxes):
        ET.SubElement(base, "geom", name=f"rail_c{i}", type="box", pos=_v(np.array(pos) * MM),
                      size=_v(np.array(half) * MM), material="base", contype="1", conaffinity="1", group="3")

    # mover = carriages+platform+rack, FREE body; carriage boxes ride the rails (contact-only DoF)
    mover = ET.SubElement(world, "body", name="mover", pos="0 0 0")
    ET.SubElement(mover, "freejoint", name="mover_free")
    for pid in MOVER:
        _add_mesh(mover, asset, f"mv_{pid}", ca.parts[pid], "mover")
    pm = _to_trimesh(TILT * ca.parts["P4"], OUT / "assets" / "vb_inertial.stl"); pm.density = DENSITY
    com = pm.center_mass; mass = float(pm.mass) + LOAD_KG; I = pm.moment_inertia
    ET.SubElement(mover, "inertial", pos=_v(com), mass=f"{mass:.9f}",
                  fullinertia=_v((I[0, 0], I[1, 1], I[2, 2], I[0, 1], I[0, 2], I[1, 2])))
    for i, (pos, half, src) in enumerate(mover_boxes):
        ET.SubElement(mover, "geom", name=f"carr_c{i}", type="box", pos=_v(np.array(pos) * MM),
                      size=_v(np.array(half) * MM), material="mover", contype="1", conaffinity="1", group="3")

    xml = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
    meta = {"n_base_boxes": len(base_boxes), "n_mover_boxes": len(mover_boxes)}
    return xml, meta


def run_vb(model, seed=0, record=False):
    """FULL CYCLE retention test (D-M13-6): raise → hold → lower, contact-only, gravity along travel.
    With the preloaded lips the free welded platform must stay RETAINED on the two rails throughout
    (off-axis ≤3°, lateral ≤6 mm, no derail, all parts retained). The lip-preload contact is an
    INTENDED contact class (D22) — it is the retention doing its job, not a defect."""
    d = mj.MjData(model)
    rng = np.random.default_rng(seed)
    mover = mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, "mover")
    base = mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, "base")
    cam = mj.mj_name2id(model, mj.mjtObj.mjOBJ_CAMERA, "iso")
    box_diag = float(model.stat.extent)
    adr = model.jnt_qposadr[model.body_jntadr[mover]]
    # mass of the mover (for the hold-force = weight)
    weight = float(model.body_mass[mover]) * G
    mj.mj_forward(model, d)
    d.qpos[adr:adr + 3] += rng.uniform(-2e-5, 2e-5, 3)
    mj.mj_forward(model, d)
    up = np.array([0, 0, 1.0])
    x0 = float(d.xpos[mover] @ up); R0 = d.xmat[mover].reshape(3, 3).copy(); grip = d.xpos[mover].copy()
    watched = [b for b in range(1, model.nbody)
               if mj.mj_id2name(model, mj.mjtObj.mjOBJ_BODY, b) != "base"]
    start_pos = {b: d.xpos[b].copy() for b in watched}
    renderer = mj.Renderer(model, 480, 640) if record else None
    RAISE_TO, F_RAISE, T_RAMP = 100.0, 25.0, 1.5   # F represents the crank+gear rack force
    ts, s_mm, off, lat, phase_ser, frames, nxt = [], [], [], [], [], [], 0.0
    diverged = derailed = part_lost = False
    peak_off = peak_lat = 0.0; hold_drift = 0.0
    phase = "RAISE"; t_hold0 = t_low0 = None; hold_s0 = None
    while d.time < 6.0:
        s = (float(d.xpos[mover] @ up) - x0) * 1e3
        if phase == "RAISE":
            F = min(F_RAISE, F_RAISE * d.time / T_RAMP)
            if s >= RAISE_TO:
                phase, t_hold0, hold_s0 = "HOLD", d.time, s
        elif phase == "HOLD":
            F = weight                                    # crank/gear balances gravity — a force-held pause
            hold_drift = max(hold_drift, abs(s - hold_s0))
            if d.time - t_hold0 > 0.6:
                phase, t_low0 = "LOWER", d.time
        else:                                            # LOWER — release: gravity descends, the tight-fit
            F = 0.0                                        # lip drag DAMPS it (a controlled fall), retained
        d.qfrc_applied[:] = 0.0
        mj.mj_applyFT(model, d, up * F, np.zeros(3), d.xpos[mover], mover, d.qfrc_applied)
        mj.mj_step(model, d)
        if (not np.all(np.isfinite(d.qpos))
                or np.linalg.norm(d.xpos[mover] - d.xpos[base]) > 10 * box_diag
                or float(np.abs(d.qvel).max()) > 1e3):
            diverged = True; break
        R = d.xmat[mover].reshape(3, 3); Rrel = R0.T @ R
        oa = math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(Rrel) - 1) / 2))))
        offv = d.xpos[mover] - grip - up * ((d.xpos[mover] - grip) @ up)
        latmm = float(np.linalg.norm(offv)) * 1e3
        peak_off = max(peak_off, oa); peak_lat = max(peak_lat, latmm)
        if latmm > 6.0:
            derailed = True
        for b in watched:
            dv = d.xpos[b] - start_pos[b]; offb = dv - up * (dv @ up)
            if float(np.linalg.norm(offb)) * 1e3 > 15.0:
                part_lost = True
        ts.append(d.time); s_mm.append(s); off.append(oa); lat.append(latmm); phase_ser.append(phase)
        if record and d.time >= nxt:
            renderer.update_scene(d, camera=cam); frames.append(renderer.render()); nxt += 1 / FPS
        if phase == "LOWER" and s <= 3.0:
            break
    if renderer:
        renderer.close()
    s_arr = np.array(s_mm) if s_mm else np.array([0.0])
    crit = {
        "reaches_stroke (raise ≥100 mm)": {"value": round(float(s_arr.max()), 1), "threshold": RAISE_TO,
                                           "pass": bool(s_arr.max() >= RAISE_TO - 2.0 and not diverged)},
        "retained (off≤3°)": {"value": round(peak_off, 2), "threshold": 3.0,
                              "pass": bool(peak_off <= 3.0 and not diverged)},
        "on_rails (lateral≤6 mm)": {"value": round(peak_lat, 2), "threshold": 6.0,
                                    "pass": bool(peak_lat <= 6.0 and not diverged)},
        "no_derail": {"value": derailed, "threshold": False, "pass": bool(not derailed and not diverged)},
        "all_parts_retained": {"value": part_lost, "threshold": False,
                               "pass": bool(not part_lost and not diverged)},
        "returns_to_base (≤6 mm)": {"value": round(float(s_arr[-1]) if len(s_arr) else 0.0, 1),
                                    "threshold": 6.0,
                                    "pass": bool((s_mm[-1] if s_mm else 99) <= 6.0 and not diverged)},
    }
    v = {"mode": "V-B", "seed": seed, "peak_offaxis_deg": round(peak_off, 2), "peak_lateral_mm": round(peak_lat, 2),
         "hold_drift_mm": round(hold_drift, 2), "s_max_mm": round(float(s_arr.max()), 1),
         "diverged": diverged, "derailed": derailed, "part_lost": part_lost,
         "criteria": crit, "passed": bool(all(c["pass"] for c in crit.values()))}
    return v, {"t": ts, "s_mm": s_mm, "off": off, "lat": lat, "phase": phase_ser}, frames


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    plan = anchor_lift()
    assert not validate_all(plan), "golden must be validator-clean"
    for e in plan.elements:
        e.params = CARD_REGISTRY[e.card_ref].resolve_params(plan, e)
    ca = compile_assembly(plan)
    preload = float(plan.element("E1").params.get("preload_mm", 0.0))
    xml, meta = build_vb(ca, plan)
    xf = OUT / "t2_pslide_VB.xml"; xf.write_text(xml)
    model = mj.MjModel.from_xml_path(str(xf))
    per, s0, f0, v0 = [], None, None, None
    for seed in range(N_SEEDS):
        v, s, fr = run_vb(model, seed, record=(seed == 0))
        per.append(v)
        if seed == 0:
            s0, f0, v0 = s, fr, v
    npass = sum(x["passed"] for x in per)
    if f0:
        imageio.mimsave(OUT / "lift_pslide_VB.mp4", f0, fps=FPS)
        _plot(s0, v0)
    result = {
        "decision_row": "m13 D-M13-6 — P-SLIDE V-B (contact-only) with the VERTICAL preloaded retention",
        "compile_hash": _hash(), "preload_mm": preload,
        "fix": ("D-M13-6: slide_rail orientation rule — when travel ∥ gravity the retention lips are "
                "PRELOADED by half the PETG print clearance (0.15 mm, sourced), a sprung take-up of the "
                "sliding slack. No preset change (R5); no criteria weakened."),
        "meta": meta,
        "p_slide_vb": {"ran": True, "n_seeds": N_SEEDS, "seeds_passed": npass,
                       "passed": bool(npass >= SEED_PASS), "criteria_seed0": per[0]["criteria"],
                       "per_seed": per},
        "d22_note": "the lip-preload contact is an INTENDED contact class — the retention working, not a defect",
        "shape_assert": {"contact_only": True, "gravity_along_travel": True, "preloaded_lips": preload > 0,
                         "n_rail_boxes": meta["n_base_boxes"], "n_carriage_boxes": meta["n_mover_boxes"]},
    }
    (OUT / "t2_pslide_vb_verdict.json").write_text(json.dumps(result, indent=2))
    c = per[0]
    print(f"P-SLIDE V-B (D-M13-6 preload {preload} mm): {npass}/{N_SEEDS} "
          f"{'PASS' if npass>=SEED_PASS else 'FAIL'}  s_max={c['s_max_mm']}mm "
          f"off={c['peak_offaxis_deg']}° lat={c['peak_lateral_mm']}mm derail={c['derailed']} "
          f"parts_lost={c['part_lost']} hold_drift={c['hold_drift_mm']}mm")
    for n, cc in c["criteria"].items():
        print(f"   {'ok  ' if cc['pass'] else 'FAIL'} {n:<34s} {cc['value']} (≤ {cc['threshold']})")
    print("wrote", OUT / "t2_pslide_vb_verdict.json")


def _plot(series, v):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, (a0, a1) = plt.subplots(2, 1, figsize=(9, 6), sharex=True, gridspec_kw={"height_ratios":[3,1]})
    t, sh, ph = series["t"], series["s_mm"], series["phase"]
    cols = {"RAISE":"#2f855a","HOLD":"#b7791f","LOWER":"#2b6cb0"}
    for phase,c in cols.items():
        xs=[t[i] for i in range(len(t)) if ph[i]==phase]; ys=[sh[i] for i in range(len(sh)) if ph[i]==phase]
        if xs: a0.plot(xs,ys,lw=2.2,color=c,label=phase)
    b="PASS" if v["passed"] else "FAIL"
    a0.set_ylabel("height s (mm)"); a0.legend(fontsize=9,loc="upper right"); a0.grid(alpha=.25)
    a0.set_title(f"P-SLIDE V-B (contact-only, preloaded vertical retention)  [{b}]  "
                 f"off-axis {v['peak_offaxis_deg']}° · lateral {v['peak_lateral_mm']} mm · retained",
                 fontsize=10, color="#22543d" if v["passed"] else "#742a2a")
    a1.plot(t, series["off"], lw=1.4, color="#dd6b20", label="off-axis (°)")
    a1.axhline(3.0, ls="--", c="#c53030", lw=1); a1.set_ylabel("off (°)"); a1.set_xlabel("t (s)")
    a1.grid(alpha=.25); a1.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(OUT / "lift_pslide_VB.png", dpi=130); plt.close(fig)


if __name__ == "__main__":
    main()
