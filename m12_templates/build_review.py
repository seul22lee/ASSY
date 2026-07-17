"""m12 (D-track 3) — render each Hard-anchor host template with its anchors OVERLAID and LABELLED.

The milestone's pass-look: every anchor the m13 assembly will bind to is visible and named NOW, so a
later binding failure can't be blamed on a missing anchor. One PNG per template — the mesh (light,
translucent) with each anchor drawn as a coloured dot, its name, and a short arrow along its normal.

Run:  ./bin/py m12_templates/build_review.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402
from build123d import export_stl  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

from knowledge.templates import TEMPLATES  # noqa: E402

OUT = Path(__file__).parent / "out"
KIND_COLOR = {"axis": "#c53030", "face": "#2b6cb0", "edge": "#2f855a", "point": "#805ad5"}


def _mesh(name, tr):
    stl = OUT / "assets" / f"{name}.stl"
    stl.parent.mkdir(parents=True, exist_ok=True)
    export_stl(tr.part, str(stl), tolerance=0.1, angular_tolerance=0.3)
    return trimesh.load(stl, force="mesh")


def render(name):
    tr = TEMPLATES[name]()
    m = _mesh(name, tr)
    fig = plt.figure(figsize=(9, 7.5))
    ax = fig.add_subplot(111, projection="3d")
    tris = m.vertices[m.faces]
    ax.add_collection3d(Poly3DCollection(tris, facecolor="#cbd5e0", edgecolor="none", alpha=0.28))

    ext = float(np.linalg.norm(m.bounding_box.extents))
    arr = ext * 0.10
    for a in tr.anchors.values():
        c = KIND_COLOR.get(a.kind, "#000")
        px, py, pz = a.position
        ax.scatter([px], [py], [pz], color=c, s=45, depthshade=False, edgecolor="k", linewidths=0.5)
        n = np.array(a.normal, float)
        if np.linalg.norm(n) > 1e-9:
            n = n / np.linalg.norm(n) * arr
            ax.quiver(px, py, pz, n[0], n[1], n[2], color=c, lw=1.5, arrow_length_ratio=0.35)
        ax.text(px + n[0] * 0.4 if np.linalg.norm(n) > 1e-9 else px, py, pz + arr * 0.4,
                f" {a.name}\n [{a.kind}]", color=c, fontsize=7.5, weight="bold")

    lo = m.bounding_box.bounds[0]; hi = m.bounding_box.bounds[1]
    ctr = (lo + hi) / 2; span = float((hi - lo).max()) * 0.6
    ax.set_xlim(ctr[0] - span, ctr[0] + span)
    ax.set_ylim(ctr[1] - span, ctr[1] + span)
    ax.set_zlim(ctr[2] - span, ctr[2] + span)
    ax.set_xlabel("X"); ax.set_ylabel("Y (front = +Y)"); ax.set_zlabel("Z")
    ax.set_title(f"{name} — anchor overlay ({len(tr.anchors)} anchors)\n"
                 f"red=axis  blue=face  green=edge  purple=point", fontsize=10)
    ax.view_init(elev=22, azim=-58)
    fig.tight_layout()
    path = OUT / f"{name}_anchors.png"
    fig.savefig(path, dpi=135); plt.close(fig)
    return path, list(tr.anchors)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name in ("cabinet_shell", "drawer_tray", "knob_shaft", "rack_bar"):
        path, anchors = render(name)
        print(f"{name:16s} -> {path.name}   anchors: {anchors}")


if __name__ == "__main__":
    main()
