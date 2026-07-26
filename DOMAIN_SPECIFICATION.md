# DOMAIN_SPECIFICATION.md

> **ASSY-Next Domain Specification**
>
> This document defines the stable engineering vocabulary of the ASSY-Next framework.
>
> It describes the meaning, ownership, lifecycle, boundaries, and invariants of the major domain objects exchanged between system stages.
>
> This document intentionally does **not** define complete JSON schemas, Pydantic field layouts, CAD intermediate representations, simulator-specific structures, or benchmark-specific examples.
>
> Those implementation details belong in the corresponding stage specifications and may evolve as evidence is gathered.
>
> Read `PROJECT_CHARTER.md`, `SYSTEM_ARCHITECTURE.md`, and `ENGINEERING_RULES.md` before modifying this document.

---

# 1. Purpose

ASSY-Next transforms natural-language functional requirements into physically validated mechanical designs.

The framework does this through a sequence of reasoning, deterministic engineering, simulation, evaluation, and revision stages.

Each stage produces a structured engineering object for the next stage.

The objects defined in this document form the shared engineering language of the system.

They must remain:

- conceptually stable,
- implementation-independent,
- benchmark-independent,
- simulator-independent where practical,
- CAD-kernel-independent where practical,
- explicit,
- versioned,
- serializable,
- validated,
- traceable,
- and suitable for increasingly complex mechanical systems.

---

# 2. Scope

This document defines the following top-level domain objects:

1. `RequirementSpec`
2. `MechanicalConceptPlan`
3. `GeometryPlan`
4. `SolvedDesign`
5. `CADArtifactManifest`
6. `SimulationPlan`
7. `SimulationResult`
8. `MetricReport`
9. `EvaluationReport`
10. `RevisionDirective`
11. `IterationRecord`
12. `DesignSession`

It also defines the relationships and ownership boundaries between them.

This document does not define:

- exact field names,
- exact JSON layouts,
- exact Pydantic models,
- Geometry IR internals,
- CAD operation schemas,
- MuJoCo XML structure,
- benchmark-specific test definitions,
- LLM prompt wording,
- database implementation,
- or file-system layout.

Those details must be specified only when the relevant stage is implemented.

---

# 3. Domain Object Flow

The primary forward flow is:

```text
Natural-Language Requirement
        │
        ▼
RequirementSpec
        │
        ▼
MechanicalConceptPlan
        │
        ▼
GeometryPlan
        │
        ▼
SolvedDesign
        │
        ▼
CADArtifactManifest
        │
        ▼
SimulationPlan
        │
        ▼
SimulationResult
        │
        ▼
MetricReport
        │
        ▼
EvaluationReport
```

When requirements are not satisfied:

```text
EvaluationReport
        │
        ▼
RevisionDirective
        │
        ▼
Restart from the earliest affected stage
```

The current engineering state and iteration history are maintained through:

```text
DesignSession
        │
        └── IterationRecord
```

---

# 4. Global Domain Rules

## 4.1 Stable Meaning, Flexible Representation

The meaning of a domain object should remain stable even if its internal implementation changes.

For example:

- `GeometryPlan` must continue to represent geometric intent.
- It may later use a feature graph, region graph, interface graph, hybrid IR, or another representation.
- The conceptual responsibility must not change merely because the implementation evolves.

## 4.2 One Owner

Each top-level object has exactly one producing stage.

Other stages may consume or reference it, but must not redefine its meaning.

## 4.3 No Hidden Information Flow

A downstream stage must not depend on undocumented prompt context, conversation history, global variables, or implicit assumptions.

Required information must be present in:

- the current domain object,
- an explicitly referenced upstream object,
- an explicit project policy,
- or an explicit artifact.

## 4.4 Immutable Versions

A produced domain object should be treated as immutable.

A revision creates a new version.

Do not mutate historical objects in place.

This supports:

- reproducibility,
- comparison,
- rollback,
- provenance,
- debugging,
- and scientific analysis.

## 4.5 References Instead of Duplication

Objects should reference upstream entities by stable identifiers rather than repeatedly embedding complete copies.

Duplication should be used only when a compact, intentionally denormalized summary is required for execution or token-efficient LLM context.

The authoritative source must remain identifiable.

## 4.6 No Benchmark-Specific Core Fields

Core objects must not include fields that exist only for:

- a snap-fit box,
- a Geneva mechanism,
- a rack lift,
- a drawer,
- a clamp,
- or any other active benchmark.

Benchmark-specific meaning belongs in:

- object instances,
- benchmark configuration,
- stage fixtures,
- simulation protocols,
- evaluators,
- and acceptance criteria.

## 4.7 General Mechanical Complexity

Core objects must not assume:

- one part,
- one mechanism,
- one input,
- one output,
- one operating scenario,
- one simulation,
- one metric,
- one violation,
- one revision,
- or one manufacturing process.

They must support multi-part, multi-mechanism, multi-stage mechanical designs.

---

# 5. Common Metadata

Every persisted top-level domain object should eventually support common metadata such as:

- schema version,
- object identifier,
- design identifier,
- session identifier where relevant,
- creation time,
- producer stage,
- producer implementation version,
- parent object or parent revision references,
- provenance references,
- and validation status.

The exact metadata schema should be defined during implementation.

Do not force all metadata into every nested object unless it provides clear engineering or traceability value.

---

# 6. RequirementSpec

## Purpose

`RequirementSpec` represents the structured engineering meaning of the user's request.

It defines what the intended product must accomplish, under what conditions, and how success may eventually be verified.

## Produced By

`Requirement Interpreter`

## Primary Consumers

- `Mechanical Concept Planner`
- `Simulation Plan Builder`
- `Requirement Evaluation`
- `Revision Routing`
- `DesignSession`

## Lifecycle

Created once at the beginning of a design session.

A new version is created only when:

- the user clarifies a requirement,
- a blocking ambiguity is resolved,
- a requirement conflict is explicitly reconciled,
- or a justified revision requires requirement-level reconsideration.

## Must Represent

- product intent,
- required functions,
- intended inputs,
- intended outputs,
- operating scenarios,
- measurable performance requirements,
- qualitative requirements,
- manufacturing constraints,
- material constraints,
- environmental constraints,
- usability constraints,
- safety constraints,
- assembly or maintenance expectations where relevant,
- priorities,
- assumptions,
- unknowns,
- and high-level verification intent.

## Must Not Represent

- selected mechanisms,
- parts,
- joints,
- topology,
- detailed geometry,
- CAD features,
- solved dimensions,
- simulation results,
- or design revisions.

## Invariants

1. Explicit user requirements must remain distinguishable from inferred assumptions.
2. Unknowns must not be silently converted into precise invented requirements.
3. Requirements must be traceable to user statements, defaults, assumptions, or derived engineering interpretation.
4. Quantitative requirements must be suitable for deterministic evaluation where possible.
5. Qualitative requirements must remain explicit when they cannot yet be measured.
6. The object must support conflicting, dependent, and prioritized requirements.

## Key Boundary

`RequirementSpec` answers:

> What must be achieved?

It does not answer:

> How should it be achieved?

---

# 7. MechanicalConceptPlan

## Purpose

`MechanicalConceptPlan` represents the selected mechanical architecture intended to satisfy the requirements.

It explains how functions may be realized through parts, mechanisms, interfaces, motion relationships, packaging intent, and high-level product form intent.

## Produced By

`Mechanical Concept Planner`

## Primary Consumers

- `Geometry Planner`
- `Simulation Plan Builder`
- `Revision Routing`
- `DesignSession`

## Lifecycle

Created after `RequirementSpec`.

A new version is created when:

- the selected mechanism changes,
- major part decomposition changes,
- topology changes,
- a major interface changes,
- a mechanism cannot satisfy the required behavior,
- or a global product architecture change is justified.

## Must Represent

- major parts or functional bodies,
- functional decomposition,
- selected mechanical principles,
- mechanism roles,
- mechanism participants,
- motion relationships,
- input-output transformations,
- interfaces,
- degrees of freedom at the conceptual level,
- assembly concept,
- packaging intent,
- product-form intent,
- user interaction intent,
- major tradeoffs,
- and deferred geometry decisions.

## Must Not Represent

- executable CAD operations,
- sketches,
- exact face or edge references,
- finalized coordinates,
- solved dimensions,
- detailed contact geometry,
- simulation measurements,
- or revision patches.

## Invariants

1. Every selected mechanism must relate to at least one requirement or function.
2. Every major part must have an engineering role.
3. Interfaces must reference valid participants.
4. Motion relationships must identify intended inputs and outputs.
5. Product form intent must support mechanism integration rather than treating mechanisms as isolated attachments.
6. The plan must support multiple mechanisms and coupled functions.
7. The plan must not claim physical success before simulation.

## Key Boundary

`MechanicalConceptPlan` answers:

> What mechanical architecture should realize the required functions?

It does not answer:

> What exact geometry should be built?

---

# 8. GeometryPlan

## Purpose

`GeometryPlan` represents the parametric geometric intent required to realize the mechanical concept as a plausible, manufacturable, assemblable product.

It is the contract between reasoning and deterministic geometry execution.

## Produced By

`Geometry Planner`

## Primary Consumers

- `Parametric Solver`
- `CAD Builder`
- `Simulation Plan Builder`
- `Revision Routing`
- `DesignSession`

## Lifecycle

Created after `MechanicalConceptPlan`.

A new version is created when:

- feature structure changes,
- local geometry changes,
- product integration changes,
- assembly geometry changes,
- geometric references change,
- a CAD build failure requires redesign,
- or simulation evidence requires a geometric revision.

## Must Represent

At a conceptual level:

- product-level geometry intent,
- part-level geometry intent,
- geometry dependencies,
- symbolic parameters,
- geometric constraints,
- mechanism-integration geometry,
- assembly geometry,
- motion-clearance intent,
- user-interaction geometry,
- manufacturing-related geometric intent,
- simulation-relevant semantic references,
- and stable targets for local revision.

## Must Not Represent

- arbitrary executable Python,
- arbitrary CAD source code,
- simulator results,
- requirement evaluation,
- LLM conversation history,
- or final physical validation.

## Invariants

1. It must be possible to solve the declared parameters deterministically.
2. It must be possible to compile the plan into CAD or return a structured build failure.
3. Mechanical elements must be integrated into believable product geometry.
4. Assembly access, motion clearance, structural transition, and user interaction must be represented when relevant.
5. The internal representation must support local patches.
6. The representation must eventually support complex multi-part systems.
7. No benchmark-specific orchestration assumptions may be embedded in the object.

## Deliberately Deferred Decision

The exact internal Geometry IR is not fixed by this document.

Possible future representations include:

- feature graphs,
- body-region-interface graphs,
- operation graphs,
- hybrid parametric graphs,
- or another evidence-supported representation.

The Geometry IR must be specified separately immediately before implementing the Geometry Planner and CAD Builder.

## Key Boundary

`GeometryPlan` answers:

> What parametric geometric structure should be realized?

It does not answer:

> What exact numerical solution satisfies all constraints?

---

# 9. SolvedDesign

## Purpose

`SolvedDesign` represents a numerically resolved instance of a `GeometryPlan`.

It contains parameter values and deterministic constraint-solving results.

## Produced By

`Parametric Solver`

## Primary Consumers

- `CAD Builder`
- `Simulation Plan Builder`
- `Revision Routing`
- `DesignSession`

## Lifecycle

A new `SolvedDesign` is created whenever:

- parameter values change,
- solver objectives change,
- bounds change,
- geometry constraints change,
- or an upstream plan changes.

## Must Represent

- solved parameter values,
- units,
- satisfied constraints,
- violated constraints,
- solution status,
- solver diagnostics,
- objective values where relevant,
- feasible margins,
- and useful sensitivity information where available.

## Must Not Represent

- mechanism selection,
- topology redesign,
- undeclared geometry features,
- simulation results,
- or LLM-generated revision reasoning.

## Invariants

1. Every solved value must correspond to a declared parameter.
2. Units must remain explicit.
3. Constraint status must be reproducible.
4. Solver failure must be represented explicitly.
5. The solver must not silently change topology.
6. Parameter-only deterministic repair must remain within declared bounds and policies.

## Key Boundary

`SolvedDesign` answers:

> What numerical parameter values satisfy the current geometry plan?

It does not answer:

> Does the physical product work?

---

# 10. CADArtifactManifest

## Purpose

`CADArtifactManifest` records the deterministic CAD outputs generated from a `SolvedDesign`.

It provides stable references to engineering artifacts and mapping data.

## Produced By

`CAD Builder`

## Primary Consumers

- `Simulation Plan Builder`
- geometry validation,
- manufacturing checks,
- artifact export,
- `DesignSession`,
- debugging and provenance tools.

## Lifecycle

Created for every CAD build attempt.

A failed build should still produce a diagnostic manifest or equivalent structured build result.

## Must Represent

- build status,
- part artifacts,
- assembly artifacts,
- STEP references,
- mesh references,
- collision geometry references,
- visual geometry references,
- mass-property references where available,
- feature-reference mapping,
- assembly transforms,
- topology diagnostics,
- and build warnings or failures.

## Must Not Represent

- binary CAD data embedded directly in the object,
- hidden geometry repair,
- simulation conclusions,
- or user-facing success claims.

## Invariants

1. Artifacts must be referenced by stable paths or artifact identifiers.
2. The producing `SolvedDesign` must be traceable.
3. Part identity must remain stable.
4. Feature or semantic mappings required by simulation and revision must remain available.
5. CAD build failures must be explicit and structured.
6. The builder must not silently redesign the product.

## Key Boundary

`CADArtifactManifest` answers:

> What CAD and geometry artifacts were deterministically produced?

It does not answer:

> How should they be physically tested?

---

# 11. SimulationPlan

## Purpose

`SimulationPlan` defines how the current design should be physically tested.

It translates requirements, operating scenarios, mechanical semantics, and CAD artifacts into one or more deterministic simulation experiments.

## Produced By

`Simulation Plan Builder`

## Primary Consumers

- `MuJoCo Runner`
- future supported simulation runners,
- `DesignSession`,
- test reproducibility tools.

## Lifecycle

A new version is created when:

- a relevant requirement changes,
- a mechanical concept changes,
- simulation semantics change,
- an operating scenario changes,
- an observable changes,
- or the CAD assembly changes materially.

A parameter change may reuse the same logical simulation plan if the experiment definition remains valid.

## Must Represent

- test identity,
- relevant requirement references,
- initial conditions,
- actuation,
- constraints or joints used by the simulation,
- observed entities,
- requested metrics,
- material and contact assumptions,
- termination conditions,
- simulation validity conditions,
- and artifact references.

## Must Not Represent

- measured results,
- pass/fail conclusions,
- revision decisions,
- or arbitrary LLM predictions.

## Invariants

1. Every test must trace to at least one requirement, scenario, or engineering validation objective.
2. Observables must be computable from the simulator output.
3. Initial conditions and actuation must be reproducible.
4. Simulation assumptions must be explicit.
5. Invalid or insufficient simulations must be distinguishable from genuine design failures.
6. The representation should permit multiple tests per design.

## Key Boundary

`SimulationPlan` answers:

> How should the generated design be physically tested?

It does not answer:

> What happened during the test?

---

# 12. SimulationResult

## Purpose

`SimulationResult` represents the raw outcome of executing a `SimulationPlan`.

It records simulator evidence without converting that evidence into engineering pass/fail conclusions.

## Produced By

`MuJoCo Runner` or another deterministic simulation backend.

## Primary Consumers

- `Metric Extraction`
- simulation debugging,
- visualization,
- artifact persistence,
- `DesignSession`.

## Lifecycle

Created for every test execution.

Simulation retries create separate results or attempts.

## Must Represent

- execution status,
- simulator version,
- test reference,
- duration,
- trajectory artifact references,
- contact artifact references,
- event records,
- solver diagnostics,
- stability status,
- warnings,
- and failure or invalidity reasons.

## Must Not Represent

- requirement pass/fail,
- design revision,
- unsupported causal diagnosis,
- or LLM-generated interpretation.

## Invariants

1. Raw large arrays should remain artifact references rather than inline payloads.
2. Simulator instability must be distinguishable from product failure.
3. Results must be traceable to the exact simulation plan and CAD build.
4. Repeated runs under identical deterministic conditions should be reproducible within declared numerical tolerances.
5. No LLM should be required to parse raw simulator logs.

## Key Boundary

`SimulationResult` answers:

> What did the simulator produce?

It does not answer:

> What engineering metrics were measured?

---

# 13. MetricReport

## Purpose

`MetricReport` contains deterministic engineering measurements extracted from one or more simulation results or deterministic checks.

## Produced By

`Metric Extraction`

## Primary Consumers

- `Requirement Evaluation`
- revision context builder,
- engineering reports,
- `DesignSession`.

## Lifecycle

Created after a simulation or deterministic validation run.

A new report is produced when the underlying result or extraction method changes.

## Must Represent

- metric identity,
- name,
- value,
- unit,
- calculation method,
- source artifact,
- relevant entities,
- uncertainty or numerical tolerance where relevant,
- detected events,
- and metric validity.

## Must Not Represent

- requirement satisfaction,
- design revisions,
- mechanism choices,
- or speculative causes.

## Invariants

1. Every metric must be reproducibly computed.
2. Units must be explicit.
3. Calculation methods must be identifiable.
4. Invalid metrics must not be silently converted to values.
5. Metric names must remain stable enough for requirement mapping.
6. Multiple metrics and multiple tests must be supported.

## Key Boundary

`MetricReport` answers:

> What measurable physical quantities were observed?

It does not answer:

> Are those values acceptable?

---

# 14. EvaluationReport

## Purpose

`EvaluationReport` determines whether the measured design behavior satisfies the explicit requirements.

It is the authoritative deterministic comparison between engineering evidence and requirement targets.

## Produced By

`Requirement Evaluation`

## Primary Consumers

- deterministic revision routing,
- conditional LLM diagnosis,
- final engineering report,
- `DesignSession`,
- iteration comparison.

## Lifecycle

Created for every evaluated iteration.

A new version is produced when:

- requirements change,
- metrics change,
- evaluation rules change,
- or evidence validity changes.

## Must Represent

- overall status,
- requirement-level results,
- passed requirements,
- failed requirements,
- insufficient-evidence requirements,
- violations,
- severity,
- evidence references,
- observed margins,
- simulation validity,
- and candidate restart levels where deterministically known.

## Must Not Represent

- applied design changes,
- complete regenerated plans,
- unsupported causal certainty,
- or hidden LLM reasoning.

## Invariants

1. Numeric comparisons must be deterministic.
2. Requirement targets and observed values must remain traceable.
3. Simulation failure must be distinguishable from requirement failure.
4. Proven causes must be distinguishable from candidate causes.
5. Insufficient evidence must be represented explicitly.
6. Multiple simultaneous failures must be supported.
7. The evaluator must not modify the design.

## Key Boundary

`EvaluationReport` answers:

> Which requirements passed or failed, based on what evidence?

It does not answer:

> What exact design change should be applied?

---

# 15. RevisionDirective

## Purpose

`RevisionDirective` specifies the smallest justified change and the earliest stage that must rerun.

It may be produced deterministically or through a narrowly scoped LLM diagnosis.

## Produced By

- deterministic revision routing for clear cases,
- conditional LLM diagnosis for ambiguous or semantic cases.

## Primary Consumers

- patch application,
- `Parametric Solver`,
- `Geometry Planner`,
- `Mechanical Concept Planner`,
- `Requirement Interpreter` when clarification is required,
- `DesignSession`.

## Lifecycle

Created only when a design iteration requires revision.

Each directive belongs to one parent iteration.

## Must Represent

- restart stage,
- diagnosis summary,
- evidence references,
- confidence where reasoning is uncertain,
- preserve list,
- allowed modification scope,
- change operations or planning directive,
- expected effects,
- risks,
- required revalidation,
- and escalation reason where applicable.

## Must Not Represent

- proof that the revision will succeed,
- hidden full-session context,
- unrelated plan regeneration,
- or direct mutation of historical objects.

## Invariants

1. The directive must restart from the earliest affected stage, not automatically from the beginning.
2. It must preserve as much of the validated design as possible.
3. It must use parameter or local geometry patches when sufficient.
4. Its expected effects are hypotheses, not evidence.
5. Every applied directive must be followed by deterministic rebuilding and revalidation.
6. It must not include cross-design retrieved knowledge.
7. It must support parameter, geometry, concept, and requirement-clarification routes.

## Key Boundary

`RevisionDirective` answers:

> What should change next, and where should execution restart?

It does not answer:

> Did the change succeed?

---

# 16. IterationRecord

## Purpose

`IterationRecord` is the compact engineering history of one design iteration.

It enables comparison, rollback, token-efficient revision context, and research traceability.

## Produced By

`DesignSession Manager`

## Primary Consumers

- `DesignSession`,
- revision context builder,
- development reports,
- experiment analysis,
- rollback logic.

## Lifecycle

Created once after each completed or terminated iteration.

It is immutable.

## Must Represent

- iteration identity,
- parent iteration,
- applied revision reference,
- changed objects,
- compact metric summary,
- compact evaluation summary,
- outcome,
- comparison to parent,
- artifact references,
- and whether it became the best-known iteration.

## Must Not Represent

- complete raw trajectories,
- complete CAD data,
- complete LLM prompts,
- complete LLM responses,
- or the entire domain state duplicated inline.

## Invariants

1. History must remain compact.
2. The record must be sufficient to compare iterations.
3. The authoritative artifacts must remain referenceable.
4. Failed revision directions may be summarized for future avoidance.
5. Iteration records must not become a cross-design retrieval database.

## Key Boundary

`IterationRecord` answers:

> What changed in this iteration, and what happened afterward?

---

# 17. DesignSession

## Purpose

`DesignSession` is the authoritative index of the current design process.

It ties together current object versions, artifacts, iteration history, best-known design, and execution status.

## Produced By

`DesignSession Manager`

## Primary Consumers

- pipeline orchestration,
- artifact management,
- revision routing,
- user-facing progress reporting,
- final engineering report.

## Lifecycle

Created when a user starts a design request.

Closed when:

- the design passes,
- the user stops the process,
- a blocking clarification remains unresolved,
- the iteration budget is exhausted,
- or no justified revision remains.

## Must Represent

- session identity,
- design identity,
- execution status,
- current iteration,
- references to current domain objects,
- iteration records,
- best-known iteration,
- blocked revision directions,
- open engineering questions,
- and artifact locations.

## Must Not Represent

- an unbounded conversation transcript,
- cross-session memory,
- embedded CAD binaries,
- raw simulation arrays,
- or hidden agent state.

## Invariants

1. It must be reconstructable from persisted objects and artifacts.
2. It must never be sent wholesale to an LLM.
3. LLM context must be built from minimal, relevant slices.
4. Historical object versions must remain available.
5. The best-known iteration must be distinguishable from the latest iteration.
6. Session state must not leak into another design session.

## Key Boundary

`DesignSession` answers:

> What is the current state and history of this design session?

It does not itself perform engineering reasoning.

---

# 18. Object Versioning and Provenance

Every top-level object should support version lineage.

A new version should identify:

- the previous version,
- the producing stage,
- the reason for change,
- the triggering revision directive where relevant,
- and the implementation version that produced it.

Versioning should support:

- rollback,
- deterministic replay,
- artifact comparison,
- debugging,
- and research analysis.

Do not introduce a complex event-sourcing system before evidence demonstrates that it is needed.

Simple immutable files with explicit references are acceptable initially.

---

# 19. Validation Philosophy

Validation exists at multiple levels.

## Structural Validation

Checks:

- required data exists,
- types are correct,
- identifiers are valid,
- references resolve,
- enumerated values are legal.

## Semantic Validation

Checks:

- an object respects its domain responsibility,
- referenced requirements or parts exist,
- contradictory values are represented explicitly,
- units are compatible,
- prohibited downstream information is absent.

## Execution Validation

Checks:

- a geometry plan can be solved,
- a solved design can be built,
- a simulation plan can run,
- a metric can be computed,
- an evaluation has sufficient evidence.

Invalid objects must not silently continue downstream.

Validation errors must remain structured and traceable.

---

# 20. Stage Specifications Own Concrete Schemas

This document defines conceptual contracts.

Each stage specification must define the concrete implementation contract for that stage, including:

- exact Pydantic models,
- exact JSON examples,
- required and optional fields,
- field-level validation,
- prompt input,
- prompt output,
- fixtures,
- negative tests,
- producer behavior,
- consumer assumptions,
- and migration notes.

Examples:

```text
STAGE_01_REQUIREMENT_INTERPRETER.md
STAGE_02_MECHANICAL_CONCEPT_PLANNER.md
GEOMETRY_IR.md
STAGE_03_GEOMETRY_PLANNER.md
STAGE_04_PARAMETRIC_SOLVER.md
```

If a concrete stage schema changes, update that stage specification first.

Change this document only when the meaning or ownership of a top-level engineering concept changes.

---

# 21. Criteria for Adding a New Top-Level Object

Do not create a new top-level domain object merely because a new class is convenient.

A new top-level object is justified only when:

1. It represents a distinct engineering concept.
2. No existing object can own it without violating responsibility boundaries.
3. It has a clear producer.
4. It has a clear consumer.
5. It has an independent lifecycle.
6. It improves generality or traceability.
7. At least two structurally different use cases justify it.

Otherwise, extend an existing object or use a nested supporting model.

---

# 22. Criteria for Changing an Existing Object

A top-level object's meaning or boundary may change when evidence shows:

- repeated responsibility overlap,
- missing information required by multiple downstream stages,
- inability to represent a broad class of mechanical systems,
- excessive duplication,
- unacceptable token or persistence cost,
- or inability to reproduce or revise a design.

Before changing ownership or meaning, create an Architecture Change Proposal.

Field-level changes inside a stage-owned schema do not require an architecture change when the conceptual boundary remains intact.

---

# 23. Generality Check

Every top-level object must be reviewable against at least:

- the active benchmark,
- a structurally different benchmark,
- and a more complex hypothetical mechanical system.

For example:

```text
Active benchmark:
A lidded enclosure with a retaining mechanism.

Contrasting benchmark:
An intermittent indexing device.

Complexity check:
A multi-stage mechanism with several parts, multiple inputs, coupled outputs,
assembly constraints, and several simulation tests.
```

If an object cannot represent all three without benchmark-specific core fields, its specification is incomplete.

---

# 24. Final Principle

The domain specification is the stable engineering language of ASSY-Next.

Prompts may change.

Pydantic models may change.

Geometry IR may change.

CAD kernels may change.

Simulation backends may change.

Benchmarks may change.

The conceptual meaning and ownership of the top-level engineering objects should change only when implementation evidence demonstrates that the current language is insufficient.

Do not freeze implementation details too early.

Do not leave engineering meaning implicit.

Preserve stable concepts while allowing evidence-driven implementation evolution.
