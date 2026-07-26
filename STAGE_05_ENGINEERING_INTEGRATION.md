
# STAGE_05_ENGINEERING_INTEGRATION.md

# Stage 05 — Engineering Integration

> **Living Specification**
>
> This document defines the pre-CAD engineering design process of ASSY-Next.
>
> Stage 05 is not a geometry-generation step and not a CAD-authoring step.
>
> It is the stage in which Mechanical Architecture, Product Architecture, and Concept Visualization are resolved into a complete, spatially coherent, mechanically plausible, manufacturable, assemblable, and CAD-ready engineering definition.
>
> This document incorporates the current evidence from the latching storage box, the hand-cranked lift box, and the Geneva indexing-product trace.
>
> The internal model described here is a working architectural hypothesis. Exact schemas and execution policies should evolve through implementation evidence.

---

# 1. Purpose

Stage 05 completes the engineering work that must occur before deterministic CAD generation.

Its purpose is to answer:

> **Can the selected mechanical and product architecture be resolved into a complete engineering definition that can be compiled into CAD without requiring the CAD Builder to invent engineering decisions?**

This stage must resolve:

- component identity,
- spatial organization,
- support,
- motion,
- interfaces,
- assembly,
- manufacturing,
- tolerances,
- critical characteristics,
- and unresolved engineering conflicts.

The final output must contain enough engineering meaning that downstream software can:

- solve parameters,
- build CAD,
- prepare validation,
- identify affected regions during revision,
- and preserve traceability.

---

# 2. Engineering Question

> **How can the current product concept become a complete, physically coherent, and CAD-ready engineering design?**

This is distinct from earlier stages:

```text
Stage 02
What mechanical principles make the product work?

Stage 03
How do those mechanisms become a usable and manufacturable product?

Stage 04
How might that product architecture appear spatially?

Stage 05
How must the design actually be engineered so that it can exist, move,
assemble, manufacture, and proceed to deterministic CAD generation?
```

---

# 3. Inputs

Stage 05 consumes:

- `RequirementSpec`
- selected `MechanicalArchitectureCandidate`
- `ProductArchitecture`
- `ConceptVisualizationResult`
- applicable project policies
- applicable engineering knowledge
- applicable manufacturing intent

The concept image is non-authoritative.

The authoritative input order is:

```text
RequirementSpec
    >
Mechanical Architecture
    >
Product Architecture
    >
Concept Visualization
```

If a concept image conflicts with structured engineering data, the image must be corrected, reinterpreted, or ignored.

---

# 4. Output

Stage 05 produces:

```text
CADReadyEngineeringDefinition
```

This is not CAD.

It is the complete engineering definition required for:

```text
Parametric Solver
        ↓
Solved Engineering Definition
        ↓
CAD Builder
```

The exact schema remains implementation-defined.

At minimum, the final definition should preserve:

- stable engineering identities,
- component inventory,
- spatial frames,
- spatial layout,
- motion definitions,
- support definitions,
- interfaces,
- assembly intent,
- manufacturing intent,
- symbolic parameters,
- engineering constraints,
- objectives,
- tolerance intent,
- critical characteristics,
- simulation-relevant semantics,
- provenance,
- unresolved non-blocking risks,
- and readiness evidence.

---

# 5. Stage 05 Is a Design Process, Not Merely a Representation

Stage 05 should not be modeled as:

```text
Input
    ↓
One LLM call
    ↓
Final Geometry Plan
```

Mechanical design is iterative and circular.

Examples:

```text
A shaft location affects its load.
The load affects shaft size.
The shaft size affects packaging.
Packaging changes the shaft location.
```

```text
A housing split affects assembly.
Assembly affects bearing placement.
Bearing placement affects support spacing.
Support spacing affects shaft deflection.
```

Therefore Stage 05 must support an engineering loop:

```text
Current Engineering State
        ↓
Problem Discovery
        ↓
Candidate Resolutions
        ↓
Selected Resolution
        ↓
Updated Engineering State
        ↓
Invalidated Checks
        ↓
Revalidation
        ↓
Repeat
```

The final engineering representation must emerge from the design process.

It must not be designed independently from the engineering decisions and problems it must preserve.

---

# 6. Primary Working-State Model

The Stage 05 working state contains four primary object families:

```text
EngineeringWorkingState
├── Commitment Store
├── Problem Agenda
├── Resolution Graph
└── Check Registry
```

No fifth primitive was required during the Geneva falsification trace.

However, each primitive requires explicit semantics described below.

---

# 7. Commitment Store

## 7.1 Purpose

The Commitment Store contains the current engineering state of the design.

A commitment represents something the design currently asserts, assumes, proposes, or has verified.

It may exist before exact numeric values are known.

Examples:

- the platform uses two side guides,
- the input shaft is supported on both sides of the pinion,
- the housing has a removable side plate,
- the gear center distance is symbolic,
- the locking interface owns dwell accuracy,
- the design objective is to minimize input torque,
- the material is provisionally PLA,
- the shaft diameter remains unresolved.

## 7.2 Commitment Kinds

At minimum:

```text
entity
relation
parameter
value
constraint
objective
interface
motion
support
assembly
manufacturing
tolerance
critical_characteristic
assumption
```

`objective` is mandatory.

Tradeoffs cannot always be represented as pass/fail constraints.

Examples:

- minimize dwell angular error,
- minimize release force while preserving retention,
- minimize input torque while preserving travel,
- minimize packaging volume without harming serviceability.

## 7.3 Commitment Status

At minimum:

```text
assumed
provisional
selected
verified
superseded
rejected
```

The state must distinguish:

- a temporary assumption,
- an unverified proposal,
- a selected working choice,
- a verified commitment,
- and a retired commitment.

## 7.4 Symbolic Commitments

The store must support structural commitments without final values.

Example:

```text
support scheme = two bearings
bearing spacing = symbolic
shaft diameter = unresolved parameter
```

Symbolic-before-numeric is required because loads and geometry are co-dependent.

## 7.5 Provenance

Every commitment must reference:

- which requirement it serves,
- which problem it resolves,
- which resolution created it,
- which method or rule justified it,
- which assumptions it depends on,
- and which checks currently support it.

## 7.6 Supersession

Commitments must never be deleted.

A new resolution may supersede an earlier commitment.

Example:

```text
C-38:
monolithic four-wall shell
status = superseded

superseded_by:
R-42 removable side plate
```

Supersession must:

- preserve history,
- prevent contradictory active commitments,
- reopen problems previously closed by retired commitments when necessary,
- and invalidate dependent checks.

This is blocking functionality.

Real design routinely retracts earlier choices.

---

# 8. Problem Agenda

## 8.1 Purpose

The Problem Agenda contains everything that prevents the current engineering state from being complete, coherent, verified, or CAD-ready.

Problems are the primary driver of Stage 05.

A design-in-progress cannot be represented by decisions alone.

Examples:

- pinion axial retention is missing,
- platform travel collides with the housing,
- crank clearance is unverified,
- gear ratio is inconsistent,
- shaft support is insufficient,
- assembly order is blocked,
- manufacturing process is incompatible,
- tolerance chain exceeds the requirement,
- no torque-transfer method exists between shaft and turntable.

## 8.2 Problem Types

At minimum:

```text
undetermined
violated
unverified
conflicting
unknown
incomplete
invalidated
```

## 8.3 Problem Origins

Every problem must record how it was discovered.

At minimum:

```text
requirement-derived
spawned-by-commitment
detected-by-check
manufacturing-derived
assembly-derived
simulation-derived
human-raised
external-evidence-derived
```

This distinction matters because:

- some problems arise from requirements,
- some are implied when a new entity is introduced,
- some are detected by geometry or analysis,
- and some arrive from later physical validation.

## 8.4 Canonical Problem Identity

Duplicate problems must be merged.

A useful initial canonical form is:

```text
affected entities
+
phenomenon
+
evaluation domain
```

Example:

```text
(driver_disc, geneva_wheel)
+
interference
+
indexing_phase_0_to_120_deg
```

Evaluation domain is required.

The same entities may have different problems during:

- dwell,
- engagement,
- full rotation,
- assembly,
- service,
- or another operating state.

## 8.5 Blocking and Non-Blocking Problems

Problems should declare severity:

```text
blocking
high
medium
low
informational
```

Only blocking problems prevent CAD readiness.

However, non-blocking risks must be preserved and reported.

---

# 9. Resolution Graph

## 9.1 Purpose

The Resolution Graph records candidate and selected responses to engineering problems.

A problem may have multiple candidate resolutions.

Example:

```text
Problem:
platform tilts under load

Candidates:
- increase guide spacing
- add a second guide
- widen the guide profile
- relocate the transmission
```

## 9.2 Resolution Status

At minimum:

```text
proposed
selected
rejected
applied
verified
invalidated
superseded
```

## 9.3 Resolution Content

A resolution should identify:

- the problem it addresses,
- required inputs,
- reasoning method,
- proposed commitments,
- commitments to supersede,
- expected benefits,
- expected risks,
- affected engineering domains,
- checks to invalidate,
- and downstream problems likely to be spawned.

## 9.4 Selection

Resolution selection may use:

- deterministic rejection,
- engineering rules,
- analytical comparison,
- LLM tradeoff reasoning,
- or human review.

The selected resolution is a hypothesis until checked.

## 9.5 Revision

Later evidence may invalidate a resolution.

In that case:

```text
new problem
    ↓
find relevant prior resolution
    ↓
reopen or replace
    ↓
supersede affected commitments
    ↓
recheck dependents
```

Revision routing is therefore derived from the same dependency graph used during Stage 05.

A separate hidden revision mechanism should not be necessary.

---

# 10. Check Registry

## 10.1 Purpose

The Check Registry records every engineering analysis that evaluated the current commitment state.

Checks may detect problems, verify commitments, or invalidate candidate resolutions.

## 10.2 Check Kinds

At minimum:

```text
deterministic
analytical
rule
judgment
external-evidence
```

Examples:

### Deterministic

- envelope collision,
- center distance,
- DOF count,
- assembly insertion path,
- exact ratio relationship.

### Analytical

- shaft deflection,
- beam stress,
- torque balance,
- tolerance stack,
- self-lock condition.

### Rule

- minimum wall thickness,
- process-material compatibility,
- pinch-access rule,
- support-count requirement.

### Judgment

- believable proportions,
- ergonomic plausibility,
- product coherence,
- likely maintainability.

### External Evidence

- MuJoCo result,
- FEA result,
- physical prototype measurement,
- external test report.

Only deterministic, analytical, and rule checks may autonomously gate CAD readiness.

Judgment checks may raise concerns but should not silently block without explicit policy.

## 10.3 Check Validity

Every check must record:

- commitment-store version,
- input commitments,
- evaluation domain,
- validity scope,
- result,
- produced problems,
- and staleness status.

## 10.4 Evaluation Domain

A check without an evaluation domain is incomplete.

Examples:

```text
single pose
full crank revolution
full platform stroke
engagement phase
dwell phase
all assembly states
all tolerance extremes
all required operating scenarios
```

The Geneva trace demonstrated that a per-pose check may pass while a full-cycle sweep fails.

## 10.5 Staleness and Invalidation

When commitments change, dependent checks become stale.

A stale check must not be treated as evidence.

The system should automatically create an `unverified` problem when required checks become stale.

---

# 11. Problem Discovery

Problems are discovered in two fundamentally different ways.

## 11.1 Commitment-Spawning Rules

A new commitment may imply required engineering work.

Examples:

```text
rotating shaft
→ support problem
→ axial retention problem
→ lubrication or wear problem

gear pair
→ center distance problem
→ ratio problem
→ backlash problem
→ shaft support problem

moving platform
→ guidance problem
→ travel envelope problem
→ jamming problem
→ stop problem
```

These rules represent engineering knowledge.

They must remain explicit and inspectable.

They must not be hidden inside prompts.

## 11.2 Check-Detected Problems

Deterministic or analytical checks detect violations.

Examples:

- motion sweep collision,
- excessive deflection,
- impossible assembly path,
- insufficient clearance,
- invalid gear geometry,
- tolerance failure,
- unsafe access.

The distinction creates a structural LLM boundary:

```text
Checks detect measurable problems.
Reasoning proposes candidate resolutions.
```

This boundary is preferred over asking LLMs to simulate deterministic engineering.

## 11.3 Knowledge-Completeness Limitation

Absence discovery depends on the completeness of the spawning knowledge.

No system can prove that every necessary engineering concern has been generated.

This limitation must be stated honestly.

The architecture should mitigate it with mandatory closure checks, not pretend the agenda is self-completing.

---

# 12. Specialist Analysis Passes

Stage 05 may use narrow specialist reasoning or analysis passes.

These are logical roles, not necessarily autonomous long-running agents.

Recommended roles:

```text
Kinematics and Motion
Spatial Integration and Packaging
Support and Load Path
Interface and Fit
Assembly and Access
Manufacturing
Tolerance and Variation
Safety and Human Interaction
```

Specialists must not directly mutate the authoritative state.

They produce:

- confirmed conditions,
- detected problems,
- candidate resolutions,
- required commitments,
- conflicts,
- and checks to run.

An Integration Planner accepts or rejects proposals and commits the next state version.

---

# 13. Shared Spatial Engineering Knowledge

Specialist passes must share a structured spatial model, not natural-language descriptions.

The working state should eventually support:

- coordinate frames,
- product envelope,
- component envelopes,
- functional volumes,
- motion envelopes,
- keep-out volumes,
- reserved volumes,
- interfaces,
- support locations,
- load paths,
- assembly operations,
- tool-access volumes,
- service-access volumes,
- tolerance zones,
- and symbolic dimensions.

The exact internal representation remains implementation-defined.

The following information must be computationally interpretable.

## 13.1 Static Space

Where each component exists in the assembled state.

## 13.2 Motion Space

Where moving components travel.

## 13.3 Assembly Space

Where components must move during installation.

## 13.4 Tool and Service Space

Where tools, hands, and removable parts require access.

## 13.5 Tolerance-Aware Space

Whether clearance remains after accounting for:

- manufacturing tolerance,
- assembly misalignment,
- deformation allowance,
- thermal variation where relevant,
- and required reserve.

## 13.6 Reserved Space

Required empty space for:

- user access,
- spring deflection,
- fastener heads,
- wiring,
- lubrication,
- debris protection,
- maintenance,
- cooling,
- or other non-solid needs.

---

# 14. Engineering Decision Domains

Stage 05 should resolve the following domains when applicable.

These are not a fixed universal sequence.

They are problem families that may be activated adaptively.

## 14.1 Kinematic Synthesis

- joint axes,
- travel,
- ratio,
- DOF,
- datum frames,
- link relationships,
- motion phase,
- dwell or indexing behavior.

## 14.2 Loads and Duty

- payload,
- input force or torque,
- reaction paths,
- duty cycles,
- worst-case operating scenarios,
- dynamic or quasi-static assumptions.

## 14.3 Margin Policy

- safety factor,
- allowable stress,
- deflection limit,
- wear life,
- failure consequence.

## 14.4 Material and Process Binding

- material per part,
- process per part,
- compatibility,
- directional properties,
- environmental suitability.

## 14.5 Machine Element Engineering

- gear relationships,
- shafts,
- bearings,
- guides,
- screws,
- springs,
- latches,
- joints,
- retention,
- and other machine elements.

Exact formulas should be handled by explicit engineering knowledge and deterministic functions where possible.

## 14.6 Support and Constraint Scheme

- support count,
- support spacing,
- axial retention,
- anti-rotation,
- exact or over-constrained guidance,
- ground path.

## 14.7 Interface and Fit Design

- contact,
- fits,
- clearances,
- backlash,
- fastening,
- mating,
- retention,
- sealing where relevant.

## 14.8 Motion Envelopes

- full-domain swept volume,
- interference,
- travel limits,
- moving/static boundaries,
- phase-dependent relationships.

## 14.9 Structural Load Path

- force application,
- transfer through components,
- support reactions,
- structural members,
- wall, rib, boss, or bracket needs.

## 14.10 Part Decomposition

- part inventory,
- housing split,
- modules,
- service panels,
- split surfaces,
- feature ownership.

## 14.11 Assembly Sequence

- insertion order,
- insertion direction,
- intermediate states,
- tool access,
- fastening sequence,
- service removal.

## 14.12 Manufacturing Resolution

- process legality,
- build orientation,
- overhang,
- draft,
- tool reach,
- minimum feature,
- print anisotropy,
- machining access.

## 14.13 Tolerance and Variation

- critical chains,
- worst-case stack,
- RSS stack,
- process capability,
- functional reserve.

## 14.14 Critical Characteristics

- what must be measured,
- between which entities,
- under what operating condition,
- and against which requirement.

---

# 15. Engineering Knowledge Grounding

Stage 05 must not rely only on LLM memory.

Engineering knowledge should be explicit, inspectable, testable, and traceable.

Possible implementations include:

- declarative engineering rules,
- analytical formulas,
- standards-derived constraints,
- machine-element libraries,
- process rules,
- material-property tables,
- deterministic sizing functions,
- and validation checks.

The architecture does not yet prescribe one implementation.

## 15.1 Gear Example

For gears, knowledge may include:

- gear ratio,
- module or diametral pitch,
- tooth count,
- pressure angle,
- center distance,
- undercut risk,
- backlash,
- face width,
- shaft support,
- bearing placement,
- housing clearance,
- contact direction,
- load path,
- and manufacturability.

The concept image must not decide these.

The LLM may choose or propose a gear-based strategy.

Deterministic engineering should evaluate formulas and constraints.

## 15.2 Knowledge Ownership

The exact location of engineering knowledge remains open.

It may reside in:

- rule libraries,
- solver modules,
- machine-element definitions,
- or another explicit data-rich representation.

It must not become:

- hidden prompt knowledge,
- cross-project uncontrolled memory,
- or benchmark-specific branching.

---

# 16. Pre-CAD Deterministic Checks

Complete CAD is not required for all engineering checks.

A coarse computational spatial model may support:

- bounding-volume overlap,
- motion-envelope collision,
- ratio consistency,
- center distance,
- assembly direction,
- tool access,
- support spacing,
- approximate torque,
- basic process feasibility,
- and clearance reserve.

Recommended precision levels:

```text
Level 0
Topology and interfaces

Level 1
Frames, axes, envelopes, swept volumes, keep-outs

Level 2
Parametric engineering geometry
```

Stage 05 should reject obvious failures before detailed CAD.

Post-CAD checks remain necessary for exact interference, topology, wall thickness, contact geometry, and precise manufacturing validation.

---

# 17. CAD-Readiness Closure

Agenda exhaustion is necessary but not sufficient.

The Geneva trace demonstrated that an empty agenda may still leave essential engineering information undefined.

Therefore Stage 05 requires a mandatory total closure pass.

The stage may exit only when all conditions are satisfied:

```text
No unresolved blocking problems
AND
all mandatory readiness checks have executed
AND
all mandatory checks are valid and passing
AND
no required commitment remains undetermined
AND
the parameter/constraint system is structurally solvable
```

## 17.1 Minimum Readiness Coverage

At minimum:

```text
Definition closure
Kinematic consistency
Full-domain motion interference
Support and load-path closure
Assembly feasibility
Tolerance closure
Manufacturing process legality
```

When applicable:

```text
Safety and user access
Serviceability
Environmental compatibility
Critical-characteristic mapping
```

## 17.2 Definition Closure

Every required entity must have:

- identity,
- role,
- ownership,
- interfaces,
- support,
- motion or fixed state,
- material/process intent,
- assembly role,
- and required symbolic definitions.

Every moving component must have:

- DOF,
- axis or path,
- range,
- support,
- retention,
- and relevant clearance.

Every interface must have:

- participants,
- type,
- fit or relation,
- and assembly meaning.

---

# 18. Convergence Policy

Stage 05 is not guaranteed to converge.

Resolutions may spawn new problems.

A resolution may invalidate earlier work.

The architecture should initially use explicit budgets rather than claim mathematical convergence.

Possible limits:

- maximum integration iterations,
- maximum supersession depth,
- maximum repeated canonical problem signature,
- maximum unresolved blocking problems,
- maximum cost or token budget.

If exceeded, return a structured blocked result.

Possible reasons:

```text
cyclic resolution
insufficient engineering knowledge
conflicting requirements
no feasible spatial arrangement
manufacturing incompatibility
concept architecture unsuitable
budget exhausted
```

The result should recommend the earliest restart stage:

```text
Product Architecture
Mechanical Architecture
Requirement Clarification
```

The system must never silently force closure.

---

# 19. Token Efficiency

Stage 05 is reasoning-intensive.

Token efficiency must be achieved through scoped context, not by collapsing engineering responsibilities.

Rules:

- specialist passes receive only relevant state slices,
- state is referenced by stable IDs,
- raw histories are not passed,
- only active problems and affected commitments are included,
- deterministic checks replace LLM reasoning where possible,
- candidate resolutions are concise and structured,
- local patches are preferred,
- unchanged engineering state is not regenerated,
- concept images are used as supporting spatial compression, not as engineering truth.

Efficiency is a constraint.

It must not reduce engineering correctness or readiness coverage.

---

# 20. Relationship to CAD

The CAD Builder must be a deterministic compiler.

It may:

- realize declared construction intent,
- instantiate solved parameters,
- create parts,
- create assemblies,
- export artifacts,
- and report structured failures.

It must not:

- invent supports,
- select materials,
- repair missing interfaces,
- redesign assembly order,
- choose mechanisms,
- resolve packaging conflicts,
- or infer critical dimensions.

If CAD generation requires an engineering decision that is not present in the Stage 05 output, Stage 05 is incomplete.

---

# 21. Semantic Identity and CAD Topology

Upstream engineering objects must never depend on kernel face or edge IDs.

Correct:

```text
bore carrying input shaft
locking surface of Geneva wheel
mounting region for guide rail
```

Incorrect:

```text
face_17
edge_4
```

CAD topology is downstream and unstable.

The CAD Builder may create a semantic-to-topological mapping in the CAD artifact output.

This mapping must never become the authority for upstream engineering identity.

---

# 22. Failure Handling and Revision

Stage 05 failures should be explicit.

Examples:

```text
no feasible packaging
unsatisfied motion envelope
unsupported rotating body
blocked assembly path
manufacturing incompatibility
tolerance closure failure
structural margin failure
unresolved critical parameter
```

Failures should produce:

- affected problems,
- supporting checks,
- failed resolutions,
- preserved commitments,
- superseded commitments,
- recommended restart stage,
- and minimal revision scope.

Stage 05 should attempt local engineering resolution before escalating.

---

# 23. Evidence Basis

The current model is supported by three contrasting design classes.

## Latching Storage Box

Stresses:

- compliant retention,
- release-force tradeoff,
- hinge motion,
- user access,
- housing integration,
- FDM constraints.

## Hand-Cranked Lift Box

Stresses:

- force transmission,
- gear or screw alternatives,
- back-drive,
- shaft support,
- guidance,
- packaging,
- stable housing.

## Geneva Indexing Product

Stresses:

- phase-dependent geometry,
- dwell and indexing,
- curved engagement,
- shaft support,
- supersession,
- assembly closure,
- tolerance chains,
- full-cycle motion checks.

The Geneva trace supported the four-object model with required modifications.

The most important findings were:

- supersession is mandatory,
- agenda exhaustion is insufficient,
- objectives must be commitments,
- checks require kinds and evaluation domains,
- duplicate problems require canonical identity,
- and convergence requires an explicit policy.

---

# 24. Known Open Questions

These should remain open until implementation evidence exists.

- What exact schema should represent the Engineering Working State?
- Which specialist passes require separate LLM calls?
- Which passes should be deterministic modules?
- How should engineering knowledge be organized?
- How should problem keys be canonicalized across complex mechanisms?
- What is the minimum CAD-readiness coverage for different product classes?
- How should judgment checks affect gating?
- How should alternative resolutions be ranked?
- How much spatial precision is needed before CAD?
- When should Stage 05 return to Product Architecture versus Mechanical Architecture?

---

# 25. Success Criteria

Stage 05 is successful when:

- the design has a coherent spatial engineering state,
- all required machine elements have support and interfaces,
- full-domain motion is represented,
- required empty spaces are preserved,
- assembly is feasible,
- manufacturing intent is resolved enough for CAD,
- tolerances and critical characteristics are defined,
- no blocking problem remains,
- mandatory readiness checks are valid and passing,
- no required commitment is undetermined,
- the solver can resolve the declared parameter system,
- the CAD Builder can build without inventing engineering decisions,
- and all important commitments remain traceable to requirements, problems, resolutions, methods, and checks.

---

# 26. Final Principle

Stage 05 is where ASSY-Next stops describing a product and finishes engineering it.

```text
Mechanical Architecture
    defines how it works.

Product Architecture
    defines how it becomes a product.

Concept Visualization
    provides a spatial hypothesis.

Engineering Integration
    resolves the design into CAD-ready engineering truth.

Parametric Solver and CAD Builder
    execute that truth deterministically.
```

The goal is not to imitate the concept image.

The goal is not to produce a plausible-looking CAD model.

The goal is to create a complete, explicit, testable engineering definition that can survive deterministic construction, validation, and revision.
