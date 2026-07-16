"""Generate the m4_templates review artifacts (D-ONT-7) for the snap-box compile.

Compiles T-S1 (box_shell + lid_panel templates + snap_hook carve), checks G6-d determinism, and
renders into m4_templates/out/:
  views_{front,top,right,iso}.png   4 orthographic-ish views of the assembly
  exploded.png                      lid lifted to reveal hooks + windows
  anchors.png                       assembly + declared anchors (dots + normals + labels)
  s6_hook_closeup.png               hook/catch XZ section with y/h/L/α dimension overlays (§6)
  determinism.txt                   STEP hashes, compiled twice

Pure-matplotlib rendering (no EGL/`dot`, per the standing constraint). Run:
  ./bin/py m4_templates/build_review.py
"""

from __future__ import annotations

import hashlib
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from build123d import export_step, export_stl
from knowledge.cards.snap_hook_geometry import CLEARANCE, GEOM_DEFAULTS, build_hook, carve
from knowledge.templates import box_shell, lid_panel
from tasks.build_goldens import snap_starter

OUT = Path(__file__).parent / "out"
BOX = {"box_l": 80.0, "box_w": 60.0, "box_h": 40.0, "wall": 2.0}
C_BOX, C_LID = "#7fb2e5", "#f6c453"


def compile_ts1():
    pieces = {"P1": box_shell(), "P2": lid_panel()}
    pieces["P1"].params.update(BOX)
    plan = snap_starter()
    inst = plan.element("E1")
    binds = [b for b in plan.bindings if b.element_id == "E1"]
    res = carve(pieces, inst, binds)
    return res, pieces


def step_hashes(parts) -> dict:
    """G6-d: normalized STEP hash (volatile timestamp header stripped)."""
    hashes = {}
    for pid, part in sorted(parts.items()):
        f = OUT / f"{pid}.step"
        export_step(part, str(f))
        txt = open(f).read()
        txt = re.sub(r"FILE_NAME\([^;]*\);", "FILE_NAME(NORM);", txt, flags=re.S)
        txt = re.sub(r"/\* time_stamp \*/ '[^']*'", "TS", txt)
        hashes[pid] = hashlib.sha256(txt.encode()).hexdigest()[:16]
    return hashes


def _mesh(part):
    f = OUT / "_tmp.stl"
    export_stl(part, str(f), tolerance=0.05, angular_tolerance=0.3)
    m = trimesh.load(f, force="mesh")
    f.unlink()
    return m


def _add_mesh(ax, mesh, color, alpha=1.0, dz=0.0):
    tris = mesh.vertices[mesh.faces]
    if dz:
        tris = tris + np.array([0, 0, dz])
    ax.add_collection3d(Poly3DCollection(tris, facecolor=color, edgecolor="#33333322",
                                         linewidths=0.2, alpha=alpha))


def _frame(ax, meshes):
    allv = np.vstack([m.vertices for m in meshes])
    c = allv.mean(0)
    r = (allv.max(0) - allv.min(0)).max() / 2 * 1.05
    ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(c[2] - r, c[2] + r)
    ax.set_box_aspect((1, 1, 1)); ax.set_axis_off()


def render_views(box_m, lid_m):
    cams = {"front": (0, -90), "top": (89, -90), "right": (0, 0), "iso": (24, -58)}
    for name, (elev, azim) in cams.items():
        fig = plt.figure(figsize=(5, 5)); ax = fig.add_subplot(111, projection="3d")
        _add_mesh(ax, box_m, C_BOX); _add_mesh(ax, lid_m, C_LID)
        _frame(ax, [box_m, lid_m]); ax.view_init(elev=elev, azim=azim)
        ax.set_title(f"T-S1 assembly — {name}", fontsize=10)
        fig.tight_layout(); fig.savefig(OUT / f"views_{name}.png", dpi=120); plt.close(fig)


def render_exploded(box_m, lid_m):
    fig = plt.figure(figsize=(6, 6)); ax = fig.add_subplot(111, projection="3d")
    _add_mesh(ax, box_m, C_BOX)
    _add_mesh(ax, lid_m, C_LID, dz=35)   # lift the lid to reveal hooks (below it) + windows
    lifted = lid_m.copy(); lifted.vertices = lifted.vertices + [0, 0, 35]
    _frame(ax, [box_m, lifted]); ax.view_init(elev=20, azim=-60)
    ax.set_title("T-S1 exploded — lid lifted (hooks hang below; windows in the walls)", fontsize=9)
    fig.tight_layout(); fig.savefig(OUT / "exploded.png", dpi=120); plt.close(fig)


def render_anchors(box_m, lid_m, boxes_tr, lid_tr):
    fig = plt.figure(figsize=(7, 6.2)); ax = fig.add_subplot(111, projection="3d")
    # very translucent meshes so the anchor markers read on top (mplot3d has no true depth sort)
    _add_mesh(ax, box_m, C_BOX, alpha=0.14); _add_mesh(ax, lid_m, C_LID, alpha=0.14)
    for tr, col in ((boxes_tr, "#c53030"), (lid_tr, "#1a7f4b")):
        for a in tr.anchors.values():
            p = np.array(a.position); n = np.array(a.normal) * 10
            ax.scatter(*p, color=col, s=70, zorder=10, depthshade=False, edgecolor="k", lw=0.5)
            ax.quiver(*p, *n, color=col, lw=2.2, arrow_length_ratio=0.3, zorder=10)
            lab = p + n * 1.25 + np.array([0, 0, 2])
            ax.text(*lab, a.name, fontsize=8, color=col, zorder=11, weight="bold")
    _frame(ax, [box_m, lid_m]); ax.view_init(elev=26, azim=-52)
    ax.set_title("Declared anchors — red = box_shell (side_wall_*), green = lid_panel "
                 "(rim_underside_*)\ndots = position, arrows = outward normal", fontsize=8)
    fig.tight_layout(); fig.savefig(OUT / "anchors.png", dpi=120); plt.close(fig)


def render_hook_closeup():
    """2D XZ section of the RIGHT hook + wall + window with y/h/L/α dimension overlays (§6)."""
    g = dict(GEOM_DEFAULTS); g["_from_defaults"] = True
    _hook, d, segs, nose = build_hook(1, BOX["box_l"], BOX["wall"], BOX["box_h"], g)
    x_tip, z_tip, h_lead, tip_flat, h_under, protrude = nose
    x_wall_i = BOX["box_l"] / 2 - BOX["wall"]        # 38
    x_wall_o = BOX["box_l"] / 2                       # 40
    x_outer = x_wall_i - CLEARANCE                    # beam outer face

    fig, ax = plt.subplots(figsize=(7.5, 7))
    # wall (with the window gap)
    win_lo, win_hi = z_tip - CLEARANCE, z_tip + 6.0
    ax.add_patch(plt.Rectangle((x_wall_i, 0), BOX["wall"], win_lo, color="#bcd", ec="k"))
    ax.add_patch(plt.Rectangle((x_wall_i, win_hi), BOX["wall"], BOX["box_h"] - win_hi,
                               color="#bcd", ec="k"))
    ax.text(x_wall_i + 1, (win_lo + win_hi) / 2, "catch\nwindow", fontsize=7, ha="center",
            va="center", color="#2b6cb0")
    # beam outline (tapered stack)
    for (cx, h, cz, dz) in segs:
        ax.add_patch(plt.Rectangle((cx - h / 2, cz - dz / 2), h, dz, color=C_LID, ec="#b7791f"))
    # nose polygon
    npts = [(x_outer, z_tip), (x_tip, z_tip + h_lead), (x_tip, z_tip + h_lead + tip_flat),
            (x_outer, z_tip + h_lead + tip_flat + h_under)]
    ax.add_patch(plt.Polygon(npts, closed=True, color="#f6a723", ec="#b7791f"))

    def dim(x0, z0, x1, z1, label, color="#c53030", off=(0, 0)):
        ax.annotate("", (x1, z1), (x0, z0), arrowprops=dict(arrowstyle="<->", color=color, lw=1.3))
        ax.text((x0 + x1) / 2 + off[0], (z0 + z1) / 2 + off[1], label, color=color, fontsize=9,
                ha="center", va="center", bbox=dict(fc="white", ec="none", alpha=.8))

    # L (beam length), h (root thickness), y (undercut protrusion past wall inner face)
    dim(x_outer + 3.5, z_tip, x_outer + 3.5, BOX["box_h"], f"L = {d.L:g} mm", off=(1.2, 0))
    dim(x_outer - d.h_root, BOX["box_h"] - 1.2, x_outer, BOX["box_h"] - 1.2,
        f"h = {d.h_root:g} mm", off=(0, 1.1))
    dim(x_wall_i, z_tip + h_lead - 2, x_tip, z_tip + h_lead - 2, f"y = {d.y:g} mm", off=(0, -1.1))
    # α_in (lead-in ramp) and α_out (undercut) angle labels at the faces
    ax.text(x_tip - 1.2, z_tip + h_lead / 2, f"α_in\n{d.alpha_in:g}°", fontsize=8, color="#2f855a",
            ha="right")
    ax.text(x_outer + 0.4, z_tip + h_lead + tip_flat + h_under / 2, f"α_out\n{d.alpha_out:g}°",
            fontsize=8, color="#2f855a", ha="left")

    ax.axvline(x_wall_i, color="#888", ls=":", lw=0.8)
    ax.set_xlim(x_outer - d.h_root - 3, x_wall_o + 3); ax.set_ylim(z_tip - 4, BOX["box_h"] + 3)
    ax.set_aspect("equal"); ax.set_xlabel("x (mm)"); ax.set_ylabel("z (mm)")
    tag = " (defaults — stage 5 not run)" if d.from_defaults else ""
    ax.set_title(f"s6_hook_closeup — cantilever snap hook XZ section{tag}", fontsize=10)
    ax.grid(alpha=.25)
    fig.tight_layout(); fig.savefig(OUT / "s6_hook_closeup.png", dpi=130); plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    res, pieces = compile_ts1()

    h1 = step_hashes(res.parts)
    res2, _ = compile_ts1()
    h2 = step_hashes(res2.parts)
    det = h1 == h2
    (OUT / "determinism.txt").write_text(
        f"G6-d determinism (normalized STEP hash, compiled twice)\ncompile 1: {h1}\n"
        f"compile 2: {h2}\nIDENTICAL: {det}\n")

    box_m, lid_m = _mesh(res.parts["P1"]), _mesh(res.parts["P2"])
    render_views(box_m, lid_m)
    render_exploded(box_m, lid_m)
    render_anchors(box_m, lid_m, pieces["P1"], pieces["P2"])
    render_hook_closeup()

    print("  views_{front,top,right,iso}.png · exploded.png · anchors.png · s6_hook_closeup.png")
    print(f"  determinism.txt   G6-d identical: {det}")
    print(f"  tags: {list(res.tags)}   dims: {[(d.side, d.y, d.h_root, d.L) for d in res.dims]}")
    print(f"  from_defaults: {res.meta['from_defaults']}")


if __name__ == "__main__":
    main()
