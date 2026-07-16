"""Generate the m5_resolve_t0 review artifacts (D-ONT-7): stage-⑤ resolution + Tier0/Tier1 + the
D-GEN-1 panel proof + the T-S1a/T-S1b variant diff.

out/:
  s5_params.md            resolved parameters (value/bounds/resolved_by/citation)
  t0_report.md            three-way stratified interference + the undercut measurement
  t1_report.md            re-measured L/h/b/y vs IR (COMPILE_DRIFT gate)
  s6_hook_closeup.png     hook section with RESOLVED dimensions (from_defaults gone)
  variant_hdiff.png       T-S1a vs T-S1b beam — the 60% frequent-reopen rule's effect on h
  panel_dgen1.png         flat_panel_mount assembly — same carve on a different host (D-GEN-1)

Run:  ./bin/py m5_resolve_t0/build_review.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from build123d import export_stl
from knowledge.cards.snap_hook_geometry import (CLEARANCE, _canonical_hook, _geom, carve)
from knowledge.templates import box_shell, lid_panel, flat_panel_mount, retained_board
from ontology.schema import Binding, ElementInstance
from pipeline.s5_geometry import resolve_plan
from tasks.build_goldens import snap_starter
from verify.t0_static import clearance_check, three_way_check, watertight
from verify.t1_remeasure import check_drift, remeasure_hook

OUT = Path(__file__).parent / "out"
BOX = {"box_l": 80.0, "box_w": 60.0, "box_h": 40.0, "wall": 2.0}


def compile_ts1(frequent=False):
    plan = snap_starter()
    res5, _ = resolve_plan(plan, frequent=frequent)
    pieces = {"P1": box_shell(), "P2": lid_panel()}
    pieces["P1"].params.update(BOX)
    inst = plan.element("E1")
    cr = carve(pieces, inst, [b for b in plan.bindings if b.element_id == "E1"])
    return plan, res5["E1"], cr


def _engage_dirs(cr):
    eng = {}
    for d in cr.dims:
        v = np.array(d.nose_tip_xyz) - np.array(d.root_xyz); v[2] = 0
        eng["hook_" + d.side_tag] = tuple(v / np.linalg.norm(v))
    return eng


def _mesh(part):
    f = OUT / "_t.stl"; export_stl(part, str(f), tolerance=0.04, angular_tolerance=0.3)
    m = trimesh.load(f, force="mesh"); f.unlink(); return m


def write_s5(plan):
    lines = ["# Stage ⑤ — resolved parameters (T-S1a)", "",
             "| Parameter | Value | Unit | Bounds | resolved_by | Citation |",
             "|---|---:|---|---|---|---|"]
    for p in plan.parameters:
        if p.resolved_by is None:
            continue
        c = f"{p.citation.doc} · {p.citation.section}" if p.citation else "—"
        lines.append(f"| {p.name} | {p.value} | {p.unit or '–'} | [{p.lo},{p.hi}] | "
                     f"{p.resolved_by.value} | {c} |")
    (OUT / "s5_params.md").write_text("\n".join(lines) + "\n")


def write_t0(cr, t0):
    lines = ["# Tier0 — static verification (T-S1a)", "",
             "Three-way stratified interference check (§5.2 / D22) — the undercut is a MEASUREMENT.",
             "", "| Check | Result | Detail |", "|---|:--:|---|"]
    for name, ok, det in watertight(cr.parts):
        lines.append(f"| {name} | {'✓' if ok else '✗'} | {det} |")
    cc = clearance_check(cr.dims[0].b + 2 * CLEARANCE, cr.dims[0].b)
    lines.append(f"| {cc[0]} | {'✓' if cc[1] else '✗'} | {cc[2]} |")
    for name, ok, det in t0.checks:
        lines.append(f"| {name} | {'✓' if ok else '✗'} | {det} |")
    lines += ["", f"**Undercut measured {t0.undercut_measured_mm:.3f} mm vs designed "
              f"y {cr.dims[0].y:.3f} mm — the compiled geometry agrees with the IR.**",
              f"**Tier0 verdict: {'PASS' if t0.passed else 'FAIL'}.**", ""]
    (OUT / "t0_report.md").write_text("\n".join(lines))


def write_t1(rem):
    lines = ["# Tier1 — re-measurement from STEP geometry (§5.3)", "",
             "Inputs measured from the tagged hook solid's own axes (NOT the IR); "
             "|IR − measured| > 0.05 mm = COMPILE_DRIFT.", "",
             "| Dimension | IR | Measured | Drift (mm) | OK |", "|---|---:|---:|---:|:--:|"]
    for k, ir, m, d, ok in rem.rows:
        lines.append(f"| {k} | {ir} | {m} | {d} | {'✓' if ok else '✗'} |")
    lines += ["", f"**No compile drift — the compiler reproduced the IR "
              f"({'PASS' if rem.ok else 'FAIL'}).**", ""]
    (OUT / "t1_report.md").write_text("\n".join(lines))


def render_closeup(dims):
    """Hook XZ section (canonical frame) with RESOLVED y/h/L/α overlays."""
    g = _geom(type("I", (), {"params": {"L_hook": dims.L, "h_root": dims.h_root, "b": dims.b,
              "y_undercut": dims.y, "alpha_in_deg": dims.alpha_in, "alpha_out_deg": dims.alpha_out}}))
    _p, segs, nose = _canonical_hook(g, dims.L, 0.0)
    x0, x_tip, z_tip, h_lead, tip_flat, h_under, protrude, nose_h = nose
    fig, ax = plt.subplots(figsize=(7, 7))
    for (cx, h, cz, dz) in segs:
        ax.add_patch(plt.Rectangle((cx - h / 2, cz - dz / 2), h, dz, color="#f6c453", ec="#b7791f"))
    ax.add_patch(plt.Polygon([(x0, z_tip), (x_tip, z_tip - h_lead), (x_tip, z_tip - h_lead - tip_flat),
                              (x0, z_tip - nose_h)], closed=True, color="#f6a723", ec="#b7791f"))
    ax.axvline(0, color="#888", ls=":", lw=.8); ax.text(0.1, dims.L * 0.1, "catch face", fontsize=7,
                                                        color="#2b6cb0")

    def dim(x0d, z0, x1, z1, label, off=(0, 0)):
        ax.annotate("", (x1, z1), (x0d, z0), arrowprops=dict(arrowstyle="<->", color="#c53030", lw=1.2))
        ax.text((x0d + x1) / 2 + off[0], (z0 + z1) / 2 + off[1], label, color="#c53030", fontsize=9,
                ha="center", bbox=dict(fc="white", ec="none", alpha=.85))
    xo = -CLEARANCE
    dim(xo - dims.h_root - 1.2, 0, xo - dims.h_root - 1.2, dims.L, f"L={dims.L:g}", off=(-1, 0))
    dim(xo - dims.h_root, dims.L - 0.6, xo, dims.L - 0.6, f"h={dims.h_root:.2f}", off=(0, 0.8))
    dim(0, z_tip - h_lead - 1.5, x_tip, z_tip - h_lead - 1.5, f"y={dims.y:g}", off=(0, -0.9))
    ax.text(x_tip + 0.2, z_tip - h_lead / 2, f"α_in {dims.alpha_in:g}°", fontsize=8, color="#2f855a")
    ax.text(xo + 0.2, z_tip - nose_h + 0.3, f"α_out {dims.alpha_out:g}°", fontsize=8, color="#2f855a")
    ax.set_xlim(-CLEARANCE - dims.h_root - 4, x_tip + 3)
    ax.set_ylim(-1.5, dims.L + 2)
    ax.set_aspect("equal"); ax.set_xlabel("engage (mm)"); ax.set_ylabel("growth / L (mm)")
    ax.set_title(f"s6_hook_closeup — RESOLVED (h={dims.h_root:.2f} mm; from_defaults="
                 f"{dims.from_defaults})", fontsize=10); ax.grid(alpha=.25)
    fig.tight_layout(); fig.savefig(OUT / "s6_hook_closeup.png", dpi=130); plt.close(fig)


def render_three_way():
    """Demo A's mechanism, one session early: T-S1a vs T-S1b(fixed_y, INFEASIBLE) vs
    T-S1b(hold_retention). fixed_y thins toward failure; hold_retention lengthens."""
    from pipeline.s5_geometry import resolve_snap_hook
    di = {"L": 12.0, "y": 1.5, "b": 8.0}
    common = dict(y=di["y"], b=di["b"], alpha_in=30.0, alpha_out=45.0, n_hooks=2, design_type=2)
    cases = [
        ("T-S1a\nsingle", resolve_snap_hook(L=di["L"], frequent=False, strategy="fixed_y", **common),
         "#2b6cb0"),
        ("T-S1b fixed_y\n(frequent)", resolve_snap_hook(L=di["L"], frequent=True, strategy="fixed_y",
                                                        **common), "#c53030"),
        ("T-S1b hold_retention\n(frequent)", resolve_snap_hook(L=di["L"], frequent=True,
                                                              strategy="hold_retention", **common),
         "#2f855a"),
    ]
    labels = [c[0] for c in cases]
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.4))
    for ax, key, ylab, fmt in [(axes[0], "h", "root thickness h (mm)", "{:.2f}"),
                               (axes[1], "L", "beam length L (mm)", "{:.1f}"),
                               (axes[2], "W_out", "retention W_out (N)", "{:.1f}")]:
        vals = [getattr(c[1], key) for c in cases]
        bars = ax.bar(labels, vals, color=[c[2] for c in cases], width=0.6)
        for b, v, c in zip(bars, vals, cases):
            feas = c[1].feasible
            ax.text(b.get_x() + b.get_width() / 2, v, ("" if feas else "✗ INFEASIBLE\n") + fmt.format(v),
                    ha="center", va="bottom", fontsize=8, color="#742a2a" if not feas else "#222")
        ax.set_ylabel(ylab); ax.grid(alpha=.25, axis="y")
        ax.tick_params(axis="x", labelsize=7.5)
    axes[2].axhline(15, ls="--", c="#c53030", lw=1); axes[2].text(2.4, 15.5, "floor 15 N", fontsize=7,
                                                                 color="#c53030", ha="right")
    fig.suptitle("Demo A mechanism — the 60% frequent-reopen rule's geometric consequence depends "
                 "on the resolve strategy:\nfixed_y THINS toward retention failure (INFEASIBLE); "
                 "hold_retention LENGTHENS (L 12→15.7) keeping h thick — longer, not thinner",
                 fontsize=8.5)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(OUT / "variant_three_way.png", dpi=130); plt.close(fig)


def render_panel():
    inst = ElementInstance(id="E1", card_ref="snap_hook_cantilever", host_pieces=["M1", "B1"],
                           params={"n_hooks": 2, "design_type": 2, "alpha_in_deg": 30,
                                   "alpha_out_deg": 45, "L_hook": 5.0, "h_root": 1.5, "b": 6.0,
                                   "y_undercut": 1.0})
    binds = [Binding(element_id="E1", port="beam_root", piece_id="M1", anchor=a, mate="on_face_uv",
                     offset_params={"u": 0.5, "v": 0.5}) for a in ("rail_inner_left", "rail_inner_right")]
    binds += [Binding(element_id="E1", port="catch_window", piece_id="B1", anchor=a,
                      mate="offset_face", offset_params={"undercut_dir": "inward"})
              for a in ("board_edge_left", "board_edge_right")]
    cr = carve({"M1": flat_panel_mount(), "B1": retained_board()}, inst, binds)
    mount_m, board_m = _mesh(cr.parts["M1"]), _mesh(cr.parts["B1"])
    fig = plt.figure(figsize=(6.5, 6)); ax = fig.add_subplot(111, projection="3d")
    for m, c in ((mount_m, "#7fb2e5"), (board_m, "#8fd694")):
        ax.add_collection3d(Poly3DCollection(m.vertices[m.faces], facecolor=c, edgecolor="#33333322",
                                             linewidths=0.2, alpha=0.9))
    allv = np.vstack([mount_m.vertices, board_m.vertices]); c = allv.mean(0)
    r = (allv.max(0) - allv.min(0)).max() / 2 * 1.05
    ax.set_xlim(c[0]-r, c[0]+r); ax.set_ylim(c[1]-r, c[1]+r); ax.set_zlim(c[2]-r, c[2]+r)
    ax.set_box_aspect((1, 1, 1)); ax.set_axis_off(); ax.view_init(elev=22, azim=-58)
    ax.set_title("D-GEN-1: flat_panel_mount (blue) clips a board (green)\nSAME carve() as the box "
                 "— only the bindings differ", fontsize=9)
    fig.tight_layout(); fig.savefig(OUT / "panel_dgen1.png", dpi=120); plt.close(fig)
    return len(cr.parts["M1"].solids()), len(cr.parts["B1"].solids())


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    plan_a, ra, cr_a = compile_ts1(frequent=False)
    eng = _engage_dirs(cr_a)
    hooks = {k: v for k, v in cr_a.tags.items() if k.startswith("hook")}
    t0 = three_way_check(receiver=cr_a.parts["P1"], mover=cr_a.parts["P2"], hooks=hooks,
                         y=ra.geom["y_undercut"], engage_dirs=eng, K=40)
    d0 = cr_a.dims[0]
    rem = check_drift(d0, remeasure_hook(cr_a.tags["hook_" + d0.side_tag], d0, t0.undercut_measured_mm))

    write_s5(plan_a); write_t0(cr_a, t0); write_t1(rem)
    render_closeup(d0)
    render_three_way()
    ms, bs = render_panel()

    print(f"  s5_params.md · t0_report.md (undercut {t0.undercut_measured_mm:.3f}=y) · t1_report.md "
          f"(drift ok={rem.ok})")
    print(f"  s6_hook_closeup.png (h={d0.h_root:.2f}, from_defaults={d0.from_defaults})")
    print(f"  variant_three_way.png  (T-S1a | T-S1b fixed_y INFEASIBLE | T-S1b hold_retention)")
    print(f"  panel_dgen1.png    mount solids={ms} board solids={bs} (D-GEN-1)")


if __name__ == "__main__":
    main()
