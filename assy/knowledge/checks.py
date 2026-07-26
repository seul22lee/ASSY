"""The check library.

Implements STAGE_05 sections 10 and 17. Every check declares a kind and an
evaluation domain; only deterministic/analytical/rule checks gate CAD readiness.

``definition_closure`` is the mandatory total pass. The Geneva trace showed the
agenda emptying while the design was still underdetermined, so exhaustion alone
is not a valid exit condition (section 17).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from assy.domain.engineering import (
    Check,
    CheckKind,
    CheckResult,
    CommitmentKind,
    EngineeringWorkingState,
    Problem,
    ProblemOrigin,
    ProblemType,
    Severity,
)
from assy.knowledge import materials as mat

# Aspects a commitment with a given role must eventually own, expressed as
# "<subject>.<aspect>" commitments. This table is what makes closure *total*.
REQUIRED_ASPECTS: dict[str, list[str]] = {
    "rotating": ["radial_support", "axial_retention", "material", "process"],
    "translating": ["guidance", "travel_envelope", "end_stops", "material", "process"],
    "load_bearing": ["load_path", "material", "process"],
    "enclosure": ["assembly_access", "material", "process", "wall_thickness"],
    "user_contact": ["pinch_access"],
    "manufactured": ["material", "process", "build_orientation"],
    "precision_interface": ["tolerance_chain"],
}


@dataclass
class Outcome:
    result: CheckResult
    detail: str = ""
    margin: float | None = None
    problems: list[Problem] = field(default_factory=list)
    inputs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CheckSpec:
    name: str
    kind: CheckKind
    evaluation_domain: str
    fn: Callable[[EngineeringWorkingState], Outcome]
    mandatory: bool = False


def _entities(state: EngineeringWorkingState):
    return state.active_by_kind(CommitmentKind.ENTITY)


def _has(state: EngineeringWorkingState, subject: str) -> bool:
    return state.find_subject(subject) is not None


def _problem(
    entities: list[str], phenomenon: str, statement: str, domain: str, check_name: str
) -> Problem:
    return Problem(
        type=ProblemType.VIOLATED,
        origin=ProblemOrigin.CHECK,
        entities=entities,
        phenomenon=phenomenon,
        evaluation_domain=domain,
        statement=statement,
        severity=Severity.BLOCKING,
        discovered_by=check_name,
    )


# --------------------------------------------------------------------------
# 1. Definition closure - the mandatory total pass
# --------------------------------------------------------------------------
def definition_closure(state: EngineeringWorkingState) -> Outcome:
    """Total sweep of the commitment store for anything still undetermined.

    This is the check that must exist for agenda exhaustion to mean anything.
    """
    missing: list[Problem] = []
    inputs: list[str] = []

    for ent in _entities(state):
        inputs.append(ent.subject)
        for role in ent.roles:
            for aspect in REQUIRED_ASPECTS.get(role, []):
                subject = f"{ent.subject}.{aspect}"
                if not _has(state, subject):
                    missing.append(
                        Problem(
                            type=ProblemType.INCOMPLETE,
                            origin=ProblemOrigin.CHECK,
                            entities=[ent.subject],
                            phenomenon=aspect,
                            evaluation_domain="definition",
                            statement=f"{ent.subject}: {aspect} is undefined",
                            severity=Severity.BLOCKING,
                            discovered_by="definition_closure",
                        )
                    )

    # Any parameter still lacking both a value and an expression.
    for p in state.active:
        if not p.is_determined:
            missing.append(
                Problem(
                    type=ProblemType.UNDETERMINED,
                    origin=ProblemOrigin.CHECK,
                    entities=[p.subject],
                    phenomenon="parameter_value",
                    evaluation_domain="definition",
                    statement=f"parameter {p.subject} has no value or expression",
                    severity=Severity.BLOCKING,
                    discovered_by="definition_closure",
                )
            )

    if missing:
        return Outcome(
            CheckResult.FAIL,
            f"{len(missing)} undetermined items",
            problems=missing,
            inputs=inputs,
        )
    return Outcome(CheckResult.PASS, "all required definitions present", inputs=inputs)


# --------------------------------------------------------------------------
# 2. Kinematic consistency
# --------------------------------------------------------------------------
def kinematic_consistency(state: EngineeringWorkingState) -> Outcome:
    motions = state.active_by_kind(CommitmentKind.MOTION)
    if not motions:
        return Outcome(CheckResult.INCONCLUSIVE, "no motion commitments")
    problems: list[Problem] = []
    inputs = [m.subject for m in motions]
    for m in motions:
        if m.expression is None and m.value is None:
            problems.append(
                _problem(
                    [m.subject],
                    "motion_relation",
                    f"{m.subject} has no kinematic relation",
                    "full_stroke",
                    "kinematic_consistency",
                )
            )
    if problems:
        return Outcome(CheckResult.FAIL, "incomplete motion relations", problems=problems, inputs=inputs)
    return Outcome(CheckResult.PASS, f"{len(motions)} motion relations defined", inputs=inputs)


# --------------------------------------------------------------------------
# 3. Full-domain motion interference
# --------------------------------------------------------------------------
def motion_interference(state: EngineeringWorkingState) -> Outcome:
    """Swept clearance over the whole motion domain, not a single pose.

    Generic over any translating entity and any enclosure; no product assumed.
    """
    movers = [e for e in _entities(state) if "translating" in e.roles]
    shells = [e for e in _entities(state) if "enclosure" in e.roles]
    if not movers or not shells:
        return Outcome(CheckResult.INCONCLUSIVE, "no translating body inside an enclosure")

    problems: list[Problem] = []
    inputs: list[str] = []
    worst: float | None = None

    for mover in movers:
        stroke = state.find_subject(f"{mover.subject}.travel_envelope")
        clearance = state.find_subject(f"{mover.subject}.motion_clearance")
        if not (stroke and clearance):
            return Outcome(
                CheckResult.INCONCLUSIVE,
                f"{mover.subject}: envelope commitments incomplete",
                inputs=inputs,
            )
        for shell in shells:
            inner = state.find_subject(f"{shell.subject}.internal_height")
            if inner is None:
                continue
            inputs += [stroke.subject, clearance.subject, inner.subject]
            required = float(stroke.value or 0) + 2.0 * float(clearance.value or 0)
            margin = float(inner.value or 0) - required
            worst = margin if worst is None else min(worst, margin)
            if margin < 0:
                problems.append(
                    _problem(
                        [mover.subject, shell.subject],
                        "motion_interference",
                        f"{mover.subject} sweep exceeds {shell.subject} by {-margin:.1f} mm",
                        "full_stroke",
                        "motion_interference",
                    )
                )

    if problems:
        return Outcome(CheckResult.FAIL, "swept travel exceeds the enclosure", margin=worst,
                       problems=problems, inputs=inputs)
    if worst is None:
        return Outcome(CheckResult.INCONCLUSIVE, "no comparable envelope pair", inputs=inputs)
    return Outcome(CheckResult.PASS, f"clearance margin {worst:.1f} mm", margin=worst, inputs=inputs)


# --------------------------------------------------------------------------
# 4. Support and load-path closure
# --------------------------------------------------------------------------
def support_closure(state: EngineeringWorkingState) -> Outcome:
    problems: list[Problem] = []
    inputs: list[str] = []
    for ent in _entities(state):
        if "rotating" not in ent.roles:
            continue
        inputs.append(ent.subject)
        support = state.find_subject(f"{ent.subject}.radial_support")
        if support is None:
            problems.append(
                _problem(
                    [ent.subject],
                    "radial_support",
                    f"{ent.subject} rotates without declared support",
                    "static",
                    "support_closure",
                )
            )
        elif isinstance(support.value, (int, float)) and float(support.value) < 2:
            problems.append(
                _problem(
                    [ent.subject],
                    "support_count",
                    f"{ent.subject} has {support.value} support(s); 2 required for a located axis",
                    "static",
                    "support_closure",
                )
            )
    if problems:
        return Outcome(CheckResult.FAIL, "support incomplete", problems=problems, inputs=inputs)
    return Outcome(CheckResult.PASS, "all rotating bodies supported", inputs=inputs)


def shaft_deflection(state: EngineeringWorkingState) -> Outcome:
    """Analytical: midspan deflection against the declared allowable."""
    from assy.knowledge.elements import shaft_deflection_simply_supported

    dia = state.find_subject("drive_shaft.diameter")
    span = state.find_subject("drive_shaft.support_span")
    load = state.find_subject("drive_shaft.radial_load")
    allow = state.find_subject("drive_shaft.deflection_allowable")
    matc = state.find_subject("drive_shaft.material")
    inputs = [c.subject for c in (dia, span, load, allow, matc) if c]
    if not all((dia, span, load, allow, matc)):
        return Outcome(CheckResult.INCONCLUSIVE, "shaft inputs incomplete", inputs=inputs)

    e = mat.material(str(matc.value)).youngs_modulus_mpa
    d = shaft_deflection_simply_supported(
        float(load.value), float(span.value), float(dia.value), e
    )
    limit = float(allow.value)
    margin = limit - d
    if d > limit:
        return Outcome(
            CheckResult.FAIL,
            f"deflection {d:.3f} mm exceeds allowable {limit:.3f} mm",
            margin=margin,
            problems=[
                _problem(
                    ["drive_shaft"],
                    "structural_margin",
                    f"shaft deflection {d:.3f} mm over allowable {limit:.3f} mm",
                    "static",
                    "shaft_deflection",
                )
            ],
            inputs=inputs,
        )
    return Outcome(CheckResult.PASS, f"deflection {d:.3f} mm within {limit:.3f} mm", margin=margin, inputs=inputs)


# --------------------------------------------------------------------------
# 5. Assembly feasibility
# --------------------------------------------------------------------------
def assembly_feasibility(state: EngineeringWorkingState) -> Outcome:
    order = state.find_subject("assembly.sequence")
    access = state.find_subject("housing.assembly_access")
    inputs = [c.subject for c in (order, access) if c]
    if order is None:
        return Outcome(
            CheckResult.FAIL,
            "no assembly sequence",
            problems=[
                _problem(
                    ["assembly"],
                    "assembly_sequence",
                    "no assembly sequence defined",
                    "all_assembly_states",
                    "assembly_feasibility",
                )
            ],
            inputs=inputs,
        )
    if access is None:
        return Outcome(
            CheckResult.FAIL,
            "enclosure has no assembly access",
            problems=[
                _problem(
                    ["housing"],
                    "assembly_access",
                    "enclosed housing provides no insertion access",
                    "all_assembly_states",
                    "assembly_feasibility",
                )
            ],
            inputs=inputs,
        )
    return Outcome(CheckResult.PASS, f"sequence via {access.value}", inputs=inputs)


# --------------------------------------------------------------------------
# 6. Tolerance closure
# --------------------------------------------------------------------------
def tolerance_closure(state: EngineeringWorkingState) -> Outcome:
    from assy.knowledge.elements import stack_rss

    chains = state.active_by_kind(CommitmentKind.TOLERANCE)
    if not chains:
        return Outcome(CheckResult.INCONCLUSIVE, "no tolerance chains declared")
    inputs = [c.subject for c in chains]
    problems: list[Problem] = []
    worst = None
    for chain in chains:
        parts = [float(x) for x in str(chain.expression or "").split(",") if x.strip()]
        if not parts:
            continue
        stack = stack_rss(parts)
        limit = float(chain.value or 0)
        margin = limit - stack
        worst = margin if worst is None else min(worst, margin)
        if stack > limit:
            problems.append(
                _problem(
                    [chain.subject],
                    "tolerance_chain",
                    f"{chain.subject} RSS stack {stack:.3f} exceeds {limit:.3f}",
                    "all_tolerance_extremes",
                    "tolerance_closure",
                )
            )
    if problems:
        return Outcome(CheckResult.FAIL, "tolerance stack exceeded", problems=problems, inputs=inputs)
    return Outcome(CheckResult.PASS, f"stacks within limits (min margin {worst:.3f})", margin=worst, inputs=inputs)


# --------------------------------------------------------------------------
# 7. Manufacturing legality
# --------------------------------------------------------------------------
def manufacturing_legality(state: EngineeringWorkingState) -> Outcome:
    problems: list[Problem] = []
    inputs: list[str] = []
    for ent in _entities(state):
        if "manufactured" not in ent.roles:
            continue
        m = state.find_subject(f"{ent.subject}.material")
        p = state.find_subject(f"{ent.subject}.process")
        if not (m and p):
            continue
        inputs += [m.subject, p.subject]
        if not mat.compatible(str(m.value), str(p.value)):
            problems.append(
                _problem(
                    [ent.subject],
                    "process_compatibility",
                    f"{ent.subject}: {m.value} incompatible with {p.value}",
                    "static",
                    "manufacturing_legality",
                )
            )
        wall = state.find_subject(f"{ent.subject}.wall_thickness")
        if wall is not None:
            proc = mat.process(str(p.value))
            if float(wall.value) < proc.min_wall_mm:
                problems.append(
                    _problem(
                        [ent.subject],
                        "min_wall",
                        f"{ent.subject}: wall {wall.value} mm below {proc.name} minimum {proc.min_wall_mm} mm",
                        "static",
                        "manufacturing_legality",
                    )
                )
    if problems:
        return Outcome(CheckResult.FAIL, "process rule violation", problems=problems, inputs=inputs)
    return Outcome(CheckResult.PASS, "all parts process-legal", inputs=inputs)


# --------------------------------------------------------------------------
# 8. Safety / user access
# --------------------------------------------------------------------------
PINCH_LIMIT_MM = 3.0


def user_access_safety(state: EngineeringWorkingState) -> Outcome:
    problems: list[Problem] = []
    inputs: list[str] = []
    for ent in _entities(state):
        if "user_contact" not in ent.roles:
            continue
        gap = state.find_subject(f"{ent.subject}.pinch_access")
        if gap is None:
            continue
        inputs.append(gap.subject)
        g = float(gap.value)
        if 0 < g < PINCH_LIMIT_MM:
            continue  # too small to admit a finger
        if g >= PINCH_LIMIT_MM and not state.find_subject(f"{ent.subject}.guard"):
            problems.append(
                _problem(
                    [ent.subject],
                    "pinch_access",
                    f"{ent.subject}: {g:.1f} mm moving/static gap is a pinch hazard and is unguarded",
                    "full_stroke",
                    "user_access_safety",
                )
            )
    if problems:
        return Outcome(CheckResult.FAIL, "pinch hazard", problems=problems, inputs=inputs)
    return Outcome(CheckResult.PASS, "no unguarded pinch points", inputs=inputs)


# --------------------------------------------------------------------------
# 9. Solvability (structural, not numeric)
# --------------------------------------------------------------------------
def system_solvable(state: EngineeringWorkingState) -> Outcome:
    params = [c for c in state.active if c.kind == CommitmentKind.PARAMETER]
    free = [p for p in params if p.value is None and p.expression is None]
    inputs = [p.subject for p in params]
    if free:
        return Outcome(
            CheckResult.FAIL,
            f"{len(free)} free parameters with no defining relation",
            problems=[
                _problem(
                    [p.subject], "parameter_value", f"{p.subject} undetermined", "definition", "system_solvable"
                )
                for p in free
            ],
            inputs=inputs,
        )
    return Outcome(CheckResult.PASS, f"{len(params)} parameters determined", inputs=inputs)


# --------------------------------------------------------------------------
# Registry
# --------------------------------------------------------------------------
CHECKS: list[CheckSpec] = [
    CheckSpec("definition_closure", CheckKind.DETERMINISTIC, "definition", definition_closure, True),
    CheckSpec("kinematic_consistency", CheckKind.DETERMINISTIC, "full_stroke", kinematic_consistency, True),
    CheckSpec("motion_interference", CheckKind.DETERMINISTIC, "full_stroke", motion_interference, True),
    CheckSpec("support_closure", CheckKind.RULE, "static", support_closure, True),
    CheckSpec("shaft_deflection", CheckKind.ANALYTICAL, "static", shaft_deflection, False),
    CheckSpec("assembly_feasibility", CheckKind.DETERMINISTIC, "all_assembly_states", assembly_feasibility, True),
    CheckSpec("tolerance_closure", CheckKind.ANALYTICAL, "all_tolerance_extremes", tolerance_closure, True),
    CheckSpec("manufacturing_legality", CheckKind.RULE, "static", manufacturing_legality, True),
    CheckSpec("user_access_safety", CheckKind.RULE, "full_stroke", user_access_safety, False),
    CheckSpec("system_solvable", CheckKind.DETERMINISTIC, "definition", system_solvable, True),
]

MANDATORY = [c.name for c in CHECKS if c.mandatory]


def run_check(spec: CheckSpec, state: EngineeringWorkingState) -> tuple[Check, list[Problem]]:
    """Execute one check and register it with full validity metadata."""
    outcome = spec.fn(state)
    check = Check(
        name=spec.name,
        kind=spec.kind,
        evaluation_domain=spec.evaluation_domain,
        result=outcome.result,
        detail=outcome.detail,
        margin=outcome.margin,
        input_commitments=outcome.inputs,
        mandatory=spec.mandatory,
    )
    state.record_check(check)

    if outcome.result == CheckResult.PASS:
        # The check that opens a problem is the authority that closes it.
        state.clear_problems_from(spec.name, check.id)
        return check, []

    opened: list[Problem] = []
    for p in outcome.problems:
        p.discovered_by = check.id
        opened.append(state.open_problem(p))
    check.produced_problems = [p.id for p in opened]
    return check, opened
