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

from ontology.schema import Citation, EmergentCheck

if TYPE_CHECKING:
    from ontology.schema import Behavior, Port


class CollisionHintRequired(TypeError):
    """Raised at class definition when a functional-clearance card omits collision_hint()."""


class EmergentCheckRequired(TypeError):
    """Raised at class definition (card registration) when a card omits its axis-5 emergent_check tag
    (D-M18-4). Mirrors CollisionHintRequired: a curved-contact element that ships without NAMING its
    unverified emergent gap is exactly the failure this makes structurally impossible — so every
    concrete card MUST declare taxonomy['emergent_check'], and a 'deferred' one MUST carry reason+risk
    (the EmergentCheck model enforces the latter at construction; this enforces the former)."""


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


CARD_REGISTRY: dict = {}   # card_id -> instance (auto-populated on subclass definition)


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

    # populated by __init_subclass__ as concrete cards are imported (M18 refactor: cards live in
    # one-file-per-element modules; the registry stays here so `from ...base import CARD_REGISTRY`
    # keeps working everywhere).

    # M18 axis-6 (P&B §8.1.3, elastic connection): RESERVED. Fixed "rigid" this milestone; the
    # validator rejects "compliant" with a P-SPRING message (spring/damper/living_hinge are the future
    # compliant=true, needing a protocol not built here). The field exists so it can't be misused.
    compliance: str = "rigid"    # "rigid" | "compliant"  (D-M18-2)

    # M18 7-axis taxonomy tag (D-M18-2; see m18_element_expansion/REVIEW.md §1). A dict with keys:
    # working_motion=(type,nature), axis_relationship, connection_principle, self_locking,
    # emergent_check (axis-5 struct, D-M18-4), compliance, kinematic_dof(note). Every card sets it.
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
            # D-M18-4: every concrete card MUST declare its axis-5 emergent_check tag — no curved-
            # contact element may ship without naming its (deferred) emergent gap. The EmergentCheck
            # model enforces reason+risk for 'deferred' at construction; this enforces the tag exists.
            ec = (cls.taxonomy or {}).get("emergent_check")
            if not isinstance(ec, EmergentCheck):
                raise EmergentCheckRequired(
                    f"card '{cls.card_id}' does not declare taxonomy['emergent_check'] as an "
                    f"EmergentCheck (D-M18-4). Every card must state whether its assembly-level "
                    f"emergent behaviour is verified / deferred (with reason+risk) / not_applicable — "
                    f"a curved-contact element that hides its unverified gap is what this prevents."
                )
            CARD_REGISTRY[cls.card_id] = cls()   # auto-register (replaces the old _ALL_CARDS build)

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


def card_ports(card_ref: str) -> list[str]:
    card = CARD_REGISTRY.get(card_ref)
    return [p.name for p in card.ports] if card else []
def is_passive(card_ref: str) -> bool:
    card = CARD_REGISTRY.get(card_ref)
    return bool(card and card.card_class == "feature")
