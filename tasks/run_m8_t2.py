"""Drive stage-⑨ Tier2 (P-HINGE V-A + V-B) on the COMPILED Easy anchor. Builds the t2 hints by
composing the template seating primitives (box floor+walls, lid inset panel — D14) with the card
collision hints (hinge ring-of-wedges, owner-tagged; pin cylinder along the axis), then runs both
verification modes, 5 seeds each, seed-0 recorded with the HUD."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tasks.build_goldens import anchor_easy
from pipeline.compile_assembly import compile_assembly
from knowledge.cards.base import CARD_REGISTRY
from knowledge.templates.host_templates import box_shell_collision, lid_panel_collision
from verify.t2_physics.runner import t2


def build_hints(plan, ca):
    """t2 collision hints = template seating prims + card hints, per piece — every prim carrying the
    `source` its producer stamped (D-M8-4; build_mjcf refuses anything unsourced).

    Nothing is built HERE. The driver only ROUTES what the cards and templates emit: card prims carry
    an `owner` (A → base host, B → mover host, pin → the hardware piece the element provides), and
    template prims go to the piece whose template_ref produced them. That is deliberate — the
    retracted open-stop was driver-built geometry, and a driver that cannot author prims cannot
    repeat that mistake.
    """
    bp = plan.piece("P1").params
    lp = {**plan.piece("P2").params, "box_h": bp["box_h"]}
    axis = ca.axes["E1"]
    owner_pid = {"A": "P1", "B": "P2", "pin": "P3"}

    hints = {"P1": box_shell_collision(**bp), "P2": lid_panel_collision(**lp), "P3": []}
    # MechanicalElement hints (the hinge: ring-of-wedges + the pin it provides, D-ONT-11)
    for e in plan.elements:
        prims = CARD_REGISTRY[e.card_ref].collision_hint(e)
        for prim in prims or []:
            pid = owner_pid.get(prim.get("owner"))
            if pid:
                hints[pid].append(prim)
    # PassiveFeature hints (the stop_flange, when the plan declares one)
    for f in plan.features:
        host = next(b.piece_id for b in plan.bindings if b.element_id == f.id)
        host_params = lp if host == "P2" else plan.piece(host).params
        prims = CARD_REGISTRY[f.card_ref].collision_hint(f, host_params, axis)
        hints[host] = hints.get(host, []) + list(prims or [])
    return hints


def stop_angle_from_ir(plan) -> float:
    """The design stop angle READ FROM THE IR: the range_value of a use-phase rotation behaviour
    with bound='max' that a PassiveFeature imposes (the B3-class limit a stop_flange registers per
    V-08). No such behaviour ⇒ inf ⇒ the plan declares NO stop, and the lid is free to fold flat.
    This is the only legitimate source: a stop the IR does not carry does not exist."""
    for b in plan.behaviors:
        m = b.motion
        if (b.imposed_by and getattr(m, "kind", None) == "rotation"
                and getattr(m, "bound", None) == "max" and getattr(m, "range_value", None)):
            if plan.feature(b.imposed_by):        # imposed by a PassiveFeature (stop_flange)
                return float(m.range_value)
    return float("inf")


def main():
    variant = sys.argv[2] if len(sys.argv) > 2 else None
    plan = anchor_easy(variant) if variant else anchor_easy()
    ca = compile_assembly(plan)
    hints = build_hints(plan, ca)
    roles = {"P1": "base", "P2": "mover", "P3": "hardware"}
    parts = {pid: ca.parts[pid] for pid in ("P1", "P2", "P3")}

    bp = plan.piece("P1").params
    tip = (0.0, bp["box_w"] / 2.0, bp["box_h"])                     # lid free edge (front), mm
    latch = (0.0, bp["box_w"] / 2.0 - bp["wall"], bp["box_h"] * 0.7)  # front latch catch point
    e1 = plan.element("E1")
    clearance = float(e1.params.get("clearance", 0.2))
    protrusion = 3.0                                               # PROTRUDE (pin_hinge PROTRUDE)

    stop_deg = stop_angle_from_ir(plan)
    # the BENCHMARK (stop) is plain "easy"; the D20 demo is tagged by its variant
    tag = "easy" if plan.variant == "stop" else f"easy_{plan.variant}"
    print(f"variant={plan.variant or 'baseline (no stop)'}  stop_angle_from_IR={stop_deg}")
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("verify/t2_physics/out_easy")
    res = t2(parts, hints, ca.axes["E1"], roles, ["V-A", "V-B"], out,
             "P1", "P2", "P3", tag, tip_point=tip, latch_point=latch,
             clearance=clearance, protrusion=protrusion, stop_angle_deg=stop_deg, plan=plan,
             expected_fail=("expected: fold-over, no angular limit — the lid has no stop_flange, so "
                            "past 90° the over-centre lid folds flat (D20 demo golden)"
                            if plan.variant == "nostop" else ""),
             decision_row="stage-⑨ P-HINGE on compiled Easy anchor")

    for mode, e in res["modes"].items():
        print(f"\n=== {mode} ===  G-CONV {'ok' if e['g9_gconv'] else 'FAIL'}")
        ph = e.get("p_hinge", {})
        if not ph.get("ran"):
            print("   P-HINGE not run:", ph.get("reason")); continue
        print(f"   seeds {ph['seeds_passed']}/{ph['n_seeds']}  =>  {'PASS' if ph['passed'] else 'FAIL'}")
        for name, c in ph["criteria_seed0"].items():
            print(f"      {'ok  ' if c['pass'] else 'FAIL'} {name:<50s} {c['value']} (<= {c['threshold']})")
        print(f"      video: {ph.get('video')}   plot: {ph.get('plot')}")
    print("\nverdict:", res["verdict"], " shape_assert:", res["shape_assert"])
    import json
    (out / f"t2_{tag}_verdict.json").write_text(json.dumps(res, indent=2))
    print("wrote", out / f"t2_{tag}_verdict.json")


if __name__ == "__main__":
    main()
