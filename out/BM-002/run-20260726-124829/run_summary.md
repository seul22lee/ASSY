# Run Summary - BM-002 (core)

- run: `20260726-124829`
- created: 2026-07-26T12:48:29
- commit: `c7862a1`
- code version: `0.2.0`
- session status: **passed**

## Stages

| # | stage | status | main output | authority | evidence / checks | unresolved |
|---|---|---|---|---|---|---|
| 01 | requirement_interpreter | ok | RequirementSpec | `placeholder` | - | - |
| 02 | mechanical_architecture | ok | MechanicalArchitecture | `placeholder` | - | - |
| 03 | product_architecture | ok | ProductArchitecture | `placeholder` | - | - |
| 04 | concept_visualization | ok | ConceptVisualization | `placeholder` | - | - |
| 05 | engineering_integration | ok | CADReadyEngineeringDefinition | `authoritative` | 22/26 checks satisfied | 0 blocking |
| 06 | parametric_solver | ok | SolvedDesign | `authoritative` | 34 parameters | 0 violated constraints |
| 07 | cad_builder | ok | CADArtifactManifest | `authoritative` | 6 parts built | 0 build failures |
| 08 | simulation_plan | ok | SimulationPlan | `authoritative` | - | - |
| 09 | simulation_runner | ok | SimulationResult | `evidence-backed` | 2 runs via mujoco | 0 not completed |
| 10 | metric_extraction | ok | MetricReport | `evidence-backed` | 7 metrics | 0 invalid |
| 11 | requirement_evaluation | ok | EvaluationReport | `evidence-backed` | overall=pass | 0 failed, 0 under-evidenced |
| 12 | revision_routing | ok | RevisionDirective | `authoritative` | - | - |

## Authority legend

| value | meaning |
|---|---|
| `authoritative` | genuinely derived from upstream engineering data |
| `evidence-backed` | produced by a validation backend and valid |
| `provisional` | produced, but incomplete or under-evidenced |
| `placeholder` | temporary scaffolding, not engineering judgement |

## CAD readiness

**ready = True**

- blocking problems cleared: True
- mandatory checks executed: True
- mandatory checks passing: True
- all commitments determined: True
- structurally solvable: True

## Requirement evaluation

**overall = pass**

| requirement | status | observed | note |
|---|---|---|---|
| REQ-001 | pass | 87.258mm |  |
| REQ-002 | pass | 87.258mm | payload was present as simulated mass during the travel test |
| REQ-003 | pass | - | CAD-readiness closure plus evidence from motion/contact |
| REQ-004 | pass | - | CAD-readiness closure plus evidence from motion/contact |
| REQ-005 | pass | - | CAD-readiness closure plus evidence from motion/contact |
| REQ-006 | pass | - | CAD-readiness closure plus evidence from motion/contact |
| REQ-007 | pass | - | CAD-readiness closure plus evidence from motion/contact |
| REQ-008 | pass | - | CAD-readiness closure plus evidence from motion/contact |
| REQ-009 | pass | - | CAD-readiness closure plus evidence from motion/contact |

## Where to look

- design loop: `stage_05_engineering_integration/trace.md`
- geometry: `stage_07_cad_builder/part_legend.md`
- physical evidence: `stage_09_simulation_runner/report.md`
- assumptions: `assumptions.md`
