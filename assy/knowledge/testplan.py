"""Test planning rules: mechanism semantics -> validation experiments.

Test planning keys on the engineering roles present in the definition, never on
the presence of a particular entity. A product with a hinged body gets swing
tests because it is hinged, not because it is a box.

Each rule also declares which **backend** is competent for the phenomenon, and
what that backend's results are and are not valid for. No single backend has
universal authority (SYSTEM_ARCHITECTURE section 16): rigid-body contact goes to
MuJoCo, compliant-element behaviour goes to closed-form analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from assy.domain.downstream import ValidationBackend
from assy.domain.engineering import CommitmentKind, EngineeringWorkingState


@dataclass(frozen=True)
class TestRule:
    """One validation experiment implied by a role being present."""

    name: str
    role: str
    backend: ValidationBackend
    phenomenon: str
    observables: tuple[str, ...]
    validity_domain: tuple[str, ...]
    duration_s: float = 3.0
    rationale: str = ""
    requires_aspects: tuple[str, ...] = ()
    actuation: dict[str, float] = field(default_factory=dict)

    def applicable(self, state: EngineeringWorkingState) -> str | None:
        """Return the subject of the first entity this rule applies to."""
        for ent in state.active_by_kind(CommitmentKind.ENTITY):
            if self.role not in ent.roles:
                continue
            if all(
                state.find_subject(f"{ent.subject}.{a}") is not None
                for a in self.requires_aspects
            ):
                return ent.subject
        return None


RULES: tuple[TestRule, ...] = (
    # -- hinged bodies: rigid-body motion and contact ----------------------
    TestRule(
        name="close_and_engage",
        role="hinged",
        backend=ValidationBackend.MUJOCO,
        phenomenon="closing_motion_and_engagement",
        observables=("lid_angle_deg", "input_torque_nmm", "latch_contact_state", "engagement_event"),
        validity_domain=("rigid body motion", "contact timing", "gross interference"),
        duration_s=2.5,
        requires_aspects=("angular_range",),
        rationale="A hinged closure must reach the closed state and engage its retention.",
    ),
    TestRule(
        name="hold_under_disturbance",
        role="retention_interface",
        backend=ValidationBackend.MUJOCO,
        phenomenon="retention_under_load",
        observables=("lid_angle_deg", "retention_force_n", "latch_contact_state"),
        validity_domain=("rigid contact retention", "gross release under load"),
        duration_s=2.0,
        rationale="Retention is only meaningful against an external opening disturbance.",
    ),
    TestRule(
        name="release_latch",
        role="user_release",
        backend=ValidationBackend.MUJOCO,
        phenomenon="release_actuation",
        observables=("lid_angle_deg", "release_force_n", "latch_contact_state", "disengagement_event"),
        validity_domain=("gross disengagement kinematics",),
        duration_s=2.0,
        rationale="A releasable feature must actually disengage when actuated.",
    ),
    TestRule(
        name="reopen_without_interference",
        role="hinged",
        backend=ValidationBackend.MUJOCO,
        phenomenon="reopening_clearance",
        observables=("lid_angle_deg", "interference_event"),
        validity_domain=("swept rigid-body clearance",),
        duration_s=2.5,
        requires_aspects=("angular_range",),
        rationale="Reopening must not jam or collide anywhere in the swing.",
    ),
    # -- compliant elements: closed-form, not rigid-body -------------------
    TestRule(
        name="latch_compliance",
        role="compliant",
        backend=ValidationBackend.ANALYTICAL,
        phenomenon="compliant_retention",
        observables=(
            "beam_deflection_mm",
            "peak_strain",
            "peak_stress_mpa",
            "insertion_force_n",
            "retention_force_n",
            "release_force_n",
            "strain_margin",
        ),
        validity_domain=(
            "small-deflection linear-elastic cantilever",
            "quasi-static single actuation",
        ),
        requires_aspects=("beam_geometry",),
        rationale=(
            "Beam compliance sets retention, insertion, and release force. A rigid-body "
            "simulator cannot represent it, so it is evaluated in closed form."
        ),
    ),
    # -- translating bodies: the lift case ---------------------------------
    TestRule(
        name="full_travel",
        role="translating",
        backend=ValidationBackend.MUJOCO,
        phenomenon="powered_travel",
        observables=("platform_height_mm", "platform_overshoot_mm", "peak_actuator_force_n"),
        validity_domain=("rigid-body travel", "quasi-static actuation"),
        duration_s=4.0,
        requires_aspects=("travel_envelope",),
        rationale="A translating output must achieve its declared stroke under load.",
    ),
    TestRule(
        name="hold_under_load",
        role="translating",
        backend=ValidationBackend.MUJOCO,
        phenomenon="unpowered_hold",
        observables=("platform_drift_mm", "platform_height_mm"),
        validity_domain=("unpowered drift", "joint friction model"),
        duration_s=3.0,
        requires_aspects=("travel_envelope",),
        rationale="A lifting device must hold position when the input is released.",
    ),
)


def applicable_rules(state: EngineeringWorkingState) -> list[tuple[TestRule, str]]:
    """Every test rule the current engineering definition activates."""
    out: list[tuple[TestRule, str]] = []
    for rule in RULES:
        subject = rule.applicable(state)
        if subject is not None:
            out.append((rule, subject))
    return out
