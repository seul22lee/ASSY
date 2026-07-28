"""A part as a construction program, not as a bounding box.

Stage 05 previously said `housing` carries a `BORE`. That names a feature and
states nothing a builder can act on: not which face it is on, not where on that
face, not along which axis, not how big. Stage 07 had to invent all four, and the
invented answers are what made the CAD unrecognisable.

What a part actually is, at this stage, is a base solid plus an **ordered sequence
of operations**, each placed on a named face at a stated position with its own
dimensions. That is the representation a parametric feature program needs, and it
is what lets Stage 06 solve dimensions and Stage 07 merely replay them.

Two derivations do the work, and neither is a convention:

  * **Which face.** A feature exists because of an interface, and an interface has
    another element on the far side of it. The feature belongs on the face of its
    host whose normal points toward that element. A bore for a shaft is on the
    side the shaft is on.
  * **Which mate.** Two parts rigidly joined meet on facing faces. Their relative
    position is that mate plus a gap - a relation between named faces, not a pair
    of world coordinates that happen to have been assigned separately.

Everything carries a unit. A bare `0.4` meant whatever the reader assumed, which
is how a concept estimate came to be read as millimetres.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from assy.geometry import FORM_PARAMS, FormClass, Sym, Vec3
from assy.knowledge import partfeatures as PF

FACES = ("+x", "-x", "+y", "-y", "+z", "-z")

#: Outward normal of each named face, in the part's own frame.
FACE_NORMAL: dict[str, Vec3] = {
    "+x": Vec3(1, 0, 0), "-x": Vec3(-1, 0, 0),
    "+y": Vec3(0, 1, 0), "-y": Vec3(0, -1, 0),
    "+z": Vec3(0, 0, 1), "-z": Vec3(0, 0, -1),
}


class Unit(str, Enum):
    MM = "mm"
    DEG = "deg"
    N = "N"
    COUNT = "count"
    RATIO = "ratio"


@dataclass
class Dim:
    """One dimension of one feature, with its unit stated."""

    name: str
    value: float | None
    unit: Unit
    basis: str
    why: str = ""

    @property
    def determined(self) -> bool:
        return self.value is not None


@dataclass
class FeatureOp:
    """One operation in a part's construction program."""

    name: str
    kind: PF.FeatureKind
    effect: PF.FeatureEffect
    on_face: str
    """Which face of the base solid it is applied to."""
    at: tuple[float, float]
    """Position on that face, normalised to (-1..1) in the face's two axes."""
    axis: str
    """The product axis the feature is oriented along."""
    dims: dict[str, Dim] = field(default_factory=dict)
    serves: str = ""
    """The interface or obligation this exists for."""
    why: str = ""
    face_derived: bool = True
    """False when no partner fixed the face and a default was recorded instead."""


@dataclass
class PartProgram:
    """A base solid and the ordered operations that turn it into a part."""

    part: str
    base_form: FormClass
    base_dims: dict[str, Dim] = field(default_factory=dict)
    operations: list[FeatureOp] = field(default_factory=list)

    def ordered(self) -> list[FeatureOp]:
        # Material is added before it is cut: a bore through a boss needs the boss
        # to exist first, and the reverse silently produces a hole in nothing.
        rank = {PF.FeatureEffect.ADD: 0, PF.FeatureEffect.CUT: 1, PF.FeatureEffect.FACE: 2}
        return sorted(self.operations, key=lambda o: (rank[o.effect], o.name))


@dataclass
class Mate:
    """Two parts meeting on named faces."""

    part_a: str
    face_a: str
    part_b: str
    face_b: str
    gap: Dim
    why: str


@dataclass
class Assembly:
    programs: dict[str, PartProgram] = field(default_factory=dict)
    mates: list[Mate] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)


def face_toward(host_origin: Vec3, other_origin: Vec3) -> str:
    """The face of the host whose normal points at the other element.

    This is the derivation that replaces a hardcoded face. A feature serving an
    element on the far side of an interface belongs on the side that element is
    on; picking a fixed face put bores on whichever side the author happened to
    write down.
    """
    d = other_origin - host_origin
    comps = {"x": d.x, "y": d.y, "z": d.z}
    axis = max(comps, key=lambda a: abs(comps[a]))
    if abs(comps[axis]) < 1e-9:
        return "+z"
    return ("+" if comps[axis] > 0 else "-") + axis


def face_axes(face: str) -> tuple[str, str]:
    """The two in-plane axes of a face, for positioning on it."""
    normal = face[1]
    return tuple(a for a in ("x", "y", "z") if a != normal)  # type: ignore[return-value]


def _unit_for(quantity: str) -> Unit:
    return {"angle": Unit.DEG, "count": Unit.COUNT,
            "force": Unit.N, "ratio": Unit.RATIO}.get(quantity, Unit.MM)


def _dim(name: str, sym: Sym | None, scale: float, why: str = "") -> Dim:
    if sym is None:
        return Dim(name, None, Unit.MM, "undetermined", why)
    return Dim(name, sym.value * scale, Unit.MM, sym.basis.value, why or sym.source)


def build_assembly(km, product, characteristic: dict[str, tuple[float | None, str, str]],
                   scale: float = 1.0) -> Assembly:
    """Derive a construction program for every part.

    `characteristic` maps `part.parameter` to (value, quantity, why) - the
    quantities the mechanism principle needs, which is where a hook depth or a
    thread lead enters a feature's dimensions rather than a bounding box.
    """
    asm = Assembly()
    bodies = getattr(km, "bodies", {}) or {}
    poses = getattr(km, "poses", {}) or {}
    states = sorted({s for s, _ in poses})
    state = states[0] if states else None
    origin = {n: poses[(state, n)].origin for (s, n) in poses if s == state} if state else {}

    hosts = getattr(km, "feature_hosts", {}) or {}
    axes = getattr(km, "axes", {}) or {}

    for name, body in bodies.items():
        if name in hosts:
            continue  # a feature is an operation on its host, not a part
        form = body.solid.form
        asm.programs[name] = PartProgram(
            part=name, base_form=form,
            base_dims={p: _dim(f"{name}.{p}", body.solid.params.get(p), scale)
                       for p in FORM_PARAMS[form]},
        )

    # Which element each feature serves, so its face can be derived.
    partner: dict[str, str] = {}
    for iface in getattr(product, "interfaces", []):
        a, b = iface.between
        partner.setdefault(a, b)
        partner.setdefault(b, a)

    for name, host in hosts.items():
        prog = asm.programs.get(host)
        if prog is None:
            continue
        far = partner.get(name)
        far_host = hosts.get(far, far)
        if far_host in origin and host in origin and far_host != host:
            face = face_toward(origin[host], origin[far_host])
            derived = True
        else:
            face = "+z"
            derived = False
            asm.unresolved.append(
                f"{host}.{name}: no partner position fixed which face it belongs on"
            )
        try:
            kind = PF.FeatureKind(name.rsplit(".", 1)[-1])
        except ValueError:
            kind = PF.FeatureKind.BOSS
        prog.operations.append(FeatureOp(
            name=name, kind=kind, effect=PF.effect_of(kind), on_face=face,
            at=(0.0, 0.0), axis=axes.get(host, "z"),
            serves=far or "", face_derived=derived,
            why=f"carried by {host} to serve {far or 'no declared partner'}",
        ))

    # Parts rigidly joined meet on facing faces; that relation replaces a pair of
    # independently assigned world positions.
    for iface in getattr(product, "interfaces", []):
        a, b = iface.between
        if a not in asm.programs or b not in asm.programs:
            continue
        if iface.kind.value not in ("fixed_attachment", "contact_pair", "sliding_joint"):
            continue
        if a not in origin or b not in origin:
            continue
        fa = face_toward(origin[a], origin[b])
        asm.mates.append(Mate(
            part_a=a, face_a=fa, part_b=b, face_b=("-" if fa[0] == "+" else "+") + fa[1],
            gap=Dim(f"{a}~{b}.gap", 0.0 if iface.kind.value == "fixed_attachment" else None,
                    Unit.MM, "contact" if iface.kind.value == "fixed_attachment" else "undetermined",
                    "a rigid joint closes the gap; a sliding or contact pair needs a clearance"),
            why=f"{iface.kind.value}: {iface.transmits or 'load'}",
        ))

    # Characteristic parameters dimension the feature they belong to, which is what
    # stops a detent from inheriting the size of the box it sits on.
    for subject, (value, quantity, why) in characteristic.items():
        part, pname = subject.rsplit(".", 1)
        prog = asm.programs.get(part)
        if prog is None:
            for owner, p in asm.programs.items():
                if any(o.name == part for o in p.operations):
                    prog = p
                    break
        if prog is None:
            continue
        target = next((o for o in prog.operations if o.name == part), None)
        dim = Dim(subject, value, _unit_for(quantity), "mechanism_principle", why)
        if target is not None:
            target.dims[pname] = dim
        else:
            prog.base_dims[pname] = dim

    return asm
