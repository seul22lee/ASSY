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
    """t2 collision hints = template seating prims + card hints, per piece (D-ONT-11 provenance)."""
    bp = plan.piece("P1").params
    lp = {**plan.piece("P2").params, "box_h": bp["box_h"]}
    e1 = plan.element("E1")
    wedges = CARD_REGISTRY["pin_hinge"].collision_hint(e1)          # ring-of-wedges, owner A/B
    axis = ca.axes["E1"]
    ap = axis["point"]                                              # mm, on the axis
    p3 = plan.piece("P3").params
    pin_r, pin_len = p3["pin_d"] / 2.0, p3["pin_len"]
    # the pin: a cylinder along the world axis (+X). local +Z → +X via euler (0,90,0).
    pin_cyl = {"type": "cylinder", "frame": "world", "pos": tuple(ap), "cclass": "mech",
               "size": (pin_r, pin_len / 2.0), "euler_world": (0.0, 90.0, 0.0)}
    # NO invented open-stop. An end stop must come from the IR (a stop_flange PassiveFeature whose
    # imposed B3-class rotation limit V-08 registers) and be REAL geometry in the carve — never a
    # collision prim conjured in the physics driver. The baseline anchor_easy has no stop_flange, so
    # it HAS no stop: past 90° the over-centre lid folds right over, and that fold-over is the
    # finding (M0 hinge_box: "no stop: the lid is free to fold flat. That is the finding.") — V-B
    # exists precisely to expose it, so suppressing it would defeat the mode's whole purpose.
    hints = {
        "P1": box_shell_collision(**bp) + [w for w in wedges if w.get("owner") == "A"],
        "P2": lid_panel_collision(**lp) + [w for w in wedges if w.get("owner") == "B"],
        "P3": [pin_cyl],
    }
    # PassiveFeature collision, straight from the IR: a stop_flange in the plan means real carved
    # flange geometry on its host, so its (exact, box) proxy joins that piece's hints. If the plan
    # declares no feature, no stop geometry exists and none is added — the fold-over stands.
    for f in plan.features:
        card = CARD_REGISTRY[f.card_ref]
        host = next(b.piece_id for b in plan.bindings if b.element_id == f.id)
        host_params = lp if host == "P2" else plan.piece(host).params
        prims = card.collision_hint(f, host_params, axis)
        if prims:
            hints[host] = hints.get(host, []) + prims
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
    plan = anchor_easy(variant=variant) if variant else anchor_easy()
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
    tag = f"easy_{plan.variant}" if plan.variant else "easy"
    print(f"variant={plan.variant or 'baseline (no stop)'}  stop_angle_from_IR={stop_deg}")
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("verify/t2_physics/out_easy")
    res = t2(parts, hints, ca.axes["E1"], roles, ["V-A", "V-B"], out,
             "P1", "P2", "P3", tag, tip_point=tip, latch_point=latch,
             clearance=clearance, protrusion=protrusion, stop_angle_deg=stop_deg,
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
