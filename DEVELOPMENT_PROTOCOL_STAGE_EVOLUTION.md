# Stage Evolution Protocol

## Purpose

This document defines how ASSY-Next evolves each Stage.

The objective is **not** to maximize benchmark performance.

The objective is to construct a general engineering reasoning pipeline capable of
producing mechanically complete products across arbitrary engineering problems.

Benchmark-specific logic is prohibited.

---

# Fundamental Principle

ASSY-Next is **not** optimized by adding benchmark-specific rules.

Instead, every improvement must take the form of a better general engineering
reasoning process.

Every benchmark failure should be converted into a more general engineering
question.

Never into a benchmark-specific solution.

---

# Development Order

Stages are improved sequentially.

The downstream pipeline remains frozen while a stage is under development.

Example

Stage 01

↓

BM-001
BM-002
BM-101

↓

Audit

↓

Improve common prompt

↓

Regression

↓

Freeze Stage 01

↓

Stage 02

↓

...

No stage should compensate for deficiencies in earlier stages.

---

# Stage Development Loop

Every Stage follows exactly the same procedure.

## Step 1

Freeze all downstream stages.

Only the target Stage may change.

---

## Step 2

Run every benchmark.

Current benchmarks:

- BM-001
- BM-002
- BM-101

Future benchmarks follow the same protocol.

---

## Step 3

Inspect only the output of the target Stage.

Do NOT inspect the final CAD first.

The question is

"Did this Stage preserve all information required by later engineering reasoning?"

not

"Did the final CAD succeed?"

---

## Step 4

Compare against engineering completeness.

Ver1.0 is used only as evidence of engineering completeness.

Ver1.0 is NOT the implementation to reproduce.

Specifically:

Allowed:

- engineering depth
- failure modes
- missing engineering facts
- physical completeness
- evaluation methodology

Not allowed:

- code structure
- templates
- mechanism cards
- benchmark-specific rules
- geometry reuse
- task-specific prompts

---

## Step 5

Identify reasoning gaps.

Every missing engineering fact must be classified as

- information loss
- unjustified assumption
- premature decision
- missing reasoning
- missing representation

Never classify it as

"BM-001 requires a hinge."

Instead classify

"A moving body with a revolute DOF was not required to obtain a physical support embodiment."

---

## Step 6

Improve ONE common prompt.

Every LLM Stage owns exactly one benchmark-independent prompt.

Prompt improvements must

- generalize
- preserve traceability
- preserve provenance

Prompt improvements must NEVER mention

- benchmark names
- product names
- expected mechanisms
- expected components

---

## Step 7

Regression.

Run every benchmark again.

The exact same prompt must execute for all benchmarks.

No benchmark-specific branches may exist.

---

## Step 8

Record Prompt Evolution.

Every prompt change must record

Observed failure

Rejected benchmark-specific solution

General engineering reasoning gap

Prompt improvement

Regression coverage

Remaining risks

---

## Step 9

Freeze the Stage.

Proceed to the next Stage only after

- completeness improves
- regressions are understood
- prompt remains benchmark-independent

---

# Benchmark Independence

The following are prohibited inside shared prompts.

Examples

❌

"If the product is a storage box, create a hinge."

"If the mechanism is a gear, add bearings."

"If BM-001 then..."

"If Geneva..."

"If Lift Box..."

Instead prompts must ask engineering questions.

Examples

✓

What bodies move?

Which DOFs are intended?

Which DOFs must be constrained?

What supports the allowed motion?

What transfers load?

What interfaces exist?

What remains unresolved?

---

# Role of ASSY_VER1.0

ASSY_VER1.0 is not the target architecture and not the target output.

It is an implementation evidence source.

Its purpose is to help answer questions such as:

- What engineering information was explicitly represented?
- What physical mechanisms were successfully embodied?
- What engineering checks were useful?
- What failure modes were discovered?
- What assumptions were unintentionally benchmark-specific?
- What limitations prevented further generalization?

Every observation from Ver1 must be classified into one of four categories:

1. General engineering principle
   - Independent of benchmarks and implementation.
   - Candidate to preserve.

2. Useful implementation evidence
   - Demonstrates a successful engineering realization.
   - May inspire ASSY-Next, but must not be copied directly.

3. Benchmark-specific implementation
   - Depends on prior topology knowledge, templates,
     handwritten geometry, or product-specific assumptions.
   - Must not be inherited into ASSY-Next.

4. Known limitation
   - A weakness that ASSY-Next should overcome.

Ver1 is therefore treated as engineering evidence,
not as engineering truth.

ASSY-Next should preserve only those ideas that remain valid after removing
benchmark-specific assumptions.

---

# Success Criterion

A Stage succeeds when

- engineering information is preserved,

- benchmark-independent reasoning improves,

- downstream stages require fewer assumptions,

- no benchmark-specific logic is introduced,

- the common prompt becomes more generally useful.

Not when

- one benchmark matches Ver1.0,

- CAD visually resembles Ver1.0,

- additional hard-coded rules are added.

---

# Long-term Objective

Ver1.0 demonstrated high engineering completeness for a narrow class of
products.

ASSY-Next must achieve equal or greater engineering completeness while remaining
fully general.

The architecture must remain Stage-based.

Engineering quality should emerge from increasingly better reasoning, not from
benchmark-specific implementation.
