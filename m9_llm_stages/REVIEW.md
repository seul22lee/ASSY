# M9 · E-track 1 — LLM stages ①–④, first command→IR→report run (G-H entry point)

> ## Frontier update (G-H follow-up) — local vs Gemini, and the question answered
>
> A Gemini key was provided; the same N=3 eval now ran on **two models** (same prompts, same
> few-shot, same gates, same scorer), both with the D-E-5 protocol fix and D-E-2 alias scoring. Full
> table in [`out/comparison.md`](out/comparison.md); [`out/report.html`](out/report.html) is the
> best run (Gemini, F1 0.972, physics PASS).
>
> **The question — does bindings-blindness (0.18) persist at frontier scale? — is answered: NO, it
> is a small-model artefact.**
>
> | ④ bindings F1 | run1 | run2 | run3 |
> |---|---|---|---|
> | qwen3-coder 30B | 0.18 | 0.18 | 0.18 |
> | **gemini-3.1-pro** | 0.00\* | **0.92** | **1.00** |
>
> qwen matched only the trivial `axis → rear_top_edge` (1 of 6), *identically every run*. Gemini
> gets **6/6 exact** — `mount_A→rear_wall_outer`, `mount_B→rear_edge_underside`,
> `catch_window→front_wall_inner`, `stop_flange contact→stop_flange_face`. **Nothing in the
> scaffolding changed between the two columns**, so the gap is model capability, not pipeline design:
> the small model knows *what* mechanism (elements 0.80), the frontier model knows *what and where*.
> (\*Gemini run1's ② failed G2 outright — capability and reliability are separate axes; see below.)
>
> **And the physics separates them exactly as the benchmark intends.** Gemini **declared the stop
> the command never mentioned** and its compiled design **passes contact-only physics: V-A 5/5,
> V-B 4/5 PASS**. qwen omitted the stop → **V-B 0/5, folds over**. Both IRs validator-clean, both
> machine-made. Only V-B separates them (V-A passes both). **D20, now shown across two models on
> designs neither had seen.**
>
> The original E-track-1 result below stands unchanged — it was the local run, correctly reported as
> "qwen3-coder + this scaffolding" (D-E-6). The frontier run does not overwrite it; it answers the
> question it left open.

## Grader-fairness note — the m8 lesson, applied to the grader itself (G-H directed)

Two gate bugs in the first E-track pass were **mine, not the model's**, and both are the exact error
class the m8 retraction was about — a check that encodes an expected *answer* or invents a *rule*,
dressed as an objective gate. Recorded here permanently, because a grader that is unfair in the
synthesizer's favour is worse than no grader:

1. **G2 hardcoded the golden's dialect.** I required an `assembly/translation` behaviour; the model
   produced `assembly/snap_event` — a defensible reading of the spec's "2-piece fastening" (the
   golden's assembly/translation behaviours are the *insertion paths*, not the fastening event). It
   failed 3 retries against my answer key. Fixed: G2 encodes the *requirement* (a set of acceptable
   `(phase, kinds)`), never one spelling.
2. **I invented a "V-08" rule.** A hand-written ④ check rejected a behaviour for carrying both
   `realized_by` and `imposed_by` — **a rule V-08 does not contain** — and gave the fabrication a
   real validator's name. The model was failed for breaking a constraint I had made up. Fixed: ④
   now calls the **real** `validate_all` (filtered to V-02/V-03/V-05/V-08 per §4-④); it no longer
   paraphrases validators, because a paraphrase is a place for the grader to drift from the law it
   claims to enforce.

Both inflated the apparent failure rate before they were fixed. The audit trail (`stage_log`) is
what surfaced them: had I not read the model's actual outputs, I would have reported a worse model
and blamed it. **The discipline "verification is only as honest as the checker" applies to the
checker built to measure the LLM, not just to the physics.**

---

## Original E-track-1 result (local qwen3-coder — stands as reported)

**Outcome: the loop closes.** A one-sentence command became a compiled, physically-simulated
assembly with **no human in the loop** — and the physics caught the design flaw the LLM's IR
contained. Local run, all 3: **①②③④ PASS → ⑤ resolve PASS → ⑥ compile PASS (3 parts) → t2 V-A 5/5,
V-B 0/5**.

> ### The result worth reading twice
> On an IR **no human touched**, V-A passes 5/5 and **V-B fails 0/5 — the lid folds over.** The LLM
> never declared a stop, so the compiled geometry has none. **The pipeline rediscovered, from the
> model's own design, the requirement D-M8-5 records** ("opens ≥90° AND returns closed" is
> unsatisfiable for an over-centre lid without a stop). That is not the benchmark failing — it is
> the benchmark working, on a design it had never seen. V-A cannot tell the two designs apart; only
> V-B can (D20).

**Read the local scores as "qwen3-coder-30B-Q4 + this scaffolding", never as "LLM stages don't
work"** (D-E-6). At the time of the first run this environment had **no frontier API key** — probed
exhaustively; the only working LLM was local Ollama, ceiling ~30B quantized (`gpt-oss:120b` won't
load, `llama3:70b` 500s, GPUs contended). A modest model clearing every gate is evidence *for* the
constraint thesis: the scaffolding is doing the work. The frontier run above was that re-run, one
env var away (`MECHSYNTH_LLM_BACKEND=gemini`).

## What you asked to see

| item | file | result |
|---|---|---|
| scorecards ×3 (local) | [`out/scorecard_ollama_run1.md`](out/scorecard_ollama_run1.md) · [2](out/scorecard_ollama_run2.md) · [3](out/scorecard_ollama_run3.md) | strict **F1 0.676** / alias **0.759**, identical across all 3 |
| audit trail | [`out/stage_log_ollama_run1.json`](out/stage_log_ollama_run1.json) · [2](out/stage_log_ollama_run2.json) · [3](out/stage_log_ollama_run3.json) | every prompt + response verbatim, retry counts |
| **IR diff** | [`out/ir_diff_ollama_run1.svg`](out/ir_diff_ollama_run1.svg) · [2](out/ir_diff_ollama_run2.svg) · [3](out/ir_diff_ollama_run3.svg) | golden ∥ LLM, **decision-keyed** deltas in red |
| best-run report | [`out/report.html`](out/report.html) | command→decisions+citations→rationale→gates→videos→verdict |
| failure taxonomy | § below | which stage broke, error class, retry behaviour |

## Scorecard (all 3 runs identical)

| axis | F1 | what it says |
|---|---:|---|
| ① functions (by verb) | 0.50 | chose `position` over `allow_access` — both legal vocabulary (see D-E-2) |
| ② behaviors (by phase+kind) | 0.57 | got use/rotation-90 and the fastening; invented `assembly/rotation` |
| ③ pieces (by template_ref) | **1.00** | `box_shell` + `lid_panel`, first call, zero retries |
| ③/④ hardware (by role) | **1.00** | the pin — via the card's own `provides_pieces` (D-ONT-11) |
| ④ elements (by card_ref) | **0.80** | `pin_hinge` + `snap_hook_cantilever` correct; missed `stop_flange` |
| ④ bindings (card_ref+port+anchor) | **0.18** | ← **the weak spot** |

**The shape of the result: the model knows WHAT mechanism, not WHERE.** Elements 0.80 vs bindings
0.18. It bound the hinge to `rim_underside_left` / `side_wall_left` instead of `rear_wall_outer` /
`rear_edge_underside`, and put the latch on the **side** walls instead of the **front**. And it still
compiled — a hinge on the wrong face is a *worse design*, not an invalid one. No validator catches
"mechanically sensible but spatially wrong", which is precisely the class Tier0/Tier2 exist for.

**Variance (N=3, T=0.0/0.6/0.6): none.** Same F1, same retries, same elements, same V-A/V-B. Under
schema-constrained decoding this model is effectively deterministic here — itself a datum, and it
means one run is currently as informative as three.

### The physics-implied requirement (scored on its own axis, as instructed)

The command never mentions a stop; the golden has one because physics proved it necessary. **Missed:
YES.** Not a field mismatch — the IR is valid without it. But the audit shows something sharper:

```
KG candidates for B2 (use/rotation):  ['pin_hinge', 'stop_flange']
```

**The knowledge graph offered `stop_flange`, and the model declined it** — while `pin_hinge`'s own
`selection_notes`, which it read and cited, carry the warning: *"an over-centre lid will FOLD FLAT
under gravity unless a stop is added … pair with the stop_flange (D-M8-5)."* The knowledge was in
front of it, citable, and it still missed. **This is a selection failure, not a narrowing failure** —
G3.2 (`tests/test_kg_candidates.py`, 5/5) exists precisely to separate those two, and it did.

## Failure taxonomy

| stage | class | what happened | retry behaviour |
|---|---|---|---|
| ① | — | PASS, 1 call, 0 retries | — |
| ② | **schema violation → self-corrected** | emitted `range_unit: "degrees"`; the literal is `deg` | repair loop fed the pydantic error back verbatim → **fixed on attempt 1** |
| ② | **gate: G2 expectation** | needed 2 retries to add an assembly-phase fastening | converged |
| ③ | — | PASS, 1 call, 0 retries, F1 1.00 | — |
| ④ | — | PASS, 2 calls | rationale cited `MECHSYNTH_SPEC_v0.1 §3.3 Card 1 — pin_hinge` ✓ |
| ⑤⑥ | — | resolve + compile PASS (3 parts) | — |
| **t2 V-B** | **honest physics failure** | **0/5 — folds over** | the run's headline; expected and correct |
| — | **V-01, all runs** | no card implements `verification()` → no stage can emit protocols | **not the model's failure** (D-E-5) |

**Two gate bugs were mine, not the model's** — both found by the audit trail, and worth naming
because they are the same error class the m8 retraction was about (encoding an expected answer, or
inventing a rule and giving it a real rule's name):

1. **G2 hardcoded the golden's dialect.** I required `assembly/translation`; the model produced
   `assembly/snap_event` — a defensible reading of the spec's "2-piece fastening" (the golden's
   assembly/translation behaviours are the *insertion paths*, not the fastening event). It failed
   3 retries against my answer key. The gate now encodes the *requirement* (a set of acceptable
   kinds), not one spelling.
2. **I invented a "V-08" rule.** My hand-written ④ check rejected behaviours carrying both
   `realized_by` and `imposed_by` — **a rule V-08 does not contain.** The model was failed for
   breaking a constraint I had fabricated and given a real validator's name. ④ now **calls the real
   validators** (`validate_all`, filtered to V-02/V-03/V-05/V-08 per §4-④) instead of paraphrasing
   them.

Both inflated the apparent failure rate before they were fixed. Had I not read the trail, I would
have reported a worse model.

## What was built (spec'd but missing before this session)

- **`ontology/functional_basis.py`** — NIST TN 1447 subset (§4-① G1a's vocabulary). Was in the
  spec's file tree, absent from the repo. `allow_access` is a flagged extension (D-E-2 DRAFT).
- **card `selection_notes` + `citations`** — **empty on every element card**, which made G4's
  "rationale must cite selection_notes" unsatisfiable. Now populated, grounded in §3.3–3.6 + Bayer.
- **`knowledge/kg.py`** (§3.7) — `candidates(behavior)` narrowing + `briefing()`; gate **G3.2**
  pinned by a test (5/5). Returns an honest `[]` when it knows no card, never a fallback to "all".
- **`pipeline/llm_client.py`** — structured output, validator-repair retry (≤3), and the
  `stage_log` audit that made this REVIEW's findings visible at all.
- **`pipeline/s1_intent, s2_behavior, s3_decompose, s4_interface`** + `fewshot.py` (D-E-1).
- **`tests/eval_llm_stages.py`** — the scorer (self-tested: golden==1.0, stop isolated, ids/order
  free).

## Decisions

**D-E-1** few-shot/leakage (one example, different task, mechanically enforced) · **D-E-2** DRAFT
`allow_access` not canonical NIST · **D-E-3** DRAFT §4-③'s six-template vocab is 2/6 implemented
(the Hard anchor needs all four missing) · **D-E-4** card entailments (`imposes`, `provides_pieces`)
registered by ④ deterministically — picking is the model's, entailment is code's · **D-E-5** DRAFT
`verification()` unimplemented → V-01 unsatisfiable · **D-E-6** local-model run + how to read the
scores.

Suite **54/54**.

## Reproduce

```
./bin/py m9_llm_stages/run_e_track.py 3      # the run (N=3): ①→④→⑤→⑥→t2, ~35 s/run
./bin/py m9_llm_stages/build_ir_diff.py      # IR diffs
./bin/py m9_llm_stages/build_report.py       # best-run report.html
./bin/py tests/eval_llm_stages.py            # scorer self-test
./bin/py tests/test_kg_candidates.py         # G3.2
```

## Model comparison (frontier follow-up) — full per-stage

See [`out/comparison.md`](out/comparison.md) for the complete table. Headlines:

| axis | qwen3-coder 30B | gemini-3.1-pro |
|---|---:|---:|
| ① functions | 1.00 | 1.00 |
| ② behaviors | 0.57 | 0.56 (0.00–0.83) |
| ③ pieces | 1.00 | 0.67 (0.00–1.00) |
| ④ elements | 0.80 | 0.67 (0.00–1.00) |
| **④ bindings** | **0.18** | **0.64 (0.00–1.00)** |
| macro F1 (alias) | 0.76 | 0.70 (0.17–0.97) |

**Reading the means honestly:** Gemini's *mean* looks level with or below qwen on several axes — an
artefact of its one G2 failure (run1 = all zeros) dragging a 3-run mean. On the runs where ②
converged, Gemini reaches **F1 0.96–0.97 and passes physics**; qwen plateaus at a rock-steady 0.76.
The right summary is not a single number but two axes: **capability** (Gemini's ceiling is far
higher — bindings, the stop, physics-pass) and **reliability** (qwen is boringly consistent, Gemini
is spiky). The comparison table shows ranges, never bare means, for exactly this reason.

Both models' IR diffs: [`out/ir_diff_ollama_run1.svg`](out/ir_diff_ollama_run1.svg) (stop missed,
4 spurious bindings, all red) vs [`out/ir_diff_gemini_run3.svg`](out/ir_diff_gemini_run3.svg)
(elements missed NONE, 0 spurious — near-black, i.e. near-perfect agreement with the golden).

## Decisions (this follow-up)

**D-E-2 CONFIRMED** — `allow_access` official + nearest-NIST annotation; scorer alias-aware, reports
both numbers. **D-E-5 CONFIRMED & FIXED** — `verification()` on all three cards; ④ attaches
protocols from cards (D5); generated IRs now `validate_all` CLEAN. **D-E-7 CONFIRMED & FIXED** —
a selectable card must be resolvable: `StopFlangeCard.resolve_params` + ⑤ resolves feature params
(the frontier model's correct stop selection exposed a hole the goldens had masked). **D-E-8
CONFIRMED** — bindings-blindness is a small-model artefact; frontier gets 6/6 and passes physics.
**D-E-3 RECORDED** (no action — Hard/D-track prerequisite). **D-E-6** (local-model context) stands.

## Reproduce (both models)

```
# key in .env (gitignored): MECHSYNTH_LLM_BACKEND=gemini, GEMINI_API_KEY=...
MECHSYNTH_LLM_BACKEND=ollama MECHSYNTH_LLM_MODEL=qwen3-coder:latest ./bin/py m9_llm_stages/run_e_track.py 3
MECHSYNTH_LLM_BACKEND=gemini                                        ./bin/py m9_llm_stages/run_e_track.py 3
./bin/py m9_llm_stages/build_comparison.py    # the side-by-side scorecard
./bin/py m9_llm_stages/build_ir_diff.py        # per-model IR diffs
./bin/py m9_llm_stages/build_report.py         # best-run report.html
```

Suite **54/54**. Key handling: `.env` gitignored before the key existed (commit `44ebb15`); keys are
read from env/`.env` only, sent as headers, `_redact`ed from every logged string — verified absent
from the 24k-char audit trail.
