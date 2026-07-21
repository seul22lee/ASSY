"""coupling element card + geometry (M18 Tier-1; completed to the m19 D-track standard in m20).
One element, one file.

WHICH coupling this models: a RIGID sleeve/clamp coupling — a stiff hub that grips two COAXIAL shaft
ends and transmits rotation 1:1 with no ratio. Being rigid, it does **not** absorb misalignment
(angular / parallel / axial); a shaft train that needs to tolerate misalignment wants a FLEXIBLE
coupling, which is a different future card (a different taxonomy/protocol per D-M20-0b — flexible adds
a compliance axis and a misalignment-capacity protocol this card does not carry).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field  # noqa: F401

from build123d import Align, Box, Cylinder, Location, Pos  # noqa: F401

from knowledge.cards.base import MechanicalElementCard, ProvidedPiece  # noqa: F401
from knowledge.cards.base import _p
from knowledge.cards.carve_utils import _cit_pb
from ontology.schema import Citation, EmergentCheck  # noqa: F401
from knowledge.cards.carve_utils import CarveResult, _add, _anchor_point, _pid

PRINT_CLEARANCE_MM = 0.30   # A-PETG-1 (R5 preset): a slip fit so the shaft inserts into the bore


@dataclass
class CouplingDims:
    bore_d: float = 8.0         # shaft-bore diameter = the shaft diameter it grips (mm)
    body_d: float = 20.0        # coupling hub OD (mm)
    length: float = 24.0        # hub axial length (mm)
    tau_allow: float = 25.0     # allowable shear stress (MPa; PETG conservative, A-PETG-1)


def coupling_dims(p: dict) -> CouplingDims:
    p = p or {}
    return CouplingDims(bore_d=float(p.get("bore_d", 8.0)), body_d=float(p.get("body_d", 20.0)),
                        length=float(p.get("length", 24.0)), tau_allow=float(p.get("tau_allow", 25.0)))


def coupling_mechanics(g: CouplingDims) -> dict:
    """RULE CHAIN (Shigley §3-12 shaft torsion + rigid-coupling hub proportions):

      rated torque      T_rated = τ_allow · π · bore_d³ / 16      (the torque the coupled shaft carries
                                                                   at surface shear τ; capacity is bounded
                                                                   by the smaller BORE shaft, Shigley §3-12)
      hub OD (min)      body_d ≥ 2 · bore_d                       (wall ≥ bore radius to carry the torque
                                                                   through the hub — rigid-coupling proportion)
      hub length (min)  length ≥ 1.5 · bore_d                     (grip/engagement length rule of thumb)
      bore-to-shaft fit bore_d = shaft_d (+ print clearance)      (a slip fit; the shaft inserts, A-PETG-1)
      ratio             = 1.0                                     (a coupling adds NO ratio — input speed
                                                                   = output speed, axis_relationship parallel)

    Reproduced numerically in tests/test_coupling.py against a hand-worked example — if a formula
    assert fails the CODE is wrong, not the arithmetic (the source section is cited above)."""
    T_rated = g.tau_allow * math.pi * (g.bore_d ** 3) / 16.0     # N·mm  (τ in MPa=N/mm², d in mm)
    hub_od_min = 2.0 * g.bore_d
    hub_len_min = 1.5 * g.bore_d
    return {"ratio": 1.0, "torque_capacity_Nmm": round(T_rated, 2),
            "hub_od_min_mm": round(hub_od_min, 2), "hub_len_min_mm": round(hub_len_min, 2),
            "body_d_ok": bool(g.body_d >= hub_od_min - 1e-9),
            "length_ok": bool(g.length >= hub_len_min - 1e-9),
            "bore_fit_clearance_mm": PRINT_CLEARANCE_MM}


# back-compat alias (m18 name)
def coupling_torque(g: CouplingDims) -> dict:
    m = coupling_mechanics(g)
    return {"torque_capacity_Nmm": m["torque_capacity_Nmm"], "ratio": m["ratio"]}


_HUB_OVERLAP_MM = 4.0     # hub bottom sinks this far onto the input stub so the union is ONE solid (D14)
_HUB_SOLID_FLOOR_MM = 10.0  # solid hub floor kept below the blind bore, fusing the hub to the input stub


def coupling_carve(pieces, inst, bindings) -> CarveResult:
    """A RIGID coupling is FUSED to the input shaft and GRIPS the output shaft (the physical picture,
    and the one-solid fix for the D-D-1 'two yellow bodies' lesson — a clearance through-bore would
    leave the hub floating, two solids). So: a hub cylinder (OD body_d) sits on the input-stub top
    (overlapping it so hub∪stub is one solid) with a BLIND clearance bore (bore_d) drilled from the
    TOP — the bottom floor stays solid and fuses to the input shaft; the output shaft inserts into the
    blind bore from above with print clearance. One solid, added to the shaft_in host."""
    g = coupling_dims(getattr(inst, "params", {}) or {})
    x, y, z = _anchor_point(pieces, bindings, "shaft_in")
    bottom = z - _HUB_OVERLAP_MM
    hub = Location(Pos(x, y, bottom)) * Cylinder(radius=g.body_d / 2, height=g.length,
                                                 align=(Align.CENTER, Align.CENTER, Align.MIN))
    bore_depth = max(6.0, g.length - _HUB_SOLID_FLOOR_MM)
    bore_bottom = bottom + g.length - bore_depth
    bore = Location(Pos(x, y, bore_bottom)) * Cylinder(radius=g.bore_d / 2, height=bore_depth + 1.0,
                                                       align=(Align.CENTER, Align.CENTER, Align.MIN))
    body = hub - bore
    return CarveResult(parts=_add(pieces, _pid(bindings, "shaft_in"), body), tags={"coupling": body}, dims=g)


def coupling_collision(inst) -> list:
    """The hub as a coarse cylinder proxy, source-stamped (D-M8-4). Unlike gear teeth / thread flanks,
    the hub↔shaft interface is CONCENTRIC (a cylindrical clamp fit), NOT curved conjugate contact — so
    there is no m17/R2b-class emergent-contact gap to defer (see the card's emergent_check)."""
    g = coupling_dims(getattr(inst, "params", {}) or {})
    return [{"type": "cylinder", "frame": "world", "owner": "coupling",
             "source": f"card:coupling@{getattr(inst,'id','?')}",
             "r": g.body_d / 2.0, "h": g.length,
             "note": "rigid hub; concentric clamp fit (NOT curved contact) -> no V-B curved-contact defer"}]


def _coupling_imposes() -> list:
    """The coupling imposes an ASSEMBLY shaft-insertion path: each shaft is inserted axially into the
    bore, so the shaft axis must stay open for assembly (like lead_screw's threading path, pin_hinge's
    pin path). Registered + attributed to the element (V-08)."""
    from ontology.schema import Behavior, MotionSpec
    return [Behavior(id="_imposed_shaft_insert", phase="assembly",
                     motion=MotionSpec(kind="translation"))]


class CouplingCard(MechanicalElementCard):
    """Rigid shaft coupling (P&B §8.1, Shigley §3-12): transmits rotation 1:1 between two COAXIAL
    shafts, no ratio. The non-tautological content is TORQUE TRANSMISSION UNDER LOAD (declaring 1:1 and
    measuring 1:1 alone verifies nothing) — P-COUPLING V-A drives the input, loads the output with a
    resisting torque SOURCED from the rated-torque formula, and checks the output still tracks and the
    transmitted torque matches. Being rigid, no misalignment absorption (a flexible coupling is a
    separate future card, D-M20-0b)."""
    card_id = "coupling"
    has_functional_clearance = False
    taxonomy = {"working_motion": ("rotation", "regular"), "axis_relationship": "parallel",
                "connection_principle": None, "self_locking": False,
                "emergent_check": EmergentCheck(status="deferred",
                    reason="declared-pair V-A protocol defined (P-COUPLING) but the rig lands in m20 "
                           "Stage 4; a rigid coupling is concentric clamped solids with NO curved-contact "
                           "gap, so once V-A runs this becomes verified (not an R2b defer)",
                    risk="1:1 transmission + torque capacity not yet physics-checked until the m20 rig; "
                         "the hub↔shaft FORCE-closure grip (clamp/set-screw slip) is a preload question "
                         "the transmission rig will not test regardless"),
                "compliance": "rigid", "kinematic_dof": "1 revolute (through-transmitted)"}
    param_bounds = {"bore_d": (4.0, 20.0, "mm"), "body_d": (10.0, 40.0, "mm"),
                    "length": (10.0, 60.0, "mm"), "tau_allow": (10.0, 40.0, "MPa")}
    ports = [_p("shaft_in", "axis"), _p("shaft_out", "axis")]
    imposes = _coupling_imposes()     # §8.1: the assembly shaft-insertion path (V-08)
    selection_notes = (
        "Use to join two COAXIAL shafts and transmit rotation 1:1 (no ratio). axis_relationship="
        "parallel/coaxial (the discriminator vs universal_joint, which joins INTERSECTING axes — "
        "axis-2). RIGID: transmits torque up to T=τ·π·d³/16 (bore shaft) but absorbs NO misalignment; "
        "for angular/parallel misalignment use a flexible coupling (a separate future card, D-M20-0b). "
        "V-A verifies the declared 1:1 pair AND torque transmission under a rated-torque load; there is "
        "no curved-contact V-B (the hub↔shaft fit is concentric, not conjugate).")
    citations = [_cit_pb("§8.1", "connections"),
                 Citation(doc="Shigley's Mechanical Engineering Design", section="§3-12 (shaft torsion)"),
                 Citation(doc="DECISIONS_LOG", section="D-M20-1 (D-track); D-M20-0b (card-vs-param)")]

    def resolve_params(self, ir, inst):
        from knowledge.cards.coupling import coupling_dims, coupling_mechanics
        out = dict(inst.params or {})
        out.setdefault("bore_d", 8.0)
        out.setdefault("tau_allow", 25.0)
        bore = float(out["bore_d"])
        # hub proportions DERIVED from the bore (the card owns the capacity geometry it advertises):
        # body_d ≥ 2·bore, length ≥ 1.5·bore — set defaults then enforce the minimums.
        out.setdefault("body_d", round(max(20.0, 2.0 * bore), 1))
        out.setdefault("length", round(max(24.0, 1.5 * bore), 1))
        out["body_d"] = round(max(float(out["body_d"]), 2.0 * bore), 3)
        out["length"] = round(max(float(out["length"]), 1.5 * bore), 3)
        return out

    def carve(self, host_parts, inst, bindings):
        from knowledge.cards.coupling import coupling_carve
        return coupling_carve(host_parts, inst, bindings)

    def collision_hint(self, inst):
        from knowledge.cards.coupling import coupling_collision
        return coupling_collision(inst)

    def formula_check(self, inst):
        from knowledge.cards.coupling import coupling_dims, coupling_mechanics
        return coupling_mechanics(coupling_dims(getattr(inst, "params", {}) or {}))

    def verification(self, ir, inst):
        from ontology.schema import Criterion, VerificationProtocol
        b = next((x for x in ir.behaviors if x.realized_by == inst.id
                  and getattr(x.phase, "value", x.phase) == "use"
                  and getattr(x.motion.kind, "value", x.motion.kind) == "rotation"), None)
        if b is None:
            return []
        return [VerificationProtocol(
            id=f"P-COUPLING-VA-{inst.id}", verifies=b.id, mode="V-A", seeds=5, seed_pass=4,
            actuation={"kind": "shaft_velocity", "n_rev": 3.0, "ratio_expected": 1.0,
                       "load": "resisting torque on OUTPUT sourced from T_rated (non-tautology: a rigid "
                               "coupling's content is torque transmission, not the trivially-declared 1:1)"},
            criteria=[Criterion(name="transmits_ratio", observable="transmission_residual", op="<=",
                                threshold=0.001, unit=""),
                      Criterion(name="transmits_rated_torque", observable="torque_residual", op="<=",
                                threshold=0.05, unit="")], observables=[])]
