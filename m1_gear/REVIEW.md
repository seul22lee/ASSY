# M1 · gear-pair standalone (V-B) — REVIEW (G-H entry point)

Risk-retirement experiment for **R2**, the tooth-profile analog of M0's bore. Hand-built geometry
only — no pipeline, no ontology, no cards — reusing the M0 rig (step2mjcf conventions, G-CONV, V-B,
HUD, and the **FROZEN contact preset**, R5). No solver tuning beyond the sanctioned §6.4 single
timestep halving. Failure at a rung is DATA.

**Question M0 answered:** does a bore survive hint-approximation and hold a pin through contact?
**Question M1 asks:** does a TOOTH PROFILE survive hint-approximation and MESH — no slip, no jam —
at backlash scale?

## Design decision (recorded)

**Gear PAIR — z1=12 pinion, z2=24 gear, m=2.0, face width 8 mm, 20° pressure angle, backlash
0.20 mm** — not rack-and-pinion. The P-GEAR protocol runs 3 revs forward + 3 reverse; a rack would
span 3·πd ≈ 226 mm (36+ teeth) with a panning, tiny-pinion video. A compact rotating pair gives the
clean fixed-frame HUD mesh video that is the core evidence (D15), is the **stricter** test (both
flanks approximated ⇒ retires rack-and-pinion transitively), and is the canonical "gear-pair
standalone". The rack is closer to the Hard anchor and its straight flank is the exact generating
profile — noted as the easier, transitively-covered sub-case.

## The answer — nuanced: R2 splits into R2a (RETIRED) and R2b (OPEN) at m=2 (D-M1-2)

Two separable questions, two separate answers:

**1. Does the profile survive conversion? YES.** All four ladder rungs pass **G-CONV** (mass > 0, no
initial penetration, at rest under gravity). The collision-wedge tooth model (N convex prisms per
flank — the tooth-profile analog of M0's ring-of-wedges) holds together. The involute even passes the
exact-B-rep mesh pre-check (`mesh_check_involute.png`: 0.001 mm³ interference at the ideal centre —
the textbook conjugate mesh).

**2. Does it MESH? Geometrically YES; under the frozen preset NO.**
- **Geometrically conjugate — proven.** The out-of-bounds probe (involute, 4 wedges/flank, fine dt)
  rolls at **ratio −0.501** (ideal −0.500, error **−0.2%**), transmission error peak **1.05°** (far
  under the half-tooth-pitch slip bound of 15°), gear counter-rotating at exactly half speed. See
  `conjugate_roll.png` (measured angle lies on the ideal −z1/z2 line) and
  `t_gear_conjugate_roll.mp4`. The teeth mesh and transmit correctly.
- **But not within the frozen contact preset.** At the frozen dt (5e-4) **and** the single §6.4
  retry (2.5e-4), **every rung DIVERGES** on tooth engagement — the pinion is kicked violently
  backward. The faceted tooth contact is the pathological case for MuJoCo's convex solver:
  conjugate action is *tangential rolling of near-parallel facets*, exactly the tied-separating-axis
  normal-flip that M0's `COLLISION_EPS` note flags — here intrinsic, not removable by an inset. It
  is stable only at dt ≈ 2e-5, **25× below the frozen preset** and far below the sanctioned retry.

**Under the rules (R5 frozen preset + one §6.4 halving), all four rungs FAIL.** Per the G-H ruling
this splits R2 (D-M1-2): **R2a (geometry) is RETIRED** — the involute meshes conjugately (ratio
error −0.5%); **R2b (simulation parameters) is OPEN** — stable only at dt/25, out of bounds under R5.

## The ladder (`ladder.md`, `ladder_verdict.json`)

| Rung | profile | wedges/flank | G-CONV | frozen dt | §6.4 retry | verdict |
|---|---|---|:--:|:--:|:--:|:--:|
| L1 | trapezoid | 2 | PASS | DIVERGED | DIVERGED | **FAIL** |
| L2 | trapezoid | 4 | PASS | DIVERGED | DIVERGED | **FAIL** |
| L3 | involute | 4 | PASS | DIVERGED | DIVERGED | **FAIL** |
| L4 | involute | 6 | PASS | DIVERGED | DIVERGED | **FAIL** |

More wedges (2→6) and the true involute lower the transmission error (L4 TE 0.15° at first contact)
but do **not** cure the divergence — the instability is the contact formulation, not the facet count.

**L1 failure evidence (paper material): `l1_contact_jump.png`.** The trapezoid at the frozen dt —
the contact count flickers 0↔2 as the constant-slope facets make/break contact (they cannot roll
conjugately), the transmission error kicks, and the pinion velocity spikes from ≈0 to **128 rad/s**
(target 3) — "why naive tooth approximations fail, demonstrated in contact simulation."

## Second finding — the trapezoidal v0 profile is doubly deficient

The trapezoid (straight 20° flanks) is *fatter than the conjugate involute in the dedendum*, so at
z=12 it **cannot even seat** at the ideal centre / design backlash (`mesh_check_trapezoid.png`:
4.27 mm³ interference). It needs **+0.9 mm operating centre distance**, inflating backlash from the
designed 0.20 mm to **0.85 mm** (4×). So MECHSYNTH §3.6's trapezoidal v0 is not a viable meshing
profile for a low tooth count even before the contact-stability question — the involute upgrade is
mandatory, not optional, here.

## CoACD-once, for the record (`coacd_pinion.json`)

CoACD (the general fallback, spec 6.2 (b)) on the pinion — the D18 analog. At the finest usable
threshold (0.005) it produced **849 convex hulls** — an impractical collision model versus the
96-wedge hint (and it is CoACD's *best* case: the coarse default threshold 0.03 fills concave
features, the clearance-retention failure it inflicted on M0's bore). So even when it approximately
preserves the tooth valleys it does so at ~9× the geom count and with no per-flank control. The
**wedge hint is the pathway**; CoACD is recorded and dropped. (`mujoco.sdf.gear` remains FORBIDDEN,
D21 — it simulates an ideal gear, not ours.) *(The valley-depth ray metric in `coacd_pinion.json` is
a coarse diagnostic; the load-bearing point is the 849-hull count, not the per-valley numbers.)*

## D-M1-1 (decision / log row)

**Spec consequence (doc-first, §12) — applied:**
- **MECHSYNTH §3.6's "trapezoidal approximation allowed" clause is DEAD.** Evidence = L1's
  contact-jump divergence (`l1_contact_jump.png`): the constant-slope facets cannot roll
  conjugately, so the contact jumps facet→facet (see the flickering contact count) and the pinion is
  kicked to 128 rad/s. §3.6 now reads "the tooth profile is the true involute; `collision_hint()`
  defaults to an involute wedge decomposition."
- **`rack_pinion.collision_hint` defaults to involute wedge decomposition** (convex prism per flank
  segment). The **wedge count** is pending the passing rung — which does not exist in-bounds at m=2,
  so it is DEFERRED behind the R2 mitigation, and a `rack_pinion` design must carry an explicit
  "R2-open at this module" flag until then.

**No rung passes in-bounds at m=2, so the passing-rung wedge count CANNOT be fixed yet** — the analog
of D18's ring-of-wedges outcome, but *unresolved*: the profile is conjugate, the contact is too
numerically stiff for the frozen preset. Per the protocol ("If L4 fails, R2 is real — stop and
report; discuss geometry-scale mitigations before ever touching the preset"), the recommendation is:

- **Do NOT touch the frozen preset (R5).** The divergence is a contact-formulation stiffness, and
  softening the preset to chase it would corrupt every other experiment's contact fidelity.
- **Discuss a geometry-scale mitigation first (R2b mitigation queue, D-M1-2):** (1) **larger module,
  m=2→3** — a gentler contact geometry may relax the dt requirement without touching the preset (R5
  intact); (2) only if (1) is insufficient, a formally versioned preset change with full V-A/V-B
  regression re-runs per R5's amendment procedure. This is the pre-authorised discussion point,
  brought to G-H rather than taken unilaterally.
- **Draft observation (D-M1-DRAFT):** the true blocker is that MuJoCo's convex-convex contact has no
  stable normal for tangent gear flanks. If a larger module does not retire R2, the honest options
  are (a) accept gears require a finer standing timestep for this rig (a preset amendment, recorded
  and re-run across the board per R5), or (b) a contact representation the convex solver handles
  (e.g. a rolling-pitch-cylinder proxy for the kinematics + wedge teeth only for backlash/limit
  checks). Both are G-H calls, not to be taken here.

## Pre-task verification (symbolic track — this sign-off covers it too)

Two bookkeeping items from the m6 panel diagnosis, closed and tested. Decisions in
`DECISIONS_LOG.md`.

**D-GEN-5 (CONFIRMED) — `window_catch` only on an owned, mutable host.** Now enforced at ④ by a new
schema validator **V-14**: a `catch_window` binding may not target a `role='retained'` (foreign,
immutable) piece. Negative-test fixture = the board-clip golden (`snap_panel`), which V-14 rejects
×2 (both bindings); positive control = the box (`catch` = printed wall). Defense-in-depth:
V-14 at ④, the ⑥ retained-cut refusal (GEOM_INFEASIBLE), and Tier0 (d) at ⑦ each catch it
independently. (`run_snap` does not re-validate, so the panel golden still *runs* to ⑥ in the m6
close-out — all three layers remain demonstrated.)

**D-GEN-6 (CONFIRMED) — retention demonstrated geometrically, Tier0 (d) positive_retention.** The
nose must bear against the catch on pull-out: box = **9.12 mm²**, panel = **0 mm²** (held by gravity
only). `verify/t0_static.py` + `tests/test_positive_retention.py`.

**The 9.12 vs ~25 number (your question).** The value in `report_T-S1a.html` is **9.12 mm²** and has
been since it was written — no artifact of mine ever reported 24.94. The ~25 corresponds to the
**naive** computation I did *not* ship: *any* overlap of the nose's shadow with the catch's shadow
(measured directly: **27.68 mm²** at the same grid). The shipped computation counts only the columns
where catch material lies **ahead of the nose in the pull-out direction** — the material that
actually resists lift-off — giving 9.12 mm². The naive number over-credits nose area with no catch
behind it to bear against (e.g. the nose tip sitting in the open window): that area carries no
retention load. **9.12 is the load-bearing figure and the correct one;** which computation you use is
the whole difference.

**V-14 negative test:** `tests/test_validators.py::test_v14_window_catch_not_on_retained` — asserts
V-14 fires on `snap_panel` and stays silent on `snap_starter`.

**Suite tally (all green):** `test_golden_bayer` 7/7 · `test_validators` **15/15** (was 14 + V-14) ·
`test_roundtrip` 4/4 · `test_t1_drift` 3/3 · `test_positive_retention` 2/2 = **31/31**.

## Deliverables in `out/`

`ladder.md` · `ladder_verdict.json` · `conjugate_roll.png` (ratio + TE) ·
`t_gear_conjugate_roll.mp4` (HUD roll) · **`l1_contact_jump.png` (L1 failure — paper material)** ·
`mesh_check_{trapezoid,involute}.png` · `coacd_pinion.json`. G-CONV reports are printed per rung in
the run log.

## G-H checklist (covers M1 + the symbolic pre-task)

M1:
- ☐ Design decision (gear pair, with rationale) accepted
- ☐ R2 = real at m=2 accepted: profile is conjugate (ratio −0.501) but diverges within the frozen
  preset + §6.4 retry; stable only 25× below frozen
- ☐ Trapezoidal v0 rejected for low tooth count (contact-jump divergence + needs 4× backlash to seat)
- ☐ §3.6 edited (trapezoidal clause DEAD; involute wedge default) accepted (doc-first, §12)
- ☐ Ruling on the mitigation: **larger module m=2→3** as the next probe, preset untouched (R2b)
- ☐ D-M1-1 recorded; `rack_pinion` wedge-count default deferred until a rung passes in-bounds
- ☐ L1 failure figure preserved (`l1_contact_jump.png`) as paper material

Pre-task (symbolic):
- ☐ D-GEN-5 confirmed; V-14 enforces it at ④ (negative-test fixture = snap_panel), suite 15/15
- ☐ D-GEN-6 confirmed; positive_retention 9.12 vs 0 mm²; the 9.12-vs-naive-27.7 explanation accepted
- ☐ 31/31 suite tally accepted

Stop after REVIEW.md, per directive. The larger-module retry and any preset discussion await G-H.
