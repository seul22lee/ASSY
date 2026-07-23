"""m25 — CONTACT LAYER applied to latched_drawer (§14 T3c landing verified by ACTUAL CONTACT, D-M19-3).

The class-② LIMIT carrier here is the CLOSED landing: the oversized front panel lands on the face frame.
The drawer is driven shut; the panel×face CONTACT (frozen R5 preset) stops it at s=0 — the declared
slide RANGE lower bound that stood in for the closed stop is WIDENED (limited=false), so the PART does
the stopping (recorded per joint). The tray×rail RIDE+RETENTION is the declared slide DoF + fit clearance
(no LIMIT to carry — printed in the map). The clip×bump retention stays class-③ (sourced Bayer W_out,
m23) — printed EXCLUDED. Judgement: IR criteria + guards.

  export MUJOCO_GL=egl ; ./bin/py m25_contact_layer/apply_latched_drawer.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "m0")); sys.path.insert(0, str(ROOT / "m25_contact_layer"))

import imageio.v2 as imageio  # noqa: E402
import mujoco as mj  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402

from knowledge.templates.host_templates import latch_design_parts  # noqa: E402
from verify import contact_layer as CL  # noqa: E402
from verify.t2_physics.mjcf import _to_trimesh  # noqa: E402
from verify.t2_physics.runner import _hash, g9_gconv  # noqa: E402
from contact_schedule import SCHEDULE  # noqa: E402
from step2mjcf import MM  # noqa: E402

DRAWER_MASS = 0.05
STROKE_M = 0.050


def _hud(img, lines, colors):
    from PIL import Image, ImageDraw
    im = Image.fromarray(img.copy()); dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, 500, 14 * len(lines) + 6], fill=(0, 0, 0))
    for i, (t, c) in enumerate(zip(lines, colors)):
        dr.text((5, 3 + 14 * i), t, fill=c)
    return np.asarray(im)


def main():
    out = ROOT / "m25_contact_layer" / "out"; out.mkdir(parents=True, exist_ok=True)
    parts = latch_design_parts()
    mdir = out / "ld_assets"; mdir.mkdir(parents=True, exist_ok=True)
    meshes = {k: _to_trimesh(v, mdir / f"{k}.stl") for k, v in parts.items()}
    dm = trimesh.util.concatenate([meshes["drawer_body"], meshes["clip"]])
    dm.density = DRAWER_MASS / dm.volume
    diag = np.clip(np.diag(dm.moment_inertia), 1e-9, None)
    inertial = {"mass": DRAWER_MASS, "pos": tuple(dm.center_mass), "diag": tuple(diag)}

    # the closed landing: the panel back lands on the face-frame front (both at x≈0.030 at s=0). Pads meet
    # at s≈0; the CONTACT carries the closed stop, so the drawer slide is UNLIMITED (limited=false).
    spec = {
        "model": "contact_latched_drawer", "gravity": (0, 0, -9.81),
        "materials": [{"name": "cab", "rgba": "0.60 0.66 0.72 0.30"}, {"name": "bump", "rgba": "0.85 0.30 0.30 1"},
                      {"name": "drawer", "rgba": "0.95 0.72 0.35 1"}, {"name": "clip", "rgba": "0.20 0.55 0.95 1"},
                      {"name": "stop", "rgba": "0.20 0.75 0.30 1"}, {"name": "mk", "rgba": "0.90 0.15 0.15 1"}],
        "meshes_assets": [{"name": f"m_{k}", "file": f"{k}.stl"} for k in meshes],
        "cameras": [{"name": "cutaway", "pos": "0.03 -0.12 0.055", "xyaxes": "1 0 0 0 0.4 0.92"}],
        "world_meshes": [{"name": "cab_mesh", "mesh": "m_cabinet_body", "material": "cab"},
                         {"name": "bump_mesh", "mesh": "m_bump", "material": "bump"}],
        # the face-frame FRONT pad (fixed) the panel lands on.
        "world_pads": [{"name": "face_frame", "pos": (0.028, 0, 0.013), "size": (0.002, 0.016, 0.009), "material": "stop"}],
        "bodies": [
            {"name": "drawer", "inertial": inertial,
             "joints": [{"name": "drawer_slide", "type": "slide", "axis": (1, 0, 0), "damping": 30.0}],
             "pads": [{"name": "panel_pad", "pos": (0.0322, 0, 0.013), "size": (0.002, 0.016, 0.009), "material": "drawer"}],
             "meshes": [{"name": "dr_mesh", "mesh": "m_drawer_body", "material": "drawer"},
                        {"name": "clip_mesh", "mesh": "m_clip", "material": "clip"}],
             "markers": [{"name": "mk_drawer", "pos": (0.010, -0.012, 0.010), "size": (0.003, 0.0015, 0.003), "material": "mk"}]},
        ],
        "pairs": [("panel_pad", "face_frame")],
        "actuators": [{"name": "drive", "joint": "drawer_slide", "kv": 40.0}],
    }
    xml, meta = CL.build_contact_mjcf(spec, mdir)
    (out / "t2_contact_latched_drawer.xml").write_text(xml)
    meta["init_qpos"] = {"drawer_slide": STROKE_M}          # start OPEN
    model = mj.MjModel.from_xml_path(str(out / "t2_contact_latched_drawer.xml"))
    gok, _ = g9_gconv(model)

    # drive the drawer SHUT (−X); the panel×face CONTACT stops it at s≈0 (the closed landing).
    phases = [{"name": "close", "secs": 3.0, "ctrl": {"drive": -0.05}}]
    series, frames, diverged = CL.run(model, meta, phases, {"drawer": "drawer_slide"}, record=True, cam="cutaway")
    final_mm = series["drawer"][-1] * 1000 if series["drawer"] else 99.0
    min_mm = min(series["drawer"]) * 1000 if series["drawer"] else 99.0

    criteria = [
        {"name": "panel lands on the face frame (closed, s≈0)", "observable": "drawer", "agg": "final",
         "op": "~", "threshold": 0.0, "tol": 0.6},
        {"name": "no drive-through of the closed stop (s ≥ 0)", "observable": "drawer", "agg": "min",
         "op": ">=", "threshold": -0.6},
    ]
    crit = CL.judge(series, diverged, criteria)
    passed = all(c["pass"] for c in crit.values())

    if frames:
        vid = []
        for img, t, ph, obs, ncon in frames:
            s_mm = obs["drawer"] * 1000
            tag = "STOP: panel on FACE FRAME (closed landing)" if (ncon > 0 and s_mm < 1.5) else "CLOSE — sliding shut"
            vid.append(_hud(img, [f"CONTACT LAYER  latched_drawer  closed stop = panel-on-face CONTACT (R5)  [4x slow]",
                                  f"t {t:4.2f}s   drawer {s_mm:5.2f} mm   contacts={ncon}",
                                  tag,
                                  "the face-frame PART carries the closed limit — drawer-slide range widened (limited=false)"],
                            [(255, 255, 255), (150, 220, 255), (150, 255, 180) if ncon > 0 else (200, 220, 255), (200, 200, 200)]))
        imageio.mimsave(out / "t2_contact_latched_drawer.mp4", vid, fps=CL.OUT_FPS, macro_block_size=1)

    cmap = CL.print_contact_map(SCHEDULE["latched_drawer"])
    result = {"decision_row": "D-M19-3 CONTACT LAYER — latched_drawer closed landing by real contact",
              "compile_hash": _hash(), "task": "latched_drawer", "R5_preset": meta["R5_preset"],
              "limit_carriers": [{"contact_pair": "panel×face_frame", "was": "drawer_slide range lower bound 0",
                                  "now": "face-frame CONTACT (drawer_slide limited=false)"}],
              "contact_map": cmap,
              "closed_landing": {"final_mm": round(final_mm, 2), "min_mm": round(min_mm, 2), "target_mm": 0.0},
              "g9_gconv": bool(gok), "criteria": crit, "passed": bool(passed and gok)}
    (out / "t2_contact_latched_drawer_verdict.json").write_text(json.dumps(result, indent=2))
    print("\n".join(cmap))
    print(f"\n=== CONTACT LAYER · latched_drawer ===  G-CONV {'ok' if gok else 'FAIL'}")
    print(f"   driven shut → panel lands on the face frame at {final_mm:.2f} mm (target 0); face PART carries the stop")
    for name, c in crit.items():
        print(f"   {'ok  ' if c['pass'] else 'FAIL'} {name:<48s} {c['value']}")
    print(f"   => {'PASS' if result['passed'] else 'FAIL'}   wrote {out/'t2_contact_latched_drawer_verdict.json'}")


if __name__ == "__main__":
    main()
