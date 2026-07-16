"""M0: hand-built snap-... no, *hinged* box. No pipeline, no LLM, no ontology.

The single question M0 answers: does a real printed pin hinge -- interleaved knuckles,
a 0.30 mm print clearance, a separate pin -- still behave like a hinge after it has been
tessellated and dropped into a rigid-body contact solver? (spec R1 / M0)

So the geometry here is deliberately *real*, not a stand-in: the clearances, wall
thicknesses and the chamfer rule all come from the pin_hinge card (spec 3.3) and the PETG
constants (spec 3.1). An idealized hinge would pass the sim and prove nothing.

Frame:  +X = hinge axis,  +Y = front,  +Z = up.  Units mm (converted to m at MJCF time).

Pieces (1 STEP = 1 Piece, per spec 2.2):
    box_shell   walls + floor, open top, box knuckles on lugs behind the rear wall
    lid_panel   flat panel + centre tab carrying the lid knuckle
    hinge_pin   the pin, inserted along +X (this is the 'assembly' behaviour of spec 3.3)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np

from build123d import (
    Align,
    Axis,
    Box,
    Cylinder,
    Location,
    Plane,
    Rotation,
    chamfer,
    export_step,
)

VARIANT = os.environ.get("M0_VARIANT", "nostop")
OUT = Path(__file__).parent / "out" / VARIANT

# --- PETG, spec 3.1 -------------------------------------------------------------------
PRINT_CLEARANCE = 0.30  # mm
MIN_WALL = 1.2  # mm
DENSITY = 1270.0  # kg/m^3


@dataclass(frozen=True)
class HingeBox:
    """Every number here is a card parameter or derived from one. Nothing is a magic
    constant -- that is the point of the exercise (spec 3.1 gate G3.1)."""

    # box_shell / lid_panel host template params
    box_l: float = 80.0  # X
    box_w: float = 60.0  # Y
    box_h: float = 40.0  # Z
    wall: float = 2.0  # >= MIN_WALL
    lid_t: float = 3.0

    # pin_hinge card params (spec 3.3 bounds in comments)
    pin_d: float = 4.0  # [2, 6]
    knuckle_w: float = 8.0  # [4, 12]
    knuckle_n: int = 3  # {3, 5}
    knuckle_wall: float = 2.0  # -> knuckle OD = pin_d + 2*knuckle_wall = 8.0
    clearance: float = PRINT_CLEARANCE  # [0.2, 0.4]
    # Rearward flange on the lid -> end stop. ZERO in the baseline: the Easy anchor's
    # behaviour spec (spec 8.1) never asks for an angular limit, so adding one here would be
    # smuggling a design decision in under cover of a bug fix. The baseline is built exactly
    # as specified and the missing stop is *reported as an observable* (see vb.py
    # overtravel_check). The `stop` variant exists to show what a stop would buy, so the
    # intent layer can decide with evidence.
    stop_flange_r: float = 8.0 if VARIANT == "stop" else 0.0

    # ---- derived -----------------------------------------------------------------
    @property
    def knuckle_od(self) -> float:
        return self.pin_d + 2 * self.knuckle_wall

    @property
    def knuckle_r(self) -> float:
        return self.knuckle_od / 2

    @property
    def bore_d(self) -> float:
        """Rotational clearance = PETG print clearance (spec 3.3)."""
        return self.pin_d + self.clearance

    @property
    def axis_y(self) -> float:
        """Hinge axis sits behind the rear wall, tangent to its outer face, so the
        knuckles never intrude into the lid panel's footprint."""
        return -self.box_w / 2 - self.knuckle_r

    @property
    def axis_z(self) -> float:
        """At lid mid-thickness, so the closed lid's rear edge pivots off the rim."""
        return self.box_h + self.lid_t / 2

    @property
    def stack_w(self) -> float:
        """Total axial width of the knuckle stack incl. the axial clearance gaps."""
        return self.knuckle_n * self.knuckle_w + (self.knuckle_n - 1) * self.clearance

    @property
    def lid_rear_y(self) -> float:
        """The lid is cut back so the box knuckles clear it by exactly one print
        clearance. Without this the knuckles and the panel occupy the same Z band and
        the assembly is un-printable (and un-simulatable)."""
        return self.axis_y + self.knuckle_r + self.clearance

    @property
    def chamfer_len(self) -> float:
        """pin_hinge rule: lid edge chamfer >= pin_d/2 + clearance (spec 3.3)."""
        return self.pin_d / 2 + self.clearance

    @property
    def pin_len(self) -> float:
        return self.stack_w + 6.0  # protrudes ~3 mm each side for insertion/extraction

    @property
    def stop_angle_deg(self) -> float:
        """Where the end stop engages.

        The lid needs one. Without it this hinge is *over-centre*: past 90 deg gravity pulls
        the lid further open rather than shut, so it flops right over and lands on whatever
        is behind the box. V-A hid this -- MuJoCo's joint `range` acted as a stop the part
        does not physically have -- and V-B, which declares no joints, exposed it by spinning
        the lid through 223 deg into the floor.

        The fix needs no new part: a flange on the lid extending *rearward* of the axis
        swings down as the lid opens and lands flat against the box's own rear wall. The
        stop angle is where the flange's rear-bottom corner first reaches the plane of that
        wall. Solved by scan rather than in closed form -- the closed form has a branch
        ambiguity that silently returns the wrong root.
        """
        if self.stop_flange_r <= 0:
            return float("inf")  # no stop: the lid is free to fold flat. That is the finding.
        dy, dz = -self.stop_flange_r, -self.lid_t / 2  # rear-bottom corner, rel. axis
        y_wall = -self.box_w / 2 - self.axis_y  # wall plane, rel. axis
        for deg in np.arange(0.0, 180.0, 0.05):
            t = np.radians(deg)
            if dy * np.cos(t) - dz * np.sin(t) >= y_wall:
                return float(deg)
        return 180.0

    @property
    def bore_keepout_r(self) -> float:
        """Nothing but the knuckles may enter this radius about the axis, or the pin has
        no through-path and the card's 'assembly' constraint (spec 3.3) is violated."""
        return self.bore_d / 2 + self.clearance

    @property
    def lug_top_z(self) -> float:
        """Box lugs approach the knuckles from below, stopping clear of the bore."""
        return self.axis_z - self.bore_keepout_r

    @property
    def tab_rear_y(self) -> float:
        """Lid tabs approach the knuckles from the front, stopping clear of the bore."""
        return self.axis_y + self.bore_keepout_r

    @property
    def edge_margin(self) -> float:
        """Rule: edge_margin >= knuckle_w (spec 3.3)."""
        return self.box_l / 2 - self.stack_w / 2

    def knuckle_spans(self) -> list[tuple[float, float, str]]:
        """Interleave along X: box takes the outer knuckles, lid the inner ones."""
        spans = []
        x = -self.stack_w / 2
        for i in range(self.knuckle_n):
            owner = "box" if i % 2 == 0 else "lid"
            spans.append((x, x + self.knuckle_w, owner))
            x += self.knuckle_w + self.clearance
        return spans

    def check_rules(self) -> list[str]:
        """The card's own rules, checked before we ever build. A violation here is a
        design error, not a sim failure -- catch it at the cheapest possible moment."""
        v = []
        if not 2.0 <= self.pin_d <= 6.0:
            v.append(f"pin_d {self.pin_d} outside [2,6]")
        if not 4.0 <= self.knuckle_w <= 12.0:
            v.append(f"knuckle_w {self.knuckle_w} outside [4,12]")
        if self.knuckle_n not in (3, 5):
            v.append(f"knuckle_n {self.knuckle_n} not in {{3,5}}")
        if not 0.2 <= self.clearance <= 0.4:
            v.append(f"clearance {self.clearance} outside [0.2,0.4]")
        if self.edge_margin < self.knuckle_w:
            v.append(f"edge_margin {self.edge_margin:.1f} < knuckle_w {self.knuckle_w}")
        if self.wall < MIN_WALL:
            v.append(f"wall {self.wall} < print_min_wall {MIN_WALL}")
        if self.knuckle_wall < MIN_WALL:
            v.append(f"knuckle_wall {self.knuckle_wall} < print_min_wall {MIN_WALL}")
        return v


def _knuckle_outer(p: HingeBox, x0: float, x1: float):
    """One knuckle body, unbored. The bore is cut once, from the finished part, so that
    it also clears any lug/tab material it passes through."""
    w = x1 - x0
    loc = Location((x0 + w / 2, p.axis_y, p.axis_z))
    # Cylinder's axis is +Z by default; rotate onto +X.
    return loc * Rotation(0, 90, 0) * Cylinder(radius=p.knuckle_r, height=w)


def _bore(p: HingeBox):
    """The pin's through-path, as one cylinder spanning the whole part."""
    return (
        Location((0, p.axis_y, p.axis_z))
        * Rotation(0, 90, 0)
        * Cylinder(radius=p.bore_d / 2, height=p.box_l)
    )


def build_box_shell(p: HingeBox):
    shell = Box(p.box_l, p.box_w, p.box_h, align=(Align.CENTER, Align.CENTER, Align.MIN))
    cavity = Location((0, 0, p.wall)) * Box(
        p.box_l - 2 * p.wall,
        p.box_w - 2 * p.wall,
        p.box_h,  # runs past the top face -> open top
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    part = shell - cavity

    # Lugs carry the knuckles up from the rear wall. They stop below the bore keep-out and
    # reach forward into the wall (not merely up to its face) so the union is a real fuse.
    lug_y0, lug_y1 = p.axis_y, -p.box_w / 2 + p.wall
    lug_z0, lug_z1 = p.lug_top_z - 5.0, p.lug_top_z
    for x0, x1, owner in p.knuckle_spans():
        if owner != "box":
            continue
        part += Location(((x0 + x1) / 2, (lug_y0 + lug_y1) / 2, (lug_z0 + lug_z1) / 2)) * Box(
            x1 - x0, lug_y1 - lug_y0, lug_z1 - lug_z0
        )
        part += _knuckle_outer(p, x0, x1)
    return part - _bore(p)


def build_lid_panel(p: HingeBox):
    lid_y0, lid_y1 = p.lid_rear_y, p.box_w / 2
    panel = Location((0, (lid_y0 + lid_y1) / 2, p.box_h)) * Box(
        p.box_l, lid_y1 - lid_y0, p.lid_t, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )
    # Chamfer the rear underside edge -- the edge that sweeps closest to the box rim.
    rear_bottom = (
        panel.edges()
        .filter_by(Axis.X)
        .filter_by_position(Axis.Z, p.box_h - 0.01, p.box_h + 0.01)
        .sort_by(Axis.Y)[0]
    )
    part = chamfer(rear_bottom, length=p.chamfer_len)

    # Tabs bridge the panel to the lid knuckles, approaching from the front and stopping
    # clear of the bore keep-out. They overlap the panel by 3 mm to fuse properly.
    tab_y0, tab_y1 = p.tab_rear_y, lid_y0 + 3.0
    # Stop flange: extends rearward of the axis, swings down as the lid opens, and bottoms
    # out against the box's rear wall (see HingeBox.stop_angle_deg). It starts 3 mm short of
    # the axis so it fuses into the knuckle without entering the bore keep-out.
    for x0, x1, owner in p.knuckle_spans():
        if owner != "lid":
            continue
        part += Location(((x0 + x1) / 2, (tab_y0 + tab_y1) / 2, p.box_h)) * Box(
            x1 - x0, tab_y1 - tab_y0, p.lid_t, align=(Align.CENTER, Align.CENTER, Align.MIN)
        )
        if p.stop_flange_r > 0:
            f_y0, f_y1 = p.axis_y - p.stop_flange_r, p.axis_y - 3.0
            part += Location(((x0 + x1) / 2, (f_y0 + f_y1) / 2, p.box_h)) * Box(
                x1 - x0, f_y1 - f_y0, p.lid_t, align=(Align.CENTER, Align.CENTER, Align.MIN)
            )
        part += _knuckle_outer(p, x0, x1)
    return part - _bore(p)


def build_hinge_pin(p: HingeBox):
    return (
        Location((0, p.axis_y, p.axis_z))
        * Rotation(0, 90, 0)
        * Cylinder(radius=p.pin_d / 2, height=p.pin_len)
    )


def main() -> None:
    p = HingeBox()
    violations = p.check_rules()
    if violations:
        raise SystemExit("pin_hinge card rule violations:\n  " + "\n  ".join(violations))

    OUT.mkdir(parents=True, exist_ok=True)
    parts = {
        "box_shell": build_box_shell(p),
        "lid_panel": build_lid_panel(p),
        "hinge_pin": build_hinge_pin(p),
    }

    manifest = {
        "params": asdict(p),
        "derived": {
            "knuckle_od": p.knuckle_od,
            "bore_d": p.bore_d,
            "stack_w": p.stack_w,
            "edge_margin": p.edge_margin,
            "chamfer_len": p.chamfer_len,
            "pin_len": p.pin_len,
            "lid_rear_y": p.lid_rear_y,
            "bore_keepout_r": p.bore_keepout_r,
            "lug_top_z": p.lug_top_z,
            "tab_rear_y": p.tab_rear_y,
            "stop_flange_r": p.stop_flange_r,
            "stop_angle_deg": round(p.stop_angle_deg, 2),
        },
        # The hinge axis is the one thing the physics layer must know and cannot infer
        # from a mesh. In the real pipeline this comes from the Binding (spec 2.2).
        "hinge_axis": {"point_mm": [0.0, p.axis_y, p.axis_z], "dir": [1.0, 0.0, 0.0]},
        "knuckles": [
            {"x0": x0, "x1": x1, "owner": o} for x0, x1, o in p.knuckle_spans()
        ],
        "pieces": {},
    }

    for name, part in parts.items():
        step = OUT / f"{name}.step"
        export_step(part, str(step))
        vol_mm3 = part.volume
        manifest["pieces"][name] = {
            "step": step.name,
            "volume_mm3": round(vol_mm3, 3),
            "mass_kg": round(vol_mm3 * 1e-9 * DENSITY, 6),
            "bbox_mm": [round(v, 3) for v in (*part.bounding_box().min, *part.bounding_box().max)],
        }
        print(f"{name:11s} vol {vol_mm3:9.1f} mm^3   mass {vol_mm3*1e-9*DENSITY*1000:6.1f} g   -> {step.name}")

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"\nhinge axis  y={p.axis_y:.2f}  z={p.axis_z:.2f}   bore {p.bore_d} / pin {p.pin_d}"
          f"  (radial clearance {(p.bore_d - p.pin_d)/2:.3f} mm)")
    print(f"knuckles    {[f'{o}[{x0:.1f},{x1:.1f}]' for x0, x1, o in p.knuckle_spans()]}")
    print(f"wrote       {OUT/'manifest.json'}")


if __name__ == "__main__":
    main()
