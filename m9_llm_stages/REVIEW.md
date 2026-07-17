# M9 · E-track 1 — LLM stages ①–④, first command→IR→report run (G-H entry point)

**Outcome: the loop closes.** A one-sentence command became a compiled, physically-simulated
assembly with **no human in the loop** — and the physics caught the design flaw the LLM's IR
contained. All 3 runs: **①②③④ PASS → ⑤ resolve PASS → ⑥ compile PASS (3 parts) → t2 V-A 5/5,
V-B 0/5**.

> ### The result worth reading twice
> On an IR **no human touched**, V-A passes 5/5 and **V-B fails 0/5 — the lid folds over.** The LLM
> never declared a stop, so the compiled geometry has none. **The pipeline rediscovered, from the
> model's own design, the requirement D-M8-5 records** ("opens ≥90° AND returns closed" is
> unsatisfiable for an over-centre lid without a stop). That is not the benchmark failing — it is
> the benchmark working, on a design it had never seen. V-A cannot tell the two designs apart; only
> V-B can (D20).

**Read the scores as "qwen3-coder-30B-Q4 + this scaffolding", never as "LLM stages don't work"**
(D-E-6). This environment has **no frontier API key** — probed exhaustively; the only working LLM is
local Ollama, ceiling ~30B quantized (`gpt-oss:120b` won't load, `llama3:70b` 500s, GPUs contended).
A modest model clearing every gate is evidence *for* the constraint thesis: the scaffolding is doing
the work. A frontier re-run is one env var away (`MECHSYNTH_LLM_BACKEND`/`_MODEL`).

## What you asked to see

| item | file | result |
|---|---|---|
| scorecards ×3 | [`out/scorecard_run1.md`](out/scorecard_run1.md) · [2](out/scorecard_run2.md) · [3](out/scorecard_run3.md) | macro **F1 0.676**, identical across all 3 |
| audit trail | [`out/stage_log_run1.json`](out/stage_log_run1.json) · [2](out/stage_log_run2.json) · [3](out/stage_log_run3.json) | every prompt + response verbatim, retry counts |
| **IR diff** | [`out/ir_diff_run1.svg`](out/ir_diff_run1.svg) · [2](out/ir_diff_run2.svg) · [3](out/ir_diff_run3.svg) | golden ∥ LLM, **decision-keyed** deltas in red |
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
