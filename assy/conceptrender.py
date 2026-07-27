"""Concept layout renderer - derived, non-authoritative, deterministic.

Turns a Stage 04 spatial blueprint into a coarse engineering block layout. The
images are a **review artifact**: they exist so a human (or a reviewing model) can
see a packaging problem that survives a structured check. Nothing here may
influence an engineering decision, and `output.json` remains the authority.

    blueprint (JSON)  ->  block layout  ->  standard engineering views

**The layout convention is the renderer's, not the blueprint's.** The blueprint
states qualitative zones - core, flanking, end, boundary, external - and this
module maps each to a slot in a unit envelope so the arrangement can be drawn.
Those slot extents are *nominal drawing units*, never dimensions: they carry no
engineering meaning, they are not proportional to anything, and no downstream
stage may read them. Changing them changes only the picture.

Deterministic: the same blueprint always produces the same image. Ordering is by
blueprint order, colours are keyed on zone and piece kind, and nothing is random.

A failure to render never fails a run - the caller receives whatever paths were
produced.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

# -- nominal drawing units. NOT dimensions. -------------------------------
W, D, H = 2.0, 1.6, 2.6  # envelope width, depth, height

ZONE_COLOR = {
    "core": "#4c78a8",
    "flanking": "#72b7b2",
    "end": "#e45756",
    "offset": "#b279a2",
    "boundary": "#9d9d9d",
    "external": "#f58518",
}

KIND_COLOR = {
    "shell": "#bcbcbc",
    "cover": "#d5a6bd",
    "moving_body": "#4c78a8",
    "transmission_element": "#54a24b",
    "support_element": "#e45756",
    "limit_element": "#b279a2",
    "retention_element": "#ff9da6",
    "user_element": "#f58518",
}

SWEPT_COLOR = "#ffd166"


def _box(cx: float, cy: float, cz: float, sx: float, sy: float, sz: float):
    """Eight corners of an axis-aligned box, centred on (cx, cy, cz)."""
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    return [
        (cx - hx, cy - hy, cz - hz), (cx + hx, cy - hy, cz - hz),
        (cx + hx, cy + hy, cz - hz), (cx - hx, cy + hy, cz - hz),
        (cx - hx, cy - hy, cz + hz), (cx + hx, cy - hy, cz + hz),
        (cx + hx, cy + hy, cz + hz), (cx - hx, cy + hy, cz + hz),
    ]


def _faces(c):
    return [
        [c[0], c[1], c[2], c[3]], [c[4], c[5], c[6], c[7]],
        [c[0], c[1], c[5], c[4]], [c[2], c[3], c[7], c[6]],
        [c[1], c[2], c[6], c[5]], [c[0], c[3], c[7], c[4]],
    ]


class Block:
    """One drawable volume: a named box with a colour and a role."""

    def __init__(self, name, cx, cy, cz, sx, sy, sz, color, alpha, kind="piece"):
        self.name = name
        self.c = (cx, cy, cz)
        self.s = (sx, sy, sz)
        self.color = color
        self.alpha = alpha
        self.kind = kind

    @property
    def bounds(self):
        (cx, cy, cz), (sx, sy, sz) = self.c, self.s
        return (cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2,
                cz - sz / 2, cz + sz / 2)


def _layout(bp: dict[str, Any]) -> list[Block]:
    """Map qualitative zones onto nominal slots. The convention lives here."""
    blocks: list[Block] = []
    pieces = bp.get("placed_pieces", [])

    # Counters make repeated occupants of one zone sit side by side rather than
    # on top of each other, so an overlap in the picture means a real conflict.
    n_flank = n_end = n_ext = n_core = n_bound = 0
    flank = [p for p in pieces if (p.get("zone") == "flanking")]
    ends = [p for p in pieces if (p.get("zone") == "end")]
    exts = [p for p in pieces if (p.get("zone") == "external")]
    cores = [p for p in pieces if (p.get("zone") == "core")]
    bounds = [p for p in pieces if (p.get("zone") == "boundary")]

    for p in pieces:
        zone = p.get("zone") or "core"
        kind = p.get("kind", "shell")
        color = KIND_COLOR.get(kind, "#888888")

        if kind == "shell":
            blocks.append(Block(p["name"], 0, 0, H / 2, W, D, H, color, 0.08, "shell"))
            continue
        if zone == "boundary" and kind == "cover":
            n_bound += 1
            blocks.append(
                Block(p["name"], 0, -D / 2, H * 0.30, W * 0.86, 0.07, H * 0.42,
                      color, 0.55, "cover")
            )
            continue
        if zone == "boundary":
            i, n = n_bound, max(len(bounds), 1)
            n_bound += 1
            blocks.append(
                Block(p["name"], W * 0.30, D / 2 - 0.06,
                      H * (0.55 + 0.12 * i), W * 0.22, 0.10, H * 0.10,
                      color, 0.85, "piece")
            )
            continue
        if zone == "external":
            i = n_ext
            n_ext += 1
            blocks.append(
                Block(p["name"], W * (-0.28 + 0.42 * i), -D / 2 - 0.28, H * 0.30,
                      0.34, 0.34, 0.34, color, 0.9, "piece")
            )
            continue
        if zone == "flanking":
            i, n = n_flank, max(len(flank), 1)
            n_flank += 1
            side = -1 if i % 2 == 0 else 1
            blocks.append(
                Block(p["name"], side * W * 0.33, 0, H * 0.52,
                      0.16, D * 0.22, H * 0.62, color, 0.85, "piece")
            )
            continue
        if zone == "end":
            i, n = n_end, max(len(ends), 1)
            n_end += 1
            # Alternate bottom and top so both ends of the primary axis are used.
            cz = H * 0.10 if i % 2 == 0 else H * 0.90
            off = W * (-0.18 + 0.36 * (i // 2))
            blocks.append(
                Block(p["name"], off, 0, cz, W * 0.30, D * 0.30, H * 0.07,
                      color, 0.9, "piece")
            )
            continue
        # core
        i, n = n_core, max(len(cores), 1)
        n_core += 1
        blocks.append(
            Block(p["name"], W * (-0.14 + 0.28 * (i % 2)), 0, H * (0.30 + 0.22 * (i // 2)),
                  W * 0.20, D * 0.28, H * 0.34, color, 0.9, "piece")
        )
    return blocks


def _region_blocks(bp) -> list[Block]:
    """Regions as volumes. A region with no piece in it still occupies space."""
    blocks: list[Block] = []
    counts: dict[str, int] = {}
    for rp in bp.get("region_placements", []):
        zone = rp.get("zone", "core")
        if rp["region"].endswith("_swept_volume"):
            continue  # drawn from the swept-volume spec, with its own shape
        i = counts.get(zone, 0)
        counts[zone] = i + 1
        color = ZONE_COLOR.get(zone, "#888888")
        if zone == "core":
            b = Block(rp["region"], W * (-0.16 + 0.32 * (i % 2)), 0,
                      H * (0.30 + 0.24 * (i // 2)), W * 0.30, D * 0.42, H * 0.40,
                      color, 0.13, "region")
        elif zone == "flanking":
            side = -1 if i % 2 == 0 else 1
            b = Block(rp["region"], side * W * 0.36, 0, H * 0.52,
                      W * 0.14, D * 0.42, H * 0.70, color, 0.13, "region")
        elif zone == "end":
            cz = H * 0.08 if i % 2 == 0 else H * 0.93
            b = Block(rp["region"], W * (-0.20 + 0.40 * (i // 2)), 0, cz,
                      W * 0.42, D * 0.42, H * 0.10, color, 0.13, "region")
        elif zone == "boundary":
            b = Block(rp["region"], 0, 0, H / 2, W * 1.01, D * 1.01, H * 1.01,
                      color, 0.05, "region")
        else:  # external
            b = Block(rp["region"], W * (-0.34 + 0.34 * i), -D / 2 - 0.34, H * 0.30,
                      0.46, 0.42, 0.46, color, 0.13, "region")
        blocks.append(b)
    return blocks


def _swept_blocks(bp: dict[str, Any], blocks: list[Block]) -> list[Block]:
    """Swept envelopes, shaped by how the element actually moves."""
    by_name = {b.name: b for b in blocks}
    out: list[Block] = []
    for sv in bp.get("swept_volumes", []):
        src = by_name.get(sv["element"])
        if src is None:
            continue
        cx, cy, cz = src.c
        shape = sv.get("shape")
        if shape == "prism":
            # A translating element sweeps its own section along the whole travel.
            out.append(
                Block(f"{sv['element']} sweep", cx, cy, H * 0.55,
                      src.s[0] * 1.05, src.s[1] * 1.05, H * 0.70,
                      SWEPT_COLOR, 0.20, "swept")
            )
        elif shape == "disc":
            r = 0.30 if sv.get("external") else 0.24
            out.append(
                Block(f"{sv['element']} sweep", cx, cy, cz, r * 2, 0.10, r * 2,
                      SWEPT_COLOR, 0.22, "swept_disc")
            )
        elif shape == "arc_sector":
            out.append(
                Block(f"{sv['element']} sweep", cx, cy - D * 0.18, cz + H * 0.12,
                      src.s[0] * 1.2, D * 0.9, H * 0.42,
                      SWEPT_COLOR, 0.18, "swept_arc")
            )
        else:
            out.append(
                Block(f"{sv['element']} sweep (unclassified)", cx, cy, cz,
                      src.s[0] * 1.3, src.s[1] * 1.3, src.s[2] * 1.3,
                      "#ff0000", 0.15, "swept")
            )
    return out


def _draw_iso(ax, blocks, bp):
    for b in blocks:
        polys = _faces(_box(*b.c, *b.s))
        col = Poly3DCollection(
            polys, alpha=b.alpha, facecolor=b.color,
            edgecolor="#333333" if b.kind != "shell" else "#666666",
            linewidths=0.4,
        )
        ax.add_collection3d(col)
        if b.kind not in ("shell", "swept", "swept_disc", "swept_arc"):
            ax.text(b.c[0], b.c[1], b.c[2], b.name.replace("_", " "),
                    fontsize=5.2, ha="center", va="center", zorder=10)

    frame = bp.get("reference_frame") or {}
    ax.plot([0, 0], [0, 0], [-0.15, H + 0.15], color="#d62728", lw=1.4, ls="--")
    ax.text(0, 0, H + 0.25, frame.get("primary_axis", "axis").replace("_", " "),
            color="#d62728", fontsize=6, ha="center")

    ax.set_xlim(-W, W); ax.set_ylim(-D, D); ax.set_zlim(-0.2, H + 0.4)
    ax.set_box_aspect((2 * W, 2 * D, H + 0.6))
    ax.view_init(elev=22, azim=-58)
    ax.set_axis_off()
    ax.set_title("isometric", fontsize=8)


def _draw_ortho(ax, blocks, bp, plane: str, title: str, hide_shell=False, label_all=False):
    """Orthographic projection. plane: 'front' (XZ), 'side' (YZ), 'top' (XY)."""
    pick = {"front": (0, 2, 0, 2), "side": (1, 2, 1, 2), "top": (0, 1, 0, 1)}[plane]
    ai, bi = pick[0], pick[1]

    n_label = 0
    for blk in blocks:
        if hide_shell and blk.kind == "shell":
            continue
        c, s = blk.c, blk.s
        rect = mpatches.Rectangle(
            (c[ai] - s[ai] / 2, c[bi] - s[bi] / 2), s[ai], s[bi],
            facecolor=blk.color, alpha=max(blk.alpha, 0.12),
            edgecolor="#333333" if blk.kind != "shell" else "#777777",
            linewidth=0.5, linestyle="-" if blk.kind != "shell" else "--",
        )
        ax.add_patch(rect)
        if label_all or blk.kind not in ("shell", "swept", "swept_disc", "swept_arc"):
            # Stagger labels so co-located blocks stay readable.
            nudge = 0.055 * (n_label % 3 - 1) * (1 if plane != "top" else 1.6)
            ax.text(c[ai], c[bi] + nudge, blk.name.replace("_", " "), fontsize=4.4,
                    ha="center", va="center", zorder=12)
            n_label += 1

    if plane in ("front", "side"):
        ax.plot([0, 0], [-0.15, H + 0.15], color="#d62728", lw=1.0, ls="--")

    lim = {"front": ((-W, W), (-0.3, H + 0.4)),
           "side": ((-D * 1.4, D * 1.4), (-0.3, H + 0.4)),
           "top": ((-W, W), (-D * 1.4, D * 1.4))}[plane]
    ax.set_xlim(*lim[0]); ax.set_ylim(*lim[1])
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_color("#cccccc")
    ax.set_title(title, fontsize=8)


def render_concept(bp: dict[str, Any], out_dir: Path, stem: str = "concept_layout") -> list[str]:
    """Render the blueprint. Returns the paths written."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    try:
        pieces = _layout(bp)
        swept = _swept_blocks(bp, pieces)
        regions = _region_blocks(bp)
        blocks = pieces + swept

        fig = plt.figure(figsize=(17.0, 8.4), dpi=165)
        frame = bp.get("reference_frame") or {}
        fig.suptitle(
            f"Concept layout - {bp.get('source_candidate_id', '?')}   "
            f"(primary axis: {frame.get('primary_axis', '?')}, "
            f"{frame.get('primary_motion', '?')})\n"
            "block layout for spatial review - NOT geometry, NOT to scale, non-authoritative",
            fontsize=9,
        )

        ax = fig.add_subplot(2, 4, 1, projection="3d")
        _draw_iso(ax, blocks, bp)
        _draw_ortho(fig.add_subplot(2, 4, 2), blocks, bp, "front", "front (looking along depth)")
        _draw_ortho(fig.add_subplot(2, 4, 3), blocks, bp, "side", "side (looking along width)")
        _draw_ortho(fig.add_subplot(2, 4, 4), blocks, bp, "top", "top (looking down the axis)")
        _draw_ortho(fig.add_subplot(2, 4, 5), blocks, bp, "front",
                    "cutaway (housing hidden)", hide_shell=True)
        _draw_ortho(fig.add_subplot(2, 4, 6), regions, bp, "front",
                    "regions by zone (front)", label_all=True)
        _draw_ortho(fig.add_subplot(2, 4, 7), regions, bp, "top",
                    "regions by zone (top)", label_all=True)

        legend_ax = fig.add_subplot(2, 4, 8)
        legend_ax.set_axis_off()
        handles = [
            mpatches.Patch(color=c, label=k.replace("_", " "))
            for k, c in KIND_COLOR.items()
            if any(p.get("kind") == k for p in bp.get("placed_pieces", []))
        ]
        handles.append(mpatches.Patch(color=SWEPT_COLOR, alpha=0.35, label="swept volume"))
        handles.append(mpatches.Patch(color="none", label=" "))
        handles += [
            mpatches.Patch(color=c, alpha=0.35, label=f"zone: {z}")
            for z, c in ZONE_COLOR.items()
            if any(r.get("zone") == z for r in bp.get("region_placements", []))
        ]
        legend_ax.legend(handles=handles, loc="upper left", fontsize=6.5, frameon=False)
        n_unaddressed = sum(
            1 for i in bp.get("interference_candidates", []) if not i.get("addressed_by")
        )
        legend_ax.text(
            0.0, 0.42,
            f"regions placed: {len(bp.get('region_placements', []))}\n"
            f"pieces: {len(bp.get('placed_pieces', []))}\n"
            f"swept volumes: {len(bp.get('swept_volumes', []))}\n"
            f"interference candidates: {len(bp.get('interference_candidates', []))}"
            f" ({n_unaddressed} unresolved)\n"
            f"issues: {len(bp.get('issues', []))}",
            fontsize=6.5, va="top", family="monospace",
        )

        fig.tight_layout(rect=(0, 0, 1, 0.93))
        path = out_dir / f"{stem}.png"
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        written.append(str(path))
    except Exception:  # pragma: no cover - a render must never fail a run
        plt.close("all")
    return written
