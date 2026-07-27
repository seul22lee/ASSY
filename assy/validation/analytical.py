"""Analytical validation backend: compliant elements.

A cantilever snap is strain-limited and quasi-static. Its governing behaviour -
retention force, insertion force, release effort, peak strain - is a closed-form
function of geometry and material, and a rigid-body simulator cannot produce any
of it. This backend evaluates that physics directly.

Validity domain: small-deflection linear-elastic cantilever, quasi-static single
actuation. Outside that (large deflection, creep, fatigue, impact) these numbers
are not evidence.
"""

from __future__ import annotations

from assy.domain.downstream import SimRunStatus, SimTest, SimTestResult, ValidationBackend
from assy.domain.engineering import CADReadyEngineeringDefinition, CommitmentKind
from assy.knowledge import elements as el
from assy.knowledge import materials as mat

LARGE_DEFLECTION_RATIO = 0.1
"""y/L beyond which linear small-deflection theory understates strain."""


def _value(definition: CADReadyEngineeringDefinition, subject: str) -> float | None:
    c = definition.working_state.find_subject(subject)
    if c is None or not isinstance(c.value, (int, float)) or isinstance(c.value, bool):
        return None
    return float(c.value)


def _compliant_entity(definition: CADReadyEngineeringDefinition) -> str | None:
    for ent in definition.working_state.active_by_kind(CommitmentKind.ENTITY):
        if "compliant" in ent.roles:
            return ent.subject
    return None


def run_test(test: SimTest, definition: CADReadyEngineeringDefinition) -> SimTestResult:
    """Evaluate a compliant element in closed form."""
    entity = _compliant_entity(definition)
    if entity is None:
        return SimTestResult(
            test_id=test.id,
            backend=ValidationBackend.ANALYTICAL,
            simulator="analytical",
            status=SimRunStatus.ERROR,
            diagnostics=["no compliant entity in the engineering definition"],
        )

    length = _value(definition, f"{entity}.length")
    width = _value(definition, f"{entity}.width")
    thickness = _value(definition, f"{entity}.thickness")
    undercut = _value(definition, f"{entity}.undercut")
    allowable = _value(definition, f"{entity}.strain_allowable")
    missing = [
        n
        for n, v in (
            ("length", length),
            ("width", width),
            ("thickness", thickness),
            ("undercut", undercut),
            ("strain_allowable", allowable),
        )
        if v is None
    ]
    if missing:
        return SimTestResult(
            test_id=test.id,
            backend=ValidationBackend.ANALYTICAL,
            simulator="analytical",
            status=SimRunStatus.ERROR,
            diagnostics=[f"{entity}: missing {', '.join(missing)}"],
        )

    mat_c = definition.working_state.find_subject(f"{entity}.material")
    material = mat.material(str(mat_c.value)) if mat_c else mat.material("PLA")
    e_mpa = material.youngs_modulus_mpa
    mu = material.friction_vs_self

    force = el.cantilever_snap_deflection_force(undercut, length, width, thickness, e_mpa)
    strain = el.cantilever_snap_strain(undercut, length, thickness)
    stress = e_mpa * strain  # linear elastic

    lead = _value(definition, f"{entity}.lead_angle")
    retain = _value(definition, f"{entity}.retention_angle")
    # Engagement geometry may live on the mating retention entity.
    if lead is None or retain is None:
        for ent in definition.working_state.active_by_kind(CommitmentKind.ENTITY):
            if "retention_interface" in ent.roles:
                lead = lead if lead is not None else _value(definition, f"{ent.subject}.lead_angle")
                retain = retain if retain is not None else _value(
                    definition, f"{ent.subject}.retention_angle"
                )
    lead = lead if lead is not None else 30.0
    retain = retain if retain is not None else 60.0

    insertion = el.snap_engagement_force(force, lead, mu)
    retention = el.snap_engagement_force(force, retain, mu)
    release = force * (1.0 + mu)
    self_lock_limit = el.self_locking_face_angle(mu)

    events: list[str] = []
    diagnostics: list[str] = []
    status = SimRunStatus.COMPLETED

    strain_margin = allowable - strain
    if strain > allowable:
        events.append(f"peak strain {strain:.4f} exceeds allowable {allowable:.4f}")
    stress_margin = material.yield_strength_mpa - stress
    if stress > material.yield_strength_mpa:
        events.append(f"peak stress {stress:.1f} MPa exceeds yield {material.yield_strength_mpa:.1f} MPa")
    if retain >= self_lock_limit:
        events.append(
            f"retention face {retain:.1f} deg at or beyond the {self_lock_limit:.1f} deg "
            "self-locking angle: the latch would be permanent"
        )

    ratio = undercut / length
    if ratio > LARGE_DEFLECTION_RATIO:
        diagnostics.append(
            f"y/L = {ratio:.3f} exceeds {LARGE_DEFLECTION_RATIO}: small-deflection theory "
            "understates strain here; treat the strain margin as optimistic"
        )

    summary = {
        "beam_deflection_mm": round(undercut, 4),
        "beam_length_mm": round(length, 3),
        "beam_thickness_mm": round(thickness, 3),
        "peak_strain": round(strain, 6),
        "strain_allowable": round(allowable, 6),
        "strain_margin": round(strain_margin, 6),
        "peak_stress_mpa": round(stress, 3),
        "stress_margin_mpa": round(stress_margin, 3),
        "deflection_force_n": round(force, 4),
        "insertion_force_n": round(insertion, 4),
        "retention_force_n": round(retention, 4),
        "release_force_n": round(release, 4),
        "retention_to_insertion_ratio": round(retention / insertion, 4) if insertion else 0.0,
        "self_locking_limit_deg": round(self_lock_limit, 3),
        "lead_angle_deg": round(lead, 2),
        "retention_angle_deg": round(retain, 2),
    }

    return SimTestResult(
        test_id=test.id,
        backend=ValidationBackend.ANALYTICAL,
        simulator="analytical/linear-elastic-cantilever",
        simulator_version="1.0",
        status=status,
        duration_s=0.0,
        events=events,
        diagnostics=diagnostics,
        series_summary=summary,
    )
