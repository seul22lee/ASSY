# m15 4-rung ablation — BUDGET ESTIMATE (for go/no-go)

**Grid:** 4 rungs × 6 core tasks × 2 paraphrases × N=3 = **144 runs**.
Rungs: **A** direct-CAD · **B** monolithic-IR · **C** staged-no-KG · **D** full (staged+KG+retry).

**Basis:** rung D is the pipeline **measured this session** (dieted s4, qwen local — prompt-token
counts transfer to Gemini since the prompts are identical). Rungs A/B/C are modeled from D's stage
breakdown with the assumptions stated per row. Diet (D-M16-4) already applied → s4 is 53% smaller,
so these are post-diet numbers.

| rung | runs | input (k tok) | output (k tok) | calls | modeling assumption |
|---|---:|---:|---:|---:|---|
| A direct-CAD | 36 | 21.6 | 54.0 | 36 | 1 call: command → CAD code |
| B monolithic-IR | 36 | 108.0 | 64.8 | 54 | 1 big call → full IR (+ ~0.5 retry) |
| C staged-no-KG | 36 | 234.0 | 57.6 | 180 | 4 stages; s4 sees ALL cards (no narrowing) → bigger prompt |
| D full (**measured**) | 36 | 200.4 | 54.5 | 252 | 4 stages + KG narrowing + retries (empirical) |
| **TOTAL** | **144** | **564** | **231** | **522** | ≈ 0.56M in + 0.23M out tokens |

## Cost scenarios

Gemini public rates ($/M tok), **approximate — confirm current pricing before spend**; the
gemini-3-pro-preview tier may be pricier than 2.5-pro (flag).

| scenario | paid cost | + 50% retry/fail buffer |
|---|---:|---:|
| **ALL on 2.5-pro** (upper bound) | **$3.01** | $4.52 |
| ALL on 2.5-flash | $0.75 | $1.12 |
| **Policy-compliant** (Pro only for the final frontier column) | **~$0.40** | ~$0.60 |

**Policy-compliant** = paid Pro ONLY for the recorded frontier column (rung D, 6 tasks × 1 paraphrase
× N=3 = 18 runs → 100k in / 27k out → ~$0.40). The other 126 runs go on **flash free-tier / local
qwen → $0.00**. This is the cost policy you set: paid Pro only for the final recorded column.

## Headline

m15 is **cheap** — a mechanism IR is a small document, so even running the *entire* 144-run grid on
paid Pro is **~$3–5**. Under the cost policy it is **~$0.40 paid**, or **~$0** if the bulk holds on
flash free-tier. The gating question is not money; it's whether **flash holds the bindings** well
enough to carry the bulk cells (the deferred flash-vs-pro check answers that). Latency, not cost, is
the real constraint on free-tier.

## What's still gated (needs your go — billed generation)

1. **flash-vs-pro bindings check** (full pipeline, N=1, latency-tolerant): confirms flash ≥0.9
   bindings before trusting it for bulk. Uses generation calls → held per "no API spend until go".
2. **m15 bulk run** itself (ITEM 1).

Reachability (probed now, **unbilled** metadata only): ollama ✓ (11 local models), gemini ✓
(flash + pro; flash free tier), openai_compat ready-but-unconfigured.
