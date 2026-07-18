"""m15 — geometry gallery: render each task's TARGET design (the golden, which rung D reproduces
when design_ok) beside the rung-A naive output for the same task. The side-by-side that makes the
ladder visual: a proper multi-part mechanism vs whatever the direct-CAD baseline emitted.

Rendered with trimesh (load) + matplotlib 3D (no OpenGL/offscreen needed).

Run:  ./bin/py m15_ablation/render_gallery.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "m0"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

from ontology.schema import DesignPlan  # noqa: E402
from pipeline.compile_assembly import compile_assembly  # noqa: E402

OUT = Path(__file__).parent / "out"
GAL = OUT / "gallery"
TASKS = ["A1-snap-base", "B1-hinge-latch-base", "C1-lift-base", "C4-drawer"]
COLORS = ["#4e79a7", "#f28e2b", "#59a14f", "#e15759", "#b07aa1", "#76b7b2"]


def golden_stls(task_id, wd):
    """Compile the golden and export each printed part to its own STL."""
    from build123d import export_stl
    g = DesignPlan.model_validate_json((ROOT / "tasks/benchmark/goldens" / f"{task_id}.json").read_text())
    ca = compile_assembly(g)
    paths = []
    for pid, part in ca.parts.items():
        solid = getattr(part, "part", part)
        p = wd / f"{task_id}__{pid}.stl"
        try:
            export_stl(solid, str(p)); paths.append(p)
        except Exception:
            pass
    return paths


def render(stls, title, out_png):
    fig = plt.figure(figsize=(5.2, 4.6))
    ax = fig.add_subplot(111, projection="3d")
    allpts = []
    for i, s in enumerate(stls):
        try:
            m = trimesh.load(str(s), force="mesh")
        except Exception:
            continue
        if not len(m.faces):
            continue
        tris = m.vertices[m.faces]
        pc = Poly3DCollection(tris, alpha=0.9, facecolor=COLORS[i % len(COLORS)],
                              edgecolor="k", linewidths=0.05)
        ax.add_collection3d(pc)
        allpts.append(m.vertices)
    if allpts:
        pts = np.vstack(allpts)
        lo, hi = pts.min(0), pts.max(0)
        c = (lo + hi) / 2; r = (hi - lo).max() / 2 * 1.1
        ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(c[2] - r, c[2] + r)
    ax.set_box_aspect((1, 1, 1)); ax.view_init(elev=22, azim=-58)
    ax.set_xticks([]); ax.set_yticks([]); ax.set_zticks([])
    ax.set_title(title, fontsize=10)
    fig.tight_layout(); fig.savefig(out_png, dpi=130); plt.close(fig)


def find_naive_stls(task_id):
    """Any executed rung-A output for this task (naive gen dirs). Usually empty — that IS the floor."""
    for base in (ROOT / "m15_naive" / "gen", ):
        hits = sorted(base.glob(f"{task_id}__*/stl/*.stl")) if base.exists() else []
        if hits:
            return hits
    return []


def main():
    GAL.mkdir(parents=True, exist_ok=True)
    index = ["# m15 geometry gallery — target (golden ≈ rung D) vs naive floor (rung A)", ""]
    for t in TASKS:
        gp = golden_stls(t, GAL)
        gpng = GAL / f"target_{t}.png"
        render(gp, f"TARGET (golden ≈ D): {t}\n{len(gp)} printed parts", gpng)
        npng = GAL / f"naive_{t}.png"
        ns = find_naive_stls(t)
        if ns:
            render(ns, f"naive (rung A): {t}\n{len(ns)} solids", npng)
            naive_line = f"![]({npng.name})"
        else:
            naive_line = "*(no executable geometry — rung A did not produce a valid solid)*"
        index += [f"## {t}", "", f"| target (golden ≈ rung D) | naive (rung A) |", "|---|---|",
                  f"| ![]({gpng.name}) | {naive_line} |", ""]
        print(f"  {t}: target {len(gp)} parts, naive {len(ns)} solids")
    (GAL / "README.md").write_text("\n".join(index))
    print("wrote", GAL / "README.md")


if __name__ == "__main__":
    main()
