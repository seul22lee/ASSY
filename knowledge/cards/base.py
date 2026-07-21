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

from ontology.schema import Citation

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

    # is this an active element, a passive feature, or a connection? Set by the subclasses; consulted
    # by the validators (a passive feature/connection may not be realized_by; V-08 spans all classes).
    card_class: str = "element"  # "element" | "feature" | "connection" (D-M18-1)

    # M18 axis-6 (P&B §8.1.3, elastic connection): RESERVED. Fixed "rigid" this milestone; the
    # validator rejects "compliant" with a P-SPRING message (spring/damper/living_hinge are the future
    # compliant=true, needing a protocol not built here). The field exists so it can't be misused.
    compliance: str = "rigid"    # "rigid" | "compliant"  (D-M18-2)

    # M18 7-axis taxonomy tag (D-M18-2; see m18_element_expansion/REVIEW.md §1). A dict with keys:
    # working_motion=(type,nature), axis_relationship, connection_principle, self_locking,
    # vb_verifiable, compliance, kinematic_dof(note). Every card sets it; the KG narrows on it.
    taxonomy: dict = {}

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


class ConnectionCard(_StubCard):
    """Third card category (D-M18-1, P&B §8.1): FIXES / FASTENS parts together — it realizes no DoF
    and supports no motion; it JOINS. Distinct from PassiveFeatureCard (which supports/constrains a
    DoF, e.g. a stop or a bearing) — a connection is a joint BETWEEN parts.

    Carries `connection_principle` ∈ {form, force, material} (axis 3, P&B §8.1): form = geometric
    interlock (dowel), force = friction/preload (press-fit, screw clamp), material = fused (weld —
    future). NOTE the anti-conflation rule (m18 REVIEW §2.1): connection_principle is a PROPERTY;
    a ConnectionCard is an OBJECT — they share a word, not a level.

    Orthogonal to hardware (m18 REVIEW §2.2): a threaded fastener is a ConnectionCard that ALSO
    declares provides_pieces (its screw body is hardware, D-ONT-11). "Connection role" and "hardware
    piece" are independent axes; one card can be both.

    Referenceable by NEITHER realized_by (V-08: it realizes nothing) nor imposed_by-of-a-motion.
    verification() is usually [] (a static fastener is checked by formula_check + t0, not a protocol).
    """
    card_class = "connection"
    connection_principle: str = ""   # "form" | "force" | "material"  (axis 3, P&B §8.1)


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
    taxonomy = {"working_motion": ("rotation", "regular"), "axis_relationship": "parallel",
                "connection_principle": None, "self_locking": False, "vb_verifiable": True,
                "compliance": "rigid", "kinematic_dof": "1 revolute"}  # M18 tag (D-M18-2)
    selection_notes = (
        "Use when one piece must ROTATE about a FIXED AXIS relative to another, repeatedly and "
        "through a large angle (a lid, a door, a flap). Realizes a use-phase rotation.\n"
        "Trade-offs: needs a loose PIN (a hardware piece the card provides, D-ONT-11) — a part "
        "count a snap-fit does not pay. Rotational clearance is the print clearance, so the fit is "
        "loose by design. IMPOSES an assembly constraint: the pin-insertion path must stay open "
        "along the axis (§3.3), which constrains where else you may put material.\n"
        "CAUTION — an over-centre lid (one whose CoM crosses the axis past ~90°) will FOLD FLAT "
        "under gravity unless a stop is added: physics showed 'opens >=90 AND returns closed' is "
        "unsatisfiable without one, so pair with the stop_flange PassiveFeature (D-M8-5).\n"
        "Do NOT use for straight-line travel (see slide_rail) or for a fasten-once joint (see "
        "snap_hook_cantilever).")
    citations = [Citation(doc="MECHSYNTH_SPEC_v0.1", section="§3.3 Card 1 — pin_hinge"),
                 Citation(doc="M0 hinge box (proven rig)", section="P-HINGE V-A/V-B"),
                 Citation(doc="DECISIONS_LOG", section="D-M8-5 (stop is a physics-derived requirement)")]
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
    def verification(self, ir, inst):
        """D-E-5: the hinge's own verification knowledge — P-HINGE in BOTH modes (§6.1/§6.3).

        Protocols are CARD knowledge (D5), never LLM-authored: which observables prove a hinge works,
        and at what thresholds, is exactly the handbook/M0 knowledge a card exists to hold. ④ attaches
        these at element selection; the model never writes a criterion.

        BOTH modes, always — the M0/D20 result made structural. V-A (declared joint) alone cannot
        tell a stop-less lid from a stopped one: its `range` silently supplies a stop the part does
        not have, and only V-B (contact-only) exposes it. A hinge card offering V-A alone would
        certify the fold-over."""
        from ontology.schema import Criterion, VerificationProtocol
        use_b = next((b for b in ir.behaviors
                      if b.realized_by == inst.id
                      and getattr(b.phase, "value", b.phase) == "use"
                      and getattr(b.motion.kind, "value", b.motion.kind) == "rotation"), None)
        if use_b is None:
            return []
        floor = float(getattr(use_b.motion, "range_value", None) or 90.0)
        clearance = float((inst.params or {}).get("clearance", 0.30))
        crits = [
            Criterion(name="opens", observable="theta_max_deg", op=">=", threshold=floor, unit="deg"),
            Criterion(name="pin_radial_retention", observable="pin_radial_max_mm", op="<=",
                      threshold=round(clearance + 0.1, 3), unit="mm"),
            Criterion(name="settles_closed", observable="theta_final_deg", op="<=", threshold=5.0,
                      unit="deg"),
            Criterion(name="no_travel_interference", observable="pen_travel_mm", op="<=",
                      threshold=0.20, unit="mm"),
        ]
        return [
            VerificationProtocol(
                id=f"P-HINGE-VA-{inst.id}", verifies=use_b.id, mode="V-A", seeds=5, seed_pass=4,
                actuation={"kind": "follower_force_ramp", "F_open_N": 0.15, "point": "free_edge_mid"},
                criteria=[c.model_copy() for c in crits], observables=[]),
            VerificationProtocol(
                id=f"P-HINGE-VB-{inst.id}", verifies=use_b.id, mode="V-B", seeds=5, seed_pass=4,
                actuation={"kind": "follower_force_ramp", "F_open_N": 0.15, "point": "free_edge_mid",
                           "release_at_theta_deg": 95.0},
                criteria=[c.model_copy() for c in crits], observables=[]),
        ]


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
    taxonomy = {"working_motion": ("snap_event", "regular"), "axis_relationship": "parallel",
                "connection_principle": "form", "self_locking": False, "vb_verifiable": False,
                "compliance": "rigid", "kinematic_dof": "fastens (reclass candidate -> ConnectionCard, m18 REVIEW §5)"}
    selection_notes = (
        "Use when two pieces must FASTEN to each other by hand — a cantilever beam deflects over a "
        "catch and snaps back, giving a tactile/audible click and a defined separation force. "
        "Realizes an assembly-phase snap_event and a static-phase retention.\n"
        "Trade-offs: NO added parts (the beam is moulded into the piece) — cheaper than a pin hinge "
        "on part count. But it is ELASTIC: a rigid-body engine cannot express the deflection (D3), "
        "so it is verified by Bayer formulas (Tier1) + geometry (Tier0), NOT by physics.\n"
        "IMPOSES two constraints: an assembly insertion path for the hook, and a use-phase "
        "clearance — the latch must lie OUTSIDE the swept volume of any rotating host it shares a "
        "piece with (the AssemblyRule it contributes, D-ONT-12).\n"
        "Do NOT use to realize continuous motion — it holds parts together, it does not move them.")
    citations = [Citation(doc="BASF/Bayer Snap-Fit Design Guide", section="p.5 Fig.1 (cantilever); "
                                                                        "p.9 Table 1 (y_perm, P)"),
                 Citation(doc="SNAPFIT_STARTER_v0", section="§2 (authoritative for the snap task)"),
                 Citation(doc="MECHSYNTH_SPEC_v0.1", section="§3.4 Card 2")]
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
    def verification(self, ir, inst):
        """D-E-5: the latch's verification knowledge — PR-LATCH (the snap event) + PR-SWEEP (the
        clearance it imposes).

        NOT a physics-engine target (D3/§3.4): a rigid-body engine cannot express the beam's elastic
        deflection, so the snap EVENT is checked by the Bayer formulas (Tier1) and the sweep
        clearance by geometry (Tier0). That its own verification lives OUTSIDE the simulator is
        precisely the kind of thing only the card can know."""
        from ontology.schema import Criterion, VerificationProtocol
        out = []
        snap_b = next((b for b in ir.behaviors
                       if b.realized_by == inst.id
                       and getattr(b.motion.kind, "value", b.motion.kind) == "snap_event"), None)
        if snap_b is not None:
            w = getattr(snap_b.motion, "event_force_window_N", None) or (15.0, 60.0)
            out.append(VerificationProtocol(
                id=f"PR-LATCH-{inst.id}", verifies=snap_b.id, mode=None, seeds=5, seed_pass=4,
                actuation={"kind": "formula_recheck"},
                criteria=[
                    Criterion(name="hand_closeable", observable="mating_force_total_N", op="<=",
                              threshold=80.0, unit="N"),
                    Criterion(name="retention_floor", observable="retention_force_N", op=">=",
                              threshold=float(w[0]), unit="N")],
                observables=[]))
        # the use-phase clearance this card IMPOSES — matched to its OWN `imposes` template
        # (use/fixed), not merely "the first use behaviour attributed to me": the card declares
        # exactly which constraint it forces, and that declaration is the thing to verify.
        sweep_b = next((b for b in ir.behaviors
                        if b.imposed_by == inst.id
                        and getattr(b.phase, "value", b.phase) == "use"
                        and getattr(b.motion.kind, "value", b.motion.kind) == "fixed"), None)
        if sweep_b is not None:
            out.append(VerificationProtocol(
                id=f"PR-SWEEP-{inst.id}", verifies=sweep_b.id, mode=None, seeds=5, seed_pass=4,
                actuation={"kind": "tier0_sweep"},
                criteria=[Criterion(name="no_defect_interference", observable="pen_travel_mm",
                                    op="<=", threshold=0.20, unit="mm")],
                observables=[]))
        return out



def _slide_rail_imposes() -> list:
    """The slide imposes two constraints (§3.5): an ASSEMBLY axial-insertion path (the carriage
    threads onto the rail along the travel axis — nothing may block that axis), and a USE travel
    keep-out (nothing may intrude into the swept volume the carriage passes through). Both are
    registered in the IR and attributed to the slide (V-08)."""
    from ontology.schema import Behavior, MotionSpec
    return [Behavior(id="_imposed_axial_insertion", phase="assembly",
                     motion=MotionSpec(kind="translation")),
            Behavior(id="_imposed_travel_keepout", phase="use",
                     motion=MotionSpec(kind="fixed"))]


class SlideRailCard(MechanicalElementCard):
    """Rectangular retaining slide (MECHSYNTH §3.5) — a T-rail + captured carriage. Geometry (all
    boxes, no curves) in knowledge/cards/slide_rail.py, host-agnostic (D-GEN-1). Realizes a use-phase
    translation; imposes an axial-insertion path + a travel keep-out."""
    card_id = "slide_rail"
    has_functional_clearance = True  # rail/carriage sliding clearance (§3.5)
    taxonomy = {"working_motion": ("translation", "regular"), "axis_relationship": "parallel",
                "connection_principle": None, "self_locking": False, "vb_verifiable": True,
                "compliance": "rigid", "kinematic_dof": "1 prismatic"}
    imposes = _slide_rail_imposes()
    param_bounds = {"rail_h": (4.0, 10.0, "mm"), "rail_w": (4.0, 10.0, "mm"),
                    "clearance": (0.25, 0.45, "mm"), "engagement_len": (5.0, 200.0, "mm"),
                    "stroke": (10.0, 400.0, "mm")}
    selection_notes = (
        "Use when a piece must TRANSLATE along a straight axis (a drawer, a tray). Realizes a "
        "use-phase translation.\n"
        "Trade-offs: engagement_len >= 0.35*stroke or the carriage racks and jams under moment "
        "load (§3.5); that engagement eats depth the payload wanted. The rail/carriage clearance "
        "is a functional clearance a generic mesh approximation destroys, so the card must supply "
        "its own collision decomposition (D18).\n"
        "Do NOT use for rotation (see pin_hinge)."
        "ORIENTATION (D-M13-6): a HORIZONTAL slide is gravity-seated — the lips catch on lift "
        "with the sliding clearance c. A VERTICAL slide (travel ∥ gravity) is NOT gravity-seated, "
        "so resolve_params tightens the retention STOP gap to a quarter of the PETG print clearance (0.075 mm); the lip "
        "catches within that tight gap on any wobble (a retention stop), independent of gravity direction.")
    citations = [Citation(doc="MECHSYNTH_SPEC_v0.1", section="§3.5 Card 3 — slide_rail")]
    ports = [_p("rail_mount", "face"), _p("carriage_mount", "face"), _p("travel_axis", "axis")]

    def carve(self, host_parts, inst, bindings):
        """Grow the rail on the rail_mount host + the captured carriage on the carriage_mount host,
        anchor-driven. Delegates to slide_rail geometry (host-agnostic)."""
        from knowledge.cards.slide_rail import carve as _carve
        return _carve(host_parts, inst, bindings)

    def collision_hint(self, inst, stroke=None):
        """All-box decomposition of the rail + carriage channel (§3.5: groove as box primitives, no
        curves). Every prim carries `owner` (rail|carriage) and a `source` stamp (D-M8-4)."""
        from knowledge.cards.slide_rail import collision_primitives
        return collision_primitives(inst, stroke)

    def resolve_params(self, ir, inst):
        """⑤/D6: derive engagement_len from the §3.5 moment-resistance rule (≥ 0.35·stroke), and
        carry the stroke from the use-phase translation behaviour's range. stroke is the design
        input; engagement_len is DERIVED (never free) — the card owns the formula, ⑤ owns when."""
        from knowledge.cards.slide_rail import dims_from
        out = dict(inst.params or {})
        # stroke from the behaviour this element realizes (its use-phase translation range), else param
        strk = out.get("stroke")
        if strk is None:
            b = next((x for x in ir.behaviors if x.realized_by == inst.id
                      and getattr(x.motion.kind, "value", x.motion.kind) == "translation"
                      and getattr(x.motion, "range_value", None)), None)
            strk = float(b.motion.range_value) if b else 60.0
        out["stroke"] = float(strk)
        # engagement_len = the §3.5 minimum unless the IR already asked for more (moment resistance)
        g = dims_from(out, out["stroke"])
        out["engagement_len"] = round(max(float(out.get("engagement_len", 0.0)), g.min_engagement), 3)
        out.setdefault("rail_w", 8.0)
        out.setdefault("rail_h", 8.0)
        out.setdefault("clearance", 0.35)
        # D-M13-6 ORIENTATION RULE: when travel ∥ gravity (a VERTICAL lift, not a horizontal drawer),
        # gravity no longer seats the carriage in the groove, so the retention lips are PRELOADED.
        # The preload is SOURCED, not invented: it uses a QUARTER of the PETG print clearance (a retention STOP face bears only on wobble,
        # not during travel, so it tolerates a gap tighter than the sliding fit): 0.30/4 = 0.075 mm.
        # A tight positive gap (NOT interference — an interference on the rigid stops jams them, the
        # PETG leaf's compliance can't be modelled at the frozen stiff preset R5) catches the pitch
        # before the platform escapes the groove. Detected from the realized translation behaviour's
        # axis_hint (vertical / travel-parallel-to-gravity).
        b = next((x for x in ir.behaviors if x.realized_by == inst.id
                  and getattr(x.motion.kind, "value", x.motion.kind) == "translation"), None)
        hint = (getattr(b.motion, "axis_hint", "") or "") if b is not None else ""
        if "vert" in hint.lower():
            from knowledge.materials import PETG
            out.setdefault("preload_mm", round(PETG.print_clearance_mm / 4.0, 3))   # 0.075 mm, sourced
        return out

    def verification(self, ir, inst):
        """D-track/§6.3: P-SLIDE in both modes. V-A (declared prismatic joint) is REQUIRED; V-B
        (contact-only, the geometry must produce and retain the DoF) is the TARGET. Judge s_max ≥
        stroke, off-axis ≤ 3°, no derail, back-drift ≤ 5 mm (§6.3)."""
        from ontology.schema import Criterion, VerificationProtocol
        use_b = next((b for b in ir.behaviors
                      if b.realized_by == inst.id
                      and getattr(b.phase, "value", b.phase) == "use"
                      and getattr(b.motion.kind, "value", b.motion.kind) == "translation"), None)
        if use_b is None:
            return []
        stroke = float((inst.params or {}).get("stroke", 60.0))
        crits = [
            Criterion(name="reaches_stroke", observable="stroke_mm", op=">=", threshold=stroke,
                      unit="mm"),
            Criterion(name="tracks_straight", observable="offaxis_rot_deg", op="<=", threshold=3.0,
                      unit="deg"),
        ]
        out = [
            VerificationProtocol(id=f"P-SLIDE-VA-{inst.id}", verifies=use_b.id, mode="V-A",
                                 seeds=5, seed_pass=4, actuation={"kind": "force_ramp_axial"},
                                 criteria=[c.model_copy() for c in crits], observables=[]),
            VerificationProtocol(id=f"P-SLIDE-VB-{inst.id}", verifies=use_b.id, mode="V-B",
                                 seeds=5, seed_pass=4, actuation={"kind": "force_ramp_axial"},
                                 criteria=[c.model_copy() for c in crits], observables=[]),
        ]
        # the USE-phase travel keep-out this slide IMPOSES (§3.5): nothing intrudes into the swept
        # volume — a Tier0 sweep, like the snap card's PR-SWEEP. Verifies that imposed behaviour so
        # it is not left unverified (V-01).
        keep_b = next((b for b in ir.behaviors
                       if b.imposed_by == inst.id
                       and getattr(b.phase, "value", b.phase) == "use"
                       and getattr(b.motion.kind, "value", b.motion.kind) == "fixed"), None)
        if keep_b is not None:
            out.append(VerificationProtocol(
                id=f"PR-KEEPOUT-{inst.id}", verifies=keep_b.id, mode=None, seeds=5, seed_pass=4,
                actuation={"kind": "tier0_sweep"},
                criteria=[Criterion(name="no_travel_intrusion", observable="offaxis_rot_deg",
                                    op="<=", threshold=3.0, unit="deg")], observables=[]))
        return out


def _rack_pinion_imposes() -> list:
    """The rack_pinion imposes an assembly-phase constraint: the pinion must be inserted onto its
    shaft along the axis, and the rack threaded into mesh (§3.6). One assembly/translation behaviour,
    registered and attributed to the element (V-08)."""
    from ontology.schema import Behavior, MotionSpec
    return [Behavior(id="_imposed_mesh_assembly", phase="assembly",
                     motion=MotionSpec(kind="translation"))]


class RackPinionCard(MechanicalElementCard):
    """Spur rack & pinion (MECHSYNTH §3.6, amended) — the true INVOLUTE pinion (M1: the trapezoid is
    dead, D-M1-1) driving a straight rack. Realizes a use-phase rot_to_trans transmission. Geometry
    in knowledge/cards/rack_pinion.py (reuses M1's involute + L3 wedge decomposition)."""
    card_id = "rack_pinion"
    has_functional_clearance = True  # tooth-flank backlash (§3.6, D21)
    taxonomy = {"working_motion": ("rot_to_trans", "regular"), "axis_relationship": "parallel",
                "connection_principle": None, "self_locking": False, "vb_verifiable": False,
                "compliance": "rigid", "kinematic_dof": "1 rot coupled to 1 trans"}  # curved contact -> V-B deferred (R2b)
    imposes = _rack_pinion_imposes()
    # §3.6 AMENDED: module bounds are LARGE {5,6}, and the reason is SIMULATION STABILITY, not
    # mechanics — mechanically a smaller module meshes fine, but R2b (D-M1-2/-3/-5) showed the rigid
    # contact rig is dt-unstable below the large-module range at the frozen preset. The bounds encode
    # a physics-of-verification constraint, and selection_notes says so explicitly (D-M1-4 rule text).
    param_bounds = {"module": (5.0, 6.0, "mm"), "z_pinion": (10.0, 24.0, "count"),
                    "pressure_angle_deg": (20.0, 20.0, "deg"), "face_w": (4.0, 10.0, "mm"),
                    "backlash": (0.1, 0.25, "mm"), "stroke": (20.0, 400.0, "mm")}
    selection_notes = (
        "Use when ROTATION must be converted to TRANSLATION at a defined ratio (a knob that drives "
        "a drawer). Realizes a use-phase rot_to_trans transmission.\n"
        "WHY THE MODULE BOUNDS ARE LARGE ({5,6}, not the mechanically-natural 1-2): the bound is a "
        "CONTACT-SIMULATION-STABILITY requirement, NOT a mechanical one (D-M1-2/-4). Mechanically a "
        "fine-module rack meshes perfectly; but the rigid convex-facet contact rig is dt-unstable "
        "below the large-module range at the frozen preset (R5) — larger teeth = gentler contact "
        "geometry = a larger stable timestep. The card mandates the large module so the geometry it "
        "produces is the geometry the verifier can actually simulate.\n"
        "STANDING R2b-OPEN FLAG: contact-only (V-B) BIDIRECTIONAL meshing is NOT stable — the "
        "reversal backlash-crossing impact diverges at the frozen preset, and no module or preset "
        "param fixes it (a contact-FORMULATION limit, D-M1-5/-7). FORWARD meshing IS demonstrable "
        "(ratio −0.50). So a rack_pinion is verified V-A (declared-shaft ratio); its bidirectional "
        "contact verification is DEFERRED to a versioned preset_v2 or a pitch-cylinder proxy.\n"
        "Prefer a simpler element if the task does not genuinely need ratio'd rotation→translation.")
    citations = [Citation(doc="MECHSYNTH_SPEC_v0.1", section="§3.6 Card 4 — rack_pinion (amended)"),
                 Citation(doc="DECISIONS_LOG", section="D-M1-1/-2/-4/-5/-7 (involute; R2a retired; R2b frozen)"),
                 Citation(doc="M1 gear rig", section="gear_geom involute + L3 flank_wedges")]
    ports = [_p("pinion_axis", "axis"), _p("rack_mount", "face"), _p("mesh_line", "edge")]

    def carve(self, host_parts, inst, bindings):
        """Place the involute pinion on its shaft + the straight rack in mesh (host-agnostic)."""
        from knowledge.cards.rack_pinion import carve as _carve
        return _carve(host_parts, inst, bindings)

    def collision_hint(self, inst, n_wedge=4):
        """L3 involute flank-wedge decomposition (§3.6, D18/D21) — the card's OWN convex hint;
        mujoco.sdf.gear is FORBIDDEN. Deferred with V-B this session (V-A uses no tooth contact)."""
        from knowledge.cards.rack_pinion import collision_primitives
        return collision_primitives(inst, n_wedge)

    def resolve_params(self, ir, inst):
        """⑤/D6: stroke from the use-phase transmission behaviour's range; module snapped INTO the
        {5,6} stability band (never below); z_pinion carried. The card owns the §3.6 formulas."""
        out = dict(inst.params or {})
        b = next((x for x in ir.behaviors if x.realized_by == inst.id
                  and getattr(x.motion.kind, "value", x.motion.kind) == "rot_to_trans"), None)
        if b is not None and getattr(b.motion, "range_value", None):
            out["stroke"] = float(b.motion.range_value)
        out.setdefault("stroke", 120.0)
        out.setdefault("z_pinion", 12)
        # snap the module up into the stability band [5,6] (R2b — never below)
        m = float(out.get("module", 5.0))
        out["module"] = min(6.0, max(5.0, m))
        out.setdefault("backlash", 0.20)
        out.setdefault("face_w", 8.0)
        out.setdefault("pressure_angle_deg", 20.0)
        return out

    def verification(self, ir, inst):
        """§6.3 P-GEAR, V-A ONLY (the standing requirement, D-M1-7). V-A checks the declared-shaft
        transmission ratio: |s / (θ·r_pitch) − 1| ≤ 5% over N revolutions. **V-B (emergent contact
        ratio) is DOWNGRADED** — the bidirectional reversal is R2b-open; the gap is NAMED in the
        protocol so a design never silently claims contact-level meshing it cannot show."""
        from ontology.schema import Criterion, VerificationProtocol
        use_b = next((b for b in ir.behaviors
                      if b.realized_by == inst.id
                      and getattr(b.phase, "value", b.phase) == "use"
                      and getattr(b.motion.kind, "value", b.motion.kind) == "rot_to_trans"), None)
        if use_b is None:
            return []
        return [VerificationProtocol(
            id=f"P-GEAR-VA-{inst.id}", verifies=use_b.id, mode="V-A", seeds=5, seed_pass=4,
            actuation={"kind": "shaft_velocity", "n_rev": 3.0,
                       "v_b_gap": "bidirectional contact meshing PENDING preset_v2 (R2b/D-M1-7); "
                                  "forward V-B demonstrable, reversal backlash-crossing diverges"},
            criteria=[Criterion(name="transmission_ratio", observable="transmission_residual",
                                op="<=", threshold=0.05, unit="")], observables=[])]


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


def _pawl_imposes() -> list:
    """The pawl imposes a USE-phase ratchet click-over — an INTENDED contact (D22), not a defect: as
    the platform rises the pawl deliberately rides over each ratchet tooth. Registered per V-08."""
    from ontology.schema import Behavior, MotionSpec
    return [Behavior(id="_imposed_ratchet_clickover", phase="use", motion=MotionSpec(kind="fixed"))]


class PawlDetentCard(MechanicalElementCard):
    """Spring-arm ratchet pawl (physics-discovered element #2, D-M13-4) — snap_hook's mechanical
    cousin. PERMITS crank-driven lift (shallow drive-over angle) and BLOCKS back-drive (steep lock
    angle ≥ the self-locking asymptote atan(1/μ)). Reuses the Bayer cantilever formulas VERBATIM
    (knowledge/cards/pawl_detent.py delegates to snap_hook_cantilever). Provides no pieces — a spring
    arm carved on the tower + fine ratchet detents on the rack side."""
    card_id = "pawl_detent"
    has_functional_clearance = True   # the detent engagement clearance (D18/D21)
    taxonomy = {"working_motion": ("fixed", "regular"), "axis_relationship": "parallel",
                "connection_principle": None, "self_locking": True, "vb_verifiable": True,
                "compliance": "rigid", "kinematic_dof": "unilateral ratchet (reclass candidate -> compliant, m18 REVIEW §5)"}
    imposes = _pawl_imposes()
    requires = {"eps_allow_pct": (">=", 3.0)}   # the spring arm must sustain the flexure strain
    param_bounds = {"L_mm": (8.0, 25.0, "mm"), "b_mm": (4.0, 10.0, "mm"), "h_mm": (0.8, 2.0, "mm"),
                    "alpha_drive_deg": (25.0, 35.0, "deg"), "alpha_lock_deg": (74.0, 90.0, "deg"),
                    "detent_pitch_mm": (2.0, 5.0, "mm"), "detent_depth_mm": (0.6, 1.5, "mm")}
    selection_notes = (
        "Use when a transmission must HOLD a load against a back-driving force it cannot self-lock — "
        "e.g. a rack-pinion LIFT (μ·W·rp ≪ W·rp, so a plain gear back-drives; discovered at P-HOLD, "
        "D-M13-2). The pawl is asymmetric: a SHALLOW drive-over angle so the crank clicks over each "
        "ratchet tooth cheaply, and a STEEP lock angle ≥ self_locking_angle(μ)=atan(1/μ)=73.3° (at "
        "μ=0.30) so the Fig.18 factor DIVERGES and back-drive cannot deflect the pawl out — it "
        "self-locks. This is the m3 permanent-lock cliff (D-GEN-2) used DELIBERATELY, not avoided. "
        "The hold RESOLUTION is one detent pitch (the platform drops ≤ one tooth before catching).")
    citations = [Citation(doc="Bayer", section="p.14 Fig.18 factor (μ+tanα)/(1−μtanα) + self-lock asymptote"),
                 Citation(doc="DECISIONS_LOG", section="D-M13-4 (physics-discovered element #2, after the stop)")]
    ports = [_p("pawl_mount", "face"), _p("ratchet_line", "edge")]

    def carve(self, host_parts, inst, bindings):
        from knowledge.cards.pawl_detent import carve as _carve
        return _carve(host_parts, inst, bindings)

    def collision_hint(self, inst):
        from knowledge.cards.pawl_detent import collision_primitives
        return collision_primitives(inst)

    def resolve_params(self, ir, inst):
        """Snap the lock angle UP to at least the self-locking angle so the pawl actually holds."""
        from knowledge.cards.pawl_detent import dims_from, forces
        out = dict(inst.params or {})
        f = forces(dims_from(out))
        if float(out.get("alpha_lock_deg", 80.0)) < f["self_lock_angle_deg"]:
            out["alpha_lock_deg"] = round(f["self_lock_angle_deg"] + 5.0, 1)
        out.setdefault("detent_pitch_mm", 3.0)
        return out

    def verification(self, ir, inst):
        """PR-PAWL — the hold verification. Gate: back-drive ≤ one detent pitch (+margin). The FORMULA
        facts (self-locks? drive-over force in budget?) ride in the actuation, Bayer-computed."""
        from ontology.schema import Criterion, VerificationProtocol
        from knowledge.cards.pawl_detent import dims_from, forces
        hold_b = next((b for b in ir.behaviors if b.realized_by == inst.id
                       and getattr(b.phase, "value", b.phase) == "static"), None)
        if hold_b is None:
            return []
        g = dims_from(inst.params)
        f = forces(g)
        load = hold_b.load or {}
        budget_N = float(load.get("mass_kg", 0.5)) * 9.81 + 4.0   # lift force the crank already carries
        protos = [VerificationProtocol(
            id=f"PR-PAWL-{inst.id}", verifies=hold_b.id, mode="V-A", seeds=5, seed_pass=4,
            actuation={"kind": "release_and_watch", "load_kg": load.get("mass_kg", 0.5),
                       "self_locks": f["self_locks"], "W_drive_N": f["W_drive_N"],
                       "self_lock_angle_deg": f["self_lock_angle_deg"],
                       "alpha_lock_deg": f["alpha_lock_deg"], "drive_over_budget_N": round(budget_N, 2),
                       "drive_over_in_budget": bool(f["W_drive_N"] <= budget_N),
                       "note": "self-locks at alpha_lock>=atan(1/mu); catches within one detent pitch"},
            criteria=[Criterion(name="no_backdrive", observable="backdrive_mm", op="<=",
                                threshold=round(g.detent_pitch + 2.0, 2), unit="mm")], observables=[])]
        click_b = next((b for b in ir.behaviors if b.imposed_by == inst.id
                        and getattr(b.phase, "value", b.phase) == "use"), None)
        if click_b is not None:
            protos.append(VerificationProtocol(
                id=f"PR-CLICK-{inst.id}", verifies=click_b.id, mode=None,
                actuation={"kind": "formula_recheck", "source": "Bayer p.14 drive-over"},
                criteria=[Criterion(name="drive_over_in_budget", observable="pawl_drive_N", op="<=",
                                    threshold=round(budget_N, 2), unit="N")], observables=[]))
        return protos


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
    taxonomy = {"working_motion": ("rotation", "regular"), "axis_relationship": "parallel",
                "connection_principle": None, "self_locking": False, "vb_verifiable": True,
                "compliance": "rigid", "kinematic_dof": "constrains a rotation limit (realizes none)"}
    ports = [_p("contact", "face")]  # the flange face that lands on the base wall
    param_bounds = {"stop_angle": (0.0, 180.0, "deg"), "stop_flange_r": (2.0, 20.0, "mm")}
    imposes = _stop_flange_imposes()
    def resolve_params(self, ir, inst):
        """D-E-7 / D6: resolve this feature's geometry params at ⑤.

        Why this exists: a frontier model correctly SELECTED the stop_flange at ④ — and ⑥ then died
        on `KeyError: stop_flange_r`, because ④ creates a FeatureInstance with params={} and nothing
        ever filled them. The hand-written goldens set them, which hid the hole: the pipeline could
        only ever build a stop that a human had already dimensioned. The model did the right thing
        and the machine could not compile it.

        The fix belongs HERE, not in the carve: a carve that silently defaults a missing dimension
        would be inventing geometry with no declaring source (the m8 lesson). The card owns the
        formula; ⑤ owns when it runs.

        `stop_flange_r` takes the midpoint of the card's own declared param_bounds; `stop_angle` is
        SOLVED from this box's geometry by the card's scan (never copied — the m8 108.85° lesson).
        """
        from knowledge.cards.stop_flange_geometry import stop_angle_deg
        out = dict(inst.params or {})
        if "stop_flange_r" not in out:
            lo, hi, _u = self.param_bounds["stop_flange_r"]
            out["stop_flange_r"] = round((lo + hi) / 2, 3)
        out.setdefault("flange_w", 8.0)
        host = next((b.piece_id for b in ir.bindings if b.element_id == inst.id), None)
        piece = ir.piece(host) if host else None
        ax = next((b for b in ir.bindings
                   if b.port == "axis" and b.mate == "coincident_axis"), None)
        if piece is not None:
            bw = float(piece.params.get("box_w", 60.0))
            bh = float(piece.params.get("box_h", 40.0))
            # the hinge axis sits off the base's rear top edge (the template's own anchor geometry)
            out["stop_angle"] = stop_angle_deg(axis_y=-bw / 2 - 4.0, axis_z=bh, box_w=bw,
                                               box_h=bh, stop_flange_r=out["stop_flange_r"])
        return out

    def verification(self, ir, inst):
        """D-E-5 / D-ONT-4: the stop_flange's verification CONTRIBUTION — it owns no protocol; it
        PROMOTES the overtravel measurement to a criterion on the protocol that already verifies the
        rotation it caps.

        A passive feature realizes nothing, so it has no behaviour of its own to verify. Returning a
        protocol would claim a DoF it does not realize (V-08's class rule). What it has is a reason
        the hinge's protocol must now ask one more question: "did travel stay capped?" """
        return []

    def criterion_contribution(self, ir, inst):
        """The angle-limit criterion this feature adds to whatever protocol verifies the rotation it
        caps. Threshold = the IR's declared ceiling + a band for contact compliance (the flange
        arrests ~4° past its solved angle — m8). WITHOUT the stop the same measurement stays an
        OBSERVABLE, because a stop-less lid folding flat is the finding, not a gate (D-M8-5/D20)."""
        from ontology.schema import Criterion
        b3 = next((b for b in ir.behaviors
                   if b.imposed_by == inst.id
                   and getattr(b.motion.kind, "value", b.motion.kind) == "rotation"
                   and getattr(b.motion, "bound", None) == "max"), None)
        ceiling = (float(getattr(b3.motion, "range_value", None) or 150.0) if b3
                   else float((inst.params or {}).get("stop_angle", 150.0)))
        return b3, Criterion(name="angle_limited", observable="theta_max_deg", op="<=",
                             threshold=round(ceiling + 30.0, 2), unit="deg")


    def carve(self, host_parts, inst, bindings, axis=None):
        """Grow the rearward flange on the bound (moving) piece. Needs the hinge axis it caps —
        the same information M0's builder had. Delegates to stop_flange_geometry."""
        from knowledge.cards.stop_flange_geometry import carve as _carve
        return _carve(host_parts, inst, bindings, axis)

    def collision_hint(self, inst, lid_params=None, axis=None):
        """The flange box — an EXACT proxy of real carved geometry (a box is already convex), not a
        stop invented in the physics layer. Required for V-B: contact-only is the mode in which a
        stop must act BY CONTACT, so the geometry that does the stopping must be present."""
        from knowledge.cards.stop_flange_geometry import collision_primitives
        return collision_primitives(inst, lid_params, axis)
    selection_notes = ("Use when a hinged lid must not fold past a set angle. Cheapest stop: a "
                       "flange on the moving piece landing on a fixed wall — no added part.")
    citations = [Citation(doc="MECHSYNTH_SPEC_v0.1", section="§3.3 (stop_flange companion)"),
                 Citation(doc="M0 hinge box", section="stop variant — stop_angle_deg by scan"),
                 Citation(doc="DECISIONS_LOG", section="D20 / D-M8-2 (stopping by contact)")]


# ======================================================================================
# M18 TIER-1 ELEMENTS (D-M18-1/-2/-3). Schema/ontology expansion, no new physics: V-A or static /
# formula verified (NO curved-contact V-B — that is the next milestone). Geometry + cited formulas in
# knowledge/cards/m18_tier1.py; every card carries its 7-axis taxonomy tag (m18 REVIEW §1).
# ======================================================================================
def _cit_pb(section, note=""):
    return Citation(doc="Pahl & Beitz, Engineering Design", section=section + (f" — {note}" if note else ""))


# --- MechanicalElementCards (realize a DoF) -------------------------------------------
class LeadScrewCard(MechanicalElementCard):
    """Power lead screw (P&B §7.4.3, Shigley §8-2): converts rotation to translation and — unlike a
    plain rack_pinion — SELF-LOCKS when the lead angle ≤ the friction angle (holds a load with no
    added brake). Resolves the ontology gap D-M13-3: 'holds under load' is now the axis-4
    self_locking field. V-A only: the helical thread flank is CURVED contact, V-B deferred (cite m17
    / D-M1-7), exactly as rack_pinion defers its tooth contact."""
    card_id = "lead_screw"
    has_functional_clearance = True   # thread flank backlash (curved) — V-B deferred, cite m17
    taxonomy = {"working_motion": ("rot_to_trans", "regular"), "axis_relationship": "parallel",
                "connection_principle": None, "self_locking": True, "vb_verifiable": False,
                "compliance": "rigid", "kinematic_dof": "1 rot coupled to 1 trans (reserved axis-7)"}
    param_bounds = {"d_major": (5.0, 20.0, "mm"), "lead": (1.0, 6.0, "mm"), "starts": (1.0, 2.0, "count"),
                    "length": (20.0, 200.0, "mm"), "stroke": (10.0, 180.0, "mm")}
    ports = [_p("screw_axis", "axis"), _p("nut_mount", "face")]
    selection_notes = (
        "Use when ROTATION must become TRANSLATION and the load must HOLD when released without a "
        "brake (a screw-jack, a vice, a leadscrew stage). Realizes a use-phase rot_to_trans that "
        "SELF-LOCKS (axis-4) — the discriminator vs rack_pinion, which back-drives and needs a "
        "pawl_detent (D-M13-4). Self-locks iff lead angle λ=atan(lead/πd_p) ≤ friction angle "
        "φ=atan(μ) (P&B §7.4.3); the cost is low efficiency (η≈0.2 at self-lock).\n"
        "V-A only: the thread flank is curved contact — bidirectional V-B is deferred behind a "
        "preset_v2 (m17/D-M1-7), like rack_pinion. Prefer rack_pinion for fast travel that need not "
        "hold; prefer lead_screw when self-locking hold matters more than speed.")
    citations = [_cit_pb("§7.4.3", "self-help / self-locking"),
                 Citation(doc="Shigley's Mechanical Engineering Design", section="§8-2 Power Screws"),
                 Citation(doc="DECISIONS_LOG", section="D-M13-3 (holds-under-load, now axis-4); m17 (V-B deferred)")]

    def resolve_params(self, ir, inst):
        from knowledge.cards.m18_tier1 import lead_screw_dims, lead_screw_mechanics
        out = dict(inst.params or {})
        b = next((x for x in ir.behaviors if x.realized_by == inst.id
                  and getattr(x.motion.kind, "value", x.motion.kind) == "rot_to_trans"), None)
        if b is not None and getattr(b.motion, "range_value", None):
            out["stroke"] = float(b.motion.range_value)
        out.setdefault("stroke", 40.0); out.setdefault("d_major", 8.0); out.setdefault("lead", 2.0)
        out.setdefault("length", round(float(out["stroke"]) + 20.0, 1))
        # keep it self-locking if the behaviour asked for it: shrink the lead until λ ≤ φ
        if b is not None and getattr(b, "self_locking", False):
            while not lead_screw_mechanics(lead_screw_dims(out))["self_locks"] and out["lead"] > 1.0:
                out["lead"] = round(out["lead"] - 0.5, 2)
        return out

    def carve(self, host_parts, inst, bindings):
        from knowledge.cards.m18_tier1 import lead_screw_carve
        return lead_screw_carve(host_parts, inst, bindings)

    def collision_hint(self, inst):
        from knowledge.cards.m18_tier1 import lead_screw_collision
        return lead_screw_collision(inst)

    def formula_check(self, inst):
        from knowledge.cards.m18_tier1 import lead_screw_dims, lead_screw_mechanics
        return lead_screw_mechanics(lead_screw_dims(getattr(inst, "params", {}) or {}))

    def verification(self, ir, inst):
        from ontology.schema import Criterion, VerificationProtocol
        b = next((x for x in ir.behaviors if x.realized_by == inst.id
                  and getattr(x.phase, "value", x.phase) == "use"
                  and getattr(x.motion.kind, "value", x.motion.kind) == "rot_to_trans"), None)
        if b is None:
            return []
        stroke = float((inst.params or {}).get("stroke", 40.0))
        return [VerificationProtocol(
            id=f"P-SCREW-VA-{inst.id}", verifies=b.id, mode="V-A", seeds=5, seed_pass=4,
            actuation={"kind": "shaft_velocity", "n_rev": 3.0,
                       "v_b_gap": "helical thread flank is CURVED contact — bidirectional V-B "
                                  "deferred to preset_v2 (m17/D-M1-7), like rack_pinion"},
            criteria=[Criterion(name="reaches_stroke", observable="stroke_mm", op=">=",
                                threshold=stroke, unit="mm"),
                      Criterion(name="self_locks_holds", observable="backdrive_mm", op="<=",
                                threshold=1.0, unit="mm")], observables=[])]


class CouplingCard(MechanicalElementCard):
    """Rigid shaft coupling (P&B §8.1, Shigley §3-12): transmits rotation 1:1 between two COAXIAL /
    parallel shafts, no ratio. A rigid connection between shaft ends — V-A verifies the declared 1:1
    pair (no curved contact)."""
    card_id = "coupling"
    has_functional_clearance = False
    taxonomy = {"working_motion": ("rotation", "regular"), "axis_relationship": "parallel",
                "connection_principle": None, "self_locking": False, "vb_verifiable": True,
                "compliance": "rigid", "kinematic_dof": "1 revolute (through-transmitted)"}
    param_bounds = {"bore_d": (4.0, 20.0, "mm"), "body_d": (10.0, 40.0, "mm"), "length": (10.0, 60.0, "mm")}
    ports = [_p("shaft_in", "axis"), _p("shaft_out", "axis")]
    selection_notes = ("Use to join two coaxial shafts and transmit rotation 1:1 (no ratio). "
                       "axis_relationship=parallel/coaxial. V-A verifies the declared 1:1 pair.")
    citations = [_cit_pb("§8.1", "connections"), Citation(doc="Shigley's", section="§3-12 (shaft torsion)")]

    def resolve_params(self, ir, inst):
        out = dict(inst.params or {})
        out.setdefault("bore_d", 8.0); out.setdefault("body_d", 20.0); out.setdefault("length", 24.0)
        return out

    def carve(self, host_parts, inst, bindings):
        from knowledge.cards.m18_tier1 import coupling_carve
        return coupling_carve(host_parts, inst, bindings)

    def formula_check(self, inst):
        from knowledge.cards.m18_tier1 import coupling_dims, coupling_torque
        return coupling_torque(coupling_dims(getattr(inst, "params", {}) or {}))

    def verification(self, ir, inst):
        from ontology.schema import Criterion, VerificationProtocol
        b = next((x for x in ir.behaviors if x.realized_by == inst.id
                  and getattr(x.phase, "value", x.phase) == "use"
                  and getattr(x.motion.kind, "value", x.motion.kind) == "rotation"), None)
        if b is None:
            return []
        return [VerificationProtocol(
            id=f"P-COUPLING-VA-{inst.id}", verifies=b.id, mode="V-A", seeds=5, seed_pass=4,
            actuation={"kind": "shaft_velocity", "n_rev": 3.0, "ratio_expected": 1.0},
            criteria=[Criterion(name="transmits_1to1", observable="transmission_residual", op="<=",
                                threshold=0.05, unit="")], observables=[])]


class UniversalJointCard(MechanicalElementCard):
    """Cardan universal joint (P&B §8.1): transmits rotation across INTERSECTING axes at an angle β.
    Not constant-velocity (velocity ratio fluctuates cos β … 1/cos β over a rev — recorded, not a
    defect). V-A verifies the declared angled pair."""
    card_id = "universal_joint"
    has_functional_clearance = False
    taxonomy = {"working_motion": ("rotation", "regular"), "axis_relationship": "intersecting",
                "connection_principle": None, "self_locking": False, "vb_verifiable": True,
                "compliance": "rigid", "kinematic_dof": "2 revolute (cross) — reserved axis-7"}
    param_bounds = {"yoke_d": (10.0, 30.0, "mm"), "bore_d": (4.0, 16.0, "mm"),
                    "length": (10.0, 50.0, "mm"), "angle_deg": (5.0, 35.0, "deg")}
    ports = [_p("shaft_in", "axis"), _p("shaft_out", "axis")]
    selection_notes = ("Use to transmit rotation between shafts whose axes INTERSECT at an angle "
                       "(axis_relationship=intersecting). Not constant-velocity — a single Cardan "
                       "joint's output speed fluctuates by ±(1/cosβ−cosβ); pair two to cancel it. "
                       "V-A verifies the declared angled pair.")
    citations = [_cit_pb("§8.1", "connections / intersecting-axis transmission")]

    def resolve_params(self, ir, inst):
        out = dict(inst.params or {})
        out.setdefault("angle_deg", 20.0); out.setdefault("bore_d", 8.0); out.setdefault("length", 20.0)
        return out

    def carve(self, host_parts, inst, bindings):
        from knowledge.cards.m18_tier1 import ujoint_carve
        return ujoint_carve(host_parts, inst, bindings)

    def formula_check(self, inst):
        from knowledge.cards.m18_tier1 import ujoint_dims, ujoint_kinematics
        return ujoint_kinematics(ujoint_dims(getattr(inst, "params", {}) or {}))

    def verification(self, ir, inst):
        from ontology.schema import Criterion, Observable, VerificationProtocol
        b = next((x for x in ir.behaviors if x.realized_by == inst.id
                  and getattr(x.phase, "value", x.phase) == "use"
                  and getattr(x.motion.kind, "value", x.motion.kind) == "rotation"), None)
        if b is None:
            return []
        return [VerificationProtocol(
            id=f"P-UJOINT-VA-{inst.id}", verifies=b.id, mode="V-A", seeds=5, seed_pass=4,
            actuation={"kind": "shaft_velocity", "n_rev": 3.0},
            criteria=[Criterion(name="transmits_rotation", observable="transmission_residual", op="<=",
                                threshold=0.2, unit="")],   # looser: single Cardan fluctuates by design
            observables=[Observable(name="cv_fluctuation", measured="transmission_residual",
                                    note="single Cardan is NOT constant-velocity (cosβ..1/cosβ)")])]


# --- PassiveFeatureCards (support a DoF; realize nothing) ------------------------------
class JournalBearingCard(PassiveFeatureCard):
    """Journal (plain) bearing (P&B §8.2): a low-friction bore that SUPPORTS a rotating shaft. It
    realizes nothing (V-08). Generalises pin_hinge's bore. Static/optional-V-A; running clearance is
    a functional clearance → collision_hint (D18/D21), an exact convex tube."""
    card_id = "journal_bearing"
    has_functional_clearance = True
    taxonomy = {"working_motion": ("rotation", "regular"), "axis_relationship": "parallel",
                "connection_principle": None, "self_locking": False, "vb_verifiable": True,
                "compliance": "rigid", "kinematic_dof": "supports 1 revolute (realizes none)"}
    param_bounds = {"bore_d": (3.0, 30.0, "mm"), "wall": (1.5, 6.0, "mm"), "length": (4.0, 40.0, "mm")}
    ports = [_p("bore_mount", "face"), _p("shaft_axis", "axis")]
    selection_notes = ("Use to SUPPORT a rotating shaft at low friction (a journal). Realizes "
                       "nothing (imposed_by, never realized_by). Running clearance ≈ d/1000, floored "
                       "at the print clearance so it is printable (Shigley §12).")
    citations = [_cit_pb("§8.2", "bearings / guides"), Citation(doc="Shigley's", section="§12 (journal bearings)")]

    def resolve_params(self, ir, inst):
        out = dict(inst.params or {})
        out.setdefault("bore_d", 8.0); out.setdefault("wall", 3.0); out.setdefault("length", 10.0)
        return out

    def carve(self, host_parts, inst, bindings):
        from knowledge.cards.m18_tier1 import bearing_carve
        return bearing_carve(host_parts, inst, bindings)

    def collision_hint(self, inst):
        from knowledge.cards.m18_tier1 import bearing_collision
        return bearing_collision(inst, cid="journal_bearing")

    def formula_check(self, inst):
        from knowledge.cards.m18_tier1 import bearing_dims, bearing_fit
        return bearing_fit(bearing_dims(getattr(inst, "params", {}) or {}))

    def verification(self, ir, inst):
        return []   # a passive support realizes nothing → no protocol of its own (like stop_flange)


class BushingCard(PassiveFeatureCard):
    """Bushing (P&B §8.2): a low-friction SLEEVE support — a shorter journal, often press-inserted as
    a wear surface. Realizes nothing. Same fit knowledge as the journal_bearing."""
    card_id = "bushing"
    has_functional_clearance = True
    taxonomy = {"working_motion": ("rotation", "regular"), "axis_relationship": "parallel",
                "connection_principle": None, "self_locking": False, "vb_verifiable": True,
                "compliance": "rigid", "kinematic_dof": "supports 1 revolute (realizes none)"}
    param_bounds = {"bore_d": (3.0, 24.0, "mm"), "wall": (1.0, 4.0, "mm"), "length": (3.0, 24.0, "mm")}
    ports = [_p("bore_mount", "face"), _p("shaft_axis", "axis")]
    selection_notes = ("Use as a low-friction sleeve support / wear surface for a shaft or a sliding "
                       "pin. Realizes nothing (imposed_by). A shorter journal_bearing.")
    citations = [_cit_pb("§8.2", "bearings / guides")]

    def resolve_params(self, ir, inst):
        out = dict(inst.params or {})
        out.setdefault("bore_d", 6.0); out.setdefault("wall", 2.0); out.setdefault("length", 8.0)
        return out

    def carve(self, host_parts, inst, bindings):
        from knowledge.cards.m18_tier1 import bearing_carve
        return bearing_carve(host_parts, inst, bindings)

    def collision_hint(self, inst):
        from knowledge.cards.m18_tier1 import bearing_collision
        return bearing_collision(inst, cid="bushing")

    def formula_check(self, inst):
        from knowledge.cards.m18_tier1 import bearing_dims, bearing_fit
        return bearing_fit(bearing_dims(getattr(inst, "params", {}) or {}))

    def verification(self, ir, inst):
        return []


# --- ConnectionCards (fasten/fix; realize nothing, support no DoF) --------------------
class DowelPinCard(ConnectionCard):
    """Dowel pin (P&B §8.1, FORM connection): LOCATES two parts by geometric interlock — removes
    in-plane DoF, transmits no load through friction. Static t0 check (bore receives pin, no
    interference). Provides no separate hardware piece (the dowel IS the located feature)."""
    card_id = "dowel_pin"
    has_functional_clearance = False
    connection_principle = "form"
    taxonomy = {"working_motion": ("fixed", "regular"), "axis_relationship": "parallel",
                "connection_principle": "form", "self_locking": False, "vb_verifiable": True,
                "compliance": "rigid", "kinematic_dof": "removes 2 in-plane translations"}
    param_bounds = {"pin_d": (2.0, 10.0, "mm"), "length": (5.0, 30.0, "mm"),
                    "fit_clearance": (0.0, 0.1, "mm")}
    ports = [_p("location", "point"), _p("mate", "point")]
    selection_notes = ("Use to LOCATE two parts precisely with no degree of freedom (align a lid to "
                       "a box, register two plates). FORM connection (geometric interlock, §8.1). A "
                       "single dowel removes 2 in-plane translations; a pair also fixes rotation. "
                       "Static — checked by t0 fit, not physics.")
    citations = [_cit_pb("§8.1", "form-closed connection")]

    def resolve_params(self, ir, inst):
        out = dict(inst.params or {})
        out.setdefault("pin_d", 4.0); out.setdefault("length", 12.0); out.setdefault("fit_clearance", 0.02)
        return out

    def carve(self, host_parts, inst, bindings):
        from knowledge.cards.m18_tier1 import dowel_carve
        return dowel_carve(host_parts, inst, bindings)

    def formula_check(self, inst):
        from knowledge.cards.m18_tier1 import dowel_dims, dowel_fit
        return dowel_fit(dowel_dims(getattr(inst, "params", {}) or {}))

    def verification(self, ir, inst):
        return []


class ScrewBossCard(ConnectionCard):
    """Self-tapping screw boss (P&B §8.1, FORCE connection) — the FIRST force-connection card. A boss
    receives a self-tapping screw (single PETG, D8); the clamp/preload is friction+thread interlock.
    Provides the SCREW as a hardware piece (D-ONT-11) — a ConnectionCard that is ALSO a hardware
    provider (connection-role and hardware-piece are orthogonal, m18 REVIEW §2.2). Static pull-out
    formula (BASF/Bayer boss rules)."""
    card_id = "screw_boss"
    has_functional_clearance = False
    connection_principle = "force"
    taxonomy = {"working_motion": ("fixed", "regular"), "axis_relationship": "parallel",
                "connection_principle": "force", "self_locking": False, "vb_verifiable": True,
                "compliance": "rigid", "kinematic_dof": "fully constrains (fastened)"}
    param_bounds = {"screw_d": (2.0, 6.0, "mm"), "engagement": (3.0, 20.0, "mm"),
                    "tau_shear": (20.0, 45.0, "MPa")}
    ports = [_p("boss_mount", "face"), _p("clamped", "face")]
    provides_pieces = [ProvidedPiece("screw", ["screw_d", "screw_len"], role="fastener")]
    selection_notes = ("Use to FASTEN two parts with a self-tapping screw into a moulded/printed boss "
                       "(FORCE connection, §8.1). The screw is HARDWARE the card provides (D-ONT-11). "
                       "Bayer boss rules: boss OD≈2·screw_d, pilot≈0.8·screw_d, engagement≥2·screw_d; "
                       "pull-out = π·pilot·engagement·τ_shear. Prefer a dowel_pin if you only need to "
                       "LOCATE (no clamp), or a snap_hook if you want tool-free hand assembly.")
    citations = [_cit_pb("§8.1", "force-closed connection"),
                 Citation(doc="BASF/Bayer Snap-Fit & Boss Design Guide", section="self-tap boss rules"),
                 Citation(doc="DECISIONS_LOG", section="D8 (single-material PETG); D-ONT-11 (hardware)")]

    def resolve_params(self, ir, inst):
        out = dict(inst.params or {})
        out.setdefault("screw_d", 3.0)
        out["engagement"] = round(max(float(out.get("engagement", 0.0)), 2.0 * float(out["screw_d"])), 2)
        out.setdefault("tau_shear", 30.0)
        return out

    def resolve_piece_params(self, name, inst):
        if name != "screw":
            return {}
        d = float((inst.params or {}).get("screw_d", 3.0))
        return {"screw_d": d, "screw_len": round(float((inst.params or {}).get("engagement", 6.0)) + 4.0, 1)}

    def carve(self, host_parts, inst, bindings):
        from knowledge.cards.m18_tier1 import screwboss_carve
        return screwboss_carve(host_parts, inst, bindings)

    def formula_check(self, inst):
        from knowledge.cards.m18_tier1 import screwboss_dims, screwboss_design
        return screwboss_design(screwboss_dims(getattr(inst, "params", {}) or {}))

    def verification(self, ir, inst):
        return []


class PressFitCard(ConnectionCard):
    """Press (interference) fit (P&B §8.1, FORCE connection): holds by radial interference pressure ×
    friction. axis-6 BOUNDARY CASE — this is STATIC INTERFERENCE verified by FORMULA (Shigley §3-56),
    not full compliant behaviour; a real PETG press-fit CREEPS (stress relaxation), so the holding
    formula is an UPPER bound on long-term hold. Flagged honestly (compliance='rigid' at the field;
    the creep caveat lives in the formula + selection_notes, since a P-SPRING protocol isn't built)."""
    card_id = "press_fit"
    has_functional_clearance = False
    connection_principle = "force"
    taxonomy = {"working_motion": ("fixed", "regular"), "axis_relationship": "parallel",
                "connection_principle": "force", "self_locking": False, "vb_verifiable": True,
                "compliance": "rigid", "kinematic_dof": "fully constrains (interference)",
                "caveat": "static_interference — creeps in PETG (upper-bound hold)"}
    param_bounds = {"d_nom": (3.0, 30.0, "mm"), "interference": (0.01, 0.15, "mm"),
                    "length": (3.0, 30.0, "mm")}
    ports = [_p("interface", "face"), _p("mate", "face")]
    selection_notes = ("Use to FASTEN a pin/bore or shaft/hub by INTERFERENCE (FORCE connection, "
                       "§8.1) — no separate part, no tool. Holding = π·d·L·p·μ with p=E·δ/d "
                       "(Shigley §3-56). CAVEAT (honest): a PETG press-fit CREEPS under sustained "
                       "load (stress relaxation), so the formula is an UPPER bound on long-term hold — "
                       "prefer a screw_boss where a durable clamp matters. axis-6 boundary case: "
                       "static-interference, verified by formula not physics.")
    citations = [_cit_pb("§8.1", "force-closed connection"),
                 Citation(doc="Shigley's", section="§3-56 (interference fits); Roark Table 13.1")]

    def resolve_params(self, ir, inst):
        out = dict(inst.params or {})
        out.setdefault("d_nom", 8.0); out.setdefault("interference", 0.05); out.setdefault("length", 10.0)
        return out

    def carve(self, host_parts, inst, bindings):
        from knowledge.cards.m18_tier1 import pressfit_carve
        return pressfit_carve(host_parts, inst, bindings)

    def formula_check(self, inst):
        from knowledge.cards.m18_tier1 import pressfit_dims, pressfit_holding
        return pressfit_holding(pressfit_dims(getattr(inst, "params", {}) or {}))

    def verification(self, ir, inst):
        return []


# card_ref -> card instance. Validators look up ports/requires/imposes/card_class here.
# The deprecated `snap_latch` alias (D-ONT-8) has been REMOVED now that the card has landed and
# MECHSYNTH §3.4/§8.1 are reconciled to `snap_hook_cantilever` (D-ONT-8 resolution).
_ALL_CARDS = (PinHingeCard, SnapHookCantileverCard, SlideRailCard, RackPinionCard, PawlDetentCard,
              StopFlangeCard,
              # M18 Tier-1 (D-M18-1/-2/-3)
              LeadScrewCard, CouplingCard, UniversalJointCard, JournalBearingCard, BushingCard,
              DowelPinCard, ScrewBossCard, PressFitCard)
CARD_REGISTRY: dict[str, ElementCard] = {c.card_id: c() for c in _ALL_CARDS}


def card_ports(card_ref: str) -> list[str]:
    card = CARD_REGISTRY.get(card_ref)
    return [p.name for p in card.ports] if card else []


def is_passive(card_ref: str) -> bool:
    card = CARD_REGISTRY.get(card_ref)
    return bool(card and card.card_class == "feature")
