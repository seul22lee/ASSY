"""Diagnostic sections for the D-GEN-1 HOLD (visual review). Slices the ACTUAL compiled solids
at y=0 (ground truth, not a schematic) and plots the XZ cross-section with anchors (position +
normal arrows) and the insertion axis annotated.

  panel_section.png   board clip: shows the hook nose sits BELOW the board top and INSIDE its
                      edge — it does NOT overhang → the wrong nose topology (Defect 2).
  box_section.png     the box (correct): nose sits INSIDE the wall window with the designed y.

Run: ./bin/py m6_ms_closeout/diag_sections.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from build123d import export_stl

from knowledge.cards.snap_hook_geometry import carve
from knowledge.templates import flat_panel_mount, retained_board
from pipeline.s5_geometry import resolve_plan
from tasks.build_goldens import snap_panel, snap_starter
from pipeline.run_snap import _instantiate

OUT = Path(__file__).parent / "out"
TMP = Path("/tmp/_diag.stl")


def _section_xz(part, color, ax, label=None, y0=0.0):
    """Slice `part` at plane y=y0 and draw its XZ outline."""
    export_stl(part, str(TMP), tolerance=0.03, angular_tolerance=0.2)
    m = trimesh.load(TMP, force="mesh"); TMP.unlink()
    sec = m.section(plane_origin=[0, y0, 0], plane_normal=[0, 1, 0])
    if sec is None:
        return
    first = True
    for poly in sec.discrete:
        ax.fill(poly[:, 0], poly[:, 2], facecolor=color, edgecolor="#222", lw=0.8,
                alpha=0.55, label=(label if first else None), zorder=2)
        first = False


def _anchor(ax, pos, normal, name, col="#c0392b"):
    x, z = pos[0], pos[2]
    ax.plot(x, z, "o", color=col, ms=6, zorder=5)
    nx, nz = normal[0], normal[2]
    L = 4.0
    ax.annotate("", xy=(x + nx * L, z + nz * L), xytext=(x, z),
                arrowprops=dict(arrowstyle="-|>", color=col, lw=1.6), zorder=5)
    ax.annotate(name, (x, z), textcoords="offset points", xytext=(6, -10),
                fontsize=7, color=col)


def panel():
    plan = snap_panel()
    res, _ = resolve_plan(plan, frequent=False)
    r = res["E1"]
    pieces = _instantiate(plan)
    inst = plan.elements[0]
    binds = [b for b in plan.bindings if b.element_id == inst.id]
    cr = carve(pieces, inst, binds)
    d = [dd for dd in cr.dims if dd.root_xyz[0] > 0][0]   # right hook

    fig, ax = plt.subplots(figsize=(8.4, 5.4))
    _section_xz(cr.parts["M1"], "#7fb2e5", ax, "mount M1 (base + rails + hooks)")
    _section_xz(cr.parts["B1"], "#f6c453", ax, "board B1 (RETAINED — immutable)")

    # board top edge: an edge-overhang clip would curl the nose OVER this without touching the board
    ax.axhline(24, ls=":", color="#f6a", lw=1)
    ax.annotate("board TOP edge z=24  (an overhang clip would curl OVER here — cut nothing)", (-3, 24.4),
                fontsize=8, color="#b03a70")
    # the window-catch compilation CUTS a notch into the retained board — the illegal move
    nt = d.nose_tip_xyz
    ax.plot(nt[0], nt[2], "v", color="#8e44ad", ms=11, zorder=6)
    ax.annotate("WINDOW-catch compile cuts a NOTCH into the\nRETAINED board B1 (top-right corner) — "
                "illegal:\na foreign board/PCB may not be modified\n→ GEOM_INFEASIBLE at ⑥ (needs "
                "overhang, M-G-1)",
                (24.5, 23.4), textcoords="offset points", xytext=(-260, -34),
                fontsize=8, color="#8e44ad",
                arrowprops=dict(arrowstyle="-|>", color="#8e44ad", lw=1.2))
    # anchors
    for nm, a in flat_panel_mount().anchors.items():
        if a.position[0] > 0:
            _anchor(ax, a.position, a.normal, nm)
    for nm, a in retained_board().anchors.items():
        if a.position[0] > 0:
            _anchor(ax, a.position, a.normal, nm, col="#16794f")
    # insertion axis = growth dir (+Z here)
    ax.annotate("", xy=(30, 30), xytext=(30, 24),
                arrowprops=dict(arrowstyle="-|>", color="#333", lw=2))
    ax.annotate("insertion / growth  +Z", (30.5, 27), fontsize=8, rotation=90)

    ax.set_title(f"PANEL board-clip — section @ y=0 (right hook)\n"
                 f"⑥ now HONORS ⑤'s L: resolve L={r.L:.0f} = geometry L={d.L:.0f}mm (D-GEN-3)  ·  "
                 f"α_out={r.alpha_out_final:.0f}° SEPARABLE, W_sep={r.W_out_label}  ·  "
                 f"but window-catch cuts the retained board → INFEASIBLE", fontsize=8.5)
    ax.set_xlabel("X (mm)"); ax.set_ylabel("Z (mm)"); ax.set_aspect("equal")
    ax.set_xlim(-4, 40); ax.set_ylim(0, 33); ax.grid(alpha=0.25); ax.legend(loc="lower left", fontsize=7)
    fig.tight_layout(); fig.savefig(OUT / "panel_section.png", dpi=130); plt.close(fig)
    print(f"  panel_section.png   ⑥ honors L (resolve {r.L:.0f} = geom {d.L:.0f}); window-catch would "
          f"cut retained board B1 → GEOM_INFEASIBLE")


def box():
    plan = snap_starter()
    for pc in plan.pieces:
        if pc.id == "P1":
            pc.params.update({"box_l": 80.0, "box_w": 60.0, "box_h": 40.0, "wall": 2.0})
    res, _ = resolve_plan(plan, frequent=False)
    r = res[plan.elements[0].id]
    pieces = _instantiate(plan)
    for pid, bp in {"P1": {"box_l": 80.0, "box_w": 60.0, "box_h": 40.0, "wall": 2.0}}.items():
        pieces[pid].params.update(bp)
    inst = plan.elements[0]
    binds = [b for b in plan.bindings if b.element_id == inst.id]
    cr = carve(pieces, inst, binds)
    d = [dd for dd in cr.dims if dd.root_xyz[0] > 0][0]

    fig, ax = plt.subplots(figsize=(8.4, 5.4))
    _section_xz(cr.parts[binds[0].piece_id], "#7fb2e5", ax, "box P1 (wall + window)")
    lid_pid = next(b.piece_id for b in binds if b.port == "beam_root")
    if lid_pid != binds[0].piece_id:
        _section_xz(cr.parts[lid_pid], "#8fd694", ax, "lid " + lid_pid)
    nt = d.nose_tip_xyz
    ax.plot(nt[0], nt[2], "v", color="#8e44ad", ms=11, zorder=6)
    ax.annotate(f"nose tip (x={nt[0]:.1f}, z={nt[2]:.1f})\nengages window with y={d.y:.1f}",
                (nt[0], nt[2]), textcoords="offset points", xytext=(-140, 10),
                fontsize=8, color="#8e44ad")
    ax.annotate("", xy=(nt[0] + 6, nt[2]), xytext=(nt[0] + 6, nt[2] + 6),
                arrowprops=dict(arrowstyle="-|>", color="#333", lw=2))
    ax.annotate("insertion  −Z", (nt[0] + 6.5, nt[2] + 3), fontsize=8, rotation=90)
    ax.set_title(f"BOX (correct, for contrast) — section @ y=0 (right hook)\n"
                 f"resolve L={r.L:.0f}mm = geometry L={d.L:.0f}mm  ·  nose inside window, y={d.y:.1f}",
                 fontsize=9)
    ax.set_xlabel("X (mm)"); ax.set_ylabel("Z (mm)"); ax.set_aspect("equal")
    ax.grid(alpha=0.25); ax.legend(loc="lower left", fontsize=7)
    fig.tight_layout(); fig.savefig(OUT / "box_section.png", dpi=130); plt.close(fig)
    print(f"  box_section.png     resolve L={r.L:.0f} = geom L={d.L:.0f}; nose engages window")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    panel()
    box()
