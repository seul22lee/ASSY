# Research Log

A persistent record of **why** each architectural revision was made.

This is not a changelog. Git already records what changed and when. What Git
cannot record is the reasoning: what exposed a defect, what evidence was
gathered, why one correction was chosen over another, and why the correction is
general rather than a patch fitted to the benchmark that revealed it.

The log exists so the design history can be reconstructed later — for a technical
report, a paper, or by whoever inherits this system and needs to know whether a
contract is the way it is by decision or by accident.

## Convention

One sequential file per meaningful architecture revision:

    RL-0001.md, RL-0002.md, RL-0003.md, ...

Numbers are never reused and entries are never rewritten. A superseded decision
gets a new entry that references the old one; the original stays as it was
written, including where it turned out to be wrong. A log that is silently
corrected is no longer evidence.

An entry is warranted when a **contract** changes: a schema, a stage boundary, an
ownership assignment, or a rule about what a stage may read. Bug fixes,
refactors and test additions do not warrant one unless they revealed a contract
defect — in which case the defect is the subject, not the fix.

Each entry is 1–2 pages and carries these sections:

| Section | Records |
|---|---|
| Summary | what the revision did, in two or three sentences |
| Trigger | what exposed the issue — a run, an audit, a rendering, a golden comparison |
| Evidence | the observation that justified acting, with numbers where they exist |
| Root cause | the contract defect, not the symptom |
| Design decision | what was chosen, and what was rejected |
| Stage ownership | which stage owns each new field, and why there |
| Generalization | why this is not a benchmark-specific patch |
| Validation performed | what was run and what it proved |
| Freeze status | whether the contract is stable |
| Remaining issues | what was deliberately left open |
| Next validation target | what should be tested next |

## Standing constraints these entries are written against

- Benchmarks evaluate the pipeline; they never define it. No entry may justify a
  rule by "BM-00x needed it".
- Evidence is reported as observed. A failed refinement is recorded as a failure,
  not restated as a success.
- Temperature-0 reproducibility is not evidence of repeatability.
- A stage that lacks information reports a typed deficiency; it never
  compensates silently.

## Index

| Entry | Subject | Contract touched |
|---|---|---|
| [RL-0001](RL-0001.md) | Stage 01 → 02 strict-consumer migration | `BehaviourSpec`, `Stage01ContractDeficiency` |
| [RL-0002](RL-0002.md) | Stage 02 architecture completeness | typed obligations, interfaces, functions |
| [RL-0003](RL-0003.md) | Stage 03 as strict consumer | product pieces, obligation ownership |
| [RL-0004](RL-0004.md) | Stage 04 spatial concept analysis | reference frame, swept volumes, issues |
| [RL-0005](RL-0005.md) | Stage 04 visualization and visual review | `placed_pieces`, render artifact |
| [RL-0006](RL-0006.md) | Spatial contract repair | frame/faces/stations, access paths, motion kind, realization constraints |
| [RL-0007](RL-0007.md) | Renderer readability and coverage audit | none — renderer only |
| [RL-0008](RL-0008.md) | Kinematic element class | `ElementClass`, `permits_motion`, `attached_to` |
| [RL-0009](RL-0009.md) | Spatial-first, semantics-on-top | none — renderer only |
| [RL-0010](RL-0010.md) | Topological anchors | `TopologyKind`, `TopologicalAnchor` |
| [RL-0011](RL-0011.md) | Derived placement | `LocationBasis`, `LocationDerivation` |
