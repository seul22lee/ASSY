"""m13 — THE HARD ANCHOR (MECHSYNTH §8.2): the deterministic spine of the rack-pinion drawer
cabinet. ⑤ constraint chain → ⑥ compile → t0 (alignment rule firing) → renders + IR graph.

Produces (m13_hard_anchor/out/):
  s5_chain.json / .md   the four §8.2 equalities, each number DERIVED + cited
  t0_assembly_rules.json the alignment rule firing on real geometry (parallel + level)
  anchor_hard_4view.png / _exploded.png / _section.png   the assembly
  ir_hard.svg           the IR graph (2 rail instances + the alignment node)
  s5_verdict.json       guard trio + the chain + alignment result

Run:  ./bin/py m13_hard_anchor/build_review.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402
from build123d import export_stl  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

from build123d import Rotation  # noqa: E402
from knowledge.cards.base import CARD_REGISTRY  # noqa: E402
from ontology.validators import validate_all  # noqa: E402
from pipeline.compile_assembly import compile_assembly  # noqa: E402
from tasks.build_goldens import anchor_hard, anchor_lift  # noqa: E402
from verify.assembly_rules import check_alignment, evaluate  # noqa: E402
from verify.t2_physics.runner import _hash  # noqa: E402
from viz.ir_graph import to_svg  # noqa: E402

OUT = Path(__file__).parent / "out"
TILT = Rotation(0, -90, 0)          # lift: +X travel → +Z (vertical); applied to geometry for renders
VARIANT = "lift"                    # PRIMARY (D-M13-2); set to "drawer" for the alternate
COL = {"P1": "#8aa9c9", "P2": "#e0a458", "P3": "#e0a458", "P4": "#6bbf7b",
       "P5": "#c98bbf", "P6": "#c98bbf"}
LABEL = {"P1": "cabinet", "P2": "carriage_L", "P3": "carriage_R", "P4": "drawer",
         "P5": "knob+pinion"}


def s5_chain():
    """The four §8.2 equalities, resolved. Each row: symbol, formula, value, citation. This is the
    ⑤ test §8.2/§10 call out — the constraint chain the resolver must solve, shown DERIVED."""
    m, z, stroke = 5.0, 12, 120.0
    rail_w, cl, wall, cab_w = 8.0, 0.35, 4.0, 140.0
    rp, d = m * z / 2.0, m * z
    tpr = math.pi * m * z
    cab_inner_w = cab_w - 2 * wall
    drawer_w = cab_inner_w - 2 * (rail_w + cl)
    L_rack = stroke + tpr / 4.0
    engagement_min = 0.35 * stroke
    rows = [
        {"symbol": "drawer_w", "formula": "cab_inner_w − 2·(rail_w+cl)",
         "substituted": f"{cab_inner_w:.0f} − 2·({rail_w:.0f}+{cl})", "value": round(drawer_w, 2),
         "unit": "mm", "cite": "§8.2 / §3.5 (D6: geometry derived from the equality)"},
        {"symbol": "L_rack", "formula": "stroke + π·m·z/4",
         "substituted": f"{stroke:.0f} + {tpr:.2f}/4", "value": round(L_rack, 2),
         "unit": "mm", "op": "≥", "cite": "§3.6 rack engagement margin"},
        {"symbol": "axis_offset", "formula": "rack_pitchline + d/2  (mesh offset = d/2 = rp)",
         "substituted": f"d/2 = {d:.0f}/2", "value": round(rp, 2),
         "unit": "mm", "cite": "§8.2 pinion-rack mesh offset"},
        {"symbol": "engagement", "formula": "≥ 0.35·stroke",
         "substituted": f"0.35·{stroke:.0f}", "value": round(engagement_min, 2),
         "unit": "mm", "op": "≥", "cite": "§3.5 moment resistance"},
        {"symbol": "transmission", "formula": "π·m·z per rev",
         "substituted": f"π·{m:.0f}·{z}", "value": round(tpr, 2),
         "unit": "mm/rev", "cite": "§3.6 / §8.2 rot_to_trans"},
    ]
    meta = {"module": m, "z_pinion": z, "stroke_mm": stroke,
            "stroke_note": ("scaled from the §8.2 nominal 300 mm: the cabinet is 200 mm deep, so "
                            "300 mm would pull the drawer clean out; 120 mm keeps ≥45 mm engaged"),
            "cab_inner_w_mm": cab_inner_w, "rp_mm": rp, "d_mm": d}
    return rows, meta


def _mesh(part):
    stl = OUT / "assets" / "tmp.stl"
    stl.parent.mkdir(parents=True, exist_ok=True)
    export_stl(TILT * part if VARIANT == "lift" else part, str(stl), tolerance=0.1,
               angular_tolerance=0.3)
    return trimesh.load(stl, force="mesh")


def _draw(ax, meshes, offsets=None, alpha=0.55):
    offsets = offsets or {p: (0, 0, 0) for p in meshes}
    for pid, m in meshes.items():
        v = m.vertices + np.array(offsets[pid])
        ax.add_collection3d(Poly3DCollection(v[m.faces], facecolor=COL[pid], edgecolor="#33333322",
                                             linewidths=0.1, alpha=alpha))
    allv = np.vstack([m.vertices + np.array(offsets[p]) for p, m in meshes.items()])
    c = (allv.min(0) + allv.max(0)) / 2
    r = float((allv.max(0) - allv.min(0)).max()) * 0.55
    ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(c[2] - r, c[2] + r)
    ax.set_xlabel("X (pull →)"); ax.set_ylabel("Y"); ax.set_zlabel("Z")


def render_four_view(meshes):
    fig = plt.figure(figsize=(12, 9))
    views = [("front (−Y)", 0, 0), ("right (+X)", 0, 90), ("top", 90, -90), ("iso", 24, -58)]
    for i, (name, el, az) in enumerate(views, 1):
        ax = fig.add_subplot(2, 2, i, projection="3d")
        _draw(ax, meshes)
        ax.view_init(elev=el, azim=az); ax.set_title(name, fontsize=10)
    title = ("Lift platform — crank-driven, VERTICAL travel (tower · 2 carriages · platform+load · crank+pinion)"
             if VARIANT == "lift" else
             "Hard anchor — rack-pinion drawer cabinet (cabinet · 2 carriages · drawer · knob+pinion)")
    fig.suptitle(title, fontsize=11)
    fig.tight_layout(); fig.savefig(OUT / "anchor_hard_4view.png", dpi=125); plt.close(fig)


def render_exploded(meshes):
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection="3d")
    off = {"P1": (0, 0, 0), "P2": (0, 0, 60), "P3": (0, 0, 60), "P4": (0, 0, 120),
           "P5": (0, 0, 60)}
    _draw(ax, meshes, offsets=off, alpha=0.75)
    for pid, lab in LABEL.items():
        if pid in meshes:
            c = meshes[pid].vertices.mean(0) + np.array(off[pid])
            ax.text(c[0], c[1], c[2], f"  {lab}", fontsize=8, weight="bold")
    ax.view_init(elev=20, azim=-60); ax.set_title("exploded (drawer + carriages + knob lifted +Z)")
    fig.tight_layout(); fig.savefig(OUT / "anchor_hard_exploded.png", dpi=125); plt.close(fig)


def _sec(ax, meshes, which, origin, normal):
    for pid, m in meshes.items():
        if pid not in which:
            continue
        try:
            sec = m.section(plane_origin=origin, plane_normal=normal)
            if sec is None:
                continue
            planar, _ = sec.to_planar()
            for ent in planar.entities:
                pts = planar.vertices[ent.points]
                ax.plot(pts[:, 0], pts[:, 1], color=COL[pid], lw=1.4)
        except Exception:
            pass
    ax.set_aspect("equal"); ax.grid(alpha=.25)


def render_section(parts, meshes):
    """One figure, both engagements. For the lift (tilted) the rails run +Z, the pinion sits at
    tilted (−30,60,76): cut horizontally (normal +Z) at the rail height for rail↔carriage, and at
    the pinion height for pinion↔rack. For the drawer, cut YZ at x=0 and x=76."""
    fig, (a0, a1) = plt.subplots(1, 2, figsize=(13, 5.5))
    if VARIANT == "lift":
        _sec(a0, meshes, {"P1", "P2", "P3", "P4"}, [0, 0, 10], [0, 0, 1])
        a0.set_title("horizontal cut z=10 — rail↔carriage engagement (both rails)")
        a0.set_xlabel("X (mm)"); a0.set_ylabel("Y (mm)")
        _sec(a1, meshes, {"P4", "P5"}, [0, 0, 76], [0, 0, 1])
        a1.set_title("horizontal cut z=76 — pinion↔rack mesh")
        a1.set_xlabel("X (mm)"); a1.set_ylabel("Y (mm)")
        fig.suptitle("Lift — rail engagement + pinion-rack mesh (vertical-travel frame)", fontsize=12)
        out = OUT / "anchor_hard_section.png"
    else:
        _sec(a0, meshes, {"P1", "P2", "P3", "P4"}, [0, 0, 0], [1, 0, 0])
        a0.set_title("YZ section at x=0 — rail↔carriage engagement (both rails)")
        a0.set_xlabel("Y (mm)"); a0.set_ylabel("Z (mm)")
        _sec(a1, meshes, {"P4", "P5"}, [76, 30, 0], [1, 0, 0])
        a1.set_title("YZ section at x=76 — pinion↔rack mesh")
        a1.set_xlabel("Y (mm)"); a1.set_ylabel("Z (mm)")
        fig.suptitle("Hard anchor — the two engagements in one figure", fontsize=12)
        out = OUT / "anchor_hard_section.png"
    fig.tight_layout(); fig.savefig(out, dpi=125); plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    plan = anchor_lift() if VARIANT == "lift" else anchor_hard()
    assert not validate_all(plan), "golden must be validator-clean"
    for e in plan.elements:
        e.params = CARD_REGISTRY[e.card_ref].resolve_params(plan, e)
    ca = compile_assembly(plan)

    # ⑤ chain
    rows, meta = s5_chain()
    (OUT / "s5_chain.json").write_text(json.dumps({"rows": rows, "meta": meta}, indent=2))
    md = ["| symbol | formula | substituted | value | cite |", "|---|---|---|---|---|"]
    for r in rows:
        op = r.get("op", "=")
        md.append(f"| `{r['symbol']}` | {op} {r['formula']} | {r['substituted']} | "
                  f"**{r['value']} {r['unit']}** | {r['cite']} |")
    (OUT / "s5_chain.md").write_text("\n".join(md) + "\n")

    # t0 alignment rule firing (the first real firing)
    ok, detail = check_alignment(plan, plan.assembly_rules[0])
    compiled = {"parts": ca.parts}
    ar_rows = [evaluate(plan, ar, compiled, ca.axes.get("E1", {"point": (0, 0, 0), "dir": (1, 0, 0)}))
               for ar in plan.assembly_rules]
    (OUT / "t0_assembly_rules.json").write_text(json.dumps(
        {"alignment_fired": {"ok": ok, "detail": detail}, "rules": ar_rows}, indent=2))

    # renders
    meshes = {p: _mesh(ca.parts[p]) for p in ca.parts}
    render_four_view(meshes)
    render_exploded(meshes)
    render_section(ca.parts, meshes)

    # IR graph
    (OUT / "ir_hard.svg").write_text(to_svg(plan, title=f"Hard anchor — anchor_hard @ {_hash()}"))

    verdict = {
        "decision_row": "m13 Hard anchor — ⑤ chain + ⑥ compile + t0 alignment (spine)",
        "compile_hash": _hash(),
        "validator_clean": True,
        "n_pieces": len(plan.pieces), "n_elements": len(plan.elements),
        "carve_order": ca.order,
        "s5_chain": rows, "s5_meta": meta,
        "alignment_rule": {"ok": bool(ok), "detail": detail},
        "assembly_rules": ar_rows,
        "shape_assert": {"two_slide_rails": sum(e.card_ref == "slide_rail" for e in plan.elements) == 2,
                         "one_rack_pinion": sum(e.card_ref == "rack_pinion" for e in plan.elements) == 1,
                         "alignment_present": any(a.kind == "alignment" for a in plan.assembly_rules),
                         "alignment_passed": bool(ok)},
    }
    (OUT / "s5_verdict.json").write_text(json.dumps(verdict, indent=2))

    print("=== ⑤ constraint chain ===")
    for r in rows:
        print(f"  {r['symbol']:12s} {r.get('op','='):1s} {r['substituted']:20s} = {r['value']} {r['unit']}")
    print(f"\n=== t0 alignment (first real firing) ===\n  {'PASS' if ok else 'FAIL'}: {detail}")
    print(f"\ncompiled {len(ca.parts)} bodies, carve order {ca.order}")
    print("wrote renders, ir_hard.svg, s5_verdict.json →", OUT)


if __name__ == "__main__":
    main()
