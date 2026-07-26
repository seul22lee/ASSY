# STAGE_02_MECHANICAL_ARCHITECTURE.md

# Stage 02 --- Mechanical Architecture Generator

> This document defines the responsibilities, engineering boundaries,
> and design philosophy of the Mechanical Architecture Generator.
>
> This is the first true engineering reasoning stage of ASSY-Next.

------------------------------------------------------------------------

# Purpose

The Mechanical Architecture Generator determines **how the required
functions can be realized mechanically**.

It does **not** determine geometry, dimensions, CAD features, or final
product appearance.

Its output is one or more **mechanically distinct architecture
candidates** that are capable of satisfying the engineering intent
defined by `RequirementSpec`.

------------------------------------------------------------------------

# Engineering Question

> **What physical principles and machine elements should realize the
> required functions?**

This stage answers:

-   What mechanisms should exist?
-   How should motion be transformed?
-   How should forces be transmitted?
-   How should required functions interact?

It does **not** answer:

-   What should the product look like?
-   Where should every component be located?
-   What dimensions should be used?
-   How should CAD features be constructed?

------------------------------------------------------------------------

# Inputs

Input:

-   RequirementSpec

No downstream information is available.

The Mechanical Architecture Generator must reason only from engineering
intent.

------------------------------------------------------------------------

# Outputs

Output:

`MechanicalArchitectureCandidateSet`

Candidate count is adaptive:

``` text
1 ... N
```

There is **no fixed number of candidates**.

Candidates should only be generated when they represent genuinely
different engineering solutions.

------------------------------------------------------------------------

# Responsibilities

Each candidate should define:

-   primary mechanical principle
-   motion transformation
-   major machine elements
-   major functional parts
-   interfaces between parts
-   force-transmission strategy
-   motion chain
-   degrees of freedom
-   locking or holding strategy
-   expected strengths
-   expected weaknesses
-   expected engineering risks
-   unresolved engineering questions

The output should explain **how the product works**, not **how it is
built**.

------------------------------------------------------------------------

# Candidate Policy

## Generate one candidate when:

-   one solution clearly dominates,
-   alternatives differ only cosmetically,
-   requirements strongly constrain the design.

## Generate multiple candidates when:

alternatives differ by engineering principle, including:

-   motion conversion,
-   force transmission,
-   back-driving behavior,
-   mechanism family,
-   packaging implications,
-   assembly strategy,
-   expected failure modes,
-   manufacturability tradeoffs.

------------------------------------------------------------------------

# Candidate Diversity Rule

Every candidate must differ by **engineering principle**, not cosmetic
implementation.

Good:

-   Rack-and-pinion
-   Lead screw
-   Cable drum

Bad:

-   Rack with blue housing
-   Rack with different guide thickness
-   Rack with slightly different mounting

------------------------------------------------------------------------

# Required Reasoning

The stage should reason about:

-   kinematics
-   force paths
-   machine elements
-   functional decomposition
-   mechanism selection
-   engineering tradeoffs

It should avoid detailed geometric reasoning.

------------------------------------------------------------------------

# Non-Responsibilities

This stage must NOT determine:

-   product appearance
-   housing geometry
-   wall thickness
-   shaft diameter
-   gear module
-   tooth count
-   pressure angle
-   backlash
-   bearing dimensions
-   CAD operations
-   feature trees
-   exact dimensions
-   manufacturing parameters
-   simulation parameters

Those belong to downstream stages.

------------------------------------------------------------------------

# Relationship to Product Architecture

Mechanical Architecture answers:

> What makes the product work?

Product Architecture answers:

> How do those mechanisms become one coherent product?

Mechanical Architecture therefore provides engineering intent, while
Product Architecture organizes that intent into a usable product.

------------------------------------------------------------------------

# Downstream Contract

The Product Architecture Planner may assume that every candidate
includes:

-   complete functional decomposition,
-   identified mechanisms,
-   identified interfaces,
-   motion relationships,
-   engineering rationale,
-   known risks,
-   unresolved questions.

Product Architecture should never reinterpret engineering intent.

------------------------------------------------------------------------

# Validation

A valid Mechanical Architecture should:

-   satisfy all functional requirements,
-   remain independent of geometry,
-   remain independent of CAD,
-   remain independent of dimensions,
-   be internally consistent,
-   be traceable to RequirementSpec,
-   expose engineering tradeoffs.

------------------------------------------------------------------------

# Revision Philosophy

Mechanical Architecture is expensive to revise.

Preferred revision order is:

Parameter → Geometry → Geometry Strategy → Product Architecture →
Mechanical Architecture

Mechanical Architecture should only be revisited when evidence shows the
selected concept is fundamentally incapable of satisfying the
requirements.

Existing candidates should be reconsidered before generating entirely
new concepts.

------------------------------------------------------------------------

# Example A --- Latching Storage Box

Possible candidates:

-   Cantilever snap latch + revolute hinge
-   Rotary latch + hinge
-   Sliding latch + hinge

Each differs by locking principle.

------------------------------------------------------------------------

# Example B --- Hand-Cranked Lift Box

Possible candidates:

-   Rack-and-pinion lift
-   Lead screw lift
-   Cable drum lift

Each differs by motion conversion and force transmission.

------------------------------------------------------------------------

# Known Open Questions

Implementation should determine:

-   What is the best candidate ranking strategy?
-   Should candidate ranking be deterministic, LLM-based, or hybrid?
-   How should uncertainty be represented?
-   When should alternative candidates be discarded?
-   When should entirely new candidates be generated?

These questions remain intentionally open until implementation evidence
exists.

------------------------------------------------------------------------

# Success Criteria

This stage is complete when:

-   Mechanically distinct candidates are produced only when justified.
-   Candidates are independent of geometry and CAD.
-   Candidate diversity is based on engineering principles.
-   Downstream Product Architecture requires no reinterpretation of
    engineering intent.
-   Both benchmark products (Latching Storage Box and Hand-Cranked Lift
    Box) can be represented without architecture changes.
