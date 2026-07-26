
# BM-001_LATCHING_STORAGE_BOX.md

# Benchmark 001 — Latching Storage Box

> Public benchmark specification for ASSY-Next.
>
> This document defines the engineering problem, not the expected solution.

---

# 1. Purpose

This benchmark evaluates whether ASSY-Next can transform a simple product request into a mechanically coherent consumer product.

Primary engineering stresses include:

- compliant mechanism reasoning
- latch synthesis
- enclosure integration
- manufacturability
- assembly
- user interaction
- revision readiness

---

# 2. User Requirement

The system receives only the following requirement.

---

Design a compact desktop storage box with a reusable latch.

The box should open and close repeatedly without accidental opening during normal handling.

The latch should be easy for a user to operate while remaining secure during transport.

The product should be suitable for low-cost manufacturing and should be practical for desktop use.

The design should be mechanically plausible and easy to assemble.

---

# 3. Clarifications

If clarification is requested, the following information may be provided.

- Approximate product size: desktop-sized (roughly hand-held).
- Opening angle is not prescribed.
- One-handed operation is desirable but not mandatory.
- Repeated opening and closing is expected.
- A separate metal fastener is allowed but not required.
- Multiple engineering solutions are acceptable.

---

# 4. Fixed Requirements

The final product must include:

- an enclosed storage volume
- a lid
- a repeatable opening mechanism
- a repeatable closing mechanism
- a latch or retention feature
- practical user access
- manufacturable construction
- feasible assembly strategy

---

# 5. Allowed Design Freedom

The system is free to choose:

- latch mechanism
- hinge mechanism
- materials
- manufacturing process
- wall construction
- fastening strategy
- overall appearance
- internal organization

Any mechanically justified solution is acceptable.

---

# 6. Forbidden Assumptions

Do not assume:

- a snap-fit latch
- a living hinge
- additive manufacturing
- injection molding
- magnets
- screws
- benchmark-specific dimensions
- benchmark-specific heuristics

The solution must emerge from engineering reasoning.

---

# 7. Expected Engineering Challenges

Typical engineering challenges include:

- latch force
- retention reliability
- compliant behavior (if used)
- hinge integration
- housing stiffness
- wall thickness
- support strategy
- packaging
- assembly sequence
- serviceability
- manufacturing compatibility
- tolerance allocation
- user ergonomics

These are representative rather than exhaustive.

---

# 8. Evaluation Philosophy

The benchmark evaluates engineering quality rather than similarity to a reference design.

Different mechanisms should receive equal consideration if they satisfy the requirements.

No mechanism is considered the canonical solution.

---

# 9. Stress Map

| Engineering Domain | Stress |
|--------------------|:------:|
| Requirement Interpretation | ★★★☆☆ |
| Mechanism Synthesis | ★★★★☆ |
| Product Architecture | ★★★★★ |
| Packaging | ★★★★☆ |
| Manufacturing | ★★★★★ |
| Assembly | ★★★★☆ |
| Tolerance | ★★★☆☆ |
| Revision | ★★★★☆ |

---

# 10. Success Criteria

A successful solution should:

- satisfy the functional requirements
- be mechanically coherent
- integrate the latch into the product architecture
- support deterministic downstream CAD generation
- support engineering validation
- remain general rather than benchmark-specific

There is intentionally no unique correct design.
