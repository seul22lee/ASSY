
# BM-101_GENEVA_INDEXING_BOX.md

# Benchmark 101 — Geneva Indexing Box

> **Advanced Mechanical Benchmark**
>
> This benchmark evaluates ASSY-Next on a product containing an intermittent
> indexing mechanism. Unlike the Core Benchmarks, this benchmark stresses
> phase-dependent kinematics, timing, tolerance, and motion reasoning.
>
> It is intended for later validation of the complete ASSY-Next pipeline.
> It should not be treated as part of the initial implementation milestone.

---

# 1. Purpose

This benchmark evaluates the system's ability to engineer a mechanically
coherent product whose primary functionality depends on a Geneva indexing
mechanism.

Primary engineering stresses:

- intermittent motion
- phase-dependent kinematics
- indexing accuracy
- dwell behavior
- spatial packaging
- shaft support
- assembly planning
- tolerance reasoning
- revision robustness

---

# 2. User Requirement

The system receives only the following request.

---

Design a compact desktop indexing box.

The user should rotate an external hand crank to advance an internal indexing
platform by one discrete step.

The output should remain stationary between indexing events.

The mechanism should be enclosed inside a protective housing.

The product should be mechanically plausible, easy to assemble, practical to
manufacture, and suitable for repeated manual operation.

---

# 3. Clarifications

If clarification is requested:

- Desktop-sized product.
- Manual operation only.
- The number of indexed positions is not prescribed.
- Different housing layouts are acceptable.
- Multiple support strategies are acceptable.
- The Geneva implementation may vary provided the required behavior is achieved.

---

# 4. Fixed Requirements

The final product must include:

- enclosed housing
- external hand crank
- intermittent indexing mechanism
- indexed output platform
- stable dwell between indexing events
- structurally supported rotating elements
- practical assembly strategy
- manufacturable construction

---

# 5. Allowed Design Freedom

The implementation may choose:

- Geneva geometry
- number of stations
- support arrangement
- bearing strategy
- housing architecture
- materials
- manufacturing process
- fastening strategy

Engineering reasoning should determine the design.

---

# 6. Forbidden Assumptions

Do not assume:

- a predefined Geneva geometry
- predefined dimensions
- predefined tolerances
- predefined materials
- benchmark-specific heuristics
- a hidden reference design

The benchmark evaluates engineering reasoning rather than reproduction.

---

# 7. Required Functional Behaviour

The output should:

- advance discretely
- remain stationary during dwell
- avoid unintended reverse indexing
- maintain mechanically plausible engagement
- remain enclosed inside a stable product

---

# 8. Expected Engineering Challenges

Representative challenges include:

- Geneva wheel geometry
- driver pin engagement
- locking geometry
- shaft support
- bearing placement
- motion envelopes
- phase-dependent clearance
- packaging
- assembly order
- tolerance allocation
- manufacturing compatibility

These are representative rather than exhaustive.

---

# 9. Evaluation Philosophy

The benchmark evaluates:

- engineering reasoning
- mechanism integration
- spatial coherence
- manufacturability
- CAD readiness
- revision capability

Different engineering solutions are acceptable if they satisfy the required
behavior.

---

# 10. Stress Map

| Engineering Domain | Stress |
|--------------------|:------:|
| Requirement Interpretation | ★★★☆☆ |
| Mechanism Synthesis | ★★★★★ |
| Product Architecture | ★★★★★ |
| Spatial Integration | ★★★★★ |
| Motion Planning | ★★★★★ |
| Structural Support | ★★★★☆ |
| Assembly | ★★★★☆ |
| Manufacturing | ★★★☆☆ |
| Tolerance | ★★★★★ |
| Revision | ★★★★★ |

---

# 11. Success Criteria

A successful solution should:

- satisfy the functional requirements
- produce correct intermittent indexing behavior
- provide complete support and motion definitions
- package the mechanism into a coherent product
- support deterministic downstream CAD generation
- support engineering validation and later revision

There is intentionally no unique correct solution.
