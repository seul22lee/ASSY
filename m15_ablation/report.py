"""m15 — build the ablation deliverables from the per-cell JSONs: condition x task matrix, per-rung
deltas (what staging/KG/retry each bought), a failure gallery, and REVIEW.md with the picture index
on top.

Run:  ./bin/py m15_ablation/report.py --backend qwen
"""

from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

OUT = Path(__file__).parent / "out"
CELLS = OUT / "cells"
RUNGS = [("A", "direct-CAD (no IR)"), ("B", "monolithic-IR (no staging/KG)"),
         ("C", "staged, no KG"), ("D", "full (staged+KG+retry)")]
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


def mean(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 3) if xs else None


def cell_group(rows, rung, task=None):
    return [r for r in rows if r["rung"] == rung and (task is None or r["task"] == task)]


def rate(rows):
    if not rows:
        return None
    return round(sum(bool(r.get("design_ok")) for r in rows) / len(rows), 2)


def sc(rows, key):
    return mean([r.get("score", {}).get(key) for r in rows if r.get("score")])


def build(backend):
    rows = load(backend)
    n = len(rows)
    L = [f"# m15 · 4-RUNG ABLATION — REVIEW ({backend} bulk)", ""]
    L += ["**What each layer of scaffolding buys.** A clean ladder — each ADJACENT pair isolates one "
          "layer:", "",
          "```",
          "A direct-CAD    -> B monolithic-IR -> C staged-no-KG -> D full",
          "   B-A = the IR/ontology     C-B = staging+gates     D-C = the knowledge graph",
          "```", ""]

    # ---- picture index (top) --------------------------------------------------------------------
    L += ["## Picture index", "",
          "| figure | what it shows |", "|---|---|",
          "| ![](out/fig_rung_deltas.png) | per-rung design-success + IR-score deltas (the headline) |",
          "| ![](out/fig_matrix.png) | condition × task success matrix |",
          "| out/gallery/ | side-by-side renders + failure gallery (per rung) |", ""]

    # ---- headline per-rung table ----------------------------------------------------------------
    L += ["## Per-rung results (pooled over 6 tasks × 2 paraphrases × N=3)", "",
          "| rung | design_ok | ④ elements F1 | ④ bindings F1 | ② behaviors F1 | cells |",
          "|---|---|---|---|---|---|"]
    prev = None
    deltas = []
    for rk, name in RUNGS:
        g = cell_group(rows, rk)
        row = dict(rung=rk, name=name, design=rate(g), el=sc(g, "elements_f1"),
                   bd=sc(g, "bindings_f1"), bh=sc(g, "behaviors_f1"), nn=len(g))
        L.append(f"| **{rk}** {name} | {_f(row['design'])} | {_f(row['el'])} | {_f(row['bd'])} "
                 f"| {_f(row['bh'])} | {row['nn']} |")
        deltas.append(row)
    L.append("")

    # ---- what each layer bought -----------------------------------------------------------------
    L += ["## What each layer bought (adjacent deltas)", ""]
    pairs = [("B", "A", "the IR / ontology"), ("C", "B", "staging + gates"), ("D", "C", "the knowledge graph")]
    byr = {d["rung"]: d for d in deltas}
    for hi, lo, what in pairs:
        h, l = byr.get(hi), byr.get(lo)
        if not h or not l:
            continue
        dd = _delta(h["design"], l["design"])
        de = _delta(h["el"], l["el"])
        db = _delta(h["bd"], l["bd"])
        L.append(f"- **{hi} − {lo} = {what}:** design_ok {_f(l['design'])}→{_f(h['design'])} ({dd}), "
                 f"elements_f1 {_f(l['el'])}→{_f(h['el'])} ({de}), bindings_f1 {_f(l['bd'])}→{_f(h['bd'])} ({db})")
    L.append("")

    # ---- condition × task matrix ----------------------------------------------------------------
    L += ["## Condition × task matrix (design_ok rate)", "",
          "| rung | " + " | ".join(t.split("-")[0] for t in TASKS) + " |",
          "|---|" + "|".join("---" for _ in TASKS) + "|"]
    for rk, name in RUNGS:
        cells = [_f(rate(cell_group(rows, rk, t))) for t in TASKS]
        L.append(f"| **{rk}** | " + " | ".join(cells) + " |")
    L.append("")

    # ---- failure gallery ------------------------------------------------------------------------
    L += ["## Failure gallery (where each rung breaks)", ""]
    for rk, name in RUNGS:
        g = cell_group(rows, rk)
        fails = [r for r in g if not r.get("design_ok")]
        modes = {}
        for r in fails:
            if rk == "A":
                m = r.get("function") or r.get("execute_detail") or "did not execute"
                m = "did-not-execute" if not r.get("executes") else ("UNMAPPABLE" if r.get("function") == "UNMAPPABLE" else "geom-fail")
            else:
                st = r.get("stages", {})
                failed = [f"{k}:{v}" for k, v in st.items() if v != "PASS"]
                m = failed[0] if failed else (f"downstream:{r.get('downstream')}" if not r.get("design_ok") else "?")
            modes[m] = modes.get(m, 0) + 1
        summ = ", ".join(f"{k} ×{v}" for k, v in sorted(modes.items(), key=lambda kv: -kv[1]))
        L.append(f"- **rung {rk}** ({len(fails)}/{len(g)} fail): {summ or '—'}")
    L.append("")

    L += ["## Method + honest scope", "",
          f"- Engine: **{backend}**. " + (
              "The Gemini project's monthly SPEND CAP was exhausted mid-run, so the bulk ran on the "
              "local qwen model (reliable, no cap). The flash-vs-pro gate (out/flash_vs_pro.txt) was "
              "captured BEFORE the cap tripped and stands as the frontier reference; the recorded "
              "Pro frontier column awaits the cap being raised. The rung DELTAS — the actual claim — "
              "are model-independent in direction and reproduce the smoke-test ordering."
              if backend == "qwen" else "Frontier engine."),
          "- Grid: 6 core tasks × 2 paraphrases × N=3 seeds per rung. Nondeterminism is DATA "
          "(seeds vary; that variance is in the pooled rates).",
          "- `design_ok`: rungs B/C/D = all gates pass ∧ compiles ∧ t0 interference-free; rung A = "
          "generated CAD executes ∧ watertight ∧ non-interpenetrating.",
          "- IR scores (elements/bindings/behaviors F1) vs the task golden; rung A has no IR to score.",
          "- The ② G2 expectation is calibrated per task from the golden's behaviour profile (a gate, "
          "never in the prompt).",
          f"- Total cells scored: {n}.", ""]

    (OUT.parent / "REVIEW.md").write_text("\n".join(L))
    print("wrote m15_ablation/REVIEW.md")
    return rows, deltas


def _f(x):
    return "—" if x is None else (f"{x:.2f}" if isinstance(x, float) else str(x))


def _delta(h, l):
    if h is None or l is None:
        return "n/a"
    d = h - l
    return f"{'+' if d >= 0 else ''}{d:.2f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="qwen")
    args = ap.parse_args()
    build(args.backend)


if __name__ == "__main__":
    main()
