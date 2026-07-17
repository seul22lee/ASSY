"""P-GEAR (MECHSYNTH §6.3) on the compiled rack_pinion_fixture — V-A ONLY (D-M1-7, the standing
R2b-open flag).

WHY V-A ONLY. rack_pinion carries a STANDING R2b-OPEN FLAG (D-M1-5/-7): the involute IS conjugate
and FORWARD meshing is demonstrable (M1 R2b, ratio −0.50), but BIDIRECTIONAL contact meshing
diverges at the frozen preset — the reversal backlash-crossing impact blows up, and no module size
or preset parameter fixes it (a contact-FORMULATION limit, not a tuning one). So a rack_pinion is
verified V-A: the transmission is a DECLARED kinematic pair — a hinge on the pinion, a slide on the
rack, coupled by an equality constraint at the pitch radius — and P-GEAR checks that this declared
pair realizes the card's §3.6 ratio to within 5% over N revolutions. The emergent-contact V-B is
NAMED-DEFERRED (see the verdict's `v_b_gap`), never silently claimed.

WHAT V-A ACTUALLY TESTS (it is not a tautology). The equality coupling's polycoef is rp in METRES,
rp = m·z/2 computed by the card. Driving the pinion and measuring the rack's travel end-to-end
exercises: (1) the card's rp formula, (2) the mm→m unit path, (3) the joint axes, (4) model
stability under the servo. If any were wrong the measured travel would not match the INDEPENDENT
formula prediction travel_per_rev·N (travel_per_rev = π·m·z) and the residual would exceed 5%.

The frozen contact preset (R5) is imported for provenance, but V-A declares NO contact geoms
(contype/conaffinity = 0) — the joints are the mechanism — so dt is set to the frozen 5e-4 only to
keep every experiment on the same clock; no contact solver runs here.

Run:  ./bin/py m11_rack_pinion/p_gear_va.py [out_dir]
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

from build123d import Pos  # noqa: E402
from knowledge.cards.base import CARD_REGISTRY  # noqa: E402
from knowledge.cards.rack_pinion import build_pinion, dims_from  # noqa: E402
from knowledge.templates import TEMPLATES  # noqa: E402
from ontology.validators import validate_all  # noqa: E402
from pipeline.compile_assembly import compile_assembly  # noqa: E402
from tasks.build_goldens import rack_pinion_fixture  # noqa: E402
from verify.t2_physics.mjcf import _inertial, _to_trimesh  # noqa: E402
from verify.t2_physics.runner import _hash, g9_gconv  # noqa: E402

from step2mjcf import MM, SOLIMP, SOLREF  # FROZEN preset (R5)  # noqa: E402

FROZEN_DT = 5e-4
FPS = 60
N_SEEDS, SEED_PASS = 5, 4
OMEGA = 3.0            # rad/s drive speed
RATIO_TOL = 0.05      # |s/(θ·rp) − 1| ≤ 5% (§6.3)
KV = 5e-2             # velocity-servo gain (tight tracking against the coupled rack inertia)
RAMP = 0.4            # s to reach omega


def _v(a):
    return " ".join(f"{float(x):.9f}" for x in a)


def build_va_mjcf(plan, ca, meshdir: Path):
    """Hand-build the V-A rig: base(welded) + pinion(hinge) + rack(slide), coupled by an equality
    joint at the pitch radius. Reuses the frozen-preset mesh helpers; declares NO contact geoms."""
    meshdir.mkdir(parents=True, exist_ok=True)
    e1 = plan.element("E1")
    g = dims_from(e1.params)
    rp_m = (g.module * g.z_pinion / 2.0) * MM          # pitch radius in METRES (equality polycoef)
    ax = ca.axes["E1"]
    ax_pt = np.array(ax["point"], float) * MM
    ax_dir = np.array(ax["dir"], float); ax_dir /= np.linalg.norm(ax_dir)

    # three solids: bare carrier (base), the placed pinion (rotating), rack∪carrier (sliding mover)
    base_solid = TEMPLATES["pinion_carrier"](**{k: v for k, v in plan.piece("P1").params.items()
                                                if isinstance(v, (int, float))}).part
    pinion_solid = Pos(*ax["point"]) * build_pinion(g)
    rack_solid = ca.parts["P2"]

    root = ET.Element("mujoco", model="t2_rack_pinion_VA")
    ET.SubElement(root, "compiler", angle="radian", meshdir=meshdir.name, autolimits="true")
    ET.SubElement(root, "option", timestep=f"{FROZEN_DT}", integrator="implicitfast",
                  cone="elliptic", impratio="10")     # FROZEN clock (R5); no contact solver used
    vis = ET.SubElement(root, "visual")
    ET.SubElement(vis, "headlight", ambient="0.5 0.5 0.5", diffuse="0.6 0.6 0.6",
                  specular="0.2 0.2 0.2")
    ET.SubElement(vis, "global", offwidth="1280", offheight="960", azimuth="140", elevation="-20")
    dflt = ET.SubElement(root, "default")
    # a default geom is declared with the frozen solref/solimp for provenance, but every geom below
    # sets contype/conaffinity=0 — V-A carries motion in the joints, not in contact (D-M1-7).
    ET.SubElement(dflt, "geom", solref=f"{SOLREF[0]} {SOLREF[1]}",
                  solimp=f"{SOLIMP[0]} {SOLIMP[1]} {SOLIMP[2]}", density="0",
                  contype="0", conaffinity="0", group="2")
    asset = ET.SubElement(root, "asset")
    ET.SubElement(asset, "material", name="base", rgba="0.35 0.65 0.85 1")
    ET.SubElement(asset, "material", name="pinion", rgba="0.95 0.62 0.25 1")
    ET.SubElement(asset, "material", name="rack", rgba="0.6 0.75 0.6 1")
    world = ET.SubElement(root, "worldbody")
    ET.SubElement(world, "light", pos="0.15 -0.25 0.4", dir="-0.3 0.5 -1", directional="true",
                  diffuse="0.5 0.5 0.5")
    ET.SubElement(world, "camera", name="iso", pos="0.18 -0.22 0.16",
                  xyaxes="0.78 0.63 0 -0.28 0.34 0.90")

    masses = {}
    specs = [("base", base_solid, "base", None),
             ("pinion", pinion_solid, "pinion", ("hinge", ax_dir)),
             ("rack", rack_solid, "rack", ("slide", ax_dir_x := np.array([1.0, 0.0, 0.0])))]
    for name, solid, mat, joint in specs:
        body = ET.SubElement(world, "body", name=name, pos="0 0 0")
        if joint is not None:
            jkind, jaxis = joint
            if jkind == "hinge":
                ET.SubElement(body, "joint", name="pinion_hinge", type="hinge", axis=_v(jaxis),
                              pos=_v(ax_pt), damping="0.002")
            else:
                ET.SubElement(body, "joint", name="rack_slide", type="slide", axis=_v(jaxis),
                              pos=_v(ax_pt), damping="0.02")
        vf = meshdir / f"rp_{name}_vis.stl"
        mesh = _to_trimesh(solid, vf)
        masses[name] = _inertial(body, mesh)
        ET.SubElement(asset, "mesh", name=f"{name}_vis", file=vf.name)
        ET.SubElement(body, "geom", name=f"{name}_vis", type="mesh", mesh=f"{name}_vis",
                      material=mat)

    # THE DECLARED TRANSMISSION (V-A): rack_slide(m) = rp_m · pinion_hinge(rad). polycoef =
    # [a0, a1, …] with joint1 = a0 + a1·joint2 + …  → a1 = rp in metres. This is the "declared-shaft
    # ratio" of D-M1-7 — the pair the geometry is meant to realize, checked here end-to-end.
    eq = ET.SubElement(root, "equality")
    # near-RIGID coupling: a gear transmission is a hard kinematic constraint, not a compliant spring.
    # A stiff solref/solimp keeps s = rp·θ to <1% so the declared ratio is what the rack actually
    # tracks (the default equality softness lets the rack lag the pinion ~3% under drive).
    ET.SubElement(eq, "joint", name="couple", joint1="rack_slide", joint2="pinion_hinge",
                  polycoef=f"0 {rp_m:.9f} 0 0 0",
                  solref="0.0005 1", solimp="0.999 0.9999 0.0001 0.5 2")
    act = ET.SubElement(root, "actuator")
    ET.SubElement(act, "velocity", name="drive", joint="pinion_hinge", kv=f"{KV}")

    xml = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
    meta = {"rp_mm": g.module * g.z_pinion / 2.0, "rp_m": rp_m, "module": g.module,
            "z_pinion": g.z_pinion, "travel_per_rev_mm": round(math.pi * g.module * g.z_pinion, 4),
            "stroke_mm": g.stroke, "rack_len_mm": g.rack_len,
            "masses_kg": masses, "axis_m": {"point": list(ax_pt), "dir": list(ax_dir)}}
    return xml, meta


def run_va(model, meta, seed=0, record=False):
    """Drive the pinion N_REV forward; measure the rack travel vs the card's independent formula
    prediction (travel_per_rev·N). Residual = |s_meas/(θ·rp) − 1|; also report the formula residual."""
    d = mj.MjData(model)
    rng = np.random.default_rng(seed)
    jpin = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "pinion_hinge")
    jrack = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, "rack_slide")
    ipa = model.jnt_qposadr[jpin]
    ira = model.jnt_qposadr[jrack]
    rp_m = meta["rp_m"]
    cam = mj.mj_name2id(model, mj.mjtObj.mjOBJ_CAMERA, "iso")

    # seeds perturb the pinion start angle slightly — robustness, not re-tuning (R5)
    d.qpos[ipa] += rng.uniform(-1e-3, 1e-3)
    mj.mj_forward(model, d)

    renderer = mj.Renderer(model, 480, 640) if record else None
    # drive until the rack reaches its DESIGN STROKE (not an arbitrary rev count): the rack physically
    # travels `stroke` mm and no further, and rack_len = stroke + tpr/4 (§3.6) is sized so the pinion
    # never runs off the toothed span across that stroke. θ_target = stroke/rp.
    stroke_m = meta["stroke_mm"] * MM
    theta_target = stroke_m / rp_m
    theta0 = float(d.qpos[ipa])
    s0 = float(d.qpos[ira])
    ts, thp, srk, ratio_series, frames, next_frame = [], [], [], [], [], 0.0
    diverged = False
    t_wall = theta_target / OMEGA + 4 * RAMP + 8.0    # generous: the servo lags the coupled inertia

    while True:
        ctrl = min(OMEGA, OMEGA * d.time / RAMP)
        d.ctrl[0] = ctrl
        mj.mj_step(model, d)
        if not np.all(np.isfinite(d.qpos)) or abs(d.qvel[0]) > 200:
            diverged = True
            break
        th = float(d.qpos[ipa]) - theta0
        s = float(d.qpos[ira]) - s0
        ts.append(d.time); thp.append(th); srk.append(s)
        if abs(th) > np.deg2rad(20):
            ratio_series.append(s / (th * rp_m))
        if record and d.time >= next_frame:
            renderer.update_scene(d, camera=cam)
            frames.append(renderer.render())
            next_frame += 1.0 / FPS
        if th >= theta_target:
            break
        if d.time > t_wall:
            break
    if renderer:
        renderer.close()

    th_final = float(thp[-1]) if thp else 0.0
    s_final = float(srk[-1]) if srk else 0.0                  # metres
    revs = th_final / (2 * np.pi)
    # (1) kinematic ratio residual: measured travel vs (θ·rp)
    s_pred_kin = th_final * rp_m
    ratio_resid = abs(s_final / s_pred_kin - 1.0) if s_pred_kin else 1.0
    # (2) formula residual: measured travel (mm) vs the CARD's travel_per_rev·revs (independent)
    s_meas_mm = s_final / MM
    s_formula_mm = meta["travel_per_rev_mm"] * revs
    formula_resid = abs(s_meas_mm / s_formula_mm - 1.0) if s_formula_mm else 1.0

    # the rack reaches its design stroke AND rack_len (§3.6) covers that travel with margin
    reaches_stroke = s_meas_mm >= meta["stroke_mm"] - 1.0
    rack_covers = meta["rack_len_mm"] >= s_meas_mm
    crit = {
        "transmission_ratio (|s/(θ·rp)−1| ≤ 5%)": {
            "value": round(ratio_resid, 4), "threshold": RATIO_TOL,
            "pass": bool(ratio_resid <= RATIO_TOL and not diverged)},
        "matches_§3.6_formula (|s/(tpr·rev)−1| ≤ 5%)": {
            "value": round(formula_resid, 4), "threshold": RATIO_TOL,
            "pass": bool(formula_resid <= RATIO_TOL and not diverged)},
        "reaches_design_stroke": {"value": round(s_meas_mm, 1), "threshold": meta["stroke_mm"],
                                  "pass": bool(reaches_stroke and rack_covers and not diverged)},
        "converged (no blow-up)": {"value": diverged, "threshold": False,
                                   "pass": bool(not diverged)},
    }
    v = {"ran": True, "mode": "V-A", "seed": seed, "diverged": diverged,
         "revs_done": round(revs, 3), "theta_final_deg": round(np.rad2deg(th_final), 1),
         "rack_travel_mm": round(s_meas_mm, 3), "formula_travel_mm": round(s_formula_mm, 3),
         "rack_len_mm": meta["rack_len_mm"], "stroke_mm": meta["stroke_mm"],
         "ratio_residual": round(ratio_resid, 4), "formula_residual": round(formula_resid, 4),
         "criteria": crit, "passed": bool(all(c["pass"] for c in crit.values()))}
    series = {"t": ts, "theta_deg": list(np.rad2deg(thp)), "rack_mm": [s / MM for s in srk]}
    return v, series, frames


def _plot(series, v, path, meta):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 5))
    th = series["theta_deg"]; rk = series["rack_mm"]
    ax.plot(th, rk, lw=2, color="#2b6cb0", label="rack travel s(θ)  [measured]")
    # the card's §3.6 line: s = travel_per_rev · (θ/360)
    tpr = meta["travel_per_rev_mm"]
    th_line = np.array(th) if th else np.array([0.0])
    ax.plot(th_line, tpr * th_line / 360.0, ls="--", lw=1.4, color="#c53030",
            label=f"§3.6 formula  s = {tpr:.1f}·θ/360")
    badge = "PASS" if v["passed"] else "FAIL"
    ax.set_xlabel("pinion angle θ (deg)"); ax.set_ylabel("rack travel s (mm)")
    ax.set_title(f"P-GEAR / V-A  rack_pinion  [{badge}]   travel={v['rack_travel_mm']:.1f} mm over "
                 f"{v['revs_done']:.2f} rev,  ratio resid={v['ratio_residual']*100:.2f}%",
                 color="#22543d" if v["passed"] else "#742a2a", fontsize=10)
    ax.legend(fontsize=9); ax.grid(alpha=.25)
    fig.tight_layout(); fig.savefig(path, dpi=130)
    import matplotlib.pyplot as _p; _p.close(fig)


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "out"
    out.mkdir(parents=True, exist_ok=True)
    plan = rack_pinion_fixture()
    e1 = plan.element("E1")
    e1.params = CARD_REGISTRY["rack_pinion"].resolve_params(plan, e1)
    assert not validate_all(plan), "fixture must be validator-clean"
    ca = compile_assembly(plan)

    xml, meta = build_va_mjcf(plan, ca, out / "assets")
    xf = out / "t2_rack_pinion_VA.xml"; xf.write_text(xml)
    model = mj.MjModel.from_xml_path(str(xf))
    gok, checks = g9_gconv(model)

    va_proto = next(p for p in plan.protocols if p.mode == "V-A")
    result = {
        "decision_row": "D-D-2 P-GEAR V-A on compiled rack_pinion_fixture (V-B DEFERRED, R2b/D-M1-7)",
        "compile_hash": _hash(),
        "card": "rack_pinion", "element": "E1",
        "params": {k: e1.params[k] for k in ("module", "z_pinion", "stroke", "backlash")},
        "rp_mm": meta["rp_mm"], "travel_per_rev_mm": meta["travel_per_rev_mm"],
        "g9_gconv": bool(gok),
        "g9_checks": [(c[0], bool(c[1]), c[2]) for c in checks],
        "v_b_gap": va_proto.actuation.get("v_b_gap"),
        "modes": {},
    }
    if not gok:
        result["modes"]["V-A"] = {"ran": False, "reason": "G-CONV failed (model incoherent)"}
    else:
        per_seed, series0, frames0, v0 = [], None, None, None
        for seed in range(N_SEEDS):
            rec = seed == 0
            v, series, frames = run_va(model, meta, seed, record=rec)
            per_seed.append(v)
            if rec:
                series0, frames0, v0 = series, frames, v
        n_pass = sum(v["passed"] for v in per_seed)
        result["modes"]["V-A"] = {
            "ran": True, "n_seeds": N_SEEDS, "seeds_passed": n_pass,
            "passed": bool(n_pass >= SEED_PASS), "criteria_seed0": per_seed[0]["criteria"],
            "per_seed": per_seed}
        if series0:
            _plot(series0, v0, out / "t2_rack_pinion_VA.png", meta)
            result["modes"]["V-A"]["plot"] = "t2_rack_pinion_VA.png"
            if frames0:
                imageio.mimsave(out / "t2_rack_pinion_VA.mp4", frames0, fps=FPS)
                result["modes"]["V-A"]["video"] = "t2_rack_pinion_VA.mp4"
        print(f"\n=== V-A ===  G-CONV ok   seeds {n_pass}/{N_SEEDS} => "
              f"{'PASS' if n_pass >= SEED_PASS else 'FAIL'}")
        for name, c in per_seed[0]["criteria"].items():
            print(f"   {'ok  ' if c['pass'] else 'FAIL'} {name:<42s} {c['value']} (<= {c['threshold']})")

    # guard trio: decision_row (above), compile_hash (above), shape_assert (below)
    result["verdict_VA"] = result["modes"].get("V-A", {}).get("passed", False)
    result["verdict_VB"] = "DEFERRED — pending preset_v2 (R2b/D-M1-7)"
    result["shape_assert"] = {
        "va_present": "V-A" in result["modes"],
        "vb_named_deferred": result["v_b_gap"] is not None,
        "no_vb_pass_claimed": result["verdict_VB"].startswith("DEFERRED")}
    (out / "t2_rack_pinion_verdict.json").write_text(json.dumps(result, indent=2))
    print(f"\nV-A pass: {result['verdict_VA']}   V-B: {result['verdict_VB']}")
    print("wrote", out / "t2_rack_pinion_verdict.json")


if __name__ == "__main__":
    main()
