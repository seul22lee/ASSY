# DEVELOPMENT_LOG.md

> **ASSY-Next Development Log**
>
> This document is the research notebook and implementation history of ASSY-Next.
>
> Unlike the stable project documents, this file is expected to evolve continuously.
>
> Every implementation, architectural decision, experiment, and important observation should be recorded here.
>
> The purpose is not only to track progress, but also to preserve the reasoning behind engineering decisions and avoid repeating failed ideas.
>
> This document should always represent the current state of the project.

---

# Project Status

## Current Phase

**Phase 1 — Core Framework Definition**

The project's philosophy, engineering rules, domain language, and system architecture are being established before implementation.

---

## Overall Progress

| Component | Status |
|------------|--------|
| Project Charter | ✅ Complete |
| Engineering Rules | ✅ Complete |
| Domain Specification | ✅ Complete |
| System Architecture | ✅ Complete |
| Development Log | 🟡 Active |
| Stage 01–05 Specifications | ✅ Complete |
| Stage 05 working-state model | ✅ Falsified and implemented |
| Domain objects (12) | ✅ Implemented |
| Stage 01 Requirement Interpreter | 🟡 Placeholder (deterministic) |
| Stage 02 Mechanical Architecture | 🟡 Placeholder (catalogue + weighted score) |
| Stage 03 Product Architecture | 🟡 Placeholder (role-derived regions) |
| Stage 04 Concept Visualization | 🟡 Placeholder (textual, no image model) |
| Stage 05 Engineering Integration | ✅ Real loop, partial knowledge base |
| Parametric Solver | 🟡 Evaluates declared values; no optimisation |
| CAD Builder | ✅ Deterministic compiler, primitive geometry |
| Simulation Pipeline | ✅ MuJoCo, commitment-derived physics |
| Evaluation Pipeline | ✅ Implemented |
| Revision Pipeline | 🟡 Routes; does not yet re-execute |
| Geometry IR | ➖ Superseded by the Stage 05 commitment store |

---

# Current Roadmap

## Phase 1 — Foundation

Status: **In Progress**

Objectives

- Define project philosophy
- Define engineering rules
- Define domain language
- Define system architecture

---

## Phase 2 — Requirement Understanding

Status: **Pending**

Objectives

- Design Stage 01
- Implement Requirement Interpreter
- Validate RequirementSpec generation

---

## Phase 3 — Mechanical Concept Planning

Status: **Pending**

Objectives

- Design Stage 02
- Implement Mechanical Concept Planner
- Validate MechanicalConceptPlan generation

---

## Phase 4 — Geometry Representation

Status: **Pending**

Objectives

- Design Geometry IR
- Design Stage 03
- Implement Geometry Planner

---

## Phase 5 — Deterministic Engineering

Status: **Pending**

Objectives

- Parametric Solver
- CAD Builder
- Geometry validation

---

## Phase 6 — Physical Validation

Status: **Pending**

Objectives

- Simulation Builder
- MuJoCo integration
- Metric extraction
- Requirement evaluation

---

## Phase 7 — Revision System

Status: **Pending**

Objectives

- Revision routing
- Local geometry revision
- Concept revision
- Full engineering iteration loop

---

# Current Architecture Decisions

This section records architectural decisions that define the framework.

Each decision should include:

- Decision
- Reason
- Expected impact
- Status

---

## AD-001

### Decision

Separate engineering reasoning from deterministic engineering execution.

### Reason

LLMs are effective at semantic reasoning but should not perform deterministic engineering computation.

### Expected Impact

Improved correctness, reproducibility, and modularity.

### Status

Accepted

---

## AD-002

### Decision

Use multiple narrowly scoped LLM stages instead of one large planning stage.

### Reason

Smaller reasoning problems are generally more reliable and easier to revise.

### Expected Impact

Improved modularity and lower token usage.

### Status

Accepted

---

## AD-003

### Decision

Perform deterministic evaluation before any revision.

### Reason

Engineering revisions should always be based on measured evidence.

### Expected Impact

More reliable revision decisions.

### Status

Accepted

---

## AD-004

### Decision

Use deterministic revision routing whenever possible.

### Reason

LLMs should only be used when genuine engineering reasoning is required.

### Expected Impact

Reduced token usage and simpler execution.

### Status

Accepted

---

## AD-005

### Decision

Delay Geometry IR design until Stage 01 and Stage 02 are implemented.

### Reason

Geometry representation should be driven by implementation evidence rather than speculation.

### Expected Impact

A more general and stable Geometry IR.

### Status

Accepted

---

# Open Architecture Questions

These are unresolved research questions.

Only questions that may influence the architecture belong here.

---

### OA-001

What is the most general Geometry IR that supports:

- CAD generation
- simulation
- revision
- local patching
- manufacturability
- future complex mechanisms

Status

**Resolved (2026-07-26, AD-006).** No separate Geometry IR was needed. Deriving
the engineering process first showed the CAD-ready definition is a projection of
the Stage 05 commitment store, with each downstream consumer reading a different
projection of the same state.

---

### OA-002

How should symbolic parameter relationships be represented to maximize solver flexibility while minimizing complexity?

Status

Open

---

### OA-003

How should simulation semantics be represented independently of MuJoCo?

Status

Open

---

# Known Technical Risks

## Risk 1

Geometry Planner may become responsible for too many unrelated engineering decisions.

Mitigation

Keep Geometry IR independent from CAD implementation.

---

## Risk 2

Token usage may increase as design complexity grows.

Mitigation

Continue using minimal structured context and patch-based revisions.

---

## Risk 3

Geometry quality may degrade if mechanical integration is treated as an afterthought.

Mitigation

Require product-level geometry reasoning during planning.

---

# Implementation Rules for Claude

At the end of every meaningful implementation task:

1. Update this document.
2. Record completed work.
3. Record important engineering observations.
4. Record architecture changes.
5. Record newly discovered limitations.
6. Record open questions.
7. Record benchmark-independent insights.
8. Update roadmap status if necessary.

Do **not** record trivial implementation details such as variable renaming or formatting.

---

# Research Log

---

## 2026-07-25

### Summary

Initial framework definition completed.

### Completed

- Project philosophy established.
- Engineering rules established.
- Stable domain language defined.
- Initial system architecture defined.

### Major Decisions

- Separate reasoning from execution.
- Three primary LLM planning stages.
- Deterministic engineering pipeline.
- Simulation-first evaluation.
- Revision starts from the earliest affected stage.
- Token efficiency treated as a core architectural objective.
- Geometry IR intentionally postponed until sufficient implementation evidence exists.

### Lessons Learned

The project should prioritize stable engineering concepts over early implementation details.

Several implementation-level specifications were intentionally moved out of the architecture into future stage documents.

### Next Objective

Create the Stage 01 (Requirement Interpreter) specification.

---

## 2026-07-26

### Summary

Implemented the complete pipeline as a vertical slice. Every stage executes for
every benchmark. The objective was interface correctness, not stage quality.

### Completed

- 12 domain objects with ownership, provenance, and versioning metadata.
- All 12 stages implemented and wired end to end (`assy/pipeline.py`).
- Stage 05 working-state model implemented in full, including all six
  modifications the Geneva falsification established.
- Explicit engineering knowledge extracted into `assy/knowledge/`:
  spawning rules, check library, resolvers, machine elements, materials,
  mechanism catalogue. None of it lives in prompts.
- Deterministic CAD via build123d (STEP + STL); MuJoCo simulation; metric
  extraction; requirement evaluation; revision routing.
- 23 interface contract tests; Geneva regression probe with 7 assertions.

### Decisions

**AD-006 — The Geometry IR is the Stage 05 commitment store.** OA-001 asked for
a general Geometry IR. Deriving the engineering *process* first (per
STAGE_05 section 5) showed that a separate IR is not needed: the CAD-ready
definition is a projection of the commitment store, and the four downstream
consumers each read a different projection of the same state. No separate
representation was introduced.

**AD-007 — Placeholder stages must be transparent, never plausible.** Stage 01–04
are deterministic stand-ins. `DeterministicReasoner` selects among structured
options and never invents engineering content, so a placeholder decision can
never be mistaken for engineering evidence (Rule L-5).

**AD-008 — The simulation plan derives its physics from commitments.** The first
MJCF modelled the platform as a generic spring-damper positioner. It drooped
13 mm under load and sagged when unpowered, contradicting the self-locking
commitment Stage 05 had verified analytically. Joint friction is now derived
from `lift_screw.backdrive_behaviour`. A simulation that contradicts a
commitment is not evidence about the design.

**AD-009 — Benchmarks and architecture experiments are separate categories.**
A benchmark evaluates the complete pipeline; an experiment validates or falsifies
an architectural hypothesis. `benchmarks/` carries a `Tier` (core / advanced);
`experiments/` carries hypothesis records. A product may appear in both in
different roles — Geneva is evidence for the Stage 05 architecture *and*, as
BM-101, an advanced benchmark. Promotion runs one way only: investigate as an
experiment first, promote to a benchmark only if it proves valuable as a complete
product-level evaluation. The purpose of the separation is to keep a benchmark
from becoming the reason the architecture has a particular shape.

### Observations

**Two benchmark-specific couplings appeared in the implementation, both mine.**
The CAD builder and the `motion_interference` check were written against the
lift-box topology and failed immediately on the other benchmark. Both are now
generic — shape rules and checks key on engineering roles. Running a second
structurally different benchmark is what exposed this; one benchmark would not
have.

**Checks must close the problems they open.** A check that detects a problem
must also clear it when a later run passes, or a transient detection blocks the
agenda permanently. This was not in the Geneva findings and only appeared under
execution.

**Incomplete knowledge surfaces as honest incompleteness, not failure.** BM-001
has no compliant-retention resolvers, so Stage 05 reports `ready=False` with
named inconclusive checks, the simulation plan emits zero tests rather than
fabricating a mover, and evaluation returns `insufficient_evidence`. The system
declines to claim what it cannot support.

**A metric definition error is indistinguishable from a design failure until
inspected.** Travel was first measured peak-to-peak, which reported a 103 mm
servo overshoot as achieved travel against a 100 mm limit. It looked exactly
like a real requirement violation. Observables now measure settled values.

**A first-match intent classifier produced a false pass, which is worse than any
failure.** BM-101 asks for an "indexing platform". The Stage 02 conversion table
tested the translation pattern first, `platform` matched, and the pipeline
selected a **lead screw for an indexing product** — then ran to `ready=True` and
`overall=pass`. Every downstream stage behaved correctly; they were simply
answering about a different machine. Two lessons:

1. Intent matching is now *scored*, not first-match, and words naming a part
   (`platform`, `turntable`) are weighted below words naming the output motion
   (`index`, `lift`). Competing intents with equal evidence now raise a
   requirement-clarification error instead of silently picking one.
2. **Identical commitment counts across structurally different products is a
   false-pass signature.** BM-101 and BM-002 both reported 84 iterations and 226
   commitments. That coincidence is what exposed the defect, and it is worth
   treating as a routine cross-benchmark sanity check.

This is direct evidence for keeping benchmarks and experiments separate (AD-009):
the failure was invisible within BM-002 alone and only appeared when a
structurally different problem ran through the same code.

### Open Questions

- **OA-001 — resolved** by AD-006; the commitment store is the representation.
- **OA-004** How much of the knowledge base must exist before a product class is
  supportable? BM-001 needs compliant-retention resolvers that BM-002 did not.
- **OA-005** Should the revision loop re-execute automatically, and under what
  budget? Routing exists; iteration does not.
- **OA-006** How should judgment checks participate in gating? None are
  implemented, and the gating policy for them is still unspecified.

### Next Objective

Close the knowledge gaps BM-001 exposed (compliant retention, hinge motion), then
implement revision re-execution so the loop in SYSTEM_ARCHITECTURE section 3
closes rather than terminating at the directive.

---

# Future Log Entries

Append new entries below this section.

Each entry should follow this structure:

```
## YYYY-MM-DD

### Summary

...

### Completed

...

### Decisions

...

### Observations

...

### Open Questions

...

### Next Objective

...
```

---

# Long-Term Research Notes

This section contains observations that remain useful across many iterations.

Only add information that is likely to influence future architectural decisions.

Current Notes

- Stable engineering concepts are more valuable than early implementation details.
- Generality should always be prioritized over benchmark performance.
- Geometry representation should emerge from implementation evidence.
- Token efficiency is an architectural constraint, not a later optimization.
- Engineering evidence should always dominate LLM reasoning.