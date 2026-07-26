# ENGINEERING_RULES.md

> **ASSY-Next Engineering Rules**
>
> This document defines the implementation rules that every contributor and every LLM implementation must follow.
>
> Unlike `PROJECT_CHARTER.md`, which defines the philosophy of the project, this document defines the practical engineering rules that should guide every implementation decision.
>
> These rules should be treated as constraints unless implementation evidence demonstrates that a change improves the framework's generality.

---

# Documentation Rules

## Stable Documents

The following documents define the long-term identity of the project and should only change with strong implementation evidence:

- PROJECT_CHARTER.md
- ENGINEERING_RULES.md
- DOMAIN_SPECIFICATION.md

## Living Documents

The following documents are expected to evolve during implementation:

- SYSTEM_ARCHITECTURE.md
- STAGE_XX_*.md
- GEOMETRY_IR.md
- DEVELOPMENT_LOG.md

Changes to living documents are encouraged when they improve:

- generality
- engineering correctness
- modularity
- token efficiency
- implementation clarity

Do not modify stable documents merely because a different design appears cleaner.

---

# 1. Core Principle

Every implementation is an experiment.

Every architectural decision is a hypothesis.

Every benchmark is evidence.

Never optimize for the current benchmark at the expense of the general framework.

---

# 2. Generality Rules

## Rule G-1

Always design for the general mechanical design problem.

Never optimize specifically for:

- a benchmark
- a product
- a mechanism
- a CAD kernel
- a simulator

---

## Rule G-2

The active benchmark validates the framework.

It never defines the framework.

---

## Rule G-3

If a solution only works for one benchmark, assume it is incorrect until proven otherwise.

---

## Rule G-4

Before introducing any new abstraction, ask:

> Would this abstraction still make sense for products that are substantially more complex?

If the answer is no, redesign it.

---

# 3. Architecture Rules

## Rule A-1

Each stage answers exactly one engineering question.

Never merge unrelated responsibilities.

Never duplicate responsibilities.

---

## Rule A-2

Increase data richness before increasing architectural complexity.

Prefer:

- richer schemas
- better validation
- better evaluation
- better deterministic algorithms

before introducing:

- new agents
- new orchestration layers
- new repair loops
- benchmark branches

---

## Rule A-3

Every stage communicates only through validated structured data.

Never pass free-form engineering decisions between stages.

---

## Rule A-4

No stage should depend on another stage's prompt.

Only structured outputs may be consumed.

---

## Rule A-5

The architecture should evolve only through implementation evidence.

Never redesign because another architecture appears cleaner.

---

# 4. LLM Rules

## Rule L-1

LLMs perform engineering reasoning.

Deterministic software performs engineering execution.

---

## Rule L-2

Never ask an LLM to perform deterministic computation.

Examples:

- collision detection
- constraint solving
- CAD generation
- numerical optimization
- force calculation
- finite element analysis

---

## Rule L-3

Every LLM call must have one narrowly defined responsibility.

Avoid large prompts that ask the model to solve multiple engineering problems simultaneously.

---

## Rule L-4

Every LLM output must validate against a structured schema.

Invalid outputs are rejected.

---

## Rule L-5

Never trust an LLM prediction without deterministic verification.

Simulation always has higher authority.

---

# 5. Geometry Rules

## Rule GEO-1

Mechanisms should emerge naturally from the product.

Never attach mechanisms as isolated objects.

---

## Rule GEO-2

Products should appear manufacturable.

Avoid unrealistic wall structures.

Avoid disconnected supports.

Avoid impossible assemblies.

---

## Rule GEO-3

Geometry should preserve believable proportions.

Mechanical correctness alone is insufficient.

---

## Rule GEO-4

Every moving feature should have an engineering justification.

Every structural feature should have an engineering justification.

---

## Rule GEO-5

Geometry Planner defines intent.

CAD Builder constructs geometry.

Never mix these responsibilities.

---

# 6. Simulation Rules

## Rule SIM-1

Simulation is the source of engineering evidence.

---

## Rule SIM-2

Simulation measures.

Evaluation interprets.

LLMs revise.

These responsibilities must remain separate.

---

## Rule SIM-3

Never estimate physical performance when deterministic simulation is available.

---

## Rule SIM-4

Raw simulation data should never be sent directly to an LLM.

Always summarize it deterministically first.

---

# 7. Revision Rules

## Rule REV-1

Always attempt the smallest justified modification.

---

## Rule REV-2

Preferred revision order:

1. Parameter
2. Geometry
3. Mechanical concept
4. Requirement clarification

---

## Rule REV-3

Never redesign an entire product when a local modification is sufficient.

---

## Rule REV-4

Every revision must preserve as much of the previous design as possible.

---

## Rule REV-5

Every revision must be verified by simulation.

LLM reasoning is never considered evidence.

---

# 8. Token Efficiency Rules

Token efficiency is a first-class architectural requirement.

---

## Rule TOK-1

Only send information required for the current stage.

---

## Rule TOK-2

Never send the entire DesignSession to an LLM.

---

## Rule TOK-3

Never send complete CAD representations.

---

## Rule TOK-4

Never send raw simulation trajectories.

---

## Rule TOK-5

Never send unrelated history.

---

## Rule TOK-6

Prefer deterministic preprocessing over larger prompts.

---

## Rule TOK-7

Compress history before sending it to an LLM.

History should contain:

- recent iterations
- best iteration
- blocked directions
- preserved decisions

Nothing else.

---

## Rule TOK-8

Prefer patch outputs.

Do not regenerate complete plans unless required.

---

## Rule TOK-9

Avoid repeated LLM calls.

If deterministic software can solve the problem, use deterministic software.

---

## Rule TOK-10

Do not introduce retrieval systems or cross-project memory.

Only the current engineering session may be used.

---

# 9. Coding Rules

## Rule CODE-1

Represent engineering concepts explicitly.

Avoid anonymous dictionaries for core domain objects.

---

## Rule CODE-2

Every public model should have validation.

---

## Rule CODE-3

Every public class should describe its engineering responsibility.

---

## Rule CODE-4

Prefer pure functions whenever practical.

---

## Rule CODE-5

Avoid global mutable state.

---

## Rule CODE-6

Avoid hidden caches.

---

## Rule CODE-7

Avoid God classes.

---

## Rule CODE-8

Keep modules focused.

One module should represent one engineering concept.

---

## Rule CODE-9

Every stage should be independently testable.

---

## Rule CODE-10

Deterministic components should always produce reproducible outputs from identical inputs.

---

# 10. Benchmark Rules

## Rule BM-1

Never introduce benchmark-specific logic into the core framework.

---

## Rule BM-2

Benchmark fixtures belong in benchmark directories.

Core code should never check benchmark names.

Incorrect:

```python
if benchmark == "snap_box":
    ...
```

Correct:

Benchmark-specific configuration.

---

## Rule BM-3

A new benchmark should require:

- new fixtures
- new tests
- optional evaluator configuration

It should not require architecture changes.

---

# 11. Documentation Rules

Every major implementation should document:

- engineering question
- hypothesis
- implementation
- evidence
- conclusion

If the implementation changes the architecture, document:

- why
- supporting evidence
- expected impact
- migration strategy

---

# 12. Before Every LLM Call

Confirm:

- Is an LLM actually necessary?
- Can deterministic code solve this?
- Is the input minimal?
- Is the output schema defined?
- Is validation available?
- Is the token budget reasonable?

If any answer is "No", redesign the call.

---

# 13. Before Every Commit

Verify:

- No benchmark-specific logic entered the core.
- No unnecessary LLM calls were introduced.
- Structured schemas remain consistent.
- Token usage did not increase unnecessarily.
- The implementation remains general.
- Existing tests still pass.
- New functionality has corresponding tests.
- Documentation is updated when architecture changes.

---

# 14. Final Rule

When in doubt, prefer:

Generality over convenience.

Determinism over heuristics.

Evidence over assumptions.

Small revisions over large redesigns.

Structured engineering reasoning over prompt engineering.

Long-term architecture over short-term benchmark success.
