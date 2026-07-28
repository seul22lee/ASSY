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

Every mark on the page traces to a blueprint field, and every blueprint field is
either drawn or explicitly excluded with a reason. Both directions are registered
in `conceptcoverage` and enforced by tests: a glyph that comes from nowhere is the
picture asserting engineering the contracts never stated.

A failure to render never fails a run - the caller receives whatever paths were
produced.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.lines as mlines  # noqa: E402
import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

from assy.conceptcoverage import audit  # noqa: E402

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

# Relations that occupy a definite engagement region rather than merely relating
# two elements at a distance. A routed link and an access reachability claim are
# not localized contacts, so they stay as connectors.
DERIVED_KINDS = (
    "topology_edge", "topology_axis", "topology_corridor",
    "topology_contact", "topology_boundary", "engagement_region",
)

LOCALIZED_RELATIONS = {
    "shared_axis", "coaxial_working_overlap", "mating_adjacency",
    "axis_surrounded", "axial_reaction_station", "contact_at_extreme",
    "common_travel_direction",
}
MOTION_COLOR = "#0b6e4f"      # kinematics
JOINT_COLOR = "#5b2c8d"       # a relationship, not a member
FEATURE_COLOR = "#e07a5f"     # a local detail on a host body
INTERFACE_COLOR = "#1f4e79"   # realizable relationship
VIOLATED_COLOR = "#c1121f"    # unrealizable relationship
UNCHECKED_COLOR = "#9a9a9a"   # undecidable - never drawn as a pass
ISSUE_COLOR = "#c1121f"

# Relation kind -> the mark that stands for it. One symbol per mechanical demand,
# so a hinge, a threaded pair and a bolted joint never render identically.
INTERFACE_MARK = {
    "shared_axis": ("o", "shared axis"),
    "coaxial_working_overlap": ("H", "engaged over a working length"),
    "common_travel_direction": ("_", "shared travel span"),
    "mating_adjacency": ("D", "mating contact"),
    "axis_surrounded": ("s", "axis surrounded"),
    "axial_reaction_station": ("^", "axial reaction"),
    "contact_at_extreme": ("|", "contact at travel extreme"),
    "disjoint_swept": ("x", "must stay clear"),
    "exterior_reachable": (">", "reachable from outside"),
    "continuous_route": (".", "routed connection"),
    "separated_along_axis": ("*", "distinct reaction stations"),
}

STATUS_COLOR = {
    "satisfied": INTERFACE_COLOR,
    "violated": VIOLATED_COLOR,
    "not_checkable": UNCHECKED_COLOR,
}




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
        self.axis: str | None = None
        self.radius: float | None = None

    @property
    def bounds(self):
        (cx, cy, cz), (sx, sy, sz) = self.c, self.s
        return (cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2,
                cz - sz / 2, cz + sz / 2)


SLOT_MIN, SLOT_MAX = 0, 7


def _slot_to_z(lo: int, hi: int) -> tuple[float, float]:
    """Map an ordinal span onto the drawing height.

    The ordinal scale is the blueprint's; this is the only place it becomes a
    length, and the length carries no engineering meaning.
    """
    span = max(SLOT_MAX - SLOT_MIN, 1)
    z0 = H * (lo - SLOT_MIN) / (span + 1)
    z1 = H * (hi + 1 - SLOT_MIN) / (span + 1)
    return (z0 + z1) / 2, max(z1 - z0, 0.10)


def _layout(bp: dict[str, Any]) -> list[Block]:
    """Draw the layout the blueprint synthesized. Nothing here decides position.

    Every coordinate comes from `body_placements`: the ordinal span sets the
    extent along the principal axis, `radial` sets whether a body sits on that
    axis or beside it, and `containment` sets which side of the boundary it is
    on. There is no zone slot table and no per-zone counter, because a renderer
    choosing a position would make the picture disagree with the artifact.
    """
    blocks: list[Block] = []
    placements = {b["body"]: b for b in bp.get("body_placements", [])}
    kinds = {p["name"]: p for p in bp.get("placed_pieces", [])}

    off_axis_seen = 0
    for name in sorted(placements):
        pl = placements[name]
        piece = kinds.get(name, {})
        kind = piece.get("kind", "shell")
        colour = KIND_COLOR.get(kind, "#888888")
        lo, hi = (pl.get("span") or [SLOT_MIN, SLOT_MAX])[:2]
        cz, sz = _slot_to_z(lo, hi)
        containment = pl.get("containment", "interior")
        radial = pl.get("radial", "on_axis")

        if kind == "shell":
            blocks.append(Block(name, 0, 0, cz, W, D, sz, colour, 0.08, "shell"))
            continue

        cx = 0.0
        sx = W * 0.30
        if radial == "off_axis":
            side = -1 if off_axis_seen % 2 == 0 else 1
            off_axis_seen += 1
            cx = side * W * 0.33
            sx = W * 0.13

        cy, sy = 0.0, D * 0.30
        if containment == "exterior":
            cy, sy = -D / 2 - 0.30, 0.34
        elif containment == "spanning":
            cy, sy = -D * 0.32, D * 0.72
        elif containment == "boundary":
            cy, sy = 0.0, D * 0.94
            sx = W * 0.94

        blocks.append(
            Block(name, cx, cy, cz, sx, sy, sz, colour,
                  0.55 if containment == "boundary" else 0.85, "piece")
        )
    return blocks


# ---------------------------------------------------------------------------
# State-sequence rendering. Positions come only from state_poses.
# ---------------------------------------------------------------------------
INTERACTION_STYLE = {
    "engagement": ("o", "#0b6e4f", "engaged"),
    "disengagement": ("o", "#c1121f", "released"),
    "stop_contact": ("s", "#5b2c8d", "stop contact"),
    "contact": ("D", "#1f4e79", "contact"),
    "clearance": ("2", "#e07a5f", "clear"),
}


def _ext_to_xy(extent):
    """Ordinal box -> (x0, z0, dx, dz) in the front (X-Z) projection."""
    (xlo, xhi), _, (zlo, zhi) = extent
    x0 = W * (xlo / 7.0 - 0.5)
    x1 = W * ((xhi + 1) / 7.0 - 0.5)
    z0 = H * (zlo / 8.0)
    z1 = H * ((zhi + 1) / 8.0)
    return x0, z0, max(x1 - x0, 0.06), max(z1 - z0, 0.06)


def _ext_depth(extent):
    """The same box in the side (Y-Z) projection, so a swing is visible."""
    _, (ylo, yhi), (zlo, zhi) = extent
    y0 = D * (ylo / 7.0 - 0.5)
    y1 = D * ((yhi + 1) / 7.0 - 0.5)
    z0 = H * (zlo / 8.0)
    z1 = H * ((zhi + 1) / 8.0)
    return y0, z0, max(y1 - y0, 0.06), max(z1 - z0, 0.06)


def _draw_state_panel(ax, bp, state, side=False):
    """One functional state, drawn from its poses alone."""
    poses = [p for p in bp.get("state_poses", []) if p["state"] == state]
    kinds = {p["name"]: p for p in bp.get("placed_pieces", [])}
    project = _ext_depth if side else _ext_to_xy

    for pose in sorted(poses, key=lambda p: p["body"]):
        piece = kinds.get(pose["body"], {})
        kind = piece.get("kind", "shell")
        x, z, dx, dz = project(pose["extent"])
        shell = kind == "shell"
        ax.add_patch(mpatches.Rectangle(
            (x, z), dx, dz,
            facecolor=KIND_COLOR.get(kind, "#888888"),
            alpha=0.10 if shell else 0.85,
            edgecolor="#666666" if shell else "#333333",
            linewidth=0.5, linestyle="--" if shell else "-", zorder=2 if shell else 4))
        if not shell:
            ax.text(x + dx / 2, z + dz / 2, pose["body"].replace("_", " "),
                    fontsize=3.9, ha="center", va="center", zorder=6)
            if pose.get("joint_value"):
                ax.text(x + dx / 2, z + dz + 0.05, pose["joint_value"],
                        fontsize=3.4, ha="center", va="bottom",
                        color=MOTION_COLOR, zorder=6)

    # Local elements have no pose of their own: their position in this state is
    # derived from the bodies they are attached to, so a retaining pair is drawn
    # in contact when its hosts meet and apart when they separate.
    at_body = {p["body"]: project(p["extent"]) for p in poses}

    def _between(hosts):
        boxes = [at_body[h] for h in hosts if h in at_body]
        if not boxes:
            return None
        if len(boxes) == 1:
            x, z, dx, dz = boxes[0]
            return x + dx / 2, z
        (ax0, az0, adx, adz), (bx0, bz0, bdx, bdz) = boxes[0], boxes[1]
        acx, acz = ax0 + adx / 2, az0 + adz / 2
        bcx, bcz = bx0 + bdx / 2, bz0 + bdz / 2
        # Meet at the nearest surfaces, not between centres.
        px = min(max(bcx, ax0), ax0 + adx)
        pz = min(max(bcz, az0), az0 + adz)
        qx = min(max(acx, bx0), bx0 + bdx)
        qz = min(max(acz, bz0), bz0 + bdz)
        return (px + qx) / 2, (pz + qz) / 2

    for piece in sorted(bp.get("placed_pieces", []), key=lambda p: p["name"]):
        klass = piece.get("element_class", "body")
        if klass == "body" or not piece.get("attached_to"):
            continue
        spot = _between(piece["attached_to"])
        if spot is None:
            continue
        px, pz = spot
        if klass == "joint":
            ax.plot(px, pz, marker="o", ms=8, mfc="white", mec=JOINT_COLOR,
                    mew=1.6, zorder=11)
        else:
            ax.plot(px, pz, marker="^", ms=7, mfc=FEATURE_COLOR, mec="#333333",
                    mew=0.6, zorder=11)
        ax.text(px + 0.06, pz, piece["name"].replace("_", " "), fontsize=3.4,
                va="center", color=JOINT_COLOR if klass == "joint" else FEATURE_COLOR,
                zorder=11)

    # Joints: drawn at the interface between parent and child in this state.
    at = {p["body"]: project(p["extent"]) for p in poses}
    for j in bp.get("kinematic_joints", []):
        if j["child"] not in at or j["parent"] not in at:
            continue
        cx, cz, cdx, cdz = at[j["child"]]
        marker = {"revolute": "o", "prismatic": "s",
                  "helical": "H", "fixed": "P"}.get(j["type"], "o")
        jx, jz = cx, cz + cdz
        ax.plot(jx, jz, marker=marker, ms=9, mfc="none", mec=JOINT_COLOR,
                mew=1.2, zorder=9)
        ax.text(jx, jz + 0.09, f"{j['name']}\n{j['type']}", fontsize=3.1,
                color=JOINT_COLOR, ha="center", va="bottom", zorder=9)

    # Interactions belonging to this state.
    for n, inter in enumerate(
            [i for i in bp.get("state_interactions", []) if i["state"] == state]):
        a = inter["between"][0]
        box = at.get(a) or at.get(inter["between"][1])
        if box is None:
            continue
        x, z, dx, dz = box
        mark, colour, label = INTERACTION_STYLE.get(
            inter["kind"], ("x", "#333333", inter["kind"]))
        px, pz = x + dx * 0.5, z - 0.10 - 0.11 * n
        ax.plot(px, pz, marker=mark, ms=6, color=colour, zorder=10)
        ax.text(px + 0.07, pz, f"{label}: {a.replace('_', ' ')}", fontsize=3.3,
                color=colour, va="center", zorder=10)

    holds = [
        f"{p['predicate']}({p['subject']})"
        for p in bp.get("state_predicates", []) if p["state"] == state and p["holds"]
    ]
    ax.text(-W * 0.72, H * 1.02, "\n".join(holds), fontsize=3.5, va="top",
            color="#0b6e4f", zorder=11)

    lim = (-W * 0.75, W * 0.75) if not side else (-D * 0.85, D * 0.85)
    ax.set_xlim(*lim); ax.set_ylim(-0.45, H * 1.12)
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_color("#cccccc")
    ax.set_title(f"{state}{' (side)' if side else ''}", fontsize=8)


def _draw_chain_panel(ax, bp):
    """The motion chain: what drives what, by which coupling, at what ratio."""
    couplings = bp.get("joint_couplings", [])
    ax.set_axis_off()
    ax.set_title("motion chain (driver -> driven)", fontsize=8)
    if not couplings:
        ax.text(0.5, 0.5, "single moving body; no coupling", fontsize=5,
                ha="center", va="center")
        return
    n = len(couplings)
    for i, c in enumerate(couplings):
        y = 1.0 - (i + 0.5) / n
        ax.annotate("", xy=(0.62, y), xytext=(0.30, y),
                    arrowprops=dict(arrowstyle="-|>", color=MOTION_COLOR, lw=1.4))
        ax.text(0.28, y, c["driver"].replace("_", " "), fontsize=4.4,
                ha="right", va="center")
        ax.text(0.64, y, c["driven"].replace("_", " "), fontsize=4.4,
                ha="left", va="center")
        ax.text(0.46, y + 0.045, c["kind"].replace("_", " "), fontsize=3.6,
                ha="center", color=MOTION_COLOR)
        if c.get("ratio_symbol"):
            ax.text(0.46, y - 0.05, f"{c['ratio_symbol']} - unresolved ({c['resolved_by']})",
                    fontsize=3.3, ha="center", color="#8a6d00")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)


def _draw_access_panel(ax, bp, access_paths):
    """Who reaches what, through which opening, and what is unmet."""
    ax.set_axis_off()
    ax.set_title("access, reactions and limits", fontsize=8)
    lines = []
    for a in access_paths:
        mark = "OK " if a.get("satisfied") else "BLOCKED "
        lines.append(
            f"{mark}{a['agent']} -> {a['target']}"
            + (f" via {a['boundary_interface']}" if a.get("boundary_interface") else "")
        )
    for j in bp.get("kinematic_joints", []):
        lines.append(f"reaction: {j['parent']} <- {j['name']} ({j['type']}) <- {j['child']}")
    for p in bp.get("state_predicates", []):
        if p["predicate"] == "at_limit" and p["holds"]:
            lines.append(f"limit: {p['subject']} bounds the {p['state']} state")
    ax.text(0.0, 1.0, "\n".join(lines) or "-", fontsize=4.0, va="top",
            family="monospace")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)


def _axis_index(axis: str | None) -> int:
    return {"x": 0, "y": 1, "z": 2}.get(axis or "z", 2)


def _anchor_extent(anchor: dict, hosts: list[Block], name: str) -> Block | None:
    """Geometry for one topological anchor.

    The shape follows the topology, not a fraction of the host: an edge and an
    axis are lines, a corridor is a band along the travel, a contact surface is a
    thin patch between two members, a boundary is a plate on a named face. This is
    what makes a hinge read as a hinge rather than as a small box.
    """
    if not hosts:
        return None
    kind = anchor.get("kind")
    h = hosts[0]
    ai = _axis_index(anchor.get("axis"))
    thin = 0.07

    if kind == "edge":
        # A line on a named face of the host. Which edge is a declared freedom, so
        # it is drawn at one edge of that face and dashed like any derived extent.
        face = (anchor.get("faces") or ["+Z"])[0]
        fi = _axis_index(face[1].lower())
        sign = 1 if face[0] == "+" else -1
        long_axis = 0 if fi != 0 else 1
        c = list(h.c)
        c[fi] = h.c[fi] + sign * h.s[fi] / 2
        other = 3 - fi - long_axis
        c[other] = h.c[other] - h.s[other] / 2
        size = [thin, thin, thin]
        size[long_axis] = h.s[long_axis] * 0.92
        return Block(name, *c, *size, JOINT_COLOR, 0.55, "topology_edge")

    if kind == "axis":
        c, size = list(h.c), [thin, thin, thin]
        span = anchor.get("span") or []
        station = anchor.get("station")
        if span:
            size[ai] = H * 0.62
            c[ai] = H * 0.50
        elif station in ("negative_end", "range_min"):
            size[ai] = H * 0.16
            c[ai] = H * 0.14
        elif station in ("positive_end", "range_max"):
            size[ai] = H * 0.16
            c[ai] = H * 0.86
        else:
            size[ai] = h.s[ai] * 1.25
        return Block(name, *c, *size, JOINT_COLOR, 0.55, "topology_axis")

    if kind == "corridor":
        c, size = list(h.c), [h.s[0] * 0.45, h.s[1] * 0.45, h.s[2]]
        size[ai] = H * 0.70
        c[ai] = H * 0.52
        return Block(name, *c, *size, JOINT_COLOR, 0.22, "topology_corridor")

    if kind == "contact_surface":
        other = hosts[1] if len(hosts) > 1 else None
        c = list(_contact_centre(h, other) if other else h.c)
        size = [max(h.s[i] * 0.55, 0.12) for i in range(3)]
        normal = ai
        if other is not None:
            deltas = [abs(h.c[i] - other.c[i]) for i in range(3)]
            normal = deltas.index(max(deltas))
        size[normal] = thin
        return Block(name, *c, *size, FEATURE_COLOR, 0.45, "topology_contact")

    if kind == "boundary":
        face = (anchor.get("faces") or ["-Y"])[0]
        fi = _axis_index(face[1].lower())
        sign = 1 if face[0] == "+" else -1
        c, size = [0.0, 0.0, H / 2], [W * 0.8, D * 0.8, H * 0.8]
        c[fi] = (W, D, H)[fi] / 2 * sign + (H / 2 if fi == 2 else 0.0)
        size[fi] = thin
        return Block(name, *c, *size, INTERFACE_COLOR, 0.20, "topology_boundary")

    return None


def _derived_extents(bp, bodies: list[Block]) -> list[Block]:
    """Spatial extent for everything located by something else.

    Extent is now driven by the *topological anchor* the blueprint states, so a
    hinge is a line on an edge, a guide is a corridor along the travel, and a
    catch is a patch on a shared surface. Previously each of these was a small box
    scaled off its host, which said only "it is near this member".
    """
    by_name = {b.name: b for b in bodies}
    out: list[Block] = []

    for p in bp.get("placed_pieces", []):
        anchor = p.get("anchor")
        if not anchor:
            continue
        hosts = [by_name[n] for n in anchor.get("hosts", []) if n in by_name]
        blk = _anchor_extent(anchor, hosts, p["name"])
        if blk is not None:
            out.append(blk)

    placed = {p["name"]: p for p in bp.get("placed_pieces", [])}
    for con in bp.get("spatial_constraints", []):
        if con.get("relation") not in LOCALIZED_RELATIONS:
            continue
        anchor = con.get("anchor")
        if not anchor:
            continue
        hosts = [
            h for h in (_extent_of(n, by_name, placed) for n in anchor.get("hosts", []))
            if h is not None
        ]
        blk = _anchor_extent(anchor, hosts, con["relation"])
        if blk is not None:
            blk.color = STATUS_COLOR.get(con.get("status"), UNCHECKED_COLOR)
            blk.alpha = 0.20
            blk.kind = "engagement_region"
            out.append(blk)
    return out


def _surface_point(blk, toward) -> tuple:
    """The point on `blk`'s boundary nearest `toward`.

    Two members touch at their surfaces, not at their centroids. Using centroids
    puts the contact between a closure and a shell in mid-air, halfway inside the
    volume the shell encloses.
    """
    return tuple(
        min(max(toward[i], blk.c[i] - blk.s[i] / 2), blk.c[i] + blk.s[i] / 2)
        for i in range(3)
    )


def _contact_centre(a, b) -> tuple:
    """Where two members meet: midway between their nearest surfaces."""
    pa = _surface_point(a, b.c)
    pb = _surface_point(b, a.c)
    return tuple((pa[i] + pb[i]) / 2 for i in range(3))


def _extent_of(name, by_name, placed):
    """The block standing for an element - its own, or its host's if derived."""
    if name in by_name:
        return by_name[name]
    hosts = (placed.get(name) or {}).get("attached_to", [])
    for h in hosts:
        if h in by_name:
            return by_name[h]
    return None


def _joint_and_feature_marks(bp, bodies: list[Block]) -> list[tuple]:
    """Where each joint and feature sits, derived from the bodies it touches.

    Returns (name, kind, x, y, z, permits) tuples in nominal units. A joint sits at
    the midpoint of the bodies it connects; a feature sits on the boundary of its
    host. Neither has extent of its own.
    """
    by_name = {b.name: b for b in bodies}
    marks = []
    for p in bp.get("placed_pieces", []):
        klass = p.get("element_class", "body")
        if klass == "body":
            continue
        hosts = [by_name[n] for n in p.get("attached_to", []) if n in by_name]
        if not hosts:
            continue
        cx = sum(h.c[0] for h in hosts) / len(hosts)
        cy = sum(h.c[1] for h in hosts) / len(hosts)
        cz = sum(h.c[2] for h in hosts) / len(hosts)
        if klass == "feature" and len(hosts) == 1:
            # A feature sits on its host's surface, not at its centroid.
            h = hosts[0]
            cz = h.c[2] - h.s[2] / 2
        marks.append((p["name"], klass, cx, cy, cz, p.get("permits_motion", "fixed")))
    return marks


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


def _swept_axis(sv: dict[str, Any], piece: dict[str, Any] | None) -> str:
    """Which axis the element turns or travels about.

    A face-mounted element turns about that face's normal; anything else uses the
    frame's primary axis. Both are read from the blueprint, never assumed.
    """
    face = (piece or {}).get("face")
    if face:
        return face[1].lower()
    return "z"


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
        piece = next(
            (p for p in bp.get("placed_pieces", []) if p["name"] == sv["element"]), None
        )
        axis = _swept_axis(sv, piece)
        if shape == "prismatic":
            # A translating element sweeps its own section along the whole travel.
            out.append(
                Block(f"{sv['element']} sweep", cx, cy, H * 0.55,
                      src.s[0] * 1.05, src.s[1] * 1.05, H * 0.70,
                      SWEPT_COLOR, 0.20, "swept")
            )
        elif shape == "cylindrical":
            r = 0.30 if sv.get("external") else 0.24
            thin = 0.12
            sx, sy, sz = (
                (thin, r * 2, r * 2) if axis == "x"
                else (r * 2, thin, r * 2) if axis == "y"
                else (r * 2, r * 2, thin)
            )
            b = Block(f"{sv['element']} sweep", cx, cy, cz, sx, sy, sz,
                      SWEPT_COLOR, 0.22, "swept_cylinder")
            b.axis = axis
            b.radius = r
            out.append(b)
        elif shape == "helical":
            b = Block(f"{sv['element']} sweep", cx, cy, H * 0.55,
                      src.s[0] * 1.15, src.s[1] * 1.15, H * 0.70,
                      SWEPT_COLOR, 0.20, "swept_helix")
            b.axis = axis
            b.radius = max(src.s[0], src.s[1]) * 0.6
            out.append(b)
        elif shape == "deformation":
            b = Block(f"{sv['element']} sweep", cx, cy, cz,
                      src.s[0] * 1.45, src.s[1] * 1.45, src.s[2] * 1.25,
                      SWEPT_COLOR, 0.18, "swept_deformation")
            out.append(b)
        else:
            # An unspecified motion gets a marker, never a guessed envelope.
            b = Block(f"{sv['element']} motion unspecified", cx, cy, cz,
                      0.16, 0.16, 0.16, VIOLATED_COLOR, 0.0, "swept_unknown")
            out.append(b)
    return out


# ---------------------------------------------------------------------------
# A/C/D/E/F - behaviour and review glyph layers, all 2D
# ---------------------------------------------------------------------------
def _projected(blk, ai, bi):
    return blk.c[ai], blk.c[bi]


def _volume(blk) -> float:
    return blk.s[0] * blk.s[1] * blk.s[2]


def _draw_swept_2d(ax, blk, ai, bi, plane):
    """A swept envelope drawn as the shape its motion actually sweeps."""
    c, sz = blk.c, blk.s
    axis_index = {"x": 0, "y": 1, "z": 2}
    if blk.kind == "swept_cylinder" and blk.radius:
        # Seen along its own axis a rotation sweeps a circle; seen across it, a band.
        if axis_index.get(blk.axis or "z") not in (ai, bi):
            ax.add_patch(mpatches.Circle(
                _projected(blk, ai, bi), blk.radius, facecolor=SWEPT_COLOR,
                alpha=0.25, edgecolor=MOTION_COLOR, linewidth=0.6, zorder=2))
            return
    if blk.kind == "swept_unknown":
        x, y = _projected(blk, ai, bi)
        ax.plot(x, y, marker="o", ms=7, mfc="none", mec=VIOLATED_COLOR, mew=1.2, zorder=9)
        ax.text(x, y, "?", fontsize=5, color=VIOLATED_COLOR, ha="center",
                va="center", zorder=10)
        return
    style = "--" if blk.kind == "swept_deformation" else "-"
    ax.add_patch(mpatches.Rectangle(
        (c[ai] - sz[ai] / 2, c[bi] - sz[bi] / 2), sz[ai], sz[bi],
        facecolor=SWEPT_COLOR, alpha=0.20, edgecolor=MOTION_COLOR,
        linewidth=0.6, linestyle=style, zorder=2))


def _motion_axis(bp: dict[str, Any], piece: dict[str, Any]) -> str:
    """The axis a body moves about, taken from the joint that permits the motion.

    A motion axis is a property of the joint, not of the moving body. Where a
    permitting joint sits on a product face, that face's normal is the axis;
    otherwise the frame's primary axis applies. Nothing is guessed from a name.
    """
    for other in bp.get("placed_pieces", []):
        if other.get("element_class") != "joint":
            continue
        if piece["name"] not in other.get("attached_to", []):
            continue
        if other.get("permits_motion") != piece.get("motion_kind"):
            continue
        face = other.get("face") or piece.get("face")
        if face:
            return face[1].lower()
    face = piece.get("face")
    if face:
        return face[1].lower()
    return str((bp.get("reference_frame") or {}).get("primary_axis", "z"))


def _draw_joints_and_features(ax, bp, pieces, ai, bi):
    """Joints as pivots or sliders on the members they join; features as small marks."""
    marks = _joint_and_feature_marks(bp, pieces)
    extents = {b.name: b for b in _derived_extents(bp, pieces)}
    for name, klass, cx, cy, cz, permits in marks:
        # Sit the glyph on the derived region, so symbol and extent agree.
        blk = extents.get(name)
        pos = blk.c if blk is not None else (cx, cy, cz)
        x, y = pos[ai], pos[bi]
        if klass == "joint":
            marker = "o" if permits == "rotation" else "s"
            ax.plot(x, y, marker=marker, ms=7.5, mfc="white", mec=JOINT_COLOR,
                    mew=1.4, zorder=10)
            ax.plot(x, y, marker=".", ms=2.5, color=JOINT_COLOR, zorder=11)
        else:
            ax.plot(x, y, marker="^", ms=5.0, mfc=FEATURE_COLOR, mec="#333333",
                    mew=0.5, zorder=10)
        ax.text(x, y - 0.13, name.replace("_", " "), fontsize=3.8, ha="center",
                va="top", color="#333333", zorder=11)


def _draw_motion_glyphs(ax, bp, pieces, ai, bi):
    """One glyph per declared motion kind. Nothing is drawn for a fixed element."""
    by_name = {b.name: b for b in pieces}
    axis_index = {"x": 0, "y": 1, "z": 2}
    for p in bp.get("placed_pieces", []):
        blk = by_name.get(p["name"])
        if blk is None:
            continue
        if p.get("element_class", "body") != "body":
            continue  # a joint permits motion; it does not perform it
        kind = p.get("motion_kind")
        x, y = _projected(blk, ai, bi)
        r = max(blk.s[ai], blk.s[bi]) * 0.62 + 0.10
        axis = _motion_axis(bp, p)

        if kind == "rotation":
            if axis_index.get(axis) not in (ai, bi):
                ax.add_patch(mpatches.Arc((x, y), r * 2, r * 2, theta1=25, theta2=305,
                                          color=MOTION_COLOR, lw=1.1, zorder=8))
                ax.annotate("", xy=(x + r * 0.95, y + r * 0.30), xytext=(x + r, y),
                            arrowprops=dict(arrowstyle="-|>", color=MOTION_COLOR, lw=1.0),
                            zorder=8)
            else:
                ax.annotate("", xy=(x, y + r), xytext=(x, y - r),
                            arrowprops=dict(arrowstyle="<|-|>", color=MOTION_COLOR,
                                            lw=0.9, ls=":"), zorder=8)
        elif kind == "translation":
            span = blk.s[bi] * 0.75 + 0.18
            ax.annotate("", xy=(x, y + span), xytext=(x, y - span),
                        arrowprops=dict(arrowstyle="<|-|>", color=MOTION_COLOR, lw=1.3),
                        zorder=8)
        elif kind == "rotation_translation":
            ax.add_patch(mpatches.Arc((x, y), r * 1.6, r * 1.6, theta1=200, theta2=340,
                                      color=MOTION_COLOR, lw=1.0, zorder=8))
            ax.annotate("", xy=(x, y + r), xytext=(x, y - r),
                        arrowprops=dict(arrowstyle="-|>", color=MOTION_COLOR, lw=1.1),
                        zorder=8)
        elif kind == "compliant_deformation":
            ax.add_patch(mpatches.Rectangle(
                (x - blk.s[ai] * 0.5 + 0.06, y - blk.s[bi] * 0.5 + 0.06),
                blk.s[ai], blk.s[bi], facecolor="none", edgecolor=MOTION_COLOR,
                lw=0.9, ls="--", zorder=8))
        elif kind == "unspecified":
            ax.plot(x, y, marker="o", ms=7, mfc="none", mec=VIOLATED_COLOR,
                    mew=1.2, zorder=9)


def _draw_interface_glyphs(ax, bp, pieces, ai, bi):
    """One mark per declared spatial relation, coloured by whether it is realizable."""
    by_name = {b.name: b for b in pieces}
    for c in bp.get("spatial_constraints", []):
        a, b = by_name.get(c["between"][0]), by_name.get(c["between"][1])
        if a is None or b is None:
            continue
        ax0, ay0 = _projected(a, ai, bi)
        bx0, by0 = _projected(b, ai, bi)
        colour = STATUS_COLOR.get(c.get("status"), UNCHECKED_COLOR)
        style = {"satisfied": "-", "violated": "-", "not_checkable": ":"}.get(
            c.get("status"), ":")
        ax.plot([ax0, bx0], [ay0, by0], color=colour, lw=0.8, ls=style,
                alpha=0.85, zorder=6)
        mark, _label = INTERFACE_MARK.get(c.get("relation"), ("+", "relation"))
        # The mark sits where the members meet - on the nearer face of the smaller
        # member - not at the midpoint of two centroids.
        small, large = (a, b) if _volume(a) <= _volume(b) else (b, a)
        sx, sy = _projected(small, ai, bi)
        lx, ly = _projected(large, ai, bi)
        d = math.hypot(lx - sx, ly - sy) or 1.0
        reach = min(max(small.s[ai], small.s[bi]) / 2, d * 0.5)
        mx = sx + (lx - sx) / d * reach
        my = sy + (ly - sy) / d * reach
        ax.plot(mx, my, marker=mark, ms=5.0, color=colour, zorder=7)
        if c.get("status") == "violated":
            ax.plot(mx, my, marker="x", ms=9, color=VIOLATED_COLOR, mew=1.6, zorder=8)


def _draw_review_overlay(ax, bp, blocks, ai, bi):
    """Annotation callouts and numbered issue markers."""
    by_name = {b.name: b for b in blocks}
    for i, a in enumerate(bp.get("annotations", [])):
        blk = by_name.get(a.get("subject"))
        if blk is None:
            continue
        x, y = _projected(blk, ai, bi)
        dx = 0.55 if i % 2 == 0 else -0.55
        dy = 0.10 * ((i % 5) - 2)
        ax.annotate(
            a.get("note", ""), xy=(x, y), xytext=(x + dx, y + dy), fontsize=3.6,
            ha="left" if dx > 0 else "right", va="center", color="#333333",
            arrowprops=dict(arrowstyle="-", color="#999999", lw=0.4), zorder=11,
        )
    for n, issue in enumerate(bp.get("issues", []), start=1):
        for region in issue.get("regions", []):
            blk = by_name.get(region)
            if blk is None:
                continue
            x, y = _projected(blk, ai, bi)
            ax.plot(x, y, marker="o", ms=8, mfc="white", mec=ISSUE_COLOR,
                    mew=1.0, zorder=12)
            ax.text(x, y, str(n), fontsize=4.2, color=ISSUE_COLOR, ha="center",
                    va="center", zorder=13)
            break


def _draw_iso(ax, blocks, bp):
    for b in blocks:
        polys = _faces(_box(*b.c, *b.s))
        col = Poly3DCollection(
            polys, alpha=b.alpha, facecolor=b.color,
            edgecolor=(
                b.color if b.kind in DERIVED_KINDS
                else "#333333" if b.kind != "shell" else "#666666"
            ),
            linewidths=0.4,
            linestyles="--" if b.kind in DERIVED_KINDS else "-",
        )
        ax.add_collection3d(col)
        if b.kind not in ("shell", "engagement_region") and not b.kind.startswith("swept"):
            ax.text(b.c[0], b.c[1], b.c[2], b.name.replace("_", " "),
                    fontsize=5.2, ha="center", va="center", zorder=10)

    frame = bp.get("reference_frame") or {}
    ax.plot([0, 0], [0, 0], [-0.15, H + 0.15], color="#d62728", lw=1.4, ls="--")
    ax.text(0, 0, H + 0.25, f"+{str(frame.get('primary_axis', 'z')).upper()}",
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
    n_derived = 0
    for blk in blocks:
        if hide_shell and blk.kind == "shell":
            continue
        if blk.kind.startswith("swept"):
            _draw_swept_2d(ax, blk, ai, bi, plane)
            continue
        if blk.kind in DERIVED_KINDS:
            c, sz = blk.c, blk.s
            ax.add_patch(mpatches.Rectangle(
                (c[ai] - sz[ai] / 2, c[bi] - sz[bi] / 2), sz[ai], sz[bi],
                facecolor=blk.color, alpha=blk.alpha, edgecolor=blk.color,
                linewidth=0.8, linestyle="--", zorder=5))
            if blk.kind != "engagement_region":
                off = 0.06 + 0.085 * (n_derived % 3)
                n_derived += 1
                ax.text(c[ai], c[bi] - sz[bi] / 2 - off, blk.name.replace("_", " "),
                        fontsize=3.8, ha="center", va="top", color=blk.color, zorder=6)
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


def render_concept(bp: dict[str, Any], out_dir: Path, stem: str = "concept_layout",
                   access_paths: list | None = None) -> list[str]:
    """Render the blueprint. Returns the paths written."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    try:
        pieces = _layout(bp)
        derived = _derived_extents(bp, pieces)
        swept = _swept_blocks(bp, pieces)
        regions = _region_blocks(bp)
        # Spatial layer first, glyphs on top. A joint, a feature and an engagement
        # all keep an extent; the glyph says what that extent does.
        blocks = pieces + derived + swept

        # An explicit grid, not tight_layout: mixing a 3D axis into an auto-laid
        # grid scrambles the panel alignment and makes the sheet unreadable.
        states = []
        for pose in bp.get("state_poses", []):
            if pose["state"] not in states:
                states.append(pose["state"])
        ncol = max(len(states) + 1, 4)

        fig = plt.figure(figsize=(3.6 * ncol, 9.6), dpi=160)
        gs = fig.add_gridspec(
            2, ncol, left=0.012, right=0.988, top=0.87, bottom=0.03,
            wspace=0.10, hspace=0.20,
        )
        frame = bp.get("reference_frame") or {}
        n_block = sum(
            1 for v in bp.get("state_validations", []) if not v.get("feasible")
        )
        fig.suptitle(
            f"{bp.get('source_candidate_id', '?')} - state sequence: "
            + "  ->  ".join(states)
            + f"\nprincipal axis {str(frame.get('primary_axis', '?')).upper()} "
            f"({frame.get('primary_motion', '?')})   |   "
            f"{len(bp.get('state_validations', []))} transitions, {n_block} not feasible"
            "\nqualitative state model - NOT geometry, NOT to scale, non-authoritative",
            fontsize=9,
        )

        # Row 1: the operating sequence, front projection.
        for k, st in enumerate(states):
            _draw_state_panel(fig.add_subplot(gs[0, k]), bp, st)
        _draw_chain_panel(fig.add_subplot(gs[0, ncol - 1]), bp)

        # Row 2: the same sequence in side projection, so a swing is visible.
        for k, st in enumerate(states):
            _draw_state_panel(fig.add_subplot(gs[1, k]), bp, st, side=True)

        if len(states) + 1 < ncol:
            _draw_access_panel(fig.add_subplot(gs[1, ncol - 2]), bp,
                               bp.get("_access_paths", []))
        legend_ax = fig.add_subplot(gs[1, ncol - 1])
        legend_ax.set_axis_off()
        handles = [
            mpatches.Patch(color=c, label=k.replace("_", " "))
            for k, c in KIND_COLOR.items()
            if any(p.get("kind") == k for p in bp.get("placed_pieces", []))
        ]
        handles += [
            mlines.Line2D([], [], color=JOINT_COLOR, marker="o", ls="none",
                          mfc="white", mew=1.5, ms=7, label="revolute joint"),
            mlines.Line2D([], [], color=JOINT_COLOR, marker="s", ls="none",
                          mfc="white", mew=1.5, ms=6, label="prismatic joint"),
            mlines.Line2D([], [], color=JOINT_COLOR, marker="H", ls="none",
                          mfc="white", mew=1.5, ms=6, label="helical joint"),
        ]
        handles += [
            mlines.Line2D([], [], color=col, marker=mk, ls="none", ms=6, label=lab)
            for kind, (mk, col, lab) in sorted(INTERACTION_STYLE.items())
            if any(i["kind"] == kind for i in bp.get("state_interactions", []))
        ]
        legend_ax.legend(handles=handles, loc="upper left", fontsize=5.6, frameon=False)
        verdicts = "\n".join(
            f"{'FEASIBLE' if v['feasible'] else 'BLOCKED  '} {v['transition']}"
            for v in bp.get("state_validations", [])
        )
        legend_ax.text(0.0, 0.34, verdicts, fontsize=4.6, va="top", family="monospace")
        legend_ax.text(
            0.0, 0.16,
            "envelopes are conservative over-estimates:\n"
            "they can expose a necessary overlap,\n"
            "never certify clearance",
            fontsize=4.2, va="top", color="#8a6d00",
        )

        path = out_dir / f"{stem}.png"
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        written.append(str(path))

        # The coverage report ships with the image: a reviewer can see what was
        # drawn, what was deliberately not, and why.
        report = out_dir / "render_coverage.json"
        report.write_text(json.dumps(audit(bp), indent=2, sort_keys=True) + "\n")
        written.append(str(report))
    except Exception:  # pragma: no cover - a render must never fail a run
        plt.close("all")
    return written
