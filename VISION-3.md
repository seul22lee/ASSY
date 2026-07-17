# VISION-3 — framework pillars

> **Note on this file.** No `VISION-3` existed in the repo or environment, so this holds the
> section below as an **append-ready pillar** to merge into your VISION-3 (which you maintain
> outside this repo). Every claim is traceable to in-repo evidence — file/test/decision cited inline
> — so the pillar can be lifted into a paper without re-deriving the support. If your VISION-3 already
> has Pillar #1, drop in "## Pillar #2" below and reconcile numbering.

---

## Pillar #2 — Knowledge as compiled cards, not retrieved text (the anti-RAG position)

**Decision of record: [D5]** — *"Knowledge compiled into ontology + executable Element Cards, not
RAG. Formulas must be executed, not retrieved."*

The dominant pattern for putting engineering knowledge behind an LLM is retrieval: index the
handbook, fetch the relevant passage, let the model read it and act. **This framework rejects
retrieval as the knowledge substrate.** A handbook passage is *text about* a design rule; what the
pipeline needs is the rule itself — as an **executable formula, a machine-checked bound, an owned
verification protocol, a citeable provenance** — compiled once into a card and thereafter *run*, not
re-read. The card is the compiled artifact; the handbook is its source, the way a `.o` file's source
is a `.c`.

Four kinds of evidence separate "compiled card" from "retrieved text," each an ability RAG structurally
does not have:

### (a) Golden-validated executable formulas — the knowledge *runs*, and is pinned to the book

The Bayer cantilever-snap formulas are **executed**, and pinned by a golden that reproduces the
handbook's own worked example. `tests/test_golden_bayer.py` reproduces **Bayer "Calculation Example
I" (PDF p.16) — 7/7**. Two distinct claims, kept separate:

- **Gate bound** — the golden asserts to fixed tolerances taken from p.16: permissible deflection *h*
  within **±1 %**, deflection force *P* / mating force *W* / the Fig.18 friction factor within **±2 %**.
  This is the pass/fail line the CI holds.
- **Measured residual** — the *actual* error against the book's printed numbers is **< 0.2 % on all
  four quantities** (m3_cards record, `out/golden_bayer_comparison.md`): *h* 3.279 vs 3.28 (−0.03 %),
  *P* 32.53 vs 32.5 (+0.09 %), *W* 58.591 vs 58.5 (+0.16 %), factor 1.801 vs 1.8 (+0.08 %). This is
  how close the executed formulas come, not how loose the gate is.

The test's stance is explicit: *"If this fails, the CODE is wrong, not the book."* A retrieved passage
can be quoted correctly and still computed wrong downstream; an executed formula whose residual against
the source's own numbers is sub-0.2 % cannot — the arithmetic is the artifact, and it is checked
end-to-end.

### (b) Machine-enforced bounds/constraints — the decisive contrast with read-and-ignore

The sharpest evidence is a **measured RAG-style failure inside our own pipeline** [D-E-8]. At stage ④
the local model (qwen3-coder-30B) was handed the `pin_hinge` card's `selection_notes` — which carry,
verbatim, the warning *"an over-centre lid will FOLD FLAT under gravity unless a stop is added … pair
with the `stop_flange`"* — and the knowledge graph **explicitly offered `stop_flange` as a candidate
for the opening behaviour** (`KG candidates for B2: ['pin_hinge', 'stop_flange']`). The model **read
the warning, cited the card, and still declined the stop** (its rationale never mentions
`stop_flange`; the frontier model, given the identical text, took it).

That is the anti-RAG thesis in one datum: **having the text is not complying with it.** Retrieval's
ceiling is "the relevant passage was in context"; it was, and the requirement was dropped anyway. In
this framework the requirement did not depend on the model reading prose — it was caught by the
**deterministic layers the compiled cards own**: physics (V-B) folded the stop-less lid over (0/5),
exactly reproducing the requirement the *system* had earlier discovered [D-M8-5], and validators keep
every card-imposed constraint registered in the IR [V-08]. Knowledge enforced as executable
checks/bounds is falsifiable and load-bearing; knowledge retrieved as text is advisory and, here,
ignored.

### (c) Verification protocols + collision approximations as *card-owned* knowledge — inexpressible in RAG

Each card owns not just formulas but **how its element is proven to work** and **how its functional
clearance survives simulation** — both as executable methods, not documents:

- `verification()` returns the element's own protocols: `pin_hinge` → P-HINGE V-A + V-B;
  `snap_hook_cantilever` → PR-LATCH + PR-SWEEP; `slide_rail` → P-SLIDE V-A + V-B + PR-KEEPOUT;
  `stop_flange` → its angle-limit *criterion contribution* to the hinge's protocol. Protocols are
  **card knowledge (D5), never LLM-authored** — the ④ stage attaches them *from* the card at
  selection.
- `collision_hint()` returns the card's own convex decomposition that keeps the functional clearance
  a generic mesher would swallow: the hinge bore as a ring-of-wedges, the T-rail groove as boxes
  [D18/D21].

There is no text passage that *is* a MuJoCo protocol or a convex-decomposition-that-preserves-a-bore.
These are procedures with parameters and thresholds; they can be compiled into a card and executed,
and they simply **cannot be retrieved** — which is the point.

### (d) Per-dimension citation traceability — provenance at the granularity of a number

Every resolved constant traces to a source at the level of the individual dimension: `Parameter`
carries a `Citation` (doc + section), and card `citations` ground the trade-off text (Bayer page/table,
the M0 rig, the relevant decision). "No constant may be hard-coded without provenance" is enforced,
not aspirational. RAG attributes at the granularity of a *retrieved chunk*; compiled cards attribute
at the granularity of a *value*, so a report can footnote each number to the table it came from.

### Honest limit, and the scalability claim

**The cards are hand-authored.** Compiling a handbook chapter into a validated card is, today, human
work — the framework has not automated handbook→card compilation. That is the real cost, and it is
stated plainly rather than hidden behind the results.

The scalability evidence is the **cost-per-card trend**, measured in this project's own sessions:
`pin_hinge` took the multi-session B-track to reach a passing card + physics; `slide_rail` (D-track 1)
was a **single session** to a full card (formulas, carve, collision_hint, both P-SLIDE modes) with a
first-class ontology extension landed alongside it. The marginal card is getting cheaper as the
scaffolding (templates, the verification harness, the validator suite, the guard trio) amortizes — a
**~3→1 session** trajectory. Whether that curve continues, and whether **handbook→card compilation
can itself be (semi-)automated, is paper-2** — the natural sequel, and the point at which "compiled
cards" stops being a hand-craft and becomes a pipeline.

---

*Evidence index for this pillar:* `MECHSYNTH_SPEC_v0.1.md` (D5, D18/D21) · `tests/test_golden_bayer.py`
(7/7) · `m9_llm_stages/REVIEW.md` + `out/stage_log_ollama_run1.json` (D-E-8, the cite-and-decline) ·
`knowledge/cards/*.py` (`verification`, `collision_hint`) · `ontology/schema.py` (`Parameter.citation`)
· `DECISIONS_LOG.md` (D5, D-M8-5, D-E-8, D-D-1).
