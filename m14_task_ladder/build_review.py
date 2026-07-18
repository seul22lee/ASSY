"""m14 — render representative variant goldens for the REVIEW (one per axis).

  dimensional : A1 (80×60×40) vs A2 (120×90×50) snap box — visibly bigger.
  constraint  : B1 (hinge + latch) vs B3 (hinge, NO latch) — the latch element visibly gone.
  constraint  : C1 lift (vertical) vs C4 drawer (horizontal) — the same cards, re-oriented.

Run:  ./bin/py m14_task_ladder/build_review.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402
from build123d import Rotation, export_stl  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

from knowledge.cards.base import CARD_REGISTRY  # noqa: E402
from pipeline.compile_assembly import compile_assembly  # noqa: E402
from tasks.benchmark.benchmark import easy_no_latch  # noqa: E402
from tasks.build_goldens import anchor_easy, anchor_hard, anchor_lift, snap_starter  # noqa: E402

OUT = Path(__file__).parent / "out"
COL = ["#8aa9c9", "#e0a458", "#6bbf7b", "#c98bbf", "#d98b8b"]


def _meshes(plan, tilt=None):
    for e in plan.elements:
        try:
            e.params = CARD_REGISTRY[e.card_ref].resolve_params(plan, e)
        except NotImplementedError:
            pass
    ca = compile_assembly(plan)
    ms = {}
    for i, (pid, part) in enumerate(ca.parts.items()):
        stl = OUT / "assets" / f"{pid}.stl"; stl.parent.mkdir(parents=True, exist_ok=True)
        export_stl((tilt * part) if tilt else part, str(stl), tolerance=0.2, angular_tolerance=0.4)
        ms[pid] = trimesh.load(stl, force="mesh")
    return ms


def _draw(ax, ms, title):
    for i, (pid, m) in enumerate(ms.items()):
        ax.add_collection3d(Poly3DCollection(m.vertices[m.faces], facecolor=COL[i % len(COL)],
                                             edgecolor="#33333322", linewidths=0.1, alpha=0.55))
    allv = np.vstack([m.vertices for m in ms.values()])
    c = (allv.min(0) + allv.max(0)) / 2; r = float((allv.max(0) - allv.min(0)).max()) * 0.55
    ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(c[2] - r, c[2] + r)
    ax.view_init(elev=22, azim=-58); ax.set_title(title, fontsize=10)
    ax.set_xticklabels([]); ax.set_yticklabels([]); ax.set_zticklabels([])


def pair(fname, left, right, suptitle):
    fig = plt.figure(figsize=(12, 5.2))
    for i, (plan, title, tilt) in enumerate((left, right), 1):
        ax = fig.add_subplot(1, 2, i, projection="3d")
        _draw(ax, _meshes(plan, tilt), title)
    fig.suptitle(suptitle, fontsize=12)
    fig.tight_layout(); fig.savefig(OUT / fname, dpi=125); plt.close(fig)
    print("wrote", fname)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # dimensional
    pair("axis_dimensional.png",
         (snap_starter(), "A1 · 80×60×40, 2 hooks", None),
         (snap_starter(box_l=120, box_w=90, box_h=50, n_hooks=3), "A2 · 120×90×50, 3 hooks", None),
         "DIMENSIONAL axis — same snap card, ⑤ re-resolves at the larger size (visibly bigger)")
    # constraint (forbid the latch)
    pair("axis_constraint_latch.png",
         (anchor_easy("stop"), "B1 · hinge + LATCH (+stop)", None),
         (easy_no_latch(), "B3 · hinge + stop, NO latch", None),
         "CONSTRAINT axis — 'no latch' drops the snap element (visibly absent on the front rim)")
    # constraint (orientation: lift vs drawer)
    tilt = Rotation(0, -90, 0)
    pair("axis_constraint_orient.png",
         (anchor_lift(), "C1 · crank LIFT (vertical travel)", tilt),
         (anchor_hard("drawer"), "C4 · knob DRAWER (horizontal)", None),
         "CONSTRAINT axis — same 2×slide_rail + rack_pinion, re-oriented (lift vs drawer)")


if __name__ == "__main__":
    main()
