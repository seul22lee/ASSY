# PROJECT_CHARTER.md

> ASSY-Next Project Charter
>
> Version: Draft 1.0
>
> This document defines the long-term philosophy, scientific methodology,
> architectural principles, and implementation mindset for the ASSY project.
>
> Every implementation decision should be evaluated against this document.
>
> Individual benchmark tasks, implementation instructions, or architectural
> proposals must never contradict these principles.

---

# 1. Vision

ASSY aims to build a general-purpose mechanical design framework capable of transforming natural language requirements into manufacturable, mechanically functional, and physically validated products.

The objective is **not** to automate CAD.

The objective is **not** to generate geometry.

The objective is to build a reasoning system capable of progressively converting engineering intent into validated mechanical designs.

The framework should eventually support products of increasing complexity while preserving architectural simplicity.

---

# 2. Research Goal

The project is a research effort rather than a software product.

The primary research question is:

> How can a large language model collaborate with deterministic engineering software to perform general mechanical design?

This question should guide every architectural decision.

Every implemented feature should contribute evidence toward answering this question.

---

# 3. Scientific Philosophy

Every implementation is considered an experiment.

Every architectural decision is considered a hypothesis.

Every benchmark is considered evidence.

Nothing should be accepted solely because it appears elegant or familiar.

Changes should be justified through implementation evidence.

The framework should continuously evolve through observation rather than speculation.

---

# 4. Generality First

Generality is the highest priority.

The framework must never become specialized for one benchmark, one mechanism, one CAD system, one simulator, or one product family.

Every implementation should be evaluated against the following question:

> Would this design still make sense for a significantly more complex mechanical product?

If the answer is no, reconsider the implementation.

---

# 5. Benchmarks Are Validation Cases

Benchmarks exist only to validate the framework.

Benchmarks do not define the architecture.

The first benchmark is not the target system.

The first benchmark is only the first experiment.

Whenever a benchmark introduces product-specific logic into the core framework, that implementation should be rejected.

Benchmark-specific behavior belongs in:

- fixtures
- simulation protocols
- acceptance criteria
- benchmark adapters

Never inside the core architecture.

---

# 6. Simplicity Over Cleverness

Architectural simplicity is a long-term asset.

Do not introduce:

- additional agents
- additional pipelines
- additional orchestration layers
- additional repair loops

unless there is clear implementation evidence that the existing architecture cannot support a demonstrated requirement.

Complexity should emerge from richer data and better reasoning—not from more components.

---

# 7. One Responsibility Per Stage

Every stage must answer exactly one engineering question.

Examples:

Requirement Interpreter

"What must be accomplished?"

Mechanism Planner

"What mechanical principles satisfy the requirements?"

Geometry Planner

"How should those mechanisms become product geometry?"

Simulation

"What physically happened?"

Evaluation

"What engineering conclusions can be drawn?"

Revision Planner

"What is the smallest justified modification?"

No stage should answer another stage's question.

---

# 8. LLM Philosophy

LLMs are reasoning modules.

They are not geometry engines.

They are not CAD kernels.

They are not simulation engines.

They are not numerical solvers.

LLMs should make engineering decisions.

Deterministic software should execute those decisions.

Every LLM call should have:

- one responsibility
- structured input
- structured output
- explicit validation

LLMs should never generate arbitrary executable CAD code.

---

# 9. Deterministic Engineering

Geometry generation, parameter solving, CAD construction, simulation, and validation should remain deterministic whenever practical.

Engineering software should always produce reproducible results from identical inputs.

LLMs should influence decisions rather than execution.

---

# 10. Simulation-Driven Design

Simulation is not the final goal.

Simulation is evidence.

Simulation should answer:

"What happened?"

Evaluation should answer:

"What does that mean?"

Revision should answer:

"What should change?"

Never merge these responsibilities.

---

# 11. Product Philosophy

A mechanically moving object is not necessarily a believable product.

Every generated design should satisfy both:

Mechanical plausibility

and

Product plausibility.

Product plausibility includes:

- believable proportions
- integrated mechanisms
- consistent wall structure
- manufacturable geometry
- reasonable assembly
- realistic user interaction
- coherent product form

Mechanisms should appear integrated into the product—not attached afterward.

---

# 12. Revision Philosophy

Revision is incremental.

The framework should always attempt the smallest justified modification.

Preferred order:

Parameter revision

↓

Geometry revision

↓

Form integration revision

↓

Mechanism revision

The framework should never redesign an entire product if a local modification is sufficient.

---

# 13. Session Memory

The framework maintains only current-session engineering memory.

There is:

- no RAG
- no vector database
- no retrieval from previous projects
- no cross-project learning

Only the current design session should be remembered.

This memory should contain engineering state—not conversation history.

---

# 14. Architecture Is a Working Hypothesis

The current architecture is not sacred.

It is the current best hypothesis.

It should remain stable until implementation evidence demonstrates a fundamental limitation.

Architecture should evolve through evidence—not preference.

Every proposed architectural change should include:

- observed limitation
- supporting evidence
- proposed solution
- complexity analysis
- generality analysis
- migration plan

---

# 15. Evidence Before Abstraction

Avoid speculative abstraction.

Generalization should be based on demonstrated variation rather than imagined future requirements.

Every abstraction should have at least two concrete use cases.

If only one benchmark benefits from an abstraction, it is probably premature.

---

# 16. Scientific Development Workflow

Every implementation task should follow the same sequence.

1. Define the engineering question.

2. Form a hypothesis.

3. Design the smallest experiment.

4. Implement.

5. Produce evidence.

6. Evaluate the result.

7. Document conclusions.

8. Define the next question.

Implementation should always be evidence-driven.

---

# 17. Coding Philosophy

Code should express engineering concepts rather than benchmark logic.

Core code should remain:

- reusable
- deterministic
- testable
- explicit
- composable

Avoid:

- hidden state
- implicit assumptions
- benchmark conditionals
- duplicated logic
- overly clever abstractions

Prefer explicit domain models over large dictionaries.

Prefer validation over silent correction.

Prefer clarity over brevity.

---

# 18. Data Philosophy

Structured engineering information is the foundation of the framework.

Engineering intent should always exist as validated structured data.

Every LLM output should become a validated domain object before entering the pipeline.

Free-form text should disappear as early as possible.

---

# 19. Evaluation Philosophy

Evaluation should produce engineering evidence rather than binary success.

An evaluation report should explain:

- what succeeded
- what failed
- why it failed
- what evidence supports that conclusion
- which stage should respond

Evaluation should never redesign the product.

---

# 20. Complexity Policy

Support increasing design complexity without increasing architectural complexity.

New mechanical concepts should primarily require:

- richer schemas
- additional evaluators
- additional geometry operations
- additional benchmark fixtures

They should not require:

- new orchestration pipelines
- benchmark-specific branches
- benchmark-specific agents

---

# 21. Decision Criteria

Every significant implementation decision should be evaluated against the following questions.

Does it improve generality?

Does it preserve responsibility boundaries?

Does it reduce unnecessary information flow?

Does it improve determinism?

Does it improve reproducibility?

Does it remain benchmark-independent?

Does it preserve architectural coherence?

Does it support more complex future designs?

If the answer to several of these questions is "no," reconsider the decision.

---

# 22. What This Project Is NOT

ASSY is not:

- a benchmark-specific CAD generator
- an autonomous CAD scripting engine
- a prompt engineering experiment
- a collection of disconnected agents
- a retrieval-heavy knowledge system
- a geometry-only optimization tool

The project is a structured engineering reasoning framework.

---

# 23. Working Mindset

When implementing any feature:

Think about the project before thinking about the benchmark.

Think about engineering before thinking about software.

Think about evidence before thinking about architecture.

Think about generality before thinking about convenience.

Think about the next ten benchmarks—not only today's benchmark.

---

# 24. Final Principle

Every implementation should move the project closer to answering one fundamental question:

> Can a structured collaboration between language models and deterministic engineering software perform general mechanical design?

If a proposed implementation improves today's benchmark but weakens the answer to that question, it should not be accepted.

The benchmark exists to validate the framework.

The framework does not exist to solve the benchmark.
