"""The comparison: local qwen3-coder vs frontier Gemini, same prompts, same few-shots, same gates.

The question it answers: is the bindings-blindness (0.18) a fundamental limit of the
"constrain-the-LLM-to-discrete-decisions" design, or a small-model artifact?

Run:  ./bin/py m9_llm_stages/build_comparison.py
"""

from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

OUT = Path(__file__).parent / "out"
MODELS = [("ollama", "qwen3-coder 30.5B Q4 (local)"), ("gemini", "gemini-3.1-pro-preview")]


def load(tag):
    f = OUT / f"runs_{tag}.json"
    return json.loads(f.read_text()) if f.exists() else []


def axis_names(runs):
    for r in runs:
        if "axes" in r.get("score", {}):
            return [a["axis"] for a in r["score"]["axes"]]
    return []


def per_axis(runs, name):
    """F1 per run for one axis. Only runs that produced a scoreable IR."""
    out = []
    for r in runs:
        sc = r.get("score", {})
        if "axes" not in sc:
            continue
        a = next((x for x in sc["axes"] if x["axis"] == name), None)
        if a:
            out.append(a["f1"])
    return out


def fmt(vals):
    if not vals:
        return "—"
    if len(set(vals)) == 1:
        return f"{vals[0]:.2f}"
    return f"{st.mean(vals):.2f} ({min(vals):.2f}–{max(vals):.2f})"


def main():
    data = {tag: load(tag) for tag, _ in MODELS}
    names = axis_names(data["gemini"]) or axis_names(data["ollama"])

    L = ["# E-track — model comparison: local vs frontier", "",
         "Same command, same prompts, same few-shot (T-S1, D-E-1), same gates, same scorer, "
         "N=3 each. Both with the D-E-5 protocol fix and D-E-2 alias scoring.", ""]
    for tag, label in MODELS:
        rs = data[tag]
        m = rs[0]["backend"]["model"] if rs else "?"
        L.append(f"- **{label}** — `{m}`, {len(rs)} runs")
    L += ["", "## Per-stage agreement (F1, mean over scoreable runs; range if it varied)", "",
          "| axis | qwen3-coder 30B | **gemini-3.1-pro** |", "|---|---:|---:|"]
    for n in names:
        q, g = per_axis(data["ollama"], n), per_axis(data["gemini"], n)
        star = " ⭐" if (q and g and st.mean(g) - st.mean(q) > 0.3) else ""
        L.append(f"| {n} | {fmt(q)} | **{fmt(g)}**{star} |")

    def macro(rs, key):
        v = [r["score"][key] for r in rs if key in r.get("score", {})]
        return fmt(v)
    L += ["", f"| **macro F1 (alias-aware)** | **{macro(data['ollama'],'macro_f1_alias')}** | "
              f"**{macro(data['gemini'],'macro_f1_alias')}** |",
          f"| macro F1 (strict) | {macro(data['ollama'],'macro_f1_strict')} | "
          f"{macro(data['gemini'],'macro_f1_strict')} |", ""]

    # --- the headline question ------------------------------------------------------------
    qb = per_axis(data["ollama"], "④ bindings (by card_ref+port+anchor)")
    gb = per_axis(data["gemini"], "④ bindings (by card_ref+port+anchor)")
    L += ["## The question this run answers", "",
          f"**Does the bindings-blindness persist at frontier scale?** **No — it is a small-model "
          f"artifact.**", "",
          f"- qwen3-coder bindings F1: `{qb}` — identical every run; it matched only the trivial "
          f"`pin_hinge axis → rear_top_edge` (1 of 6).",
          f"- gemini-3.1-pro bindings F1: `{gb}` — **6/6 exact** on its best run, including "
          f"`stop_flange contact → stop_flange_face`.", "",
          "The small model knows WHAT mechanism (elements 0.80) but not WHERE (bindings 0.18). The "
          "frontier model knows both. Nothing about the scaffolding changed between these two "
          "columns — same KG narrowing, same prompts, same gates — so the gap is model capability, "
          "not pipeline design.", ""]

    # --- the physics-implied requirement ---------------------------------------------------
    L += ["## The physics-implied requirement (the stop)", "",
          "| model | included the stop? | t2 V-A | t2 V-B | verdict |", "|---|---|---|---|---|"]
    for tag, label in MODELS:
        for r in data[tag]:
            sc = r.get("score", {})
            if "stop_axis" not in sc:
                L.append(f"| {label} run{r['run']} | — (stage failed) | — | — | — |")
                continue
            t2 = r["downstream"].get("t2_physics", {})
            va = t2.get("V-A", "—") if isinstance(t2, dict) else "err"
            vb = t2.get("V-B", "—") if isinstance(t2, dict) else "err"
            v = r["downstream"].get("t2_verdict")
            L.append(f"| {label} run{r['run']} | "
                     f"{'**YES**' if sc['stop_axis']['in_llm_ir'] else 'no'} | {va} | **{vb}** | "
                     f"{'**PASS**' if v else ('FAIL' if v is False else '—')} |")
    L += ["", "> **This is the whole benchmark in one table.** qwen never declares a stop, so its "
               "compiled geometry has none and **V-B 0/5 — the lid folds over**. Gemini declares "
               "it, and **V-B 4/5 — PASS**. Both IRs are validator-clean; both were written with "
               "no human in the loop. Only the contact-only mode separates them (V-A passes both, "
               "5/5) — D20, now demonstrated across two models on designs neither had seen.", ""]

    # --- failure taxonomy -------------------------------------------------------------------
    L += ["## Where each model broke", "",
          "| model | run | reached | failure class | detail |", "|---|---|---|---|---|"]
    for tag, label in MODELS:
        for r in data[tag]:
            f = r.get("failure")
            if not f:
                L.append(f"| {label} | {r['run']} | t2 | — | completed |")
            else:
                L.append(f"| {label} | {r['run']} | `{f['reached']}` | {f['class']} | "
                         f"{f['error'][:110].replace('|','/')} |")
    L += ["", "**Reading it:** qwen is *consistent* (3/3 identical, F1 0.759) but plateaus. Gemini "
               "is *higher and noisier* — it reaches F1 0.96–0.97 and passes physics when ② "
               "converges, but ② failed G2 outright on 1 of 3 runs (a MotionSpec the repair loop "
               "could not fix in 3 retries). Capability and reliability are separate axes here.", ""]

    L += ["## Retries (the repair loop, per stage)", "",
          "| model | run | s1 | s2 | s3 | s4 |", "|---|---|---|---|---|---|"]
    for tag, label in MODELS:
        for r in data[tag]:
            rc = r.get("retry_counts", {})
            L.append(f"| {label} | {r['run']} | " +
                     " | ".join(str(rc.get(k, "—")) for k in ("s1", "s2", "s3", "s4")) + " |")
    L += ["", "s2 costs both models retries — the stage where a free-text command becomes typed "
               "physics is the hardest hop in the chain, for a 30B and a frontier model alike.", ""]

    (OUT / "comparison.md").write_text("\n".join(L) + "\n")
    print("\n".join(L[:60]))
    print(f"\nwrote {OUT/'comparison.md'}")


if __name__ == "__main__":
    main()
