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

from assy.geometry import FORM_PARAMS, FormClass

from assy.domain.common import ObjectMeta, Stage, new_id
from assy.domain.downstream import BuildStatus, CADArtifactManifest, PartArtifact, SolvedDesign
from assy.domain.engineering import CADReadyEngineeringDefinition, Commitment, CommitmentKind
from assy.knowledge import materials as mat
from assy.knowledge import partfeatures as PF
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


# -- shape rules, keyed on the form Stage 04 already derived ----------------
#
# The previous rules keyed on ad-hoc role tags, and the tags did not mean what the
# rules assumed. `hinged` marks the *hinge*, so the rule named "lid" built the
# hinge as a lid, while the actual lid - tagged `moving_boundary`, which no rule
# matched - fell through to a generic block. The two parts were built as each
# other, and nothing detected it because a tag that matches nothing is silent.
#
# Form is the typed answer to "what shape is this", it is derived rather than
# hand-maintained, and its parameter names come from the same FORM_PARAMS table
# the geometry kernel uses - so the vocabularies cannot drift apart.

def _from_form(form: FormClass, d: dict[str, float]) -> Part:
    """A primitive for one form, dimensioned by that form's own parameters."""
    if form is FormClass.PLATE:
        return Box(d["length"], d["width"], d["thickness"])
    if form is FormClass.SHAFT:
        return Cylinder(radius=d["diameter"] / 2, height=d["length"])
    if form is FormClass.SHELL:
        w = d["wall"]
        outer = Box(d["length"], d["width"], d["height"])
        inner = Box(max(d["length"] - 2 * w, 0.1),
                    max(d["width"] - 2 * w, 0.1),
                    max(d["height"] - 2 * w, 0.1))
        return outer - inner
    if form is FormClass.COLLAR:
        # A collar is a ring: without the through hole it is just a puck, and the
        # bore is the whole reason the part exists.
        outer = Cylinder(radius=d["bore"], height=d["length"])
        return outer - Cylinder(radius=d["bore"] / 2, height=d["length"] * 1.2)
    if form is FormClass.BLOCK:
        return Box(d["length"], d["width"], d["height"])
    if form in (FormClass.RAIL, FormClass.LINK):
        return Box(d["section"], d["section"], d["length"])
    if form is FormClass.FLEXIBLE:
        return Cylinder(radius=d["section"] / 2, height=d["length"])
    return Box(10.0, 10.0, 10.0)


#: Rotation that carries a form's long axis (local +z) onto a named product axis.
_ORIENT = {"x": (0, 90, 0), "y": (90, 0, 0), "z": (0, 0, 0)}


class CADBuilder(PipelineStage):
    stage_id: ClassVar[Stage] = Stage.CAD
    question: ClassVar[str] = "Can the solved design be deterministically realised as CAD?"
    produces: ClassVar[str] = "CADArtifactManifest"

    def __init__(self, out_dir: str | Path = "out/cad"):
        self.out_dir = Path(out_dir)

    def _form_solid(self, body, ctx: BuildCtx, scale: float) -> tuple[Part, list[str]]:
        """Build one part from its form, preferring solved values over estimates.

        Every dimension is looked up by the name Stage 04 published it under. Where
        the solver has no value the concept estimate stands in - but the caller is
        told which, because a part silently drawn to a placeholder looks exactly
        like one drawn to a solved dimension, and that is how a constant ends up
        being read as a result.
        """
        form = body.solid.form
        dims: dict[str, float] = {}
        substituted: list[str] = []
        for pname in FORM_PARAMS[form]:
            sym = body.solid.params.get(pname)
            if sym is None:
                continue
            solved = ctx.values.get(sym.name)
            if solved is None:
                substituted.append(pname)
                solved = sym.value
            # Both paths carry Stage 04's units: Stage 05 commits the concept
            # estimate verbatim and Stage 06 harvests it without converting, so a
            # "solved" value is 0.4 concept units, not 0.4 mm. Neither stage
            # declares a unit, which is the underlying defect; until one does, the
            # same conversion has to apply to both.
            dims[pname] = max(float(solved) * scale, 0.5)
        solid = _from_form(form, dims)
        axis = getattr(self, "_axes", {}).get(body.name if hasattr(body, "name") else "", "z")
        if axis in _ORIENT and axis != "z":
            solid = Location((0, 0, 0), _ORIENT[axis]) * solid
        return solid, substituted

    def _placements(self, km, state_name, entities) -> tuple[dict, float]:
        """Where each part sits, from Stage 04's poses.

        Stage 04 works in its own units; the solver works in millimetres. Rather
        than assume a conversion, the scale is taken from the two descriptions of
        the same thing - the concept extents against the built part sizes - so the
        layout keeps its proportions whatever units it was expressed in.
        """
        if km is None or not getattr(km, "poses", None):
            return {}, 0.0
        st = state_name or next(iter({s for s, _ in km.poses}), None)
        if st is None:
            return {}, 0.0
        spans = [b.solid.half().x * 2 for b in km.bodies.values()]
        concept = sum(spans) / len(spans) if spans else 1.0
        scale = 60.0 / concept if concept > 1e-9 else 1.0
        out = {}
        for (s_, name), frame in km.poses.items():
            if s_ != st:
                continue
            o = frame.origin
            out[name] = (o.x * scale, o.y * scale, o.z * scale)
        return out, scale

    def _feature_solid(self, kind: PF.FeatureKind, host_bb, ctx: BuildCtx) -> Part | None:
        """Geometry for one feature, proportioned to the part that carries it.

        Deliberately crude - a bore is a cylinder, a boss is a pad. What matters is
        that it is *applied to its part* rather than left beside it, so the result
        is a part with topology instead of a heap of primitives. Real profiles are
        Stage 06's dimensions and a later revision's shape rules.
        """
        eff = PF.effect_of(kind)
        if eff is PF.FeatureEffect.FACE:
            return None
        small = max(min(host_bb.size.X, host_bb.size.Y, host_bb.size.Z), 1.0)
        if kind in (PF.FeatureKind.BORE, PF.FeatureKind.THROUGH_BORE,
                    PF.FeatureKind.BEARING_SEAT):
            return Cylinder(radius=small * 0.22, height=host_bb.size.Z * 1.2)
        if kind is PF.FeatureKind.CAVITY:
            return Box(max(host_bb.size.X - small * 0.4, 1.0),
                       max(host_bb.size.Y - small * 0.4, 1.0),
                       max(host_bb.size.Z - small * 0.4, 1.0))
        if kind is PF.FeatureKind.OPENING:
            return Pos(0, host_bb.size.Y / 2, 0) * Box(
                host_bb.size.X * 0.5, small * 0.5, host_bb.size.Z * 0.5)
        if kind is PF.FeatureKind.FOOT:
            return Pos(0, 0, -host_bb.size.Z / 2) * Box(
                host_bb.size.X * 0.9, host_bb.size.Y * 0.9, small * 0.15)
        if eff is PF.FeatureEffect.CUT:
            return Pos(host_bb.size.X / 2, 0, 0) * Box(small * 0.3, small * 0.3, small * 0.3)
        return Pos(0, host_bb.size.Y / 2, 0) * Box(small * 0.4, small * 0.25, small * 0.4)

    def _apply_features(self, solid: Part, feats: list[str], ctx: BuildCtx) -> tuple[Part, list[str]]:
        applied: list[str] = []
        for fname in sorted(feats):
            try:
                kind = PF.FeatureKind(fname)
            except ValueError:
                continue
            bb = solid.bounding_box()
            geom = self._feature_solid(kind, bb, ctx)
            if geom is None:
                applied.append(f"{fname}:face")
                continue
            try:
                merged = (solid - geom if PF.effect_of(kind) is PF.FeatureEffect.CUT
                          else solid + geom)
                if merged.volume > 0:
                    solid = merged
                    applied.append(f"{fname}:{PF.effect_of(kind).value}")
            except Exception:
                # A cut that would consume the part is refused, not forced.
                continue
        return solid, applied

    def run(
        self, *, solved: SolvedDesign, definition: CADReadyEngineeringDefinition,
        kinematic=None, state_name: str | None = None,
    ) -> CADArtifactManifest:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        ctx = BuildCtx(solved.as_dict())
        state = definition.working_state

        # Features belong to the part named before the dot. They are applied to it,
        # not built beside it: a bore is a hole in something.
        feature_of: dict[str, list[str]] = {}
        parts: list[PartArtifact] = []
        warnings: list[str] = []
        failures: list[str] = []
        semantic_map: dict[str, str] = {}
        solids: list[Part] = []

        entities = list(state.active_by_kind(CommitmentKind.ENTITY))
        feature_of: dict[str, list[str]] = {}
        for c in entities:
            if "feature" in c.roles and "." in c.subject:
                host, fname = c.subject.split(".", 1)
                feature_of.setdefault(host, []).append(fname)

        # Placement comes from the concept layout. Without it every part is exported
        # at the origin and the assembly is a heap of solids at one point.
        placement, scale = self._placements(kinematic, state_name, entities)
        self._axes = dict(getattr(kinematic, "axes", {}) or {})

        if scale:
            warnings.append(
                f"placements taken from the concept layout, scaled by {scale:.1f} "
                "mm per concept unit to match the solved part sizes"
            )

        for ent in entities:
            if "feature" in ent.roles and "." in ent.subject:
                continue
            body = (kinematic.bodies.get(ent.subject)
                    if kinematic is not None and getattr(kinematic, "bodies", None)
                    else None)
            try:
                if body is not None:
                    solid, substituted = self._form_solid(body, ctx, scale)
                    if substituted:
                        warnings.append(
                            f"{ent.subject}: no solved value for "
                            + ", ".join(substituted)
                            + "; the concept estimate was used, so this part is "
                              "drawn to a first cut rather than to a solved size"
                        )
                else:
                    # No body in the concept model means nothing derived a form for
                    # this. Inventing one would put a solid in the assembly that no
                    # stage asked for, so it is reported instead.
                    failures.append(
                        f"{ent.subject}: no form was derived for it upstream, so "
                        "there is no shape to build"
                    )
                    continue
            except MissingDimension as exc:
                failures.append(
                    f"{ent.subject}: requires '{exc.name}', which Stage 05 never determined"
                )
                continue
            except Exception as exc:  # pragma: no cover - kernel failure path
                failures.append(f"{ent.subject}: kernel error: {exc}")
                continue

            solid, applied = self._apply_features(solid, feature_of.get(ent.subject, []), ctx)
            where = placement.get(ent.subject, (0.0, 0.0, 0.0))
            solid = Pos(*where) * solid

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
                    placement_mm=[round(v, 2) for v in where],
                )
            )
            # Generated BY the builder; never the authority for upstream identity.
            semantic_map[ent.subject] = str(step)
            solids.append(solid)

        if scale:
            warnings.append(
                f"placements taken from the concept layout, scaled by {scale:.1f} "
                "mm per concept unit to match the solved part sizes"
            )
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
