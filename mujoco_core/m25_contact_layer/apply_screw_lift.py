"""m25 — CONTACT LAYER applied to screw_lift (§14 T3c stops verified by ACTUAL CONTACT, D-M19-3).

The class-② LIMIT carriers get real contact on the frozen R5 preset: the platform's stop faces collide
with the base's TOP collar (thread-runout shoulder) and BOTTOM stop. The declared nut-slide RANGE that
silently stood in for the stroke is WIDENED (limited=false) so the PART does the stopping — recorded per
joint. The coupling chain (crank→screw→nut) is inherited (m22 P-LIFT 5/5); here we OVERCRANK and the
collar contact carries the limit (subsumes the m22 overcrank probe). Judgement: IR criteria + guards.

  export MUJOCO_GL=egl ; ./bin/py m25_contact_layer/apply_screw_lift.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "m0"))
sys.path.insert(0, str(ROOT / "m22_composition")); sys.path.insert(0, str(ROOT / "m25_contact_layer"))
sys.path.insert(0, str(ROOT / "m24_design_closure"))

import imageio.v2 as imageio  # noqa: E402
import mujoco as mj  # noqa: E402
import numpy as np  # noqa: E402

from knowledge.cards.base import CARD_REGISTRY  # noqa: E402
from tasks.build_goldens import screw_lift  # noqa: E402
from verify import contact_layer as CL  # noqa: E402
from verify.t2_physics.runner import _hash, g9_gconv  # noqa: E402
from contact_schedule import SCHEDULE  # noqa: E402
from step2mjcf import MM  # noqa: E402

import p_lift_mesh as PLM  # noqa: E402  (reuse the compiled meshes + inertials)
import p_lift_va as PV  # noqa: E402


def _hud(img, lines, colors):
    from PIL import Image, ImageDraw
    im = Image.fromarray(img.copy()); dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, 480, 14 * len(lines) + 6], fill=(0, 0, 0))
    for i, (t, c) in enumerate(zip(lines, colors)):
        dr.text((5, 3 + 14 * i), t, fill=c)
    return np.asarray(im)


def main():
    out = ROOT / "m25_contact_layer" / "out"; out.mkdir(parents=True, exist_ok=True)
    plan = screw_lift()
    for e in plan.elements:
        e.params = CARD_REGISTRY[e.card_ref].resolve_params(plan, e)

    # meshes + inertials from the verified m22 rig (the physics is inherited; we only add contact stops)
    prim_xml, _ = PV.build_lift_mjcf(plan, out / "_prim_assets")
    (out / "_prim.xml").write_text(prim_xml)
    prim = mj.MjModel.from_xml_path(str(out / "_prim.xml"))
    mpaths, g = PLM._meshes(plan, out / "sl_assets")
    lead_m = g.lead * MM
    poly = lead_m / (2 * math.pi)
    stroke_m = g.stroke * MM                       # 0.040
    z_rest_top = 0.040                             # platform block top AT REST (s=0), compiled
    z_rest_bot = 0.022                             # platform boss bottom at s=0, compiled
    z_full_top = z_rest_top + stroke_m             # 0.080 — block top at FULL stroke (where the collar is)

    def inertial(bn):
        bi = mj.mj_name2id(prim, mj.mjtObj.mjOBJ_BODY, bn)
        return {"mass": float(prim.body_mass[bi]), "pos": tuple(prim.body_ipos[bi]), "diag": tuple(prim.body_inertia[bi])}

    T_friction = float(prim.dof_frictionloss[prim.jnt_dofadr[mj.mj_name2id(prim, mj.mjtObj.mjOBJ_JOINT, "screw_hinge")]])

    # ---- the spec: full declared chain, nut slide WIDENED (limited=false → contact carries the limit) ----
    spec = {
        "model": "contact_screw_lift", "gravity": (0, 0, -9.81),
        "materials": [{"name": "base", "rgba": "0.62 0.66 0.72 1"}, {"name": "screw", "rgba": "0.95 0.62 0.25 1"},
                      {"name": "nut", "rgba": "0.45 0.78 0.5 1"}, {"name": "crank", "rgba": "0.85 0.35 0.35 1"},
                      {"name": "stop", "rgba": "0.90 0.20 0.20 1"}, {"name": "mk", "rgba": "0.10 0.55 0.95 1"}],
        "meshes_assets": [{"name": f"m_{k}", "file": v.name} for k, v in mpaths.items()],
        "cameras": [{"name": "side", "pos": "0.19 -0.24 0.055", "xyaxes": "0.78 0.62 0 -0.14 0.18 0.98"}],
        # base + screw + crank are STATIC visual context here (the coupling chain is inherited, m22 P-LIFT
        # 5/5); the contact layer verifies the STOPS, so the platform is driven directly on the R5 clock
        # (the rigid coupling equalities need dt 1e-4, D-M19-2, which fights the R5 contact preset).
        "world_meshes": [{"name": "frame_mesh", "mesh": "m_base", "material": "base"},
                         {"name": "screw_mesh", "mesh": "m_screw", "material": "screw"},
                         {"name": "crank_mesh", "mesh": "m_crank", "material": "crank"}],
        # world STOP pads (the carriers): TOP collar (bottom face at z_full_top) the platform lands
        # UNDER at full stroke; BOTTOM stop (top face just below the rest boss) it lands ON at s=0.
        "world_pads": [
            {"name": "top_collar", "pos": (0, 0, z_full_top + 0.0025), "size": (0.012, 0.008, 0.0025), "material": "stop"},
            {"name": "bottom_stop", "pos": (0, 0, z_rest_bot - 0.0030), "size": (0.012, 0.008, 0.0025), "material": "stop"},
        ],
        "bodies": [
            {"name": "nut", "inertial": inertial("nut"),
             # the slide LIMIT is now the CONTACT, not the joint range (limited=false) — the honest widen.
             "joints": [{"name": "nut_slide", "type": "slide", "axis": (0, 0, 1), "damping": 0.5}],
             # pads at the platform's REST block-top / boss-bottom; they rise/fall with the platform.
             "pads": [{"name": "nut_top", "pos": (0, 0, z_rest_top - 0.0025), "size": (0.010, 0.008, 0.0025), "material": "nut"},
                      {"name": "nut_bot", "pos": (0, 0, z_rest_bot + 0.0025), "size": (0.010, 0.008, 0.0025), "material": "nut"}],
             "meshes": [{"name": "nut_mesh", "mesh": "m_nut", "material": "nut"}],
             "markers": [{"name": "mk_nut", "pos": (0.024, 0, z_rest_top - 0.003), "size": (0.002, 0.0025, 0.003), "material": "mk"}]},
        ],
        "pairs": [("nut_top", "top_collar"), ("nut_bot", "bottom_stop")],
        "actuators": [{"name": "drive", "joint": "nut_slide", "kv": 100.0}],
    }
    xml, meta = CL.build_contact_mjcf(spec, out / "sl_assets")
    (out / "t2_contact_screw_lift.xml").write_text(xml)
    model = mj.MjModel.from_xml_path(str(out / "t2_contact_screw_lift.xml"))
    gok, _ = g9_gconv(model)

    # OVERCRANK the platform UP past full stroke (target 80 mm-worth of drive); the TOP collar CONTACT
    # must stop it at ~40 mm (the carrier), not the drive. Then drive it DOWN; the BOTTOM stop catches
    # it at s=0 (the base landing). Both stops are PARTS on the R5 preset. (The self-lock HOLD is a
    # separate mechanism — physics, m19 — not re-tested here; the coupling chain is inherited, m22.)
    phases = [{"name": "overcrank_up", "secs": 3.5, "ctrl": {"drive": 0.02}},
              {"name": "land_bottom", "secs": 3.0, "ctrl": {"drive": -0.02}}]
    series, frames, diverged = CL.run(model, meta, phases, {"nut": "nut_slide"}, record=True, cam="side")
    peak_mm = max(series["nut"]) * 1000 if series["nut"] else 0.0
    bot_mm = min(series["nut"]) * 1000 if series["nut"] else 0.0

    criteria = [
        {"name": "TOP collar stops the platform (thread runout, ~stroke)", "observable": "nut", "agg": "peak",
         "op": "~", "threshold": g.stroke, "tol": 1.0},
        {"name": "no overrun of the TOP stop under overcrank", "observable": "nut", "agg": "peak",
         "op": "<=", "threshold": g.stroke + 1.0},
        {"name": "BOTTOM stop lands the platform (s=0, no fall-through)", "observable": "nut", "agg": "min",
         "op": ">=", "threshold": -0.6},
    ]
    crit = CL.judge(series, diverged, criteria)
    passed = all(c["pass"] for c in crit.values())

    # video: the landing moments, HUD names the CARRIER
    if frames:
        vid = []
        for img, t, ph, obs, ncon in frames:
            nut_mm = obs["nut"] * 1000
            if ph == "overcrank_up":
                tag = ("STOP: TOP collar contact (thread runout)" if (ncon > 0 and nut_mm > 38)
                       else "OVERCRANK — driving the platform up past target")
            else:
                tag = ("STOP: BOTTOM base landing (s=0)" if (ncon > 0 and nut_mm < 1.0)
                       else "lowering to the base landing")
            vid.append(_hud(img, [f"CONTACT LAYER  screw_lift  stops = REAL CONTACT (frozen R5 preset)  [4x slow]",
                                  f"t {t:4.2f}s   platform {nut_mm:5.2f} mm   contacts={ncon}",
                                  tag,
                                  "the collar/base PARTS carry the limits — nut-slide range widened (limited=false)"],
                            [(255, 255, 255), (150, 220, 255), (255, 210, 120) if ncon > 0 else (150, 255, 180), (200, 200, 200)]))
        imageio.mimsave(out / "t2_contact_screw_lift.mp4", vid, fps=CL.OUT_FPS, macro_block_size=1)

    cmap = CL.print_contact_map(SCHEDULE["screw_lift"])
    result = {"decision_row": "D-M19-3 CONTACT LAYER — screw_lift stops by real contact",
              "compile_hash": _hash(), "task": "screw_lift", "R5_preset": meta["R5_preset"],
              "limit_carriers": [
                  {"contact_pair": "platform×top_collar", "was": "nut_slide range [0,0.040]",
                   "now": "collar CONTACT (nut_slide limited=false)"},
                  {"contact_pair": "platform×bottom_stop", "was": "nut_slide range lower bound 0",
                   "now": "base-stop CONTACT (nut_slide limited=false)"}],
              "contact_map": cmap,
              "overcrank": {"platform_peak_mm": round(peak_mm, 2), "platform_bottom_mm": round(bot_mm, 2),
                            "target_mm": g.stroke, "note": "subsumes the m22 overcrank probe: driven past target, the collar stops it; then lowered to the base landing"},
              "g9_gconv": bool(gok), "criteria": crit, "passed": bool(passed and gok)}
    (out / "t2_contact_screw_lift_verdict.json").write_text(json.dumps(result, indent=2))
    print("\n".join(cmap))
    print(f"\n=== CONTACT LAYER · screw_lift ===  G-CONV {'ok' if gok else 'FAIL'}")
    print(f"   overcrank UP: platform peak {peak_mm:.2f} mm (target {g.stroke}) — TOP collar stops it; "
          f"then DOWN: bottom {bot_mm:.2f} mm — BASE landing")
    for name, c in crit.items():
        print(f"   {'ok  ' if c['pass'] else 'FAIL'} {name:<52s} {c['value']}")
    print(f"   => {'PASS' if result['passed'] else 'FAIL'}   wrote {out/'t2_contact_screw_lift_verdict.json'}")


if __name__ == "__main__":
    main()
