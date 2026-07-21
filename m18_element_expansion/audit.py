"""M18 Tier-1 AUDIT — verify all 8 elements are correct AND physically verified, exhaustively.

AUDIT-ONLY: surface gaps, do NOT fix. Every element × every layer -> a PASS / WEAK / MISSING coverage
matrix, so anything incomplete surfaces BEFORE Tier-2. Does not assume the m18 tests are sufficient
(they were written alongside the code and may share blind spots); re-derives the formula anchors by
hand here and independently probes each layer.

Layers: 0 physics verification (mandatory) · 1 per-card integrity · 2 ontology consistency ·
3 KG narrowing · 4 regression. Physics runs under a real GL backend (egl); if none exists, STOP.

Run:  export MUJOCO_GL=egl ; ./bin/py m18_element_expansion/audit.py
"""

from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "m0"))

OUT = Path(__file__).parent
ELEMENTS = ["lead_screw", "coupling", "universal_joint", "journal_bearing", "bushing",
            "dowel_pin", "screw_boss", "press_fit"]
FUNCTIONAL = {"lead_screw", "coupling", "universal_joint", "journal_bearing"}   # realize/support a DoF
STATIC = {"bushing", "dowel_pin", "screw_boss", "press_fit"}

# verdicts
P, W, M, F = "PASS", "WEAK", "MISSING", "FALSE"
rows: dict[str, dict[str, tuple[str, str]]] = {}   # element -> check -> (verdict, reason)
extra: list[str] = []                              # ontology / kg / regression rows


def cell(el, check, verdict, reason=""):
    rows.setdefault(el, {})[check] = (verdict, reason)


# ======================================================================================
# GL gate (mandatory — no falling back to disable)
# ======================================================================================
def check_gl():
    import mujoco
    m = mujoco.MjModel.from_xml_string("<mujoco><worldbody><geom type='box' size='.1 .1 .1'/>"
                                       "</worldbody></mujoco>")
    r = mujoco.Renderer(m, 64, 64); d = mujoco.MjData(m); mujoco.mj_forward(m, d)
    r.update_scene(d); r.render(); r.close()


# ======================================================================================
# LAYER 0 — physics verification
# ======================================================================================
def audit_layer0():
    """For every functional element, determine whether a physics check ACTUALLY RUNS (not just that a
    protocol is declared / a formula exists), and whether the emergent_check tag is HONEST."""
    from knowledge.cards.base import CARD_REGISTRY

    # Is there ANY harness that runs a declared-pair V-A for a given card? Probe the verify/ surface.
    verify_txt = ""
    for f in (ROOT / "verify" / "t2_physics").glob("*.py"):
        verify_txt += f.read_text()
    runm8 = (ROOT / "tasks" / "run_m8_t2.py")
    compile_txt = (ROOT / "pipeline" / "compile_assembly.py").read_text()
    runm8_txt = runm8.read_text() if runm8.exists() else ""

    class _I:
        def __init__(s, params=None): s.params = params or {}; s.id = "E1"

    for el in ELEMENTS:
        card = CARD_REGISTRY[el]
        ec = card.taxonomy["emergent_check"]
        req = el in FUNCTIONAL

        # (col) physics-required?
        cell(el, "phys_required", P if req else "n/a", "functional/support" if req else "static connection")

        # (col) protocol declared? — does verification() emit a VerificationProtocol?
        protos = []
        try:
            protos = card.verification(type("Ir", (), {"behaviors": []})(), _I())
        except Exception as e:
            protos = []
        declared = bool(protos)
        # a real behaviour would be needed to emit the protocol; probe with a matching behaviour too
        if req and not declared:
            declared = _protocol_would_emit(card, el)

        # (col) is there a harness that RUNS it? — no m18 card appears anywhere in verify/rig code
        referenced = any(el in t for t in (verify_txt, runm8_txt)) or "m18_tier1" in (verify_txt + runm8_txt + compile_txt)
        harness_runs = referenced   # False for all m18 cards (verified by the grep above)

        if not req:   # static: t0/formula IS the verification
            cell(el, "protocol_runs", "n/a", "static — verified by formula_check + geometry, not physics")
            cell(el, "passes", "n/a", "")
            cell(el, "measured_vs_criterion", "n/a", "")
            # emergent honesty for static
            if ec.status == "not_applicable":
                cell(el, "emergent_honest", P, "not_applicable is honest for a static connection")
            else:
                cell(el, "emergent_honest", W, f"static card tagged {ec.status}, expected not_applicable")
            continue

        # functional element:
        cell(el, "protocol_runs", M if not harness_runs else P,
             "protocol DECLARED but NO harness in verify/ runs it (no card-specific rig; the P-HINGE "
             "runner is hinge-only)" if not harness_runs else "runs")
        cell(el, "passes", M if not harness_runs else "?", "no physics executed" if not harness_runs else "")
        cell(el, "measured_vs_criterion", M, "no measured number — physics never ran")

        # emergent_check honesty (the load-bearing cross-check)
        if ec.status == "verified" and not harness_runs:
            cell(el, "emergent_honest", F,
                 "FALSE 'verified' tag — no V-A/V-B actually runs for this element; 'verified' claims "
                 "an emergent safety net that does not exist yet")
        elif ec.status == "deferred":
            curved = ec.reason and ("curved" in ec.reason.lower() or "thread" in ec.reason.lower())
            if curved:
                cell(el, "emergent_honest", W,
                     "deferred reason is a real tool limit (curved contact, R2b) — HONEST for V-B; but "
                     "the declared-pair V-A (stroke/self-lock) also never runs, so even the non-curved "
                     "check is unbuilt (the risk it names is itself unverified)")
            else:
                cell(el, "emergent_honest", W, f"deferred but reason not clearly a curved-contact limit: {ec.reason}")
        elif ec.status == "not_applicable":
            cell(el, "emergent_honest", W,
                 "a rotational SUPPORT tagged not_applicable — defensible (realizes no DoF) but its "
                 "low-friction support behaviour under load is unverified; a V-A drag test would close it")
        else:
            cell(el, "emergent_honest", P, "")


def _protocol_would_emit(card, el):
    """Build a minimal behaviour the card's verification() keys on, to confirm a protocol IS declared
    (so 'no run' is a harness gap, not a missing declaration)."""
    from ontology.schema import Behavior, MotionSpec

    class _Ir:
        def __init__(s, bs): s.behaviors = bs

    class _I:
        def __init__(s): s.params = {}; s.id = "E1"
    kind = {"lead_screw": "rot_to_trans", "coupling": "rotation", "universal_joint": "rotation",
            "journal_bearing": "rotation"}[el]
    b = Behavior(id="B", phase="use", motion=MotionSpec(kind=kind), realized_by="E1")
    try:
        return bool(card.verification(_Ir([b]), _I()))
    except Exception:
        return False


# ======================================================================================
# LAYER 1 — per-card integrity
# ======================================================================================
def audit_layer1():
    from knowledge.cards.base import CARD_REGISTRY

    class _Ir:
        behaviors = []

    class _I:
        def __init__(s, p=None): s.params = p or {}; s.id = "E1"

    class _B:
        def __init__(s, port): s.port = port; s.piece_id = "P1"; s.anchor = "a"

    # (a) resolve_params within bounds
    for el in ELEMENTS:
        card = CARD_REGISTRY[el]
        out = card.resolve_params(_Ir(), _I())
        bad = [(k, out[k]) for k, (lo, hi, _u) in card.param_bounds.items()
               if k in out and isinstance(out[k], (int, float)) and not (lo <= out[k] <= hi)]
        none = [k for k in card.param_bounds if out.get(k) is None]
        cell(el, "resolve_params", P if not bad and not none else W,
             "" if not bad and not none else f"out-of-bound {bad} / none {none}")

    # (b) formula anchored to a HAND-computed worked value
    def approx(a, b, tol=0.02, rel=True):
        return abs(a - b) <= (tol * max(1, abs(b)) if rel else tol)

    # lead_screw: d=8,lead=2,mu=0.3 -> d_p=7, lambda=atan(2/(pi*7))=5.20deg, phi=atan(.3)=16.70 -> self-lock
    f = CARD_REGISTRY["lead_screw"].formula_check(_I({"d_major": 8, "lead": 2, "mu": 0.30}))
    ok = (f["self_locks"] is True and approx(f["lead_angle_deg"], math.degrees(math.atan(2/(math.pi*7))))
          and approx(f["friction_angle_deg"], math.degrees(math.atan(0.30))))
    cell("lead_screw", "formula_anchored", P if ok else F, "self-lock tan(lead)<=mu reproduced" if ok else "mismatch")

    # screw_boss: pilot=2.4, area=pi*2.4*6, pullout=1357.2
    f = CARD_REGISTRY["screw_boss"].formula_check(_I({"screw_d": 3, "engagement": 6, "tau_shear": 30}))
    cell("screw_boss", "formula_anchored", P if approx(f["pullout_force_N"], math.pi*2.4*6*30) else F,
         "pull-out = pi*pilot*eng*tau reproduced")

    # press_fit: p=26.25 MPa, F=1979.2 N
    f = CARD_REGISTRY["press_fit"].formula_check(_I({"d_nom": 8, "interference": 0.05, "length": 10}))
    ok = approx(f["pressure_MPa"], 2100*0.1/8) and approx(f["holding_force_N"], math.pi*8*10*(2100*0.1/8)*0.30)
    cell("press_fit", "formula_anchored", P if ok else F, "interference p=E*delta/d, F=pi*d*L*p*mu reproduced")

    # coupling: T = 25*pi*8^3/16
    f = CARD_REGISTRY["coupling"].formula_check(_I({"bore_d": 8}))
    cell("coupling", "formula_anchored", P if approx(f["torque_capacity_Nmm"], 25*math.pi*8**3/16) else F,
         "shaft torsion tau=16T/pi d^3 reproduced")

    # universal_joint: vel_ratio_max = 1/cos(20)
    f = CARD_REGISTRY["universal_joint"].formula_check(_I({"angle_deg": 20}))
    cell("universal_joint", "formula_anchored", P if approx(f["vel_ratio_max"], 1/math.cos(math.radians(20))) else F,
         "Cardan tan(out)=tan(in)/cos(beta) reproduced")

    # journal_bearing/bushing: clearance floored at print clearance (rule of thumb, not a textbook formula)
    for el in ("journal_bearing", "bushing"):
        f = CARD_REGISTRY[el].formula_check(_I({"bore_d": 8}))
        cell(el, "formula_anchored", W,
             "clearance=max(d/1000, print_clearance) is a RULE OF THUMB (Shigley §12), not a worked "
             "textbook golden — WEAKLY anchored")

    # dowel_pin: bore = pin + clearance — no real formula
    cell("dowel_pin", "formula_anchored", W,
         "no numeric golden — 'bore = pin_d + fit_clearance' is a fit rule, not a derived formula (unanchored)")

    # (c) carve produces exactly one solid, volume>0, watertight if checkable
    ports = {"lead_screw": "screw_axis", "coupling": "shaft_in", "universal_joint": "shaft_in",
             "journal_bearing": "bore_mount", "bushing": "bore_mount", "dowel_pin": "location",
             "screw_boss": "boss_mount", "press_fit": "interface"}
    for el in ELEMENTS:
        r = CARD_REGISTRY[el].carve({}, _I(), [_B(ports[el])])
        solid = list(r.tags.values())[0]
        n = len(solid.solids())
        vol = solid.volume
        wt = _watertight(solid)
        verdict = P if (n == 1 and vol > 0 and wt is not False) else W
        cell(el, "carve_one_solid", verdict,
             f"{n} solid(s), vol={vol:.0f}, watertight={wt}" + (
                 "" if verdict == P else " — not a single watertight solid"))

    # (d) all 7 taxonomy axes populated deliberately
    AXES = ["working_motion", "axis_relationship", "connection_principle", "self_locking",
            "emergent_check", "compliance", "kinematic_dof"]
    for el in ELEMENTS:
        tax = CARD_REGISTRY[el].taxonomy
        missing = [a for a in AXES if a not in tax]
        cell(el, "taxonomy_7axes", P if not missing else M, f"missing {missing}" if missing else "all 7 present")


def _watertight(solid):
    for attr in ("is_manifold", "is_valid"):
        v = getattr(solid, attr, None)
        try:
            return bool(v()) if callable(v) else (bool(v) if v is not None else None)
        except Exception:
            continue
    return None


# ======================================================================================
# LAYER 2 — ontology consistency
# ======================================================================================
def audit_layer2():
    from ontology.schema import (Anchor, Behavior, DesignPlan, ElementInstance, HostTemplate,
                                 MotionSpec, Piece)
    from ontology.validators import v08, v17
    from knowledge.cards.base import CARD_REGISTRY, ConnectionCard

    res = []
    # V-08: a ConnectionCard realized_by -> rejected
    plan = DesignPlan(task_id="t", command="c",
                      pieces=[Piece(id="P1", role="base", template_ref="box_shell", is_base=True)],
                      templates=[HostTemplate(template_ref="box_shell", anchors=[Anchor(name="a", kind="point")])],
                      elements=[ElementInstance(id="E1", card_ref="dowel_pin", host_pieces=["P1"])],
                      behaviors=[Behavior(id="B1", phase="static", motion=MotionSpec(kind="fixed"), realized_by="E1")])
    res.append(("V-08 rejects connection realized_by", any("ConnectionCard" in v.detail for v in v08(plan))))

    # V-17: compliant rejected with P-SPRING message
    card = CARD_REGISTRY["coupling"]; orig = card.compliance
    try:
        card.compliance = "compliant"
        plan2 = DesignPlan(task_id="t", command="c",
                           pieces=[Piece(id="P1", role="base", template_ref="box_shell", is_base=True)],
                           templates=[HostTemplate(template_ref="box_shell", anchors=[Anchor(name="a", kind="point")])],
                           elements=[ElementInstance(id="E1", card_ref="coupling", host_pieces=["P1"])])
        res.append(("V-17 rejects compliant (P-SPRING msg)", any("P-SPRING" in v.detail for v in v17(plan2))))
    finally:
        card.compliance = orig

    # principle (property) vs ConnectionCard (class) not conflated: the class carries the property
    conns = [c for c in CARD_REGISTRY.values() if isinstance(c, ConnectionCard)]
    prop_ok = all(c.connection_principle in ("form", "force", "material") for c in conns) and \
        all(not isinstance(getattr(c, "card_class", ""), type) for c in conns)   # card_class is a str, not a class
    res.append(("connection_principle(property) != ConnectionCard(class)", prop_ok))

    # screw_boss.provides_pieces -> hardware piece instantiates + params resolve
    from pipeline.s4_interface import _provide_hardware
    plan3 = DesignPlan(task_id="t", command="c",
                       pieces=[Piece(id="P1", role="base", template_ref="box_shell", is_base=True)],
                       templates=[HostTemplate(template_ref="box_shell", anchors=[Anchor(name="a", kind="point")])],
                       elements=[ElementInstance(id="E1", card_ref="screw_boss", host_pieces=["P1"],
                                                 params={"screw_d": 3, "engagement": 6})])
    _provide_hardware(plan3)
    hw = [p for p in plan3.pieces if p.provenance == "hardware"]
    pp = CARD_REGISTRY["screw_boss"].resolve_piece_params("screw", plan3.elements[0]) if hw else {}
    res.append(("screw_boss provides screw as hardware (provenance+params)",
                bool(hw) and hw[0].source_element == "E1" and pp.get("screw_d") == 3))

    for name, ok in res:
        extra.append(("ontology", name, P if ok else F, "" if ok else "check failed"))


# ======================================================================================
# LAYER 3 — KG narrowing
# ======================================================================================
def audit_layer3():
    from knowledge.kg import candidates
    from ontology.schema import Behavior, MotionSpec
    def B(kind, phase="use", **kw):
        return Behavior(id="B", phase=phase, motion=MotionSpec(kind=kind), **kw)
    queries = [
        ("rot_to_trans + self_locking", candidates(B("rot_to_trans", self_locking=True)),
         lambda got: "lead_screw" in got and "rack_pinion" not in got),
        ("rot_to_trans (no self_lock)", candidates(B("rot_to_trans")),
         lambda got: {"lead_screw", "rack_pinion"} <= set(got)),
        ("locate two parts (fixed+form)", candidates(B("fixed", phase="static"), connection_principle="form"),
         lambda got: got == ["dowel_pin"]),
        ("intersecting-axis rotation", candidates(B("rotation", axis_relationship="intersecting")),
         lambda got: got == ["universal_joint"]),
        ("rotational support", candidates(B("rotation")),
         lambda got: {"journal_bearing", "bushing"} <= set(got)),
    ]
    for name, got, pred in queries:
        ok = bool(got) and pred(got)
        extra.append(("kg", f"{name} -> {got}", P if ok else W, "" if ok else "unexpected narrowing"))


# ======================================================================================
# LAYER 4 — regression
# ======================================================================================
def audit_layer4():
    # full suite
    n_pass = n_fail = 0
    for t in sorted((ROOT / "tests").glob("test_*.py")):
        r = subprocess.run(["./bin/py", str(t)], cwd=str(ROOT), capture_output=True, text=True,
                           env=_env(), timeout=300)
        if "passed" in (r.stdout + r.stderr).lower() and r.returncode == 0:
            n_pass += 1
        else:
            n_fail += 1
            extra.append(("regression", f"suite: {t.name}", F, (r.stdout + r.stderr).strip().splitlines()[-1][:80]))
    extra.append(("regression", f"full test suite ({n_pass}/{n_pass+n_fail} files)", P if not n_fail else F, ""))

    # every golden validates clean
    from ontology.validators import validate_all
    goldens = _all_goldens()
    dirty = []
    for name, plan in goldens:
        vs = validate_all(plan)
        if vs:
            dirty.append(f"{name}:{[v.rule for v in vs]}")
    extra.append(("regression", f"goldens validate_all clean ({len(goldens)-len(dirty)}/{len(goldens)})",
                  P if not dirty else F, "; ".join(dirty)[:120]))

    # structure: no milestone moved, no existing card re-filed
    g = subprocess.run(["git", "status", "--porcelain"], cwd=str(ROOT), capture_output=True, text=True)
    moved = [l for l in g.stdout.splitlines() if l.startswith("R") or " -> " in l]
    extra.append(("regression", "append-only (no moved/renamed)", P if not moved else F, "; ".join(moved)[:80]))


def _all_goldens():
    out = []
    from tasks.build_goldens import anchor_easy, anchor_hard, anchor_lift, snap_starter
    for nm, fn in (("anchor_easy[stop]", lambda: anchor_easy("stop")),
                   ("anchor_easy[nostop]", lambda: anchor_easy("nostop")),
                   ("anchor_hard", anchor_hard), ("anchor_lift", anchor_lift),
                   ("snap_starter", snap_starter)):
        try:
            out.append((nm, fn()))
        except Exception as e:
            extra.append(("regression", f"golden {nm} build", F, f"{type(e).__name__}: {e}"))
    # m14 ladder goldens (json)
    gdir = ROOT / "tasks" / "benchmark" / "goldens"
    from ontology.schema import DesignPlan
    for jf in sorted(gdir.glob("*.json")) if gdir.exists() else []:
        try:
            out.append((jf.stem, DesignPlan.model_validate_json(jf.read_text())))
        except Exception as e:
            extra.append(("regression", f"golden {jf.stem} load", F, str(e)[:60]))
    return out


def _env():
    import os
    e = dict(os.environ); e["MUJOCO_GL"] = "disable"   # regression tests are non-render; keep them fast
    return e


# ======================================================================================
# MATRIX
# ======================================================================================
L0 = ["phys_required", "protocol_runs", "passes", "measured_vs_criterion", "emergent_honest"]
L1 = ["resolve_params", "formula_anchored", "carve_one_solid", "taxonomy_7axes"]
COLS = L0 + L1


def render_matrix():
    lines = ["# M18 Tier-1 element audit — coverage matrix", "",
             "AUDIT-ONLY (surface gaps, do not fix). PASS / WEAK / MISSING / **FALSE** per cell.", "",
             "## Layer 0 — physics verification  ·  Layer 1 — per-card integrity", "",
             "| element | " + " | ".join(c.replace("_", " ") for c in COLS) + " |",
             "|---|" + "|".join("---" for _ in COLS) + "|"]
    tally = {P: 0, W: 0, M: 0, F: 0, "n/a": 0, "?": 0}
    for el in ELEMENTS:
        r = rows.get(el, {})
        cells = []
        for c in COLS:
            v, _ = r.get(c, (M, "not checked"))
            tally[v] = tally.get(v, 0) + 1
            cells.append(f"**{v}**" if v == F else v)
        lines.append(f"| `{el}` | " + " | ".join(cells) + " |")
    lines += ["", "## Non-PASS reasons (element × check)", ""]
    for el in ELEMENTS:
        for c in COLS:
            v, reason = rows.get(el, {}).get(c, (M, "not checked"))
            if v in (W, M, F) and reason:
                lines.append(f"- `{el}` · **{v}** {c}: {reason}")
    lines += ["", "## Layers 2–4 — ontology · KG · regression", "",
              "| layer | check | verdict | note |", "|---|---|---|---|"]
    for layer, name, v, reason in extra:
        tally[v] = tally.get(v, 0) + 1
        lines.append(f"| {layer} | {name} | {'**'+v+'**' if v==F else v} | {reason} |")

    # summary + ordered gaps
    npass, nweak, nmiss, nfalse = tally[P], tally[W], tally[M], tally[F]
    lines += ["", "## Summary", "",
              f"**{npass} PASS · {nweak} WEAK · {nmiss} MISSING · {nfalse} FALSE** "
              f"(n/a: {tally['n/a']}).", ""]
    gaps = _ordered_gaps()
    gaps.sort(key=lambda pg: {"TOP": 0, "HIGH": 1, "MED": 2}.get(pg[0], 3))
    lines += ["## Ordered gaps to fix before Tier-2", ""]
    for i, (prio, g) in enumerate(gaps, 1):
        lines.append(f"{i}. **[{prio}]** {g}")
    return "\n".join(lines), (npass, nweak, nmiss, nfalse), gaps


def _ordered_gaps():
    gaps = []
    # TOP: functional elements reaching the design with NO physics check
    no_phys = [el for el in FUNCTIONAL if rows.get(el, {}).get("protocol_runs", ("", ""))[0] == M]
    if no_phys:
        gaps.append(("TOP", f"FUNCTIONAL elements with NO physics verification (declared protocol, no "
                            f"runner/rig): {', '.join(no_phys)}. This is where an m8-stop / m13-brake "
                            f"class emergent surprise could hide — the whole point of the framework."))
    # FALSE emergent tags
    false_tags = [el for el in ELEMENTS if rows.get(el, {}).get("emergent_honest", ("", ""))[0] == F]
    if false_tags:
        gaps.append(("TOP", f"FALSE emergent_check='verified' tags (claims a safety net that never "
                            f"runs): {', '.join(false_tags)}. Either build the V-A rig or retag to "
                            f"deferred/not-built."))
    # WEAK emergent (deferred V-A unbuilt / support n/a)
    weak_em = [el for el in ELEMENTS if rows.get(el, {}).get("emergent_honest", ("", ""))[0] == W]
    if weak_em:
        gaps.append(("HIGH", f"emergent_check WEAK: {', '.join(weak_em)} — deferred elements whose "
                            f"declared-pair V-A also never runs, and supports tagged not_applicable "
                            f"whose low-friction behaviour is unverified."))
    # unanchored formulas
    unanch = [el for el in ELEMENTS if rows.get(el, {}).get("formula_anchored", ("", ""))[0] == W]
    if unanch:
        gaps.append(("MED", f"formulas WEAKLY anchored (rule-of-thumb / no textbook golden): "
                            f"{', '.join(unanch)} — add a worked numeric anchor like Bayer's for snaps."))
    # regression failures (a test that WAS green now red — high priority)
    reg_fail = [(name, reason) for layer, name, v, reason in extra if layer == "regression" and v == F]
    for name, reason in reg_fail:
        if "full test suite" in name:
            gaps.append(("HIGH", f"REGRESSION — {name}: a previously-green test is now red. "
                                f"test_roundtrip::test_disk_json_is_canonical fails because the "
                                f"on-disk golden JSONs predate the m18 schema fields "
                                f"(nature/axis_relationship/self_locking) — they validate_all CLEAN "
                                f"but their committed serialization is stale (re-dump needed). NOTE: "
                                f"the m18 'all green' claim missed this — a `grep passed` tally matched "
                                f"'3/4 passed'; this audit's returncode check caught it."))
    # carve limits — every m18 carve is a single STANDALONE primitive, no mating bore/host
    gaps.append(("MED", "carve produces a single STANDALONE primitive per element (a cylinder/tube), "
                        "with NO mating bore or host integration — so press_fit's designed interference "
                        "overlap, and the dowel/boss fits, cannot be geometrically verified against a "
                        "mate (t0 interference has nothing to check). Assembly-level geometry is unbuilt."))
    return gaps


def main():
    print("M18 Tier-1 AUDIT — GL check...", flush=True)
    try:
        check_gl()
    except Exception as e:
        print(f"\nSTOP: no usable GL backend ({type(e).__name__}: {e}). "
              f"Physics cannot run; set MUJOCO_GL=egl|glfw|osmesa. NOT falling back to disable.")
        raise SystemExit(2)
    print("  GL OK (egl). Running layers 0-4...", flush=True)
    audit_layer0(); audit_layer1(); audit_layer2(); audit_layer3(); audit_layer4()
    md, (np_, nw, nm, nf), gaps = render_matrix()
    (OUT / "AUDIT.md").write_text(md)
    print("\n" + md)
    print(f"\n=== {np_} PASS · {nw} WEAK · {nm} MISSING · {nf} FALSE ===")
    print("wrote m18_element_expansion/AUDIT.md")
    # which elements ran REAL physics vs formula-only
    ran = [el for el in FUNCTIONAL if rows.get(el, {}).get("protocol_runs", ("", ""))[0] == P]
    print(f"REAL physics ran for: {ran or 'NONE'} | formula-only functional: "
          f"{sorted(FUNCTIONAL - set(ran))}")


if __name__ == "__main__":
    main()
