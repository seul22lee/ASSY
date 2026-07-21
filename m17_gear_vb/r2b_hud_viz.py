"""m17 — the R2b MONEY SHOT (polished, LONG cut). REUSES m1_gear/r2b_viz.capture() (no physics
rewrite, m1_gear left pristine/append-only) and wraps it in a presentation layer.

HONEST FRAMING (measured, not assumed): dt/25 does NOT "fix" R2b — it DELAYS it. Over a longer
horizon the fine-timestep run ALSO diverges, just far later: LEFT frozen dt=5e-4 blows up at ~0.24 s;
RIGHT dt/25=2e-5 rolls visibly for ~5.6x longer (to ~1.33 s, ~0.6 pinion rev) and THEN blows up too
(peak ~4.5e17 N). The fine timestep buys time, it does not remove the contact-formulation limit
(m17 D-M17-2/-3). The contrast that lands: left dead almost immediately, right rolling a long stretch
— then both dead.

  - side-by-side panels, each with a legible matplotlib HUD (label, T + OK/DIVERGED, CONTACT F, NCON,
    revs; vb._hud's 23-glyph dev font can't spell FROZEN/CONTACT/NCON so we render text here —
    m0/vb.py untouched);
  - a persistent BOTTOM STRIP: max-contact-force(t) on a LOG y-axis for BOTH runs across the FULL
    timeline with a moving cursor — left spikes to ~2e16 at 0.24 s then holds; right stays flat at
    ~0.01-0.6 N until ~1.33 s then spikes to ~4.5e17 and holds;
  - a painted REFERENCE TOOTH per gear (render-only marker geom, contype/conaffinity=0, density 0 —
    injected into the built MJCF here, so collision geoms + the explicit <inertial> are untouched) so
    the eye can follow the rotation and count mesh cycles;
  - a ~2.5 s TITLE CARD, then the long side-by-side roll played slow (~0.25x real-time).

  export MUJOCO_GL=egl ; ./bin/py m17_gear_vb/r2b_hud_viz.py
"""

from __future__ import annotations

import math
import sys
import xml.etree.ElementTree as ET
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
from gear_geom import GearSpec    # noqa: E402

OUT = Path(__file__).parent / "out"
r2b_viz.gear_mjcf.OUT = OUT       # keep build intermediates inside m17 (append-only w.r.t. m1_gear)
r2b_viz.gear_mjcf.MESHDIR = OUT / "assets"

W, H, DPI = 1000, 640, 100        # output frame px
T_END = 1.75                      # past the RIGHT run's own divergence (~1.33 s) + a beat of both-dead
CAPTURE_FPS = r2b_viz.FPS         # 60: sim-time cadence capture() keeps frames at
EXPORT_FPS = 15                   # play back at 15 -> 0.25x real-time (slow enough to track teeth)
RT = EXPORT_FPS / CAPTURE_FPS     # 0.25 -> "0.25x real-time"
TITLE_SEC, TAIL_SEC = 2.5, 1.5
OMEGA, RAMP = r2b_viz.OMEGA, r2b_viz.RAMP
MONO = {"family": "monospace", "fontsize": 11, "fontweight": "bold"}
MARK = {"pinion": "0.97 0.12 0.12 1", "gear": "0.12 0.25 0.98 1"}   # reference-tooth colours


def build_with_markers(tag="r2b_hud_long"):
    """Build the validated wedge pair, then INJECT one render-only reference-tooth marker per gear
    (contype/conaffinity=0, density 0, group 2). The explicit <inertial> and the collision geoms are
    left untouched, so mass/inertia and contact are identical to the baseline (verified by the peak
    numbers). Returns the marked XML path."""
    xml, meta = r2b_viz.gear_mjcf.build("involute", 4, tag=tag, op_cd=36.0)
    specs = {"pinion": (GearSpec(z=12, m=2.0, face_width=8.0), 0.0),
             "gear": (GearSpec(z=24, m=2.0, face_width=8.0),
                      r2b_viz.gear_mjcf.MESH_PHASE["involute"] + r2b_viz.gear_mjcf.BACKLASH_SEAT_DEG)}
    tree = ET.parse(xml); root = tree.getroot()
    world = root.find("worldbody")
    for body in world.findall("body"):
        name = body.get("name")
        if name not in specs:
            continue
        spec, phase = specs[name]
        r = 0.90 * spec.ra * 1e-3                       # just inside the tip, tooth-0 angle, metres
        a = math.radians(phase)
        x, y, z = r * math.cos(a), r * math.sin(a), 0.009   # sits on the +Z (camera-facing) top face
        ET.SubElement(body, "geom", name=f"{name}_refmark", type="box",
                      size="0.0016 0.0016 0.003", pos=f"{x:.6f} {y:.6f} {z:.6f}",
                      rgba=MARK[name], contype="0", conaffinity="0", group="2", density="0")
    marked = OUT / f"{tag}_marked.xml"
    tree.write(marked)
    return marked


def pinion_revs(t):
    ang = OMEGA * t * t / (2 * RAMP) if t < RAMP else OMEGA * RAMP / 2 + OMEGA * (t - RAMP)
    return ang / (2 * math.pi)


def _fN(f):
    return f"{f:.1e}" if f >= 1e4 else f"{f:8.1f}"


def _hud_text(ax, label, t, f, nc, dv, label_color, revs=None):
    status = "DIVERGED" if dv else "OK"
    rows = [(label, label_color),
            (f"T {t:5.3f} s   {status}", "#ff9a5a" if dv else "#8cffa0"),
            (f"CONTACT F {_fN(f)} N", "#ff7878" if f > 50 else "#c8c8ff"),
            (f"NCON {nc}", "#c8c8c8")]
    if revs is not None and not dv:
        rows.append((f"PINION {revs:4.2f} rev", "#c8c8ff"))
    y = 0.975
    for text, col in rows:
        ax.text(0.025, y, text, transform=ax.transAxes, va="top", ha="left", color=col,
                bbox=dict(facecolor="black", alpha=0.45, pad=1.5, edgecolor="none"), **MONO)
        y -= 0.072
    if dv:
        ax.text(0.5, 0.5, "DIVERGED\nPINION FLUNG", transform=ax.transAxes, ha="center",
                va="center", color="#ff5555", fontsize=20, fontweight="bold",
                bbox=dict(facecolor="black", alpha=0.4, pad=6, edgecolor="#ff5555"))


def make_frame(fr, fi, i, strip):
    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI, facecolor="#0d0d0d")
    gs = fig.add_gridspec(2, 2, height_ratios=[3.0, 1.5], hspace=0.10, wspace=0.02,
                          left=0.055, right=0.985, top=0.965, bottom=0.11)
    j_fi = min(i, len(fi["frames"]) - 1)
    t_cursor = fi["frames"][j_fi][1]
    if fi["diverged"] and j_fi == len(fi["frames"]) - 1:   # on the held final frame, advance the
        t_cursor = fi["t"][-1]                             # cursor to the actual divergence step so
    #                                                        the strip's green spike + held line show
    for col, (fset, label, lc, show_rev) in enumerate(
            ((fr, "FROZEN  dt = 5e-4", "#ffcf9a", False),
             (fi, "dt/25 = 2e-5", "#9affc0", True))):
        frames = fset["frames"]; j = min(i, len(frames) - 1)
        img, t, f, nc, dv = frames[j]
        if fset["diverged"] and j == len(frames) - 1:      # held final frame reads the divergence
            dv, f, t = True, max(fset["force"]), fset["t"][-1]
        ax = fig.add_subplot(gs[0, col]); ax.imshow(img); ax.axis("off")
        _hud_text(ax, label, t, f, nc, dv, lc, revs=(pinion_revs(t_cursor) if show_rev else None))

    frt, frf, fit, fif, fr_div_t, fr_peak, fi_div_t, fi_peak = strip
    axS = fig.add_subplot(gs[1, :]); axS.set_facecolor("#111111")
    # frozen (left) — spikes ~0.24 s, then pinned
    lm = frt <= t_cursor + 1e-9
    axS.plot(frt[lm], frf[lm], color="#e53e3e", lw=1.9,
             label=f"frozen 5e-4   →  {frf[lm][-1]:.1e} N" if lm.any() else "frozen 5e-4")
    if t_cursor > fr_div_t:
        axS.plot([fr_div_t, t_cursor], [fr_peak, fr_peak], color="#e53e3e", lw=1.1, ls=":", alpha=0.55)
    # dt/25 (right) — flat until ~1.33 s, then spikes HIGHER (delays R2b, doesn't remove it)
    rm = fit <= t_cursor + 1e-9
    if rm.any():
        rv = fif[rm][-1]
        rlab = f"dt/25 2e-5    →  {rv:.1e} N" if rv >= 1e4 else f"dt/25 2e-5    →  {rv:.2f} N"
    else:
        rlab = "dt/25 2e-5"
    axS.plot(fit[rm], fif[rm], color="#38c168", lw=1.9, label=rlab)
    if t_cursor > fi_div_t:
        axS.plot([fi_div_t, t_cursor], [fi_peak, fi_peak], color="#38c168", lw=1.1, ls=":", alpha=0.55)
    axS.axvline(t_cursor, color="#888888", lw=0.8, ls="--")
    axS.set_yscale("log"); axS.set_ylim(1e-2, 1e18); axS.set_xlim(0, T_END)
    axS.set_ylabel("contact F\n(N, log)", color="#dddddd", fontsize=8)
    axS.set_xlabel("t (s)", color="#dddddd", fontsize=8)
    axS.tick_params(colors="#bbbbbb", labelsize=7); axS.grid(alpha=0.2, which="both")
    for sp in axS.spines.values():
        sp.set_color("#444444")
    axS.legend(loc="center left", fontsize=8.5, facecolor="#1a1a1a", labelcolor="#eeeeee",
               framealpha=0.9)
    axS.set_title("dt/25 DELAYS the blow-up ~5.6x (0.24 s → 1.33 s) — it does not remove it. "
                  "Both diverge; that is R2b.", color="#dddddd", fontsize=8.5)
    fig.text(0.985, 0.992, f"{RT:.2f}x real-time", ha="right", va="top", color="#888888",
             fontsize=8.5, family="monospace")
    fig.canvas.draw()
    out = np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy()
    plt.close(fig)
    return out


def title_card():
    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI, facecolor="#0d0d0d")
    lines = [
        ("R2b — the fine timestep DELAYS, it does not fix", 20, "#ffffff", "bold", "normal"),
        ("SAME conjugate involute pair (z=12 / z=24), identical geometry.", 13, "#cccccc", "normal", "normal"),
        ("Only the solver timestep differs.", 13, "#cccccc", "normal", "normal"),
        ("LEFT:   frozen  dt = 5e-4    →   blows up at ~0.24 s", 14, "#e53e3e", "bold", "normal"),
        ("RIGHT:  dt/25 = 2e-5         →   rolls ~5.6x longer, then ALSO blows up (~1.33 s)", 12.5, "#38c168", "bold", "normal"),
        ("Painted teeth track the rotation. Played at 0.25x real-time.", 12, "#999999", "normal", "italic"),
    ]
    y = 0.78
    for text, size, color, weight, style in lines:
        fig.text(0.5, y, text, ha="center", va="center", fontsize=size, color=color,
                 fontweight=weight, style=style, family="monospace")
        y -= 0.115
    fig.canvas.draw()
    img = np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy()
    plt.close(fig)
    return img


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    xml = build_with_markers()
    fr = r2b_viz.capture(xml, r2b_viz.FROZEN, T_END)
    fi = r2b_viz.capture(xml, r2b_viz.FINE, T_END)
    print(f"frozen : diverged={fr['diverged']} t~{fr['t'][-1]:.3f} peak {max(fr['force']):.2e} N "
          f"({len(fr['frames'])} kept frames)")
    print(f"dt/25  : diverged={fi['diverged']} t~{fi['t'][-1]:.3f} peak {max(fi['force']):.2e} N "
          f"({len(fi['frames'])} kept frames, {pinion_revs(fi['t'][-1]):.2f} pinion rev)")
    # HONEST framing: BOTH diverge; the fine timestep only DELAYS the blow-up. Verify the frozen R2b
    # is unchanged (early divergence, ~2e16 peak) — that guards the untouched preset.
    assert fr["diverged"] and fr["t"][-1] < 0.4 and max(fr["force"]) > 1e15, \
        "frozen R2b changed — preset may have been touched; revert"
    assert fi["diverged"] and fi["t"][-1] > fr["t"][-1] * 3, \
        "dt/25 did not outlast frozen as expected — check the run"

    # strip data for BOTH runs; decimate but keep endpoints so each spike (the last recorded step) shows
    def dec(a, b, n=2500):
        a = np.array(a); b = np.maximum(np.array(b), 1e-2)
        if len(a) <= n:
            return a, b
        idx = np.unique(np.r_[np.linspace(0, len(a) - 1, n).astype(int), len(a) - 1])
        return a[idx], b[idx]
    frt, frf = dec(fr["t"], fr["force"]); fit, fif = dec(fi["t"], fi["force"])
    strip = (frt, frf, fit, fif, float(fr["t"][-1]), float(max(fr["force"])),
             float(fi["t"][-1]), float(max(fi["force"])))

    vid = [title_card()] * int(TITLE_SEC * EXPORT_FPS)
    n_action = max(len(fr["frames"]), len(fi["frames"]))
    last = None
    for i in range(n_action):
        last = make_frame(fr, fi, i, strip)
        vid.append(last)
    vid += [last] * int(TAIL_SEC * EXPORT_FPS)

    mp4 = OUT / "r2b_frozen_vs_fine_hud.mp4"
    imageio.mimsave(mp4, vid, fps=EXPORT_FPS, macro_block_size=1)
    imageio.imwrite(OUT / "r2b_frozen_vs_fine_hud.png", last)
    print(f"wrote {mp4.name} ({len(vid)} frames, {len(vid) / EXPORT_FPS:.1f} s @ {EXPORT_FPS}fps, "
          f"{RT:.2f}x real-time) + r2b_frozen_vs_fine_hud.png")


if __name__ == "__main__":
    main()
