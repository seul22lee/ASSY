"""snap_hook element card + Bayer cantilever formulas (M18 refactor: merges the former
snap_hook_cantilever.py formulas + the card class from base.py; geometry stays paired in
snap_hook_geometry.py). card_id stays "snap_hook_cantilever". No logic change."""

from __future__ import annotations

import math

# --- Table 1 (p.9), cross-section shape A (rectangle) — the permissible-deflection coefficient.
# Design 2 (thickness tapering root→h/2) permits >60% more deflection than design 1 (p.12), which
# is why the p.16 example uses it. Design 3 tapers width root→b/4.
SHAPE_A_COEFF = {1: 0.67, 2: 1.09, 3: 0.86}  # Bayer Table 1, p.9

# --- PETG material handling — ASSUMPTIONS (no PETG in the PDF). Gate G-S4: replace with data.
DEFAULT_SAFETY = 0.5      # p.16: working strain ε = ½ · ε_perm
FREQ_FACTOR = 0.60        # Table 2 footnote, p.12: frequent separation/rejoining → ~60%
EPS_PERM_PETG = 0.04      # ASSUMPTION: PETG amorphous ~70% yield strain (p.11); PC 4% stand-in
MU_PETG = 0.35            # ASSUMPTION: Table 3 has no PETG (extrapolated from PC 0.45–0.55)


# --- permissible deflection & its inversion ------------------------------------------------
def y_perm(eps: float, l: float, h: float, design_type: int = 2) -> float:
    """Permissible deflection (= undercut) y for a rectangular cantilever [Bayer Table 1, p.9].

        y = C · ε · l² / h        (C from SHAPE_A_COEFF)

    ε is the ABSOLUTE strain (percentage/100), e.g. 0.02 for 2% (p.9 symbols)."""
    return SHAPE_A_COEFF[design_type] * eps * l**2 / h


def solve_h(eps: float, l: float, y: float, design_type: int = 2) -> float:
    """Root thickness h that makes deflection to undercut y induce exactly strain ε — the p.16
    inversion of the Table 1 deflection equation:

        h = C · ε · l² / y

    Example I (design 2): 1.09 · 0.02 · 19² / 2.4 = 3.28 mm."""
    return SHAPE_A_COEFF[design_type] * eps * l**2 / y


# --- deflection force ----------------------------------------------------------------------
def P_deflect(b: float, h: float, Es: float, eps: float, l: float) -> float:
    """Deflection force P to bend the finger to strain ε [Bayer Table 1 bottom row, p.9]:

        P = (b · h² / 6) · (Es · ε / l)

    b·h²/6 is the rectangular section modulus Z. Es in N/mm² (MPa), lengths in mm → P in N.
    Example I: (9.5 · 3.28² / 6) · (1815 · 0.02 / 19) = 32.5 N."""
    return (b * h**2 / 6.0) * (Es * eps / l)


# --- mating / separation force -------------------------------------------------------------
def fig18_factor(mu: float, alpha_deg: float) -> float:
    """The dimensionless force factor (μ + tanα)/(1 − μ·tanα) [Bayer p.14; graph Fig.18, p.15].
    Example I: μ=0.6, α=30° → 1.80. Diverges as μ·tanα → 1 (self-locking); caller keeps α sane."""
    t = math.tan(math.radians(alpha_deg))
    denom = 1.0 - mu * t
    if denom <= 0:
        raise ValueError(f"self-locking geometry: mu*tan(alpha) >= 1 (mu={mu}, alpha={alpha_deg})")
    return (mu + t) / denom


# --- self-locking placement rule (D-GEN-2 resolution) --------------------------------------
SELF_LOCK_MARGIN_DEG = 10.0


def self_locking_angle(mu: float) -> float:
    """The retract angle at which the separation force diverges: μ·tanα′ = 1 ⇒ α′ = atan(1/μ)
    [Bayer p.14 / Fig.18 asymptote]. Beyond it the joint is permanent (cannot be pulled open)."""
    return math.degrees(math.atan(1.0 / mu))


def max_retract_angle(mu: float, margin_deg: float = SELF_LOCK_MARGIN_DEG) -> float:
    """Placement cap on α_out: stay margin° below the self-locking asymptote. A design that sits
    right at the asymptote is one μ-assumption away from a permanent lock, and μ for PETG is
    itself ASSUMPTION A-PETG-1 — so the margin is a hard rule, not a nicety (D-GEN-2)."""
    return self_locking_angle(mu) - margin_deg


def W_mate(P: float, mu: float, alpha_in_deg: float) -> float:
    """Mating (insertion) force [Bayer p.14]: W = P · (μ + tanα)/(1 − μ·tanα), α = insertion angle.
    Example I: 32.5 · 1.80 = 58.5 N."""
    return P * fig18_factor(mu, alpha_in_deg)


def W_sep(P: float, mu: float, alpha_out_deg: float) -> float:
    """Separation force [Bayer p.14]: same form as W_mate but with the RETURN angle α′ (the
    retraction/retract angle). α′ = 90° ⇒ self-locking (permanent joint)."""
    return P * fig18_factor(mu, alpha_out_deg)


# --- material helpers (ASSUMPTIONS) --------------------------------------------------------
def Es_secant(E: float, eps: float) -> float:
    """Strain-dependent secant modulus Es(ε) [Bayer Fig.16 defines it as σ/ε at the working
    strain]. Fig.16 carries Bayer PC resins only — NO PETG curve — so v0 uses a conservative
    flat approximation Es ≈ 0.75·E (PC falls to ~60–75% of E by ε≈2%). **ASSUMPTION** (G-S4:
    replace with a PETG secant curve or datasheet). `eps` accepted for interface stability /
    a future table lookup; unused in the flat approximation."""
    return 0.75 * E


def working_strain(eps_perm: float = EPS_PERM_PETG, frequent: bool = False,
                   safety: float = DEFAULT_SAFETY) -> float:
    """Working strain ε for dimensioning: ε_perm × (0.60 if frequent re-join else 1) × safety.
    The p.16 example is ε = ½ · ε_perm (single operation, safety 0.5)."""
    return eps_perm * (FREQ_FACTOR if frequent else 1.0) * safety

# --- card class (moved from base.py, verbatim) --------------------------------------------
from knowledge.cards.base import MechanicalElementCard, InteractionRule, _p  # noqa: E402
from ontology.schema import Citation, EmergentCheck  # noqa: E402

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
                "connection_principle": "form", "self_locking": False, "emergent_check": EmergentCheck(status="deferred", reason="elastic cantilever deflection is not expressible in a rigid-body engine (D3)", risk="snap mate/separation forces are Bayer-formula-verified only; the engagement event under real assembly is not physics-verified"),
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
