"""Benchmark fixtures — pipeline evaluation.

A **benchmark** evaluates the complete ASSY pipeline on a product-level problem.
An **architecture experiment** validates or falsifies an architectural hypothesis
and lives in ``experiments/``. The two are related but not the same thing:

    Experiment  ->  architectural evidence
    Benchmark   ->  pipeline evaluation

A product may legitimately appear in both categories in different roles. The
Geneva mechanism is one: it is historical evidence for the Stage 05 working-state
architecture (``experiments/geneva_stage05/``) *and* an advanced benchmark
(BM-101) for validating a mature implementation.

Fixtures live here, never in the core (Rule BM-2). A new benchmark should need
new fixtures and tests, not architecture changes (Rule BM-3). Benchmark
requirements must never prescribe a mechanism — that is what the pipeline is
being evaluated on.
"""

from dataclasses import dataclass, field
from enum import Enum


class Tier(str, Enum):
    """Benchmarks are tiered by what maturity of implementation they evaluate."""

    CORE = "core"
    """Evaluates the initial implementation milestone. Expected to run today."""

    ADVANCED = "advanced"
    """Reserved for validating a mature pipeline. Not part of the initial milestone."""


@dataclass(frozen=True)
class Benchmark:
    id: str
    name: str
    request: str
    tier: Tier = Tier.CORE
    clarifications: list[str] = field(default_factory=list)


BM001 = Benchmark(
    id="BM-001",
    name="Latching Storage Box",
    tier=Tier.CORE,
    request=(
        "Design a small storage box with a hinged lid. "
        "The lid should stay closed until the user releases it with a thumb. "
        "The box should be safe to use, easy to assemble, and practical to manufacture."
    ),
    clarifications=[
        "Desktop-sized product.",
        "Manual operation only.",
        "Additive manufacturing is expected.",
    ],
)

BM002 = Benchmark(
    id="BM-002",
    name="Hand-Cranked Lift Box",
    tier=Tier.CORE,
    request=(
        "Design a compact desktop lifting box. "
        "The user should rotate an external hand crank to raise and lower an internal platform. "
        "The platform should lift approximately 80-100 mm and support a payload of approximately 1 kg. "
        "The mechanism should be enclosed inside the housing. "
        "The product should be safe to use, mechanically plausible, easy to assemble, "
        "and practical to manufacture. Avoid obvious jamming or unstable operation."
    ),
    clarifications=[
        "Desktop-sized product.",
        "Manual operation only.",
        "Continuous or intermittent lifting is acceptable.",
        "Self-locking is optional if justified.",
        "Multiple shafts, bearings, guides, and supports are allowed.",
    ],
)

BM101 = Benchmark(
    id="BM-101",
    name="Geneva Indexing Box",
    tier=Tier.ADVANCED,
    # Note: the request never names a mechanism. Which mechanism realises
    # intermittent indexing is what the pipeline is being evaluated on.
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
    ],
)

CORE = {b.id: b for b in (BM001, BM002)}
ADVANCED = {b.id: b for b in (BM101,)}
ALL = {**CORE, **ADVANCED}

__all__ = ["ADVANCED", "ALL", "BM001", "BM002", "BM101", "CORE", "Benchmark", "Tier"]
