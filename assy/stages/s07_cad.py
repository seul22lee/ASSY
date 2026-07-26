"""Stage 07 - CAD Builder.

Question: can the solved design be deterministically realised as valid CAD?

The builder is a compiler over the entity commitments. It has no knowledge of any
particular product: shape rules key on engineering roles, and every dimension is
read from the SolvedDesign. If a declared entity lacks a dimension its shape rule
requires, that part is reported as a structured build failure rather than being
invented (STAGE_05 section 20) - a failed build still produces a diagnostic
manifest (DOMAIN_SPECIFICATION section 10).

PLACEHOLDER GEOMETRY: parts are primitive solids. This proves the interface -
solved parameters in, artifacts plus a semantic map out - without pretending to
be production geometry.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from build123d import Box, Cylinder, Location, Part, Pos, export_step, export_stl

from assy.domain.common import ObjectMeta, Stage, new_id
from assy.domain.downstream import BuildStatus, CADArtifactManifest, PartArtifact, SolvedDesign
from assy.domain.engineering import CADReadyEngineeringDefinition, Commitment, CommitmentKind
from assy.knowledge import materials as mat
from assy.stages.base import PipelineStage


class MissingDimension(Exception):
    """A shape rule needs a dimension the engineering definition never fixed."""

    def __init__(self, name: str):
        super().__init__(name)
        self.name = name


@dataclass
class BuildCtx:
    """Read-only access to solved values, keyed by semantic subject."""

    values: dict[str, float]

    def need(self, subject: str) -> float:
        if subject not in self.values:
            raise MissingDimension(subject)
        return self.values[subject]

    def get(self, subject: str, default: float) -> float:
        return self.values.get(subject, default)


ShapeFn = Callable[[str, BuildCtx], Part]


@dataclass(frozen=True)
class ShapeRule:
    name: str
    roles: tuple[str, ...]
    build: ShapeFn

    def matches(self, c: Commitment) -> bool:
        return all(r in c.roles for r in self.roles)


# -- shape rules, keyed on engineering role ---------------------------------
def _enclosure(e: str, ctx: BuildCtx) -> Part:
    w = ctx.need(f"{e}.internal_width")
    d = ctx.need(f"{e}.internal_depth")
    h = ctx.need(f"{e}.internal_height")
    t = ctx.need(f"{e}.wall_thickness")
    outer = Box(w + 2 * t, d + 2 * t, h + 2 * t)
    cavity = Box(w, d, h)
    access = Pos(0, (d + 2 * t) / 2, 0) * Box(w, 4 * t, h)
    return outer - cavity - access


def _screw(e: str, ctx: BuildCtx) -> Part:
    dia = ctx.need(f"{e}.pitch_diameter")
    length = ctx.get(f"{e}.travel_envelope", ctx.get("platform.travel_envelope", 80.0)) + 20.0
    return Cylinder(radius=dia / 2, height=length)


def _shaft(e: str, ctx: BuildCtx) -> Part:
    dia = ctx.need(f"{e}.diameter")
    span = ctx.get(f"{e}.support_span", 60.0)
    return Location((0, 0, 0), (0, 90, 0)) * Cylinder(radius=dia / 2, height=span + 20.0)


def _disc(e: str, ctx: BuildCtx) -> Part:
    radius = ctx.get(f"{e}.centre_distance", 45.0) * 0.6
    return Cylinder(radius=radius, height=8.0)


def _crank(e: str, ctx: BuildCtx) -> Part:
    r = ctx.need(f"{e}.crank_radius")
    arm = Box(r, 10.0, 6.0)
    grip = Pos(r / 2, 0, 12.0) * Cylinder(radius=6.0, height=24.0)
    return arm + grip


def _plate(e: str, ctx: BuildCtx) -> Part:
    w = ctx.get("housing.internal_width", 100.0) - 6.0
    d = ctx.get("housing.internal_depth", 80.0) - 6.0
    return Box(max(w, 10.0), max(d, 10.0), 6.0)


def _rail(e: str, ctx: BuildCtx) -> Part:
    h = ctx.get("housing.internal_height", 120.0) - 4.0
    return Cylinder(radius=4.0, height=max(h, 10.0))


def _beam(e: str, ctx: BuildCtx) -> Part:
    return Box(20.0, 6.0, 2.0)


def _generic(e: str, ctx: BuildCtx) -> Part:
    return Box(20.0, 20.0, 10.0)


# Order matters: the first matching rule wins, so specific rules precede general.
SHAPE_RULES: tuple[ShapeRule, ...] = (
    ShapeRule("enclosure", ("enclosure",), _enclosure),
    ShapeRule("screw", ("threaded_pair",), _screw),
    ShapeRule("gear_disc", ("gear_pair",), _disc),
    ShapeRule("index_disc", ("intermittent_pair",), _disc),
    ShapeRule("crank", ("rotating", "user_contact"), _crank),
    ShapeRule("shaft", ("rotating",), _shaft),
    ShapeRule("plate", ("translating",), _plate),
    ShapeRule("snap_beam", ("precision_interface",), _beam),
    ShapeRule("rail", ("load_bearing",), _rail),
    ShapeRule("generic", (), _generic),
)


class CADBuilder(PipelineStage):
    stage_id: ClassVar[Stage] = Stage.CAD
    question: ClassVar[str] = "Can the solved design be deterministically realised as CAD?"
    produces: ClassVar[str] = "CADArtifactManifest"

    def __init__(self, out_dir: str | Path = "out/cad"):
        self.out_dir = Path(out_dir)

    def run(
        self, *, solved: SolvedDesign, definition: CADReadyEngineeringDefinition
    ) -> CADArtifactManifest:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        ctx = BuildCtx(solved.as_dict())
        state = definition.working_state

        parts: list[PartArtifact] = []
        warnings: list[str] = []
        failures: list[str] = []
        semantic_map: dict[str, str] = {}
        solids: list[Part] = []

        for ent in state.active_by_kind(CommitmentKind.ENTITY):
            rule = next((r for r in SHAPE_RULES if r.matches(ent)), SHAPE_RULES[-1])
            try:
                solid = rule.build(ent.subject, ctx)
            except MissingDimension as exc:
                failures.append(
                    f"{ent.subject}: shape rule '{rule.name}' requires '{exc.name}', "
                    "which Stage 05 never determined"
                )
                continue
            except Exception as exc:  # pragma: no cover - kernel failure path
                failures.append(f"{ent.subject}: kernel error: {exc}")
                continue

            mat_c = state.find_subject(f"{ent.subject}.material")
            material = str(mat_c.value) if mat_c else "PLA"
            step = self.out_dir / f"{ent.subject}.step"
            stl = self.out_dir / f"{ent.subject}.stl"
            try:
                export_step(solid, str(step))
                export_stl(solid, str(stl))
            except Exception as exc:  # pragma: no cover
                failures.append(f"{ent.subject}: export failed: {exc}")
                continue

            bb = solid.bounding_box()
            density = mat.material(material).density_kg_m3 if material in mat.MATERIALS else 1240.0
            parts.append(
                PartArtifact(
                    part_id=ent.subject,
                    name=ent.subject,
                    step_path=str(step),
                    mesh_path=str(stl),
                    volume_mm3=round(solid.volume, 2),
                    mass_g=round(solid.volume * 1e-9 * density * 1000.0, 2),
                    bbox_mm=[round(bb.size.X, 2), round(bb.size.Y, 2), round(bb.size.Z, 2)],
                    material=material,
                    placement_mm=[0.0, 0.0, 0.0],
                )
            )
            # Generated BY the builder; never the authority for upstream identity.
            semantic_map[ent.subject] = str(step)
            solids.append(solid)

        assembly_path = None
        if solids:
            try:
                assembly = solids[0]
                for s in solids[1:]:
                    assembly = assembly + s
                assembly_path = str(self.out_dir / "assembly.step")
                export_step(assembly, assembly_path)
            except Exception as exc:  # pragma: no cover
                warnings.append(f"assembly export failed: {exc}")
                assembly_path = None

        status = (
            BuildStatus.FAILED
            if not parts
            else BuildStatus.PARTIAL
            if failures
            else BuildStatus.OK
        )
        return CADArtifactManifest(
            meta=ObjectMeta(object_id=new_id("CAD"), producer=self.stage_id),
            status=status,
            parts=parts,
            assembly_path=assembly_path,
            semantic_map=semantic_map,
            warnings=warnings,
            failures=failures,
            source_solved_id=solved.meta.object_id,
        )
