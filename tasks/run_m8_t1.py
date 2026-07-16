"""Drive Tier1 re-measurement (§5.3 / stage-⑧) on the COMPILED Easy anchor — both elements:

  E2 snap_hook  : re-measure L/h/b/y from the compiled hook solid (+ the Tier0 undercut) and
                  compare to ⑤'s RESOLVED params (COMPILE_DRIFT guard, the panel blind-spot check).
  E1 pin_hinge  : re-measure pin_d/pin_len/bore_d/knuckle_od from the compiled hinge tags and
                  compare to the card's resolved dims.

Both use the SAME geometry-vs-IR rule: |IR − measured| > 0.05 mm ⇒ StageFailure(COMPILE_DRIFT).
The IR reference is the resolved plan/formula value, NOT the compiled geometry (that distinction
is the whole point of Tier1 — see verify/t1_remeasure)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tasks.build_goldens import anchor_easy
from pipeline.compile_assembly import compile_assembly
from knowledge.cards.base import CARD_REGISTRY
from knowledge.templates import TEMPLATES
from knowledge.cards import snap_hook_geometry as shg
from verify.t0_static import three_way_check
from verify.t1_remeasure import remeasure_hook, remeasure_hinge, check_drift
from verify.t2_physics.runner import _hash


def _snap_carve(plan):
    """Re-run E2's carve on fresh host pieces to recover the CarveResult (dims + hook tag)."""
    pieces = {}
    for pc in plan.pieces:
        if pc.provenance == "hardware":
            continue
        tr = TEMPLATES[pc.template_ref](**{k: v for k, v in pc.params.items()
                                            if isinstance(v, (int, float))})
        pieces[pc.id] = tr
    # carve E1 first (motion before fasteners) so E2 sees the same host state the compiler used
    for eid in ("E1", "E2"):
        e = plan.element(eid)
        binds = [b for b in plan.bindings if b.element_id == eid]
        cr = CARD_REGISTRY[e.card_ref].carve(pieces, e, binds)
        cr_parts = getattr(cr, "parts", None) or cr["parts"]
        for pid, solid in cr_parts.items():
            if pid in pieces:
                pieces[pid] = type(pieces[pid])(part=solid, anchors=pieces[pid].anchors,
                                                params=pieces[pid].params)
        if eid == "E2":
            return cr, pieces
    return None, pieces


def main():
    plan = anchor_easy()
    ca = compile_assembly(plan)
    result = {"decision_row": "stage-⑧ Tier1 re-measure on compiled Easy anchor",
              "compile_hash": _hash(), "elements": {}}

    # --- E2 snap: t0 undercut → re-measure L/h/b/y ------------------------------------------
    cr, pieces = _snap_carve(plan)
    d = cr.dims[0] if isinstance(cr.dims, list) else cr.dims
    hook = cr.tags[f"hook_{d.side_tag}"]
    e2 = plan.element("E2")
    # undercut from the Tier0 three-way (measured penetration in the hook region)
    tw = three_way_check(receiver=pieces["P1"].part, mover=pieces["P2"].part,
                         hooks={d.side_tag: hook}, y=d.y,
                         engage_dirs={d.side_tag: d.engage_dir})
    meas = remeasure_hook(hook, d, tw.undercut_measured_mm)
    ir = {"L": float(e2.params["L_mm"]), "h": d.h_root, "b": float(e2.params["b_mm"]),
          "y": float(e2.params["y_mm"])}
    try:
        r = check_drift(d, meas, ir_params=ir)
        e2_ok, e2_rows = r.ok, r.rows
    except Exception as ex:
        e2_ok, e2_rows = False, ex.data["rows"]
    result["elements"]["E2_snap"] = {"ok": bool(e2_ok),
                                     "rows": [[k, i, m, dr, bool(o)] for k, i, m, dr, o in e2_rows],
                                     "undercut_measured_mm": round(tw.undercut_measured_mm, 4)}

    # --- E1 hinge: re-measure pin/bore/knuckle ----------------------------------------------
    g = CARD_REGISTRY["pin_hinge"]
    from knowledge.cards.pin_hinge import dims_from
    hd = dims_from(plan.element("E1").params, 40.0)
    hmeas = remeasure_hinge(ca.tags["E1"], ca.axes["E1"]["dir"])
    hir = {"pin_d": hd.pin_d, "pin_len": float(plan.piece("P3").params["pin_len"]),
           "bore_d": hd.bore_d, "knuckle_od": hd.knuckle_od}
    try:
        r = check_drift(None, hmeas, ir_params=hir)
        e1_ok, e1_rows = r.ok, r.rows
    except Exception as ex:
        e1_ok, e1_rows = False, ex.data["rows"]
    result["elements"]["E1_hinge"] = {"ok": bool(e1_ok),
                                      "rows": [[k, i, m, dr, bool(o)] for k, i, m, dr, o in e1_rows]}

    result["shape_assert"] = {"elements_covered": set(result["elements"]) == {"E2_snap", "E1_hinge"}}
    result["verdict"] = bool(e2_ok and e1_ok)

    for name, e in result["elements"].items():
        print(f"\n=== {name} ===  {'OK' if e['ok'] else 'COMPILE_DRIFT'}")
        for k, i, m, dr, o in e["rows"]:
            print(f"   {'ok  ' if o else 'DRIFT'} {k:11s} IR {i:8.4f}  measured {m:8.4f}  |Δ| {dr:.4f}")
    print("\nt1 verdict:", result["verdict"], " shape_assert:", result["shape_assert"])
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("verify/t2_physics/out_easy")
    out.mkdir(parents=True, exist_ok=True)
    (out / "t1_easy_verdict.json").write_text(json.dumps(result, indent=2))
    print("wrote", out / "t1_easy_verdict.json")


if __name__ == "__main__":
    main()
