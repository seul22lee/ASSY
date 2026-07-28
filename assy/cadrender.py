"""Draw the solids Stage 07 actually built.

Distinct from the Stage 04 renderer, which draws the *concept* - boxes at derived
poses, to review whether the layout reasoning is sound. This draws the exported
meshes, so what appears is what the kernel produced and nothing else. If a feature
failed to apply or a part exported empty, it is missing here, which is the point:
a concept drawing cannot tell you that.

Meshes are read back from the STL files rather than taken from the kernel, so the
picture is of the delivered artifact rather than of an object that happened to be
in memory when the manifest was written.
"""

from __future__ import annotations

import struct
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

#: Enough distinct hues to tell neighbouring parts apart; reused beyond that.
PALETTE = [
    "#4c78a8", "#54a24b", "#e45756", "#b279a2", "#f58518", "#72b7b2",
    "#9d755d", "#eeca3b", "#bab0ac", "#ff9da6", "#79706e", "#8cd17d",
]


def read_stl(path: Path) -> list[list[tuple[float, float, float]]]:
    """Triangles from a binary or ASCII STL. Returns [] rather than raising."""
    try:
        raw = path.read_bytes()
    except OSError:
        return []
    if raw[:5] == b"solid" and b"facet" in raw[:512]:
        tris, cur = [], []
        for line in raw.decode("utf-8", "ignore").splitlines():
            parts = line.split()
            if parts[:1] == ["vertex"] and len(parts) >= 4:
                cur.append((float(parts[1]), float(parts[2]), float(parts[3])))
                if len(cur) == 3:
                    tris.append(cur)
                    cur = []
        return tris
    if len(raw) < 84:
        return []
    count = struct.unpack("<I", raw[80:84])[0]
    tris = []
    for i in range(count):
        off = 84 + i * 50
        if off + 50 > len(raw):
            break
        v = struct.unpack("<12f", raw[off:off + 48])
        tris.append([(v[3], v[4], v[5]), (v[6], v[7], v[8]), (v[9], v[10], v[11])])
    return tris


def render_cad(manifest, out_path: Path, subtitle: str = "") -> Path:
    """Three views of the built assembly, plus a part inventory."""
    meshes: list[tuple[str, list]] = []
    for part in manifest.parts:
        tris = read_stl(Path(part.mesh_path))
        if tris:
            meshes.append((part.part_id, tris))

    # An enclosure hides everything it encloses, which is what an enclosure is for
    # and useless in a review drawing. The largest solids are drawn as glass so the
    # mechanism inside stays visible; nothing is omitted.
    volumes = {p.part_id: (p.bbox_mm[0] * p.bbox_mm[1] * p.bbox_mm[2]) for p in manifest.parts}
    biggest = max(volumes.values(), default=1.0)
    glass = {n for n, v in volumes.items() if v > biggest * 0.35}

    fig = plt.figure(figsize=(17.0, 6.4), dpi=160)
    views = [("isometric", 24, -58), ("front", 0, -90), ("top", 89, -90)]
    all_pts = [p for _, tris in meshes for t in tris for p in t]
    if all_pts:
        lo = [min(p[i] for p in all_pts) for i in range(3)]
        hi = [max(p[i] for p in all_pts) for i in range(3)]
        span = max(max(hi[i] - lo[i] for i in range(3)), 1.0) / 2
        mid = [(hi[i] + lo[i]) / 2 for i in range(3)]

    for n, (label, elev, azim) in enumerate(views):
        ax = fig.add_subplot(1, 4, n + 1, projection="3d")
        for i, (name, tris) in enumerate(meshes):
            see_through = name in glass
            ax.add_collection3d(Poly3DCollection(
                tris, facecolor=PALETTE[i % len(PALETTE)],
                edgecolor="#33333355" if see_through else "#33333322",
                linewidths=0.3 if see_through else 0.15,
                alpha=0.10 if see_through else 0.95,
                zorder=1 if see_through else 3))
        if all_pts:
            ax.set_xlim(mid[0] - span, mid[0] + span)
            ax.set_ylim(mid[1] - span, mid[1] + span)
            ax.set_zlim(mid[2] - span, mid[2] + span)
        ax.view_init(elev=elev, azim=azim)
        ax.set_box_aspect((1, 1, 1))
        ax.set_title(label, fontsize=9)
        ax.set_xticks([]); ax.set_yticks([]); ax.set_zticks([])
        for pane in (ax.xaxis, ax.yaxis, ax.zaxis):
            pane.pane.set_alpha(0.03)

    info = fig.add_subplot(1, 4, 4); info.set_axis_off()
    lines = [f"PARTS BUILT ({len(manifest.parts)})"]
    for i, part in enumerate(manifest.parts):
        mark = PALETTE[i % len(PALETTE)] if any(n == part.part_id for n, _ in meshes) else None
        bb = "x".join(f"{v:g}" for v in part.bbox_mm)
        lines.append(f"  {part.part_id}  {bb} mm  {part.mass_g:g} g"
                     + ("  [drawn as glass]" if part.part_id in glass else "")
                     + ("" if mark else "   [no mesh]"))
    if manifest.failures:
        lines += ["", f"BUILD FAILURES ({len(manifest.failures)})"]
        lines += [f"  {f}" for f in manifest.failures[:12]]
    if manifest.warnings:
        lines += ["", "WARNINGS"] + [f"  {w}" for w in manifest.warnings[:6]]
    info.text(0.0, 1.0, "\n".join(lines), fontsize=5.0, va="top", family="monospace")
    info.set_xlim(0, 1); info.set_ylim(0, 1)

    fig.suptitle(
        f"{subtitle}\nstatus: {manifest.status.value} · "
        f"{len(manifest.parts)} part(s) built · geometry read back from the exported STL",
        fontsize=10)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return out_path
