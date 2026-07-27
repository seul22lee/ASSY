"""Visualization layer - derived and non-authoritative.

Every artifact here is a *rendering* of an authoritative domain object. Nothing
in this module may influence an engineering decision, and a failure to render
must never fail a run: each entry point returns the paths it managed to produce
and swallows its own errors.

The authoritative stage output is always ``output.json``.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

PALETTE = ["#3b7dd8", "#e08a1e", "#4aa564", "#c8443c", "#8a63bd", "#5b8fa8"]
GRID = {"color": "#d5d8dd", "linewidth": 0.6}


def _style(ax, title: str, xlabel: str, ylabel: str) -> None:
    ax.set_title(title, fontsize=11, pad=8)
    ax.set_xlabel(xlabel, fontsize=9)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.grid(True, **GRID)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.tick_params(labelsize=8)


def _save(fig, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=140, facecolor="white")
    plt.close(fig)
    return path


# --------------------------------------------------------------------------
# Simulation plots
# --------------------------------------------------------------------------
def _read_series(csv_path: Path) -> dict[str, list[float]]:
    with csv_path.open() as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        return {}
    return {k: [float(r[k]) for r in rows] for k in rows[0]}


def plot_trajectory(csv_path: Path, out_dir: Path, test_name: str) -> list[Path]:
    """Angle/displacement, force/torque, and contact-state plots for one test."""
    made: list[Path] = []
    try:
        series = _read_series(csv_path)
    except Exception:
        return made
    if not series or "time_s" not in series:
        return made
    t = series["time_s"]

    groups: list[tuple[str, list[str], str, str]] = [
        ("displacement", ["lid_angle_deg", "beam_deflection_deg"], "angle (deg)", "Lid and beam angle"),
        ("displacement", ["platform_height_mm"], "position (mm)", "Platform displacement"),
        ("force", ["input_torque_nmm", "release_force_n"], "torque (N.mm)", "Actuator effort"),
        ("force", ["peak_actuator_force_n"], "force (N)", "Actuator force"),
        ("contact", ["contact_force_n"], "force (N)", "Latch contact force"),
    ]
    for kind, keys, ylabel, title in groups:
        present = [k for k in keys if k in series and any(abs(v) > 1e-12 for v in series[k])]
        if not present:
            continue
        fig, ax = plt.subplots(figsize=(7.2, 3.2))
        for i, key in enumerate(present):
            ax.plot(t, series[key], color=PALETTE[i % len(PALETTE)], linewidth=1.6, label=key)
        _style(ax, f"{test_name} - {title}", "time (s)", ylabel)
        if len(present) > 1:
            ax.legend(fontsize=8, frameon=False)
        made.append(_save(fig, out_dir / f"{test_name}_{kind}.png"))

    if "latch_contact_state" in series:
        state = series["latch_contact_state"]
        if any(state):
            fig, ax = plt.subplots(figsize=(7.2, 2.0))
            ax.fill_between(t, 0, state, step="post", color=PALETTE[3], alpha=0.35)
            ax.plot(t, state, drawstyle="steps-post", color=PALETTE[3], linewidth=1.4)
            ax.set_ylim(-0.1, 1.2)
            ax.set_yticks([0, 1])
            ax.set_yticklabels(["clear", "engaged"])
            _style(ax, f"{test_name} - latch contact state", "time (s)", "")
            made.append(_save(fig, out_dir / f"{test_name}_contact_state.png"))
    return made


def plot_metric_summary(metrics: list[dict[str, Any]], out_dir: Path) -> Path | None:
    """Horizontal bar of extracted metrics, grouped by backend."""
    if not metrics:
        return None
    try:
        items = [m for m in metrics if isinstance(m.get("value"), (int, float))][:18]
        if not items:
            return None
        labels = [m["name"] for m in items]
        values = [float(m["value"]) for m in items]
        colors = [
            PALETTE[0] if str(m.get("method", "")).startswith("mujoco") else PALETTE[2]
            for m in items
        ]
        fig, ax = plt.subplots(figsize=(8.4, 0.34 * len(items) + 1.4))
        y = np.arange(len(items))
        ax.barh(y, values, color=colors, height=0.62)
        ax.set_yticks(y)
        ax.set_yticklabels(labels, fontsize=7.5)
        ax.invert_yaxis()
        for i, v in enumerate(values):
            ax.text(v, i, f"  {v:g}", va="center", fontsize=7)
        _style(ax, "Extracted metrics (blue = MuJoCo, green = analytical)", "value", "")
        ax.set_ylabel("")
        return _save(fig, out_dir / "metric_summary.png")
    except Exception:
        return None


def plot_analytical_summary(summary: dict[str, float], out_dir: Path) -> Path | None:
    """Force/strain summary for the compliant element."""
    if not summary:
        return None
    try:
        fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.4))
        forces = [
            ("insertion", summary.get("insertion_force_n", 0.0)),
            ("retention", summary.get("retention_force_n", 0.0)),
            ("release", summary.get("release_force_n", 0.0)),
            ("deflection", summary.get("deflection_force_n", 0.0)),
        ]
        names = [n for n, _ in forces]
        vals = [v if np.isfinite(v) else 0.0 for _, v in forces]
        axes[0].bar(names, vals, color=PALETTE[:4], width=0.6)
        for i, v in enumerate(vals):
            axes[0].text(i, v, f"{v:.2f}", ha="center", va="bottom", fontsize=8)
        _style(axes[0], "Snap-fit forces (analytical)", "", "force (N)")

        strain = summary.get("peak_strain", 0.0)
        allowable = summary.get("strain_allowable", 0.0)
        axes[1].bar(["peak", "allowable"], [strain, allowable],
                    color=[PALETTE[3] if strain > allowable else PALETTE[2], "#b8bcc4"], width=0.55)
        for i, v in enumerate([strain, allowable]):
            axes[1].text(i, v, f"{v * 100:.2f}%", ha="center", va="bottom", fontsize=8)
        _style(axes[1], "Peak strain vs allowable", "", "strain (-)")
        return _save(fig, out_dir / "analytical_summary.png")
    except Exception:
        return None


# --------------------------------------------------------------------------
# MuJoCo animation
# --------------------------------------------------------------------------
def animate(
    model_path: Path, out_path: Path, test: dict[str, Any], camera: str | None = None, fps: int = 30
) -> Path | None:
    """Render a test to mp4. Returns None if rendering is unavailable."""
    try:
        import imageio.v2 as imageio
        import mujoco

        model = mujoco.MjModel.from_xml_path(str(model_path))
        data = mujoco.MjData(model)
        mujoco.mj_resetData(model, data)

        for joint, value in (test.get("initial_conditions") or {}).items():
            i = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint)
            if i >= 0:
                data.qpos[model.jnt_qposadr[i]] = value
        mujoco.mj_forward(model, data)
        for act, value in (test.get("actuation") or {}).items():
            i = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, act)
            if i >= 0:
                data.ctrl[i] = value

        cam_id = -1
        if camera:
            cam_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_CAMERA, camera)
        renderer = mujoco.Renderer(model, 480, 640)
        duration = float(test.get("duration_s", 2.0))
        steps = int(duration / model.opt.timestep)
        every = max(1, int((1.0 / fps) / model.opt.timestep))

        frames = []
        for k in range(steps):
            mujoco.mj_step(model, data)
            if k % every == 0:
                if cam_id >= 0:
                    renderer.update_scene(data, camera=cam_id)
                else:
                    renderer.update_scene(data)
                frames.append(renderer.render())
        renderer.close()
        if not frames:
            return None
        out_path.parent.mkdir(parents=True, exist_ok=True)
        imageio.mimsave(str(out_path), frames, fps=fps, macro_block_size=1)
        return out_path
    except Exception:
        return None


# --------------------------------------------------------------------------
# CAD views
# --------------------------------------------------------------------------
def _load_meshes(parts: list[dict[str, Any]]):
    import trimesh

    loaded = []
    for p in parts:
        path = p.get("mesh_path")
        if not path or not Path(path).exists():
            continue
        try:
            mesh = trimesh.load(path, force="mesh")
            if mesh is not None and len(mesh.faces):
                loaded.append((p["part_id"], mesh))
        except Exception:
            continue
    return loaded


def render_cad_views(
    parts: list[dict[str, Any]],
    out_dir: Path,
    roles: dict[str, list[str]] | None = None,
) -> dict[str, Path]:
    """Isometric, transparent, section, and exploded views from the exported meshes.

    Enclosures are drawn near-transparent: an opaque housing hides exactly the
    internal mechanism a reviewer needs to see.
    """
    made: dict[str, Path] = {}
    try:
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    except Exception:
        return made
    meshes = _load_meshes(parts)
    if not meshes:
        return made
    roles = roles or {}

    def is_shell(name: str) -> bool:
        return "enclosure" in roles.get(name, [])

    def draw(ax, items, explode: float = 0.0, xray: bool = False):
        # Big parts first so smaller internals paint over them.
        order = sorted(range(len(items)), key=lambda i: -items[i][1].volume)
        for rank, i in enumerate(order):
            name, mesh = items[i]
            verts = np.array(mesh.vertices, dtype=float).copy()
            if explode:
                direction = np.array([0.0, 0.0, 1.0]) if i % 2 else np.array([1.0, 0.0, 0.0])
                verts += direction * explode * (i + 1)
            tri = verts[np.array(mesh.faces)]
            shell = is_shell(name)
            alpha = (0.10 if shell else 0.95) if xray else (0.35 if shell else 0.95)
            coll = Poly3DCollection(
                tri,
                alpha=alpha,
                facecolor=PALETTE[i % len(PALETTE)],
                edgecolor="#33383f" if shell and xray else "none",
                linewidths=0.15 if shell and xray else 0.0,
                zsort="min",
            )
            ax.add_collection3d(coll)
        allv = np.vstack([np.array(m.vertices) for _, m in items])
        centre = allv.mean(axis=0)
        span = max(allv.max(axis=0) - allv.min(axis=0)) * (0.62 + explode * 0.02)
        for setter, c in ((ax.set_xlim, centre[0]), (ax.set_ylim, centre[1]), (ax.set_zlim, centre[2])):
            setter(c - span, c + span)
        ax.set_box_aspect((1, 1, 1))
        ax.set_axis_off()

    def legend(ax, items):
        from matplotlib.patches import Patch

        handles = [
            Patch(facecolor=PALETTE[i % len(PALETTE)], label=name)
            for i, (name, _) in enumerate(items)
        ]
        ax.legend(handles=handles, fontsize=7.5, frameon=False, loc="upper left", ncol=2)

    for key, title, xray in (
        ("isometric", "Isometric", False),
        ("transparent", "Transparent (enclosure at 10% opacity)", True),
    ):
        try:
            fig = plt.figure(figsize=(7.2, 6.2))
            ax = fig.add_subplot(111, projection="3d")
            draw(ax, meshes, xray=xray)
            ax.view_init(elev=24, azim=-56)
            ax.set_title(title, fontsize=11)
            legend(ax, meshes)
            made[key] = _save(fig, out_dir / f"{key}.png")
        except Exception:
            pass

    try:
        fig = plt.figure(figsize=(7.0, 6.0))
        ax = fig.add_subplot(111, projection="3d")
        draw(ax, meshes, explode=6.0)
        ax.view_init(elev=20, azim=-60)
        ax.set_title("Exploded", fontsize=11)
        made["exploded"] = _save(fig, out_dir / "exploded.png")
    except Exception:
        pass

    # Section: slice every mesh on the XZ plane and draw the resulting outlines.
    try:
        fig, ax = plt.subplots(figsize=(7.0, 5.4))
        drew = False
        for i, (name, mesh) in enumerate(meshes):
            try:
                section = mesh.section(plane_origin=mesh.centroid, plane_normal=[0, 1, 0])
                if section is None:
                    continue
                planar, _ = section.to_2D()
                for entity in planar.entities:
                    pts = planar.vertices[entity.points]
                    ax.plot(pts[:, 0], pts[:, 1], color=PALETTE[i % len(PALETTE)],
                            linewidth=1.6, label=name if not drew else None)
                    drew = True
            except Exception:
                continue
        if drew:
            ax.set_aspect("equal")
            _style(ax, "Section through the assembly centroid (XZ plane)", "x (mm)", "z (mm)")
            handles, labels = ax.get_legend_handles_labels()
            if labels:
                ax.legend(fontsize=7.5, frameon=False, ncol=3)
            made["section"] = _save(fig, out_dir / "section.png")
        else:
            plt.close(fig)
    except Exception:
        pass

    return made
