"""m17 — the R2b MONEY SHOT (polished). REUSES m1_gear/r2b_viz.capture() (no rewrite, no re-render
of the physics) and wraps it in a presentation layer:

  - side-by-side panels: LEFT frozen preset dt=5e-4 (blows up) | RIGHT dt/25=2e-5 (rolls calmly),
    each with a legible per-frame HUD: panel label, T + OK/DIVERGED, CONTACT F (N), NCON
    (green=OK, orange=DIVERGED, red force text when >50 N — the same field/colour scheme as vb._hud,
    rendered here with matplotlib because vb._hud's 23-glyph dev font cannot spell FROZEN/CONTACT/
    NCON/DIVERGED; m0/vb.py is left untouched, append-only);
  - a persistent BOTTOM STRIP plotting max-contact-force(t) on a LOG y-axis for BOTH runs with a
    moving cursor, so the 16-orders-of-magnitude gap is visible AS IT HAPPENS — the key addition;
  - a 6-line TITLE CARD for the first ~1.5 s;
  - after the left run diverges its frame HOLDS with a "DIVERGED — PINION FLUNG" banner while the
    right run keeps rolling to the end.

m1_gear is left PRISTINE (append-only): this imports capture(), writes only to m17_gear_vb/out/.

  export MUJOCO_GL=egl ; ./bin/py m17_gear_vb/r2b_hud_viz.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import imageio.v2 as imageio
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "m0"))
sys.path.insert(0, str(ROOT / "m1_gear"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import r2b_viz                    # noqa: E402  the validated capture() harness (REUSED, not rewritten)
from p_gear import FPS            # noqa: E402

OUT = Path(__file__).parent / "out"
r2b_viz.gear_mjcf.OUT = OUT       # keep build intermediates inside m17 (append-only w.r.t. m1_gear)
r2b_viz.gear_mjcf.MESHDIR = OUT / "assets"

W, H, DPI = 1000, 640, 100        # output frame px
HOLD = 5                          # output frames per action frame (slows the 0.35 s action to ~2 s)
TITLE_SEC, TAIL_SEC = 1.5, 1.0
MONO = {"family": "monospace", "fontsize": 11, "fontweight": "bold"}


def _fig_to_rgb(fig):
    fig.canvas.draw()
    return np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy()


def _fN(f):
    return f"{f:.1e}" if f >= 1e4 else f"{f:8.1f}"


def _hud_text(ax, label, t, f, nc, dv, label_color):
    """The HUD block, top-left of a panel: label, T+status, CONTACT F, NCON."""
    status = "DIVERGED" if dv else "OK"
    rows = [(label, label_color),
            (f"T {t:5.3f} s   {status}", "#ff9a5a" if dv else "#8cffa0"),
            (f"CONTACT F {_fN(f)} N", "#ff7878" if f > 50 else "#c8c8ff"),
            (f"NCON {nc}", "#c8c8c8")]
    y = 0.975
    for text, col in rows:
        ax.text(0.025, y, text, transform=ax.transAxes, va="top", ha="left", color=col,
                bbox=dict(facecolor="black", alpha=0.45, pad=1.5, edgecolor="none"), **MONO)
        y -= 0.075
    if dv:
        ax.text(0.5, 0.5, "DIVERGED\nPINION FLUNG", transform=ax.transAxes, ha="center",
                va="center", color="#ff5555", fontsize=20, fontweight="bold",
                bbox=dict(facecolor="black", alpha=0.4, pad=6, edgecolor="#ff5555"))


def make_frame(fr, fi, i):
    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI, facecolor="#0d0d0d")
    gs = fig.add_gridspec(2, 2, height_ratios=[3.0, 1.5], hspace=0.10, wspace=0.02,
                          left=0.055, right=0.985, top=0.965, bottom=0.11)
    for col, (fset, label, lc) in enumerate(
            ((fr, "FROZEN  dt = 5e-4", "#ffcf9a"), (fi, "dt/25 = 2e-5", "#9affc0"))):
        frames = fset["frames"]; j = min(i, len(frames) - 1)
        img, t, f, nc, dv = frames[j]
        # capture() breaks on divergence without recording a diverged frame, so the held last frame
        # still reads OK/pre-spike. Once this run has diverged and we're on its final held frame,
        # reflect the DIVERGENCE and the actual PEAK force (the spike), matching the strip.
        if fset["diverged"] and j == len(frames) - 1:
            dv, f, t = True, max(fset["force"]), fset["t"][-1]
        ax = fig.add_subplot(gs[0, col]); ax.imshow(img); ax.axis("off")
        _hud_text(ax, label, t, f, nc, dv, lc)

    # bottom strip: log-y contact force, both runs, up to the cursor
    t_cursor = fi["frames"][min(i, len(fi["frames"]) - 1)][1]
    axS = fig.add_subplot(gs[1, :]); axS.set_facecolor("#111111")
    frt = np.array(fr["t"]); frf = np.maximum(np.array(fr["force"]), 1e-2)
    fit = np.array(fi["t"]); fif = np.maximum(np.array(fi["force"]), 1e-2)
    lm, rm = frt <= t_cursor + 1e-9, fit <= t_cursor + 1e-9
    axS.plot(frt[lm], frf[lm], color="#e53e3e", lw=1.9,
             label=f"frozen 5e-4   →  {frf[lm][-1]:.1e} N" if lm.any() else "frozen 5e-4")
    axS.plot(fit[rm], fif[rm], color="#38c168", lw=1.9,
             label=f"dt/25 2e-5    →  {fif[rm][-1]:.2f} N" if rm.any() else "dt/25 2e-5")
    axS.axvline(t_cursor, color="#888888", lw=0.8, ls="--")
    axS.set_yscale("log"); axS.set_ylim(1e-2, 1e18); axS.set_xlim(0, max(fit[-1], frt[-1]))
    axS.set_ylabel("contact F\n(N, log)", color="#dddddd", fontsize=8)
    axS.set_xlabel("t (s)", color="#dddddd", fontsize=8)
    axS.tick_params(colors="#bbbbbb", labelsize=7); axS.grid(alpha=0.2, which="both")
    for sp in axS.spines.values():
        sp.set_color("#444444")
    axS.legend(loc="center left", fontsize=8.5, facecolor="#1a1a1a", labelcolor="#eeeeee",
               framealpha=0.9)
    axS.set_title("16 orders of magnitude separate two runs of IDENTICAL geometry — that gap is R2b",
                  color="#dddddd", fontsize=8.5)
    img = _fig_to_rgb(fig); plt.close(fig)
    return img


def title_card():
    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI, facecolor="#0d0d0d")
    lines = [
        ("R2b — the contact-formulation blow-up", 21, "#ffffff", "bold", "normal"),
        ("SAME conjugate involute gear pair (z=12 / z=24), identical geometry.", 13, "#cccccc", "normal", "normal"),
        ("The ONLY difference is the solver timestep.", 13, "#cccccc", "normal", "normal"),
        ("LEFT:   frozen preset  dt = 5e-4    →   diverges", 14, "#e53e3e", "bold", "normal"),
        ("RIGHT:  dt/25 = 2e-5                →   rolls calmly", 14, "#38c168", "bold", "normal"),
        ("Watch the log-scale contact force below the gears.", 12, "#999999", "normal", "italic"),
    ]
    y = 0.78
    for text, size, color, weight, style in lines:
        fig.text(0.5, y, text, ha="center", va="center", fontsize=size, color=color,
                 fontweight=weight, style=style, family="monospace")
        y -= 0.115
    img = _fig_to_rgb(fig); plt.close(fig)
    return img


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    xml, meta = r2b_viz.gear_mjcf.build("involute", 4, tag="r2b_hud", op_cd=36.0)
    fr = r2b_viz.capture(xml, r2b_viz.FROZEN, 0.35)
    fi = r2b_viz.capture(xml, r2b_viz.FINE, 0.35)
    print(f"frozen : diverged={fr['diverged']} t~{fr['t'][-1]:.3f} peak {max(fr['force']):.2e} N "
          f"({len(fr['frames'])} frames)")
    print(f"dt/25  : diverged={fi['diverged']} t~{fi['t'][-1]:.3f} peak {max(fi['force']):.2e} N "
          f"({len(fi['frames'])} frames)")
    assert fr["diverged"] and not fi["diverged"], "R2b did not reproduce — check the render preset"

    vid = [title_card()] * int(TITLE_SEC * FPS)
    n_action = max(len(fr["frames"]), len(fi["frames"]))
    last = None
    for i in range(n_action):
        frame = make_frame(fr, fi, i)
        vid += [frame] * HOLD
        last = frame
    vid += [last] * int(TAIL_SEC * FPS)

    mp4 = OUT / "r2b_frozen_vs_fine_hud.mp4"
    imageio.mimsave(mp4, vid, fps=FPS, macro_block_size=1)
    imageio.imwrite(OUT / "r2b_frozen_vs_fine_hud.png", last)
    print(f"wrote {mp4.name} ({len(vid)} frames, {len(vid) / FPS:.1f} s @ {FPS}fps) + "
          f"r2b_frozen_vs_fine_hud.png")


if __name__ == "__main__":
    main()
