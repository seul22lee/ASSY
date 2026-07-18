"""m14 TASK LADDER — the 15±5 benchmark task set + certification (D-M14-1).

No new cards/templates, no LLM calls. Each task is a real-sounding COMMAND plus the golden IR it
implies (built from the existing parameterized builders). A task ENTERS the set only if it certifies:
  - PASS         → validator-CLEAN, ⑤ resolves, ⑥ compiles, and its physics protocols pass (reused
                   from the base's certified verdict where the mechanism is unchanged, or a real
                   measured number where a spec tightens a gate).
  - EXPECTED_FAIL → a legal IR whose physics verdict must fail (kept as a regression target).
  - INFEASIBLE(layer, code) → the deterministic pipe refuses it at the DECLARED layer with the
                   DECLARED code (validator V-xx, ⑤ StageFailure, or a KG no-realizer).

Run:  ./bin/py tasks/benchmark/benchmark.py     (writes manifest.json + certification_matrix.json)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ontology.schema import (Behavior, Binding, Criterion, DesignPlan, ElementInstance, Function,  # noqa: E402
                             MotionSpec, Piece, VerificationProtocol)
from ontology.validators import validate_all  # noqa: E402
from knowledge.kg import candidates  # noqa: E402
from pipeline.compile_assembly import compile_assembly  # noqa: E402
from pipeline.s5_geometry import resolve_plan  # noqa: E402
from pipeline.stage_failure import StageFailure  # noqa: E402
from knowledge.cards.base import CARD_REGISTRY  # noqa: E402
from tasks.build_goldens import anchor_easy, anchor_hard, anchor_lift, snap_starter  # noqa: E402

OUT = Path(__file__).parent


# ---- helpers for constraint variants (NO new cards — reshape an existing golden) ---------------
def easy_no_latch(box_l=80.0, box_w=60.0, box_h=40.0):
    """B3: strip the snap latch (E2) from the stop-variant Easy anchor → a hinge that opens and
    stays put on its stop, no latch. Removes E2 + its bindings/behaviours/protocols + the exclusion
    AR that referenced it — the 'forbid the latch' constraint realised deterministically."""
    p = anchor_easy("stop", box_l=box_l, box_w=box_w, box_h=box_h)
    p.elements = [e for e in p.elements if e.id != "E2"]
    p.bindings = [b for b in p.bindings if b.element_id != "E2"]
    p.behaviors = [b for b in p.behaviors if b.realized_by != "E2" and b.imposed_by != "E2"]
    p.protocols = [pr for pr in p.protocols if pr.id not in ("PR-LATCH", "PR-SWEEP")]
    p.assembly_rules = [a for a in p.assembly_rules
                        if not any(str(sub).split(".")[0] == "E2" for sub in (a.subjects or []))]
    return p


def implied_screw_jack():
    """D1 (out-of-vocab): the IR a 'leadscrew screw-jack' implies — a host template AND an element
    card that are NOT in our vocabulary. The deterministic validators refuse it (V-02 unknown
    template, V-03 unregistered card)."""
    return DesignPlan(
        task_id="screw_jack_ovv", command="threaded screw-jack lift",
        functions=[Function(verb="position", object="load", qualifier="screw lift")],
        behaviors=[Behavior(id="B1", phase="use", realized_by="E1", verified_by="P1",
                            motion=MotionSpec(kind="rot_to_trans", transmission={"mm_per_rev": 2.0}))],
        pieces=[Piece(id="P1", role="base", template_ref="leadscrew_column", is_base=True)],
        elements=[ElementInstance(id="E1", card_ref="leadscrew", host_pieces=["P1"])],
        bindings=[Binding(element_id="E1", port="nut_travel", piece_id="P1", anchor="shaft",
                          mate="coincident_axis")],
        protocols=[VerificationProtocol(id="P1", verifies="B1", mode="V-A",
                   actuation={"kind": "shaft_velocity"},
                   criteria=[Criterion(name="lifts", observable="stroke_mm", op=">=", threshold=1.0,
                                       unit="mm")])])


# ---- the ladder ---------------------------------------------------------------------------------
# each task: id, command, base, axis, expected, build(), physics-evidence, scoring note
TASKS = [
    # ---------- Base A: push-on snap-lid box ----------
    dict(id="A1-snap-base", base="snap-box", axis="base", expected="PASS",
         command="Design a snap-lid box I can push shut and pull open by hand. Plastic, for 3D printing.",
         build=lambda: snap_starter(),
         physics=dict(tier="tier1-reused", evidence="m6_ms_closeout (T-S1 formula PASS)", passes=True),
         note="base snap box; certifies the T-S1 track."),
    dict(id="A2-snap-big", base="snap-box", axis="dimensional", expected="PASS",
         command="Design a snap-lid storage box about 120 × 90 × 50 mm that pushes shut and pulls open by hand. Plastic.",
         build=lambda: snap_starter(box_l=120.0, box_w=90.0, box_h=50.0, n_hooks=3),
         physics=dict(tier="tier1", evidence="resolve_snap feasible at the larger size, 3 hooks", passes=True),
         note="dimensional: bigger box + 3 hooks; ⑤ re-resolves within bounds."),
    dict(id="A3-snap-force", base="snap-box", axis="spec-tightening", expected="PASS",
         command="Design a push-on snap-lid box that closes with no more than 60 N by hand and needs at least 15 N of pull to open.",
         build=lambda: snap_starter(window_mate=(0.0, 60.0), window_sep=(15.0, 60.0)),
         physics=dict(tier="tier1", evidence="resolve_snap force windows satisfied (mate ≤60, sep ≥15)", passes=True),
         note="spec: explicit force window the ⑤ formula chain must hit."),
    dict(id="A4-snap-impossible-force", base="snap-box", axis="infeasible-spec", expected="INFEASIBLE",
         command="Design a snap-lid box that closes with at most 5 N by hand but needs at least 60 N of pull to open.",
         build=lambda: snap_starter(window_mate=(0.0, 5.0), window_sep=(60.0, 90.0)),
         layer="s5", code="INFEASIBLE",
         physics=dict(tier="none", evidence="⑤ resolve_snap: force windows unsatisfiable", passes=None),
         note="physically-contradictory: retention/mating ratio the snap geometry cannot achieve."),

    # ---------- Base B: hinged latch box ----------
    dict(id="B1-hinge-latch-base", base="hinge-box", axis="base", expected="PASS",
         command="A small hinged box whose lid latches shut at the front. Plastic, for 3D printing.",
         build=lambda: anchor_easy("stop"),
         physics=dict(tier="reused", evidence="m8 Easy anchor V-A 5/5 + V-B 5/5", passes=True),
         note="base hinge+latch (+stop); the Easy benchmark."),
    dict(id="B2-hinge-big", base="hinge-box", axis="dimensional", expected="PASS",
         command="A hinged box with a 100 × 70 mm lid that latches shut at the front. Plastic.",
         build=lambda: anchor_easy("stop", box_l=100.0, box_w=70.0),
         physics=dict(tier="inherited", evidence="same mechanism as B1, box in-bounds", passes=True),
         note="dimensional: larger box footprint."),
    dict(id="B3-hinge-nolatch", base="hinge-box", axis="constraint", expected="PASS",
         command="A hinged box whose lid opens and stays put near 110° — no latch, just a stop.",
         build=lambda: easy_no_latch(),
         physics=dict(tier="inherited", evidence="hinge+stop of B1 (latch removed); stop caps ~109°", passes=True),
         note="constraint: FORBID the latch — the golden visibly drops the snap element."),
    dict(id="B4-hinge-nostop", base="hinge-box", axis="constraint", expected="EXPECTED_FAIL",
         command="A hinged box whose lid opens 90° and returns closed — no stop tab, no latch.",
         build=lambda: anchor_easy("nostop"),
         physics=dict(tier="reused", evidence="anchor_easy_nostop V-B 0/5 (folds flat, D20)", passes=False),
         note="constraint→EXPECTED_FAIL: the over-centre lid folds flat with no stop (kept as a regression)."),
    dict(id="B5-hinge-openangle", base="hinge-box", axis="spec-tightening", expected="PASS",
         command="A hinged box whose lid opens at least 100° and settles closed within 5°.",
         build=lambda: anchor_easy("stop", open_min=100.0),
         physics=dict(tier="reused", evidence="m8 measured theta_max 112.4° ≥ 100° (stop cap)", passes=True),
         note="spec: open-angle floor the P-HINGE gate must clear (real measured 112.4°)."),

    # ---------- Base C: crank lift (+ drawer alternate) ----------
    dict(id="C1-lift-base", base="crank-lift", axis="base", expected="PASS",
         command="Design a crank-operated platform that raises and lowers a load to different heights.",
         build=lambda: anchor_lift(),
         physics=dict(tier="reused", evidence="m13 lift V-A 5/5 + P-FULL 5/5 + P-SLIDE V-B 5/5", passes=True),
         note="base crank lift; the Hard benchmark."),
    dict(id="C2-lift-load", base="crank-lift", axis="dimensional", expected="PASS",
         command="Design a crank platform that raises a 1 kg load by about 90 mm.",
         build=lambda: anchor_hard(variant="lift", stroke=90.0, load_kg=1.0),
         physics=dict(tier="inherited", evidence="same mechanism as C1; load 1 kg, stroke 90 in-bounds", passes=True),
         note="dimensional: heavier load, shorter stroke."),
    dict(id="C3-lift-holddrift", base="crank-lift", axis="spec-tightening", expected="PASS",
         command="Design a crank lift whose platform holds within 5 mm of its set height when the crank is released, under a 0.5 kg load.",
         build=lambda: anchor_lift(),
         physics=dict(tier="reused", evidence="m13 P-FULL hold-drop 3.37 mm ≤ 5 mm (pawl)", passes=True),
         note="spec: hold-drift ceiling the pawl (P-HOLD) must clear (real measured 3.37 mm)."),
    dict(id="C4-drawer", base="crank-lift", axis="constraint", expected="PASS",
         command="Design a desktop cabinet whose drawer slides out horizontally when you turn a knob.",
         build=lambda: anchor_hard("drawer"),
         physics=dict(tier="reused", evidence="m13 drawer V-A 5/5 (t2_hard_verdict)", passes=True),
         note="constraint: HORIZONTAL travel (no gravity-hold) — the drawer alternate, gear NOT over-engineered here."),
    dict(id="C5-lift-nogear", base="crank-lift", axis="infeasible-constraint", expected="INFEASIBLE",
         command="Design a crank lift that holds a 0.5 kg load, but without any gear or ratchet.",
         build=None, layer="s4", code="KG_NO_PERMITTED_REALIZER",
         forbidden=["rack_pinion", "pawl_detent"],
         physics=dict(tier="none", evidence="④ KG: the only rot_to_trans realizer is forbidden", passes=None),
         note="constraint-contradiction: a crank→lift needs rot_to_trans, whose ONLY card is rack_pinion; forbidding gear+ratchet leaves no realizer AND no hold."),
    dict(id="C6-lift-toofar", base="crank-lift", axis="infeasible-dimensional", expected="INFEASIBLE",
         command="Design a crank lift that raises the platform 500 mm inside a compact desktop frame.",
         build=lambda: anchor_hard(variant="lift", stroke=500.0),
         layer="validator", code="V-04",
         physics=dict(tier="none", evidence="stroke 500 outside the card bound [20,400]", passes=None),
         note="dimensional-exceeds: the requested stroke is beyond the slide/gear param bounds."),

    # ---------- Out-of-vocabulary ----------
    dict(id="D1-screw-jack", base="(none)", axis="infeasible-oov", expected="INFEASIBLE",
         command="Design a threaded screw-jack that lifts a load by turning a leadscrew.",
         build=implied_screw_jack, layer="validator", code="V-03",
         physics=dict(tier="none", evidence="leadscrew card + column template ∉ vocabulary", passes=None),
         note="out-of-vocabulary: names a host + element we do not have (no leadscrew card/template)."),
]


def certify_one(t: dict) -> dict:
    """Run the task's golden through the deterministic pipe and record the per-stage verdict."""
    row = {"id": t["id"], "expected": t["expected"], "stages": {}}
    exp = t["expected"]

    if exp == "INFEASIBLE":
        code, layer = t["code"], t["layer"]
        if layer == "s4":                       # KG no-permitted-realizer (constraint-contradiction)
            from ontology.schema import Behavior as _B, MotionSpec as _M
            beh = _B(id="B", phase="use", motion=_M(kind="rot_to_trans", transmission={"mm_per_rev": 1}))
            cand = [c for c in candidates(beh) if c not in t.get("forbidden", [])]
            ok = (len(cand) == 0)
            row["stages"]["④ KG"] = f"candidates(rot_to_trans) − forbidden = {cand} → {'EMPTY (refused)' if ok else 'NONEMPTY'}"
            row["fired"] = ok
            row["refusal"] = (f"④ KG_NO_PERMITTED_REALIZER: the only rot_to_trans realizer is "
                              f"'rack_pinion' (KG), forbidden by the task; no permitted card can "
                              f"realize the crank→lift transmission or the hold.")
        elif layer == "s5":                     # ⑤ StageFailure(INFEASIBLE)
            p = t["build"]()
            row["stages"]["validators"] = "clean" if not validate_all(p) else "DIRTY"
            try:
                resolve_plan(p); row["fired"] = False; row["stages"]["⑤ resolve"] = "NO FAILURE"
            except StageFailure as e:
                ok = (e.stage == "s5" and e.code == code)
                row["fired"] = ok
                row["stages"]["⑤ resolve"] = f"StageFailure({e.stage}/{e.code})"
                row["refusal"] = str(e)
        else:                                   # validator (V-xx)
            p = t["build"]()
            viols = validate_all(p)
            hit = [v for v in viols if v.rule == code]
            row["fired"] = bool(hit)
            row["stages"]["validators"] = f"{sorted(set(v.rule for v in viols))}"
            row["refusal"] = f"{code}: " + (hit[0].detail if hit else "(expected rule not raised)")
        row["verdict"] = "CERTIFIED" if row.get("fired") else "UNCERTIFIED"
        return row

    # PASS / EXPECTED_FAIL — the golden must be legal and buildable
    p = t["build"]()
    viols = validate_all(p)
    row["stages"]["validators"] = "clean" if not viols else f"{sorted(set(v.rule for v in viols))}"
    ok_val = not viols
    ok_res = ok_comp = False
    if ok_val:
        try:
            resolve_plan(p)                          # ⑤ snap force-windows (no-op for hinge/slide/gear)
            for e in p.elements:                     # mechanical cards resolve here; snap/hinge are baked
                try:
                    e.params = CARD_REGISTRY[e.card_ref].resolve_params(p, e)
                except NotImplementedError:
                    pass
            row["stages"]["⑤ resolve"] = "ok"; ok_res = True
        except StageFailure as e:
            row["stages"]["⑤ resolve"] = f"StageFailure({e.stage}/{e.code})"
        except Exception as e:
            row["stages"]["⑤ resolve"] = f"ERR {type(e).__name__}: {str(e)[:40]}"
        if ok_res:
            try:
                ca = compile_assembly(p)
                row["stages"]["⑥ compile"] = f"{len(ca.parts)} bodies"; ok_comp = True
            except Exception as e:
                row["stages"]["⑥ compile"] = f"ERR {type(e).__name__}: {str(e)[:50]}"
    ph = t["physics"]
    row["stages"]["physics"] = f"{ph['tier']} — {'PASS' if ph['passes'] else 'FAIL' if ph['passes'] is False else '—'}"
    row["physics_evidence"] = ph["evidence"]
    deterministic_ok = ok_val and ok_res and ok_comp
    if exp == "PASS":
        row["verdict"] = "CERTIFIED" if (deterministic_ok and ph["passes"]) else "UNCERTIFIED"
    else:  # EXPECTED_FAIL
        row["verdict"] = "CERTIFIED" if (deterministic_ok and ph["passes"] is False) else "UNCERTIFIED"
    return row


def main():
    rows = [certify_one(t) for t in TASKS]
    manifest = [{"id": t["id"], "command": t["command"], "base": t["base"], "axis": t["axis"],
                 "expected_class": (t["expected"] if t["expected"] != "INFEASIBLE"
                                    else f"INFEASIBLE({t['layer']},{t['code']})"),
                 "physics_implied": t["physics"]["evidence"] if t["physics"]["passes"] else
                                    (t["physics"]["evidence"] if t["expected"] != "INFEASIBLE" else None),
                 "scoring_note": t["note"]} for t in TASKS]
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    (OUT / "certification_matrix.json").write_text(json.dumps(rows, indent=2))
    refusals = {r["id"]: r.get("refusal") for r in rows if r.get("refusal")}
    (OUT / "refusals.json").write_text(json.dumps(refusals, indent=2))

    gdir = OUT / "goldens"; gdir.mkdir(exist_ok=True)
    for t in TASKS:
        if t["expected"] in ("PASS", "EXPECTED_FAIL") and t.get("build"):
            try:
                (gdir / f"{t['id']}.json").write_text(t["build"]().model_dump_json(indent=2))
            except Exception:
                pass
    ncert = sum(r["verdict"] == "CERTIFIED" for r in rows)
    print(f"=== m14 task ladder — {len(TASKS)} tasks, {ncert} CERTIFIED ===\n")
    for r in rows:
        mark = "✓" if r["verdict"] == "CERTIFIED" else "✗ UNCERTIFIED"
        print(f"  {mark:14s} {r['id']:26s} [{r['expected']}]  {r['stages']}")
    if ncert != len(TASKS):
        print("\n!! NOT ALL CERTIFIED — an uncertified task may not enter the set.")
    print(f"\nwrote manifest.json ({len(TASKS)} tasks), certification_matrix.json, refusals.json")


if __name__ == "__main__":
    main()
