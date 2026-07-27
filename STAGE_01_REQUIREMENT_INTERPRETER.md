# STAGE_01_REQUIREMENT_INTERPRETER.md

# Stage 01 — Requirement Interpretation

> **This document is the single living specification for Stage 01.**
>
> It follows the ten-section structure required by
> [`docs/STAGE_DEVELOPMENT_PROTOCOL.md`](docs/STAGE_DEVELOPMENT_PROTOCOL.md) §4. When this
> document and any implementation disagree, **this document is correct and the
> implementation is a defect**.
>
> It is written to be precise enough that an implementation can be judged compliant
> **from its output artifact alone**, without reading its code.

**Revision history.**

- **r1 — audit closure.** Added the Reasoning Procedure (§6), widened the Engineering
  Question to match the Outputs list, defined "function", replaced adjectival validation
  with rules (§9).
- **r2 — first contract review.** Written after executing Prompt v1 against the benchmark
  suite. Four acceptance rules were found defective and one specification ambiguity was
  found to be the true cause of observed output instability. Changes: §3.4 separates
  recording / inferring / selecting; §6.8b defines the unknown-freedom-requirement
  boundary and the obligation condition for an unknown; A-4, A-5, A-6, A-9 revised;
  A-29…A-31 added; SD-7…SD-9 opened; §9.4 reviews every validator as an artifact.
  **Implementation of r2 is pending** — the schema and validator code still implement r1.

---

# 1. Purpose

Stage 01 converts an unstructured design request into a structured statement of the
engineering problem, **without making any engineering design decision**.

It establishes the contract every later stage is bound by. Everything downstream —
mechanism choice, architecture, embodiment, validation, judgement — is evaluated against
what this stage records. A requirement that Stage 01 fails to capture cannot be designed
for, cannot be verified, and cannot fail: it simply disappears from the project.

This stage is therefore the only place where **omission is unrecoverable**.

---

# 2. Engineering Question

> **What engineering problem is actually being asked?**

**This replaces the previous question, "What must this product do?"**

The previous wording was narrower than this stage's own Outputs list. "What must it do"
asks for a function inventory. It does not ask for operating context, constraints,
assumptions, unknowns, conflicts, priorities, or verification intent — all of which this
stage is required to produce. The audit found the stage behaving consistently with the
narrow question and inconsistently with its obligations.

The question is deliberately about **the problem**, not the product. It includes:

- what must be achieved,
- under what conditions,
- within what constraints,
- with what left deliberately open,
- and how anyone would later know whether it was achieved.

It does **not** include how any of it might be done.

---

# 3. Responsibilities

## 3.1 What this stage decides

Stage 01 decides **only** how to represent the request faithfully:

- which clauses of the request carry engineering meaning,
- how each is classified,
- what is stated versus supplied,
- what remains unknown,
- and how each requirement could eventually be falsified.

## 3.2 Prohibited decisions

These belong to other stages. Each is machine- or audit-checkable (§9).

| # | Prohibited | Note |
|---|---|---|
| **PD-1** | Selecting or inferring a mechanism, machine element, or physical principle | See §3.4 — recording the user's own wording is required, not merely permitted |
| **PD-2** | Proposing product architecture, layout, regions, or subsystems | — |
| **PD-3** | Proposing geometry, dimensions, or CAD representation | — |
| **PD-4** | Selecting a material | Recording a *stated* material constraint is required; choosing one is prohibited |
| **PD-5** | Selecting a manufacturing process | Same distinction as PD-4 |
| **PD-6** | Estimating force, torque, stress, deflection, or any derived physical quantity | — |
| **PD-7** | Judging manufacturability, assemblability, or feasibility | Recording them as *requirements* is required; judging them is prohibited |
| **PD-8** | Resolving an ambiguity by inventing a value | Ambiguity must be recorded, never closed |
| **PD-9** | Dropping a stated requirement because it appears redundant, vague, or hard | — |
| **PD-10** | Strengthening, weakening, or rounding a stated target | A stated range stays a range |
| **PD-11** | Introducing a quantity that appears nowhere in the request | Unless tagged `PROJECT_DEFAULT` with the policy named |

## 3.3 The Design Rule (retained)

> Stage 01 must preserve engineering intent. It must never improve, simplify, reinterpret,
> or optimize the user's request merely to make downstream design easier.
>
> Its responsibility is faithful engineering interpretation — not engineering design.

## 3.4 Recording, inferring, and selecting

The previous revision treated "mechanism words" as a single prohibited class. That was
wrong, and made the contract unsatisfiable: PD-1 permitted recording a user's term while
acceptance rule A-6 forbade the term unconditionally. Three distinct acts were conflated.

| Act | Example shape | Status | Why |
|---|---|---|---|
| **Recording** | The request says a word naming a solution; the stage preserves it inside a requirement traceable to that clause | **Required** | §3.3 forbids reinterpreting the user. Paraphrasing away the user's own noun *is* reinterpretation, and it destroys information Stage 02 needs to know was imposed |
| **Inferring** | Concluding from a described behaviour that a particular solution class is implied | **Prohibited** | This is mechanism reasoning and belongs to Stage 02 |
| **Selecting** | Choosing among solution alternatives | **Prohibited** | Stage 02 |

### The governing test

> A solution term may appear in Stage 01 output **only where it is traceable to a source
> clause that contains it**. Anywhere else, its presence is inference or selection.

This makes the rule structural rather than lexical: compliance is decided by provenance,
not by a word list. It also means the check strengthens as the ledger improves, and it
cannot be defeated by a term the lexicon happens not to list.

### Two consequences

1. **`product_intent` is held to the stricter standard.** It is a sentence the stage
   *authors*, not a clause it quotes, so it has no source clause to be traceable to and
   must be free of solution terms. Describing purpose without naming a solution is always
   possible; if it is not, the request has already constrained the solution and that
   belongs in a requirement.
2. **A recorded solution term is a constraint on the solution space**, not a design
   decision. Where the user's wording fixes a solution class, the interpreter records it —
   and §6.8 governs whether it is additionally a `prohibited`-kind freedom.

---

# 4. Inputs

| Input | Authority | Notes |
|---|---|---|
| Natural-language design request | **Authoritative** | The primary source of truth |
| Clarifications | **Authoritative** | Equal standing with the request; **must be read and scanned for constraints, freedoms, and context**, not merely appended |
| Project policy / defaults | Supporting | May supply values only when tagged `PROJECT_DEFAULT` and named |

Stage 01 has no upstream engineering object. It may not consult any downstream stage,
benchmark identity, product category, or prior run.

---

# 5. Outputs

**Produces:** `RequirementSpec` (schema in §8).

The output must carry:

| Content | Obligation |
|---|---|
| Functional intent | One sentence, **solution-independent**: the outcome requested, no solution nouns. What Stage 02 reasons from |
| User intent summary | One sentence, **faithful**: the user's own terms, preserving any solution wording they imposed |
| Functional requirements | Every required behaviour (§6.2 RD-2) |
| Performance requirements | Every measurable target |
| Constraints | Manufacturing, material, environmental, usability, safety, assembly |
| Operating scenarios | Conditions under which requirements must hold, **derived from this product** |
| Assumptions | Everything the interpreter supplied rather than read |
| Unknowns | Everything required but not determinable from the request |
| Conflicts and dependencies | Where requirements compete or depend on one another |
| Priorities | With a stated basis |
| Verification intent | How each requirement could eventually be falsified |
| Provenance | Origin of every requirement (§6.7) |

---

# 6. Reasoning Procedure

> This section defines the engineering thinking required, **independently of who or what
> performs it**. An LLM, a deterministic module, or a human engineer must each be able to
> satisfy it. Nothing here presumes a language model.

## 6.1 Procedure

Eight passes. Later passes may revise earlier ones; the procedure is complete when a pass
produces no change.

**Pass A — Clause ledger.**
Segment the request *and every clarification* into clauses. Assign each clause exactly one
disposition: `function` · `constraint` · `context` · `freedom` · `non-engineering`.
No clause may be left unassigned. This ledger is the basis of coverage (§6.4).

**Pass B — Function recovery.**
For every `function` clause, recover the behaviour it demands. A function is not merely a
verb: it must identify **actor, action, object, and triggering condition**, and its target
where one is given.

Three forms are routinely missed and must be treated as functions:

- **Maintained states** — *"stays closed"*, *"remains stationary between events"*. A state
  the product must hold is a function, not a safety wish.
- **Conditional behaviours** — *"stays closed **until** the user releases it"*. The
  trigger is part of the function; a function recorded without its condition is incomplete.
- **Prohibitions** — *"avoid jamming"*, *"without unintended collision"*. A behaviour the
  product must not exhibit is a function with a negative target.

Reversible or bidirectional motion (*"raise **and** lower"*) yields coverage for **each
direction**; a single scalar magnitude does not discharge both.

**Pass C — Constraint recovery.**
Recover every limit on the solution: quantitative (with value, unit, comparator, and
tolerance if stated) and qualitative. Bind each to its class (§5). A constraint stated in
a clarification has the same standing as one in the request.

**Pass D — Operating context.**
Derive the conditions under which the requirements must hold, **from this product's own
declared functions and duty**. A scenario is a named operating condition, not a generic
label. Scenarios that could be written before reading the request are not scenarios.

**Pass E — Stated versus supplied.**
Separate what the request contains from what the interpreter added. Anything not traceable
to a clause is `INFERRED` or `PROJECT_DEFAULT` — never `USER_STATED`. This boundary is the
stage's most important product; erasing it makes every downstream trace unreliable.

**Pass F — Unresolved.**
Record what cannot be determined: unknowns, ambiguities, conflicts, and declared design
freedoms. See §6.6 — this material must survive, not be closed.

**Pass G — Verification intent.**
For each requirement, state how it could eventually be falsified — the observable, the
condition, and the comparison. Where no means of verification is currently conceivable,
say so explicitly. **A requirement with no verification intent is not thereby invalid; it
is thereby flagged.**

**Pass H — Coverage audit.**
Confirm every ledger clause is discharged and every requirement is traceable (§6.4). Any
clause with no requirement, and any requirement with no clause and no supplied-origin tag,
is a defect.

## 6.2 Required discoveries

Each is either produced or explicitly declared absent with a reason. Silence is
non-compliance.

| # | Required discovery |
|---|---|
| **RD-1** | Product intent — one sentence, mechanism-free |
| **RD-2** | Function inventory — every required behaviour with actor, action, object, condition; including maintained states, conditional behaviours, prohibitions, and each direction of reversible motion |
| **RD-3** | Input interfaces — what the user or environment supplies, and where if stated |
| **RD-4** | Output interfaces — what the product delivers |
| **RD-5** | Quantitative targets — value, unit, comparator, tolerance, range |
| **RD-6** | Qualitative goals — recorded as requirements, not discarded for being unmeasurable |
| **RD-7** | Constraints by class — manufacturing, material, environmental, usability, safety, assembly |
| **RD-8** | Operating scenarios — product-specific |
| **RD-9** | Duty and cycling expectations, where stated or clearly implied |
| **RD-10** | Declared design freedoms — see §6.8. **Preserve only; never invent** |
| **RD-11** | Assumptions the interpreter supplied, each naming what it stands in for |
| **RD-12** | Unknowns, each naming what is missing and what would resolve it |
| **RD-13** | Conflicts and dependencies between requirements |
| **RD-14** | Verification intent per requirement |
| **RD-15** | Priority per requirement, with the basis stated |

## 6.3 Prohibited decisions

As enumerated in §3.2 (PD-1 … PD-11).

## 6.4 Semantic coverage requirements

Coverage is the property that distinguishes interpretation from summarisation.

| # | Requirement |
|---|---|
| **SC-1** | **Ledger completeness.** Every clause of the request and of every clarification carries exactly one disposition |
| **SC-2** | **Functional coverage.** Every `function` clause maps to at least one requirement of kind `functional` or `performance` |
| **SC-3** | **No orphans.** Every requirement traces to a ledger clause, or carries origin `INFERRED` / `PROJECT_DEFAULT` |
| **SC-4** | **Quantity fidelity.** Every numeric quantity in the source appears with its unit and comparator, or is recorded as an unknown. No quantity is silently dropped, rounded, or converted |
| **SC-5** | **Directional completeness.** Each direction of a reversible motion is separately covered |
| **SC-6** | **Trigger completeness.** Every conditional behaviour retains its condition |
| **SC-7** | **Freedom capture.** Every explicitly declared non-constraint is recorded (see SD-3) |
| **SC-8** | **Clarification parity.** Clarification clauses are covered at the same rate as request clauses |

## 6.5 Completeness conditions

Stage 01 may declare itself complete when **all** hold:

1. All required discoveries (RD-1 … RD-15) are produced or explicitly declared absent with a reason.
2. All coverage requirements (SC-1 … SC-8) are satisfied.
3. All acceptance rules (§9) pass.
4. Every unresolved item is **declared** rather than absent (§6.6).
5. No prohibited decision (PD-1 … PD-11) appears in the output.

Completeness is a property of the **record**, not of the request. A vague request yields a
complete `RequirementSpec` full of declared unknowns. **An incomplete request is not an
excuse for an incomplete specification.**

## 6.6 Information that must remain unresolved

Stage 01's most common failure is closing something it had no basis to close. The
following **must survive this stage unresolved**, recorded rather than settled:

| Must remain unresolved | Because |
|---|---|
| The mechanism, principle, or machine element | Stage 02 owns it |
| Product architecture and layout | Stage 03 owns it |
| Any quantity not stated and not derivable without a design choice | Inventing it fabricates a requirement |
| Ambiguity in the request | Recording it lets a later stage or the user resolve it; closing it hides the choice |
| Conflicts between requirements | Stage 01 records the tension; arbitration requires design authority it does not have |
| Declared design freedoms | A freedom deliberately widens the search space; converting it to a constraint narrows it without permission |
| Verification method where none is conceivable | Flagging is honest; inventing a test is not |

**A recorded unknown is a successful output of this stage.** An unknown silently replaced
by a plausible default is the stage's characteristic failure.

## 6.7 Provenance requirements

| # | Requirement |
|---|---|
| **PR-1** | Every requirement carries an origin: `USER_STATED` · `CLARIFICATION` · `INFERRED` · `PROJECT_DEFAULT` |
| **PR-2** | `USER_STATED` and `CLARIFICATION` are reserved for content traceable to a specific clause. If it is not in the text, it is not stated |
| **PR-3** | `INFERRED` requires the inference to be stated — what was read, and what was concluded |
| **PR-4** | `PROJECT_DEFAULT` requires the policy that supplied the value to be named |
| **PR-5** | Every assumption names the unknown it stands in for, so that resolving the unknown identifies what to revisit |
| **PR-6** | Every unknown names what is missing and what would resolve it |
| **PR-7** | The original request is preserved verbatim, so any later reader can re-audit coverage independently |
| **PR-8** | Provenance is auditable without access to the implementation |

## 6.8 Design freedoms — preservation, not construction

A **design freedom** is information about the *solution space* rather than about the
product's behaviour. It appears in requests constantly and is lost by every extractor that
looks only for requirements.

Four forms, all recorded the same way:

| Form | Example shape |
|---|---|
| **Unconstrained** | a choice the user explicitly declines to prescribe |
| **Optional** | a property permitted but not required, often "if justified" |
| **Permitted** | an approach explicitly allowed |
| **Prohibited** | an approach explicitly excluded — a *negative* freedom, bounding the space |
| **Preferred** | a stated preference that is not a hard constraint |

### The boundary

> **Stage 01 preserves freedoms that the user stated or that project policy supplied.
> It must never invent a search space.**

- **Preserve** — record the freedom, its subject, its verbatim basis, and its origin.
- **Do not enumerate** — recording "the number of positions is not prescribed" is correct;
  listing candidate position counts is not.
- **Do not infer** — silence is not a freedom. An unmentioned property is an *unknown*
  (RD-12), not an unconstrained choice. Converting silence into declared freedom
  manufactures permission the user never gave.
- **Do not resolve** — a freedom is not a requirement and must not be rewritten as one.

**Stage 02 owns interpretation.** Turning a preserved freedom into mechanism alternatives
— deciding what an "optional" property implies for the candidate set, or what an
unconstrained choice permits — is mechanism reasoning and belongs to Stage 02. Stage 01
hands over the freedom exactly as given.

This resolves **OQ-6**: freedoms belong to Stage 01 *as preserved information*, because
they originate in the request and are otherwise irrecoverable; their *interpretation*
belongs to Stage 02.

A freedom that duplicates a requirement is a defect: "manual operation only" is a
prohibition on the solution space, and the same clause must not also be emitted as a
usability requirement without the relation between them being recorded (SD-4).

## 6.8b Unknown, freedom, or qualitative requirement — the obligation boundary

The previous revision required unknowns (RD-12) and freedoms (RD-10) without ever stating
**when each is obligatory**. Three different readings of the same clause were all
compliant, so implementations oscillated between them. Evidence: across repetitions of one
request the interpreter produced 0, 3, and 4 unknowns, and the items it produced in the
larger runs were the *same clauses* it had already recorded as freedoms.

An underdetermined obligation is not model randomness. It is a specification defect that
*presents* as randomness.

### The three-way test

For anything the request does not fix, ask **why** it is not fixed:

| Condition | Record as | Test |
|---|---|---|
| The user **explicitly declined to prescribe it**, permitted it, forbade it, or expressed a preference | **Freedom** (§6.8) | Is there a clause saying so? |
| Something is **needed to satisfy a stated requirement** but the request is **silent** on it | **Unknown** (RD-12) | Is there a requirement whose satisfaction depends on it? |
| The request **states a goal in unmeasurable terms** | **Qualitative requirement** (RD-6) | Is a goal stated, but without a criterion? |

### Binding rules

- **BR-1 · Explicit non-prescription is a freedom, never an unknown.** A clause stating
  that something is not prescribed *has determined* that it is open. Nothing is missing,
  so nothing is unknown.
- **BR-2 · An unresolved item is never both.** A clause yields a freedom *or* an unknown,
  not both. Where an implementation produces both from one clause, the freedom is correct
  and the unknown is spurious.
- **BR-3 · An unmeasurable stated goal is a requirement, not an unknown.** "Must be safe
  to use" is a stated safety requirement whose *criterion* is absent. Record the
  requirement; record the missing criterion as an unknown only if some other requirement
  depends on that criterion.
- **BR-4 · Obligation condition for an unknown.** An unknown is obligatory when, and only
  when, a recorded requirement cannot be satisfied or verified without information the
  request does not supply. Every unknown must therefore name at least one affected
  requirement, or state why it affects none.
- **BR-5 · Absence must be declared.** Producing no unknowns is a legitimate result, but
  it is a *finding*, not a default. Where none exist, that must be stated rather than left
  as an empty list indistinguishable from an omitted pass.

### Why this ordering

Freedom, requirement, and unknown are progressively weaker claims about the same silence:
the user settled it (freedom), the user asked for it without saying how much (qualitative
requirement), or nobody settled it (unknown). Testing in that order makes the
classification deterministic, because only one test can succeed first.

## 6.8c Unresolved-information states and the unknown obligation

r2 defined a three-way test. Execution showed the space has **six** states, and that
conflating any two of them produces the instability first seen as varying unknown counts.

| State | Meaning | Test |
|---|---|---|
| **Freedom** | The user explicitly left it open, permitted, forbade, or preferred | Is there a clause saying so? |
| **Qualitative requirement** | A goal is stated without a criterion | Is a goal stated, but unmeasurably? |
| **Unknown** | Information is needed and absent | See the obligation rule below |
| **Assumption** | The interpreter supplied a value to proceed | Did we fill a gap ourselves? |
| **Explicitly absent** | The discovery ran and found nothing | Did we look and find none? |
| **Not applicable** | The discovery cannot apply to this request | Is the category meaningless here? |

### The unknown obligation rule

An unknown is **required** when **all** hold:

1. a later engineering decision or validation needs the information;
2. the request does not supply it;
3. it is not explicitly declared free;
4. it is not merely a qualitative requirement awaiting a criterion;
5. it cannot be validly derived at Stage 01 without a design decision; and
6. **proceeding without recording it would force a hidden assumption.**

Condition 6 is the operative one. The others narrow the field; this one decides. An
unknown exists precisely where silence would otherwise become an unexamined choice.

### Unknown, freedom, and later-stage work — the three-way separation

The six states of §6.8c distinguish what is *recorded*. This distinguishes what Stage 01
records **at all**. One discriminator decides:

> **Could the user have told us?**

| Case | Example shape | Record as |
|---|---|---|
| Only the user or their situation can supply it, and they did not | required lifetime · operating temperature · acceptable input effort · budget · duty frequency | **Unknown** |
| The user explicitly declined to prescribe it, permitted, forbade, or preferred | "the number of positions is not prescribed" · "self-locking is optional" | **Freedom** |
| An engineer will decide it later regardless of what the user said | support strategy · bearing placement · gear ratio · shaft arrangement · fastening strategy · tolerance allocation · housing layout | **Neither — do not record it** |

**The third case is the common error.** "The user did not say how it should be supported"
is not a gap in the request: support is not theirs to state. Recording it as an unknown
misrepresents a later stage's untaken decision as missing user information, and would
send Stage 02 looking for a clarification nobody can give.

Stage 01 is silent about later-stage work. Silence there is correct, not incomplete.

### Semantic equivalence of unknown sets

**Unknown count is not a contract obligation and must never be a freeze criterion.** Two
runs may express one uncertainty at different granularity — "acceptable user effort" and
"acceptable input torque" may be the same unresolved quantity under two names.

Two unknowns are **semantically equivalent** when they refer to the same unresolved
engineering quantity *and* bear on the same downstream decision. Comparison considers:

- **subject** and **resolvable_by** — the quantity and what would settle it;
- **affects** — the requirements whose satisfaction depends on it;
- **provenance** — the clause where the gap arises;
- **conflict with a freedom** — if the user declared it open, it is not unknown (BR-1);
- **conflict with an assumption** — an unknown replaced by an assumption must remain
  visible through `stands_in_for`, never silently dropped.

What is obligatory is therefore **obligation coverage** — every unknown the rule above
requires is present, up to equivalence — and **internal consistency**: no two records
expressing one uncertainty, and none contradicting a freedom or an assumption.

## 6.9 Known traps

Observed in this project's own outputs or in the Ver1 evidence audit.

| # | Trap | Evidence |
|---|---|---|
| **T1** | A maintained state read as a constraint and dropped | *"stays closed until released"*, *"remains stationary between events"* — both lost entirely |
| **T2** | Quantity-driven extraction: clauses without numbers become invisible | Products whose defining functions carry no units produced zero functional requirements |
| **T3** | Context fields emitted as constants — identical operating scenarios across dissimilar products | A false-pass signature (protocol §7.2) |
| **T4** | Everything tagged `USER_STATED`, erasing the stated/supplied boundary | The distinction PR-2 exists to protect |
| **T5** | `verifiable` set from requirement *kind* rather than from whether evidence is obtainable | Produces a flag that carries no information |
| **T6** | Clarifications passed in but never scanned for constraints | A stated process constraint lost this way |
| **T7** | Inventing an entity so a later stage has something to work with | Ver1's retracted stop, one stage earlier — the same failure at the requirement level |

---

# 7. Common LLM Prompt

**Not yet written — deliberately.**

Per protocol §2.1 (P3) and §7 step 7, the prompt is a derivative artifact. It will be
written only after this specification is agreed, and must be derived from §6 alone.

Binding constraints on the eventual prompt:

- Exactly **one** prompt for this stage, used unmodified for every product (protocol §4.2).
- It must contain **no product, benchmark, or mechanism identity** (protocol §6.1).
- Every clause must trace to a numbered item in §6.
- Any behaviour required of the prompt but absent from §6 is a specification defect to be
  fixed here first.

---

# 8. Structured Output Schema

**Unchanged by this revision.** The contract is `RequirementSpec` as currently defined
(`assy/domain/upstream.py`): `source_text`, `product_intent`, `requirements[]`,
`operating_scenarios[]`, `assumptions[]`, `unknowns[]`; each `Requirement` carrying `id`,
`kind`, `origin`, `statement`, `target`, `tolerance`, `comparator`, `upper`, `priority`,
`verifiable`.

## 8.1 Schema debt decisions

Each debt was audited against five questions: is it *genuinely required* by §6; does it
belong in `RequirementSpec`; what is the *minimum general* representation; is it required
before Prompt v1; and how is it deterministically validated.

**All six are required and all six are cleared before Prompt v1.** The reason is uniform:
a prompt cannot be asked to produce information the output cannot hold, and every one of
these debts blocks an obligation that §6 makes binding. Deferring any of them would mean
writing a prompt whose output is unverifiable — the exact drift the protocol forbids.

None of the representations below names a product, mechanism, or benchmark.

---

### SD-1 · Source-clause references

| | |
|---|---|
| **Required by §6?** | Yes — SC-1, SC-3, SC-8, PR-2 are unauditable without it. This is the debt that blocks *coverage*, the stage's headline defect |
| **Belongs in `RequirementSpec`?** | Yes, in two places: a clause ledger at spec level, and a reference from each derived object |
| **Minimum representation** | `SourceClause {id, text, source (request\|clarification), disposition}` where disposition ∈ {function, constraint, context, freedom, non_engineering}; plus `derived_from: list[str]` on every derived object |
| **Before Prompt v1?** | **Yes — blocking.** Coverage is the primary obligation |
| **Validation** | A-3 (every `function` clause referenced), A-16 (every clause has a disposition), A-17 (every `derived_from` resolves), A-18 (no orphan requirements) |

### SD-2 · Verification intent

| | |
|---|---|
| **Required by §6?** | Yes — RD-14, PR-8. `verifiable: bool` carries no information about *how* |
| **Belongs in `RequirementSpec`?** | Yes, on `Requirement`. It is intent, not a test plan — the test plan is Stage 08's |
| **Minimum representation** | `VerificationIntent {kind, observable, condition}` with kind ∈ {measurement, demonstration, inspection, analysis, not_yet_verifiable}. Five categories, no product vocabulary |
| **Before Prompt v1?** | **Yes.** Cheap, and it is what makes "how would this be falsified" answerable at all |
| **Validation** | A-12 (measurement requires an observable), A-19 (`not_yet_verifiable` requires a reason) |

### SD-3 · Design freedoms

| | |
|---|---|
| **Required by §6?** | Yes — RD-10, SC-7, §6.8. Otherwise stated freedoms are irrecoverable |
| **Belongs in `RequirementSpec`?** | Yes, as its own list. A freedom is **not** a requirement and must not be modelled as one |
| **Minimum representation** | `DesignFreedom {id, kind, subject, statement, origin, derived_from}` with kind ∈ {unconstrained, optional, permitted, prohibited, preferred} — the five forms of §6.8 |
| **Before Prompt v1?** | **Yes.** Explicitly in scope per §6.8 |
| **Validation** | A-20 (traceable to a clause or carrying a supplied origin — enforces *preserve, never invent*), A-21 (no freedom duplicates a requirement statement unless the relation is recorded) |

### SD-4 · Typed requirement relations

| | |
|---|---|
| **Required by §6?** | Yes — RD-13. Stage 01 must *record* conflicts without arbitrating them, which requires somewhere to put them |
| **Belongs in `RequirementSpec`?** | Yes, as a spec-level list. A relation is between two objects, not a property of one |
| **Minimum representation** | `RequirementRelation {kind, source, target, rationale}` with kind ∈ {conflicts_with, depends_on, refines, duplicates}. Four relations cover the observed need |
| **Before Prompt v1?** | **Yes**, though the least urgent. Cheap now; retrofitting relations after the prompt exists means re-running the cycle |
| **Validation** | A-22 (endpoints resolve, no self-relation), A-23 (`conflicts_with` requires a rationale) |

### SD-5 · Scenario bindings

| | |
|---|---|
| **Required by §6?** | Yes — RD-8, H-5. Also the direct fix for T3: unstructured strings are what allowed identical constants across products |
| **Belongs in `RequirementSpec`?** | Yes — promote `operating_scenarios` from `list[str]` |
| **Minimum representation** | `OperatingScenario {id, name, description, applies_to, derived_from}` where `applies_to` lists the requirement ids that must hold under it |
| **Before Prompt v1?** | **Yes.** A scenario that binds nothing cannot be distinguished from a label |
| **Validation** | A-24 (`applies_to` resolves), A-25 (at least one scenario binds at least one requirement when requirements exist) |

### SD-6 · Structured unknowns and assumptions

| | |
|---|---|
| **Required by §6?** | Yes — RD-11, RD-12, PR-5, PR-6. Flat strings have no identity, so nothing can reference or resolve one |
| **Belongs in `RequirementSpec`?** | Yes — promote both lists |
| **Minimum representation** | `Unknown {id, subject, reason, affects, resolvable_by}` and `Assumption {id, statement, stands_in_for, origin, derived_from}`. The pairing is the point: an assumption names the unknown it replaces, so resolving the unknown identifies what to revisit |
| **Before Prompt v1?** | **Yes.** PR-5/PR-6 are binding, and unstructured strings are what produced the identical-across-products constants |
| **Validation** | A-26 (`stands_in_for` resolves to an Unknown), A-27 (`affects` resolves), A-28 (every unknown has a non-empty subject and reason) |

---

---

## 8.2 Debts opened by the first contract review

Three further debts were identified by executing the contract rather than by reading it.

### SD-7 · `Unknown` has no provenance

| | |
|---|---|
| **Required by §6?** | Yes — A-9 (groundedness) and PR-6. `OperatingScenario` and `Assumption` both carry `derived_from`; `Unknown` does not, so its groundedness can only be tested lexically |
| **Belongs in `RequirementSpec`?** | Yes, on `Unknown`, matching its siblings |
| **Minimum representation** | `derived_from: list[str]` — identical to the field already on the other three types |
| **Before Prompt v2?** | **Yes.** A-9's revised structural form is unimplementable without it |
| **Validation** | A-9 (revised); A-17 extended to cover unknowns |

### SD-8 · A bound is three loose fields, not an object

| | |
|---|---|
| **Required by §6?** | Yes — PD-10 and SC-4. The observed defect (a stated range silently reduced to an upper bound) was *representable*: `comparator="between"` with a null lower bound is a legal object under the current schema |
| **Belongs in `RequirementSpec`?** | Yes, on `Requirement`, replacing the loose triple |
| **Minimum representation** | `RequirementBound {comparator, lower, upper, unit}` where the constructor rejects an incomplete combination. `between` requires both endpoints; single-sided comparators require exactly one |
| **Before Prompt v2?** | **Recommended, not blocking.** Revised A-4 catches the defect at validation time; SD-8 makes it unrepresentable, which is strictly better (`ERROR_TAXONOMY` §2.2) |
| **Validation** | A-4 becomes structurally redundant once the type enforces it — the preferred end state |

### SD-9 · No way to declare a considered absence

| | |
|---|---|
| **Required by §6?** | Yes — §6.5 requires each discovery to be "produced or explicitly declared absent with a reason", and BR-5 requires the same for unknowns. An empty list is indistinguishable from a pass that never ran |
| **Belongs in `RequirementSpec`?** | Yes, as a spec-level record of considered-and-empty discoveries |
| **Minimum representation** | `declared_absent: list[{discovery, reason}]` — general over all of RD-1…RD-15, not specific to unknowns |
| **Before Prompt v2?** | **Yes.** Without it BR-5 is unenforceable and "no unknowns" stays ambiguous between diligence and omission |
| **Validation** | A-31 (below) |

**Deliberately not added.** Requirement confidence (OQ-2) and a clarification-loop
representation (OQ-3) remain open. Neither is required by §6 as written, and adding a
field before the reasoning demands it is speculation.

---

# 9. Deterministic Validation Rules

A `RequirementSpec` is **accepted** only if every rule in §9.1 passes. Rules in §9.2 are
binding obligations judged by audit until their schema debt is cleared.

## 9.1 Machine-checkable against the current schema

| # | Rule | Enforces |
|---|---|---|
| **A-1** | `product_intent` is non-empty, is a single sentence, and contains no term from the prohibited mechanism lexicon | RD-1, PD-1 |
| **A-2** | At least one requirement has `kind = functional` | SC-2 |
| **A-3** | **Source-clause semantic coverage.** Every clause with disposition `function` is referenced by at least one requirement of kind `functional` or `performance`. *This is the binding completeness criterion* | SC-2, T2 |
| **A-4** | **Bound triple invariant.** `(comparator, target, upper)` must be internally complete: `between` requires BOTH `target` and `upper`, same unit, `target.value ≤ upper.value`; `>=`/`<=`/`==` require `target` and forbid `upper`; any `target` or `upper` requires a `comparator`; every present bound has a non-empty unit. *Checked on the triple, never guarded on one member* | SC-4, RD-5, PD-10 |
| **A-5** | **Range-aware quantity coverage.** Every numeric quantity in the source is captured, including BOTH endpoints of a range whose unit is written once (`80-100 mm` carries two quantities, not one). Extraction must parse ranges as objects before scanning for literals | SC-4, PD-10 |
| **A-6** | **Provenance-gated solution terms.** A solution term may appear in a requirement `statement` only if it appears in at least one clause listed in that requirement's `derived_from`. A term with no such clause is inference or selection | PD-1, §3.4 |
| **A-7** | If `assumptions` is non-empty, at least one requirement carries origin `INFERRED` or `PROJECT_DEFAULT` | PR-1, T4 |
| **A-8** | Not all requirements share one `origin` value when `assumptions` or `unknowns` is non-empty | PR-2, T4 |
| **A-9** | **Structural groundedness.** Every `operating_scenario`, `assumption`, and `unknown` cites at least one source clause in `derived_from`, or carries a supplied origin naming its policy. Groundedness is decided by citation, not by word overlap | RD-8, T3, T6 |
| **A-10** | When more than three requirements exist, at least two distinct `priority` values are present | RD-15 |
| **A-11** | No two requirements share an identical `statement` | — |
| **A-12** | `verifiable = true` requires either a `target` or an observable named in the `statement` | RD-14, T5 |
| **A-13** | `source_text` is preserved verbatim and non-empty | PR-7 |
| **A-14** | No `unknown` names a quantity that also appears as a resolved `target` | PD-8, §6.6 |

## 9.1b Diagnostics — investigated, never automatically failed

A diagnostic signals that something is *probably* wrong. It obliges investigation and a
recorded finding; it never fails a stage on its own. Treating a heuristic as a hard gate
invites tuning the output to satisfy the heuristic.

| # | Diagnostic | Signals |
|---|---|---|
| **D-1** | Count of `functional` + `performance` requirements versus distinct behavioural verbs in `source_text` | A shortfall suggests verb-phrase functions were missed (T2). Investigate against A-3, which is the binding rule |
| **D-2** | Ratio of requirements to source clauses, per product | An unusually low ratio suggests summarisation rather than interpretation |
| **D-3** | Proportion of requirements with origin `USER_STATED` | Near-100% suggests the stated/supplied boundary was collapsed (T4) |

### Cross-product warning

| # | Warning | Signals |
|---|---|---|
| **W-1** | For two products with different `product_intent`, identical `(operating_scenarios, assumptions, unknowns)` | Probable emitted constants (T3) |

**W-1 is a warning requiring investigation, not an unconditional failure.** Two products
may legitimately share context — the same operating environment, the same duty class, the
same open questions — and identical context is not by itself evidence of a defect.

W-1 **becomes a failure (A-15)** only when investigation shows that *materially different
source intent is not reflected in the output*:

| # | Rule | Enforces |
|---|---|---|
| **A-15** | Where two products' requests differ materially in stated function, duty, or operating context, that difference must be visible somewhere in their outputs. Identical output across materially different input is a failure | T3, protocol §7.2 |

The judgement is about **input difference reflected in output**, not about output
similarity alone. A shared assumption is fine; a shared assumption that erases a stated
difference is not.

## 9.1c Rules enabled by the cleared schema debts

Formerly the audit-only obligations H-1 … H-6. With SD-1 … SD-6 cleared these are
machine-checkable and binding.

| # | Rule | Enforces |
|---|---|---|
| **A-16** | Every `SourceClause` carries a disposition, and the ledger covers both the request and every clarification | SC-1, SC-8, SD-1 |
| **A-17** | Every `derived_from` reference resolves to an existing clause id | SC-3, SD-1 |
| **A-18** | Every requirement either has a non-empty `derived_from` or carries origin `INFERRED` / `PROJECT_DEFAULT` | SC-3, PR-2 |
| **A-19** | `verification.kind = not_yet_verifiable` requires a stated reason; any other kind requires an `observable` | RD-14, SD-2 |
| **A-20** | Every `DesignFreedom` traces to a clause with disposition `freedom`, or carries a supplied origin | §6.8, SD-3 |
| **A-21** | No `DesignFreedom.statement` duplicates a requirement `statement` unless a relation records the overlap | §6.8, SD-3 |
| **A-22** | Every `RequirementRelation` endpoint resolves; no relation is reflexive | RD-13, SD-4 |
| **A-23** | `conflicts_with` requires a non-empty rationale | RD-13 |
| **A-24** | Every `OperatingScenario.applies_to` entry resolves to a requirement id | RD-8, SD-5 |
| **A-25** | When requirements exist, at least one scenario binds at least one requirement | RD-8, T3 |
| **A-26** | Every `Assumption.stands_in_for`, when set, resolves to an `Unknown` id | PR-5, SD-6 |
| **A-27** | Every `Unknown.affects` entry resolves to a requirement id | PR-6, SD-6 |
| **A-28** | Every `Unknown` has a non-empty `subject` and `reason` | RD-12, PR-6 |

## 9.1d Rules enforcing the unknown/freedom boundary (§6.8b)

| # | Rule | Enforces |
|---|---|---|
| **A-29** | No `Unknown` may cite a clause that a `DesignFreedom` also cites, where both concern the same subject. Explicit non-prescription is a freedom, never an unknown | BR-1, BR-2 |
| **A-30** | Every `Unknown` names at least one affected requirement in `affects`, or states in `reason` why it affects none | BR-4 |
| **A-31** | An empty `unknowns`, `freedoms`, or `relations` list requires a matching entry in `declared_absent` | BR-5, §6.5 |

A-31 is **audit-only pending SD-9**; A-29 and A-30 are machine-checkable today.

## 9.1e Coverage obligations, separated (contract r3)

A-3 previously mixed four questions, so a failure never said which had gone wrong. A
clause may be semantically covered yet misclassified; it may be correctly classified yet
generate nothing. These are different defects and are now reported separately.

| # | Rule | Question it answers |
|---|---|---|
| **A-3a** | **Semantic coverage.** Every clause whose disposition is not `non_engineering` is cited by at least one record of any permitted type | Did anything at all treat this clause? |
| **A-3b** | **Function coverage.** Every `function` clause is cited by at least one `functional` or `performance` requirement | Did behaviour become a behavioural requirement? |
| **A-3d** | **Generation completeness.** A clause's disposition implies a record type: `freedom` → a `DesignFreedom`; `function`/`constraint` → a `Requirement` | Did the right kind of object get made? |
| **D-4** | *(diagnostic)* **Disposition/generation mismatch.** A `function` clause covered only by non-behavioural records | Was it misclassified, or under-generated? |

**A-3c (disposition correctness) is deliberately not an acceptance rule.** Whether a
classification is *correct* is not machine-decidable without ground truth. What is
decidable is the *mismatch* it produces, which D-4 reports without deciding between the
two causes. Asserting correctness we cannot establish would be an L1 failure in the
validator itself.

## 9.1f Intent, fidelity, and unresolved information

| # | Rule | Enforces |
|---|---|---|
| **A-1** | `product_intent` (functional intent) contains no solution term | §3.4 consequence 1 |
| **A-32** | Every solution term the request imposes survives in `user_intent_summary` or in a requirement | §3.3; prevents abstraction from erasing a user-imposed constraint |
| **A-31** | Every required discovery reaches a completion state; states other than `found`/`unknown` carry a reason | §6.8c; SD-9 revised |
| **A-33** | No two unknowns are semantically equivalent; no unknown is assumed away without a recorded assumption | §6.8c |

A-1 and A-32 are **complementary, not competing**: one forbids the term in the
abstraction, the other requires it somewhere in the record. Together they express what a
single field could not.

## 9.2 Remaining audit-only obligations

| # | Obligation | Debt |
|---|---|---|
| **H-7** | Absence of a required discovery is declared with a reason rather than left as an empty list | SD-9 |

All other obligations of §6 are machine-checkable. Any future obligation added to §6
without a corresponding rule in §9.1 is a specification defect.

## 9.3 Prohibited mechanism lexicon

Used by A-1 and A-6. Terms naming a mechanism, machine element, or physical principle —
for example: hinge, latch, snap, gear, rack, pinion, screw, thread, cam, spring, bearing,
bushing, linkage, lever, pulley, belt, chain, drum, cable, pawl, detent, ratchet, clutch,
coupling, piston, damper.

The list is **illustrative and extensible**; it is not a closed vocabulary and must never
be tuned to a benchmark. The governing rule is §3.2 PD-1: the *test* is whether the term
names a solution rather than a need. A term the user themselves supplied is permitted where
it is recorded as a user constraint, tagged accordingly.

---

## 9.4 Validator review

Validators are research artifacts and are reviewed to the same standard as prompts
(`ERROR_TAXONOMY` §2.3). For each rule: the **invariant** it asserts, the **proof
obligation** its implementation must discharge, and the ways it can be wrong.

A rule is sound only when its evidence-gathering can actually observe the thing it checks.
Two rules failed exactly there: A-4 guarded on a member of the triple it was validating,
and A-5 could not see a range endpoint.

| Rule | Invariant | Proof obligation | False-pass risk | False-fail risk |
|---|---|---|---|---|
| A-1 | Intent is purpose, not solution | Scan an authored sentence | Unlisted solution term | Domain noun that is not a solution |
| A-2 | Some behaviour was recorded | Count by kind | Behaviour mis-kinded as constraint | Product with genuinely no behaviour |
| A-3 | Every function clause is discharged | Clause→requirement reachability | **Misclassified clause is never counted** | Clause discharged by a correctly non-functional requirement |
| A-4 | The bound triple is complete and consistent | Examine all three members jointly | *(was: guarded on one member — fixed)* | Legitimate single-sided bound rejected |
| A-5 | Every source quantity survives | Parse ranges before scanning literals | *(was: blind to range endpoints — fixed)* | Quantity legitimately recorded as an unknown |
| A-6 | Solution terms are quoted, not inferred | Term ∈ some cited clause | Term quoted from an unrelated clause | *(was: all user quotations — fixed)* |
| A-7 | Supplied content is marked | Origin distribution | Assumption recorded with stated origin | Genuinely no supplied content |
| A-8 | Origin discriminates | Distinct origin values | Single mis-tagged item satisfies it | Short request legitimately all-stated |
| A-9 | Context is grounded in this product | Citation present | Citation to an unrelated clause | *(was: lexical stem mismatch — fixed)* |
| A-10 | Priority discriminates | Distinct values | Two values on a large set | Small set legitimately uniform |
| A-11 | No duplicate statements | Exact match | Near-duplicates in different words | — |
| A-12 | Verification intent exists | Presence | Intent present but vacuous | — |
| A-13 | Source preserved | Non-empty | Truncated source | — |
| A-14 | No unknown contradicts a resolved target | Substring match | Contradiction in different wording | Coincidental substring |
| A-15 | Input difference survives into output | Cross-product comparison | Difference recorded in an unexamined field | Legitimately similar products |
| A-16 | Ledger covers all inputs | Clause sources present | Clarification clauses omitted wholesale | — |
| A-17 | References resolve | Id set membership | — | — |
| A-18 | No orphan requirements | Provenance present | Requirement cites an unrelated clause | — |
| A-19 | Verification intent is coherent | Kind/field agreement | Observable present but meaningless | — |
| A-20 | Freedoms are preserved, not invented | Clause with `freedom` disposition | Freedom cites a misclassified clause | Freedom legitimately supplied by policy |
| A-21 | Freedom ≠ requirement | Statement comparison | Same content, different words | — |
| A-22 | Relations resolve | Id membership | — | — |
| A-23 | Conflicts are justified | Rationale non-empty | Vacuous rationale | — |
| A-24 | Scenario bindings resolve | Id membership | — | — |
| A-25 | Some scenario binds something | Any non-empty | One scenario satisfies it for all | — |
| A-26 | Assumptions pair with unknowns | Id membership | Assumption with null pairing | Assumption legitimately unpaired |
| A-27 | Unknown targets resolve | Id membership | — | — |
| A-28 | Unknowns are substantive | Non-empty fields | Filler text | — |
| A-29 | Freedom and unknown are exclusive | Shared clause + subject | Same subject in different words | Genuinely different aspects of one clause |
| A-30 | Unknowns are consequential | `affects` or stated reason | Reason that does not explain | — |
| A-31 | Absence is declared | `declared_absent` entry | — | — |

### Standing weaknesses

- **A-3 depends on Pass A.** Its evidence is the clause ledger, so a misclassification
  upstream produces a false failure that looks like missing coverage. This is the single
  largest source of noise in the current rule set, and it is inherent: the rule cannot
  validate the classification it depends on.
- **Several rules use lexical proxies** (A-11, A-14, A-21, A-29). Each is defeated by the
  same content in different words. They are retained because a proxy that fails open is
  better than no check, but none should be read as proof.
- **A-15 examines a fixed field set.** A difference recorded only in an unexamined field
  would pass. Extending it as the schema grows is a standing obligation.

# 10. Regression Tests

Semantic invariants, not string comparisons. Each must hold **for every product in the
suite**, and none may be relaxed to accommodate a product.

| # | Invariant |
|---|---|
| **RT-1** | Every acceptance rule A-1 … A-14 passes for every product |
| **RT-2** | A-15 holds across every pair of products in the suite |
| **RT-3** | Functional coverage does not regress: the count of source behavioural clauses discharged never decreases for any product |
| **RT-4** | No mechanism term appears in any `product_intent` or requirement `statement` |
| **RT-5** | Removing any product from the suite changes no rule, threshold, lexicon entry, or default |
| **RT-6** | Every quantitative target in the source is present, with unchanged value, unit, and comparator |
| **RT-7** | Declared unknowns are never silently converted into requirements between revisions |
| **RT-8** | A deliberately vague request produces a spec that is *complete in form* — populated unknowns, no invented quantities |
| **RT-9** | A deliberately over-specified request produces no dropped requirements |

**Negative controls.** The suite must retain at least one input expected to yield a largely
unknown-populated spec (RT-8). A suite in which everything is fully determined has stopped
measuring interpretation (protocol §7.2).

---

# 11. Success Criteria

Stage 01 may be provisionally frozen (protocol §8) when:

- the produced `RequirementSpec` satisfies §6.5 for every product in the suite,
- functional coverage is demonstrated rather than assumed,
- the stated/supplied boundary is exercised, not collapsed,
- unknowns and freedoms survive the stage,
- downstream stages need no access to the original request,
- no rule, lexicon entry, or default is traceable to a specific product,
- and the schema debts of §8.1 are recorded and unresolved rather than worked around.

---

# 12. Open Questions

Carried forward; each must be answered by implementation evidence, not speculation.

| # | Question | Status |
|---|---|---|
| **OQ-1** | How should ambiguity be represented structurally? | Open — currently a flat string list; SD-6 |
| **OQ-2** | Should requirement confidence be represented? | Open |
| **OQ-3** | Where should clarification loops live — in this stage, or as a distinct interaction? | Open |
| **OQ-4** | How should conflicting requirements be represented without arbitrating them? | Open — SD-4 |
| **OQ-5** | What is the minimum `RequirementSpec` that still generalizes to complex products? | Open |
| **OQ-6** | Do declared design freedoms belong to Stage 01 at all, or are they properly a Stage 02 search-space concern? | **Open — genuinely arguable.** Recorded here as RD-10 provisionally, because the information originates in the request and would otherwise be lost |

> **Note on OQ-1 and OQ-4.** These were previously marked open while the implementation
> shipped an answer by default. A deferred question answered by omission is specification
> drift (protocol §10, M3). They remain open, and the current representation is recorded as
> a debt (SD-4, SD-6) rather than accepted as the contract.
