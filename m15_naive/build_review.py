"""m15 — build the ablation comparison, renders, and failure gallery from the naive results + the
m14 MechSynth certification. Run AFTER naive.py finishes.

  comparison.md   : execute / geometry / function per condition (naive-pro, naive-qwen, MechSynth)
  axis_*.png      : 3-4 side-by-side renders (naive output vs the MechSynth golden, same task)
  failure_gallery : naive crashes with one-line diagnoses

Run:  ./bin/py m15_naive/build_review.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
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

from knowledge.cards.base import CARD_REGISTRY  # noqa: E402
from pipeline.compile_assembly import compile_assembly  # noqa: E402
from tasks.build_goldens import anchor_easy, anchor_hard, anchor_lift, snap_starter  # noqa: E402

OUT = Path(__file__).parent / "out"

# the MechSynth column — REUSED from the m14 certification (the deterministic guarantee). Each core
# task's (execute, geometry, function) under the scaffolded pipeline, with the golden builder for renders.
MECHSYNTH = {
    "A1-snap-base": dict(execute="✓", geometry="✓", function="✓ (PR-T1 formula, T-S1 certified)",
                         golden=lambda: snap_starter()),
    "B1-hinge-latch": dict(execute="✓", geometry="✓", function="✓ (P-HINGE V-A+V-B 5/5)",
                           golden=lambda: anchor_easy("stop")),
    "C1-lift-base": dict(execute="✓", geometry="✓", function="✓ (P-SLIDE/P-GEAR/P-HOLD/P-FULL 5/5)",
                         golden=lambda: anchor_lift()),
    "A3-snap-force": dict(execute="✓", geometry="✓", function="✓ (force window met, ⑤)",
                          golden=lambda: snap_starter(window_mate=(0.0, 60.0), window_sep=(15.0, 60.0))),
    "C4-drawer": dict(execute="✓", geometry="✓", function="✓ (P-GEAR V-A 5/5)",
                      golden=lambda: anchor_hard("drawer")),
    "C5-lift-nogear": dict(execute="REFUSED", geometry="—", function="REFUSED at ④ (KG no realizer)",
                           golden=None),
}


def _model_key(m):
    return "pro" if m.startswith("gemini") else "qwen"


def aggregate(rows):
    """per (task, model): execute/geometry rates + the dominant function verdict + a failure reason."""
    agg = defaultdict(lambda: dict(n=0, exec=0, geom=0, func_unmap=0, func_map=0, fails=[]))
    for r in rows:
        k = (r["task"], _model_key(r["model"]))
        a = agg[k]; a["n"] += 1
        if r.get("executes"):
            a["exec"] += 1
            if r.get("geometry_ok"):
                a["geom"] += 1
            if r.get("function") == "UNMAPPABLE":
                a["func_unmap"] += 1
            else:
                a["func_map"] += 1
        else:
            a["fails"].append(r.get("execute_detail") or r.get("error") or "?")
    return agg


def comparison(rows):
    agg = aggregate(rows)
    tasks = [t["task"] for t in json.loads((OUT / "naive_results.json").read_text())]
    tasks = list(dict.fromkeys(tasks))                 # preserve order, unique
    lines = ["| task | axis | naive · pro (exec/geom/func) | naive · qwen (exec/geom/func) | MechSynth |",
             "|---|---|---|---|---|"]
    ax = {r["task"]: r["axis"] for r in rows}
    for t in tasks:
        cells = []
        for mk in ("pro", "qwen"):
            a = agg[(t, mk)]
            n = a["n"] or 1
            func = ("UNMAPPABLE" if a["func_unmap"] else ("mapped" if a["func_map"] else "—"))
            cells.append(f"{a['exec']}/{n} · {a['geom']}/{n} · {func}")
        ms = MECHSYNTH.get(t, {})
        msc = f"{ms.get('execute','?')} / {ms.get('geometry','?')} / {ms.get('function','?')}"
        lines.append(f"| {t} | {ax.get(t,'')} | {cells[0]} | {cells[1]} | {msc} |")
    (OUT / "comparison.md").write_text("\n".join(lines) + "\n")
    return agg


def _mesh_stls(stls):
    ms = []
    for s in stls:
        try:
            m = trimesh.load(s, force="mesh")
            if len(m.faces):
                ms.append(m)
        except Exception:
            pass
    return ms


def _mesh_golden(fn):
    p = fn()
    for e in p.elements:
        try:
            e.params = CARD_REGISTRY[e.card_ref].resolve_params(p, e)
        except NotImplementedError:
            pass
    ca = compile_assembly(p)
    ms = []
    for pid, part in ca.parts.items():
        stl = OUT / "assets" / f"g_{pid}.stl"; stl.parent.mkdir(parents=True, exist_ok=True)
        export_stl(part, str(stl), tolerance=0.3, angular_tolerance=0.4)
        ms.append(trimesh.load(stl, force="mesh"))
    return ms


def _draw(ax, meshes, title):
    if not meshes:
        ax.text2D(0.5, 0.5, "(no solids)", ha="center", transform=ax.transAxes); ax.set_title(title, fontsize=10); return
    cols = ["#8aa9c9", "#e0a458", "#6bbf7b", "#c98bbf", "#d98b8b"]
    for i, m in enumerate(meshes):
        ax.add_collection3d(Poly3DCollection(m.vertices[m.faces], facecolor=cols[i % len(cols)],
                                             edgecolor="#33333322", linewidths=0.1, alpha=0.55))
    allv = np.vstack([m.vertices for m in meshes]); c = (allv.min(0) + allv.max(0)) / 2
    r = float((allv.max(0) - allv.min(0)).max()) * 0.55
    ax.set_xlim(c[0]-r, c[0]+r); ax.set_ylim(c[1]-r, c[1]+r); ax.set_zlim(c[2]-r, c[2]+r)
    ax.view_init(elev=22, azim=-58); ax.set_title(title, fontsize=10)
    ax.set_xticklabels([]); ax.set_yticklabels([]); ax.set_zticklabels([])


def renders(rows):
    """Side-by-side: a naive output that DID execute vs the MechSynth golden, same task."""
    by_task = defaultdict(list)
    for r in rows:
        if r.get("executes") and r.get("stls"):
            by_task[r["task"]].append(r)
    made = 0
    for t, cells in by_task.items():
        if t not in MECHSYNTH or MECHSYNTH[t]["golden"] is None or made >= 4:
            continue
        naive = cells[0]
        fig = plt.figure(figsize=(12, 5.2))
        a0 = fig.add_subplot(1, 2, 1, projection="3d")
        _draw(a0, _mesh_stls(naive["stls"]),
              f"NAIVE · {_model_key(naive['model'])} — {naive.get('function','?')[:22]}")
        a1 = fig.add_subplot(1, 2, 2, projection="3d")
        _draw(a1, _mesh_golden(MECHSYNTH[t]["golden"]), f"MechSynth — {MECHSYNTH[t]['function'][:26]}")
        fig.suptitle(f"{t}: naive one-shot vs scaffolded (same command)", fontsize=12)
        fig.tight_layout(); fig.savefig(OUT / f"cmp_{t}.png", dpi=120); plt.close(fig)
        made += 1
        print("wrote", f"cmp_{t}.png")
    return made


def gallery(rows):
    fails = [r for r in rows if not r.get("executes")]
    lines = ["# Naive failure gallery — one-line diagnoses\n"]
    for r in fails:
        lines.append(f"- **{r['tag']}**: {r.get('execute_detail') or r.get('error')}")
    (OUT / "failure_gallery.md").write_text("\n".join(lines) + "\n")
    return len(fails)


def main():
    rows = json.loads((OUT / "naive_results.json").read_text())
    aggregate_ = comparison(rows)
    n_render = renders(rows)
    n_fail = gallery(rows)
    ex = sum(r.get("executes", False) for r in rows)
    print(f"\ncomparison.md + {n_render} renders + failure_gallery ({n_fail} fails). "
          f"naive EXECUTES {ex}/{len(rows)}.")


if __name__ == "__main__":
    main()
