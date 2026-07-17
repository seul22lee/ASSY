# E-track — model comparison: local vs frontier

Same command, same prompts, same few-shot (T-S1, D-E-1), same gates, same scorer, N=3 each. Both with the D-E-5 protocol fix and D-E-2 alias scoring.

- **qwen3-coder 30.5B Q4 (local)** — `qwen3-coder:latest`, 3 runs
- **gemini-3.1-pro-preview** — `gemini-3.1-pro-preview`, 3 runs

## Per-stage agreement (F1, mean over scoreable runs; range if it varied)

| axis | qwen3-coder 30B | **gemini-3.1-pro** |
|---|---:|---:|
| ① functions (by verb) | 1.00 | **1.00** |
| ② behaviors (by phase+motion.kind) | 0.57 | **0.56 (0.00–0.83)** |
| ③ pieces (by template_ref) | 1.00 | **0.67 (0.00–1.00)** |
| ③/④ hardware pieces (by role, D-ONT-11) | 1.00 | **0.67 (0.00–1.00)** |
| ④ elements (by card_ref) | 0.80 | **0.67 (0.00–1.00)** |
| ④ bindings (by card_ref+port+anchor) | 0.18 | **0.64 (0.00–1.00)** ⭐ |

| **macro F1 (alias-aware)** | **0.76** | **0.70 (0.17–0.97)** |
| macro F1 (strict) | 0.68 | 0.70 (0.17–0.97) |

## The question this run answers

**Does the bindings-blindness persist at frontier scale?** **No — it is a small-model artifact.**

- qwen3-coder bindings F1: `[0.182, 0.182, 0.182]` — identical every run; it matched only the trivial `pin_hinge axis → rear_top_edge` (1 of 6).
- gemini-3.1-pro bindings F1: `[0.0, 0.923, 1.0]` — **6/6 exact** on its best run, including `stop_flange contact → stop_flange_face`.

The small model knows WHAT mechanism (elements 0.80) but not WHERE (bindings 0.18). The frontier model knows both. Nothing about the scaffolding changed between these two columns — same KG narrowing, same prompts, same gates — so the gap is model capability, not pipeline design.

## The physics-implied requirement (the stop)

| model | included the stop? | t2 V-A | t2 V-B | verdict |
|---|---|---|---|---|
| qwen3-coder 30.5B Q4 (local) run1 | no | 5/5 | **0/5** | FAIL |
| qwen3-coder 30.5B Q4 (local) run2 | no | 5/5 | **0/5** | FAIL |
| qwen3-coder 30.5B Q4 (local) run3 | no | 5/5 | **0/5** | FAIL |
| gemini-3.1-pro-preview run1 | no | — | **—** | — |
| gemini-3.1-pro-preview run2 | **YES** | 5/5 | **4/5** | **PASS** |
| gemini-3.1-pro-preview run3 | **YES** | 5/5 | **4/5** | **PASS** |

> **This is the whole benchmark in one table.** qwen never declares a stop, so its compiled geometry has none and **V-B 0/5 — the lid folds over**. Gemini declares it, and **V-B 4/5 — PASS**. Both IRs are validator-clean; both were written with no human in the loop. Only the contact-only mode separates them (V-A passes both, 5/5) — D20, now demonstrated across two models on designs neither had seen.

## Where each model broke

| model | run | reached | failure class | detail |
|---|---|---|---|---|
| qwen3-coder 30.5B Q4 (local) | 1 | t2 | — | completed |
| qwen3-coder 30.5B Q4 (local) | 2 | t2 | — | completed |
| qwen3-coder 30.5B Q4 (local) | 3 | t2 | — | completed |
| gemini-3.1-pro-preview | 1 | `s2` | gate_failure_after_retries | StageFailure[s2/G2]: LLM could not satisfy G2 after 3 repair retries; last errors: §4-②: use-phase behaviour B |
| gemini-3.1-pro-preview | 2 | t2 | — | completed |
| gemini-3.1-pro-preview | 3 | t2 | — | completed |

**Reading it:** qwen is *consistent* (3/3 identical, F1 0.759) but plateaus. Gemini is *higher and noisier* — it reaches F1 0.96–0.97 and passes physics when ② converges, but ② failed G2 outright on 1 of 3 runs (a MotionSpec the repair loop could not fix in 3 retries). Capability and reliability are separate axes here.

## Retries (the repair loop, per stage)

| model | run | s1 | s2 | s3 | s4 |
|---|---|---|---|---|---|
| qwen3-coder 30.5B Q4 (local) | 1 | 0 | 2 | 0 | 0 |
| qwen3-coder 30.5B Q4 (local) | 2 | 0 | 2 | 0 | 0 |
| qwen3-coder 30.5B Q4 (local) | 3 | 0 | 2 | 0 | 0 |
| gemini-3.1-pro-preview | 1 | 0 | 3 | — | — |
| gemini-3.1-pro-preview | 2 | 0 | 1 | 0 | 1 |
| gemini-3.1-pro-preview | 3 | 0 | 1 | 0 | 2 |

s2 costs both models retries — the stage where a free-text command becomes typed physics is the hardest hop in the chain, for a 30B and a frontier model alike.

