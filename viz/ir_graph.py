"""DesignPlan → graph visualisation (MECHSYNTH_SPEC §7.2).

Two renderers, both pure-Python (no system installs — `dot` is not on PATH and there is no
network for a mermaid CLI, per the session constraint):

  to_mermaid(plan) -> str   the PRIMARY artifact: mermaid flowchart text, instantly viewable in
                            the VS Code mermaid preview (spec §7.2).
  to_svg(plan)     -> str   a hand-laid layered SVG for reviewers without a mermaid preview.

Node vocabulary (spec §7.2 + D-ONT-4): Function / Behavior / Element / PassiveFeature / Piece /
Protocol, with Bindings as element→piece edges. Conventions:
  * phase colours — use = blue, assembly = orange, static = gray;
  * `imposes` edges are DASHED (a feature/element constraining a behaviour, not realizing it);
  * `is_base` pieces carry a ground symbol (⏚) — the D23 fixture anchor.

diff_* highlights what is present in plan B but not plan A (the stop-vs-nostop delta must read
as exactly the stop_flange feature + its imposed rotation-limit behaviour + the promoted gate).
"""

from __future__ import annotations

import html
from dataclasses import dataclass

from knowledge.cards.base import is_passive
from ontology.schema import DesignPlan

# ---- palette -------------------------------------------------------------------------
PHASE_FILL = {"use": "#bee3f8", "assembly": "#fed7aa", "static": "#e2e8f0"}
PHASE_STROKE = {"use": "#3182ce", "assembly": "#dd6b20", "static": "#718096"}
EL_FILL, EL_STROKE = "#c6f6d5", "#38a169"       # MechanicalElement (green)
FT_FILL, FT_STROKE = "#fefcbf", "#d69e2e"       # PassiveFeature (yellow) — visibly distinct
PC_FILL, PC_STROKE = "#edf2f7", "#4a5568"       # Piece (gray)
PR_FILL, PR_STROKE = "#ffffff", "#805ad5"       # Protocol (purple)
FN_FILL, FN_STROKE = "#ebf8ff", "#3182ce"       # Function (light blue)
NEW_STROKE = "#e53e3e"                            # diff highlight (red)


def _motion_label(m) -> str:
    """Human motion label that makes the D-ONT-9 `bound` visible: a rotation LIMIT (bound=max)
    reads 'rotation limit 109°', a range-of-motion floor (bound=min) reads 'rotation ≥90°'."""
    s = m.kind
    if m.range_value is not None:
        unit = {"deg": "°", "mm": "mm"}.get(m.range_unit, "")
        val = f"{round(m.range_value)}" if m.range_unit == "deg" else f"{m.range_value:g}"
        if m.bound == "max":
            s += f" limit {val}{unit}"
        elif m.bound == "min":
            s += f" ≥{val}{unit}"
        elif m.bound == "exact":
            s += f" ={val}{unit}"
        else:
            s += f" {val}{unit}"
    if m.event_force_window_N:
        lo, hi = m.event_force_window_N
        s += f" [{lo:g},{hi:g}]N"
    return s


# ======================================================================================
# Mermaid (primary)
# ======================================================================================
def assembly_rule_edges(plan) -> list[tuple]:
    """The D-ONT-12 AssemblyRule edges — the ONE derivation both renderers use, so the mermaid and
    SVG views cannot drift apart (tests/test_ir_graph_parity pins it). Returns (src, dst, label,
    dashed); dashed throughout, because every one of these is a constraint rather than a flow.

      rule → subject       labeled by the subject's ROLE IN THE PREDICATE (excluded/sweep_of for an
                           exclusion; the param + (+)/(budget) for a resource). Piece subjects count
                           as much as element ones — AR2's budget referent IS a piece (P2.rim_length).
      behaviour → rule     the imposed requirement ↔ its checkable form. Linked through the PROTOCOL
                           that implements the rule's check (an exclusion is checked by a tier0_sweep,
                           so the behaviour that sweep verifies — B5 — is the one AR1 makes
                           checkable). Deliberately NOT "every behaviour the card imposes": that
                           would wrongly rope in B6, the hook insertion path.
    """
    out = []
    for ar in getattr(plan, "assembly_rules", []):
        pred = ar.predicate or {}
        roles = {}
        if ar.kind == "exclusion":
            roles = {pred.get("excluded"): "excluded", pred.get("sweep_of"): "sweep_of"}
        elif ar.kind == "resource":
            for c in pred.get("contributors", []):
                roles[c] = f"{c.split('.', 1)[1]} (+)" if "." in c else "contributor"
            b = pred.get("budget")
            if b:
                roles[b] = f"{b.split('.', 1)[1]} (budget)" if "." in b else "budget"
        for subj, label in roles.items():
            if not subj:
                continue
            base = subj.split(".")[0]
            if plan.instance(base) or plan.piece(base) or plan.feature(base):
                out.append((ar.id, base, label, True))
    ROLE_ACTUATION = {"exclusion": "tier0_sweep", "resource": "budget_check"}
    for ar in getattr(plan, "assembly_rules", []):
        act = ROLE_ACTUATION.get(ar.kind)
        for pr in plan.protocols:
            if (pr.actuation or {}).get("kind") == act and pr.verifies:
                out.append((pr.verifies, ar.id, "checkable form", True))
    return out


def _mid(raw: str) -> str:
    """Mermaid-safe node id: hyphens and other punctuation in ids (P-HINGE, PR-T1-MATE) can
    break the VS Code parser, so map to [A-Za-z0-9_] while the display label keeps the original."""
    return "".join(c if c.isalnum() else "_" for c in raw)


def to_mermaid(plan: DesignPlan) -> str:
    L = ["flowchart LR"]
    L.append(f'  %% {plan.task_id}' + (f' [{plan.variant}]' if plan.variant else ''))
    m = _mid

    # Functions
    for i, fn in enumerate(plan.functions):
        q = f"{fn.verb}: {fn.object}"
        L.append(f'  FN{i}("🎯 {q}"):::fn')

    # Pieces (ground marker for base; HARDWARE pieces (D-ONT-11) drawn as a distinct parallelogram
    # with a bolt marker and their source_element instead of a template_ref)
    for p in plan.pieces:
        if p.provenance == "hardware":
            L.append(f'  {m(p.id)}[/"🔩 {p.id} {p.role}\\nhardware ← {p.source_element}"/]:::hardware')
        else:
            mark = "⏚ " if (p.is_base or p.role == "base") else ""
            L.append(f'  {m(p.id)}["{mark}{p.id} {p.role}\\n{p.template_ref}"]:::piece')

    # Elements + Features
    for e in plan.elements:
        L.append(f'  {m(e.id)}("{e.id}\\n{e.card_ref}"):::elem')
    for f in plan.features:
        L.append(f'  {m(f.id)}{{{{"{f.id}\\n{f.card_ref}"}}}}:::feat')

    # Behaviors (phase-coloured); label shows the D-ONT-9 bound (limit vs range-of-motion)
    for b in plan.behaviors:
        L.append(f'  {m(b.id)}["{b.id} · {b.phase.value}\\n{_motion_label(b.motion)}"]'
                 f':::{b.phase.value}')

    # Protocols
    for pr in plan.protocols:
        ng, no = len(pr.criteria), len(pr.observables)
        L.append(f'  {m(pr.id)}["🔬 {pr.id}\\n{ng} gates / {no} obs"]:::proto')

    # Edges
    for b in plan.behaviors:
        if b.realized_by:
            L.append(f'  {m(b.realized_by)} -->|realizes| {m(b.id)}')
        if b.imposed_by:
            L.append(f'  {m(b.imposed_by)} -.->|imposes| {m(b.id)}')   # dashed
        if b.verified_by:
            L.append(f'  {m(b.id)} -->|verified_by| {m(b.verified_by)}')
    for bd in plan.bindings:
        L.append(f'  {m(bd.element_id)} ---|{bd.port}@{bd.anchor}| {m(bd.piece_id)}')
    # D-ONT-11: the element that PROVIDES a hardware piece → a dashed provenance edge to it
    for p in plan.pieces:
        if p.provenance == "hardware" and p.source_element:
            L.append(f'  {m(p.source_element)} -.->|provides| {m(p.id)}')
    # D-ONT-12: AssemblyRules as first-class nodes (rhombus), edges to every subject they constrain
    # + the imposed behaviour ↔ checkable-rule link. Both renderers derive these from the SAME
    # helpers (`assembly_rule_edges`), so the two views cannot drift apart — see tests/test_ir_graph_parity.
    for ar in plan.assembly_rules:
        L.append(f'  {m(ar.id)}{{"⚖ {ar.id}\\n{ar.kind}"}}:::arule')
    for src, dst, label, _dashed in assembly_rule_edges(plan):
        L.append(f'  {m(src)} -.->|{label}| {m(dst)}')

    L += [
        f'  classDef hardware fill:#cbd5e0,stroke:#2d3748,stroke-width:2px;',
        f'  classDef arule fill:#fefcbf,stroke:#b7791f,stroke-width:2px;',
        f'  classDef use fill:{PHASE_FILL["use"]},stroke:{PHASE_STROKE["use"]};',
        f'  classDef assembly fill:{PHASE_FILL["assembly"]},stroke:{PHASE_STROKE["assembly"]};',
        f'  classDef static fill:{PHASE_FILL["static"]},stroke:{PHASE_STROKE["static"]};',
        f'  classDef elem fill:{EL_FILL},stroke:{EL_STROKE};',
        f'  classDef feat fill:{FT_FILL},stroke:{FT_STROKE};',
        f'  classDef piece fill:{PC_FILL},stroke:{PC_STROKE};',
        f'  classDef proto fill:{PR_FILL},stroke:{PR_STROKE};',
        f'  classDef fn fill:{FN_FILL},stroke:{FN_STROKE};',
    ]
    return "\n".join(L) + "\n"


# ======================================================================================
# SVG (layered, hand-laid)
# ======================================================================================
@dataclass
class _Node:
    id: str
    lines: list[str]
    fill: str
    stroke: str
    col: int
    row: int
    ground: bool = False
    hexagon: bool = False  # passive features drawn as hexagons
    hardware: bool = False  # D-ONT-11 hardware piece (steel fill + HW badge)
    rule: bool = False     # D-ONT-12 AssemblyRule drawn as a rhombus (⚖)
    new: bool = False      # diff highlight

    x = y = 0.0


COL_X = [40, 250, 470, 700, 940]   # piece, element/feature, behavior, protocol, assembly-rule
NODE_W, NODE_H, ROW_GAP, COL_LABEL_Y = 150, 46, 30, 24
FN_Y = 44  # functions banner


def _layout(plan: DesignPlan, new_ids: set[str] | None = None) -> list[_Node]:
    new_ids = new_ids or set()
    nodes: list[_Node] = []
    rows = [0, 0, 0, 0, 0]

    def add(nid, lines, fill, stroke, col, **kw):
        n = _Node(nid, lines, fill, stroke, col, rows[col], new=nid in new_ids, **kw)
        rows[col] += 1
        nodes.append(n)
        return n

    for p in plan.pieces:
        if p.provenance == "hardware":
            add(p.id, [f"{p.id}  {p.role}", f"hardware < {p.source_element}"], "#cbd5e0", "#2d3748",
                0, hardware=True)
        else:
            add(p.id, [f"{p.id}  {p.role}", p.template_ref or ""], PC_FILL, PC_STROKE, 0,
                ground=(p.is_base or p.role == "base"))
    for e in plan.elements:
        add(e.id, [e.id, e.card_ref], EL_FILL, EL_STROKE, 1)
    for f in plan.features:
        add(f.id, [f.id, f.card_ref], FT_FILL, FT_STROKE, 1, hexagon=True)
    for b in plan.behaviors:
        add(b.id, [f"{b.id} · {b.phase.value}", _motion_label(b.motion)],
            PHASE_FILL[b.phase.value], PHASE_STROKE[b.phase.value], 2)
    for pr in plan.protocols:
        add(pr.id, [pr.id, f"{len(pr.criteria)} gates / {len(pr.observables)} obs"],
            PR_FILL, PR_STROKE, 3)
    # D-ONT-12: AssemblyRules as first-class rhombus nodes (col 4). The sub-line shows provenance
    # — a card:<card> rule traces to that card's interaction_rules API; a task rule is plan-authored.
    for ar in getattr(plan, "assembly_rules", []):
        prov = ar.provenance
        sub = (f"< {prov.split(':', 1)[1]}.interaction_rules" if prov.startswith("card:")
               else f"provenance: {prov}")
        add(ar.id, [f"{ar.id}  {ar.kind}", sub], "#fefcbf", "#b7791f", 4, rule=True)

    # assign coordinates
    for n in nodes:
        n.x = COL_X[n.col]
        n.y = FN_Y + 40 + n.row * (NODE_H + ROW_GAP)
    return nodes


def _edges(plan: DesignPlan, new_edges: set[tuple] | None = None) -> list[tuple]:
    new_edges = new_edges or set()
    out = []  # (src, dst, label, dashed, new)
    for b in plan.behaviors:
        if b.realized_by:
            out.append((b.realized_by, b.id, "realizes", False,
                        (b.realized_by, b.id) in new_edges))
        if b.imposed_by:
            out.append((b.imposed_by, b.id, "imposes", True,
                        (b.imposed_by, b.id) in new_edges))
        if b.verified_by:
            out.append((b.id, b.verified_by, "verified_by", False,
                        (b.id, b.verified_by) in new_edges))
    for bd in plan.bindings:
        out.append((bd.element_id, bd.piece_id, f"{bd.port}", False,
                    (bd.element_id, bd.piece_id, bd.port, bd.anchor) in new_edges))
    # D-ONT-11: element → hardware piece it provides (dashed provenance edge)
    for p in plan.pieces:
        if p.provenance == "hardware" and p.source_element:
            out.append((p.source_element, p.id, "provides", True,
                        (p.source_element, p.id) in new_edges))
    for src, dst, label, dashed in assembly_rule_edges(plan):
        out.append((src, dst, label, dashed, (src, dst) in new_edges))
    return out


def _svg_node(n: _Node) -> str:
    stroke = NEW_STROKE if n.new else n.stroke
    sw = 3 if n.new else 1.5
    cx = n.x + NODE_W / 2
    parts = []
    if n.rule:  # D-ONT-12 AssemblyRule: a rhombus (⚖), matching the mermaid renderer
        w, h = NODE_W, NODE_H
        pts = f"{n.x},{n.y+h/2} {cx},{n.y} {n.x+w},{n.y+h/2} {cx},{n.y+h}"
        parts.append(f'<polygon points="{pts}" fill="{n.fill}" stroke="{stroke}" '
                     f'stroke-width="{sw}"/>')
        parts.append(f'<text x="{n.x+10}" y="{n.y+h/2+4}" font-size="12" '
                     f'fill="{stroke}">&#9878;</text>')  # scales/balance glyph
    elif n.hexagon:
        w, h = NODE_W, NODE_H
        pts = f"{n.x+12},{n.y} {n.x+w-12},{n.y} {n.x+w},{n.y+h/2} {n.x+w-12},{n.y+h} " \
              f"{n.x+12},{n.y+h} {n.x},{n.y+h/2}"
        parts.append(f'<polygon points="{pts}" fill="{n.fill}" stroke="{stroke}" '
                     f'stroke-width="{sw}"/>')
    else:
        parts.append(f'<rect x="{n.x}" y="{n.y}" width="{NODE_W}" height="{NODE_H}" rx="6" '
                     f'fill="{n.fill}" stroke="{stroke}" stroke-width="{sw}"/>')
    for i, ln in enumerate(n.lines):
        weight = "bold" if i == 0 else "normal"
        fs = 11 if i == 0 else 9.5
        col = "#1a202c" if i == 0 else "#4a5568"
        parts.append(f'<text x="{cx}" y="{n.y + 18 + i*14}" font-size="{fs}" '
                     f'font-family="monospace" font-weight="{weight}" fill="{col}" '
                     f'text-anchor="middle">{html.escape(ln)}</text>')
    if n.hardware:  # D-ONT-11 HW badge, top-right corner
        bx, by = n.x + NODE_W - 26, n.y + 3
        parts.append(f'<rect x="{bx}" y="{by}" width="22" height="12" rx="2" fill="#2d3748"/>'
                     f'<text x="{bx+11}" y="{by+9}" font-size="8" font-family="monospace" '
                     f'fill="#e2e8f0" text-anchor="middle" font-weight="bold">HW</text>')
    if n.ground:  # D23 ground symbol under the base piece
        gx, gy = cx, n.y + NODE_H + 3
        parts.append(f'<line x1="{gx}" y1="{n.y+NODE_H}" x2="{gx}" y2="{gy}" '
                     f'stroke="{n.stroke}" stroke-width="1.5"/>')
        for k, w in enumerate((14, 9, 4)):
            parts.append(f'<line x1="{gx-w}" y1="{gy+k*3}" x2="{gx+w}" y2="{gy+k*3}" '
                         f'stroke="{n.stroke}" stroke-width="1.5"/>')
    return "".join(parts)


def _anchor(n: _Node, side: str):
    if side == "l":
        return n.x, n.y + NODE_H / 2
    if side == "r":
        return n.x + NODE_W, n.y + NODE_H / 2
    return n.x + NODE_W / 2, n.y + NODE_H / 2


def to_svg(plan: DesignPlan, new_ids: set[str] | None = None,
           new_edges: set[tuple] | None = None, title: str | None = None) -> str:
    nodes = _layout(plan, new_ids)
    by_id = {n.id: n for n in nodes}
    edges = _edges(plan, new_edges)

    max_row = max((n.row for n in nodes), default=0)
    height = FN_Y + 80 + (max_row + 1) * (NODE_H + ROW_GAP) + 40
    width = COL_X[-1] + NODE_W + 40

    S = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
         f'font-family="monospace" viewBox="0 0 {width} {height}">']
    S.append(f'<rect width="{width}" height="{height}" fill="#fbfdff"/>')
    S.append('<defs>'
             '<marker id="arw" markerWidth="9" markerHeight="9" refX="8" refY="3" orient="auto">'
             '<path d="M0,0 L8,3 L0,6 Z" fill="#4a5568"/></marker>'
             '<marker id="arwN" markerWidth="9" markerHeight="9" refX="8" refY="3" orient="auto">'
             f'<path d="M0,0 L8,3 L0,6 Z" fill="{NEW_STROKE}"/></marker></defs>')

    ttl = title or f"{plan.task_id}" + (f"  [{plan.variant}]" if plan.variant else "")
    S.append(f'<text x="20" y="24" font-size="15" font-weight="bold" fill="#1a202c">{html.escape(ttl)}</text>')

    # column labels
    for cx0, lbl in zip(COL_X, ("PIECES", "ELEMENTS / FEATURES", "BEHAVIORS", "PROTOCOLS",
                                "ASSEMBLY RULES")):
        S.append(f'<text x="{cx0}" y="{FN_Y+30}" font-size="10" font-weight="bold" '
                 f'fill="#718096">{lbl}</text>')

    # functions banner (no emoji — a small filled dot marks each; emoji rendered as tofu in SVG)
    S.append(f'<text x="20" y="{FN_Y}" font-size="10" fill="#718096">INTENT:</text>')
    fx = 80
    for fn in plan.functions:
        label = f"{fn.verb}: {fn.object}"
        w = 22 + len(label) * 6.4
        S.append(f'<rect x="{fx}" y="{FN_Y-14}" width="{w}" height="20" rx="10" fill="{FN_FILL}" '
                 f'stroke="{FN_STROKE}"/>'
                 f'<circle cx="{fx+11}" cy="{FN_Y-4}" r="3.2" fill="{FN_STROKE}"/>'
                 f'<text x="{fx+20}" y="{FN_Y}" font-size="10" '
                 f'fill="#2c5282">{html.escape(label)}</text>')
        fx += w + 12

    # edges first (under nodes)
    for src, dst, label, dashed, new in edges:
        a, b = by_id.get(src), by_id.get(dst)
        if not a or not b:
            continue
        # choose facing sides by column order
        if a.col < b.col:
            x1, y1 = _anchor(a, "r"); x2, y2 = _anchor(b, "l")
        elif a.col > b.col:
            x1, y1 = _anchor(a, "l"); x2, y2 = _anchor(b, "r")
        else:
            x1, y1 = _anchor(a, "r"); x2, y2 = _anchor(b, "r")
        col = NEW_STROKE if new else "#718096"
        lcol = NEW_STROKE if new else "#4a5568"
        dash = 'stroke-dasharray="5,4" ' if dashed else ""
        mk = "arwN" if new else "arw"
        S.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" '
                 f'stroke-width="{2 if new else 1.2}" {dash}marker-end="url(#{mk})"/>')
        # label at 42% of the way (clear of the arrowhead), on a white pill so it stays legible
        # where it crosses lines or other edges.
        mx, my = x1 + (x2 - x1) * 0.42, y1 + (y2 - y1) * 0.42
        lw = len(label) * 5.0 + 6
        S.append(f'<rect x="{mx-lw/2}" y="{my-11}" width="{lw}" height="12" rx="3" '
                 f'fill="#ffffff" fill-opacity="0.88"/>')
        S.append(f'<text x="{mx}" y="{my-2}" font-size="8" fill="{lcol}" '
                 f'text-anchor="middle">{html.escape(label)}</text>')

    for n in nodes:
        S.append(_svg_node(n))

    # legend
    ly = height - 26
    items = [("use", PHASE_FILL["use"], PHASE_STROKE["use"]),
             ("assembly", PHASE_FILL["assembly"], PHASE_STROKE["assembly"]),
             ("static", PHASE_FILL["static"], PHASE_STROKE["static"]),
             ("element", EL_FILL, EL_STROKE), ("feature (hexagon)", FT_FILL, FT_STROKE),
             ("hardware piece [HW]", "#cbd5e0", "#2d3748"),
             ("AssemblyRule (rhombus)", "#fefcbf", "#b7791f")]
    lx = 20
    for lbl, fill, stroke in items:
        S.append(f'<rect x="{lx}" y="{ly}" width="14" height="14" fill="{fill}" stroke="{stroke}"/>'
                 f'<text x="{lx+18}" y="{ly+11}" font-size="9" fill="#4a5568">{lbl}</text>')
        lx += 30 + len(lbl) * 6.0
    # dashed-line + ground swatches instead of unicode glyphs (which render as tofu in SVG)
    S.append(f'<line x1="{lx+6}" y1="{ly+7}" x2="{lx+30}" y2="{ly+7}" stroke="#718096" '
             f'stroke-width="1.4"/><text x="{lx+34}" y="{ly+11}" font-size="9" '
             f'fill="#4a5568">realizes</text>')
    lx += 90
    S.append(f'<line x1="{lx+6}" y1="{ly+7}" x2="{lx+30}" y2="{ly+7}" stroke="#718096" '
             f'stroke-width="1.4" stroke-dasharray="5,4"/><text x="{lx+34}" y="{ly+11}" '
             f'font-size="9" fill="#4a5568">imposes</text>')
    lx += 88
    S.append(f'<line x1="{lx+10}" y1="{ly+2}" x2="{lx+10}" y2="{ly+9}" stroke="#4a5568" '
             f'stroke-width="1.4"/><line x1="{lx+4}" y1="{ly+9}" x2="{lx+16}" y2="{ly+9}" '
             f'stroke="#4a5568" stroke-width="1.4"/><line x1="{lx+6}" y1="{ly+12}" '
             f'x2="{lx+14}" y2="{ly+12}" stroke="#4a5568" stroke-width="1.4"/>'
             f'<text x="{lx+22}" y="{ly+11}" font-size="9" fill="#4a5568">= base</text>')

    S.append('</svg>')
    return "\n".join(S)


# ======================================================================================
# Diff (B relative to A)
# ======================================================================================
def _ids(plan) -> set[str]:
    return ({p.id for p in plan.pieces} | {e.id for e in plan.elements}
            | {f.id for f in plan.features} | {b.id for b in plan.behaviors}
            | {pr.id for pr in plan.protocols})


def _edge_set(plan) -> set[tuple]:
    s = set()
    for b in plan.behaviors:
        if b.realized_by:
            s.add((b.realized_by, b.id))
        if b.imposed_by:
            s.add((b.imposed_by, b.id))
        if b.verified_by:
            s.add((b.id, b.verified_by))
    for bd in plan.bindings:
        s.add((bd.element_id, bd.piece_id, bd.port, bd.anchor))
    return s


def diff_svg(base: DesignPlan, other: DesignPlan) -> str:
    new_ids = _ids(other) - _ids(base)
    new_edges = _edge_set(other) - _edge_set(base)
    title = f"DIFF  {other.variant or other.task_id}  vs  {base.variant or base.task_id}   " \
            f"(red = added by '{other.variant or 'B'}')"
    return to_svg(other, new_ids=new_ids, new_edges=new_edges, title=title)
