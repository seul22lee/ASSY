"""Generate the m2_ontology review artifacts (D-ONT-7).

Writes into m2_ontology/out/:
  ir_<task>.mmd / .svg         IR graph per golden (mermaid primary + SVG)
  ir_diff_stop_vs_nostop.svg   the stop-vs-nostop delta (stop_flange feature must be the red)
  schema_map.svg               ontology class map
  validator_matrix.svg         V-01..V-13 × goldens, all green

Run:  ./bin/py m2_ontology/build_review.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tasks.build_goldens import m0_hinge_box, snap_starter
from viz.ir_graph import diff_svg, to_mermaid, to_svg
from viz.schema_map import schema_map_svg, validator_matrix_svg
from ontology import validators as V

OUT = Path(__file__).parent / "out"

RULE_TEXT = [
    ("V-01", "use behavior has verified_by protocol"),
    ("V-02", "binding anchor exists in target template"),
    ("V-03", "binding port exists in element/feature card"),
    ("V-04", "parameter value within [lo,hi]"),
    ("V-05", "material satisfies card requires"),
    ("V-06", "rot_to_trans behavior has transmission"),
    ("V-07", "no orphan pieces (bound or base)"),
    ("V-08", "imposed behaviors registered; passive realizes nothing"),
    ("V-09", "on_face_uv has u,v in [0,1]"),
    ("V-10", "DesignPlan round-trips losslessly"),
    ("V-11", "snap_event has event_force_window_N"),
    ("V-12", "RESERVED (keepout) — no-op"),
    ("V-13", "measurement keys in controlled registry"),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    plans = {
        "T-S1": snap_starter(),
        "m0_stop": m0_hinge_box("stop"),
        "m0_nostop": m0_hinge_box("nostop"),
    }

    # --- IR graphs (mermaid + svg) ----------------------------------------------------
    for name, plan in plans.items():
        (OUT / f"ir_{name}.mmd").write_text(to_mermaid(plan))
        (OUT / f"ir_{name}.svg").write_text(to_svg(plan))
        print(f"  ir_{name}.mmd / .svg")

    # --- stop vs nostop diff ----------------------------------------------------------
    (OUT / "ir_diff_stop_vs_nostop.svg").write_text(
        diff_svg(plans["m0_nostop"], plans["m0_stop"]))
    print("  ir_diff_stop_vs_nostop.svg")

    # --- schema map -------------------------------------------------------------------
    (OUT / "schema_map.svg").write_text(schema_map_svg())
    print("  schema_map.svg")

    # --- validator matrix -------------------------------------------------------------
    rule_fns = {rid: getattr(V, "v" + rid.split("-")[1]) for rid, _ in RULE_TEXT}
    results = {}
    all_green = True
    for name, plan in plans.items():
        for rid, fn in rule_fns.items():
            ok = (fn(plan) == [])
            results[(rid, name)] = ok
            all_green = all_green and ok
    (OUT / "validator_matrix.svg").write_text(
        validator_matrix_svg(RULE_TEXT, list(plans), results))
    print(f"  validator_matrix.svg  (all_green={all_green})")

    # cross-check: validate_all agrees the goldens are clean
    for name, plan in plans.items():
        viols = V.validate_all(plan)
        assert viols == [], f"{name} not clean: {[(v.rule, v.detail) for v in viols]}"
    print("  all goldens validate_all() CLEAN")


if __name__ == "__main__":
    main()
