"""Geometry kernel for concept-level mechanism modelling.

Three things the previous representation could not express, and the reason it was
rebuilt rather than repaired:

  * **Shape.** A screw, a lid, a rail and a housing are not the same object. Form
    and function are inseparable: a plate has a normal and four edges per face, a
    shaft has an axis, a shell has a cavity.
  * **Orientation.** A crank turning about a horizontal axis driving a vertical
    screw is the entire spatial content of a right-angle drive. One axis cannot
    say it.
  * **Real transforms.** A hinged plate at 100 degrees is not an axis-aligned box.
    Poses compose; they are not approximated by swapping interval endpoints.

Dimensions carry a **first-cut estimate and its basis**. Stage 04 estimates so it
can test a layout: a spatial contradiction is invisible without magnitudes, and a
drawing to no scale is evidence of nothing. What matters is provenance - a value
propagated from a stated requirement is not the same claim as a placeholder, and
`EstimateBasis` keeps them distinguishable. Stage 05-06 optimises and realises;
what it must not do is mistake a placeholder for a decision.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum


# ---------------------------------------------------------------------------
# symbols
# ---------------------------------------------------------------------------
class EstimateBasis(str, Enum):
    """Where a first-cut magnitude came from. This is its provenance, not its
    accuracy: a value is only as trustworthy as the basis that produced it.
    """

    FROM_REQUIREMENT = "from_requirement"
    """Propagated from a quantitative bound the user stated."""
    PROPORTION_OF = "proportion_of"
    """A ratio to something already sized, e.g. a screw spanning the travel."""
    CLEARANCE_ALLOWANCE = "clearance_allowance"
    """A gap a declared obligation requires."""
    PLACEHOLDER = "placeholder"
    """Genuinely unconstrained. A real guess, and typed as one."""


@dataclass(frozen=True)
class Sym:
    """A dimension with a first-cut estimate and the basis that produced it.

    Stage 04 estimates so that it can *test* a layout rather than only assert
    relations: a spatial contradiction is invisible without magnitudes, and a
    drawing to no scale is evidence of nothing. Stage 05-06 optimises and
    realises; what it must not do is mistake a `PLACEHOLDER` for a decision.
    """

    name: str
    value: float
    basis: "EstimateBasis" = None  # type: ignore[assignment]
    source: str = ""
    kind: str = "length"

    def __post_init__(self) -> None:
        if self.basis is None:
            object.__setattr__(self, "basis", EstimateBasis.PLACEHOLDER)

    @property
    def is_guess(self) -> bool:
        return self.basis is EstimateBasis.PLACEHOLDER

    def __repr__(self) -> str:  # pragma: no cover - display only
        return f"{self.name}={self.value:g}[{self.basis.value}]"


def sym(owner: str, param: str, value: float,
        basis: "EstimateBasis | None" = None, source: str = "",
        kind: str = "length") -> Sym:
    return Sym(f"{owner}.{param}", value, basis or EstimateBasis.PLACEHOLDER,
               source, kind)


# ---------------------------------------------------------------------------
# vectors, rotations, frames
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Vec3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(self, o: "Vec3") -> "Vec3":
        return Vec3(self.x + o.x, self.y + o.y, self.z + o.z)

    def __sub__(self, o: "Vec3") -> "Vec3":
        return Vec3(self.x - o.x, self.y - o.y, self.z - o.z)

    def scaled(self, k: float) -> "Vec3":
        return Vec3(self.x * k, self.y * k, self.z * k)

    def as_tuple(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)


AXES: dict[str, Vec3] = {"x": Vec3(1, 0, 0), "y": Vec3(0, 1, 0), "z": Vec3(0, 0, 1)}


@dataclass(frozen=True)
class Rot:
    """A rotation, stored as a 3x3 matrix of floats.

    Built only from axis-angle about a named product axis, which is all a
    revolute joint, a prismatic guide or a right-angle drive requires.
    """

    m: tuple[tuple[float, float, float], ...] = (
        (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0),
    )

    @staticmethod
    def about(axis: str, radians: float) -> "Rot":
        c, s = math.cos(radians), math.sin(radians)
        if axis == "x":
            return Rot(((1, 0, 0), (0, c, -s), (0, s, c)))
        if axis == "y":
            return Rot(((c, 0, s), (0, 1, 0), (-s, 0, c)))
        return Rot(((c, -s, 0), (s, c, 0), (0, 0, 1)))

    def apply(self, v: Vec3) -> Vec3:
        m = self.m
        return Vec3(
            m[0][0] * v.x + m[0][1] * v.y + m[0][2] * v.z,
            m[1][0] * v.x + m[1][1] * v.y + m[1][2] * v.z,
            m[2][0] * v.x + m[2][1] * v.y + m[2][2] * v.z,
        )

    def then(self, other: "Rot") -> "Rot":
        a, b = other.m, self.m
        return Rot(tuple(
            tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3))
            for i in range(3)
        ))


@dataclass(frozen=True)
class Frame:
    """Position and orientation, relative to a parent frame."""

    origin: Vec3 = Vec3()
    rot: Rot = Rot()

    def compose(self, child: "Frame") -> "Frame":
        return Frame(self.origin + self.rot.apply(child.origin), self.rot.then(child.rot))

    def place(self, local: Vec3) -> Vec3:
        return self.origin + self.rot.apply(local)


# ---------------------------------------------------------------------------
# solids
# ---------------------------------------------------------------------------
class FormClass(str, Enum):
    """What kind of body an element is. Declared by the mechanism family."""

    PLATE = "plate"
    SHAFT = "shaft"
    SHELL = "shell"
    RAIL = "rail"
    COLLAR = "collar"
    BLOCK = "block"
    LINK = "link"
    FLEXIBLE = "flexible"


# Which local axis each form is "long" along, and how its parameters map to a
# local half-extent. Purely a property of the form.
FORM_PARAMS: dict[FormClass, tuple[str, ...]] = {
    FormClass.PLATE: ("length", "width", "thickness"),
    FormClass.SHAFT: ("length", "diameter"),
    FormClass.SHELL: ("length", "width", "height", "wall"),
    FormClass.RAIL: ("length", "section"),
    FormClass.COLLAR: ("length", "bore"),
    FormClass.BLOCK: ("length", "width", "height"),
    FormClass.LINK: ("length", "section"),
    FormClass.FLEXIBLE: ("length", "section"),
}

FACE_NAMES = ("+x", "-x", "+y", "-y", "+z", "-z")


@dataclass
class Solid:
    """A body's form, its symbolic parameters, and its local geometry.

    Local geometry is expressed as half-extents so a face or an edge can be named
    and located. A shell additionally carries a cavity, which is what makes a
    container a container rather than a filled block.
    """

    name: str
    form: FormClass
    params: dict[str, Sym] = field(default_factory=dict)

    @staticmethod
    def of(name: str, form: FormClass, nominal: dict[str, float],
           basis: dict[str, tuple["EstimateBasis", str]] | None = None) -> "Solid":
        basis = basis or {}
        return Solid(
            name=name, form=form,
            params={
                p: sym(name, p, nominal.get(p, 1.0), *basis.get(p, (None, "")))
                for p in FORM_PARAMS[form]
            },
        )

    # -- local extents ----------------------------------------------------
    def half(self) -> Vec3:
        """Half-extent of the bounding box, at nominal. Drawing/indicative only."""
        p = {k: v.value for k, v in self.params.items()}
        f = self.form
        if f is FormClass.PLATE:
            return Vec3(p["length"] / 2, p["width"] / 2, p["thickness"] / 2)
        if f in (FormClass.SHAFT, FormClass.COLLAR):
            d = p.get("diameter", p.get("bore", 0.2))
            return Vec3(d / 2, d / 2, p["length"] / 2)
        if f in (FormClass.SHELL, FormClass.BLOCK):
            return Vec3(p["length"] / 2, p["width"] / 2, p["height"] / 2)
        if f in (FormClass.RAIL, FormClass.LINK, FormClass.FLEXIBLE):
            s = p["section"]
            return Vec3(s / 2, s / 2, p["length"] / 2)
        return Vec3(0.5, 0.5, 0.5)

    def half_terms(self) -> tuple[str, str, str]:
        """The same half-extents as `half()`, but as parameter expressions.

        `half()` answers "how big is this at the current estimate"; this answers
        "which dimensions control that size". A solver needs the second: a spatial
        rule written over body names cannot be solved, because the quantities it
        would have to move are never named in it.
        """
        n = {k: v.name for k, v in self.params.items()}
        f = self.form
        if f is FormClass.PLATE:
            return (f"{n['length']}/2", f"{n['width']}/2", f"{n['thickness']}/2")
        if f in (FormClass.SHAFT, FormClass.COLLAR):
            d = n.get("diameter", n.get("bore", ""))
            return (f"{d}/2", f"{d}/2", f"{n['length']}/2")
        if f in (FormClass.SHELL, FormClass.BLOCK):
            return (f"{n['length']}/2", f"{n['width']}/2", f"{n['height']}/2")
        if f in (FormClass.RAIL, FormClass.LINK, FormClass.FLEXIBLE):
            return (f"{n['section']}/2", f"{n['section']}/2", f"{n['length']}/2")
        return ("0", "0", "0")

    def cavity_half(self) -> Vec3 | None:
        """The void inside a shell. None for solid forms."""
        if self.form is not FormClass.SHELL:
            return None
        h, w = self.half(), self.params["wall"].value
        return Vec3(max(h.x - w, 0.01), max(h.y - w, 0.01), max(h.z - w, 0.01))

    def corners(self) -> list[Vec3]:
        h = self.half()
        return [
            Vec3(sx * h.x, sy * h.y, sz * h.z)
            for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)
        ]

    def face_centre(self, face: str) -> Vec3:
        h = self.half()
        sign = 1.0 if face[0] == "+" else -1.0
        axis = face[1]
        return Vec3(
            sign * h.x if axis == "x" else 0.0,
            sign * h.y if axis == "y" else 0.0,
            sign * h.z if axis == "z" else 0.0,
        )

    def edge_midpoint(self, face: str, edge_axis: str, edge_sign: float) -> Vec3:
        """Midpoint of one edge of a named face.

        A face has four edges; `edge_axis` picks which pair and `edge_sign` which
        of the pair. This is what lets a hinge sit on one edge of an aperture and
        a catch on the opposite one.
        """
        c = self.face_centre(face)
        h = self.half()
        off = Vec3(
            edge_sign * h.x if edge_axis == "x" else 0.0,
            edge_sign * h.y if edge_axis == "y" else 0.0,
            edge_sign * h.z if edge_axis == "z" else 0.0,
        )
        return c + off

    @staticmethod
    def opposite_edge(edge_sign: float) -> float:
        return -edge_sign


def world_corners(solid: Solid, frame: Frame) -> list[Vec3]:
    return [frame.place(c) for c in solid.corners()]


def aabb(points: list[Vec3]) -> tuple[Vec3, Vec3]:
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    zs = [p.z for p in points]
    return Vec3(min(xs), min(ys), min(zs)), Vec3(max(xs), max(ys), max(zs))


def overlaps(a: tuple[Vec3, Vec3], b: tuple[Vec3, Vec3], slack: float = 0.0) -> bool:
    (alo, ahi), (blo, bhi) = a, b
    return (
        alo.x - slack < bhi.x and blo.x - slack < ahi.x
        and alo.y - slack < bhi.y and blo.y - slack < ahi.y
        and alo.z - slack < bhi.z and blo.z - slack < ahi.z
    )
