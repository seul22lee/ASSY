# SYSTEM_ARCHITECTURE.md

> **ASSY-Next System Architecture**
>
> This document defines the high-level execution architecture of ASSY-Next.
>
> It explains how natural-language requirements are transformed into candidate mechanical architectures, coherent product architectures, concept images, mechanically grounded geometry, deterministic CAD, physical validation, and evidence-driven revisions.
>
> This document intentionally avoids exact JSON schemas, Pydantic field definitions, prompt templates, and CAD-kernel-specific implementation details.
>
> Those belong to living stage specifications and future implementation documents.

---

# 1. System Objective

ASSY-Next is a general mechanical design framework.

It receives natural-language requirements describing what a product should do and produces a physically evaluated mechanical product design.

The final result is not only a CAD model.

A complete result should include:

- structured engineering requirements,
- one or more mechanical architecture candidates when meaningful alternatives exist,
- a coherent product architecture,
- concept visualizations,
- mechanically plausible geometry strategies,
- one selected detailed parametric design,
- deterministic CAD artifacts,
- simulation or analytical evidence,
- requirement-level evaluation,
- and a traceable revision history.

The framework must support increasingly complex, multi-part, multi-mechanism mechanical products.

It must not optimize only for the active benchmark.

---

# 2. Architectural Principle

ASSY separates five fundamentally different activities:

```text
Engineering Intent
        ↓
Mechanical Reasoning
        ↓
Product Organization
        ↓
Geometric Engineering
        ↓
Deterministic Verification
```

The roles are:

```text
Requirement Interpreter
    determines what must be achieved.

Mechanical Architecture Generator
    determines how required functions may be realized mechanically.

Product Architecture Planner
    determines how the mechanisms become one coherent, usable product.

Concept Visualization
    communicates and explores spatial product intent.

Geometry Planning
    turns the selected product concept into mechanically plausible,
    knowledge-grounded, parametric geometry.

Deterministic Engineering
    solves, builds, simulates, measures, and evaluates the design.
```

No visual image, LLM statement, or design rationale is considered engineering evidence.

Engineering evidence comes from deterministic calculations, CAD checks, simulation, analytical verification, manufacturing checks, and measured metrics.

---

# 3. High-Level Pipeline

```text
Natural-Language Requirement
        │
        ▼
Requirement Interpreter
        │
        ▼
RequirementSpec
        │
        ▼
Mechanical Architecture Generator
        │
        ▼
Adaptive Mechanical Candidate Set
        │
        ▼
Product Architecture Planner
        │
        ▼
Product Architecture per Candidate
        │
        ▼
Concept Visualization
        │
        ▼
Concept Images / Sketches
        │
        ▼
Multimodal Concept Review
        │
        ▼
Geometry Strategy Planner
        │
        ▼
Adaptive Geometry Alternatives
        │
        ▼
Preliminary Deterministic Feasibility
        │
        ▼
Progressive Candidate Selection
        │
        ▼
Detailed Geometry Planner
        │
        ▼
Parametric Solver
        │
        ▼
CAD Builder
        │
        ▼
Physical and Analytical Validation
        │
        ▼
Metric Extraction
        │
        ▼
Requirement Evaluation
        │
        ├── PASS → Final Design and Evidence
        │
        └── FAIL → Revision Routing
                         │
                         ├── Parameter Revision
                         ├── Geometry Revision
                         ├── Product Architecture Revision
                         ├── Mechanical Architecture Revision
                         └── Requirement Clarification
```

The pipeline supports adaptive pruning.

Not every problem requires multiple candidates.

Not every problem requires every optional reasoning step.

The architecture must avoid generating alternatives merely to satisfy a fixed number.

---

# 4. Adaptive Candidate Policy

Mechanical alternatives should be generated only when they represent materially different engineering choices.

Candidate count is:

```text
1...N
```

A single candidate is appropriate when:

- one mechanical principle clearly dominates,
- alternative concepts differ only cosmetically,
- the requirements strongly constrain the solution,
- or additional candidates would add cost without meaningful tradeoffs.

Multiple candidates are appropriate when they differ in:

- motion-transmission principle,
- force or torque behavior,
- back-driving behavior,
- part count,
- manufacturability,
- material compatibility,
- product packaging,
- assembly strategy,
- maintainability,
- safety,
- or expected failure modes.

Candidates should be progressively eliminated as evidence improves.

```text
Mechanical candidates
        ↓
Product architecture review
        ↓
Concept image review
        ↓
Geometry feasibility
        ↓
Selected detailed candidate
```

The system should preserve rejected candidates and their reasons for later concept-level revision.

---

# 5. Stage 1 — Requirement Interpreter

## Engineering Question

> What must the product accomplish?

## Responsibility

The Requirement Interpreter converts natural language into structured engineering intent.

It identifies:

- required functions,
- intended inputs,
- intended outputs,
- quantitative targets,
- qualitative goals,
- operating scenarios,
- manufacturing constraints,
- material constraints,
- environmental constraints,
- usability requirements,
- assembly expectations,
- assumptions,
- unknowns,
- and priorities.

## Non-Responsibility

It must not:

- select mechanisms,
- define product layout,
- create geometry,
- choose detailed dimensions,
- predict forces,
- or generate CAD.

## Output

```text
RequirementSpec
```

---

# 6. Stage 2 — Mechanical Architecture Generator

## Engineering Question

> What mechanical principles and mechanisms can realize the required functions?

## Responsibility

This stage produces one or more mechanically distinct candidate architectures.

Each candidate should define, at a conceptual level:

- major functional parts,
- mechanisms,
- interfaces,
- degrees of freedom,
- motion relationships,
- input-output transformation,
- holding or release behavior,
- safety-relevant mechanism behavior,
- likely tradeoffs,
- likely failure modes,
- and unresolved engineering decisions.

## Candidate Diversity

Alternatives should not be generated merely by changing names or cosmetic layout.

Meaningful alternatives must differ in the underlying engineering.

For example, a lift product may consider:

- rack-and-pinion,
- lead screw with geared input,
- cable drum with holding mechanism.

These are valid alternatives because their:

- motion conversion,
- torque behavior,
- back-driving,
- support requirements,
- packaging,
- and failure modes

are materially different.

## Non-Responsibility

This stage must not produce:

- final product appearance,
- concept images,
- detailed geometry,
- exact gear dimensions,
- exact clearances,
- CAD operations,
- or claims of physical success.

## Output

```text
MechanicalArchitectureCandidateSet
```

---

# 7. Stage 3 — Product Architecture Planner

## Engineering Question

> How should each mechanical architecture become a coherent, usable, safe, and manufacturable product?

## Responsibility

Product Architecture organizes mechanisms into product-level structure.

It should define:

- major product volumes,
- housing strategy,
- mechanism packaging,
- user interaction locations,
- input location,
- output or moving region,
- stable base or mounting strategy,
- protective structure,
- assembly access,
- service access,
- likely part splits,
- high-level load paths,
- major proportions,
- and spatial relationships between product functions.

Product Architecture is not cosmetic styling.

It is the bridge between mechanical principles and product realization.

## Examples

For a latching box:

- rear rotational interface,
- front release interaction,
- protected retaining region,
- internal storage volume,
- coherent lid-body split,
- stable base,
- integrated finger access.

For a hand-cranked lift box:

- enclosed transmission compartment,
- central platform travel volume,
- external accessible crank,
- protected gears and shafts,
- stable lower base,
- removable service cover,
- guided vertical motion region,
- upper and lower travel limits.

## Non-Responsibility

This stage must not define:

- tooth geometry,
- shaft diameters,
- exact clearances,
- detailed wall thickness,
- complete feature graphs,
- or verified mechanical feasibility.

## Output

```text
ProductArchitectureCandidateSet
```

---

# 8. Stage 4 — Concept Visualization

## Engineering Question

> How might the proposed product architecture be visually and spatially interpreted?

## Purpose

Concept images help communicate:

- product silhouette,
- user interaction,
- housing organization,
- visible motion,
- approximate mechanism packaging,
- product coherence,
- access panels,
- protective enclosure,
- and overall spatial intent.

Suitable outputs may include:

- industrial-design concept sketches,
- sectional product concepts,
- exploded conceptual views,
- functional product renders,
- and mechanism-aware silhouette studies.

## Critical Limitation

Concept images are not engineering solutions.

A concept image may be:

- mechanically impossible,
- geometrically inconsistent,
- internally unsupported,
- incorrectly proportioned,
- missing load paths,
- missing bearings or shaft supports,
- inconsistent with gear ratios,
- incompatible with assembly,
- incompatible with manufacturing,
- or unable to satisfy the required forces and motions.

The image generator may invent visually plausible but mechanically invalid details.

Therefore:

```text
Concept Image
≠ Mechanical Proof
≠ Geometry Definition
≠ CAD Specification
≠ Manufacturing Evidence
```

The authoritative sources remain:

- RequirementSpec,
- Mechanical Architecture,
- Product Architecture,
- and later deterministic engineering evidence.

Images are supporting references for spatial and product reasoning.

They must never override structured engineering intent.

---

# 9. Stage 5 — Multimodal Concept Review

## Engineering Question

> Does the concept image remain consistent with the structured mechanical and product architecture?

## Responsibility

A general multimodal LLM reviews each concept visualization against:

- requirements,
- mechanical architecture,
- product architecture,
- required user interaction,
- required motion,
- visible support structure,
- protective housing,
- service access,
- and obvious spatial contradictions.

It may identify:

- missing shaft support,
- inaccessible crank placement,
- exposed dangerous gears,
- impossible platform travel,
- missing housing split,
- unsupported moving components,
- image-invented mechanisms,
- or mismatch between text and image.

## Limitation

This stage performs semantic and conceptual review.

It does not verify:

- force,
- torque,
- stress,
- gear contact,
- tooth geometry,
- backlash,
- clearance,
- interference,
- kinematic ratio,
- structural strength,
- or manufacturability.

A multimodal approval means only:

> The concept image appears consistent enough to continue engineering development.

It does not mean:

> The design is mechanically feasible.

## Revision Limit

Concept visualization should not become an open-ended visual refinement loop.

The default policy should allow:

- one concept review,
- and at most one product-architecture/image revision before geometry exploration,

unless implementation evidence later justifies a different policy.

---

# 10. Stage 6 — Geometry Strategy Planner

## Engineering Question

> What mechanically plausible geometric arrangements could realize the selected mechanical and product architecture?

## Responsibility

This stage is the first stage that must reason deeply about physical implementation.

It creates one or more geometry strategies when meaningful alternatives exist.

A geometry strategy should define:

- major bodies,
- moving bodies,
- support structures,
- shaft-support strategy,
- guide strategy,
- motion envelopes,
- housing segmentation,
- assembly directions,
- service access,
- major load paths,
- critical interfaces,
- clearance regions,
- parameter groups,
- and likely geometry risks.

## Knowledge-Grounded Mechanical Reasoning

Geometry planning must be grounded in mechanical engineering knowledge.

It must not simply imitate the concept image.

The image provides product and spatial inspiration.

The Geometry Planner must correct, reinterpret, or reject image details when they conflict with engineering reality.

Examples of knowledge that may be required include:

### Gears

- gear ratio relationships,
- pitch diameter relationships,
- module or diametral pitch consistency,
- tooth-count compatibility,
- center distance,
- pressure angle assumptions,
- backlash,
- face width,
- shaft support,
- bearing placement,
- housing clearance,
- contact direction,
- load path,
- interference risk,
- undercut risk,
- and manufacturability.

### Shafts and Supports

- support spacing,
- bending risk,
- torque transmission,
- bearing or bushing requirements,
- axial retention,
- assembly direction,
- and housing reinforcement.

### Guides and Sliding Parts

- guide length,
- anti-rotation constraint,
- clearance,
- friction,
- tilt resistance,
- contact area,
- and jamming risk.

### Hinges and Latches

- axis placement,
- motion clearance,
- engagement geometry,
- release direction,
- retention tradeoffs,
- local reinforcement,
- assembly access,
- and material-dependent behavior.

### Enclosures and Housings

- wall continuity,
- structural transitions,
- access panels,
- part splits,
- internal packaging,
- heat or debris protection where relevant,
- and safe separation between users and moving mechanisms.

## Knowledge Source Policy

The Geometry Planner should use explicit, inspectable, and testable engineering knowledge.

Possible implementations may include:

- declarative engineering rules,
- analytical formulas,
- machine-element libraries,
- standards-derived constraints,
- deterministic sizing functions,
- solver constraints,
- or other evidence-supported knowledge representations.

The architecture does not yet prescribe one implementation.

The following are prohibited:

- relying only on the LLM's memory,
- hiding engineering formulas inside prompts,
- treating concept images as mechanical truth,
- or generating dimensions without traceable engineering justification.

The final knowledge representation should be decided through implementation evidence.

## Output

```text
GeometryStrategyCandidateSet
```

---

# 11. Stage 7 — Preliminary Deterministic Feasibility

## Engineering Question

> Which geometry strategies are plausible enough to justify detailed development?

## Responsibility

Before detailed geometry, the system should run lightweight deterministic checks where possible.

Examples include:

- motion-ratio calculations,
- gear-ratio consistency,
- approximate torque relationships,
- envelope fit,
- center-distance feasibility,
- platform travel volume,
- shaft placement,
- guide placement,
- basic clearance,
- basic assembly direction,
- major motion-envelope collision,
- and manufacturing-bound feasibility.

These checks are not full simulation.

They are low-cost rejection tests.

## Purpose

Eliminate candidates that fail obvious engineering conditions before expensive detailed geometry and CAD work.

## Output

```text
PreliminaryFeasibilityReport
```

---

# 12. Stage 8 — Progressive Candidate Selection

## Engineering Question

> Which candidate currently offers the strongest requirement fit and engineering feasibility?

Selection may use:

- deterministic rejection rules,
- weighted requirement comparison,
- engineering tradeoff analysis,
- and a narrowly scoped LLM judgment where qualitative tradeoffs remain.

Selection must consider:

- requirement satisfaction potential,
- mechanical feasibility,
- product usability,
- manufacturability,
- assembly,
- maintainability,
- packaging,
- risk,
- and expected validation cost.

Selection must not be based primarily on:

- visual attractiveness,
- image realism,
- similarity to existing products,
- or convenience for the active benchmark.

Rejected candidates should retain structured rejection reasons.

They may be reconsidered during future concept-level revision.

---

# 13. Stage 9 — Detailed Geometry Planner

## Engineering Question

> What parametric geometry should actually be built for the selected candidate?

## Responsibility

The Detailed Geometry Planner produces solver-ready geometric intent.

It should define:

- stable part identities,
- geometry entities or features,
- symbolic parameters,
- geometric constraints,
- mechanism interfaces,
- support geometry,
- housing geometry,
- assembly features,
- motion clearances,
- user-interaction geometry,
- manufacturing-related geometry,
- and stable references for local revision.

## Critical Rule

Detailed geometry must be based on:

```text
Requirements
+ Mechanical Architecture
+ Product Architecture
+ Concept Visualization
+ Multimodal Review
+ Knowledge-Grounded Geometry Strategy
+ Preliminary Feasibility Evidence
```

It must not be a direct conversion of the image into CAD.

## Output

```text
GeometryPlan
```

The exact Geometry IR remains a living design decision and should be defined from implementation evidence.

---

# 14. Stage 10 — Parametric Solver

## Engineering Question

> What numerical values satisfy the declared engineering constraints?

The solver determines:

- dimensions,
- gear parameters,
- center distances,
- clearances,
- wall thicknesses,
- fits,
- offsets,
- motion relationships,
- parameter bounds,
- equality constraints,
- inequality constraints,
- and optimization objectives.

The solver must be deterministic.

It must not invent topology or mechanisms.

## Output

```text
SolvedDesign
```

---

# 15. Stage 11 — CAD Builder

## Engineering Question

> Can the solved design be deterministically realized as valid CAD?

The CAD Builder:

- compiles geometry,
- creates parts,
- creates assemblies,
- exports manufacturing and simulation assets,
- maintains stable semantic references,
- and reports structured build failures.

It must not silently redesign the product.

## Output

```text
CADArtifactManifest
```

---

# 16. Stage 12 — Physical and Analytical Validation

## Engineering Question

> Does the generated design behave as required?

Validation may include:

- rigid-body simulation,
- contact simulation,
- kinematic analysis,
- analytical engineering calculations,
- manufacturing checks,
- assembly checks,
- structural analysis,
- or other suitable deterministic methods.

No single backend has universal authority.

The correct method depends on the physics being evaluated.

Examples:

- motion and contact may use MuJoCo,
- elastic snap behavior may require analytical or structural models,
- stress may require FEA,
- gear ratio may be checked analytically,
- manufacturability may use process-specific deterministic rules.

The framework should treat every validation method as evidence with an explicit validity domain.

---

# 17. Stage 13 — Metric Extraction

## Engineering Question

> What measurable engineering quantities were observed?

This stage extracts deterministic metrics such as:

- force,
- torque,
- travel,
- speed,
- angle,
- ratio,
- collision,
- contact duration,
- alignment,
- deflection,
- stress,
- cycle completion,
- and manufacturing margins.

It does not decide pass or fail.

---

# 18. Stage 14 — Requirement Evaluation

## Engineering Question

> Does the available evidence satisfy the requirements?

Evaluation compares deterministic metrics to RequirementSpec.

It must distinguish:

- pass,
- fail,
- invalid test,
- insufficient evidence,
- and conflicting evidence.

A test result should not be trusted merely because it is green.

The validation method must be appropriate for the claim being made.

Evidence should be capable of falsifying the design.

The exact representation of discriminating power should be decided when validation stages are implemented.

---

# 19. Stage 15 — Revision Routing

## Engineering Question

> What is the earliest stage that must change?

Preferred revision order:

```text
Parameter
    ↓
Detailed Geometry
    ↓
Geometry Strategy
    ↓
Product Architecture
    ↓
Mechanical Architecture
    ↓
Requirement Clarification
```

The system should first attempt the smallest justified change.

It should not immediately abandon the selected concept after one failed simulation.

Alternative candidates should be reconsidered only when evidence indicates the selected architecture is fundamentally unsuitable.

Every revision must be re-built and revalidated.

---

# 20. Token and Compute Efficiency

Efficiency is a constraint, not the primary objective.

No optimization may weaken:

- engineering correctness,
- stage responsibility,
- candidate diversity when alternatives matter,
- evidence quality,
- or falsifiability.

Efficiency rules include:

- generate candidate sets in one structured call where practical,
- do not force a fixed candidate count,
- prune weak candidates early,
- create detailed geometry only for selected candidates,
- pass compact structured summaries rather than full histories,
- use patches for local revisions,
- do not send raw simulation data to LLMs,
- use deterministic calculations whenever possible,
- and avoid repeated concept-image refinement.

A simpler problem may use one candidate and skip comparison stages.

A complex or ambiguous problem may retain several candidates longer.

---

# 21. LLM and Tool Roles

## General LLM

Appropriate for:

- requirement interpretation,
- mechanical alternatives,
- product architecture,
- tradeoff reasoning,
- candidate comparison,
- and multimodal concept review.

## Image Model

Appropriate for:

- product concept visualization,
- sectional concept exploration,
- silhouette studies,
- and spatial communication.

The image model does not perform mechanical engineering validation.

## Geometry-Focused LLM

Appropriate for:

- geometry strategies,
- support and guide layouts,
- mechanism integration,
- solver-ready geometry intent,
- and local geometry revision.

It must use explicit engineering knowledge and deterministic constraints.

## Deterministic Software

Responsible for:

- parameter solving,
- formula evaluation,
- engineering calculations,
- CAD generation,
- geometry checks,
- simulation,
- metric extraction,
- requirement evaluation,
- and clear revision routing.

---

# 22. Relationship Between Core Planning Stages

The intended distinction is:

```text
Mechanical Architecture
    What makes the product work?

Product Architecture
    How do the mechanisms become a coherent, usable product?

Concept Visualization
    How might that product architecture appear spatially?

Geometry Strategy
    What mechanically plausible arrangements could realize it?

Detailed Geometry
    What exact parametric geometry should be constructed?
```

The authoritative order is:

```text
Engineering intent
    precedes visual interpretation.

Mechanical knowledge
    overrides concept-image invention.

Deterministic evidence
    overrides LLM confidence.
```

---

# 23. Architecture Evolution

This architecture is a working hypothesis.

Its stage boundaries may evolve when implementation evidence demonstrates:

- duplicated reasoning,
- unnecessary token cost,
- missing information flow,
- inability to represent complex products,
- unclear responsibility,
- or repeated revision failures.

Do not change the architecture merely because an alternative appears cleaner.

Do not preserve it merely because it is documented.

Evaluate every change by asking:

> Does this improve the framework's ability to solve increasingly complex and diverse mechanical design problems?

Never evaluate an architectural decision primarily by:

- similarity to the previous ASSY implementation,
- convenience for the active benchmark,
- or implementation simplicity alone.
