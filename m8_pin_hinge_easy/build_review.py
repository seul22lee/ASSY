"""Generate the m8_pin_hinge_easy review artifacts (D-ONT-7): the compiled Easy anchor rendered
four ways + exploded + one SECTION that catches the hinge (rear) and the latch (front) in a single
cut, the IR graph (P3 hardware + two AssemblyRule nodes), the t0 AssemblyRule results, and the
report.html. The physics (t2 V-A/V-B) + t1 verdicts are read from verify/t2_physics/out_easy.

Run:  ./bin/py m8_pin_hinge_easy/build_review.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from build123d import Align, Box, Location, export_stl
from tasks.build_goldens import anchor_easy
from pipeline.compile_assembly import compile_assembly
from verify.assembly_rules import evaluate
from viz.ir_graph import to_svg

OUT = Path(__file__).parent / "out"
COL = {"P1": "#8fb8de", "P2": "#8fd39a", "P3": "#e8b24a"}   # box / lid / pin(hardware)
LABEL = {"P1": "box (base)", "P2": "lid (mover)", "P3": "pin (hardware ← E1)"}


def _mesh(part):
    f = OUT / "_t.stl"
    export_stl(part, str(f), tolerance=0.04, angular_tolerance=0.3)
    m = trimesh.load(f, force="mesh"); f.unlink()
    return m


def _draw(ax, meshes, alpha=0.92, edge="#33333322"):
    allv = []
    for pid, m in meshes.items():
        ax.add_collection3d(Poly3DCollection(m.vertices[m.faces], facecolor=COL[pid],
                                             edgecolor=edge, linewidths=0.15, alpha=alpha))
        allv.append(m.vertices)
    allv = np.vstack(allv); c = allv.mean(0)
    r = (allv.max(0) - allv.min(0)).max() / 2 * 1.05
    ax.set_xlim(c[0]-r, c[0]+r); ax.set_ylim(c[1]-r, c[1]+r); ax.set_zlim(c[2]-r, c[2]+r)
    ax.set_box_aspect((1, 1, 1)); ax.set_axis_off()


def render_four_view(meshes):
    views = [("front (−Y)", 0, -90), ("right (+X)", 0, 0), ("top (+Z)", 89, -90), ("iso", 22, -58)]
    fig = plt.figure(figsize=(10, 9))
    for i, (name, elev, azim) in enumerate(views, 1):
        ax = fig.add_subplot(2, 2, i, projection="3d")
        _draw(ax, meshes); ax.view_init(elev=elev, azim=azim)
        ax.set_title(name, fontsize=10)
    handles = [plt.Line2D([0], [0], marker="s", ls="", mfc=COL[p], mec="#333", ms=10,
                          label=LABEL[p]) for p in ("P1", "P2", "P3")]
    fig.legend(handles=handles, loc="lower center", ncol=3, fontsize=9, frameon=False)
    fig.suptitle("Easy anchor — compiled assembly (box + lid + loose pin), 4 views", fontsize=12)
    fig.tight_layout(rect=(0, 0.03, 1, 0.97))
    fig.savefig(OUT / "anchor_4view.png", dpi=125); plt.close(fig)


def render_exploded(parts):
    # separate along +Z (lid up, pin further up-and-back so it reads as its own body)
    ex = {"P1": parts["P1"],
          "P2": Location((0, 0, 55)) * parts["P2"],
          "P3": Location((0, -18, 95)) * parts["P3"]}
    meshes = {p: _mesh(s) for p, s in ex.items()}
    fig = plt.figure(figsize=(7, 7.5)); ax = fig.add_subplot(111, projection="3d")
    _draw(ax, meshes, alpha=0.95); ax.view_init(elev=18, azim=-60)
    ax.set_title("Exploded — the pin (orange) is a separate hardware body,\nprovided by the hinge "
                 "element E1 (D-ONT-11)", fontsize=10)
    handles = [plt.Line2D([0], [0], marker="s", ls="", mfc=COL[p], mec="#333", ms=10,
                          label=LABEL[p]) for p in ("P1", "P2", "P3")]
    fig.legend(handles=handles, loc="lower center", ncol=3, fontsize=9, frameon=False)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / "anchor_exploded.png", dpi=125); plt.close(fig)


def render_section(parts, meshes):
    """A true YZ cross-section at x=0 (2D). The cut plane passes through the centre hinge knuckle
    (rear, −Y) AND the single front latch (front, +Y), so the hinge/pin-bore engagement and the
    snap latch seated in its catch window show in the SAME section. Rendered as filled cross-section
    polygons via trimesh's plane section — a real engineering section, not a 3D view of a cut half."""
    fig, ax = plt.subplots(figsize=(9, 5.2))
    # map the x=0 plane to screen with world Y → horizontal, world Z → vertical (so rear/front and
    # up read correctly, instead of trimesh's arbitrary in-plane frame). (x,y,z) → (y,z,x).
    to_2D = np.array([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0], [0, 0, 0, 1.0]])
    for p in ("P1", "P2", "P3"):
        sec = meshes[p].section(plane_origin=[0, 0, 0], plane_normal=[1, 0, 0])
        if sec is None:
            continue
        planar, _ = sec.to_planar(to_2D=to_2D)
        for poly in planar.polygons_full:
            xs, ys = poly.exterior.xy
            ax.fill(np.asarray(xs), np.asarray(ys), facecolor=COL[p], edgecolor="#222",
                    linewidth=0.8, alpha=0.92, zorder={"P1": 1, "P2": 2, "P3": 3}[p])
            for hole in poly.interiors:
                hx, hy = hole.xy
                ax.fill(np.asarray(hx), np.asarray(hy), facecolor="white", edgecolor="#222",
                        linewidth=0.6, zorder={"P1": 1, "P2": 2, "P3": 3}[p] + 0.1)
    ax.set_aspect("equal"); ax.axis("off")
    ax.annotate("hinge knuckle + pin/bore\n(rear, −Y)", xy=(0.13, 0.62), xycoords="axes fraction",
                fontsize=8.5, ha="center", color="#333")
    ax.annotate("snap latch in\ncatch window\n(front, +Y)", xy=(0.86, 0.55), xycoords="axes fraction",
                fontsize=8.5, ha="center", color="#333")
    handles = [plt.Line2D([0], [0], marker="s", ls="", mfc=COL[p], mec="#333", ms=10,
                          label=LABEL[p]) for p in ("P1", "P2", "P3")]
    ax.legend(handles=handles, loc="lower center", ncol=3, fontsize=9, frameon=False,
              bbox_to_anchor=(0.5, -0.08))
    ax.set_title("SECTION at x=0 — hinge (rear) and latch (front) in one cut", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT / "anchor_section.png", dpi=135); plt.close(fig)


def render_ir(plan, nostop_plan=None):
    """ir_easy.svg = the BENCHMARK golden (stop: F1 + B3). ir_easy_nostop.svg = the D20 demo."""
    from verify.t2_physics.runner import _hash
    h = _hash()
    (OUT / "ir_easy.svg").write_text(
        to_svg(plan, title=f"anchor_easy — BENCHMARK IR: F1 stop_flange + B3 limit  (compile {h})"))
    if nostop_plan is not None:
        (OUT / "ir_easy_nostop.svg").write_text(to_svg(
            nostop_plan, title=f"anchor_easy [nostop] — D20 demo IR: no F1/B3  (compile {h})"))


def eval_ars(plan, ca):
    compiled = {"parts": ca.parts, "E2": {"_latch": ca.tags["E2"]["hook_front_edge_underside"]}}
    rows = [evaluate(plan, ar, compiled, ca.axes["E1"]) for ar in plan.assembly_rules]
    (OUT / "t0_assembly_rules.json").write_text(json.dumps(rows, indent=2))
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    plan = anchor_easy()
    ca = compile_assembly(plan)
    meshes = {p: _mesh(ca.parts[p]) for p in ("P1", "P2", "P3")}
    render_four_view(meshes)
    render_exploded(ca.parts)
    render_section(ca.parts, meshes)
    render_ir(plan, anchor_easy("nostop"))
    ars = eval_ars(plan, ca)
    print("wrote renders + ir_easy.svg + t0_assembly_rules.json")
    for r in ars:
        print(f"  {r['id']} {r['kind']:9s} {'PASS' if r['ok'] else 'FAIL'}  {r['detail']}")


if __name__ == "__main__":
    main()
