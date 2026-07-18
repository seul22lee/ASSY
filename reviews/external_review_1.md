# External Review 1 — MechSynth (pre-submission internal review)

- **Date received:** 2026-07-18
- **Status:** pre-submission internal review (not a venue review)
- **Archived by:** D-REV-1

---

## Verbatim review text

> **⚠️ PENDING PASTE.** The full verbatim review text is to be pasted here by the user and stored
> unedited. Until then, the twelve numbered points below are the reviewer's points as **condensed in
> the reviewer's/authors' own summary** (the seed for the response table) — they are NOT a substitute
> for the verbatim text and must be replaced/augmented with it when supplied.

1. The benchmark is **co-developed** by the authors (not held-out / blind).
2. The **LLM sample is too small** to support the ablation conclusions.
3. The **"closed-world" claim** overreaches.
4. **Card circularity** — the cards both define and are validated against the same knowledge.
5. **Mixed-verification overclaim** — V-A (declared kinematics) and V-B (contact-derived) results are
   presented together without per-axis marking.
6. **Fix-after-failure leakage** — the retention rule and the pawl were added *after* seeing the
   failure, then evaluated on the same conditions.
7. **Robustness sweeps missing** — results are single operating points, not regions.
8. **No physical fabrication** — everything is simulated.
9. **Element families limited** — few card types; generality unshown.
10. **Card authoring cost unmeasured** — the hand-authoring cost is asserted, not quantified.
11. **Anti-RAG framing overclaims** — retrieval is dismissed rather than positioned.
12. **Novelty is diffuse** — the central contribution is not sharply stated.

---

## Response-tracking table

| # | point (summary) | verdict | action (milestone / log ref) | status |
|---|---|---|---|---|
| 1 | Co-developed benchmark (not blind/held-out) | **ACCEPT** | m14 relabeled **DEV SET**; a blind held-out set authored by external people is planned (pending user recruitment) | table seeded; m14 relabel pending |
| 2 | LLM sample too small | **ACCEPT** | **m15 redesigned as a 4-rung ablation ladder** (direct-CAD / monolithic-IR / staged-no-KG / full), 6-task core × 2 paraphrases × N=3 | m15 in progress |
| 3 | "Closed-world" claim overreaches | **WORDING** | reframe to *"verified assembly synthesis within an executable knowledge library"* | wording rule recorded |
| 4 | Card circularity | **ACCEPT-PARTIAL** | goldens pin to an **external handbook** (Bayer); the **preset is card-independent** (R5). Mitigations: cross-engine spot-check (D-M1-8), fabrication (pending), robustness sweeps (m16) | mitigations tracked |
| 5 | Mixed-verification overclaim | **WORDING RULE** | every representative figure **marks V-A vs V-B per axis**; phrasing *"contact-derived + declared relations"* | rule recorded; applies to all figures |
| 6 | Fix-after-failure leakage | **ACCEPT** | **m16** tests the vertical-retention rule + the pawl on **UNSEEN conditions** (dimensions/loads no milestone used) | m16 planned |
| 7 | Robustness sweeps missing | **ACCEPT** | **m16** robustness sweeps → success **regions** (heatmaps), not points | m16 planned |
| 8 | No physical fabrication | **ACCEPT-PENDING** | user decision on printer access | awaiting user |
| 9 | Element families limited | **ACCEPT** | honest **coverage table** in the paper; VISION-6 (spring, gear train) stands as the extension path | coverage table pending |
| 10 | Card authoring cost unmeasured | **ACCEPT** | **card cost table** this session (LOC, sessions, new schema/API, new verifier vs reused, templates) — sourced to commit refs | **ITEM 3 — in progress** |
| 11 | Anti-RAG framing overclaims | **WORDING** | reframe: *"retrieved prose is insufficient as an execution substrate"*; retrieval and execution substrate are **complementary roles** | wording rule recorded |
| 12 | Novelty diffuse | **ACCEPT** | center claim: *"heterogeneous executable verifiers expose design errors that syntactic validity and declared kinematics cannot detect"*; cards/compiler positioned as **infrastructure** | claim recorded |

---

### Point-10 card cost table

*(Filled by ITEM 3 — see the "Card authoring cost" section appended below once the table is built.)*
