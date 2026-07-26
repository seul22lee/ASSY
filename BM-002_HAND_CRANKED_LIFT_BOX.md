
# BM-002_HAND_CRANKED_LIFT_BOX.md

# Benchmark 002 — Hand-Cranked Lift Box

> Public benchmark specification for ASSY-Next.
>
> This document defines the engineering problem only.
> It intentionally does not define the expected mechanism.

---

# 1. Purpose

This benchmark evaluates ASSY-Next's ability to synthesize a complete mechanical product involving power transmission, packaging, support, assembly, and manufacturability.

Unlike Benchmark 001, this problem requires the system to reason about multiple interacting machine elements inside an enclosed product.

Primary engineering stresses:

- mechanism synthesis
- power transmission
- load path reasoning
- machine element selection
- spatial integration
- packaging
- assembly
- manufacturability
- revision readiness

---

# 2. User Requirement

The system receives only the following request.

---

Design a compact desktop lifting box.

The user should rotate an external hand crank to raise and lower an internal platform.

The platform should lift approximately 80–100 mm and support a payload of approximately 1 kg.

The mechanism should be enclosed inside the housing.

The product should be safe to use, mechanically plausible, easy to assemble, and practical to manufacture.

Avoid obvious jamming or unstable operation.

---

# 3. Clarifications

If clarification is requested, the following information may be provided.

- Desktop-sized product.
- Manual operation only.
- Continuous or intermittent lifting is acceptable.
- Self-locking is optional if justified.
- Different transmission mechanisms are acceptable.
- Multiple shafts, bearings, guides, and supports are allowed.

---

# 4. Fixed Requirements

The final product must include:

- enclosed housing
- external hand crank
- internal lifting platform
- repeatable lifting motion
- force transmission mechanism
- platform guidance
- structurally supported rotating elements
- practical assembly strategy
- manufacturable construction

---

# 5. Allowed Design Freedom

The implementation may choose:

- rack and pinion
- lead screw
- worm gear
- cable or drum systems
- compound transmissions
- alternative mechanically justified solutions

Materials, manufacturing processes, layout, proportions, and internal architecture are intentionally unspecified.

---

# 6. Forbidden Assumptions

Do not assume:

- rack-and-pinion is the correct answer
- any specific gear ratio
- predefined housing layout
- predefined dimensions
- predefined material
- predefined manufacturing process
- benchmark-specific shortcuts

The engineering process should determine these.

---

# 7. Expected Engineering Challenges

Representative challenges include:

- transmission selection
- mechanical advantage
- load paths
- shaft support
- bearing placement
- axial retention
- platform guidance
- housing packaging
- motion envelopes
- assembly sequence
- service access
- manufacturing compatibility
- tolerance allocation
- user ergonomics
- back-drive behaviour

These are examples rather than a fixed checklist.

---

# 8. Evaluation Philosophy

The benchmark rewards engineering reasoning rather than a particular mechanism.

Different internally consistent products should be accepted.

The benchmark evaluates the quality of the engineering process and resulting design, not similarity to a hidden reference.

---

# 9. Stress Map

| Engineering Domain | Stress |
|--------------------|:------:|
| Requirement Interpretation | ★★★☆☆ |
| Mechanism Synthesis | ★★★★★ |
| Product Architecture | ★★★★★ |
| Spatial Integration | ★★★★★ |
| Packaging | ★★★★★ |
| Structural Support | ★★★★★ |
| Assembly | ★★★★☆ |
| Manufacturing | ★★★★☆ |
| Tolerance | ★★★☆☆ |
| Revision | ★★★★★ |

---

# 10. Success Criteria

A successful solution should:

- satisfy the functional requirements
- produce a mechanically coherent product
- select and justify an appropriate transmission architecture
- provide complete support and motion definitions
- be spatially packageable
- be manufacturable and assemblable
- produce a CAD-ready engineering definition
- support downstream deterministic validation

There is intentionally no unique correct solution.
