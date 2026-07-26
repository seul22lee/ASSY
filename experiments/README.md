# Architecture Experiments

> **An experiment evaluates the architecture. A benchmark evaluates the framework.**

These are two conceptually separate categories in ASSY-Next, and keeping them
separate is what prevents a benchmark from quietly becoming the reason an
architecture has a particular shape.

```text
Experiment  ->  architectural evidence
Benchmark   ->  pipeline evaluation
```

## What belongs here

An experiment validates or falsifies an **architectural hypothesis** before that
hypothesis becomes stable. It is scoped to the architecture under test and
normally stops well short of running the whole pipeline.

Examples of the kind of question an experiment answers:

- Are the proposed Stage 05 primitives sufficient?
- Can the working state represent phase-dependent engineering problems?
- Does supersession become necessary?
- Is agenda exhaustion sufficient for CAD readiness?
- What information must exist before deterministic CAD generation?

Current and anticipated experiments:

| Experiment | Hypothesis under test | Status |
|---|---|---|
| [`geneva_stage05/`](geneva_stage05/) | The Stage 05 working state needs exactly four object families | Supported with modifications |
| *(future)* | Spatial engineering representation | Not started |
| *(future)* | Solver convergence behaviour | Not started |
| *(future)* | Knowledge representation and ownership | Not started |

## What does not belong here

A product-level problem that evaluates the complete pipeline is a **benchmark**
and belongs in `benchmarks/` — see `BENCHMARK_SUITE.md`.

## Promotion

A product used in an experiment may later turn out to be a good benchmark. When
that happens it is **added** to the benchmark suite in that new role; it is not
moved, and the experiment record stays where it is.

Geneva is the worked example. It was introduced to pressure-test the Stage 05
working state, and only afterwards was recognised as a valuable product-level
problem. It now appears in both categories, in two distinct roles:

- **`experiments/geneva_stage05/`** — historical evidence supporting the current
  Stage 05 architecture. Stops at the Stage 05 boundary.
- **`BM-101_GENEVA_INDEXING_BOX.md`** — an advanced benchmark for validating a
  mature implementation. Registered as `Tier.ADVANCED`, outside the initial
  milestone.

The direction matters and only runs one way:

```text
architectural investigation
        -> treat as an experiment first
        -> promote to a benchmark only if it proves valuable
           as a complete product-level evaluation
```

## The rule this structure protects

**The architecture is derived from engineering principles and implementation
evidence — never from the requirements of a particular benchmark** (Rules G-1
through G-4).

This is a live risk, not a theoretical one. During the vertical-slice
implementation, two components were written against the BM-002 lift-box topology
and failed immediately on BM-001: the CAD builder required a `platform` and a
`housing.internal_height`, and the `motion_interference` check hardcoded the same
subjects. Both were genuine Rule BM-1 violations that had entered the *core*, and
both were only exposed by running a structurally different benchmark. They are
now generic — shape rules and checks key on engineering roles.

Running a second, structurally different problem is what surfaces this class of
defect. One benchmark never will.
