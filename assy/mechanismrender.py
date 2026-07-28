"""Mechanism renderer - draws the kinematic model, decides nothing.

Every polygon is the projection of a real solid at a real pose. A hinged plate at
105 degrees draws as a rotated quadrilateral because it *is* one; nothing is
approximated by an axis-aligned box, and no position originates here.

Scale is the estimate carried by the model. Where a dimension came from a stated
requirement the drawing is to that proportion; where it is a placeholder the
drawing says so.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

from assy.geometry import (
    EstimateBasis, FormClass, Frame, Solid, Vec3, world_corners,
)

FORM_COLOR = {
    FormClass.SHELL: "#9aa0a6",
    FormClass.PLATE: "#4c78a8",
    FormClass.SHAFT: "#54a24b",
    FormClass.RAIL: "#e45756",
    FormClass.COLLAR: "#b279a2",
    FormClass.BLOCK: "#e07a5f",
    FormClass.LINK: "#f58518",
    FormClass.FLEXIBLE: "#72b7b2",
}

JOINT_MARK = {"revolute": "o", "prismatic": "s", "helical": "H", "fixed": "P"}
JOINT_COLOR = "#5b2c8d"


def _hull(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Convex hull, so a rotated box projects as the quad it actually is."""
    pts = sorted(set(points))
    if len(pts) <= 2:
        return pts

    def half(seq):
        out: list[tuple[float, float]] = []
        for p in seq:
            while len(out) >= 2:
                (x1, y1), (x2, y2) = out[-2], out[-1]
                if (x2 - x1) * (p[1] - y1) - (y2 - y1) * (p[0] - x1) > 0:
                    break
                out.pop()
            out.append(p)
        return out[:-1]

    return half(pts) + half(reversed(pts))


def _project(corners: list[Vec3], plane: str) -> list[tuple[float, float]]:
    if plane == "front":
        return [(c.x, c.z) for c in corners]
    if plane == "side":
        return [(c.y, c.z) for c in corners]
    return [(c.x, c.y) for c in corners]


# A projection plane is spanned by two axes; a rotation about an axis is only
# visible in the plane perpendicular to it.
PLANE_AXES = {"front": ("x", "z"), "side": ("y", "z"), "top": ("x", "y")}
PERPENDICULAR_TO = {"y": "front", "x": "side", "z": "top"}


def _views(model) -> list[str]:
    """The two planes that show this mechanism do what it exists to do.

    A view is not a presentation choice; it either carries the motion or it does
    not, and the two motion kinds project oppositely:

      * a **rotation** about an axis is visible only in the plane perpendicular
        to that axis - in any plane containing it, the body turns and the
        silhouette never changes;
      * a **translation** along an axis is visible only in a plane containing
        it - perpendicular to it, the body travels and never moves.

    The axis is taken from the joint driving the *output* element. A mechanism
    exists to produce its output motion, so that is the motion the drawing has to
    show; ranking by coordinate magnitude instead just picks the fastest input.
    """
    chain = [n for n in model.chain if n in model.bodies]
    ranked = list(reversed(chain)) + sorted(model.bodies)
    for name in ranked:
        joints = [
            j for j in model.joints.values()
            if j.type.value != "fixed" and j.child == name
        ]
        if not joints:
            continue
        joint = joints[0]
        turning = joint.type.value in ("revolute", "helical")
        primary = (
            PERPENDICULAR_TO[joint.axis] if turning
            else next(pl for pl in ("front", "side") if joint.axis in PLANE_AXES[pl])
        )
        # The second view must complement the first: it carries the axis the
        # primary view drops, so the layout stays legible in all three.
        secondary = next(
            pl for pl in ("front", "side", "top")
            if pl != primary and (joint.axis in PLANE_AXES[pl]) is turning
        )
        return [primary, secondary]
    return ["front", "side"]


def _draw_solid(ax, solid: Solid, frame, plane: str, *, label: bool = True) -> None:
    poly = _hull(_project(world_corners(solid, frame), plane))
    if len(poly) < 3:
        return
    shell = solid.form is FormClass.SHELL
    ax.add_patch(mpatches.Polygon(
        poly, closed=True, facecolor=FORM_COLOR[solid.form],
        alpha=0.12 if shell else 0.85,
        edgecolor="#555555" if shell else "#222222",
        linewidth=1.0 if shell else 0.7,
        linestyle="--" if shell else "-", zorder=2 if shell else 4))
    if shell:
        cav = solid.cavity_half()
        if cav is not None:
            inner = Solid(name=solid.name + ":cavity", form=FormClass.BLOCK,
                          params=solid.params)
            pts = [
                frame.place(Vec3(sx * cav.x, sy * cav.y, sz * cav.z))
                for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)
            ]
            ax.add_patch(mpatches.Polygon(
                _hull(_project(pts, plane)), closed=True, facecolor="white",
                alpha=0.55, edgecolor="#999999", linewidth=0.5,
                linestyle=":", zorder=3))
    if label and not shell:
        cx = sum(p[0] for p in poly) / len(poly)
        cy = sum(p[1] for p in poly) / len(poly)
        ax.text(cx, cy, solid.name.replace("_", " "), fontsize=3.8,
                ha="center", va="center", zorder=8)


def _panel(ax, model, state: str, plane: str, title: str) -> None:
    for name in sorted(model.bodies):
        body = model.bodies[name]
        if body.element_class.value != "body":
            continue
        frame = model.poses.get((state, name))
        if frame is None:
            continue
        _draw_solid(ax, body.solid, frame, plane)

    # Features have no pose of their own: they ride the host they sit on, so they
    # move with it and separate when it moves away.
    for name in sorted(model.bodies):
        body = model.bodies[name]
        if body.element_class.value != "feature":
            continue
        host = model.feature_hosts.get(name)
        frame = model.poses.get((state, host)) if host else None
        if frame is None:
            continue
        offset = model.bodies[host].solid.half()
        if name in getattr(model, "radial_features", ()):
            # At a radius on a turning host, so the host's rotation carries it.
            local = Vec3(max(offset.x, offset.y) * 0.68, 0.0, offset.z * 0.9)
        else:
            end = model.feature_seats.get(name, -1.0)
            local = Vec3(0.0, -offset.y * 0.75, end * offset.z)
        seat = Frame(frame.place(local), frame.rot)
        _draw_solid(ax, body.solid, seat, plane)

    # Joints at their real frames, so a hinge sits where the hinge is.
    for jname, joint in sorted(model.joints.items()):
        if joint.type.value == "fixed":
            continue
        parent = model.poses.get((state, joint.parent))
        if parent is None:
            continue
        origin = parent.compose(joint.frame_on_parent).origin
        px, py = _project([origin], plane)[0]
        ax.plot(px, py, marker=JOINT_MARK.get(joint.type.value, "o"), ms=8,
                mfc="white", mec=JOINT_COLOR, mew=1.5, zorder=10)
        q = model.coordinates.get((state, jname), 0.0)
        ax.text(px, py + 0.06, f"{joint.name}\n{joint.type.value} · {joint.axis} · q={q:.2f}",
                fontsize=3.0, color=JOINT_COLOR, ha="center", va="bottom", zorder=10)

    ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_color("#cccccc")
    ax.set_title(title, fontsize=8)


def render_mechanism(model, states: list[str], out_path: Path, subtitle: str = "") -> Path:
    n = max(len(states), 1)
    fig = plt.figure(figsize=(3.5 * (n + 1), 8.0), dpi=165)
    gs = fig.add_gridspec(2, n + 1, left=0.015, right=0.985, top=0.86, bottom=0.04,
                          wspace=0.10, hspace=0.16)

    derived = [
        s for b in model.bodies.values() for s in b.solid.params.values()
        if not s.is_guess
    ]
    fig.suptitle(
        f"{subtitle}\nstate sequence: " + "  →  ".join(states)
        + f"\n{len(derived)} dimension(s) derived from stated requirements; "
          "the rest are first-cut estimates for Stage 05-06 to resolve",
        fontsize=9,
    )

    upper, lower = _views(model)
    for i, st in enumerate(states):
        _panel(fig.add_subplot(gs[0, i]), model, st, upper, f"{st} — {upper}")
        _panel(fig.add_subplot(gs[1, i]), model, st, lower, f"{st} — {lower}")

    info = fig.add_subplot(gs[:, n]); info.set_axis_off()
    lines = ["JOINTS"]
    lines += [
        f"  {j.name}: {j.type.value} about {j.axis}  {j.parent}→{j.child}"
        for j in sorted(model.joints.values(), key=lambda x: x.name)
    ]
    lines += ["", "DIMENSIONS FROM REQUIREMENTS"]
    lines += [
        f"  {s.name} = {s.value:.2f}  ({s.basis.value})\n      {s.source}"
        for b in model.bodies.values() for s in b.solid.params.values()
        if s.basis is EstimateBasis.FROM_REQUIREMENT
    ] or ["  none — no stated bound reaches this architecture"]
    lines += ["", "PROPORTIONS DERIVED FROM THOSE"]
    lines += [
        f"  {s.name} = {s.value:.2f}  {s.source}"
        for b in model.bodies.values() for s in b.solid.params.values()
        if s.basis is EstimateBasis.PROPORTION_OF
    ] or ["  none"]
    guesses = [
        s.name for b in model.bodies.values() for s in b.solid.params.values()
        if s.is_guess
    ]
    lines += ["", f"PLACEHOLDERS ({len(guesses)}) — free for Stage 05-06", ]
    lines += ["  " + ", ".join(sorted(guesses)[:10]) + (" …" if len(guesses) > 10 else "")]
    if model.contradictions:
        lines += ["", "CONTRADICTIONS"] + [f"  {c}" for c in model.contradictions]
    if model.unplaced:
        lines += ["", "UNPLACED (blocking)"] + [f"  {u}" for u in model.unplaced]
    info.text(0.0, 1.0, "\n".join(lines), fontsize=4.4, va="top", family="monospace")
    info.set_xlim(0, 1); info.set_ylim(0, 1)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return out_path
