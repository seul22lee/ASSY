"""Commitment-spawning rules: explicit, inspectable engineering knowledge.

Implements STAGE_05 section 11.1. A new commitment implies required engineering
work; these rules encode which work. They key on engineering *roles*, never on
part names or benchmark identity (Rule BM-1), and they are data rather than
prompt text (section 15.2).

Known limitation, stated honestly per section 11.3: absence-discovery is only as
complete as this table. No system can prove the table is complete, which is why
the mandatory closure pass exists.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from assy.domain.engineering import (
    Commitment,
    Problem,
    ProblemOrigin,
    ProblemType,
    Severity,
)


@dataclass(frozen=True)
class SpawnRule:
    """One unit of engineering knowledge: role -> implied problems."""

    name: str
    role: str
    phenomena: list[str]
    severity: Severity = Severity.BLOCKING
    domain: str = "static"
    rationale: str = ""
    origin: ProblemOrigin = ProblemOrigin.SPAWNED
    extra_roles: list[str] = field(default_factory=list)

    def matches(self, c: Commitment) -> bool:
        if self.role not in c.roles:
            return False
        return all(r in c.roles for r in self.extra_roles)

    def spawn(self, c: Commitment) -> list[Problem]:
        return [
            Problem(
                type=ProblemType.UNDETERMINED,
                origin=self.origin,
                entities=[c.subject],
                phenomenon=ph,
                evaluation_domain=self.domain,
                statement=f"{c.subject}: {ph.replace('_', ' ')} undetermined",
                severity=self.severity,
                discovered_by=c.id,
                serves_requirements=list(c.provenance.requirements),
            )
            for ph in self.phenomena
        ]


# Engineering knowledge base. Extend per domain; never branch on benchmark.
RULES: list[SpawnRule] = [
    SpawnRule(
        name="rotating_element_needs_support",
        role="rotating",
        phenomena=["radial_support", "axial_retention", "bearing_interface"],
        rationale="A rotating body must be located in 5 DOF and retained in the 6th.",
    ),
    SpawnRule(
        name="rotating_element_friction",
        role="rotating",
        phenomena=["friction_wear"],
        severity=Severity.MEDIUM,
        rationale="Sliding contact implies wear and torque loss.",
    ),
    SpawnRule(
        name="translating_element_needs_guidance",
        role="translating",
        phenomena=["guidance", "travel_envelope", "jamming", "end_stops"],
        domain="full_stroke",
        rationale="A translating body needs a guide, a defined stroke, and limits.",
    ),
    SpawnRule(
        name="threaded_pair_relations",
        role="threaded_pair",
        phenomena=["lead_relation", "backdrive_behaviour", "thread_engagement"],
        rationale="A screw pair converts rotation to translation with a lead.",
    ),
    SpawnRule(
        name="gear_pair_relations",
        role="gear_pair",
        phenomena=["ratio_relation", "centre_distance", "backlash"],
        rationale="A gear pair fixes ratio and centre distance simultaneously.",
    ),
    SpawnRule(
        name="intermittent_pair_relations",
        role="intermittent_pair",
        phenomena=["index_relation", "dwell_retention", "engagement_clearance"],
        domain="full_cycle",
        rationale="Indexing mechanisms need phase-dependent engagement and locking.",
    ),
    SpawnRule(
        name="moving_pair_needs_clearance",
        role="moving_pair",
        phenomena=["motion_interference"],
        domain="full_cycle",
        rationale="Relative motion must be swept, not evaluated at one pose.",
    ),
    SpawnRule(
        name="enclosure_needs_assembly_access",
        role="enclosure",
        phenomena=["internal_envelope", "assembly_access", "part_insertion", "service_access"],
        domain="all_assembly_states",
        origin=ProblemOrigin.ASSEMBLY,
        rationale="An enclosed volume must still be assemblable and serviceable.",
    ),
    SpawnRule(
        name="user_contact_needs_safety",
        role="user_contact",
        phenomena=["pinch_access", "ergonomic_reach"],
        origin=ProblemOrigin.REQUIREMENT,
        rationale="Any user-reachable moving boundary is a safety surface.",
    ),
    SpawnRule(
        name="load_bearing_needs_path",
        role="load_bearing",
        phenomena=["load_path", "structural_margin"],
        rationale="Every applied force must reach ground through sized material.",
    ),
    SpawnRule(
        name="manufactured_part_needs_process",
        role="manufactured",
        phenomena=["process_binding", "build_orientation"],
        origin=ProblemOrigin.MANUFACTURING,
        rationale="Process legality cannot be checked before a process is bound.",
    ),
    SpawnRule(
        name="precision_interface_needs_tolerance",
        role="precision_interface",
        phenomena=["tolerance_chain"],
        origin=ProblemOrigin.MANUFACTURING,
        rationale="A functional fit needs an allocated tolerance to survive variation.",
    ),
]


def spawn_for(c: Commitment) -> list[Problem]:
    """Every problem implied by a newly applied commitment."""
    out: list[Problem] = []
    for rule in RULES:
        if rule.matches(c):
            out.extend(rule.spawn(c))
    return out


def rules_for_role(role: str) -> list[SpawnRule]:
    return [r for r in RULES if r.role == role]
