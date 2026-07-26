"""stop_flange PassiveFeature card (M18 refactor: moved from base.py; geometry stays paired
in stop_flange_geometry.py). No logic change."""

from knowledge.cards.base import PassiveFeatureCard, _p
from ontology.schema import Behavior, Citation, EmergentCheck, MotionSpec  # noqa: F401


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
    taxonomy = {"working_motion": ("rotation", "regular"), "axis_relationship": "parallel",
                "connection_principle": None, "self_locking": False, "emergent_check": EmergentCheck(status="verified"),
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
