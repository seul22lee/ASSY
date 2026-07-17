"""IR diff visualization: the LLM's IR vs the golden, same renderer, deltas highlighted.

Side by side, both drawn by `viz.ir_graph.to_svg` so nothing about the comparison is cosmetic:

  LEFT   the GOLDEN, with everything the LLM MISSED highlighted
  RIGHT  the LLM's IR, with everything SPURIOUS (not in the golden) highlighted

The diff is keyed on DECISIONS, not ids — the same keys the scorer uses (card_ref for elements,
(card_ref, port, anchor) for bindings, (phase, motion.kind) for behaviours). `ir_graph.diff_svg`
already exists but keys on node id, which would paint "E1 vs E2" as a difference when it is a naming
accident; the interesting disagreement is "the hinge's mount_A went on rim_underside_left instead of
rear_wall_outer", and only a decision-keyed diff shows that.

Run:  ./bin/py m9_llm_stages/build_ir_diff.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ontology.schema import DesignPlan
from tasks.build_goldens import anchor_easy
from tests.eval_llm_stages import bd_keys, bh_keys, el_keys
from viz.ir_graph import to_svg

OUT = Path(__file__).parent / "out"


def _card_of(plan):
    return {e.id: e.card_ref for e in list(plan.elements) + list(plan.features)}


def _delta_ids(plan, other) -> set[str]:
    """Ids in `plan` whose DECISION does not appear in `other`."""
    out = set()
    o_cards, o_beh = set(el_keys(other)), set(bh_keys(other))
    for e in list(plan.elements) + list(plan.features):
        if e.card_ref not in o_cards:
            out.add(e.id)
    for b in plan.behaviors:
        if (getattr(b.phase, "value", b.phase),
                getattr(b.motion.kind, "value", b.motion.kind)) not in o_beh:
            out.add(b.id)
    return out


def _delta_edges(plan, other) -> set[tuple]:
    """Binding edges in `plan` whose (card_ref, port, anchor) decision is absent from `other`."""
    o = set(bd_keys(other))
    card = _card_of(plan)
    out = set()
    for bd in plan.bindings:
        if (card.get(bd.element_id, "?"), bd.port, bd.anchor) not in o:
            out.add((bd.element_id, bd.piece_id, bd.port, bd.anchor))
    return out


def _svg_size(svg: str) -> tuple[int, int]:
    m = re.search(r'width="(\d+)" height="(\d+)"', svg)
    return (int(m.group(1)), int(m.group(2))) if m else (1200, 600)


def _inner(svg: str) -> str:
    return svg[svg.index(">", svg.index("<svg")) + 1: svg.rindex("</svg>")]


def side_by_side(gold: DesignPlan, llm: DesignPlan, run) -> str:
    left = to_svg(gold, new_ids=_delta_ids(gold, llm), new_edges=_delta_edges(gold, llm),
                  title=f"GOLDEN (anchor_easy[stop])   — red = the LLM MISSED it")
    right = to_svg(llm, new_ids=_delta_ids(llm, gold), new_edges=_delta_edges(llm, gold),
                   title=f"LLM IR (run {run})   — red = SPURIOUS (not in the golden)")
    lw, lh = _svg_size(left)
    rw, rh = _svg_size(right)
    GAP, HEAD = 40, 54
    W, H = lw + rw + GAP, max(lh, rh) + HEAD
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="monospace">
<rect width="{W}" height="{H}" fill="#ffffff"/>
<text x="20" y="24" font-size="16" font-weight="bold" fill="#1a202c">IR diff — LLM vs golden (run {run}) · decision-keyed: card_ref / (card_ref,port,anchor) / (phase,motion.kind); ids and order are free</text>
<text x="20" y="42" font-size="11" fill="#718096">Left: what the golden has that the LLM did not decide. Right: what the LLM decided that the golden does not have. Black = agreed.</text>
<g transform="translate(0,{HEAD})">{_inner(left)}</g>
<g transform="translate({lw + GAP},{HEAD})">{_inner(right)}</g>
<line x1="{lw + GAP/2}" y1="{HEAD}" x2="{lw + GAP/2}" y2="{H}" stroke="#e2e8f0" stroke-width="2"/>
</svg>"""


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    gold = anchor_easy("stop")
    n = 0
    for f in sorted(OUT.glob("ir_*_run*.json")):
        m = re.search(r"ir_(\w+)_run(\d+)", f.name)
        tag, run = m.group(1), int(m.group(2))
        llm = DesignPlan.model_validate_json(f.read_text())
        if not llm.elements and not llm.behaviors:
            print(f"  (skip {tag} run{run}: stage failed, no IR to diff)"); continue
        svg = side_by_side(gold, llm, f"{tag} run {run}")
        (OUT / f"ir_diff_{tag}_run{run}.svg").write_text(svg)
        miss_e = sorted(set(el_keys(gold)) - set(el_keys(llm)))
        spur_b = sorted(set(bd_keys(llm)) - set(bd_keys(gold)))
        print(f"  ir_diff_{tag}_run{run}.svg — elements missed: {miss_e or 'NONE ✓'} · "
              f"spurious bindings: {len(spur_b)}")
        n += 1
    print(f"wrote {n} diff(s)")


if __name__ == "__main__":
    main()
