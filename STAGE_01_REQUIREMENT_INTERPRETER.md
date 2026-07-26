# STAGE_01_REQUIREMENT_INTERPRETER.md

# Stage 01 --- Requirement Interpreter

> This document defines the responsibilities, inputs, outputs, and
> engineering boundaries of the Requirement Interpreter.
>
> The purpose of this stage is to convert natural-language design
> requests into structured engineering intent without making any
> engineering design decisions.

------------------------------------------------------------------------

# Purpose

The Requirement Interpreter transforms natural-language product
requirements into a structured engineering specification.

It extracts **what the product must accomplish**, not **how it should be
designed**.

This stage establishes the engineering contract for every downstream
stage.

------------------------------------------------------------------------

# Engineering Question

> **What must this product do?**

Not:

-   How should it work?
-   What mechanisms should be used?
-   What should it look like?

Only:

> What engineering requirements must eventually be satisfied?

------------------------------------------------------------------------

# Inputs

**Input**

-   Natural-language design request
-   Product specification
-   Requirement document
-   User prompt

------------------------------------------------------------------------

# Outputs

**Output**

`RequirementSpec`

The exact schema is implementation-defined, but it should capture:

-   Functional requirements
-   Performance requirements
-   Operating scenarios
-   Manufacturing constraints
-   Material constraints (when specified)
-   Environmental constraints
-   Usability requirements
-   Safety requirements
-   Assembly requirements
-   Assumptions
-   Unresolved ambiguities
-   Requirement priorities

------------------------------------------------------------------------

# Responsibilities

The Requirement Interpreter is responsible for:

-   Identifying required product functions
-   Identifying required inputs and outputs
-   Extracting quantitative engineering targets
-   Extracting qualitative engineering goals
-   Extracting explicit engineering constraints
-   Recording implicit assumptions when appropriate
-   Recording unresolved ambiguities
-   Organizing all information into a structured engineering
    specification

The interpreter should preserve information rather than prematurely
resolve uncertainty.

------------------------------------------------------------------------

# Non-Responsibilities

The Requirement Interpreter must **not**:

-   Choose mechanisms
-   Choose machine elements
-   Generate mechanical architectures
-   Generate product architectures
-   Generate concept images
-   Generate geometry
-   Generate CAD
-   Generate dimensions
-   Estimate forces
-   Estimate torques
-   Perform engineering calculations
-   Evaluate manufacturability
-   Optimize parameters

Those responsibilities belong to downstream stages.

------------------------------------------------------------------------

# Required Reasoning

The interpreter should reason about:

-   Engineering intent
-   Product functionality
-   User goals
-   Measurable requirements
-   Operating context
-   Constraints
-   Ambiguity

It should **not** reason about implementation.

------------------------------------------------------------------------

# Validation

The resulting `RequirementSpec` should be:

-   Internally consistent
-   Traceable to the original request
-   Structured
-   Deterministic
-   Machine-readable
-   Independent of any specific mechanism
-   Independent of geometry
-   Independent of CAD representation

Every downstream engineering decision should be traceable back to one or
more requirements.

------------------------------------------------------------------------

# Downstream Contract

The Requirement Interpreter guarantees that downstream stages receive:

-   A complete engineering specification
-   No mechanism assumptions
-   No product-layout assumptions
-   No geometry assumptions
-   No CAD assumptions

Downstream stages should never need to re-interpret the original
natural-language request.

------------------------------------------------------------------------

# Design Rule

The Requirement Interpreter must preserve engineering intent.

It must never improve, simplify, reinterpret, or optimize the user's
request merely to make downstream design easier.

Its responsibility is faithful engineering interpretation---not
engineering design.

------------------------------------------------------------------------

# Known Open Questions

These questions remain intentionally open until implementation evidence
exists:

-   How should ambiguity be represented?
-   Should confidence be represented?
-   Where should clarification loops live?
-   How should conflicting requirements be represented?
-   What is the minimum RequirementSpec that still generalizes to
    complex products?

These questions should be answered through implementation evidence
rather than speculation.

------------------------------------------------------------------------

# Success Criteria

This stage is complete when:

-   The produced RequirementSpec correctly captures engineering intent.
-   The representation remains independent of mechanisms.
-   The representation remains independent of product architecture.
-   Multiple product categories can be represented without architectural
    changes.
-   Downstream stages require no access to the original user prompt.
-   Implementation evidence demonstrates generalization beyond current
    benchmark tasks.
