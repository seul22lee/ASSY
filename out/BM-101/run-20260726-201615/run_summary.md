# Run Summary - BM-101 (advanced)

- run: `20260726-201615`
- created: 2026-07-26T20:16:15
- commit: `340b508`
- code version: `0.2.0`
- session status: **failed**

## Stages

| # | stage | status | main output | authority | evidence / checks | unresolved |
|---|---|---|---|---|---|---|
| 01 | requirement_interpreter | ok | RequirementSpec | `placeholder` | - | - |
| 02 | mechanical_architecture | ok | MechanicalArchitecture | `placeholder` | - | - |
| 03 | product_architecture | ok | ProductArchitecture | `placeholder` | - | - |
| 04 | concept_visualization | ok | ConceptVisualization | `placeholder` | - | - |
| 05 | engineering_integration | ok | CADReadyEngineeringDefinition | `provisional` | 23/26 checks satisfied | 0 blocking |
| 06 | parametric_solver | ok | SolvedDesign | `authoritative` | 23 parameters | 0 violated constraints |
| 07 | cad_builder | ok | CADArtifactManifest | `authoritative` | 4 parts built | 0 build failures |
| 08 | simulation_plan | ok | SimulationPlan | `authoritative` | - | - |
| 09 | simulation_runner | ok | SimulationResult | `provisional` | 0 runs via none | 0 not completed |
| 10 | metric_extraction | ok | MetricReport | `provisional` | 0 metrics | 0 invalid |
| 11 | requirement_evaluation | ok | EvaluationReport | `provisional` | overall=insufficient_evidence | 0 failed, 5 under-evidenced |
| 12 | revision_routing | ok | RevisionDirective | `authoritative` | - | - |

## Authority legend

| value | meaning |
|---|---|
| `authoritative` | genuinely derived from upstream engineering data |
| `evidence-backed` | produced by a validation backend and valid |
| `provisional` | produced, but incomplete or under-evidenced |
| `placeholder` | temporary scaffolding, not engineering judgement |

## CAD readiness

**ready = False**

- blocking problems cleared: True
- mandatory checks executed: True
- mandatory checks passing: True
- all commitments determined: True
- structurally solvable: True

## Requirement evaluation

**overall = insufficient_evidence**

| requirement | status | observed | note |
|---|---|---|---|
| REQ-001 | insufficient_evidence | - | engineering definition is not CAD-ready |
| REQ-002 | insufficient_evidence | - | engineering definition is not CAD-ready |
| REQ-003 | insufficient_evidence | - | engineering definition is not CAD-ready |
| REQ-004 | insufficient_evidence | - | engineering definition is not CAD-ready |
| REQ-005 | insufficient_evidence | - | engineering definition is not CAD-ready |

## Where to look

- design loop: `stage_05_engineering_integration/trace.md`
- geometry: `stage_07_cad_builder/part_legend.md`
- physical evidence: `stage_09_simulation_runner/report.md`
- assumptions: `assumptions.md`
