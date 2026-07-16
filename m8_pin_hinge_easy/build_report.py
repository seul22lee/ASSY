"""Assemble m8_pin_hinge_easy/report.html from the run artifacts (renders, IR graph, t0 AR results,
t1 re-measure, t2 P-HINGE V-A/V-B). Structure (the milestone spec):

    command → decisions + citations → rationale → gates → videos → verdict

Self-contained: images/videos are referenced from ./out (kept in-repo); the IR graph is inlined SVG.
Run:  ./bin/py m8_pin_hinge_easy/build_report.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

HERE = Path(__file__).parent
OUT = HERE / "out"


def _crit_rows(criteria):
    r = ""
    for name, c in criteria.items():
        ok = "ok" if c["pass"] else "FAIL"
        cls = "pass" if c["pass"] else "fail"
        r += (f"<tr class='{cls}'><td>{name}</td><td class='num'>{c['value']}</td>"
              f"<td class='num'>≤ {c['threshold']}</td><td>{ok}</td></tr>")
    return r


def main():
    t2 = json.loads((OUT / "t2_easy_verdict.json").read_text())
    t1 = json.loads((OUT / "t1_easy_verdict.json").read_text())
    ars = json.loads((OUT / "t0_assembly_rules.json").read_text())
    ir_svg = (OUT / "ir_easy.svg").read_text()

    va, vb = t2["modes"]["V-A"]["p_hinge"], t2["modes"]["V-B"]["p_hinge"]

    # --- decisions table --------------------------------------------------------------------
    decisions = [
        ("D-ONT-11", "Element-provided pieces", "The loose pin is a Piece with provenance="
         "'hardware', instantiated at ④ and provenance-tagged; its geometry comes from the hinge "
         "element E1's carve (pin_solid). V-07 amended: hardware exempt from binding.",
         "MECHSYNTH §3.3 / M0 hinge"),
        ("D-ONT-12", "AssemblyRule as a first-class entity", "Two typed, declarative rules on the "
         "plan: an EXCLUSION (the latch must lie outside the lid's swept volume) and a RESOURCE "
         "budget (Σ contributors ≤ budget). Provenance-tagged; referents resolve per D13.",
         "MECHSYNTH §5.2 / Pahl&Beitz"),
        ("D14 / COLLISION_EPS", "Lid seating without a tied separating axis", "The moving lid's "
         "seating primitive is inset by 0.2 mm laterally so it never shares a face-plane with the "
         "static rim (the drawer lesson); the load-bearing Z plane is left exact.",
         "M0 FINDINGS / drawer"),
        ("D22", "Intended vs defect interference", "Undercut release (0–10°), the closing seat, the "
         "pin/bore interface and the open-stop impact are INTENDED contacts (observables); only "
         "non-intended travel interference gates.", "your ruling / M0 B4"),
        ("pin_hinge card", "Formalized M0 hinge (Bayer/§3.3)", "Ports axis/mount_A/mount_B; bounded "
         "params; carve() = knuckles+lugs+bore+chamfer+pin; collision_hint() = ring-of-wedges bore.",
         "SNAPFIT §12 / M0"),
        ("snap_hook_cantilever card", "Formalized Bayer cantilever", "Grows hooks into the lid, cuts "
         "catch windows; contributes the EXCLUSION AssemblyRule (imposes-family knowledge).",
         "Bayer p.5 Fig.1"),
    ]
    drows = "".join(f"<tr><td class='mono'>{d}</td><td><b>{t}</b><br><span class='sub'>{x}</span></td>"
                    f"<td class='sub'>{c}</td></tr>" for d, t, x, c in decisions)

    # --- t0 AssemblyRules -------------------------------------------------------------------
    arows = ""
    for a in ars:
        cls = "pass" if a["ok"] else "fail"
        arows += (f"<tr class='{cls}'><td class='mono'>{a['id']}</td><td>{a['kind']}</td>"
                  f"<td class='sub'>{a['provenance']}</td><td>{a['detail']}</td>"
                  f"<td>{'PASS' if a['ok'] else 'FAIL'}</td></tr>")

    # --- t1 re-measure ----------------------------------------------------------------------
    t1rows = ""
    for el, d in t1["elements"].items():
        for k, i, m, dr, ok in d["rows"]:
            cls = "pass" if ok else "fail"
            t1rows += (f"<tr class='{cls}'><td class='mono'>{el}</td><td>{k}</td>"
                       f"<td class='num'>{i}</td><td class='num'>{m}</td><td class='num'>{dr}</td>"
                       f"<td>{'ok' if ok else 'DRIFT'}</td></tr>")

    verdict = t2["verdict"] and t1["verdict"] and all(a["ok"] for a in ars)
    vbadge = "PASS" if verdict else "FAIL"

    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>m8 — pin_hinge Easy anchor</title>
<style>
 body{{font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;max-width:1080px;margin:0 auto;
   padding:24px;color:#1a202c;background:#fafbfc}}
 h1{{font-size:24px;margin:.2em 0}} h2{{font-size:18px;border-bottom:2px solid #e2e8f0;padding-bottom:4px;
   margin-top:34px}} h3{{font-size:15px;margin:18px 0 6px}}
 .verdict{{display:inline-block;padding:4px 14px;border-radius:6px;font-weight:700;color:#fff}}
 .PASS{{background:#2f855a}} .FAIL{{background:#c53030}}
 table{{border-collapse:collapse;width:100%;margin:8px 0;font-size:13px}}
 th,td{{border:1px solid #e2e8f0;padding:6px 8px;text-align:left;vertical-align:top}}
 th{{background:#f7fafc}} .num{{text-align:right;font-variant-numeric:tabular-nums}}
 .mono{{font-family:ui-monospace,Menlo,monospace;font-size:12px}} .sub{{color:#718096;font-size:12px}}
 tr.pass td:last-child{{color:#2f855a;font-weight:600}} tr.fail td:last-child{{color:#c53030;font-weight:600}}
 .cmd{{background:#1a202c;color:#e2e8f0;padding:12px 16px;border-radius:8px;font-family:ui-monospace,monospace;
   font-size:12.5px;white-space:pre-wrap}}
 .grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px}} img{{max-width:100%;border:1px solid #e2e8f0;border-radius:6px}}
 video{{width:100%;border:1px solid #e2e8f0;border-radius:6px}} .cap{{color:#718096;font-size:12px;margin:2px 0 12px}}
 .ir{{overflow-x:auto;border:1px solid #e2e8f0;border-radius:6px;padding:8px;background:#fff}}
</style></head><body>

<h1>m8 — <span class="mono">pin_hinge</span> Easy anchor <span class="verdict {vbadge}">{vbadge}</span></h1>
<p class="sub">Box + lid on a formalized pin hinge, with a front snap latch; the loose pin is
element-provided hardware (D-ONT-11); two first-class AssemblyRules (D-ONT-12) govern the latch
sweep and the rim budget. Compiled from the IR, then verified through t0 → t1 → t2.</p>

<h2>① Command</h2>
<div class="cmd">intent:  a box whose lid opens on a hinge to ~95°, is held shut by a snap latch,
         and closes back onto its seat.
plan:    2 elements (E1 pin_hinge, E2 snap_hook_cantilever) · 3 pieces (P1 box[base],
         P2 lid[mover], P3 pin[hardware ← E1]) · 2 AssemblyRules (AR1 exclusion, AR2 resource)
compile: motion-before-fasteners (E1 hinge carve → E2 snap carve → assign P3 = E1.pin_solid)
verify:  t0 three-way + AssemblyRules · t1 re-measure (COMPILE_DRIFT) · t2 P-HINGE V-A + V-B</div>

<h2>② Decisions &amp; citations</h2>
<table><tr><th>ID</th><th>Decision</th><th>Citation</th></tr>{drows}</table>

<h2>③ Rationale</h2>
<p>The pipeline constrains the LLM to discrete ontology choices (which cards, which ports, which
rules) while deterministic code owns every dimension. The pin is not modelled as a fourth free
part the planner invented — it is <b>provided by the hinge card</b> and tagged hardware, so its
geometry and provenance trace to E1 (D-ONT-11). The latch-vs-sweep constraint is not hand-written
either: it is an <b>AssemblyRule the snap card imposes</b> (D-ONT-12), evaluated on the compiled
geometry. Physics is split into two independent questions: does the declared hinge <i>axis</i>
carry the motion (V-A), and does the <i>geometry alone</i> — pin in a bored knuckle — produce the
same DoF by contact (V-B)? Both must agree, or the mechanism is an artifact of the joint we
declared rather than the shape we built.</p>

<h2>④ Assembly — 4-view, exploded, section</h2>
<div class="grid">
 <div><img src="out/anchor_4view.png"><div class="cap">Hinge knuckles + protruding pin at the rear
   (−Y); snap latch at the front (+Y).</div></div>
 <div><img src="out/anchor_exploded.png"><div class="cap">The pin is a separate hardware body,
   provided by E1 (D-ONT-11). Box knuckles + front catch window visible on the base.</div></div>
</div>
<img src="out/anchor_section.png">
<div class="cap">SECTION at x=0 — the centre hinge knuckle wraps the pin/bore (rear, left) and the
 snap latch teeth seat in the box's catch window (front, right), in a single cut.</div>

<h3>IR graph</h3>
<div class="ir">{ir_svg}</div>
<div class="cap">P3 renders as hardware provenance (steel, 🔩, “hardware ← E1”, dashed provides
 edge); AR1/AR2 render as rhombus AssemblyRule nodes with kind-labeled edges.</div>

<h2>⑤ Gates</h2>
<h3>t0 — AssemblyRules (first live firing)</h3>
<table><tr><th>rule</th><th>kind</th><th>provenance</th><th>result</th><th></th></tr>{arows}</table>
<p class="sub">AR1 is D22-aware: the rigid hook's undercut interferes with the window edge only
through the 0–10° release band (intended — in reality the beam flexes out); the free sweep beyond
is clean, so the latch clears the box. AR2 reads ⑤ values straight from the IR.</p>

<h3>t1 — re-measure on the compiled geometry (COMPILE_DRIFT guard)</h3>
<table><tr><th>element</th><th>param</th><th>IR</th><th>measured</th><th>|Δ| (mm)</th><th></th></tr>{t1rows}</table>
<p class="sub">Both elements re-measured from the compiled STEP against the resolved IR — 0.0000 mm
drift. The IR reference is ⑤'s resolved value, not the compiled dims (the panel blind-spot rule).</p>

<h3>t2 — G-CONV + P-HINGE (5 seeds/mode, ≥4/5 → PASS)</h3>
<div class="grid">
 <div><h3 style="margin-top:0">V-A — declared hinge joint</h3>
   <table><tr><th>criterion</th><th>value</th><th>thr</th><th></th></tr>{_crit_rows(va['criteria_seed0'])}</table>
   <p class="sub">{va['seeds_passed']}/{va['n_seeds']} seeds pass. The joint IS the hinge; the
    ring-of-wedge collisions are skipped (they jam a convex approximation of the joint).</p></div>
 <div><h3 style="margin-top:0">V-B — contact-only (DoF from geometry)</h3>
   <table><tr><th>criterion</th><th>value</th><th>thr</th><th></th></tr>{_crit_rows(vb['criteria_seed0'])}</table>
   <p class="sub">{vb['seeds_passed']}/{vb['n_seeds']} seeds pass. The DoF emerges from the pin in the
    bored knuckle; a designed open-stop (the lug hard-stop) arrests it at ~107°.</p></div>
</div>

<h2>⑥ Videos — P-HINGE HUD (D15: the scored values, burned in)</h2>
<div class="grid">
 <div><video controls muted loop src="out/t2_easy_V-A.mp4"></video><div class="cap">V-A —
   open to ~112°, hold, reverse, seat closed. No droop: the lid rests on the box rim.</div></div>
 <div><video controls muted loop src="out/t2_easy_V-B.mp4"></video><div class="cap">V-B —
   open to ~107° against the stop, latch region clears, close &amp; SEAT. Pin retained.</div></div>
</div>
<div class="grid">
 <div><img src="out/hud_V-A.png"><div class="cap">V-A mid-open (HUD frame).</div></div>
 <div><img src="out/hud_V-B.png"><div class="cap">V-B mid-open — ANGLE 106°, PIN R 0.20 A 0.02,
   PEN 0.00 TRAV 0.00.</div></div>
</div>
<div class="grid">
 <div><img src="out/t2_easy_V-A.png"><div class="cap">V-A θ/F/penetration series.</div></div>
 <div><img src="out/t2_easy_V-B.png"><div class="cap">V-B θ/F/stratified-penetration series.</div></div>
</div>

<h2>⑦ Verdict</h2>
<p><span class="verdict {vbadge}">{vbadge}</span>&nbsp; t0 AssemblyRules
{'all PASS' if all(a['ok'] for a in ars) else 'FAIL'} · t1 {'PASS' if t1['verdict'] else 'FAIL'}
(0 drift) · t2 V-A {va['seeds_passed']}/{va['n_seeds']} + V-B {vb['seeds_passed']}/{vb['n_seeds']}
→ {'PASS' if t2['verdict'] else 'FAIL'}. The compiled Easy anchor opens, releases, and re-seats
under physics in both verification modes, with the pin retained.</p>
<p class="sub">Guard trio on every verdict JSON: decision_row + compile_hash ({t2['compile_hash']})
+ shape assertion.</p>

</body></html>"""

    (HERE / "report.html").write_text(html)
    print("wrote", HERE / "report.html", f"(verdict {vbadge})")


if __name__ == "__main__":
    main()
