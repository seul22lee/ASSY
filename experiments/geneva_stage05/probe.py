"""Regression guard for the six findings the Geneva falsification established.

Each check below corresponds to one finding. If an assertion fails, a change to
the working-state model has silently dropped a property that the falsification
proved necessary - which is a reason to revisit the architecture, not to relax
the assertion.

    ./mujoco_core/bin/py -m experiments.geneva_stage05.probe
"""

from __future__ import annotations

import sys

from assy.domain.common import reset_ids
from assy.domain.engineering import (
    GATING_KINDS,
    Check,
    CheckKind,
    CheckResult,
    Commitment,
    CommitmentKind,
    CommitmentStatus,
    EngineeringWorkingState,
    Problem,
    ProblemOrigin,
    ProblemType,
    Resolution,
    Severity,
)
from assy.knowledge import checks as K
from assy.stages import (
    Budget,
    EngineeringIntegration,
    MechanicalArchitectureGenerator,
    ProductArchitecturePlanner,
    RequirementInterpreter,
)
from experiments.geneva_stage05 import GENEVA_CLARIFICATIONS, GENEVA_REQUEST

RESULTS: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))


# -- Finding 1: supersession is mandatory -----------------------------------
def finding_1_supersession() -> None:
    state = EngineeringWorkingState()
    shell = state.commit(
        Commitment(
            kind=CommitmentKind.ENTITY,
            subject="housing",
            statement="monolithic four-wall shell",
            roles=["enclosure"],
        )
    )
    problem = state.open_problem(
        Problem(
            type=ProblemType.UNDETERMINED,
            origin=ProblemOrigin.SPAWNED,
            entities=["housing"],
            phenomenon="assembly_access",
            evaluation_domain="all_assembly_states",
            statement="wheel cannot be installed into a closed shell",
        )
    )
    first = state.propose(
        Resolution(problem_id=problem.id, approach="monolithic shell", commitments=[shell])
    )
    state.close_problem(problem.id, first.id)

    # Assembly analysis forces retraction of the shell decision.
    retraction = state.propose(
        Resolution(
            problem_id=problem.id,
            approach="removable side panel carrying one bushing of each pair",
            supersedes=[shell.id],
        )
    )
    state.apply(retraction)

    preserved = state.commitments[shell.id].status is CommitmentStatus.SUPERSEDED
    pointed = state.commitments[shell.id].superseded_by == retraction.id
    record(
        "1 supersession retires without deleting",
        preserved and pointed,
        f"status={state.commitments[shell.id].status.value}, by={state.commitments[shell.id].superseded_by}",
    )


# -- Finding 2: agenda exhaustion is insufficient ---------------------------
def finding_2_closure() -> None:
    state = EngineeringWorkingState()
    state.commit(
        Commitment(
            kind=CommitmentKind.ENTITY,
            subject="geneva_wheel",
            statement="indexing wheel",
            roles=["rotating", "manufactured"],
            status=CommitmentStatus.SELECTED,
        )
    )
    agenda_empty = not state.open_problems
    check, opened = K.run_check(
        next(c for c in K.CHECKS if c.name == "definition_closure"), state
    )
    record(
        "2 closure finds gaps an empty agenda missed",
        agenda_empty and check.result is CheckResult.FAIL and len(opened) > 0,
        f"agenda_empty={agenda_empty}, closure={check.result.value}, found={len(opened)}",
    )


# -- Finding 3: objectives are commitments ----------------------------------
def finding_3_objectives() -> None:
    state = EngineeringWorkingState()
    obj = state.commit(
        Commitment(
            kind=CommitmentKind.OBJECTIVE,
            subject="dwell_accuracy",
            statement="minimise dwell angular error",
            expression="minimize(angular_error)",
        )
    )
    # A trade-off has no pass/fail predicate; it must survive as a direction.
    record(
        "3 objective is representable and has no closure predicate",
        obj.kind is CommitmentKind.OBJECTIVE and obj.value is None and obj.is_determined,
        f"kind={obj.kind.value}, value={obj.value}",
    )


# -- Finding 4: check kinds gate differently --------------------------------
def finding_4_check_kinds() -> None:
    judgment = Check(
        name="believable_proportions",
        kind=CheckKind.JUDGMENT,
        evaluation_domain="static",
        result=CheckResult.FAIL,
    )
    deterministic = Check(
        name="motion_interference",
        kind=CheckKind.DETERMINISTIC,
        evaluation_domain="full_cycle",
        result=CheckResult.FAIL,
    )
    ok = (not judgment.gates) and deterministic.gates and CheckKind.JUDGMENT not in GATING_KINDS
    record(
        "4 only deterministic/analytical/rule checks gate",
        ok,
        f"judgment.gates={judgment.gates}, deterministic.gates={deterministic.gates}",
    )


# -- Finding 5: checks need an evaluation domain ----------------------------
def finding_5_evaluation_domain() -> None:
    # Every registered check must declare a domain; a per-pose check would have
    # passed where the Geneva full-cycle sweep failed.
    missing = [c.name for c in K.CHECKS if not c.evaluation_domain]
    swept = [c.name for c in K.CHECKS if c.evaluation_domain not in ("static", "definition")]
    record(
        "5 every check declares an evaluation domain",
        not missing and len(swept) >= 3,
        f"missing={missing}, swept_domains={len(swept)}",
    )


# -- Finding 6: canonical problem identity ----------------------------------
def finding_6_canonical_identity() -> None:
    state = EngineeringWorkingState()

    def interference(domain: str) -> Problem:
        return Problem(
            type=ProblemType.VIOLATED,
            origin=ProblemOrigin.CHECK,
            entities=["driver_disc", "geneva_wheel"],
            phenomenon="interference",
            evaluation_domain=domain,
            statement="lock arc fouls slot tip",
        )

    a = state.open_problem(interference("indexing_phase_0_to_120_deg"))
    b = state.open_problem(interference("indexing_phase_0_to_120_deg"))  # duplicate discovery
    c = state.open_problem(interference("dwell_phase"))  # genuinely different problem

    merged = a.id == b.id
    distinct = c.id != a.id
    record(
        "6 duplicates merge, different phases stay distinct",
        merged and distinct and len(state.problems) == 2,
        f"merged={merged}, distinct_by_phase={distinct}, total={len(state.problems)}",
    )


# -- Convergence policy ------------------------------------------------------
def finding_7_convergence_policy() -> None:
    """The agenda has no guaranteed fixed point, so a budget must bound it."""
    reset_ids()
    spec = RequirementInterpreter().run(
        request=GENEVA_REQUEST, clarifications=list(GENEVA_CLARIFICATIONS)
    )
    mech = MechanicalArchitectureGenerator().run(spec=spec)
    prod = ProductArchitecturePlanner().run(spec=spec, mechanical=mech)
    tight = EngineeringIntegration(budget=Budget(max_iterations=5)).run(
        spec=spec, mechanical=mech, product=prod
    )
    blocked = tight.readiness.blocked_reason is not None and not tight.readiness.ready
    record(
        "7 exceeding the budget blocks structurally, never silently passes",
        blocked,
        f"reason={tight.readiness.blocked_reason.value if tight.readiness.blocked_reason else None}, "
        f"ready={tight.readiness.ready}",
    )
    return mech.selected_id


def main() -> int:
    print("Geneva - Stage 05 working-state falsification probe")
    print("=" * 68)
    finding_1_supersession()
    finding_2_closure()
    finding_3_objectives()
    finding_4_check_kinds()
    finding_5_evaluation_domain()
    finding_6_canonical_identity()
    selected = finding_7_convergence_policy()

    print(f"\nStage 02 selected '{selected}' for the Geneva request\n")
    width = max(len(n) for n, _, _ in RESULTS)
    failed = 0
    for name, ok, detail in RESULTS:
        mark = "PASS" if ok else "FAIL"
        if not ok:
            failed += 1
        print(f"  [{mark}] {name.ljust(width)}  {detail}")

    print()
    if failed:
        print(f"{failed}/{len(RESULTS)} findings no longer hold - the architecture regressed.")
    else:
        print(f"All {len(RESULTS)} findings hold. Four-object model supported with modifications.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
