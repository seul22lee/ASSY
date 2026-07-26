# BENCHMARK_SUITE.md

# ASSY-Next Benchmark Suite

> This document defines the philosophy, purpose, and engineering rules of the ASSY-Next benchmark suite.
>
> Individual benchmark documents define specific engineering problems.
> This document defines **how benchmarks should be designed and evaluated**.

---

# 1. Purpose

The benchmark suite exists to evaluate the engineering reasoning capability of ASSY-Next.

It is **not** intended to evaluate:

- prompt engineering
- benchmark memorization
- CAD modeling speed
- visual realism
- benchmark-specific heuristics

Instead, benchmarks evaluate the complete engineering pipeline:

```text
Natural Language Requirement
        ↓
Requirement Interpretation
        ↓
Mechanical Architecture
        ↓
Product Architecture
        ↓
Concept Visualization
        ↓
Engineering Integration
        ↓
CAD-Ready Engineering Definition
        ↓
CAD
        ↓
Simulation
        ↓
Revision
```

---

# 2. Core Philosophy

Every benchmark should reward:

- engineering reasoning
- generality
- traceability
- modularity
- deterministic downstream execution

A benchmark must never reward recognition of a known solution.

Different engineering solutions should be accepted when they satisfy the requirements.

---

# 3. Design Principles

A good benchmark should:

- represent a real product rather than an isolated mechanism
- require multiple engineering domains simultaneously
- allow multiple valid mechanical solutions
- exercise multiple pipeline stages
- expose realistic engineering trade-offs
- support future revisions

Avoid benchmarks with only one obvious solution.

---

# 4. Benchmark Structure

Each benchmark should contain:

1. Benchmark purpose
2. User requirement (natural language)
3. Clarifications
4. Fixed requirements
5. Allowed design freedom
6. Forbidden assumptions
7. Engineering challenges
8. Evaluation philosophy
9. Success criteria

Reference solutions should never appear in the public benchmark specification.

---

# 5. Evaluation Philosophy

Evaluation is requirement-driven.

The benchmark does not prescribe:

- mechanism type
- material
- manufacturing process
- geometry
- dimensions
- CAD strategy

The implementation should justify engineering choices instead of reproducing an expected design.

---

# 6. Coverage Goals

Across the benchmark suite, the system should be evaluated on:

- mechanism synthesis
- force transmission
- motion generation
- packaging
- structural support
- assembly
- manufacturability
- tolerance reasoning
- spatial reasoning
- safety
- serviceability
- revision capability

No single benchmark is expected to cover every engineering domain.

---

# 7. Benchmark Independence

Pipeline architecture must remain independent of any benchmark.

Benchmark-specific branches, prompts, rules, or shortcuts are prohibited.

If solving one benchmark degrades generality, the architecture should be reconsidered.

---

# 8. Evolution

The benchmark suite is expected to grow over time.

New benchmarks should introduce genuinely new engineering challenges rather than cosmetic variations.

Future benchmark families may include:

- compliant mechanisms
- power transmission
- fluid systems
- precision positioning
- robotics
- consumer products
- manufacturing fixtures

---

# 9. Current Benchmarks

BM-001 — Latching Storage Box

Primary stress:

- compliant design
- latch engineering
- enclosure integration
- additive manufacturing
- usability

BM-002 — Hand-Cranked Lift Box

Primary stress:

- mechanism synthesis
- power transmission
- packaging
- structural support
- assembly
- manufacturability

---

# 10. Success

The benchmark suite is successful when:

- different engineering solutions are accepted,
- benchmark-specific optimization is unnecessary,
- failures reveal architectural weaknesses,
- implementation evidence improves the framework,
- and benchmark results generalize to broader mechanical design problems.
