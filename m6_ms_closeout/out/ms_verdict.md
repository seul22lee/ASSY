# M-S verdict — against SNAPFIT_STARTER §0 (definition of done)

The snap-fit-only track (M-S) is complete. Each §0 item below, with evidence.

| # | Definition-of-done item | Status | Evidence |
|---|---|:--:|---|
| 1 | Ontology expresses functions WITHOUT motion (fastening / retention / release events) | **MET** | tasks/snap_starter.json · ontology/schema.py · report_T-S1a.html §4 |
| 2 | Card formulas reproduce the Bayer worked example (golden G-S1) | **MET** | knowledge/cards/snap_hook_cantilever.py · tests/test_golden_bayer.py · m3_cards/ |
| 3 | Formula checks run on dimensions RE-MEASURED from compiled geometry (not IR values) | **MET (+ blind spot closed)** | verify/t1_remeasure.py · tests/test_t1_drift.py · report_T-S1a.html §6 |
| 4 | Tier0 distinguishes intentional interference (undercut) from defect interference (§5.2) | **MET (window catch); overhang → M-G-1** | verify/t0_static.py · tests/test_positive_retention.py · report_T-S1a.html §6 · out/panel_section.png |
| 5 | Every stage produces visualization artifacts + report.html | **MET** | viz/report.py · report_T-S1{a,b,-panel}.html · m2../m5.. REVIEW.md |

## Detail

### 1. Ontology expresses functions WITHOUT motion (fastening / retention / release events)  — **MET**
MotionSpec.kind += snap_event with event_force_window_N (M-S ext, V-11); T-S1's B1/B2 are assembly/static snap_events, B3 a use-phase imposed clearance. No use-phase DoF.

_Evidence: tasks/snap_starter.json · ontology/schema.py · report_T-S1a.html §4_

### 2. Card formulas reproduce the Bayer worked example (golden G-S1)  — **MET**
tests/test_golden_bayer.py reproduces Calc Example I (p.16): h=3.28, P=32.5, W=58.5 to <0.2%. 7/7.

_Evidence: knowledge/cards/snap_hook_cantilever.py · tests/test_golden_bayer.py · m3_cards/_

### 3. Formula checks run on dimensions RE-MEASURED from compiled geometry (not IR values)  — **MET (+ blind spot closed)**
Tier1 (verify/t1_remeasure.py) measures L/h/b/y from the tagged hook solid's own axes and compares against ⑤'s RESOLVED parameters — NOT ⑥'s own compiled dims. That reference fix closes the blind spot found this session (⑤ resolved L=12 while ⑥ silently built L=7; both sides traced to ⑥, so a 5 mm drift was invisible). 0 drift on T-S1a; guarded by tests/test_t1_drift.py (3/3, incl. a test pinning why the old path was blind).

_Evidence: verify/t1_remeasure.py · tests/test_t1_drift.py · report_T-S1a.html §6_

### 4. Tier0 distinguishes intentional interference (undercut) from defect interference (§5.2)  — **MET (window catch); overhang → M-G-1**
verify/t0_static.py three-way: (a) assembled=0, (b) hook-region max penetration MEASURED = designed y (1.500 mm), (c) elsewhere=0 — on the box (window catch). NEW t0-(d) positive_retention: the nose must BEAR against the catch on pull-out — box = 9.1 mm² (engaged), panel = 0 mm² (held by gravity only), so 'held by gravity' now fails geometrically not by annotation (tests/test_positive_retention.py). The edge-overhang board clip is a distinct topology (D-GEN-4); refused at ⑥ (GEOM_INFEASIBLE), kept as an EXPECTED_FAIL regression target for M-G-1 — NOT routed to N/A.

_Evidence: verify/t0_static.py · tests/test_positive_retention.py · report_T-S1a.html §6 · out/panel_section.png_

### 5. Every stage produces visualization artifacts + report.html  — **MET**
Per-milestone REVIEW.md + out/ (m2 IR graphs, m3 formula-vs-golden, m4 3D+closeup, m5 s5/t0/t1 + three-way + panel). This session: one report.html per run assembling command → rationale sheet → IR graph → 3D → gates → verdict → checklist.

_Evidence: viz/report.py · report_T-S1{a,b,-panel}.html · m2../m5.. REVIEW.md_

## End-to-end runs (this session)

| Run | Config | Verdict |
|---|---|---|
| T-S1a | box, fixed_y, single | PASS |
| T-S1b | box, hold_retention, frequent | PASS |
| T-S1-panel | flat_panel_mount board clip (EXPECTED_FAIL, M-G-1) | FAIL (INFEASIBLE at ⑥ — GEOM_INFEASIBLE)  — **EXPECTED_FAIL ✓** (predicted GEOM_INFEASIBLE at ⑥) |

**Tier2 (physics): N/A across all runs — T-S1 has no use-phase motion (SNAPFIT §0); engagement/retention are Tier1 formulas, interference is Tier0.**

## Decisions updated this session

| ID | Status | Ruling |
|---|---|---|
| D-GEN-1 | **PARTIAL** (was: proven) | Host-agnostic PLACEMENT is proven (anchor-driven, zero host-type branching, one carve attaches to both hosts). Host-agnostic FUNCTIONAL CATCH is NOT proven — the box (window) works; the board clip (edge-overhang) needs topology the card lacks. Full claim re-proves at M-G. No milestone closes on the hollow version. |
| D-GEN-3 | **IMPLEMENTED** | ⑤ owns L (a Bayer result, strain ∝ 1/L²); ⑥ HONORS it — builds the beam at ⑤'s L and lets the window track the beam tip, instead of silently rebuilding at the host span. This fixed a LATENT box bug the ruling predicted: hold_retention resolves L=15.7 mm, but the old ⑥ built L=12 (the anchor span) → the wrong retention force; ⑥ now builds 15.7 (Tier1 confirms measured=resolved). Tier1's reference is now ⑤'s resolved params, not ⑥'s own dims — the guard that makes any ⑤↔⑥ L disagreement visible (was the blind spot). The ruling's 'L-doesn't-fit → INFEASIBLE' framing was refined in the doing: for a window catch L always fits a deep host (window follows the tip), so the board clip's real infeasibility is the retained-cut rule (D-GEN-4 below), not L-fit. |
| D-GEN-4 | **LOGGED (M-G-1)** | Nose topology is a discrete card option — `window_catch` [Bayer p.5 Fig.3, separable chassis] vs `edge_overhang` [Bayer p.5 Fig.2, cap lugs] — conveyed through the binding/port contract, NOT host-type branching. M-G-1 = implement edge_overhang carve + matching overhang three-way + panel golden passes + D-GEN-1 re-proof. |
| D-GEN-5 | **LOGGED (④ constraint)** | `window_catch` is legal ONLY when the catch-side piece is an OWNED host (a card may carve only pieces listed in the element's `host_pieces`; foreign/retained components are immutable). For an external component, `edge_overhang` is the only legal topology. This is a hard constraint on element/topology selection at ④ — enforced downstream today at ⑥ (the retained-cut refusal) and at Tier0 (d) positive_retention; ④ should not emit the illegal choice in the first place. Directly relevant to T-S2's board. |

Next (separate decision): LLM stages ①–④ (command → IR), measured against these goldens.
