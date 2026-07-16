"""Renderer parity guard: to_mermaid ≡ to_svg over the IR-entity node set and the edge set.

Why this exists: the AssemblyRule fix landed in `to_mermaid` (d5a44fb) but NOT in `to_svg`, so the
SVG shipped in a G-H review silently missing AR1/AR2 — a whole class of first-class IR entity absent
from the artifact a human signs off on, with nothing to catch it. Two renderers over one IR must
show the same graph; only their STYLING may differ.

Scope of the contract:
  - nodes: every IR entity (pieces, elements, features, behaviours, protocols, assembly_rules)
    appears in both. Functions are excluded BY DESIGN — mermaid draws them as nodes, the SVG as a
    banner; that difference is deliberate styling, and it is asserted explicitly below so the
    exemption cannot quietly widen.
  - edges: identical (src, dst) sets. Labels/dash styling are free.

Run:  ./bin/py tests/test_ir_graph_parity.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tasks.build_goldens import anchor_easy, m0_hinge_box
from viz.ir_graph import _edges, _layout, _mid, to_mermaid

# mermaid node decls:  ID["..."]  ID("...")  ID{{"..."}}  ID{"..."}  ID[/"..."/]
_NODE_RE = re.compile(r'^\s{2}([A-Za-z0-9_]+)(?:\[/?"|\("|\{\{"|\{")')
_EDGE_RE = re.compile(r'^\s{2}([A-Za-z0-9_]+)\s+(?:-->|-\.->|---)\|[^|]*\|\s+([A-Za-z0-9_]+)')


def _mermaid_sets(plan):
    nodes, edges = set(), set()
    for line in to_mermaid(plan).splitlines():
        if (m := _EDGE_RE.match(line)):
            edges.add((m.group(1), m.group(2)))
        elif (m := _NODE_RE.match(line)):
            nodes.add(m.group(1))
    return nodes, edges


def _svg_sets(plan):
    nodes = {_mid(n.id) for n in _layout(plan)}
    edges = {(_mid(s), _mid(d)) for s, d, *_ in _edges(plan)}
    return nodes, edges


def _ir_entity_ids(plan):
    return {_mid(x.id) for x in (list(plan.pieces) + list(plan.elements) + list(plan.features)
                                 + list(plan.behaviors) + list(plan.protocols)
                                 + list(plan.assembly_rules))}


def _check(plan, label):
    mn, me = _mermaid_sets(plan)
    sn, se = _svg_sets(plan)
    fn = {n for n in mn if n.startswith("FN")}

    # functions: mermaid-only BY DESIGN (SVG draws an INTENT banner). Pin the exemption.
    assert fn and not (fn & sn), f"{label}: function nodes must be mermaid-only (SVG banner)"
    mn -= fn

    assert mn == sn, (f"{label}: node sets differ\n  mermaid-only: {sorted(mn - sn)}\n"
                      f"  svg-only:     {sorted(sn - mn)}")
    ir = _ir_entity_ids(plan)
    assert ir <= sn, f"{label}: IR entities missing from BOTH renderers: {sorted(ir - sn)}"
    assert me == se, (f"{label}: edge sets differ\n  mermaid-only: {sorted(me - se)}\n"
                      f"  svg-only:     {sorted(se - me)}")
    return len(sn), len(se)


def test_parity_anchor_easy():
    n, e = _check(anchor_easy(), "anchor_easy (baseline)")
    assert n >= 9 and e >= 8


def test_parity_anchor_easy_stop():
    """The stop variant carries F1 + B3 — a PassiveFeature and the limit it imposes."""
    plan = anchor_easy(variant="stop")
    n, e = _check(plan, "anchor_easy (stop)")
    ids = _ir_entity_ids(plan)
    assert {"F1", "B3"} <= ids


def test_parity_m0_goldens():
    for v in ("nostop", "stop"):
        _check(m0_hinge_box(v), f"m0_hinge_box ({v})")


def test_assembly_rules_reach_both_renderers():
    """The exact regression: AR nodes AND their subject edges must be in BOTH views."""
    plan = anchor_easy()
    mn, me = _mermaid_sets(plan)
    sn, se = _svg_sets(plan)
    for ar in plan.assembly_rules:
        assert _mid(ar.id) in mn, f"{ar.id} missing from to_mermaid"
        assert _mid(ar.id) in sn, f"{ar.id} missing from to_svg"
        for s in (m := set()) or {x.split(".")[0] for x in ar.subjects}:
            if plan.instance(s) or plan.piece(s) or plan.feature(s):
                assert (_mid(ar.id), _mid(s)) in me, f"{ar.id}→{s} edge missing from to_mermaid"
                assert (_mid(ar.id), _mid(s)) in se, f"{ar.id}→{s} edge missing from to_svg"


if __name__ == "__main__":
    n = 0
    for fn in (test_parity_anchor_easy, test_parity_anchor_easy_stop, test_parity_m0_goldens,
               test_assembly_rules_reach_both_renderers):
        fn(); n += 1
    print(f"{n}/{n} passed  — to_mermaid ≡ to_svg (nodes + edges)")
