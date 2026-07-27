# Stage 01 — Implementation Status

> Engineering status report. Not a methodology document.
>
> Phase: **implementation stabilization**. The contract is provisionally stable; the
> question is no longer *what should Stage 01 be* but *can it be implemented faithfully*.

**As of:** Prompt v4, contract r3, 15 evaluation runs at temperature 0.7.

---

# 1. Implementation maturity

| Component | State | Evidence |
|---|---|---|
| Contract (r3) | **Stable** | Unchanged for two cycles; no contradiction found this cycle |
| Schema | **Implements the contract** | Every §6 obligation has a representation; illegal bounds unconstructable |
| Validators | **34 acceptance + 4 diagnostics + 1 warning** | Two known false failures corrected and re-verified |
| Prompt | **v4** | Re-derived at v3 from r3; v4 is refinement only |
| Reasoning backend | Local `qwen3-coder:30B`, temp 0.7 | 51 runs across four prompt versions |
| Placeholder | Retained, unimproved | Still fails legitimately — the baseline works |

## Current measurements (15 runs, temp 0.7)

| Metric | v1 | v2.1 | v3 | **v4** |
|---|---|---|---|---|
| Acceptance rules | 23.3/27 | 25.6/30 | 29.1/34 | **30.9/34** |
| Behavioural coverage | 56% | 74% | 78% | **78%** |
| Semantic agreement | 0.72 | 0.79 | 0.73 | **0.77** |
| Discovery completion | n/a | 1/9 | 15/15 | **15/15** |
| Relations produced | 0 | 0 | 23 | **26** |
| Mechanism leakage (A-6) | 9/9 | 0/9 | 0/15 | **0/15** |
| Invented mechanisms | 0 | 0 | 0 | **0** |

---

# 2. Remaining implementation defects

| # | Rule | Rate | Category | Status |
|---|---|---|---|---|
| **D-1** | A-3a / A-3b | 60% / 67% | PROMPT | **Refinement attempted and failed** |
| **D-2** | A-29 | 40% | PROMPT | Marginal improvement (47% → 40%) |
| **D-3** | A-20 | 20% | PROMPT | Freedoms cited to clauses not dispositioned `freedom` |
| **D-4** | A-3d | 20% | PROMPT | Right clause, wrong record type |
| **D-5** | A-10 | 13% | PROMPT | Priority not discriminating on short requests |

## D-1 in detail — the one that resisted refinement

**Observed:** 17 of 19 coverage failures are one clause: the opening product-identity
statement ("Design a compact desktop … box").

**Why it fails:** that clause carries a constraint (*compact*, *desktop*) that also
appears in a clarification. The interpreter records the constraint once and cites the
clarification, leaving the opening clause unreached.

**What was tried (v4):** the coverage pass was rewritten to say a record may cite several
clauses, and that a clause stating what the product *is* still needs a record.

**Result: no improvement.** BM-001 covers its opening clause (10/10) because that clause
also names a lid, which becomes a requirement. BM-002 and BM-101 do not.

**Assessment:** this is citation *completeness*, not coverage reasoning. The interpreter
finds the constraint; it does not record that two clauses support one requirement. A
second refinement attempt should not repeat the same approach.

---

# 3. Resolved contract questions

| Question | Resolution | Cycle |
|---|---|---|
| May a user's solution term be recorded? | Yes — required, provenance-gated (§3.4) | r2 |
| Is a bound three fields or one object? | One interval object; illegal states unconstructable | r2 |
| Does `product_intent` serve fidelity or abstraction? | **Both, in two fields** — one could not serve either well | r3 |
| Is absence a closing action or a state? | A completion state on every required discovery | r3 |
| Does `[X, X]` represent "approximately X"? | No — `approximate` is explicit; canonicalising alone asserted false exactness | r3 |
| When is an unknown obligatory? | Six-condition rule; the operative test is *would proceeding force a hidden assumption* | r3 |
| Is unknown-count stability a criterion? | **No** — obligation coverage and semantic consistency instead | r3 |

---

# 4. Knowledge-boundary evidence

**Zero invented mechanisms across 51 evaluation runs and four independently derived
prompts.** This is the strongest and most consistent result Stage 01 has produced.

- Every solution term appearing in output was traceable to the user's own wording.
- A-6 (provenance-gated) has failed **0/15** since r2; before r2 it failed 9/9 — those
  were the validator rejecting legitimate quotation, not the model inventing.
- A-32 confirms the complementary property: no user-imposed term is silently erased by
  abstraction. **0 failures in 15 runs.**
- No prompt version has contained an engineering claim. Every clause is a question or a
  structural rule about how requests decompose.

Any future change that introduces engineering knowledge into the prompt is an automatic
regression regardless of its effect on scores.

---

# 5. Regression history

| Change | Effect | Verdict |
|---|---|---|
| r2: bound as an interval | Stated range stopped losing an endpoint | Fixed a live L1 defect |
| r2: A-6 provenance-gated | 9/9 false failures → 0 | Corrected |
| r2: A-9 structural | Morphology false failures → 0 | Corrected |
| v2.1: approximate-value rule | Cleared a hard failure at temp 0; recurred 2/3 at temp 0.7 | Insufficient alone |
| r3: canonicalise `[X,X]` | Cleared the hard failure | Introduced a false-exactness claim, corrected same cycle by `approximate` |
| v3: outcomes recorded per pass | Discovery completion 1/9 → 15/15 | **Largest single gain; structural, not verbal** |
| v3: relations reasoning | 0 → 23 produced | Zero became a conclusion, not a default |
| v3 overall | Semantic agreement 0.79 → 0.73 | Cost of a larger reasoning space |
| **v4: A-8 corrected** | 12/15 → 0/15 | Validator false failure removed |
| **v4: outcome-reason wording** | A-31 8/15 → **0/15** | Priority 1 resolved |
| **v4: citation completeness** | A-3a/A-3b unchanged | **Refinement failed** |
| **v4 overall** | Agreement 0.73 → 0.77; rules 29.1 → 30.9 | Net improvement, no regression found |

---

# 6. Freeze blockers

| # | Blocker | Why it blocks |
|---|---|---|
| **B-1** | **A-1 / interface-term question unresolved** | An open *contract* ambiguity. Whether a user-imposed interface modality (crank, lever, pedal) is a "solution term" for `product_intent` has not been decided. Freezing with an unresolved contract question would freeze the ambiguity |
| **B-2** | **A-3a/A-3b at 60–67%** | A contract obligation the implementation does not meet, and one refinement has already failed |
| **B-3** | **Semantic reproducibility not characterised** | 0.77 mean, but *representation* variance has not been separated from *reasoning* variance. Only reasoning variance should block, and that separation has not been measured |

## Not blockers

- **A-29 at 40%** — improving, and every instance is a recorded, detectable inconsistency
  rather than a silent one.
- **A-20, A-3d, A-10** — low-rate implementation defects with clear causes.
- **Variance in unknown counts** — explicitly not a criterion (§3 above).

---

# 7. Evidence required before provisional freeze

| # | Required | How obtained |
|---|---|---|
| **E-1** | A decision on the interface-term question | Contract review: is a user-imposed interface modality a solution term for `product_intent`? Either narrow A-1's lexicon scope with a stated rationale, or confirm the current scope and treat the failure as an implementation target |
| **E-2** | A-3a/A-3b materially improved | A *different* refinement from the one that failed. The defect is citation completeness, not coverage reasoning |
| **E-3** | Variance decomposition | Classify each disagreement across runs as representation variance (same engineering meaning, different words), reasoning variance (different engineering conclusion), or contract violation. Only the second blocks |
| **E-4** | Knowledge boundary re-verified | Re-confirm zero invented mechanisms on the final prompt version |
| **E-5** | No known validator false failures | Two were found and corrected this phase; a final sweep of the §9.4 false-failure column |

**Estimated distance to freeze:** one contract decision (E-1), one targeted refinement
(E-2), and one measurement (E-3). No architecture change and no new engineering concepts
are anticipated.
