# Error Taxonomy

> **The common failure language for ASSY-Next.**
>
> Every observed failure is attributed to **exactly one primary category**. Categories are
> not merged, and "it's a bit of both" is not an attribution — it is an unfinished
> analysis.
>
> This taxonomy is stage-independent and is reused by every stage. Stage 01 supplies the
> worked examples because it is the first stage to complete an implementation cycle.

**Companions:** [`STAGE_DEVELOPMENT_PROTOCOL.md`](STAGE_DEVELOPMENT_PROTOCOL.md) §7
(evaluation and attribution), [`ASSY_VER1_EVIDENCE_AND_LIMITATIONS.md`](ASSY_VER1_EVIDENCE_AND_LIMITATIONS.md) §5
(the L0–L3 quality levels).

---

# 1. Why single attribution matters

A failure attributed to two causes gets fixed in two places, and neither fix is
falsifiable. Worse, the cheapest fix wins: given a choice between correcting a
specification and editing a prompt, the prompt always looks easier — and the contract
silently rots (protocol §10, M3 and M4).

Single attribution forces the question: **which artifact, if it had been correct, would
have prevented this failure?**

## 1.1 Primary versus contributing

A failure may have contributing weaknesses in several artifacts. Record them, but the
**primary** category is the one that satisfies the counterfactual above. Where more than
one artifact independently would have prevented the failure, the primary is the **earliest
in the derivation chain**:

```text
SPECIFICATION → SCHEMA → PROMPT → MODEL
                   ↘ VALIDATOR
```

Rationale: the schema is derived from the specification, the prompt from both, and the
model output from the prompt. A defect upstream reproduces downstream forever; a defect
downstream is contained.

**VALIDATOR is attributed separately** because it is not in the production chain — it is
the observer. A validator defect never causes a bad output; it causes a bad output to go
**undetected**, which is a distinct and often more serious failure.

## 1.2 Detection failures are failures

If a wrong output passed every check, there are **two** failures to record: the one that
produced it, and the one that missed it. They receive different categories.

---

# 2. The categories

## 2.1 SPECIFICATION

**Meaning.** The contract is absent, ambiguous, internally inconsistent, or under-defined.
An implementation cannot be judged, because more than one behaviour satisfies the words.

**Typical symptoms**
- Two defensible outputs for the same input, with no basis to prefer either.
- High run-to-run variance concentrated on one property.
- Two clauses of the specification that cannot both be satisfied.
- A required discovery with no stated obligation condition — *when* must it appear?
- Reviewers disagreeing about whether an output is compliant.

**Evidence**
- Point to the specification text and show that both observed behaviours satisfy it.
- Or exhibit two specification clauses in direct conflict.
- Variance alone is *not* evidence — it must be shown that the contract permits the variance.

**Correction strategy.** Fix the specification first, then re-derive schema, prompt, and
validators from it. Never resolve a specification ambiguity by adding a prompt instruction:
that hides the ambiguity from every future implementation.

**Stage 01 examples**
- **A-6 vs PD-1.** PD-1 permits recording a mechanism the user named; A-6 forbids mechanism
  terms unconditionally. No implementation can satisfy both. *(F-01)*
- **Unknown instability.** The contract never distinguishes "the user declined to prescribe
  this" (a freedom) from "this cannot be determined" (an unknown), so the same clause is
  legitimately classifiable either way. *(F-05)*

---

## 2.2 SCHEMA

**Meaning.** The reasoning is possible and the contract is clear, but the output structure
cannot express the result — or can express a state that is engineering-nonsense.

**Typical symptoms**
- An obligation that can only be checked by reading prose.
- Information present in reasoning but absent from the artifact.
- Illegal combinations of fields that the type system permits.
- A validator forced to use a lexical proxy because the structural fact is unrecorded.

**Evidence**
- Show the obligation, then show no field can hold its answer.
- Or exhibit a field combination that validates but is engineering-meaningless.

**Correction strategy.** Prefer making illegal states **unrepresentable** over adding a
validator to reject them. A rule can be forgotten; a type cannot. Add the minimum general
structure — never a product-specific field.

**Stage 01 examples**
- **`Unknown` has no `derived_from`** while `OperatingScenario` and `Assumption` do, so
  groundedness can only be checked lexically. *(F-04)*
- **The `(comparator, target, upper)` triple** allows `comparator="between"` with a null
  lower bound — a range with no floor. *(F-02, contributing)*

---

## 2.3 VALIDATOR

**Meaning.** The check does not enforce the invariant it claims to enforce. Either it
misses a violation (**false pass**) or rejects a compliant output (**false failure**).

**Typical symptoms**
- A defect found by human reading that every rule passed.
- A rule failing on outputs that are demonstrably correct.
- A rule whose precondition excludes the very case it exists to catch.
- Evidence-gathering that cannot see the thing being checked.

**Evidence**
- A concrete output plus the rule's verdict, with the mismatch shown.
- A false pass requires exhibiting the violation the rule should have caught.

**Correction strategy.** State the **invariant** and the **proof obligation** separately.
Ask what must be true, then ask what evidence would establish it, then ask whether the
implementation actually gathers that evidence. Validators are research artifacts and are
reviewed to the same standard as prompts.

**Stage 01 examples**
- **A-4 false pass.** Guarded on `target is not None`, so a malformed range with a null
  target skipped the check entirely. *(F-02)*
- **A-5 false pass.** Its quantity scan cannot see a range's lower endpoint, so it could
  not notice that "80" had been lost. *(F-03)*
- **A-9 false failure.** Lexical token matching rejects "manufacturing" against a source
  saying "manufacture". *(F-04)*

---

## 2.4 PROMPT

**Meaning.** The contract is clear and expressible, but the instruction does not elicit it.
The reasoning is under-specified, mis-ordered, or ambiguous *as an instruction*.

**Typical symptoms**
- Consistent failure on one reasoning step while others succeed.
- The model doing something defensible but not what the contract requires.
- A step the contract requires that the prompt never asks for.
- Failure that disappears when the instruction is clarified without changing the contract.

**Evidence**
- Show the contract requires X, the prompt does not ask for X, and X is absent.
- Distinguish from SPECIFICATION by confirming the contract is unambiguous.

**Correction strategy.** Revise the prompt only after confirming specification, schema, and
validator are sound. Record the revision in the mandatory evolution log. Never add a
product example — that is the fastest route to benchmark contamination.

**Stage 01 examples**
- **Pass A disposition criteria.** The contract distinguishes what a product *does* from
  what qualities it must *have*; the prompt's five disposition definitions do not draw that
  line sharply, so "should be safe to use" is labelled `function`. *(F-06)*

---

## 2.5 MODEL

**Meaning.** Specification, schema, prompt, and validators are all sound, and the failure
is variance or capability in the reasoner itself.

**Typical symptoms**
- Same input, same contract, different output — where the contract permits only one.
- Failure that changes with temperature, model size, or context length.
- Correct behaviour on short inputs, degradation on long ones.

**Evidence**
- Multiple runs at nonzero temperature, showing outputs that are **not all compliant**.
- **Critical:** variance where every variant is compliant is *not* a MODEL failure. It is
  either acceptable freedom or a SPECIFICATION ambiguity. Determine which before attributing.

**Correction strategy.** Constrain the output space, add a self-check, decompose the task,
or change the reasoner. MODEL is the **last** category to attribute, not the first — it is
the easiest to blame and the least actionable.

**Stage 01 examples**
- None confirmed. Two candidates were examined and both were reclassified:
  - **F-05** (unknown-count variance) → SPECIFICATION. The contract permitted more than
    one compliant answer, so the variance was licensed, not erroneous.
  - **F-09** (`product_intent` carrying the user's solution word) → **SCHEMA**, on
    re-audit. It was *provisionally* recorded as MODEL, which was premature: the field
    carried two incompatible obligations — be faithful to the user (§3.3) and be
    solution-free (§3.4) — with no representation for both. Precedence (§1.1) puts SCHEMA
    ahead of MODEL, and the fix confirmed it: separating the field made the fidelity rule
    pass immediately.

> **The lesson both cases teach.** MODEL is the easiest category to reach for and the
> hardest to act on. Neither of these two survived the §3 step *"prove the contract
> permitted only one answer"*. Attribute MODEL last, and only with that proof.

---

## 2.6 KNOWLEDGE

**Meaning.** Engineering knowledge is in the wrong place: injected into a prompt where it
should live in an inspectable knowledge base, absent where it is genuinely required, or
wrong.

**Typical symptoms**
- A prompt clause that states an engineering fact rather than asking a question.
- Behaviour that only works for products the author had in mind.
- A rule that cannot be traced to a citable source.
- A reasoning step that silently presupposes a mechanism.

**Evidence**
- Quote the clause and show it asserts domain knowledge:
  - *"Identify maintained states"* — a reasoning instruction. **Allowed.**
  - *"Maintained states require latches"* — domain knowledge. **Not allowed.**
  - *"Identify relative motion"* — reasoning. **Allowed.**
  - *"Rotating bodies require bearings"* — domain knowledge. **Not allowed.**
- The test: does the clause remain meaningful for a mechanism nobody has invented yet?

**Correction strategy.** Move the knowledge to the knowledge base with a citation, and
leave a question in the prompt. If the knowledge does not yet exist, record the gap rather
than inlining a guess.

**Stage 01 examples**
- **No violation found.** Zero invented mechanisms across 18 runs; every solution term was
  a quotation of the user's own wording. The boundary held. *(§4 of the review)*

---

## 2.7 PIPELINE

**Meaning.** Each stage is individually correct, but their composition is not: wiring,
ordering, information loss at a boundary, or a stage compensating for an upstream
deficiency.

**Typical symptoms**
- A stage receiving less than its contract promises.
- A downstream stage containing defensive logic for upstream gaps (protocol §2.1 P2).
- Information present at stage N and absent at N+1.
- A failure that vanishes when a stage is run in isolation.

**Evidence**
- Compare the producing stage's output with what the consuming stage received.
- Exhibit the compensating logic.

**Correction strategy.** Repair the boundary, never the symptom. Remove downstream
compensation and let the upstream failure surface.

**Stage 01 examples**
- None yet — Stage 01 has been evaluated in isolation by design. This category becomes
  active when Stage 02 begins consuming the revised `RequirementSpec`.

---

# 3. Attribution procedure

```text
(1) State the failure as an observation, not a diagnosis
(2) Ask: which artifact, if correct, would have prevented it?
(3) If more than one → take the earliest in the derivation chain
(4) If it went undetected → record a SECOND failure against VALIDATOR
(5) Before attributing MODEL → prove the contract permitted only one answer
(6) Before attributing PROMPT → prove specification and schema are sound
(7) Record contributing categories, but only one primary
```

## 3.1 Attribution smells

| Smell | What it usually means |
|---|---|
| Everything is a PROMPT failure | Attribution stopped at the cheapest fix |
| Everything is a MODEL failure | The contract was never checked for ambiguity |
| No VALIDATOR failures ever | Validators are not being reviewed as artifacts |
| A failure with two primaries | The analysis is unfinished |
| Variance attributed without a compliance check | Freedom mistaken for defect, or vice versa |

---

# 4. Failure record format

Every reviewed failure is recorded in this form. The chain from observation to expected
effect must be unbroken.

```text
F-<n>  <short name>

Observed        : what happened, with evidence reference
Primary         : SPECIFICATION | SCHEMA | VALIDATOR | PROMPT | MODEL | KNOWLEDGE | PIPELINE
Contributing    : other weakened artifacts (may be empty)
Evidence        : the artifact text or output that demonstrates it
Why this category owns it : the counterfactual — what would have prevented it
Required change : the contract change, stated precisely
Expected effect : what should change downstream, and what must NOT change
```

---

# 5. Relationship to the quality levels

The taxonomy answers *where a failure lives*; the L0–L3 levels answer *how bad it is*.

| Level | Meaning | Most likely category |
|---|---|---|
| **L0** absent | Nothing claimed | SPECIFICATION or SCHEMA |
| **L1** asserted | Claimed without support — **the dangerous level** | VALIDATOR (it went undetected) |
| **L2** derived | Follows from stated inputs by a cited rule | — |
| **L3** verified | Independent evidence that could have falsified it | — |

**An L1 failure is almost always a VALIDATOR failure in addition to whatever produced it.**
Something was asserted, and nothing objected. Stage 01's degraded range (F-02, F-03) is the
worked example: the model asserted a bound, and two rules that existed to catch exactly
that passed it.
