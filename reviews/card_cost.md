# Card authoring cost (external review point 10, D-REV-1)

Per-card cost, sourced to the first commit that introduced the card. **LOC = card class (in
`knowledge/cards/base.py`) + the card's geometry/formula module + its dedicated tests** (card-specific
code only; shared infrastructure excluded). "Sessions" = milestone sessions to a passing card + its
physics (git-milestone granularity). "New schema/API" = ontology/validator/measurement surface the
card *required*. "New verifier" = whether its verification protocol is new code or reused/adapted.

| card | first commit | milestone(s) · sessions | LOC (class + geom + tests) | new templates | new verifier | new schema / API surface |
|---|---|---|---|---|---|---|
| `snap_hook_cantilever` | `a85270a` | m3+m4+m6 · **~3** | **731** (123 + 426 + 182) | **2** (box_shell, lid_panel) | **NEW** — Bayer Tier1 formula recheck (PR-T1/PR-LATCH) | **large**: `snap_event` MotionKind, `event_force_window_N`, V-11 |
| `pin_hinge` | `76f6466` | m8 (formalizes m0) · **~1** | **484** (122 + 273 + 89) | 0 (reuses box/lid) | **REUSED** — P-HINGE V-A/V-B from m0 | ProvidedPiece / hardware pieces (D-ONT-11) |
| `stop_flange` | `ff6f812` | m8 · **~1** | **210** (112 + 98 + 0*) | 0 | **REUSED** — contributes a criterion to P-HINGE | PassiveFeatureCard class, `bound="max"` (D-ONT-9) |
| `slide_rail` | `1764f18` | m10 (+m13 fix) · **~1.5** | **489** (124 + 244 + 121) | **3** (slide_base, slide_carriage, slide_base_dual) | **NEW** — P-SLIDE V-A/V-B | **none** (translation existed; D-M13-6 is a resolve rule) |
| `rack_pinion` | `0a2ff66` | m7 (attempt) + m11 · **~1** | **412** (104 + 195 + 113) | **2** (pinion_carrier, rack_carrier) | **ADAPTED** — P-GEAR V-A from M1 | **none** (rot_to_trans existed) |
| `pawl_detent` | `61f6225` | m13 (part) · **~0.5** | **286** (77 + 127 + 82) | 0 (carved, no host) | **MOSTLY REUSED** — delegates snap's `fig18`/`self_locking_angle`; small PR-PAWL/PR-CLICK/P-HOLD | `backdrive_mm` measurement (1 line) |

\* `stop_flange` shares `tests/test_golden_hinge.py` (the stop pair) rather than a dedicated file.

## The trajectory — the marginal card gets cheaper (VISION-3, now quantified)

The point-10 finding, read down the table: as the scaffolding (templates, the verification harness,
the formula library, the validator suite) amortizes, **each new card costs less**.

- **LOC:** 731 (snap, foundational) → 286 (pawl) — the sixth card is **~40%** the first, and it
  *delegates* its formulas to the first (`pawl_detent` imports `snap_hook_cantilever`).
- **Sessions:** ~3 → ~0.5 — the **3→1→0.5** curve VISION-3 asserted, now sourced to commits.
- **New schema/API:** front-loaded — snap/hinge/stop each added ontology surface; **slide, rack, and
  pawl added essentially none** (the decision surface stabilized after the third card).
- **New verifier:** 3 of 6 cards **reuse or adapt** an existing protocol (hinge←m0, rack←M1,
  pawl←snap) rather than write new physics.
- **Templates:** 7 host templates total across 6 cards; the last card (`pawl_detent`) needed **zero**.

**Honest limit (unchanged):** cards are still hand-authored — this table measures the *human* cost and
shows it falling, but does not automate it. Handbook→card compilation is the paper-2 direction
(VISION-3). The cost is stated, not hidden.
