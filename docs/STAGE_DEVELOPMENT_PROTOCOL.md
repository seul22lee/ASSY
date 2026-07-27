# Stage Development Protocol

> **Research methodology, not software design.**
>
> This document defines how every ASSY-Next Stage will be developed, evaluated,
> improved, frozen, and regression-tested for the remainder of the project.
>
> It is deliberately written without reference to any particular product. Benchmarks
> appear only as instruments of the regression workflow. The protocol must remain valid
> for arbitrary future mechanical products.

**Status:** active from this point forward. Supersedes ad-hoc stage development.
**Companions:** [`ASSY_VER1_EVIDENCE_AND_LIMITATIONS.md`](ASSY_VER1_EVIDENCE_AND_LIMITATIONS.md)
(the evidence audit and the Engineering Output Quality Framework),
`PROJECT_CHARTER.md`, `ENGINEERING_RULES.md`, `DOMAIN_SPECIFICATION.md`.

---

# 1. Overall philosophy

## 1.1 Ver1 is evidence, not a target

ASSY_VER1.0 is a record of experiments run under a narrower and more constrained system.
It is read for **what it proved and what it failed to prove** — never for what to build.

- **Never copy** Ver1 code, architecture, mechanism cards, templates, prompts, CAD
  construction logic, golden IRs, or benchmark assumptions.
- **Do recover** its verification discipline (items R1–R12 of the evidence audit).
- **Do surpass** its structural limitations (items S1–S12), the first of which — human-
  supplied configuration — is the reason Ver1 cannot be the target at all.

Citing Ver1 is legitimate only in the form *"Ver1 demonstrated X under conditions Y, so
this dimension is reachable"* or *"Ver1 failed at X, so this is a known trap."*

## 1.2 Benchmark performance is not the objective

A benchmark is a **measuring instrument**. Optimizing against the instrument destroys the
measurement. The optimization objective is **engineering reasoning quality**, expressed as
the Engineering Output Quality Framework vector (D1–D15, levels L0–L3).

The practical consequence is uncomfortable and must be accepted in advance:

> **A change that improves a benchmark result but does not improve reasoning is a
> regression, and must be reverted even though the number improved.**

Conversely, a change that improves reasoning while a benchmark result gets *worse* may be
correct — most often when the system stops claiming something it could not support.

## 1.3 The dangerous level is L1, not L0

From the evidence audit, restated here because it governs everything below:

- **L0 (absent)** is visible. A missing claim announces itself.
- **L1 (asserted)** looks exactly like an answer. It is the level at which a system
  reports a number that no evidence supports.

Ver1's retracted V-B pass and this project's own peak-to-peak travel metric were both L1
wearing L3's clothes. **The protocol is designed primarily to prevent L1**, not to
maximise L3.

## 1.4 Stage architecture is fixed

The twelve-stage decomposition is **not** under revision by this protocol. Stage
boundaries change only through an Architecture Change Proposal justified by implementation
evidence (`DOMAIN_SPECIFICATION.md` §22), never as a convenience during stage work.

What evolves is the **reasoning inside each stage**, and the explicitness of its contract.

## 1.5 Depth emerges from reasoning, not from implementation

When a product comes out shallow, the correct response is to ask *what engineering question
was not asked* — never to add a rule that produces the missing artifact for that product.
Engineering depth must arrive as a consequence of better questions applied uniformly.

---

# 2. Stage evolution workflow

Every Stage follows the same lifecycle. No stage skips a step.

```text
Current implementation
        ↓
   (1) Audit                     observe outputs across all benchmarks
        ↓
   (2) Reasoning gap identification    name what was not reasoned about
        ↓
   (3) Stage specification update      change the contract first
        ↓
   (4) Common prompt update            derive the prompt from the contract
        ↓
   (5) Regression                      semantic, across every benchmark
        ↓
   (6) Freeze                          provisional, against §8 criteria
        ↓
   Next Stage
```

Each step produces a written artifact (§9.2). A step with no artifact did not happen.

## 2.1 Explicit prohibitions

**P1 · No benchmark-specific fixes.**
No branch, rule, prompt clause, threshold, or default may be conditioned on the identity of
a product, benchmark, or mechanism. This includes indirect conditioning — a rule that is
technically general but whose only possible trigger is one benchmark.

**P2 · No downstream compensation.**
If a stage receives incomplete input, the fix belongs upstream. A downstream stage may
**detect and report** an upstream deficiency; it may never **repair** one. Repairing
upstream deficiencies downstream hides the reasoning gap and guarantees it recurs.

**P3 · No skipping directly to prompt edits.**
Editing a prompt before updating the specification means the specification no longer
describes the system. The prompt is a *derivative artifact*. If a behaviour is worth
prompting for, it is worth specifying.

**P4 · No silent contract change.**
Changing what a stage emits, or what it may assume, is a specification change requiring
the full cycle — even when the code change is small.

**P5 · No freezing on an unexplained improvement.**
If a metric improved and no one can say which reasoning change caused it, the stage is not
frozen. Unexplained improvements are usually accidental benchmark fit.

---

# 3. Stage responsibilities

Every Stage owns **exactly one engineering question** (Rule A-1). The question is the
stage's identity: if a stage cannot answer it, the stage failed; if a stage answers a
different one, the architecture has drifted.

Prompts are **not** defined here. Only responsibility.

| # | Stage | The one engineering question |
|---|---|---|
| 01 | Requirement Interpretation | **What engineering problem is actually being asked?** |
| 02 | Mechanical Architecture | **What mechanical principles could realize the required functions?** |
| 03 | Product Architecture | **How are those principles organized into product subsystems?** |
| 04 | Spatial Plausibility | **Is the proposed product architecture spatially plausible?** |
| 05 | Engineering Integration | **How is the architecture embodied into manufacturable engineering?** |
| 06 | Parametric Resolution | **What numerical values satisfy the declared engineering relations?** |
| 07 | Deterministic Construction | **Can the resolved design be built exactly as specified, without invention?** |
| 08 | Validation Planning | **What must be physically demonstrated, and by which competent method?** |
| 09 | Evidence Production | **What did each method actually produce, and within what validity?** |
| 10 | Measurement | **What engineering quantities were observed?** |
| 11 | Requirement Judgement | **Does the available evidence satisfy the requirements?** |
| 12 | Revision Routing | **What is the earliest decision that must change?** |

## 3.1 Responsibility notes

**Stage 01 — Requirement Interpretation.**
Owns the distinction between what was *stated*, *implied*, *assumed*, and *unknown*. Owns
the verification intent: how each requirement could eventually be falsified. Must not
select mechanisms, propose form, or invent quantities to fill gaps. Governs framework
dimensions **D1, D13, D14**.

**Stage 02 — Mechanical Architecture.**
Owns the choice of physical principle and the motion/force chain that realizes each
function. Must expose genuine alternatives when they differ in principle, and record why
the others were rejected. Must not determine geometry, dimensions, or product form.
Governs **D1, D2**.

**Stage 03 — Product Architecture.**
Owns the organization of mechanisms into a coherent product: regions, packaging, access,
protection, service, load-path intent. Deliberately dimensionless. Must not re-decide the
mechanism. Governs **D4 (intent), D8 (intent)**.

**Stage 04 — Spatial Plausibility.**
Owns the question of whether the proposed organization can exist in space at all, before
expensive embodiment. This is a **verification** responsibility. Its authority is *negative*:
it may reject or flag, and it may never author engineering content. Governs **D4**.

> **Open decision.** The current `STAGE_04_CONCEPT_VISUALIZATION.md` asks a *generation*
> question ("what might this product plausibly look like?"). The responsibility above is a
> *verification* question. These are different stages with different authority. This
> protocol adopts the verification framing; the stage document must be reconciled to it, or
> the framing revisited, before Stage 04 work begins. **Flagged for decision.**

**Stage 05 — Engineering Integration.**
Owns everything required to make the design constructible without invention: entities,
interfaces, supports, motion definitions, tolerances, materials, processes, and the
resolution of engineering conflicts. Governs **D3, D5, D6, D7, D8, D9, D10**.

**Stage 06 — Parametric Resolution.**
Owns numbers only. May not invent topology, add entities, or relax a declared relation.
Must report infeasibility explicitly rather than returning a nearest solution. Governs **D11 (inputs)**.

**Stage 07 — Deterministic Construction.**
Owns exact realization. Its defining property is that it makes **no engineering decisions**:
if construction requires one, Stage 05 was incomplete and must be told so. Governs **D3, D12**.

**Stage 08 — Validation Planning.**
Owns the mapping from claim → competent method. Must declare each method's validity domain
and refuse to plan a test whose result could not bear on a requirement. Governs **D14**.

**Stage 09 — Evidence Production.**
Owns execution and honest reporting of what was produced, including instability, and must
keep method failure distinguishable from product failure. Governs **D11, D12**.

**Stage 10 — Measurement.**
Owns extraction of quantities with units, method, and validity. Must not judge. Governs **D13**.

**Stage 11 — Requirement Judgement.**
Owns the comparison of evidence to requirements, and the four-way distinction between pass,
fail, invalid method, and insufficient evidence. Must refuse to pass a claim whose supporting
method was outside its validity domain. Governs **D14**.

**Stage 12 — Revision Routing.**
Owns attribution: which decision, at which stage, must change — and the smallest such change.
Governs the loop's convergence, not any product property.

---

# 4. The Stage specification

**Each `STAGE_NN_*.md` is the single living specification for that stage.** There are no
separate reasoning-specification documents. When specification and implementation disagree,
**the specification is correct and the implementation is a defect.**

Every Stage document must eventually contain these ten sections, in this order:

| § | Section | Must answer |
|---|---|---|
| 1 | **Purpose** | Why this stage exists in the pipeline at all |
| 2 | **Engineering Question** | The single question from §3, verbatim |
| 3 | **Responsibilities** | What this stage decides — and, explicitly, what it must never decide |
| 4 | **Inputs** | Which upstream objects, in authority order, and which are non-authoritative |
| 5 | **Outputs** | The engineering objects emitted, and what each asserts |
| 6 | **Reasoning Procedure** | The engineering thinking to be performed, as questions and discoveries — *method-independent* |
| 7 | **Common LLM Prompt** | Exactly one, derived from §6, benchmark-independent |
| 8 | **Structured Output Schema** | The contract the output must validate against |
| 9 | **Deterministic Validation Rules** | Machine-checkable conditions for a satisfied contract |
| 10 | **Regression Tests** | Semantic tests that must hold across every benchmark |

## 4.1 Section 6 is the heart

The **Reasoning Procedure** is the part that must be written first and revised most. It is
not a prompt and not an algorithm: it is the set of engineering questions a competent
engineer would ask at this stage, the discoveries those questions must produce, and the
conditions under which the stage is complete.

It must be written so that **an LLM, a deterministic module, or a human** could each satisfy
it. If a procedure can only be satisfied by a language model, it is a prompt in disguise and
belongs in §7.

Recommended internal structure for §6:

- **Required discoveries** — what must be found, without saying how
- **Prohibited decisions** — what belongs to another stage
- **Completeness conditions** — when this stage may declare itself done
- **Known traps** — failure modes observed in this project or in Ver1 evidence

## 4.2 Exactly one prompt per stage

§7 contains **one** prompt. Not one per benchmark, product class, or mechanism family. A
second prompt is a benchmark branch wearing different clothing (P1).

Where genuinely different reasoning is required for different physics, that difference
belongs in the **knowledge the prompt draws on**, never in a fork of the prompt.

## 4.2b The Prompt Evolution Log is mandatory

**No undocumented prompt edit is permitted.** Every revision of §7, for every stage,
records seven fields:

| Field | Content |
|---|---|
| **Version** | vN, monotonic |
| **Reason** | The failure or gap being addressed |
| **Evidence** | The observation that motivated it, with a run reference |
| **Specification section affected** | Which numbered item of §6 changed, or *"none — instruction only"* |
| **Expected improvement** | Stated **before** the run |
| **Observed improvement** | Measured after |
| **Unexpected regressions** | What got worse, including nothing |

Three consequences:

- **Expected improvement is recorded before measurement.** A prediction written afterwards
  is a rationalisation, and cannot be wrong.
- **"Specification section affected: none" is a warning sign.** A prompt change with no
  contract basis is either an undocumented contract change (P4) or benchmark tuning (P1).
  It is permitted only for genuine instruction clarity — same obligation, clearer wording.
- **Regressions are recorded even when the net result improved.** A revision that fixes one
  property and silently degrades another is how prompt accretion (§10 M2) begins.

The log lives in the stage's prompt document and is append-only. Entries are never edited
after the fact; a mistaken entry is corrected by a later entry.

## 4.3 The four artifacts must agree

Sections 6, 7, 8, and 9 describe the same contract at four levels of formality — engineering
intent, natural-language instruction, data shape, and machine check. **A disagreement between
any two is a defect**, and the resolution order is always 6 → 7 → 8 → 9.

---

# 5. Placeholder philosophy

The current deterministic placeholders are **not** drafts of future prompts, and their
behaviour is **not** the specification.

A placeholder exists for exactly four reasons:

1. **Executable baseline** — the pipeline runs end to end today.
2. **Interface validation** — the stage's inputs and outputs compose with its neighbours.
3. **Deterministic fallback** — runs offline, reproducibly, with no external dependency.
4. **Regression reference** — a fixed point against which change is measured.

## 5.1 The relationship, stated precisely

```text
Stage Specification  (§6 Reasoning Procedure)
        ↓  derives
Common Prompt        (§7)
        ↓  produces
Structured Output    (§8)
        ↓  checked by
Deterministic Validator (§9)
        ↓
Accepted Stage Output
```

The placeholder attaches at the same point as the prompt — it is *an* implementation of §6,
deliberately a shallow one. It never defines §6.

## 5.2 Rules for placeholders

- **A placeholder must be transparently shallow.** It must never produce output that could
  be mistaken for engineering judgement. Preferring a visibly thin answer to a plausible
  invented one is the whole point (this is the L1 rule, §1.3).
- **A placeholder must never invent engineering content.** Selecting among structured
  options is acceptable; generating an engineering claim is not.
- **A placeholder must be labelled in the run artifacts** so no reader mistakes scaffolding
  for a result.
- **A placeholder is replaced, not grown.** Incrementally improving a placeholder until it
  resembles reasoning produces an unspecified system. Write §6 first, then implement against it.
- **Removing a placeholder is a specification event.** The stage document records what
  replaced it and why the replacement satisfies §6.

---

# 6. Benchmark independence

## 6.1 Prohibited forms

Never write, in a prompt, a specification, or code:

- ✗ "If the product is a box, create a hinge."
- ✗ "If the mechanism is a gear, add bearings."
- ✗ "If BM-001 …" / "for the lift box …" / "when indexing …"
- ✗ Any threshold, default, or bound chosen because it makes a known product work.
- ✗ Any list whose members were enumerated by looking at the benchmark set.

## 6.2 The required form

Every prompt and every specification clause must ask an engineering question that is
**meaningful for a product nobody has thought of yet**:

- ✓ "Which bodies move relative to which, and what constrains each remaining freedom?"
- ✓ "For each rotating element, what locates it, and what retains it axially?"
- ✓ "Which interfaces transmit load, and what is the path from each applied force to ground?"
- ✓ "Which declared behaviour has no physical carrier?"

A useful test: **replace every noun in the clause with an unfamiliar mechanism.** If the
clause stops making sense, it was benchmark knowledge.

## 6.3 Generalizing a benchmark failure

This is the central procedure of the protocol. Every benchmark failure must be converted
into a general reasoning improvement, or consciously declined.

```text
(1) OBSERVE      what is missing or wrong in the stage output
(2) ATTRIBUTE    which stage's question was not answered  (§7.3)
(3) ABSTRACT     what class of engineering situation does this belong to?
(4) GENERALIZE   state the reasoning gap without naming the product
(5) TEST         does the general statement change behaviour on unrelated products?
(6) SPECIFY      update §6 of the owning stage
(7) DERIVE       update §7 to ask for it
(8) REGRESS      confirm across all benchmarks (§7)
```

**Step 3 is where the discipline lives.** The abstraction must name a *class of engineering
situation*, not a class of product:

| Observed (specific) | ✗ Wrong abstraction | ✓ Right abstraction |
|---|---|---|
| A lid has no stop, so it folds over | "lids need stops" | *An unbounded degree of freedom is an incomplete motion definition; every DOF needs a declared range and a physical carrier for its limits.* |
| A gear shaft has no bearing | "gears need bearings" | *A rotating body must be located in five degrees of freedom and retained in the sixth.* |
| A part cannot be installed into a closed housing | "housings need split lines" | *Every part requires a collision-free insertion path in some assembly order; an enclosed volume constrains that order.* |

**Step 5 is the guard.** If the generalized statement changes nothing on any product other
than the one that motivated it, the abstraction failed — it is a benchmark patch with a
general-sounding description. Either abstract further or record it as declined.

## 6.4 Declining a generalization

Not every failure should be fixed. A failure may be **recorded and declined** when the
required knowledge does not yet exist, when the fix would need architecture change, or when
generalization would be speculative.

Declining is legitimate and must be explicit: the benchmark keeps failing, the failure is
recorded with its reason, and no local patch is applied. **A declined generalization is a
better outcome than a benchmark-specific fix**, because it leaves the deficiency visible.

---

# 7. Evaluation protocol

Executed **before any prompt change**, for the stage under development.

### Step 1 — Run every benchmark
All of them, on the current implementation, unmodified. Advanced-tier benchmarks are
included and expected to be incomplete; their incompleteness is data.

### Step 2 — Inspect only the target stage's output
Open only that stage's directory. Judge its output **on its own contract**, not on whether
the final product came out well. A stage that answered its question correctly is correct
even if the run failed later.

This isolation is why the run artifacts are stage-separated. It is also why the temptation
to look downstream must be resisted — downstream symptoms bias attribution.

### Step 3 — Identify missing engineering information
Against §5 (Outputs) and §6 (Completeness conditions) of the stage document, and against
the framework dimensions that stage governs. Record what is *missing*, not what is *wrong* —
absence is the more common and the more serious defect.

### Step 4 — Classify the failure

| Class | Meaning | Fix location |
|---|---|---|
| **Reasoning failure** | The right question was not asked, or was asked and answered poorly | §6, then §7 |
| **Representation failure** | The answer exists but cannot be expressed in the output | §8 (schema), then §5 |
| **Validation failure** | The output is wrong and nothing detected it | §9 (validators) |
| **Execution failure** | Specification and schema are correct; the implementation is broken | Code only — no specification change |

Classifying correctly matters more than fixing quickly. A representation failure fixed as a
reasoning failure produces prompt bloat that cannot help, because the answer has nowhere to go.

### Step 5 — Attribute to the earliest responsible stage
Trace backwards until reaching the stage whose question, correctly answered, would have
prevented the symptom. **Fix only there.** If two stages are plausible, the earlier one owns it.

### Step 6 — Update the Stage specification
§6 first. Then whichever of §5, §8, §9 the classification requires.

### Step 7 — Only then update the common prompt
§7 is derived from §6. If a prompt change does not correspond to a §6 change, one of the two
is wrong.

## 7.1 Semantic regression

Regression is **semantic**, never textual. Outputs will legitimately differ run to run once
reasoning is model-driven. What must hold:

- **Contract invariants** — every §9 validator passes for every benchmark.
- **Completeness monotonicity** — no framework dimension regresses from a higher level to a
  lower one on any benchmark.
- **Assumption monotonicity** — downstream stages require no more assumptions than before.
- **Honesty invariants** — nothing previously reported as uncertain is now reported as
  certain without new evidence.
- **Independence invariant** — the same prompt is used everywhere, and removing any
  benchmark from the suite changes no prompt, specification, or default.

## 7.2 False-pass detection

A pass is more dangerous than a failure. Before accepting an improvement, check:

- **Cross-benchmark divergence.** Structurally different products must produce structurally
  different outputs. Near-identical intermediate results across dissimilar products is a
  false-pass signature and must be investigated before anything else.
- **Evidence provenance.** Every improved result traces to evidence that could have come out
  the other way.
- **Negative controls.** At least one benchmark or fixture is expected to fail; if everything
  passes, the suite has stopped measuring.

## 7.3 Attribution discipline

The commonest methodological error in this project has been fixing a symptom where it was
observed. Attribution runs backwards from symptom to the earliest unanswered question, and
the fix goes there — even when a downstream fix is smaller, faster, and would make the
benchmark green.

---

# 8. Freeze criteria

A Stage may be **provisionally frozen** only when **all** of the following hold. Every one
is a veto.

| # | Criterion | Evidence required |
|---|---|---|
| F1 | **Engineering completeness improved** | At least one framework dimension the stage governs rose a level, on at least one benchmark, with none falling anywhere |
| F2 | **Benchmark-independent reasoning improved** | The change is expressible without naming any product, and demonstrably alters behaviour on more than one product |
| F3 | **One prompt for every benchmark** | §7 contains exactly one prompt, used unmodified everywhere |
| F4 | **Regression passes** | All §10 tests and all §7.1 invariants hold |
| F5 | **Downstream needs fewer assumptions** | A named reduction in what a later stage must assume or invent |
| F6 | **Uncertainty remains explicit** | Assumptions, deferrals, and validity domains are still represented; nothing became silently certain |
| F7 | **No benchmark-specific logic** | Confirmed by inspection of the diff, including defaults, thresholds, and enumerations |
| F8 | **Specification and implementation agree** | §§5–9 describe what the stage now does |

## 8.1 What "provisional" means

A freeze is a **commitment to stop working on the stage**, not a claim of correctness. A
frozen stage is reopened when:

- a downstream stage demonstrates a deficiency attributable to it (§7.5),
- a new product class exposes a reasoning gap,
- a framework dimension it governs is found at L1, or
- an architecture change alters its contract.

Reopening is normal. Reopening **without recording why** is not.

## 8.2 Freeze record

Every freeze is recorded in `DEVELOPMENT_LOG.md`: which dimensions moved and on which
products, what generalization was made, which downstream assumptions were removed, what
remains unresolved, and the evidence for F7.

---

# 9. Development order

## 9.1 Project sequence

```text
1. Ver1 engineering evidence audit          COMPLETE
2. Engineering Output Quality Framework     COMPLETE  (audit §5)
3. Stage Development Protocol               THIS DOCUMENT
4. Stage-by-stage evolution                 next
```

Stages are evolved **in pipeline order**, 01 → 12. Upstream first is not a preference: a
downstream stage cannot be correctly evaluated while its inputs are unspecified, because its
failures cannot be attributed (§7.5).

Two consequences to accept in advance:

- **Early stages will look unrewarding.** Improving Stage 01 does not visibly improve a
  product. It removes assumptions from every stage after it.
- **Later stages may need less work than expected**, because upstream improvements remove
  their compensating behaviour.

## 9.2 Per-stage cycle and artifacts

| Step | Artifact |
|---|---|
| Audit current implementation | Audit note: outputs across all benchmarks, per §7 steps 1–3 |
| Compare outputs across benchmarks | Divergence check (§7.2) — do dissimilar products diverge? |
| Identify reasoning gaps | Gap record: observation → abstraction → generalization (§6.3), one per gap |
| Update the Stage specification | Revised `STAGE_NN_*.md`, §§1–10 |
| Update the common prompt | §7 of that document, derived from §6 |
| Regression test | Regression result against §7.1 invariants |
| Provisionally freeze | Freeze record in `DEVELOPMENT_LOG.md` (§8.2) |
| Continue | Next stage |

## 9.3 Gap record template

```text
GAP-<stage>-<n>
Observed      : what was missing in the stage output, on which products
Class         : reasoning | representation | validation | execution   (§7.4)
Attributed to : stage NN, question "<the stage's question>"           (§7.5)
Abstraction   : the class of engineering situation, product-free      (§6.3 step 3)
Generalization: the reasoning gap, stated without naming any product
Cross-check   : which unrelated products this changes, and how        (§6.3 step 5)
Disposition   : specify | decline (with reason)                       (§6.4)
```

---

# 10. Known failure modes of this protocol

Stated so they can be detected. A methodology that does not anticipate its own failure modes
is itself an L1 claim.

**M1 · Generalization theatre.** A benchmark patch given a general-sounding description.
*Detection:* §6.3 step 5 — the statement changes nothing on any other product.

**M2 · Prompt accretion.** Each cycle adds a clause; the prompt becomes a checklist that no
longer reasons. *Detection:* §7 grows monotonically while §6 does not; clauses that no gap
record justifies.

**M3 · Specification drift.** Implementation moves, specification does not. *Detection:*
F8 fails; behaviour cannot be predicted from the document.

**M4 · Attribution drift.** Fixes accumulate downstream because they are cheaper.
*Detection:* late stages grow defensive logic; a stage handles cases its inputs should
have excluded.

**M5 · Freeze inflation.** Stages frozen to make progress visible. *Detection:* freeze
records without a named dimension change or a named downstream assumption removed (F1, F5).

**M6 · Suite saturation.** Every benchmark passes, so nothing is measured. *Detection:*
§7.2 — no failing negative control.

**M7 · Framework capture.** The framework is scored to look good rather than used to find
gaps. *Detection:* dimension levels rise without corresponding gap records.

---

# 11. Summary

- Ver1 is evidence. It is never copied, and its configuration mechanism is superseded.
- The objective is engineering reasoning quality, measured as a framework vector — not
  benchmark performance.
- Every stage owns one engineering question, specified in one living document with ten
  sections, of which the Reasoning Procedure is primary.
- Exactly one prompt per stage, derived from the specification, benchmark-independent.
- Placeholders are scaffolding: transparently shallow, never the specification, replaced
  rather than grown.
- Every benchmark failure is abstracted to a class of engineering situation and generalized,
  or explicitly declined. Never patched.
- Evaluation attributes backwards to the earliest unanswered question and fixes only there.
- A stage is frozen only on evidence of general improvement across eight criteria, and
  reopening is normal.
- Development proceeds in pipeline order, beginning with Stage 01.

**Next action:** reconcile the Stage 04 framing (§3.1, flagged for decision), then begin the
Stage 01 cycle at §9.2 step 1 — audit before any specification or prompt work.
