# M6 · M-S close-out — REVIEW (G-H entry point)

The snap-fit-only track (M-S) taken end-to-end: golden IR → ⑤ resolve → ⑥ compile → Tier0 → Tier1
→ `report.html`, for three hosts. This session ALSO re-opened the m5 D-GEN-1 sign-off after the
panel render failed visual review, found two real defects, and fixed the compiler bugs behind them.

Read this first, then the three `out/report_*.html`, then `out/ms_verdict.md`.

## What to look at

| Artifact | What it shows |
|---|---|
| `out/report_T-S1a.html` | box, fixed_y — **PASS**. The clean end-to-end: rationale sheet → IR graph → 3D → Tier0 three-way (undercut measured = designed y) → Tier1 (0 drift) → verdict. |
| `out/report_T-S1b.html` | box, hold_retention, frequent — **PASS**. The lengthened beam (**L=15.7 mm**) now actually gets built (see D-GEN-3). |
| `out/report_T-S1-panel.html` | board clip — **EXPECTED_FAIL ✓** (GEOM_INFEASIBLE at ⑥). A live regression target for M-G-1, not N/A, not deleted. |
| `out/panel_section.png` | ground-truth y=0 section: the window-catch compile cuts a **notch into the retained board** — the illegal move that makes the clip infeasible. |
| `out/box_section.png` | the box for contrast — nose seated in a window cut in a *printed* wall (legal). |
| `out/ms_verdict.md` | the five SNAPFIT §0 definition-of-done items + the decisions log (D-GEN-1/3/4). |
| `out/variant_smoke.md` | T-S1c (n=4, tighter-but-feasible), T-S1d (α_out=90° → permanent). |
| `PANEL_HOLD.md` | the full diagnosis that triggered the fixes (bindings, anchors, resolved vs compiled). |

## The panel HOLD — resolved

Your visual review was right: the panel was geometrically wrong. Two defects, both traced to real
compiler bugs, both now fixed. Neither was "quietly fixed" — they are logged as decisions.

**Defect 1 — ⑥ silently discarded ⑤'s L.** `build_hook_at` set the beam length from the anchor span
(`growth_dist`), ignoring ⑤'s resolved L. It looked fine on the box only because the box anchors
*coincidentally* gave `growth_dist = 12 = L`. On T-S1b that coincidence broke the other way:
hold_retention resolves **L=15.7 mm**, but ⑥ built **12** → the wrong retention force, silently.
**Fix (D-GEN-3):** ⑥ now builds at ⑤'s L; the window tracks the beam tip (a longer beam just
catches lower on a deep wall). Tier1 confirms measured = resolved on both box runs.

**The Tier1 blind spot you asked about.** Tier1's "IR" reference was ⑥'s *own* compiled dims, so
both sides of the drift check traced to ⑥ — a 5 mm ⑤↔⑥ disagreement was invisible. **Fix:** Tier1
now compares against ⑤'s *resolved* parameters. Guarded by `tests/test_t1_drift.py` (3/3), including
a test that pins *why* the old path was blind so the regression can't silently return.

**Defect 2 — window nose used for an edge-overhang catch.** The card's only catch is a WINDOW (cut a
hole, seat the nose in it). A board clip must grab the board's edge. Compiled as a window catch, the
panel cuts a **notch into the retained board B1** — illegal, because B1 is a foreign, immutable part
(a PCB). **This is the true infeasibility**, and it can't false-pass on an L/geometry coincidence.
**Fix:** ⑥ refuses a window catch whose receiver is `role='retained'` → GEOM_INFEASIBLE, roll back to
④. On your Q about t0: it never had a blind-spot pass here — the earlier N/A masking (now removed)
was mine, and it's gone.

## Post-diagnosis additions (this session)

- **Tier0 (d) positive_retention** (`verify/t0_static.py`). For every snap_event retention behavior
  (B2-class) the nose must *bear against the catch on pull-out* (the base→retained separation axis):
  box = **9.1 mm²** engaged (≈ y·b), panel = **0 mm²** (the window notch clears the nose on +Z lift).
  "Held by gravity only" now fails **geometrically**, not by annotation. The panel report carries the
  machine-checked `positive_retention = 0.00 mm²`; guarded by `tests/test_positive_retention.py`.
- **D-GEN-5 (logged, ④ constraint).** `window_catch` is legal only when the catch-side piece is an
  *owned host* (a card may carve only pieces in the element's `host_pieces`; foreign/retained parts
  are immutable). External components admit `edge_overhang` only — a hard constraint on ④ topology
  selection, relevant to T-S2's board. Enforced downstream today (⑥ retained-cut refusal + Tier0 (d)).

## Decisions (full text in `out/ms_verdict.md`)

- **D-GEN-1 → PARTIAL** (was: proven). Host-agnostic *placement* is proven (anchor-driven, zero
  host-type branching, one carve on both hosts). Host-agnostic *functional catch across topologies*
  is **not** — re-proves at M-G. No milestone closes on the hollow version.
- **D-GEN-3 → IMPLEMENTED.** ⑤ owns L; ⑥ honors it (window follows the tip); Tier1 references the
  resolved params.
- **D-GEN-4 → LOGGED (M-G-1).** Nose topology is a discrete card option — `window_catch` [Bayer p.5
  Fig.3] vs `edge_overhang` [Bayer p.5 Fig.2] — conveyed via the binding/port contract, not host-type
  branching. **M-G-1** = implement the edge_overhang carve + the matching overhang three-way check +
  panel golden passes + D-GEN-1 re-proof.
- **D-GEN-5 → LOGGED (④ constraint).** window_catch only on owned hosts; external ⇒ edge_overhang.

## Panel intent (declared)

**SEPARABLE** (service access): α_out = 45° ≪ self-lock(μ=0.3)=73.3°, so the joint releases; the
resolved **W_sep = 31.84 N** sits inside the hand-open window [15, 60] N. Declared functionally in
the golden by B2's snap_event window + PR-T1-SEP retention_floor ≥ 15 N. Not the permanent case
(that is T-S1d, α_out=90°).

## Status vs SNAPFIT §0 (definition of done)

5/5 items MET (item 3 "+ blind spot closed", item 4 "window catch; overhang → M-G-1"). See
`out/ms_verdict.md`.

**Tier2 (physics): N/A** across all runs — T-S1 has no use-phase motion; engagement/retention are
Tier1 formulas, interference is Tier0.

## Tests

`test_golden_bayer` 7/7 · `test_validators` 14/14 · `test_roundtrip` 4/4 · `test_t1_drift` 3/3 (new) ·
`test_positive_retention` 2/2 (new).

## Asking for

1. **G-H sign-off on the M-S close-out** (box T-S1a/T-S1b end-to-end, the report/runner, the five
   DoD items).
2. **Acknowledge D-GEN-1 = PARTIAL** and **D-GEN-4/M-G-1** as the next-milestone item (edge-overhang
   catch → panel golden passes → D-GEN-1 re-proof). The panel golden stays as an EXPECTED_FAIL
   regression target.

Stop after REVIEW. LLM stages (①–④: command → IR) remain a separate next decision.
