# STAGE_03_PRODUCT_ARCHITECTURE.md

# Stage 03 --- Product Architecture Planner

> This document defines how a selected Mechanical Architecture becomes a
> coherent, usable, manufacturable product.
>
> Product Architecture is the bridge between engineering principles and
> geometric realization.

------------------------------------------------------------------------

# Purpose

The Product Architecture Planner organizes a mechanical system into a
complete product.

It determines **how mechanisms are packaged, accessed, assembled,
protected, and used** before any detailed geometry is created.

This stage does **not** design CAD geometry.

It designs the **product-level engineering organization**.

------------------------------------------------------------------------

# Engineering Question

> **How should this mechanical system become a manufacturable, usable,
> maintainable product?**

This stage does **not** ask:

-   How large should a gear be?
-   What wall thickness should be used?
-   What CAD features should be created?

Those belong to Geometry Planning.

------------------------------------------------------------------------

# Inputs

Input:

-   RequirementSpec
-   Selected MechanicalArchitectureCandidate

------------------------------------------------------------------------

# Outputs

Output:

`ProductArchitecture`

The exact schema is implementation-defined.

Typical information includes:

-   product regions
-   housing strategy
-   packaging strategy
-   user interaction
-   product layout
-   assembly strategy
-   service strategy
-   protection strategy
-   high-level manufacturing intent
-   major load paths
-   product proportions
-   design rationale
-   known risks

------------------------------------------------------------------------

# Responsibilities

The Product Architecture Planner is responsible for defining:

## Product Organization

-   major product regions
-   product decomposition
-   mechanism placement
-   functional grouping

## User Interaction

-   handles
-   buttons
-   cranks
-   lids
-   access locations
-   ergonomic interaction regions

## Packaging

-   mechanism enclosure
-   internal organization
-   moving regions
-   protected regions
-   external interfaces

## Assembly Strategy

High-level assembly intent, including:

-   housing split
-   assembly direction
-   removable covers
-   service access
-   fastener philosophy
-   replaceable modules

## Manufacturing Intent (High Level)

This stage should consider manufacturability.

It should not create manufacturing geometry.

Instead it should determine:

-   intended manufacturing process (when specified)
-   compatible product organization
-   part partitioning
-   manufacturing-friendly architecture
-   assembly feasibility

Examples:

-   two-piece housing
-   removable gearbox module
-   rear assembly
-   support-free product organization (for FDM)
-   symmetric enclosure for easier manufacturing

## Safety

Examples:

-   isolate moving gears
-   prevent finger access
-   protect rotating shafts
-   stable support
-   protected latch

## Maintainability

Examples:

-   removable covers
-   replaceable transmission
-   accessible fasteners
-   inspection regions

------------------------------------------------------------------------

# Product Architecture Is NOT Industrial Design

Product Architecture is frequently misunderstood.

It is **not** styling.

It does not determine:

-   colors
-   textures
-   aesthetics
-   industrial design language

Instead it defines how engineering systems become usable products.

------------------------------------------------------------------------

# Manufacturing Boundary

Manufacturing must be considered.

Manufacturing geometry must not yet be generated.

Examples

Correct:

-   split housing into two shells
-   gearbox should be removable
-   rear assembly
-   FDM-compatible organization

Incorrect:

-   2.2 mm wall
-   0.3 mm clearance
-   draft angle
-   fillet radius
-   exact tolerances

Those belong to later engineering stages.

------------------------------------------------------------------------

# Relationship to Mechanical Architecture

Mechanical Architecture answers:

> What makes the product work?

Product Architecture answers:

> How do those mechanisms become a complete product?

Product Architecture must never redesign the selected mechanism.

It organizes the mechanism.

------------------------------------------------------------------------

# Relationship to Concept Visualization

Concept Visualization is derived from Product Architecture.

Images are visual interpretations of Product Architecture.

The image generator must not invent unsupported mechanisms or product
organization.

------------------------------------------------------------------------

# Relationship to Geometry Planning

Geometry Planning assumes Product Architecture is complete.

Geometry Planning is responsible for:

-   detailed geometry
-   engineering dimensions
-   mechanical implementation
-   knowledge-grounded realization
-   CAD-ready feature definition

Product Architecture must not attempt to solve those problems.

------------------------------------------------------------------------

# Downstream Contract

The Geometry Planner may assume that Product Architecture already
defines:

-   product regions
-   mechanism packaging
-   user interaction
-   assembly philosophy
-   manufacturing intent
-   protection strategy
-   service strategy
-   major spatial organization

Geometry Planning should not reinterpret product organization.

------------------------------------------------------------------------

# Validation

A valid Product Architecture should:

-   satisfy RequirementSpec
-   preserve Mechanical Architecture
-   define a coherent product
-   support plausible assembly
-   consider manufacturability
-   consider maintenance
-   consider safety
-   remain independent of detailed geometry

------------------------------------------------------------------------

# Example A --- Latching Storage Box

Mechanical Architecture

-   revolute hinge
-   snap latch

Product Architecture

-   rear hinge placement
-   front thumb access
-   enclosed storage cavity
-   protected latch
-   removable lid-body assembly
-   stable base
-   two-piece printable housing

------------------------------------------------------------------------

# Example B --- Hand-Cranked Lift Box

Mechanical Architecture

-   rack-and-pinion lift

Product Architecture

-   external crank
-   enclosed transmission compartment
-   central lifting platform
-   removable rear service cover
-   protected gears
-   wide stable base
-   FDM-friendly enclosure split

------------------------------------------------------------------------

# Known Open Questions

Implementation should determine:

-   How much manufacturing intent belongs here?
-   How should Product Architecture be represented?
-   Should packaging be graph-based?
-   Should assembly sequencing become its own representation?
-   Should serviceability become independently evaluable?

These questions should be resolved using implementation evidence.

------------------------------------------------------------------------

# Success Criteria

This stage is complete when:

-   Every mechanism has a product location.
-   User interaction is defined.
-   Packaging is coherent.
-   Assembly intent exists.
-   High-level manufacturing intent exists.
-   Safety and serviceability are considered.
-   Geometry Planning can proceed without reorganizing the product.
