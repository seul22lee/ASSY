"""viz/report.py — single self-contained report.html per run (MECHSYNTH §7.6, SNAPFIT §6/§9.1).

Assembles a RunData dict (from pipeline.run_snap) into one HTML page: verbatim command → per-stage
log → the design-rationale sheet (every dimension as value | governing equation | citation) → the
IR mermaid graph → 3D render → gate results (G-S2, Tier0 three-way, Tier1 re-measure) → verdict
block (with "Tier2: N/A") → the G-H approval checklist. Images are embedded as base64, so the
report is self-contained. Mermaid renders via the CDN script (the only external ref; the graph is
also printed as text so the page is legible without it).
"""

from __future__ import annotations

from pathlib import Path

import jinja2

_TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8"><title>{{ d.label }} — run report</title>
<style>
 body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:980px;margin:2rem auto;
      padding:0 1rem;color:#1a202c;line-height:1.45}
 h1{border-bottom:3px solid #2b6cb0;padding-bottom:.3rem}
 h2{margin-top:2rem;color:#2b6cb0;border-bottom:1px solid #cbd5e0;padding-bottom:.2rem}
 .cmd{background:#1a202c;color:#e2e8f0;padding:.8rem 1rem;border-radius:6px;font-family:monospace}
 table{border-collapse:collapse;width:100%;margin:.6rem 0;font-size:.9rem}
 th,td{border:1px solid #cbd5e0;padding:.35rem .5rem;text-align:left;vertical-align:top}
 th{background:#edf2f7} code{background:#edf2f7;padding:.05rem .3rem;border-radius:3px}
 .pass{color:#22543d;font-weight:bold}.fail{color:#742a2a;font-weight:bold}
 .verdict{font-size:1.15rem;padding:.8rem 1rem;border-radius:6px;font-weight:bold}
 .vpass{background:#c6f6d5;color:#22543d}.vfail{background:#fed7d7;color:#742a2a}
 .na{background:#e2e8f0;color:#4a5568;padding:.5rem .8rem;border-radius:6px;margin:.5rem 0}
 img{max-width:100%;border:1px solid #cbd5e0;border-radius:6px}
 .mermaid{background:#fbfdff;border:1px solid #cbd5e0;border-radius:6px;padding:.5rem}
 pre{background:#f7fafc;border:1px solid #cbd5e0;border-radius:6px;padding:.6rem;overflow:auto;
     font-size:.75rem} ul.chk{list-style:none;padding-left:0} ul.chk li{margin:.3rem 0}
</style></head><body>
<h1>{{ d.label }} — snap-fit run report</h1>

<h2>1 · Command (verbatim)</h2>
<div class="cmd">{{ d.command }}</div>
{% if d.strategy %}<p><b>Resolve strategy:</b> <code>{{ d.strategy }}</code>
 &nbsp; <b>frequent re-open:</b> {{ d.frequent }} &nbsp;
 {% if d.permanent %}<b style="color:#b7791f">PERMANENT joint (non-separable)</b>{% endif %}</p>{% endif %}

{% if d.infeasible %}
<h2>Verdict</h2>
<div class="verdict vfail">✗ {{ d.verdict }}</div>
<p><b>{{ d.failure.code }}:</b> {{ d.failure.detail }}</p>
<p>This is a correct diagnosis, not a crash — the pipeline rejected the design at a named stage and
rolls back to stage ④ (design choice).</p>
{% if d.expected_fail %}<div class="na"><b>EXPECTED_FAIL — regression target:</b> {{ d.expected_fail }}</div>{% endif %}
{% else %}

<h2>2 · Per-stage log</h2>
<table><tr><th>Stage</th><th>Outcome</th></tr>
{% for s, o in d.stage_log %}<tr><td>{{ s }}</td><td>{{ o }}</td></tr>{% endfor %}</table>

<h2>3 · Design-rationale sheet</h2>
<p>Every resolved dimension as <b>value | governing equation | citation</b> — the auditable trail
from the command to the geometry (D5/D7: the LLM never emits these; the formulas do).</p>
<table><tr><th>Dimension</th><th>Value</th><th>Governing equation</th><th>Citation</th></tr>
{% for r in d.rationale %}<tr><td>{{ r.name }}</td><td><b>{{ r.value }}</b></td>
 <td><code>{{ r.equation }}</code></td><td>{{ r.citation }}</td></tr>{% endfor %}</table>

<h2>4 · IR graph</h2>
<div class="mermaid">
{{ d.mermaid }}
</div>
<details><summary>mermaid source</summary><pre>{{ d.mermaid }}</pre></details>

<h2>5 · Compiled geometry</h2>
<img src="{{ d.render_iso }}" alt="assembly render">

<h2>6 · Gate results</h2>
<table><tr><th>Tier / gate</th><th>Check</th><th>Result</th><th>Detail</th></tr>
{% for tier, name, ok, det in d.gates %}<tr><td>{{ tier }}</td><td>{{ name }}</td>
 {% if ok is none %}<td style="color:#4a5568">— N/A</td>
 {% else %}<td class="{{ 'pass' if ok else 'fail' }}">{{ '✓ PASS' if ok else '✗ FAIL' }}</td>{% endif %}
 <td>{{ det }}</td></tr>{% endfor %}</table>
<div class="na"><b>Tier2 (physics): N/A.</b> {{ d.tier2 }}</div>

<h2>7 · Summary</h2>
<table>
<tr><th>h</th><th>L</th><th>W_in (per hook)</th><th>W_out</th><th>α_out</th>
 <th>undercut measured</th><th>y designed</th></tr>
<tr><td>{{ d.summary.h }} mm</td><td>{{ d.summary.L }} mm</td><td>{{ d.summary.W_in }} N</td>
 <td>{{ d.summary.W_out }}</td><td>{{ d.summary.alpha_out }}°</td>
 <td>{{ d.summary.undercut_measured }} mm</td><td>{{ d.summary.y_designed }} mm</td></tr></table>

<h2>Verdict</h2>
<div class="verdict {{ 'vpass' if 'PASS' in d.verdict else 'vfail' }}">{{ d.verdict }}</div>

<h2>G-H approval checklist</h2>
<ul class="chk">
<li>☐ Rationale sheet: every dimension traces to an equation + Bayer citation (§3)</li>
<li>☐ IR graph reads correctly: snap_hook realizes mate+retention, imposes sweep clearance (§4)</li>
<li>☐ Tier0 (b): undercut measured = designed y ({{ d.summary.undercut_measured }} vs {{ d.summary.y_designed }} mm) (§6)</li>
<li>☐ Tier1: 0 drift on L/h/b/y (§6)</li>
<li>☐ Force windows (G-S2) satisfied (§6)</li>
<li>☐ Tier2 N/A acknowledged (no use-phase motion)</li>
<li>☐ Verdict accepted</li>
</ul>
<p style="color:#718096">_Approved by: ____________ · Date: ___________</p>
{% endif %}

<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
<script>if(window.mermaid){mermaid.initialize({startOnLoad:true});}</script>
</body></html>"""


def render_report(rundata: dict, out_path: Path) -> Path:
    html = jinja2.Template(_TEMPLATE).render(d=rundata)
    out_path = Path(out_path)
    out_path.write_text(html)
    return out_path
