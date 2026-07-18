# M13 · THE HARD ANCHOR — REVIEW (crank-operated lift platform, §8.2 retargeted)

**Outcome: THE HARD ANCHOR IS CLOSED.** The second benchmark is a crank-driven vertical LIFT PLATFORM
(`slide_rail` ×2 + `rack_pinion` + `pawl_detent`), the verified geometry rotated so **travel is
vertical and gravity acts along it** — the case where the rack-pinion is *functionally necessary*.
The full V-A column passes (raise, transmit-under-gravity, hold, and the integrated P-FULL cycle); the
physics discovered a required element (a holding brake); and P-SLIDE V-B is CHECKPOINTED honestly —
the contact-only slide's clearance-fit retention does not survive gravity-along-travel, a real finding
the horizontal drawer could not surface, recorded with evidence and the preset untouched.

| what | artifact | result |
|---|---|---|
| the platform | [4-view](out/anchor_hard_4view.png) · [exploded](out/anchor_hard_exploded.png) | platform on **vertical rails**, side crank, rack up the platform's back |
| section | [one figure](out/anchor_hard_section.png) | rail↔carriage engagement + pinion↔rack mesh |
| the ⑤ chain | [s5 table](out/s5_chain.md) | drawer_w / L_rack / axis / engagement derived + cited (carries over) |
| alignment firing | [t0 report](out/t0_assembly_rules.json) | parallel/level on real geometry — **PASS, 0.00° / 0.00 mm** |
| it raises | [P-SLIDE V-A](out/lift_pslide_VA.png) · [mp4](out/lift_pslide_VA.mp4) | platform + 0.5 kg raised 128 mm **against gravity**, off-axis 0.00° — **5/5** |
| it transmits under gravity | [P-GEAR V-A](out/lift_pgear_VA.png) · [mp4](out/lift_pgear_VA.mp4) | crank→lift on the π·m·z line, 119.9 mm, ratio resid 0.01% — **5/5** |
| it holds | [P-HOLD before](out/lift_phold_before.mp4) → [after](out/lift_phold_VA.mp4) | crank released, 0.5 kg: **no pawl 62 mm** (D-M13-2) → **with pawl 3.4 mm** (D-M13-4) — **5/5** |
| the brake | [pawl closeup](out/pawl_closeup.png) | asymmetric Bayer angles — shallow drive-over (30°), steep self-locking lock (80° ≥ 73.3°) |
| the full cycle | [P-FULL](out/lift_pfull.png) · [mp4](out/lift_pfull.mp4) | raise 100 mm → hold (drop 3.4 mm) → controlled lower (≤106 mm/s) → base — **5/5** |
| contact-only slide | [P-SLIDE V-B](out/lift_pslide_VB.mp4) | **CHECKPOINT (0/5):** clearance fit not gravity-seated → platform escapes the groove (off-axis→180°) |

## Why a lift, not a drawer (D-M13-2)

A rack-pinion **drawer** is over-engineered: a capable model would correctly *omit* the gear and just
pull the drawer, so a drawer golden would **punish good judgement**. A **vertical lift** flips this —
gravity acts along the travel axis, so the transmission is load-bearing: it both raises the load and
(ideally) holds it. Here the gear is *necessary*, and the benchmark rewards including it.

The mechanism is unchanged — the **verified** drawer geometry rotated −90° about Y so travel is +Z.
The carves, the T-rail, the involute pinion, the L3 collision hint, and the equality coupling are
reused **verbatim**; only the physics layer applies the tilt. What does **not** carry over is named:
gravity is now a **load along travel** (P-SLIDE must overcome weight to *raise*, not just friction),
and the **static/hold** behaviour is new (a drawer never had to resist back-drive).

## Ruling record

- **D-M13-1 (reframe approved):** the m13 kinematic finding was real — pinion axis ⊥ travel, and the
  proven T-rail is a floor rail. Reusing the carves verbatim was correct. "Front-knob + wall-rail" is
  logged as a future carve-generalization item, not now.
- **D-M13-2 (retarget):** the lift, as above. Drawer kept as the labeled alternate
  (`tasks/anchor_hard.json`).
- **D-M13-3 (RULED — Option A):** static/hold stays in the verification layer (static+fixed+load+P-HOLD
  criterion); no schema change. B/C considered and rejected. See the schema section.
- **D-M13-4 (the brake):** `pawl_detent`, the ratchet the P-HOLD finding demanded — built, P-HOLD 5/5.

## ⑤ + t0 — carry over identically

The lift golden is validator-CLEAN; ⑤ resolves the same §8.2 chain (drawer_w 115.30 · L_rack 167.12 ·
axis_offset 30 · engagement 42 · transmission 188.50 mm/rev; **stroke 120 mm** — the 200 mm tower
raises the platform 120 mm leaving ≥45 mm engaged). ⑥ compiles the same 5 bodies. The **alignment
AssemblyRule fires and PASSES on the real geometry — `parallel 0.00°, level Δz 0.00 mm → ALIGNED`** —
because the two rail axes are still the matched pair; the vertical reframe doesn't disturb it.

## t2 — the physics, gravity along travel

- **P-SLIDE V-A — 5/5 PASS.** The platform (carriages + tray + rack + **0.5 kg load**, welded) on a
  declared +Z prismatic joint is **raised against gravity** to 128 mm (past the 120 mm stroke), off
  axis 0.00°. The declared joint carries the vertical load without racking.
- **P-GEAR V-A — 5/5 PASS.** A declared crank hinge (horizontal axis) coupled to the platform slide
  by a near-rigid equality at rp. **Turning the crank raises the load, and the height tracks π·m·z
  per rev to 0.01% — with gravity now along travel.** This is the retarget's headline question, and
  the answer is yes: the ratio holds under load (the constraint force counters gravity). The measured
  curve lies exactly on the §3.6 line.
- **P-HOLD — the finding, then the fix.** With the crank *released* and only sourced Coulomb
  friction (μ·W·rp = 0.059 N·m), a plain rack-pinion **back-drives 62 mm** — it cannot self-lock,
  because the gravity torque (W·rp = 0.198 N·m) far exceeds any friction a μ = 0.30 mesh gives. **A
  crank lift REQUIRES a holding brake** — a design requirement the system discovered from its own
  physics (the pin_hinge-stop pattern, D-M8-5). Reported as a FAIL first, not tuned to a pass. Then
  the brake was BUILT (below), and with it **P-HOLD is 5/5 PASS** (back-drive 3.4 mm).

## The brake the physics demanded — `pawl_detent` (D-M13-4)

The cheapest honest element that makes the golden pass its own protocols: a **ratchet pawl**, which is
**snap_hook's mechanical cousin** — the *same* Bayer cantilever formulas (`P_deflect`, the Fig.18
factor `(μ+tanα)/(1−μtanα)`, `self_locking_angle = atan(1/μ)`) reused **asymmetrically**:

- a **shallow drive-over angle** (30°) so the crank clicks over each ratchet tooth cheaply
  (W_drive ≈ 2.0 N ≪ the ~4.9 N lift force — verified by `PR-CLICK`);
- a **steep lock angle** (80° ≥ the **73.3°** self-lock angle at μ=0.30) where the Fig.18 factor
  **diverges**, so back-drive cannot deflect the pawl out — it self-locks (verified by `PR-PAWL`).

**The m3 permanent-lock cliff (α→90°, D-GEN-2) — mapped there as a WARNING for a separable snap — is
used here DELIBERATELY as the locking feature.** The card delegates to `snap_hook_cantilever` so the
formulas live in one place; `tests/test_pawl_detent.py` (5/5) pins the arithmetic. In the physics the
pawl is modelled as the ratchet's unilateral stop, so the released platform is caught within **one
detent pitch (3 mm)** → P-HOLD 5/5. **The golden is now a design that passes its own protocols: it
raises, transmits under gravity, and holds.**

Guard trio on the verdict ([t2_lift_verdict.json](out/t2_lift_verdict.json)): `decision_row`,
`compile_hash`, `shape_assert` (P-SLIDE + P-GEAR + P-HOLD present, gravity along travel). G9 G-CONV ok.

## D-M13-3 RULED (Option A) — static/hold stays in the verification layer

Ruling: no schema change. The static/hold requirement **is already expressible** — no hard gap:
`phase=static` + `motion=fixed` + `Behavior.load={mass_kg, direction}` (all existing fields), with the
"resists back-drive" requirement carried as a **P-HOLD criterion** (`backdrive_mm ≤ ε`; the
measurement is registered). The open question is only whether back-drive-resistance deserves
first-class status. Three options:

- **(A, recommended)** keep it in the verification layer — static/fixed + load + a P-HOLD criterion.
  No schema change; the load already lives on the behaviour, "without input" is a verification
  *actuation* (release-and-watch), and "must not back-drive" is a *criterion*. None of that is a new
  motion type.
- **(B)** a new `MotionKind = "hold"`/`"self_lock"` — first-class, but adds a kind for one behaviour
  and conflates "no motion" with "resists motion under load".
- **(C)** a `MotionSpec.holds_under_load` / `HoldSpec` attribute — first-class without a new kind, but
  unused elsewhere so far.

**Ruled: Option A.** First-classing "back-drive resistance" would bake one mechanism family's concern
into the ontology (the D-ONT-5 restraint); B and C were considered and rejected. The load already
rides on the behaviour, "without input" is a verification actuation, "must not back-drive" is a
criterion — none is a new motion type.

## P-FULL — the integrated cycle (the mechanism working as one)

One run, three phases ([plot](out/lift_pfull.png) · [mp4](out/lift_pfull.mp4)), **5/5**:

- **RAISE** — the crank drives the platform + 0.5 kg up to 100 mm under gravity; the pawl clicks over
  each ratchet tooth (an **intended contact**, D22, gated apart from a defect).
- **HOLD** — the crank is released, the pawl engages, drop **3.4 mm** (≤ one detent).
- **LOWER** — the pawl is released (its release lever) and the crank lowers the platform under
  **control** at ≤106 mm/s — no free-fall (a released plain rack-pinion would drop, D-M13-2/-4);
  returns to base (1.9 mm).

The pawl engage/release happens at runtime in the phase machine; criteria are D22-stratified.

## P-SLIDE V-B — the honest checkpoint (contact-only retention)

The one that fights the frozen preset, recorded per the rule (not tuned):
[`t2_pslide_vb_verdict.json`](out/t2_pslide_vb_verdict.json), [video](out/lift_pslide_VB.mp4).

- **Interface:** carriage-lip ↔ rail-head T-groove retention (the slide_rail mechanism contact class).
- **Scale:** contacts lost at t≈0.02 s (ncon 8→0); peak off-axis **180°**, peak lateral drift
  **116 mm** — the free welded platform escapes the groove.
- **Diagnosis:** the T-rail is a **clearance fit whose retention was gravity-SEATED** in the horizontal
  drawer (m10 V-B 5/5). Rotated vertical, gravity acts **along** travel and no longer presses the
  carriage into the groove, so the clearance-fit lips are not engaged; the rack/pinion COM offset then
  pitches the platform out. **This is the V-A/V-B distinction made concrete:** the declared prismatic
  joint (V-A) enforced retention 5/5; the contact geometry *alone* does not, under gravity-along-travel.
- **Design implication (deferred, not tuned):** a vertical contact slide needs a **preloaded /
  near-zero-clearance** retention (or the pawl + a bottom stop), not the drawer's gravity-seated fit —
  a finding the horizontal m10 could not surface. The preset is untouched (R5).

## Two elements the physics discovered

The Hard anchor's two benchmarks each surfaced a **required element from their own simulation** — the
system finding what a design needs, not assuming it:

1. **`stop_flange`** (D-M8-5, Easy anchor): honest V-B proved an over-centre lid folds flat without an
   angular stop — the stop is a *discovered* requirement, and the benchmark carries it.
2. **`pawl_detent`** (D-M13-4, this anchor): P-HOLD proved a plain rack-pinion lift back-drives (μ·W·rp
   ≪ W·rp) — the holding brake is a *discovered* requirement, built and made to pass (0/5 → 5/5).

Both were reported as FAILs first and fixed by adding the real element — never tuned to green.

## Closing — the Hard anchor is CLOSED

V-A complete (P-SLIDE, P-GEAR, P-HOLD, P-FULL all 5/5); alignment fires; ⑤ chain resolves; two
physics-discovered elements. **Remaining, named:** P-GEAR V-B stays R2b-deferred (D-M1-7); P-SLIDE V-B
is a checkpoint with a scoped design fix (preloaded vertical retention). Neither blocks the anchor's
closure — the design is assembled, self-consistent, and V-A-verified end to end.

## Status

- Goldens: `tasks/anchor_lift.json` (PRIMARY, validator-CLEAN) + `tasks/anchor_hard.json` (drawer alternate).
- Spine: `m13_hard_anchor/build_review.py` (VARIANT="lift") → ⑤ table, alignment, renders, IR graph.
- Physics: `m13_hard_anchor/p_lift.py` → P-SLIDE + P-GEAR + P-HOLD V-A, plots + mp4, verdict.
- Suite: 72/72; both goldens build clean.
- Physics: `p_lift.py` (P-SLIDE/P-GEAR/P-HOLD V-A) · `p_slide_vb.py` (V-B checkpoint) · `p_full.py` (integrated cycle).
- **CLOSED.** V-A complete + P-FULL; alignment + ⑤ verified; two physics-discovered elements. Deferred (named, non-blocking): P-GEAR V-B (R2b/D-M1-7), P-SLIDE V-B preloaded-retention design fix.
