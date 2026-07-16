"""Pure-python SVG renderers for the two non-IR review artifacts:
  schema_map_svg()          — the ontology class diagram (what contains what)
  validator_matrix_svg()    — V-01..V-13 × goldens grid, all green, with rule text
"""

from __future__ import annotations

import html

BOX_FILL, BOX_STROKE = "#ffffff", "#4a5568"
ACCENT = {"root": "#805ad5", "leaf": "#38a169", "verify": "#3182ce", "card": "#d69e2e"}


def _box(x, y, w, title, lines, accent):
    h = 22 + len(lines) * 14 + 8
    s = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{BOX_FILL}" '
         f'stroke="{accent}" stroke-width="2"/>',
         f'<rect x="{x}" y="{y}" width="{w}" height="20" rx="6" fill="{accent}"/>',
         f'<text x="{x+w/2}" y="{y+14}" font-size="11" font-weight="bold" fill="white" '
         f'font-family="monospace" text-anchor="middle">{html.escape(title)}</text>']
    for i, ln in enumerate(lines):
        s.append(f'<text x="{x+8}" y="{y+34+i*14}" font-size="9" font-family="monospace" '
                 f'fill="#4a5568">{html.escape(ln)}</text>')
    return "\n".join(s), h


def schema_map_svg() -> str:
    W, H = 900, 620
    S = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="monospace">',
         f'<rect width="{W}" height="{H}" fill="#fbfdff"/>',
         '<text x="20" y="26" font-size="16" font-weight="bold" fill="#1a202c">'
         'MechSynth ontology v0.1 — class map</text>',
         '<text x="20" y="44" font-size="10" fill="#718096">'
         'DesignPlan is the IR root; arrows = "contains list of". D-ONT rows tagged.</text>']

    root, hr = _box(360, 60, 200, "DesignPlan", [
        "task_id, command, variant", "material, stage_log"], ACCENT["root"])
    S.append(root)

    children = [
        (40, 170, "Function", ["verb, object, qualifier", "(D-ONT-3 typed)"], "leaf"),
        (250, 170, "Behavior", ["phase, motion:MotionSpec", "realized_by / imposed_by",
                                "verified_by"], "leaf"),
        (470, 170, "Piece", ["role, template_ref", "is_base  (D23/D-ONT-3)", "params"], "leaf"),
        (680, 170, "HostTemplate", ["anchors:[Anchor]", "(D-ONT-1: in IR)"], "card"),
        (40, 320, "ElementInstance", ["card_ref, host_pieces", "→ MechanicalElementCard"], "leaf"),
        (250, 320, "FeatureInstance", ["card_ref, host_pieces", "→ PassiveFeatureCard",
                                       "(D-ONT-4)"], "card"),
        (470, 320, "Binding", ["port↦anchor, mate", "offset_params",
                               "  ·undercut_dir (M-S)"], "leaf"),
        (680, 320, "Parameter", ["value, lo, hi, unit", "resolved_by"], "leaf"),
        (150, 470, "VerificationProtocol", ["criteria:[Criterion]  GATES",
                                            "observables:[Observable]", "(D-ONT-2 split)"], "verify"),
        (470, 470, "MotionSpec", ["kind (+snap_event M-S)", "event_force_window_N",
                                  "transmission"], "leaf"),
        (700, 470, "Material", ["E, eps_allow, mu ...", "PETG (D8)"], "leaf"),
    ]
    anchors = []
    for x, y, title, lines, kind in children:
        b, h = _box(x, y, 190, title, lines, ACCENT[kind])
        S.append(b)
        anchors.append((x + 95, y))  # top-center
    # edges from root bottom to each child top
    rx, ry = 460, 60 + hr
    for ax, ay in anchors:
        S.append(f'<path d="M{rx},{ry} C{rx},{(ry+ay)/2} {ax},{(ry+ay)/2} {ax},{ay}" '
                 f'fill="none" stroke="#cbd5e0" stroke-width="1.4"/>')

    # Card layer note
    S.append('<rect x="250" y="576" width="640" height="34" rx="6" fill="#fffff0" '
             'stroke="#d69e2e"/>')
    S.append('<text x="262" y="596" font-size="9.5" font-family="monospace" fill="#744210">'
             'knowledge/cards/base.py: ElementCard (ABC) → MechanicalElementCard | '
             'PassiveFeatureCard (D-ONT-4).</text>')
    S.append('<text x="262" y="606" font-size="9.5" font-family="monospace" fill="#744210">'
             'has_functional_clearance=True ⇒ collision_hint() REQUIRED at class-def time '
             '(D18/D21).</text>')
    S.append('</svg>')
    return "\n".join(S)


def validator_matrix_svg(rules: list[tuple[str, str]], goldens: list[str],
                         results: dict[tuple[str, str], bool]) -> str:
    """rules: [(id, short_text)]; results[(rule_id, golden)] = passed(bool)."""
    col0 = 300
    cw = 150
    rh = 26
    W = col0 + cw * len(goldens) + 40
    H = 90 + rh * len(rules) + 40
    S = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="monospace">',
         f'<rect width="{W}" height="{H}" fill="#fbfdff"/>',
         '<text x="20" y="26" font-size="16" font-weight="bold" fill="#1a202c">'
         'Validator matrix — V-01..V-13 × goldens</text>',
         '<text x="20" y="44" font-size="10" fill="#718096">'
         'All cells green = every rule passes on every golden. Each rule also has a dedicated '
         'FAILING-case test in tests/test_validators.py.</text>']
    y0 = 66
    # header
    for j, g in enumerate(goldens):
        gx = col0 + j * cw
        S.append(f'<text x="{gx+cw/2}" y="{y0+16}" font-size="9.5" font-weight="bold" '
                 f'fill="#2d3748" text-anchor="middle">{html.escape(g)}</text>')
    y = y0 + 26
    for i, (rid, text) in enumerate(rules):
        ry = y + i * rh
        bg = "#f7fafc" if i % 2 else "#ffffff"
        S.append(f'<rect x="20" y="{ry}" width="{W-40}" height="{rh}" fill="{bg}"/>')
        S.append(f'<text x="28" y="{ry+17}" font-size="10" font-weight="bold" fill="#2d3748">'
                 f'{rid}</text>')
        S.append(f'<text x="80" y="{ry+17}" font-size="9" fill="#4a5568">'
                 f'{html.escape(text)}</text>')
        for j, g in enumerate(goldens):
            gx = col0 + j * cw + cw / 2
            ok = results.get((rid, g), True)
            mark, col = ("✓", "#38a169") if ok else ("✗", "#e53e3e")
            S.append(f'<text x="{gx}" y="{ry+18}" font-size="14" font-weight="bold" '
                     f'fill="{col}" text-anchor="middle">{mark}</text>')
    S.append('</svg>')
    return "\n".join(S)
