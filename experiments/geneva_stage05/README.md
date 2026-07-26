# Geneva — Stage 05 Working-State Falsification

> **This is implementation evidence, not a benchmark.**
>
> Its purpose was to falsify the proposed Stage 05 working-state model. It
> exercises one architectural hypothesis, not the complete ASSY pipeline, so it
> does not belong in `benchmarks/`.

---

## Hypothesis under test

The Stage 05 working state can be represented by exactly four object families:

```text
Commitment Store
Problem Agenda
Resolution Graph
Check Registry
```

## Why Geneva

Both existing benchmarks are near-quasi-static: their clearances can be
evaluated at the extremes of travel. A Geneva indexing mechanism is
**phase-dependent** — the locking-disc/slot-tip relationship is only correct
when swept, and its worst case occurs mid-motion rather than at either end.

That property is what makes it a useful falsification target, and it is the one
thing neither BM-001 nor BM-002 stresses.

## Result

**Supported with modifications.** No fifth primitive was required. Six semantic
gaps were found, two of them blocking:

| # | Finding | Severity | Where it landed |
|---|---------|----------|-----------------|
| 1 | Supersession is mandatory — design routinely retracts choices | blocking | `EngineeringWorkingState.supersede` |
| 2 | Agenda exhaustion is insufficient for CAD readiness | blocking | `checks.definition_closure` |
| 3 | Objectives cannot be modelled as pass/fail constraints | required | `CommitmentKind.OBJECTIVE` |
| 4 | Checks need kinds; only some may autonomously gate | required | `CheckKind`, `GATING_KINDS` |
| 5 | Checks need an evaluation domain, not just a version scope | required | `Check.evaluation_domain` |
| 6 | Duplicate problems need canonical identity | required | `Problem.key` |

Plus an explicit convergence policy, since the agenda has no guaranteed fixed
point (`Budget` in `assy/stages/s05_engineering.py`).

### The two decisive observations

**Retraction is the normal case, not an exception.** Assembly analysis showed
the Geneva wheel could not be installed into a closed housing, which forced a
housing-split change that retired an earlier commitment and reopened a closed
problem. An append-only resolution graph cannot express this.

**An empty agenda is not a finished design.** The agenda emptied while seven
necessary commitments were still missing, including how the turntable transmits
torque to its shaft — without which the product cannot be built at all. This is
why a *total* closure pass over the commitment store is mandatory and cannot be
replaced by "no problems remain".

## Running it

```bash
./mujoco_core/bin/py -m experiments.geneva_stage05.probe
```

The probe drives Stage 05 alone and asserts the six findings still hold. It is a
regression guard on the architecture: if a change to the working-state model
makes any assertion fail, that change has silently dropped a property the
falsification established.

## Scope

The probe stops at the Stage 05 boundary. It deliberately does not run the
solver, CAD builder, or simulation — those are pipeline concerns, and evaluating
them is what benchmarks are for.

## Relationship to BM-101

Geneva legitimately belongs to both categories, in two different roles. That is
not a contradiction — see [`../README.md`](../README.md) for the distinction.

| | This experiment | BM-101 |
|---|---|---|
| Category | Architecture experiment | Benchmark (`Tier.ADVANCED`) |
| Evaluates | The Stage 05 working-state model | The complete pipeline |
| Scope | Stops at the Stage 05 boundary | Requirement through revision |
| Status | Complete; kept as a regression guard | Reserved for a mature implementation |

The order was experiment first, benchmark second: Geneva was introduced to
pressure-test Stage 05, and only afterwards recognised as a valuable
product-level problem. It was **added** to the benchmark suite in that new role
rather than moved, so this evidence record stays intact.
