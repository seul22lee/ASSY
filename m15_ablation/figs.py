"""m15 — the two data figures for the ablation REVIEW:
  fig_rung_deltas.png  grouped bars: design_ok / elements_f1 / bindings_f1 per rung (the headline)
  fig_matrix.png       heatmap: design_ok rate over rung x task

Run:  ./bin/py m15_ablation/figs.py --backend qwen
"""

from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

OUT = Path(__file__).parent / "out"
CELLS = OUT / "cells"
RUNGS = ["A", "B", "C", "D"]
RUNG_NAME = {"A": "A\ndirect-CAD", "B": "B\nmono-IR", "C": "C\nstaged-noKG", "D": "D\nfull"}
TASKS = ["A1-snap-base", "A3-snap-force", "B1-hinge-latch-base", "B5-hinge-openangle",
         "C1-lift-base", "C4-drawer"]


def load(backend):
    rows = []
    for f in glob.glob(str(CELLS / f"*__{backend}.json")):
        try:
            rows.append(json.load(open(f)))
        except Exception:
            pass
    return rows


def grp(rows, rung, task=None):
    return [r for r in rows if r["rung"] == rung and (task is None or r["task"] == task)]


def rate(rows):
    return sum(bool(r.get("design_ok")) for r in rows) / len(rows) if rows else np.nan


def scmean(rows, key):
    xs = [r.get("score", {}).get(key) for r in rows if r.get("score")]
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else np.nan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="qwen")
    args = ap.parse_args()
    rows = load(args.backend)
    OUT.mkdir(parents=True, exist_ok=True)

    # ---- fig 1: per-rung deltas (grouped bars) --------------------------------------------------
    design = [rate(grp(rows, r)) for r in RUNGS]
    el = [scmean(grp(rows, r), "elements_f1") for r in RUNGS]
    bd = [scmean(grp(rows, r), "bindings_f1") for r in RUNGS]
    x = np.arange(len(RUNGS)); w = 0.26
    fig, ax = plt.subplots(figsize=(8, 4.8))
    b1 = ax.bar(x - w, design, w, label="design_ok rate", color="#2e7d32")
    b2 = ax.bar(x, el, w, label="④ elements F1", color="#1565c0")
    b3 = ax.bar(x + w, bd, w, label="④ bindings F1", color="#ef6c00")
    for bars in (b1, b2, b3):
        for bar in bars:
            h = bar.get_height()
            if not np.isnan(h):
                ax.text(bar.get_x() + bar.get_width() / 2, h + 0.02, f"{h:.2f}",
                        ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels([RUNG_NAME[r] for r in RUNGS])
    ax.set_ylim(0, 1.1); ax.set_ylabel("rate / F1")
    ax.set_title(f"m15 ablation — what each layer buys ({args.backend})\n"
                 "B−A=IR/ontology   C−B=staging+gates   D−C=knowledge graph", fontsize=10)
    ax.legend(loc="upper left", fontsize=8); ax.grid(axis="y", alpha=0.3)
    fig.tight_layout(); fig.savefig(OUT / "fig_rung_deltas.png", dpi=130); plt.close(fig)

    # ---- fig 2: rung x task design_ok heatmap ---------------------------------------------------
    Z = np.array([[rate(grp(rows, r, t)) for t in TASKS] for r in RUNGS])
    fig, ax = plt.subplots(figsize=(8, 4.2))
    im = ax.imshow(Z, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(TASKS))); ax.set_xticklabels([t.split("-")[0] for t in TASKS])
    ax.set_yticks(range(len(RUNGS))); ax.set_yticklabels([r for r in RUNGS])
    ax.set_xlabel("task"); ax.set_ylabel("rung")
    for i in range(len(RUNGS)):
        for j in range(len(TASKS)):
            v = Z[i, j]
            ax.text(j, i, "—" if np.isnan(v) else f"{v:.2f}", ha="center", va="center", fontsize=9)
    ax.set_title(f"design_ok rate — rung × task ({args.backend})", fontsize=10)
    fig.colorbar(im, ax=ax, fraction=0.03)
    fig.tight_layout(); fig.savefig(OUT / "fig_matrix.png", dpi=130); plt.close(fig)
    print("wrote fig_rung_deltas.png + fig_matrix.png")


if __name__ == "__main__":
    main()
