# M7 · rack_pinion — REVIEW (G-H entry point)

**Outcome: the rack_pinion card was NOT built.** The R2b routing (D-M1-4 pre-declared rule) ran to
completion and both routes — larger module, and the preset amendment — are exhausted. R2b is a
contact-**formulation** limit, not a tunable one. This folder holds the probe outcome and the G-H
fork it forces; no card, per the pre-declared rule and the honest finding.

## What ran, in order

**1. R2b bounded module probe (D-M1-4, pre-declared rule).** Probed m=5, m=6 (z=12, frozen preset,
5 seeds), extending the trend. Under the probe's `max_stable_dt` metric the trend looked
non-monotonic (peak at m=4, frozen/5). `probe_verdict.png` — **but that metric is lenient
(forward-only, 0.5 rev, 1 seed) and is SUPERSEDED** by the full-P-GEAR result below.

**2. Preset-amendment procedure (D-M1-4 outcome ii).** The rule fired outcome (ii) — no m≤6 reached
the in-bounds line (frozen/2). I opened the preset route and searched for a `preset_v2`.

**3. Self-correction (D-M1-5).** Re-tested every lever under the REAL criterion — the **full P-GEAR
(5 seeds, forward + reverse)**. `preset_route_verdict.png`:

| lever | full P-GEAR (5 seeds, fwd+rev) |
|---|---|
| larger module m∈{2,3,4,5,6} @ frozen dt | **0/5** each |
| softer/compliant preset params (solref/solimp/impratio/cone) @ frozen | ≤ **1/5** |
| finer standing dt, m=4 | 1/5 @ 1e-4 · 0/5 @ 5e-5 · 0/5 @ 2e-5 |
| finer standing dt, m=2 | 0/5 at every dt down to frozen/25 |

**Nothing reaches ≥4/5.** The reversal (backlash slam) + full protocol diverges regardless of
module, preset parameter, or timestep.

## The finding

- **R2a (geometry): RETIRED** — the involute meshes conjugately (forward roll, ratio −0.501; see
  `r2b_frozen_vs_fine.png` / M1 REVIEW). Unchanged.
- **R2b (stable P-GEAR in this rig): a CONTACT-FORMULATION limit, not a tunable preset.** MuJoCo's
  convex-facet contact cannot stably do tangent gear-tooth rolling + backlash-reversal impact at any
  preset parameter or standing timestep tested (down to frozen/25). This is consistent with MuJoCo
  shipping a dedicated *analytic* SDF gear — which D21 forbids for our compiled-geometry philosophy.
- **No viable `preset_v2` exists**, so the amendment procedure yields no candidate to adopt. The
  frozen preset is **UNTOUCHED (R5)**; module bounds stay provisional; **no card was built.**

**Self-correction note (D-M1-5):** the lenient `max_stable_dt` metric produced a "module trend" that
did not survive the real criterion — I corrected my own measure toward the worse truth. Fourth
honesty correction in the log; first that is AI-self-correcting (after D-GEN-2, D-GEN-6, D-M1-2).

## The G-H fork (a human decision, not an AI call)

The pre-declared rule assumed a `preset_v2` would exist; it does not, so adoption is moot and the
next step is a genuine design choice:

- **(A) Change the contact representation.** A rolling **pitch-cylinder proxy** carries the
  transmission kinematics (the ratio/TE that R2a already proves), with wedge teeth kept only for the
  discrete checks they *can* do (backlash / interference / limit). This verifies gear FUNCTION
  without asking the convex-facet solver to do continuous tangent rolling it cannot.
- **(B) Accept the limit.** Gears are not P-GEAR-verifiable in this rig; the `rack_pinion` card
  carries a standing **R2b-open** flag — geometry + formula verified, contact-sim verification
  deferred — and the benchmark scores gears on that basis.

Either way the frozen preset is not touched, and the card is not built until you rule.

## Artifacts (`out/`)

`preset_route_verdict.png` (the honest full-P-GEAR wall) · `preset_route.json` ·
`probe_verdict.png` (lenient-metric module trend, **superseded**) · `probe_verdict.json` ·
`r2b_frozen_vs_fine.png` (what R2b looks like). Decision text: D-M1-4 (rule) + D-M1-5 (outcome) in
`DECISIONS_LOG.md`.

## G-H checklist

- ☐ Accept the self-correction: the lenient probe metric is superseded; full P-GEAR never passes
- ☐ Accept R2b as a contact-**formulation** limit (not module/preset/timestep tunable), preset untouched
- ☐ Accept R2a stays retired; the card is NOT built pending the fork
- ☐ Rule the fork: **(A)** pitch-cylinder proxy contact model, or **(B)** rack_pinion card with a
  standing R2b-open flag
- ☐ Module bounds remain provisional [3.0,4.0] until the fork is resolved

Stopped per the pre-declared rule (preset route → stop after the comparison table). The card and any
contact-model change await your ruling on the fork.
