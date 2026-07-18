"""Grading harness for the LLM stages ①–④ — a SCORING FUNCTION, not string equality.

The thing being measured is whether the model made the same DISCRETE DECISIONS as the golden, not
whether it typed the same characters. So every match key is the decision itself, and everything
incidental is free:

  functions  matched by  verb                      (object/qualifier reported as field agreement)
  behaviors  matched by  (phase, motion.kind)      — ids and ordering free
  pieces     matched by  template_ref              — ids and ordering free
  elements   matched by  card_ref                  — ids free
  bindings   matched by  (card_ref, port, anchor)  — element ids free; the DECISION is "this card's
                                                     this port goes on that anchor"

Note bindings are keyed by the element's CARD_REF, not its id: "E1" vs "E2" is a naming accident,
"the hinge's axis port sits on rear_top_edge" is the decision. Scoring on ids would punish a correct
design for numbering its elements in a different order.

**The stop axis (graded separately, by instruction).** The Easy command does not mention a stop, but
the benchmark golden includes one — a requirement the SYSTEM derived from physics (D-M8-5), not one
the user stated. Scoring its absence as a generic missing-element would be dishonest twice over: it
would blame the model for not reading the user's mind, and it would hide the most interesting
question in the run. It gets its own axis: `physics_implied_requirement_missed`. An IR without the
stop can still be perfectly valid — and its t2 fold-over is exactly what the benchmark exists to
show.

Run:  ./bin/py tests/eval_llm_stages.py     (self-test on the golden: must score 1.0 everywhere)
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ontology.functional_basis import ALIAS_REASON, ALIASES
from ontology.validators import validate_all


@dataclass
class Axis:
    """One scored dimension: how many golden decisions were reproduced."""
    name: str
    matched: list = field(default_factory=list)
    missing: list = field(default_factory=list)     # in golden, not in candidate
    spurious: list = field(default_factory=list)    # in candidate, not in golden
    wrong_field: list = field(default_factory=list)  # matched on key, disagreed on a field
    aliased: list = field(default_factory=list)      # matched only via a DECLARED alias (D-E-2)

    @property
    def n_golden(self) -> int:
        return len(self.matched) + len(self.missing)

    @property
    def recall(self) -> float:
        return len(self.matched) / self.n_golden if self.n_golden else 1.0

    @property
    def precision(self) -> float:
        n = len(self.matched) + len(self.spurious)
        return len(self.matched) / n if n else 1.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    def as_dict(self) -> dict:
        return {"axis": self.name, "matched": self.matched, "missing": self.missing,
                "spurious": self.spurious, "wrong_field": self.wrong_field,
                "aliased": self.aliased,
                "recall": round(self.recall, 3), "precision": round(self.precision, 3),
                "f1": round(self.f1, 3)}


def _match(gold_keys, cand_keys, name, equiv=None) -> Axis:
    """Multiset match on a decision key. Duplicates count — two hooks is a different decision
    from one hook.

    `equiv(a, b) -> bool` optionally admits DECLARED equivalences (D-E-2 aliases). Exact matches are
    always taken first, so an alias can only ever rescue a key that had no exact partner — it can
    never steal one. Alias-matched keys are recorded in `aliased` so the concession stays visible.
    """
    g, c = Counter(gold_keys), Counter(cand_keys)
    ax = Axis(name)
    for k in set(g) & set(c):                       # exact first
        for _ in range(min(g[k], c[k])):
            ax.matched.append(k)
        g[k] -= min(g[k], c[k]); c[k] = 0
    miss = [k for k, n in g.items() for _ in range(n)]
    spur = [k for k, n in c.items() for _ in range(n)]
    if equiv:
        for gk in list(miss):
            hit = next((sk for sk in spur if equiv(gk, sk)), None)
            if hit is not None:
                miss.remove(gk); spur.remove(hit)
                ax.matched.append(gk); ax.aliased.append((gk, hit))
    ax.missing, ax.spurious = miss, spur
    return ax


def _verb_equiv(a, b) -> bool:
    return b in ALIASES.get(a, ())


def _k(x):
    return getattr(x, "value", x)


# --- per-stage keys ----------------------------------------------------------------------
def fn_keys(plan):
    return [f.verb for f in plan.functions]


def bh_keys(plan):
    return [(_k(b.phase), _k(b.motion.kind)) for b in plan.behaviors]


def pc_keys(plan):
    return [p.template_ref for p in plan.pieces if p.provenance != "hardware"]


def hw_keys(plan):
    return [p.role for p in plan.pieces if p.provenance == "hardware"]


def el_keys(plan):
    return [e.card_ref for e in list(plan.elements) + list(plan.features)]


def bd_keys(plan):
    card = {e.id: e.card_ref for e in list(plan.elements) + list(plan.features)}
    return [(card.get(b.element_id, "?"), b.port, b.anchor) for b in plan.bindings]


STOP_CARD = "stop_flange"


def stop_axis(gold, cand) -> dict:
    """The physics-implied requirement, scored on its own (see module docstring)."""
    g = STOP_CARD in el_keys(gold)
    c = STOP_CARD in el_keys(cand)
    has_ceiling = any(_k(b.motion.kind) == "rotation" and b.motion.bound == "max"
                      for b in cand.behaviors)
    return {"axis": "physics_implied_requirement (stop_flange)",
            "in_golden": g, "in_llm_ir": c, "llm_has_rotation_ceiling": has_ceiling,
            "missed": bool(g and not c),
            "note": ("The command never mentions a stop; the golden carries one because PHYSICS "
                     "showed 'opens>=90 AND returns closed' is unsatisfiable without it (D-M8-5). "
                     "Not scored as a field mismatch: an IR without it is still valid, and its t2 "
                     "fold-over is the benchmark's own point (D20).")}


def forbidden_axis(cand, forbidden) -> dict:
    """D-M14-1 scorer extension — FORBIDDEN-ELEMENT COMPLIANCE. A task that forbids an element
    ("without any gear", "no latch") is only satisfied if the candidate contains NONE of the
    forbidden card_refs. This is the constraint axis the task ladder's constraint variants need."""
    present = sorted(set(el_keys(cand)) & set(forbidden))
    return {"name": "forbidden-element compliance", "forbidden": sorted(forbidden),
            "present": present, "compliant": len(present) == 0}


def _specs(plan) -> dict:
    """(observable, op) -> threshold, over every protocol criterion — the numeric gates a plan sets."""
    out = {}
    for pr in getattr(plan, "protocols", []):
        for c in pr.criteria:
            out[(c.observable, c.op)] = round(float(c.threshold), 4)
    return out


def spec_axis(gold, cand) -> dict:
    """D-M14-1 scorer extension — SPEC-NUMBER EXTRACTION/COMPLIANCE. Every gold criterion threshold
    (force window, open angle, hold-drift…) must appear in the candidate with the same value. This is
    what a spec-tightening task turns on — a criterion the LLM must carry through as a NUMBER, not a
    discrete choice (the `wrong_field` slot in Axis was reserved for exactly this)."""
    g, c = _specs(gold), _specs(cand)
    matched = [k for k in g if k in c and abs(c[k] - g[k]) < 1e-4]
    missing = [k for k in g if k not in c]
    wrong = [k for k in g if k in c and abs(c[k] - g[k]) >= 1e-4]
    return {"name": "spec-number compliance", "n_gold": len(g), "matched": len(matched),
            "missing": [f"{o} {op}" for o, op in missing],
            "wrong_value": [f"{o} {op}: {c[(o, op)]} vs {g[(o, op)]}" for o, op in wrong],
            "compliant": len(missing) == 0 and len(wrong) == 0}


def score(gold, cand, aliases: bool = True) -> dict:
    """`aliases=True` admits D-E-2's declared vocabulary aliases at ①. Both numbers are always
    reported (see `score_both`) — a scoring concession that is not shown is a scoring lie."""
    eq = _verb_equiv if aliases else None
    axes = [
        _match(fn_keys(gold), fn_keys(cand), "① functions (by verb)", equiv=eq),
        _match(bh_keys(gold), bh_keys(cand), "② behaviors (by phase+motion.kind)"),
        _match(pc_keys(gold), pc_keys(cand), "③ pieces (by template_ref)"),
        _match(hw_keys(gold), hw_keys(cand), "③/④ hardware pieces (by role, D-ONT-11)"),
        _match(el_keys(gold), el_keys(cand), "④ elements (by card_ref)"),
        _match(bd_keys(gold), bd_keys(cand), "④ bindings (by card_ref+port+anchor)"),
    ]
    viols = validate_all(cand)
    return {"axes": [a.as_dict() for a in axes],
            "alias_scoring": aliases,
            "alias_reasons": {" ~ ".join(sorted(k)): v for k, v in ALIAS_REASON.items()},
            "stop_axis": stop_axis(gold, cand),
            "validators": {"clean": not viols,
                           "violations": [f"{v.rule}: {v.detail}" for v in viols],
                           "rules_hit": sorted({v.rule for v in viols})},
            "macro_f1": round(sum(a.f1 for a in axes) / len(axes), 3)}


def scorecard_md(sc: dict, title: str, extra: dict | None = None) -> str:
    L = [f"# {title}", "", "## Per-stage agreement with the golden", "",
         "| axis | matched | missing | spurious | recall | precision | F1 |",
         "|---|---:|---:|---:|---:|---:|---:|"]
    for a in sc["axes"]:
        L.append(f"| {a['axis']} | {len(a['matched'])} | {len(a['missing'])} | "
                 f"{len(a['spurious'])} | {a['recall']:.2f} | {a['precision']:.2f} | "
                 f"**{a['f1']:.2f}** |")
    if "macro_f1_strict" in sc:
        L += ["", f"**macro F1 — alias-aware: {sc['macro_f1_alias']:.3f} · strict: "
                  f"{sc['macro_f1_strict']:.3f}** (D-E-2; delta {sc['alias_delta']:+.3f})", ""]
    else:
        L += ["", f"**macro F1: {sc['macro_f1']:.3f}**", ""]
    for a in sc["axes"]:
        if a.get("aliased"):
            L.append(f"- `{a['axis']}` — matched via DECLARED ALIAS (D-E-2): "
                     f"{[f'{g} ~ {c}' for g, c in a['aliased']]}")
    for a in sc["axes"]:
        if a["missing"] or a["spurious"]:
            L.append(f"- `{a['axis']}` — missing: `{a['missing']}` · spurious: `{a['spurious']}`")
    s = sc["stop_axis"]
    L += ["", "## Physics-implied requirement (scored separately)", "",
          f"| in golden | in LLM IR | LLM has a rotation ceiling | **missed** |",
          f"|---|---|---|---|",
          f"| {s['in_golden']} | {s['in_llm_ir']} | {s['llm_has_rotation_ceiling']} | "
          f"**{'YES' if s['missed'] else 'no'}** |", "", f"> {s['note']}", ""]
    v = sc["validators"]
    L += ["## Validators on the LLM's IR", "",
          f"- **clean: {v['clean']}**" + (f" — rules hit: `{v['rules_hit']}`" if not v["clean"] else "")]
    for x in v["violations"][:8]:
        L.append(f"  - {x}")
    if extra:
        L += ["", "## Pipeline survival", ""]
        for k, val in extra.items():
            L.append(f"- **{k}**: {val}")
    return "\n".join(L) + "\n"


# --- self-test: the grader must score the golden perfectly against itself ------------------
def test_golden_scores_perfectly():
    from tasks.build_goldens import anchor_easy
    g = anchor_easy("stop")
    sc = score(g, g)
    assert sc["macro_f1"] == 1.0, sc["macro_f1"]
    assert not sc["stop_axis"]["missed"]


def test_nostop_variant_trips_only_the_stop_axis():
    """The D20 demo differs from the benchmark by exactly the stop. The grader must localise that
    to the stop axis + the element/behaviour axes — and must NOT call it a validator failure, since
    a stop-less design is a legal IR."""
    from tasks.build_goldens import anchor_easy
    g, n = anchor_easy("stop"), anchor_easy("nostop")
    sc = score(g, n)
    assert sc["stop_axis"]["missed"] is True
    assert sc["stop_axis"]["in_golden"] and not sc["stop_axis"]["in_llm_ir"]
    assert "stop_flange" in sc["axes"][4]["missing"], sc["axes"][4]
    assert sc["validators"]["clean"], "a stop-less design is still a VALID IR"


def test_ids_and_order_are_free():
    """Renaming elements and reordering behaviours must not change the score — the decision is the
    card and the port, not the label."""
    from tasks.build_goldens import anchor_easy
    g = anchor_easy("stop")
    c = anchor_easy("stop")
    c.behaviors = list(reversed(c.behaviors))
    ren = {e.id: f"X{i}" for i, e in enumerate(c.elements)}
    for e in c.elements:
        e.id = ren[e.id]
    for b in c.bindings:
        b.element_id = ren.get(b.element_id, b.element_id)
    assert score(g, c)["macro_f1"] == 1.0


def test_forbidden_axis_flags_a_gear():
    """The crank lift HAS a gear → 'without any gear' is NOT complied with; it has no hinge → a
    'no hinge' constraint IS complied with."""
    from tasks.build_goldens import anchor_lift
    p = anchor_lift()
    assert not forbidden_axis(p, ["rack_pinion"])["compliant"], "lift contains the gear"
    assert forbidden_axis(p, ["pin_hinge"])["compliant"], "lift contains no hinge"


def test_spec_axis_matches_and_flags_wrong_number():
    """A spec-tightened golden vs itself is compliant; a candidate with a LOOSER threshold is flagged
    with the exact wrong value (the number, not just a discrete miss)."""
    from tasks.build_goldens import anchor_easy
    g = anchor_easy("stop", open_min=100.0)
    assert spec_axis(g, g)["compliant"], "self must be spec-compliant"
    c = anchor_easy("stop", open_min=90.0)
    r = spec_axis(g, c)
    assert not r["compliant"] and r["wrong_value"], "a looser open-angle must be flagged with its value"


if __name__ == "__main__":
    fns = [test_golden_scores_perfectly, test_nostop_variant_trips_only_the_stop_axis,
           test_ids_and_order_are_free, test_forbidden_axis_flags_a_gear,
           test_spec_axis_matches_and_flags_wrong_number]
    for f in fns:
        f()
    print(f"{len(fns)}/{len(fns)} passed  — scorer: golden==1.0, stop isolated to its own axis, "
          f"ids/order free")


def score_both(gold, cand) -> dict:
    """D-E-2: report BOTH numbers — strict (exact verb) and alias-aware. If they differ, the
    difference IS the vocabulary's ambiguity, quantified, and it is shown rather than absorbed."""
    strict, alias = score(gold, cand, aliases=False), score(gold, cand, aliases=True)
    return {**alias,
            "macro_f1_alias": alias["macro_f1"], "macro_f1_strict": strict["macro_f1"],
            "axes_strict": strict["axes"],
            "alias_delta": round(alias["macro_f1"] - strict["macro_f1"], 3)}
