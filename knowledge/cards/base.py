"""ElementCard abstract interface (MECHSYNTH_SPEC §3.2).

This session declares the card *interface* only — the ports/requires/imposes a card exposes,
and the D18/D21 rule that any card with a functional clearance MUST supply collision_hint().
The knowledge itself (resolve_params, carve, formula_check, verification) is out of scope
(next step); those stay abstract here.

D18/D21 enforcement — the load-bearing part:
  M0 proved that a functional clearance (a hinge bore; a gear-tooth backlash) is destroyed by
  a general mesh collision approximation — CoACD swallowed the bore, and MuJoCo's SDF ships
  only analytic shapes (so `mujoco.sdf.gear` would verify a gear we never designed). The only
  pathway that preserved the clearance was a card-supplied convex decomposition. So: **a card
  that declares has_functional_clearance = True MUST override collision_hint().** This is
  checked at class-definition time (`__init_subclass__`), so it is impossible to register a
  clearance-bearing card that forgets its collision hint — the mistake is caught structurally,
  not at M1 when the gear sim quietly rounds the involute off.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ontology.schema import Behavior, Port


class CollisionHintRequired(TypeError):
    """Raised at class definition when a functional-clearance card omits collision_hint()."""


class ProvidedPiece:
    """A HARDWARE piece an element provides (D-ONT-11): the pin hinge's pin, a fastener, etc. The
    card declares it (name, the params it resolves for it via its own formulas, and the role it
    takes). ④ instantiates it into plan.pieces (provenance='hardware', source_element=<elem>); ⑤
    resolves its params through `resolve_piece_params`; ⑥ compiles it (geometry from the card)."""

    def __init__(self, name: str, params: list[str], role: str):
        self.name, self.params, self.role = name, params, role


class InteractionRule:
    """A card's declaration that it CONTRIBUTES an AssemblyRule (D-ONT-12 provenance c): the
    latch-vs-lid-sweep rule comes from snap_hook's imposes-family knowledge, not thin air. A PARTIAL
    template in card-local terms ('self' = this element); ④ instantiates it into a concrete
    `schema.AssemblyRule` (with element ids) once the assembly's other elements are known. `kind` ∈
    {exclusion, resource}."""

    def __init__(self, kind: str, describe: str, citation: str = ""):
        self.kind, self.describe, self.citation = kind, describe, citation


class ElementCard(ABC):
    """Common base for both card classes (D-ONT-4). Carries the declared interface every card
    exposes to the validators. Two concrete kinds subclass this:

      MechanicalElementCard — REALIZES a behaviour (a hinge, latch, gear). May be referenced by
                              Behavior.realized_by.
      PassiveFeatureCard    — CONSTRAINS or SUPPORTS a behaviour (a stop, boss, rib, guide). May
                              be referenced by Behavior.imposed_by but NEVER realized_by; it
                              realizes nothing (enforced in V-08).

    The split is at the card level because "does this thing realize a DoF, or merely bound one"
    is a knowledge property of the element type, not of any particular instance.
    """

    # is this an active element or a passive feature? Set by the two subclasses; consulted by
    # the validators (a passive feature may not be realized_by; V-08 spans both classes).
    card_class: str = "element"  # "element" | "feature"

    # --- declared interface (data; consumed by validators V-03/V-05/V-08) --------------
    card_id: str = ""
    ports: list["Port"] = []
    param_bounds: dict[str, tuple[float, float, str]] = {}  # name -> (lo, hi, unit)
    requires: dict = {}  # material predicates, e.g. {"eps_allow_pct": (">=", 3.0)}
    imposes: list["Behavior"] = []  # imposed-constraint behaviour templates (V-08)
    provides_pieces: list = []  # D-ONT-11: HARDWARE pieces this element instantiates (e.g. the pin)
    interaction_rules: list = []  # D-ONT-12: AssemblyRule templates this card contributes (provenance)
    selection_notes: str = ""
    citations: list = []

    def resolve_piece_params(self, name: str, inst) -> dict:
        """Resolve a provided hardware piece's params from the element's resolved params (D-ONT-11,
        stage ⑤). Overridden by cards that declare provides_pieces; default = empty."""
        return {}

    # D18/D21: does this card carve a clearance the physics must resolve (bore, groove,
    # tooth flank)? If so, collision_hint() is mandatory (enforced below).
    has_functional_clearance: bool = False

    def __init_subclass__(cls, **kw):
        super().__init_subclass__(**kw)
        # Only enforce on *concrete* cards (those that set a card_id); abstract intermediates
        # are exempt.
        if getattr(cls, "card_id", ""):
            if cls.has_functional_clearance and "collision_hint" not in cls.__dict__:
                raise CollisionHintRequired(
                    f"card '{cls.card_id}' declares has_functional_clearance=True but does not "
                    f"override collision_hint() (D18/D21). A functional clearance destroyed by "
                    f"a generic collision approximation is exactly the M0 failure this rule "
                    f"prevents."
                )

    # --- knowledge (OUT OF SCOPE this session; kept abstract) ---------------------------
    @abstractmethod
    def resolve_params(self, ir, inst) -> dict:
        """Compute unresolved parameters via formulas/rules. NO coordinates (stage 5's job)."""

    @abstractmethod
    def carve(self, host_parts: dict, inst, bindings) -> dict:
        """Carve/attach element geometry into build123d parts (stage 6)."""

    @abstractmethod
    def formula_check(self, inst) -> list:
        """Tier1 recheck (e.g. recompute strain)."""

    @abstractmethod
    def verification(self, ir, inst):
        """Return a VerificationProtocol if use_phase, else None."""

    # collision_hint has a default that REFUSES for clearance-bearing cards, so even a
    # subclass that somehow bypassed __init_subclass__ cannot silently return "no hint".
    def collision_hint(self, inst) -> Optional[list]:
        """Primitive convex collision approximation for STEP→MJCF (§6.2). Required (and thus
        overridden) whenever has_functional_clearance is True — see class docstring."""
        if self.has_functional_clearance:
            raise NotImplementedError(
                f"card '{self.card_id}' must supply collision_hint() (D18/D21)"
            )
        return None


# --------------------------------------------------------------------------------------
# Concrete card INTERFACE stubs — ports/requires/clearance only. No formulas/carve.
#
# These exist so the validators (V-03 ports, V-05 requires, V-08 imposes) have a registry to
# check the golden IRs against, and so the D18/D21 enforcement is exercised by real cards.
# Every knowledge method raises — implementing them is the next session, explicitly.
# --------------------------------------------------------------------------------------
def _p(name, kind):
    from ontology.schema import Port
    return Port(name=name, kind=kind)


def _not_yet(*_a, **_k):
    raise NotImplementedError("card knowledge (formulas/carve) is out of scope this session")


class _StubCard(ElementCard):
    """Shared no-op knowledge bodies so the concrete stubs stay to interface-only."""
    def resolve_params(self, ir, inst) -> dict: _not_yet()
    def carve(self, host_parts, inst, bindings) -> dict: _not_yet()
    def formula_check(self, inst) -> list: _not_yet()
    def verification(self, ir, inst): _not_yet()


class MechanicalElementCard(_StubCard):
    """Active element: realizes a behaviour. Referenceable by Behavior.realized_by."""
    card_class = "element"


class PassiveFeatureCard(_StubCard):
    """Passive feature (D-ONT-4): constrains/supports a behaviour, realizes nothing.
    Referenceable by Behavior.imposed_by, never realized_by (V-08)."""
    card_class = "feature"


def _pin_hinge_imposes() -> list:
    """The pin hinge imposes an assembly-phase constraint: the pin-insertion path must be open
    along the axis (§3.3). Expressed as an assembly/translation behaviour template that V-08
    requires the IR to register and attribute to the hinge."""
    from ontology.schema import Behavior, MotionSpec
    return [Behavior(id="_imposed_insertion_path", phase="assembly",
                     motion=MotionSpec(kind="translation"))]


class PinHingeCard(MechanicalElementCard):
    """Interleaved-knuckle pin hinge (MECHSYNTH §3.3), formalizing M0's proven assets. R1 was
    retired on this geometry (D18: ring-of-wedges preserved the bore where CoACD swallowed it).
    Geometry/derivations live in knowledge/cards/pin_hinge.py (host-agnostic per D-GEN-1).

    NOTE — the pin is a THIRD, separate piece the card cannot yet EMIT (DRAFT D-ONT-11,
    element-generated pieces). carve() adds knuckles/bores/chamfers to the two bound mounts and
    returns the loose pin geometry + dims; the pin is NOT fused into a knuckle (that seizes the
    hinge — the M0 lesson). Until D-ONT-11 is ruled, the caller declares the pin as a plan Piece.
    """
    card_id = "pin_hinge"
    has_functional_clearance = True  # the pin/bore rotational clearance (§3.3)
    ports = [_p("axis", "axis"), _p("mount_A", "face"), _p("mount_B", "face")]
    requires = {}
    imposes = _pin_hinge_imposes()  # §3.3: pin insertion path must be open (V-08)
    param_bounds = {"pin_d": (2.0, 6.0, "mm"), "knuckle_w": (4.0, 12.0, "mm"),
                    "knuckle_n": (3.0, 5.0, "count"), "clearance": (0.2, 0.4, "mm")}
    # D-ONT-11: the hinge PROVIDES the pin as a hardware piece (the third body). ④ instantiates it,
    # ⑤ resolves pin_d/pin_len via the card's formulas, ⑥ compiles it (geometry from carve()).
    provides_pieces = [ProvidedPiece("pin", ["pin_d", "pin_len"], role="pin")]
    # §3.3 placement rules (M0-cited; the derivations in pin_hinge.py enforce them).
    placement_rules = [
        "bore_d = pin_d + clearance  [§3.3: rotational clearance = print clearance]",
        "knuckle_od = pin_d + 2·knuckle_wall  [M0 hinge_box]",
        "lid-edge chamfer length >= pin_d/2 + clearance  [§3.3: pin lead-in]",
        "edge_margin (= face_len/2 − stack_w/2) >= knuckle_w  [§3.3]",
        "knuckle_n ∈ {3,5}; box takes even (outer) knuckles, lid odd (inner)  [M0 interleave]",
        "bore keep-out radius = bore_d/2 + clearance: nothing but knuckles inside it  [M0 D18]",
    ]

    def carve(self, host_parts, inst, bindings):
        """Add interleaved knuckles + shared bore to the two mounts, chamfer the lid, build the loose
        pin (DRAFT D-ONT-11 — no Piece home yet). Delegates to pin_hinge geometry (host-agnostic)."""
        from knowledge.cards.pin_hinge import carve as _carve
        return _carve(host_parts, inst, bindings)

    def collision_hint(self, inst):
        """Card-supplied ring-of-wedges per knuckle (D18/D21): the ONLY pathway that preserved the
        M0 bore (128% retention; CoACD swallowed it). Inner faces circumscribe the bore → never
        pinch the pin."""
        from knowledge.cards.pin_hinge import collision_primitives
        return collision_primitives(inst)

    def resolve_piece_params(self, name, inst) -> dict:
        """D-ONT-11 ⑤: the pin's params from the hinge's own derivations. pin_len = stack_w + 6
        (M0: ~3 mm protrusion each side)."""
        if name != "pin":
            return {}
        from knowledge.cards.pin_hinge import dims_from
        g = dims_from(inst.params, face_len=40.0)  # face_len irrelevant to pin_d/pin_len
        return {"pin_d": round(g.pin_d, 4), "pin_len": round(g.pin_len, 4)}


def _snap_hook_imposes() -> list:
    """The snap hook imposes two constraints (MECHSYNTH §3.4 amended):
      (1) assembly — the hook's insertion path must be open (it must have room to deflect and
          travel to its catch); expressed as an assembly/translation template.
      (2) use — the hook must not defect-interfere with anything outside that path (SNAPFIT §1.3
          B3, §5.2 intentional-vs-defect); expressed as a use/fixed template.
    V-08 requires the IR to register both, attributed to the hook, so neither is silently dropped."""
    from ontology.schema import Behavior, MotionSpec
    return [Behavior(id="_imposed_insertion_path", phase="assembly",
                     motion=MotionSpec(kind="translation")),
            Behavior(id="_imposed_sweep_clearance", phase="use", motion=MotionSpec(kind="fixed"))]


class SnapHookCantileverCard(MechanicalElementCard):
    """Cantilever snap hook (SNAPFIT_STARTER §2 — AUTHORITATIVE for the snap task).

    SNAPFIT §12 A1 overrides the earlier MECHSYNTH §3.4 reading: this card
    has_functional_clearance=True → collision_hint() is REQUIRED. The hook and its catch window
    carry a geometric clearance (the window gap) that a generic CoACD decomposition would swallow
    exactly as it swallowed the M0 bore — so any conversion to MJCF must use card-supplied convex
    approximations of the hook and catch (D18/D21). This is true independently of the fact that
    the *engagement event* itself is verified by formula, not physics (§3.4, D3): the geometry's
    integrity in any downstream sim is a separate concern from which tier scores the event.
    """
    card_id = "snap_hook_cantilever"
    has_functional_clearance = True  # SNAPFIT §12 A1 (supersedes MECHSYNTH §3.4)
    ports = [_p("beam_root", "face"),      # grows from the lid rim underside
             _p("catch_window", "face")]   # window/undercut lip in the box side wall
    requires = {"eps_allow_pct": (">=", 3.0)}  # material must sustain the snap-fit strain
    imposes = _snap_hook_imposes()
    # D-ONT-12: the latch contributes an EXCLUSION AssemblyRule — it must lie outside a rotating
    # host's swept volume (a lid on a pin_hinge). This is where the latch-vs-sweep rule COMES FROM.
    interaction_rules = [InteractionRule(
        "exclusion",
        "self (the latch) must lie OUTSIDE the swept volume of any rotating host it shares a piece "
        "with (e.g. a lid on a pin_hinge) — the M0 B4 lid-sweep clearance",
        citation="MECHSYNTH §5.2 / M0 B4")]
    # SNAPFIT §2.2 param_bounds (bounds carried for V-04/stage-5). Governing FORMULAS now live in
    # knowledge/cards/snap_hook_cantilever.py, verified against Bayer Calc Example I (p.16).
    param_bounds = {"L_mm": (8.0, 25.0, "mm"), "h_mm": (1.2, 4.0, "mm"), "b_mm": (4.0, 12.0, "mm"),
                    "y_mm": (0.8, 2.5, "mm"), "alpha_in_deg": (25.0, 35.0, "deg"),
                    "alpha_out_deg": (30.0, 90.0, "deg"), "root_R_mm": (0.38, 2.0, "mm"),
                    "n_hooks": (2.0, 4.0, "count")}
    # SNAPFIT §2.5 placement rules (Bayer-cited). Not evaluated this session (stage-5 solver is
    # out of scope); carried so the intent is on record and stage 5 has them.
    placement_rules = [
        "root fillet R = clamp(0.5*h, 0.38, 2.0) mm  [Bayer p.8: R >= 0.015 in]",
        "hooks symmetric on opposing side walls (u = 0.5)  [SNAPFIT §2.5]",
        "hook width b <= 1/3 of the anchor face length  [SNAPFIT §2.5]",
        "window-type catch: window width = b + 2*PETG.print_clearance  [SNAPFIT §2.5]",
        "alpha_out <= self_locking_angle(mu) - 10deg  [Bayer p.14/Fig.18 asymptote; D-GEN-2]: "
        "stay clear of the permanent-lock cliff, which mu (A-PETG-1) sits near",
    ]

    def carve(self, host_parts, inst, bindings):
        """Grow hooks into the lid, cut catch windows in the box; return CarveResult with tagged
        separable sub-solids (§5.2). Delegates to snap_hook_geometry (kept out of this file so the
        formulas module stays formulas-only)."""
        from knowledge.cards.snap_hook_geometry import carve as _carve
        return _carve(host_parts, inst, bindings)

    def collision_hint(self, inst):
        """Card-supplied convex approximation (D18/D21): the beam as its own box stack + a nose
        box, so the collision geometry matches the visual at the functional feature and the catch
        clearance survives conversion (CoACD would swallow it — the M0 bore lesson)."""
        from knowledge.cards.snap_hook_geometry import collision_primitives
        return collision_primitives(inst)


class SlideRailCard(MechanicalElementCard):
    card_id = "slide_rail"
    has_functional_clearance = True  # rail/carriage sliding clearance (§3.5)
    ports = [_p("rail_mount", "face"), _p("carriage_mount", "face"), _p("travel_axis", "axis")]

    def collision_hint(self, inst):
        _not_yet()


class RackPinionCard(MechanicalElementCard):
    card_id = "rack_pinion"
    has_functional_clearance = True  # tooth-flank backlash (§3.6, D21)
    ports = [_p("pinion_axis", "axis"), _p("rack_mount", "face"), _p("mesh_line", "edge")]

    def collision_hint(self, inst):
        _not_yet()


# --------------------------------------------------------------------------------------
# PassiveFeature cards (D-ONT-4). These constrain/support; they realize nothing.
# --------------------------------------------------------------------------------------
def _stop_flange_imposes() -> list:
    """The stop_flange's imposed constraint: a use-phase rotation LIMIT on the lid. Expressed
    as a behaviour template (phase + motion kind) that V-08 requires the IR to register. The
    concrete stop angle lives on the instance's params (stop_angle); this template only says
    'a use-phase rotation limit must exist and be attributed to me'."""
    from ontology.schema import Behavior, MotionSpec
    return [Behavior(id="_imposed_rotation_limit", phase="use",
                     motion=MotionSpec(kind="rotation"))]


class StopFlangeCard(PassiveFeatureCard):
    """Thin PassiveFeature: a rearward flange that bottoms out against the base wall to cap the
    lid's travel (the M0 stop variant, D-ONT-4). It CONSTRAINS the hinge's use-phase rotation;
    it does not realize a DoF. No functional clearance (a hard contact stop, not a sliding
    interface), so no collision_hint is required. Formulas (the stop_angle from flange geometry)
    are the next session — this is a shell.

    Its verification contribution: the overtravel observable is PROMOTED to a criterion whenever
    a plan includes the stop — i.e. the plan's P-HINGE gains an 'angle limited' gate. That
    promotion is expressed in the golden IR (tasks/build_goldens.py), which is the honest place
    for it: a criterion exists because a feature is present, and both live in the IR together.
    """
    card_id = "stop_flange"
    has_functional_clearance = False
    ports = [_p("contact", "face")]  # the flange face that lands on the base wall
    param_bounds = {"stop_angle": (0.0, 180.0, "deg"), "stop_flange_r": (2.0, 20.0, "mm")}
    imposes = _stop_flange_imposes()
    selection_notes = ("Use when a hinged lid must not fold past a set angle. Cheapest stop: a "
                       "flange on the moving piece landing on a fixed wall — no added part.")


# card_ref -> card instance. Validators look up ports/requires/imposes/card_class here.
# The deprecated `snap_latch` alias (D-ONT-8) has been REMOVED now that the card has landed and
# MECHSYNTH §3.4/§8.1 are reconciled to `snap_hook_cantilever` (D-ONT-8 resolution).
_ALL_CARDS = (PinHingeCard, SnapHookCantileverCard, SlideRailCard, RackPinionCard, StopFlangeCard)
CARD_REGISTRY: dict[str, ElementCard] = {c.card_id: c() for c in _ALL_CARDS}


def card_ports(card_ref: str) -> list[str]:
    card = CARD_REGISTRY.get(card_ref)
    return [p.name for p in card.ports] if card else []


def is_passive(card_ref: str) -> bool:
    card = CARD_REGISTRY.get(card_ref)
    return bool(card and card.card_class == "feature")
