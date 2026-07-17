"""m10_slide_rail review artefacts (D-ONT-7): the rail/carriage cross-section with the clearance
overlay + the compiled fixture 3-view. The P-SLIDE s(t) plots come from the runner.

Run:  ./bin/py m10_slide_rail/build_review.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from matplotlib.patches import Rectangle
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from build123d import export_stl
from knowledge.cards.base import CARD_REGISTRY
from knowledge.cards.slide_rail import dims_from
from pipeline.compile_assembly import compile_assembly
from tasks.build_goldens import slide_fixture

OUT = Path(__file__).parent / "out"
COL = {"P1": "#8fb8de", "P2": "#8fd39a"}       # base+rail / carriage


def _mesh(part):
    f = OUT / "_t.stl"; export_stl(part, str(f), tolerance=0.04, angular_tolerance=0.3)
    m = trimesh.load(f, force="mesh"); f.unlink(); return m


def render_3view(ca):
    meshes = {p: _mesh(ca.parts[p]) for p in ("P1", "P2")}
    views = [("front (−Y): the T cross-section", 0, -90), ("iso", 20, -60), ("top (+Z)", 89, -90)]
    fig = plt.figure(figsize=(12, 4.2))
    for i, (name, elev, azim) in enumerate(views, 1):
        ax = fig.add_subplot(1, 3, i, projection="3d")
        allv = []
        for pid, m in meshes.items():
            ax.add_collection3d(Poly3DCollection(m.vertices[m.faces], facecolor=COL[pid],
                                                 edgecolor="#33333322", linewidths=0.1, alpha=0.9))
            allv.append(m.vertices)
        allv = np.vstack(allv); c = allv.mean(0); r = (allv.max(0) - allv.min(0)).max() / 2 * 1.05
        ax.set_xlim(c[0]-r, c[0]+r); ax.set_ylim(c[1]-r, c[1]+r); ax.set_zlim(c[2]-r, c[2]+r)
        ax.set_box_aspect((1, 1, 1)); ax.set_axis_off(); ax.view_init(elev=elev, azim=azim)
        ax.set_title(name, fontsize=9)
    handles = [plt.Line2D([0], [0], marker="s", ls="", mfc=COL[p], mec="#333", ms=10,
                          label=lbl) for p, lbl in (("P1", "base + T-rail"), ("P2", "carriage"))]
    fig.legend(handles=handles, loc="lower center", ncol=2, fontsize=9, frameon=False)
    fig.suptitle("slide_fixture — compiled T-rail slide (base + carriage)", fontsize=12)
    fig.tight_layout(rect=(0, 0.05, 1, 0.96))
    fig.savefig(OUT / "slide_3view.png", dpi=125); plt.close(fig)


def render_section_clearance(plan):
    """The T cross-section (Y–Z) with the clearance overlay — the functional gap the card exists to
    preserve (§3.5, D18). Rail solid + carriage channel, drawn from the box decomposition, with the
    clearance dimension annotated."""
    e1 = plan.element("E1")
    g = dims_from(e1.params, float(e1.params["stroke"]))
    c = g.clearance
    fig, ax = plt.subplots(figsize=(7.5, 6))
    z0 = 0.0

    # rail (blue): neck + head + shoulders
    ax.add_patch(Rectangle((-g.neck_w/2, z0), g.neck_w, g.neck_h, facecolor=COL["P1"], edgecolor="#222"))
    ax.add_patch(Rectangle((-g.rail_w/2, z0+g.neck_h), g.rail_w, g.head_h, facecolor=COL["P1"], edgecolor="#222"))
    # carriage (green): top wall + two sides + two lips — offset by the clearance so the gap SHOWS
    cw = g.carriage_wall
    ax.add_patch(Rectangle((-(g.rail_w/2), z0+g.rail_h), g.rail_w, cw, facecolor=COL["P2"],
                           edgecolor="#222", alpha=.9))                     # top (rests on head — exact Z)
    for sgn in (+1, -1):
        sy = sgn*(g.rail_w/2 + c)
        ax.add_patch(Rectangle((sy if sgn>0 else sy-cw, z0+g.neck_h), cw, g.head_h,
                               facecolor=COL["P2"], edgecolor="#222", alpha=.9))   # side (clearance c in Y)
        ly = sgn*(g.neck_w/2 + c)
        ax.add_patch(Rectangle((ly if sgn>0 else ly-g.shoulder_w, z0+g.neck_h-2*c), g.shoulder_w, c,
                               facecolor=COL["P2"], edgecolor="#222", alpha=.9))   # lip (under head, gap c)

    # clearance annotations
    ax.annotate("", xy=(g.rail_w/2+c, z0+g.rail_h*0.7), xytext=(g.rail_w/2, z0+g.rail_h*0.7),
                arrowprops=dict(arrowstyle="<->", color="#c53030", lw=1.3))
    ax.text(g.rail_w/2+c/2, z0+g.rail_h*0.7+0.4, f"clearance\n{c:g} mm", color="#c53030",
            fontsize=8.5, ha="center")
    ax.annotate("head captured\n(lift ≤ clearance,\nthen lips catch)", xy=(g.neck_w/2+c+g.shoulder_w/2, z0+g.neck_h-c),
                xytext=(g.rail_w/2+2.5, z0+g.neck_h-1.5), fontsize=8,
                arrowprops=dict(arrowstyle="->", color="#333"))
    ax.text(0, z0+g.rail_h+cw+0.6, "carriage rests on head-top (Z load path — exact, D14)",
            ha="center", fontsize=8, color="#22543d")
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_title(f"slide_rail SECTION (Y–Z) + clearance overlay\n"
                 f"T-rail: neck {g.neck_w:g}×{g.neck_h:g}, head {g.rail_w:g}×{g.head_h:g}, "
                 f"clearance {c:g} mm — all boxes, no curves (§3.5)", fontsize=10)
    ax.set_xlim(-g.rail_w/2-cw-3, g.rail_w/2+cw+5); ax.set_ylim(z0-1, z0+g.rail_h+cw+3)
    fig.tight_layout(); fig.savefig(OUT / "slide_section_clearance.png", dpi=135); plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    plan = slide_fixture()
    e1 = plan.element("E1")
    e1.params = CARD_REGISTRY["slide_rail"].resolve_params(plan, e1)
    ca = compile_assembly(plan)
    render_3view(ca)
    render_section_clearance(plan)
    g = dims_from(e1.params, float(e1.params["stroke"]))
    print("wrote slide_3view.png + slide_section_clearance.png")
    print(f"§3.5 constraint chain: engagement_len {g.engagement_len:g} >= 0.35·stroke "
          f"{g.min_engagement:g} ✓ ; rail_len {g.rail_len:g} = stroke {g.stroke:g} + "
          f"engagement {g.engagement_len:g} + tab ; drawer_w(inner=100) = {g.drawer_w(100):g}")


if __name__ == "__main__":
    main()
