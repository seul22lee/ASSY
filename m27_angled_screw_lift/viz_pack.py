"""m27 (§14 T5v, D-M24-8) — angled_screw_lift reviewer visualization pack. The ENGAGEMENT is the CROSS
hidden in the yokes, so per D-M24-8 it ships a STATIC section (yoke-bore fits annotated) + an ANIMATED
cutaway (the m21 rig's TRANSPARENT yokes show the cross gimbaling — t2_alift_ujoint.mp4) + the
platform-velocity overlay plot. Plus the compiled-assembly section, exploded, portrait, IR svg.

  export MUJOCO_GL=egl ; ./bin/py m27_angled_screw_lift/viz_pack.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "m0"))
sys.path.insert(0, str(ROOT / "m21_universal_joint"))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import mujoco as mj  # noqa: E402
from PIL import Image  # noqa: E402

from knowledge.cards.base import CARD_REGISTRY  # noqa: E402
from pipeline.compile_assembly import compile_assembly  # noqa: E402
from tasks.build_goldens import angled_screw_lift  # noqa: E402
from verify.t2_physics.mjcf import _to_trimesh  # noqa: E402
import p_ujoint_va as UJ  # noqa: E402

MM = 1000.0
COL = {"P1": "#9aa4b0", "P2": "#5fb87f", "P3": "#d05a5a"}
LABEL = {"P1": "base+screw+columns+angled boss", "P2": "platform/nut", "P3": "crank (β=30°)+input yoke"}


def _meshes(out):
    plan = angled_screw_lift()
    for e in plan.elements:
        e.params = CARD_REGISTRY[e.card_ref].resolve_params(plan, e)
    ca = compile_assembly(plan)
    tmp = out / "vizassets"; tmp.mkdir(parents=True, exist_ok=True)
    return {pid: _to_trimesh(part, tmp / f"{pid}.stl") for pid, part in ca.parts.items()}


def _sect(ax, meshes, yc, offy=None):
    for pid, m in meshes.items():
        sec = m.section(plane_origin=(0, yc / MM, 0), plane_normal=(0, 1, 0))
        if sec is None:
            continue
        for e in sec.discrete:
            p = np.array(e) * MM
            dz = (offy.get(pid, 0) if offy else 0)
            ax.fill(p[:, 0], p[:, 2] + dz, color=COL[pid], alpha=0.6, ec=COL[pid], lw=1.0, label=LABEL[pid])


def main():
    out = ROOT / "m27_angled_screw_lift" / "out"
    meshes = _meshes(out)

    # ASSEMBLY SECTION (y=0): the angled jack — base, screw, columns, platform, angled boss + crank at 30°
    fig, ax = plt.subplots(figsize=(7.2, 8.0))
    _sect(ax, meshes, 0.0)
    ax.annotate("crank comes out at β=30°\n(angled bearing boss carries it)", xy=(-10, -19), xytext=(-32, -30),
                fontsize=7.5, arrowprops=dict(arrowstyle="->", color="#8a6d0b", lw=1),
                bbox=dict(boxstyle="round,pad=0.25", fc="#fffbe6", ec="#b8860b", lw=0.8))
    ax.annotate("u-joint cross centre\n(axis intersection, derived)", xy=(0, -2), xytext=(14, 8),
                fontsize=7.5, arrowprops=dict(arrowstyle="->", color="#555", lw=1))
    ax.set_aspect("equal"); ax.set_title("angled_screw_lift — y=0 section: the angled-drive jack", fontsize=9)
    ax.set_xlabel("x (mm)"); ax.set_ylabel("z (mm)"); ax.grid(alpha=0.2)
    h, l = ax.get_legend_handles_labels(); seen = dict(zip(l, h)); ax.legend(seen.values(), seen.keys(), fontsize=7, loc="upper right")
    fig.tight_layout(); fig.savefig(out / "section_angled_screw_lift.png", dpi=140); plt.close(fig)

    # EXPLODED (pieces along +Z)
    fig, ax = plt.subplots(figsize=(6.6, 8.4))
    _sect(ax, meshes, 0.0, offy={"P1": 0, "P2": 60, "P3": -55})
    ax.set_aspect("equal"); ax.set_title("angled_screw_lift — exploded (P1 base / P2 platform / P3 crank)", fontsize=9)
    ax.set_xlabel("x (mm)"); ax.set_ylabel("z (mm, exploded)"); ax.grid(alpha=0.2)
    h, l = ax.get_legend_handles_labels(); seen = dict(zip(l, h)); ax.legend(seen.values(), seen.keys(), fontsize=7, loc="upper right")
    fig.tight_layout(); fig.savefig(out / "exploded_angled_screw_lift.png", dpi=140); plt.close(fig)

    # STATIC CROSS SECTION (D-M24-8): a schematic of the cross-in-yokes at the engaged pose, yoke-bore
    # fit annotated (the engagement is a pin-in-bore overlap invisible from outside).
    fig, ax = plt.subplots(figsize=(6.4, 5.2))
    # input yoke prongs (±X), output yoke prongs (±Y→ shown as depth), cross trunnions
    for sx in (-1, 1):                                  # input-yoke prongs (gold)
        ax.add_patch(plt.Rectangle((sx * 6.0 - 1.5, -5), 3, 10, fc="#f0b040", ec="#b8860b", alpha=0.5))
    ax.add_patch(plt.Rectangle((-6, -1.6), 12, 3.2, fc="#e8a020", ec="#a06000", alpha=0.9))  # trunnion X (cross)
    ax.add_patch(plt.Circle((0, 0), 2.6, fc="#f0f0f0", ec="#444"))                            # cross hub
    ax.annotate("yoke bore ⌀3.90  /  cross trunnion ⌀3.20\n→ 0.35 mm pin-in-bore fit (A-PETG-1; M2/M3)",
                xy=(6, 0), xytext=(-6, 8), fontsize=8, ha="left",
                bbox=dict(boxstyle="round,pad=0.3", fc="#fffbe6", ec="#b8860b", lw=0.8),
                arrowprops=dict(arrowstyle="->", color="#8a6d0b", lw=1))
    ax.set_xlim(-12, 12); ax.set_ylim(-9, 13); ax.set_aspect("equal"); ax.grid(alpha=0.2)
    ax.set_title("angled_screw_lift — CROSS-in-YOKES (engaged, D-M24-8): the pin-in-bore fit", fontsize=9)
    ax.set_xlabel("mm"); ax.set_ylabel("mm")
    fig.tight_layout(); fig.savefig(out / "cross_section_angled_screw_lift.png", dpi=140); plt.close(fig)

    # PORTRAIT + a live cross still from the u-joint rig (transparent yokes → the cutaway)
    plan = angled_screw_lift()
    for e in plan.elements:
        e.params = CARD_REGISTRY[e.card_ref].resolve_params(plan, e)
    xml, meta = UJ.build_va_mjcf(plan, out / "vizassets", beta_deg=30.0)
    m = mj.MjModel.from_xml_string(xml); d = mj.MjData(m)
    ji = m.jnt_qposadr[mj.mj_name2id(m, mj.mjtObj.mjOBJ_JOINT, "jin")]
    d.qpos[ji] = math.radians(45); mj.mj_forward(m, d)
    R = mj.Renderer(m, 640, 640)
    cam = mj.mj_name2id(m, mj.mjtObj.mjOBJ_CAMERA, "iso45")
    R.update_scene(d, camera=cam); Image.fromarray(R.render()).save(out / "portrait_ujoint_cutaway.png"); R.close()
    print("wrote section_angled_screw_lift.png, exploded_angled_screw_lift.png, "
          "cross_section_angled_screw_lift.png, portrait_ujoint_cutaway.png")


if __name__ == "__main__":
    main()
