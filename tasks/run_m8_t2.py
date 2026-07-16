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
    # The hinge's designed OPEN-SIDE STOP (the lug hard-stop, formalized). In V-A the declared joint
    # range is the stop; V-B is contact-only, so the stop must be a geom — a ledge behind the axis
    # that the lid leans on at STOP_ANGLE (~107°). Seat-class (it catches the lid panel), V-B only.
    stop = {"type": "box", "frame": "world", "pos": (ap[0], ap[1] - 10.0, ap[2] + 8.0),
            "size": (bp["box_l"] / 2 - 2.0, 2.0, 10.0), "modes": ["V-B"], "role_hint": "open_stop"}
    hints = {
        "P1": box_shell_collision(**bp) + [w for w in wedges if w.get("owner") == "A"] + [stop],
        "P2": lid_panel_collision(**lp) + [w for w in wedges if w.get("owner") == "B"],
        "P3": [pin_cyl],
    }
    return hints


STOP_ANGLE_DEG = 107.0   # measured open-stop angle of the V-B backstop (design lug hard-stop)


def main():
    plan = anchor_easy()
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

    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("verify/t2_physics/out_easy")
    res = t2(parts, hints, ca.axes["E1"], roles, ["V-A", "V-B"], out,
             "P1", "P2", "P3", "easy", tip_point=tip, latch_point=latch,
             clearance=clearance, protrusion=protrusion, stop_angle_deg=STOP_ANGLE_DEG,
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
    (out / "t2_easy_verdict.json").write_text(json.dumps(res, indent=2))
    print("wrote", out / "t2_easy_verdict.json")


if __name__ == "__main__":
    main()
