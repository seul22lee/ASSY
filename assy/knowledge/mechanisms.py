"""Mechanism family catalogue.

Explicit engineering knowledge for Stage 02. Entries describe what a family
*does* and its engineering traits; they never mention a benchmark. Candidates
must differ by engineering principle, not cosmetics (STAGE_02 diversity rule).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PartTemplate:
    name: str
    role: str  # MechanismRole value
    roles: tuple[str, ...]  # engineering roles for spawning rules


@dataclass(frozen=True)
class MechanismFamily:
    id: str
    principle: str
    converts_from: str
    converts_to: str
    parts: tuple[PartTemplate, ...]
    relation: str
    self_locking: bool
    part_count: int
    compactness: float  # 0..1, higher is more compact
    efficiency: float
    strengths: tuple[str, ...] = ()
    weaknesses: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    open_questions: tuple[str, ...] = ()
    extra_roles: dict[str, tuple[str, ...]] = field(default_factory=dict)


FAMILIES: tuple[MechanismFamily, ...] = (
    MechanismFamily(
        id="lead_screw",
        principle="Lead screw converting crank rotation to platform translation",
        converts_from="rotation",
        converts_to="translation",
        parts=(
            PartTemplate("crank", "input", ("rotating", "user_contact", "manufactured")),
            PartTemplate("drive_shaft", "transmission", ("rotating", "load_bearing", "manufactured")),
            PartTemplate("lift_screw", "conversion", ("rotating", "threaded_pair", "load_bearing", "manufactured")),
            PartTemplate("platform", "output", ("translating", "load_bearing", "manufactured")),
            PartTemplate("guide_rail", "guidance", ("load_bearing", "manufactured")),
            PartTemplate("housing", "structure", ("enclosure", "load_bearing", "manufactured")),
        ),
        relation="travel = turns * lead",
        self_locking=True,
        part_count=6,
        compactness=0.8,
        efficiency=0.35,
        strengths=("inherently self-locking", "high mechanical advantage", "compact vertical envelope"),
        weaknesses=("low efficiency", "slow travel per turn"),
        risks=("thread wear in polymer", "platform tilt if guidance is weak"),
        open_questions=("lead selection versus required crank effort",),
    ),
    MechanismFamily(
        id="rack_pinion",
        principle="Rack and pinion converting crank rotation to platform translation",
        converts_from="rotation",
        converts_to="translation",
        parts=(
            PartTemplate("crank", "input", ("rotating", "user_contact", "manufactured")),
            PartTemplate("drive_shaft", "transmission", ("rotating", "load_bearing", "manufactured")),
            PartTemplate("pinion", "conversion", ("rotating", "gear_pair", "load_bearing", "manufactured")),
            PartTemplate("rack", "conversion", ("translating", "gear_pair", "load_bearing", "manufactured")),
            PartTemplate("platform", "output", ("translating", "load_bearing", "manufactured")),
            PartTemplate("guide_rail", "guidance", ("load_bearing", "manufactured")),
            PartTemplate("housing", "structure", ("enclosure", "load_bearing", "manufactured")),
        ),
        relation="travel = turns * pi * module * teeth",
        self_locking=False,
        part_count=7,
        compactness=0.6,
        efficiency=0.90,
        strengths=("high efficiency", "fast travel per turn", "simple tooth geometry"),
        weaknesses=("back-drives under load", "needs a brake or detent to hold position"),
        risks=("payload falls when the crank is released",),
        open_questions=("how position is held without continuous crank effort",),
    ),
    MechanismFamily(
        id="cable_drum",
        principle="Cable drum winding to raise a platform",
        converts_from="rotation",
        converts_to="translation",
        parts=(
            PartTemplate("crank", "input", ("rotating", "user_contact", "manufactured")),
            PartTemplate("drum", "conversion", ("rotating", "load_bearing", "manufactured")),
            PartTemplate("cable", "transmission", ("load_bearing",)),
            PartTemplate("platform", "output", ("translating", "load_bearing", "manufactured")),
            PartTemplate("guide_rail", "guidance", ("load_bearing", "manufactured")),
            PartTemplate("housing", "structure", ("enclosure", "load_bearing", "manufactured")),
        ),
        relation="travel = turns * pi * drum_diameter",
        self_locking=False,
        part_count=6,
        compactness=0.7,
        efficiency=0.85,
        strengths=("very low friction", "tolerant of misalignment"),
        weaknesses=("tension only", "requires a ratchet to hold", "cable spooling discipline"),
        risks=("uncontrolled descent if the ratchet fails", "cable fatigue"),
        open_questions=("spooling control across the drum width",),
    ),
    MechanismFamily(
        id="geneva",
        principle="External Geneva mechanism producing intermittent indexing",
        converts_from="rotation",
        converts_to="intermittent_rotation",
        parts=(
            PartTemplate("crank", "input", ("rotating", "user_contact", "manufactured")),
            PartTemplate("driver_disc", "conversion", ("rotating", "intermittent_pair", "load_bearing", "manufactured")),
            PartTemplate("geneva_wheel", "output", ("rotating", "intermittent_pair", "load_bearing", "manufactured")),
            PartTemplate("housing", "structure", ("enclosure", "load_bearing", "manufactured")),
        ),
        relation="index_angle = 360 / slots",
        self_locking=True,
        part_count=4,
        compactness=0.75,
        efficiency=0.70,
        strengths=("positive indexing", "inherent dwell locking"),
        weaknesses=("phase-dependent clearance", "impact at entry if mistimed"),
        risks=("locking disc interference with slot tips",),
        open_questions=("slot count versus dwell fraction",),
    ),
    MechanismFamily(
        id="cantilever_snap",
        principle="Cantilever snap-fit providing releasable retention",
        converts_from="displacement",
        converts_to="retention",
        parts=(
            PartTemplate("snap_beam", "retention", ("load_bearing", "manufactured", "precision_interface")),
            PartTemplate("catch", "retention", ("load_bearing", "manufactured")),
            PartTemplate("housing", "structure", ("enclosure", "load_bearing", "manufactured")),
        ),
        relation="retention_force = f(beam_stiffness, undercut)",
        self_locking=False,
        part_count=3,
        compactness=0.95,
        efficiency=1.0,
        strengths=("zero added parts", "tool-free release"),
        weaknesses=("creep under sustained load", "strain-limited"),
        risks=("beam yields if over-deflected during assembly",),
    ),
)


def families_for(converts_from: str, converts_to: str) -> list[MechanismFamily]:
    return [f for f in FAMILIES if f.converts_from == converts_from and f.converts_to == converts_to]


def by_id(fid: str) -> MechanismFamily:
    for f in FAMILIES:
        if f.id == fid:
            return f
    raise KeyError(fid)
