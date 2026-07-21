"""M18 — Tier-1 element expansion + taxonomy tests (schema/ontology, no physics).

Golden-style: every new card's cited formula is reproduced to tolerance, its carve makes one solid,
its 7-axis taxonomy tag is present, and the ontology rules (ConnectionCard-not-realized_by, reject
compliant, the morphological-matrix narrowings) hold. If a formula assert fails, the CODE is wrong,
not the arithmetic (the source section is cited in knowledge/cards/m18_tier1.py).

Run:  ./bin/py tests/test_m18_elements.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from knowledge.cards.base import CARD_REGISTRY, ConnectionCard
from knowledge.kg import candidates
from ontology.schema import Behavior, MotionSpec

NEW = ["lead_screw", "coupling", "universal_joint", "journal_bearing", "bushing",
       "dowel_pin", "screw_boss", "press_fit"]
AXES = {"working_motion", "axis_relationship", "connection_principle", "self_locking",
        "vb_verifiable", "compliance", "kinematic_dof"}


class _I:
    def __init__(self, params=None, iid="E1"):
        self.params = params or {}
        self.id = iid


class _B:
    def __init__(self, port, pid="P1", anchor="a"):
        self.port, self.piece_id, self.anchor = port, pid, anchor


# --- taxonomy + three-category ontology ----------------------------------------------------------
def test_every_card_carries_the_7_axis_taxonomy():
    for cid, card in CARD_REGISTRY.items():
        tax = getattr(card, "taxonomy", {})
        assert AXES.issubset(set(tax)), f"{cid} missing axes {AXES - set(tax)}"


def test_three_card_categories_present():
    classes = {c.card_class for c in CARD_REGISTRY.values()}
    assert classes == {"element", "feature", "connection"}, classes
    conns = [cid for cid, c in CARD_REGISTRY.items() if c.card_class == "connection"]
    assert set(conns) == {"dowel_pin", "screw_boss", "press_fit"}, conns
    # connection_principle is a PROPERTY the ConnectionCard carries (m18 REVIEW §2.1)
    assert CARD_REGISTRY["dowel_pin"].connection_principle == "form"
    assert CARD_REGISTRY["screw_boss"].connection_principle == "force"
    assert CARD_REGISTRY["press_fit"].connection_principle == "force"
    for cid in conns:
        assert isinstance(CARD_REGISTRY[cid], ConnectionCard)


# --- formulas (cited; reproduced to tolerance) ---------------------------------------------------
def test_lead_screw_self_locks_when_lead_angle_le_friction_angle():
    """Shigley §8-2 / P&B §7.4.3: self-locks iff lambda=atan(lead/pi d_p) <= phi=atan(mu).
    d_major=8, lead=2, mu=0.30 -> d_p=7, lambda=5.20deg, phi=16.70deg -> SELF-LOCKS."""
    f = CARD_REGISTRY["lead_screw"].formula_check(_I({"d_major": 8, "lead": 2, "mu": 0.30}))
    d_p = 8 - 2 / 2
    assert abs(f["lead_angle_deg"] - math.degrees(math.atan(2 / (math.pi * d_p)))) < 1e-2
    assert abs(f["friction_angle_deg"] - math.degrees(math.atan(0.30))) < 1e-2
    assert f["self_locks"] is True
    # a coarse lead (fast travel) does NOT self-lock -> back-drives (needs a pawl, D-M13-4)
    f2 = CARD_REGISTRY["lead_screw"].formula_check(_I({"d_major": 8, "lead": 12, "mu": 0.30}))
    assert f2["self_locks"] is False


def test_self_locking_resolves_d_m13_3_axis_distinguishes_leadscrew_from_rackpinion():
    """The whole point of axis-4 (D-M18-3, resolving D-M13-3): lead_screw self-locks (holds a load
    with no brake); rack_pinion does not (needs a pawl_detent). The taxonomy now says so."""
    assert CARD_REGISTRY["lead_screw"].taxonomy["self_locking"] is True
    assert CARD_REGISTRY["rack_pinion"].taxonomy["self_locking"] is False


def test_screw_boss_pullout_matches_thread_shear_area_formula():
    """Bayer boss + Shigley thread shear: pull-out = pi * pilot_d * engagement * tau. screw_d=3,
    engagement=6, tau=30 -> pilot=2.4, area=pi*2.4*6=45.24, F=1357.2 N."""
    f = CARD_REGISTRY["screw_boss"].formula_check(_I({"screw_d": 3, "engagement": 6, "tau_shear": 30}))
    expect = math.pi * (0.8 * 3) * 6 * 30
    assert abs(f["pullout_force_N"] - expect) < 1.0, (f["pullout_force_N"], expect)
    assert abs(f["boss_od_mm"] - 6.0) < 1e-6 and abs(f["pilot_d_mm"] - 2.4) < 1e-6


def test_press_fit_holding_matches_interference_formula_and_flags_creep():
    """Shigley §3-56: p=E*delta/d (delta=2*interference), F=pi*d*L*p*mu. d=8,intf=0.05,L=10,E=2100,
    mu=0.30 -> delta=0.1, p=26.25 MPa, F=pi*8*10*26.25*0.30=1979.2 N. Creep caveat present."""
    f = CARD_REGISTRY["press_fit"].formula_check(_I({"d_nom": 8, "interference": 0.05, "length": 10}))
    p = 2100 * (2 * 0.05) / 8
    expect = math.pi * 8 * 10 * p * 0.30
    assert abs(f["pressure_MPa"] - p) < 1e-3
    assert abs(f["holding_force_N"] - expect) < 1.0
    assert "creep" in f["compliance_note"].lower(), "the honest PETG-creep caveat must be flagged"


def test_coupling_torque_and_ujoint_cardan_and_bearing_fit():
    ct = CARD_REGISTRY["coupling"].formula_check(_I({"bore_d": 8}))
    assert abs(ct["torque_capacity_Nmm"] - 25.0 * math.pi * 8 ** 3 / 16) < 1e-2
    assert ct["ratio"] == 1.0
    uj = CARD_REGISTRY["universal_joint"].formula_check(_I({"angle_deg": 20}))
    beta = math.radians(20)
    assert abs(uj["vel_ratio_max"] - 1 / math.cos(beta)) < 1e-3
    assert uj["fluctuation_pct"] > 0, "a single Cardan joint is NOT constant-velocity"
    jb = CARD_REGISTRY["journal_bearing"].formula_check(_I({"bore_d": 8}))
    assert jb["bore_id_mm"] > 8.0, "running clearance opens the bore"


# --- carve produces one solid; params resolve within bounds --------------------------------------
def test_every_new_card_carves_one_solid():
    ports = {"lead_screw": "screw_axis", "coupling": "shaft_in", "universal_joint": "shaft_in",
             "journal_bearing": "bore_mount", "bushing": "bore_mount", "dowel_pin": "location",
             "screw_boss": "boss_mount", "press_fit": "interface"}
    for cid in NEW:
        r = CARD_REGISTRY[cid].carve({}, _I(), [_B(ports[cid])])
        solid = list(r.tags.values())[0]
        assert len(solid.solids()) == 1, f"{cid} carve did not make one connected solid"
        assert solid.volume > 0


def test_resolve_params_stay_within_declared_bounds():
    class _Ir:
        behaviors = []
    for cid in NEW:
        card = CARD_REGISTRY[cid]
        out = card.resolve_params(_Ir(), _I({}, iid="E1"))
        for name, (lo, hi, _u) in card.param_bounds.items():
            if name in out and isinstance(out[name], (int, float)):
                assert lo <= out[name] <= hi, f"{cid}.{name}={out[name]} outside [{lo},{hi}]"


# --- the morphological-matrix narrowings (P&B §3.2.3 Zwicky) — at least two ----------------------
def test_kg_narrowing_self_locking_picks_lead_screw():
    b = Behavior(id="B", phase="use", motion=MotionSpec(kind="rot_to_trans"), self_locking=True)
    assert candidates(b) == ["lead_screw"], "self_locking rot_to_trans must narrow to lead_screw"
    # without the flag, BOTH are offered (rack_pinion + lead_screw)
    b0 = Behavior(id="B", phase="use", motion=MotionSpec(kind="rot_to_trans"))
    assert set(candidates(b0)) == {"rack_pinion", "lead_screw"}


def test_kg_narrowing_intersecting_axis_picks_universal_joint():
    b = Behavior(id="B", phase="use", motion=MotionSpec(kind="rotation"),
                 axis_relationship="intersecting")
    assert candidates(b) == ["universal_joint"], "intersecting-axis rotation -> universal_joint"


def test_kg_narrowing_connection_principle_picks_dowel_for_form():
    b = Behavior(id="B", phase="static", motion=MotionSpec(kind="fixed"))
    assert candidates(b, connection_principle="form") == ["dowel_pin"]
    assert set(candidates(b, connection_principle="force")) == {"screw_boss", "press_fit"}


# --- ontology rules: V-08 (connection not realized_by), V-17 (reject compliant) ------------------
def test_v08_rejects_connection_card_realized_by():
    from ontology.schema import Binding, DesignPlan, ElementInstance, HostTemplate, Anchor, Piece
    from ontology.validators import v08
    # a dowel_pin (ConnectionCard) placed as an element, with a behaviour trying to be realized by it
    plan = DesignPlan(task_id="t", command="c",
                      pieces=[Piece(id="P1", role="base", template_ref="box_shell", is_base=True)],
                      templates=[HostTemplate(template_ref="box_shell",
                                              anchors=[Anchor(name="a", kind="point")])],
                      elements=[ElementInstance(id="E1", card_ref="dowel_pin", host_pieces=["P1"])],
                      behaviors=[Behavior(id="B1", phase="static", motion=MotionSpec(kind="fixed"),
                                          realized_by="E1")])
    vs = v08(plan)
    assert any("ConnectionCard" in v.detail and "realized_by" in v.detail for v in vs), \
        "a ConnectionCard may not be realized_by (D-M18-1)"


def test_v17_rejects_compliant_with_pspring_message():
    from ontology.schema import DesignPlan, ElementInstance, Piece, HostTemplate, Anchor
    from ontology.validators import v17
    card = CARD_REGISTRY["coupling"]
    orig = card.compliance
    try:
        card.compliance = "compliant"                 # simulate a future compliant card (no P-SPRING)
        plan = DesignPlan(task_id="t", command="c",
                          pieces=[Piece(id="P1", role="base", template_ref="box_shell", is_base=True)],
                          templates=[HostTemplate(template_ref="box_shell",
                                                  anchors=[Anchor(name="a", kind="point")])],
                          elements=[ElementInstance(id="E1", card_ref="coupling", host_pieces=["P1"])])
        vs = v17(plan)
        assert any("P-SPRING" in v.detail and "compliant" in v.detail for v in vs), \
            "compliance='compliant' must be rejected with the P-SPRING message (D-M18-2)"
    finally:
        card.compliance = orig
    assert not v17(plan), "with compliance restored to rigid, V-17 must pass"


# --- hardware orthogonality: a ConnectionCard can ALSO provide hardware (m18 REVIEW §2.2) --------
def test_screw_boss_is_a_connection_that_provides_the_screw_as_hardware():
    card = CARD_REGISTRY["screw_boss"]
    assert card.card_class == "connection"
    roles = {pp.role for pp in card.provides_pieces}
    assert "fastener" in roles, "the screw_boss provides its screw as hardware (D-ONT-11)"
    pp = card.resolve_piece_params("screw", _I({"screw_d": 3, "engagement": 6}))
    assert pp["screw_d"] == 3 and pp["screw_len"] > 6


# --- default fields keep every existing golden IR valid ------------------------------------------
def test_new_schema_defaults_keep_goldens_valid():
    from tasks.build_goldens import anchor_easy, snap_starter
    from ontology.validators import validate_all
    for plan in (anchor_easy("stop"), anchor_easy("nostop"), snap_starter()):
        # the new fields default (nature=regular, axis_relationship=parallel, self_locking=False),
        # so the golden still parses AND still validates clean.
        vs = validate_all(plan)
        assert not vs, f"golden {plan.task_id} broke: {[v.rule for v in vs]}"
        for b in plan.behaviors:
            assert b.motion.nature == "regular" and b.axis_relationship == "parallel"
            assert b.self_locking is False


if __name__ == "__main__":
    fns = [test_every_card_carries_the_7_axis_taxonomy, test_three_card_categories_present,
           test_lead_screw_self_locks_when_lead_angle_le_friction_angle,
           test_self_locking_resolves_d_m13_3_axis_distinguishes_leadscrew_from_rackpinion,
           test_screw_boss_pullout_matches_thread_shear_area_formula,
           test_press_fit_holding_matches_interference_formula_and_flags_creep,
           test_coupling_torque_and_ujoint_cardan_and_bearing_fit,
           test_every_new_card_carves_one_solid, test_resolve_params_stay_within_declared_bounds,
           test_kg_narrowing_self_locking_picks_lead_screw,
           test_kg_narrowing_intersecting_axis_picks_universal_joint,
           test_kg_narrowing_connection_principle_picks_dowel_for_form,
           test_v08_rejects_connection_card_realized_by,
           test_v17_rejects_compliant_with_pspring_message,
           test_screw_boss_is_a_connection_that_provides_the_screw_as_hardware,
           test_new_schema_defaults_keep_goldens_valid]
    for f in fns:
        f()
    print(f"{len(fns)}/{len(fns)} passed  — M18: 8 Tier-1 cards (3 categories), 7-axis taxonomy, "
          f"cited formulas reproduced, morphological narrowings (self_lock->lead_screw, "
          f"intersecting->uni_joint, form->dowel), V-08 connection rule + V-17 compliant guard")
