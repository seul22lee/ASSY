"""Benchmark fixtures — synchronized with the BM Markdown documents.

The BM Markdown files are the **golden problem definitions**. These fixtures carry
only the *User Requirement* and *Clarifications* sections verbatim, because those
are the only sections Stage 01 may consume. Everything else in a BM document
(fixed requirements, stress map, success criteria) is reviewer material and must
never reach the pipeline.

A **benchmark** evaluates the complete pipeline; an **architecture experiment**
validates one hypothesis and lives in ``experiments/``.

    Experiment  ->  architectural evidence
    Benchmark   ->  pipeline evaluation

Fixtures live here, never in the core (Rule BM-2).
"""

from dataclasses import dataclass, field
from enum import Enum


class Tier(str, Enum):
    CORE = "core"
    """Evaluates the initial implementation milestone."""

    ADVANCED = "advanced"
    """Reserved for validating a mature pipeline."""


@dataclass(frozen=True)
class Benchmark:
    id: str
    name: str
    request: str
    tier: Tier = Tier.CORE
    clarifications: list[str] = field(default_factory=list)
    document: str = ""


BM001 = Benchmark(
    id="BM-001",
    name="Latching Storage Box",
    tier=Tier.CORE,
    document="BM-001_LATCHING_STORAGE_BOX.md",
    request=(
        "Design a compact desktop storage box with a reusable latch. "
        "The box should open and close repeatedly without accidental opening during "
        "normal handling. "
        "The latch should be easy for a user to operate while remaining secure during "
        "transport. "
        "The product should be suitable for low-cost manufacturing and should be "
        "practical for desktop use. "
        "The design should be mechanically plausible and easy to assemble."
    ),
    clarifications=[
        "Approximate product size: desktop-sized (roughly hand-held).",
        "Opening angle is not prescribed.",
        "One-handed operation is desirable but not mandatory.",
        "Repeated opening and closing is expected.",
        "A separate metal fastener is allowed but not required.",
        "Multiple engineering solutions are acceptable.",
    ],
)

BM002 = Benchmark(
    id="BM-002",
    name="Enclosed Hand-Cranked Platform Lift",
    tier=Tier.CORE,
    document="BM-002_ENCLOSED_HAND_CRANKED_PLATFORM_LIFT.md",
    request=(
        "Design a compact desktop platform-lifting device enclosed within a housing. "
        "The user should rotate an external hand crank to raise and lower an internal "
        "platform. "
        "The platform should move approximately 80-100 mm and support a payload of "
        "approximately 1 kg. "
        "The mechanism should remain enclosed within the housing during normal operation. "
        "The product should be safe to use, mechanically plausible, easy to assemble, "
        "and practical to manufacture. "
        "Avoid obvious jamming or unstable operation."
    ),
    clarifications=[
        "Desktop-sized product.",
        "Manual operation only.",
        "Continuous or intermittent lifting is acceptable.",
        "Self-locking is optional if justified.",
        "Different transmission mechanisms are acceptable.",
        "Multiple shafts, bearings, guides, and supports are allowed.",
    ],
)

BM101 = Benchmark(
    id="BM-101",
    name="Geneva Indexing Box",
    tier=Tier.ADVANCED,
    document="BM-101_GENEVA_INDEXING_BOX.md",
    request=(
        "Design a compact desktop indexing box. "
        "The user should rotate an external hand crank to advance an internal indexing "
        "platform by one discrete step. "
        "The output should remain stationary between indexing events. "
        "The mechanism should be enclosed inside a protective housing. "
        "The product should be mechanically plausible, easy to assemble, practical to "
        "manufacture, and suitable for repeated manual operation."
    ),
    clarifications=[
        "Desktop-sized product.",
        "Manual operation only.",
        "The number of indexed positions is not prescribed.",
        "Different housing layouts are acceptable.",
        "Multiple support strategies are acceptable.",
        "The Geneva implementation may vary provided the required behavior is achieved.",
    ],
)

CORE = {b.id: b for b in (BM001, BM002)}
ADVANCED = {b.id: b for b in (BM101,)}
ALL = {**CORE, **ADVANCED}

__all__ = ["ADVANCED", "ALL", "BM001", "BM002", "BM101", "CORE", "Benchmark", "Tier"]
