"""m24 (§14 T5v, D-M24-7) — the HIDDEN-MECHANISM DETAIL CLIP for latched_drawer: an ANIMATED SECTION.

The bottom clip is zero-protrusion — an exterior zoom shows an opaque shell, not the catch, so it is not
evidence. This replays the RECORDED seed-0 trajectory (`out/t2_ld_series.json`, written by
p_latch_bottomclip.py — NO re-sim here) through the y=15 section machinery: the compiled sub-solids
sectioned once, then the drawer parts shifted by the recorded x(t) each frame. Colours match the section
PNG (clip blue, bump red). The full story on one film: ride over the bump (the rigid-sweep interference
honestly visible, labelled "deflection by formula, D3") -> click behind the bump -> hold at 0.5·W_out ->
release pop at 1.5·W_out -> rail-end stop. HUD: drawer position + applied pull + latch state.

  ./bin/py m24_design_closure/section_anim.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "m0"))

import imageio.v2 as imageio  # noqa: E402
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from knowledge.templates.host_templates import latch_design_parts  # noqa: E402
from verify.t2_physics.mjcf import _to_trimesh  # noqa: E402

MM = 1000.0
COLORS = {"cabinet_body": "#9aa4b0", "bump": "#d05a5a", "drawer_body": "#e0b050", "clip": "#4a90d0"}
MOVING = {"drawer_body", "clip"}
Y_PLANE = 15.0          # the clip/bump plane
OUT_FPS = 25


def _polys(mesh, yc):
    """the y=yc section of a metres-mesh as a list of (N,2) [x,z] polylines in mm."""
    sec = mesh.section(plane_origin=(0, yc / MM, 0), plane_normal=(0, 1, 0))
    if sec is None:
        return []
    return [np.array(e)[:, [0, 2]] * MM for e in sec.discrete]


def main():
    out = ROOT / "m24_design_closure" / "out"
    series = json.loads((out / "t2_ld_series.json").read_text())
    tmp = out / "ld_mesh_assets"; tmp.mkdir(parents=True, exist_ok=True)
    parts = latch_design_parts()
    meshes = {k: _to_trimesh(v, tmp / f"{k}.stl") for k, v in parts.items()}
    base = {k: _polys(meshes[k], Y_PLANE) for k in meshes}          # section once

    t = series["t"]; xs = series["x_mm"]; pulls = series["pull_N"]
    states = series["state"]; phases = series["phase"]
    Wc = series["W_out_N"]; stroke = series["stroke_mm"]
    n = len(t); step = max(1, n // 130)                             # ~130 frames
    idx = list(range(0, n, step))

    frames = []
    fig, ax = plt.subplots(figsize=(9.0, 4.2), dpi=92)             # reused across frames (speed)
    for i in idx:
        x = xs[i]                                                   # drawer slide position (mm)
        ax.clear()
        for k, polys in base.items():
            for p in polys:
                px = p[:, 0] + (x if k in MOVING else 0.0)
                ax.fill(px, p[:, 1], color=COLORS[k], alpha=0.62, edgecolor=COLORS[k], lw=1.0,
                        label=k, zorder=(3 if k == "clip" else 2 if k == "bump" else 1))
        ax.set_aspect("equal"); ax.set_xlim(-38, 96); ax.set_ylim(-5, 17)
        ax.set_xlabel("x (mm)"); ax.set_ylabel("z (mm)"); ax.grid(alpha=0.18)
        h, l = ax.get_legend_handles_labels(); seen = dict(zip(l, h))
        ax.legend(seen.values(), seen.keys(), fontsize=7, loc="upper right", ncol=4)
        ph = phases[i]; st = states[i]; pull = pulls[i]
        ptag = {"close": "CLOSE — sliding shut (clip rides the bump)",
                "hold": f"HOLD — pull 0.5·W_out = {series['pull_hold_N']:.1f} N",
                "release": f"RELEASE — pull 1.5·W_out = {series['pull_release_N']:.1f} N"}.get(ph, ph)
        ax.set_title(f"latched_drawer — SECTION (y=15) clip↔bump  [recorded run, no re-sim]   "
                     f"W_out={Wc:.1f} N (inverse-Bayer)", fontsize=9)
        ax.text(0.012, 0.965, f"t={t[i]:5.2f}s   drawer {x:5.1f}/{stroke:.0f} mm   pull {pull:5.1f} N   "
                f"latch: {st}", transform=ax.transAxes, fontsize=8.5, va="top",
                bbox=dict(boxstyle="round,pad=0.3", fc="black", ec="none"), color="white")
        ax.text(0.012, 0.87, ptag, transform=ax.transAxes, fontsize=8.5, va="top",
                color=("#c0392b" if ph == "release" else "#1f6f43" if ph == "hold" else "#2c3e6b"))
        # the RIGID-SWEEP interference honesty: while closing and the clip is over the bump, the rigid
        # solids OVERLAP where a real elastic beam would DEFLECT — label it (D3).
        if ph == "close" and st == "—" and -2 < x < 16:
            ax.annotate("rigid sweep OVERLAPS here — the real beam DEFLECTS up\n"
                        "(elastic deflection by formula, D3; not rigid-body sim)",
                        xy=(18 + x, 2.0), xytext=(30, 12), fontsize=7.5, ha="left",
                        arrowprops=dict(arrowstyle="->", color="#8a6d0b", lw=1.0),
                        bbox=dict(boxstyle="round,pad=0.25", fc="#fffbe6", ec="#b8860b", lw=0.8))
        if st == "ENGAGED":
            ax.annotate("CLICK — barb behind the bump", xy=(18 + x, 1.5), xytext=(28, 13),
                        fontsize=8, color="#1f6f43", arrowprops=dict(arrowstyle="->", color="#1f6f43", lw=1.0))
        fig.tight_layout()
        fig.canvas.draw()
        w, hh = fig.canvas.get_width_height()
        buf = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8).reshape(hh, w, 4)[:, :, :3]
        buf = buf[:hh - hh % 2, :w - w % 2]                        # even dims for libx264/yuv420p
        frames.append(buf.copy())
    plt.close(fig)

    imageio.mimsave(out / "t2_ld_section.mp4", frames, fps=OUT_FPS, macro_block_size=1)
    print(f"wrote {out/'t2_ld_section.mp4'}  ({len(frames)} frames @ {OUT_FPS} fps)")
    # a representative still (the click) for the REVIEW
    ci = next((k for k, i in enumerate(idx) if states[i] == "ENGAGED"), len(idx) // 2)
    imageio.imwrite(str(out / "section_click_latched_drawer.png"), frames[ci])
    print(f"wrote section_click_latched_drawer.png")


if __name__ == "__main__":
    main()
