# M8 · pin_hinge Easy anchor — REVIEW (G-H entry point)

**Outcome: PASS.** The Easy anchor — a box whose lid opens on a formalized **pin hinge** to ~110°,
is held shut by a **snap latch**, and closes back onto its seat — is compiled from the IR and
verified end-to-end: **t0** AssemblyRules (first live firing) both PASS, **t1** re-measure on both
elements shows **0.0000 mm** drift, **t2** P-HINGE **V-A 5/5** and **V-B 4/5** → PASS. This is the
first time the pipeline's own compiled output goes through physics as a **multi-element assembly**
with **element-provided hardware** (D-ONT-11) and **first-class AssemblyRules** (D-ONT-12).

Open [`report.html`](report.html) for the full run (command → decisions → rationale → gates →
videos → verdict).

## The assembly

2 elements — **E1 `pin_hinge`**, **E2 `snap_hook_cantilever`** · 3 pieces — **P1 box [base]**,
**P2 lid [mover]**, **P3 pin [hardware ← E1]** · 2 AssemblyRules — **AR1 exclusion**, **AR2 resource**.
Compiled **motion-before-fasteners** (E1 hinge carve → E2 snap carve → assign P3 = E1.pin_solid).

| view | file | what to look for |
|---|---|---|
| 4-view | [`out/anchor_4view.png`](out/anchor_4view.png) | hinge knuckles + **protruding pin** at the rear (−Y); snap latch at the front (+Y) |
| exploded | [`out/anchor_exploded.png`](out/anchor_exploded.png) | the **pin is a separate hardware body** (D-ONT-11); box knuckles + front catch window on the base |
| **SECTION** | [`out/anchor_section.png`](out/anchor_section.png) | one x=0 cut — hinge knuckle wraps the pin/bore (rear, left) **and** the latch teeth seat in the catch window (front, right) |
| IR graph | [`out/ir_easy.svg`](out/ir_easy.svg) | P3 as hardware (steel/HW badge, dashed `provides`); **AR1/AR2 as rhombus nodes** with subject edges + provenance; **B5→AR1 `checkable form`** |

## Gates, in order

**t0 — AssemblyRules (first live firing on compiled geometry).** Both PASS
([`out/t0_assembly_rules.json`](out/t0_assembly_rules.json)):
- **AR1 exclusion** (provenance `card:snap_hook_cantilever`, D22-aware): the rigid hook's undercut
  interferes with the window edge only through the **0–10° release band** — intended (a real beam
  flexes out); the **free sweep beyond is clean (0.00 mm³)**, so the latch clears the box.
- **AR2 resource** (provenance `task`): Σ(E2.L_mm 12 + E1.edge_margin 27.7) = **39.7 ≤ 80** = P2.rim_length.

**t1 — re-measure on the compiled STEP (COMPILE_DRIFT guard).** Both elements, **0.0000 mm** drift
([`out/t1_easy_verdict.json`](out/t1_easy_verdict.json)): E2 L/h/b/y from the compiled hook + the
Tier0 undercut; E1 pin_d/pin_len/bore_d/knuckle_od from the compiled hinge tags. The IR reference is
⑤'s resolved value, not the compiled dims (the panel blind-spot rule).

**t2 — G-CONV + P-HINGE (5 seeds/mode, ≥4/5 → PASS)** ([`out/t2_easy_verdict.json`](out/t2_easy_verdict.json)):

| mode | seeds | θ_max | θ_final | travel | pin retention | note |
|---|---|---|---|---|---|---|
| **V-A** declared joint | **5/5** | 112° | 3.0° | 0.00 mm | n/a (pin visual) | the joint IS the hinge; knuckle-wedge collisions skipped |
| **V-B** contact-only | **4/5** | 107° | 2.7° | 0.00 mm | radial 0.23 mm (op) | DoF from pin-in-bored-knuckle; open-stop at ~107° |

Videos (HUD burns the scored values in — D15): [`out/t2_easy_V-A.mp4`](out/t2_easy_V-A.mp4),
[`out/t2_easy_V-B.mp4`](out/t2_easy_V-B.mp4); side-by-side HUD frames
[`out/hud_V-A.png`](out/hud_V-A.png) / [`out/hud_V-B.png`](out/hud_V-B.png); θ/F/penetration series
[`out/t2_easy_V-A.png`](out/t2_easy_V-A.png) / [`out/t2_easy_V-B.png`](out/t2_easy_V-B.png).

## Rationale sheet (the harness rulings this milestone rests on — D-M2-1)

1. **Lid seating on the TEMPLATE, not the card** (step 1). The lid-on-box seat is a host property, so
   the collision primitive is added to `lid_panel`/`box_shell`, inset by **COLLISION_EPS = 0.2 mm**
   laterally (D14 — never share a face-plane with the static rim; the drawer lesson), Z left exact.
   G-CONV (c) at-rest drift went **24.5 mm → 0.000 mm**.
2. **Two contact classes — `mech` vs `seat`.** The ring-of-wedge bore proxy + pin (`mech`) and the
   seating boxes (`seat`) collide only within their own class. This is what lets the pin/bore DoF and
   the seating load path both work while their convex-proxy cross-grinding — the ~26° sweep jam — is
   suppressed as the artefact it is. In V-A the declared joint IS the mechanism, so the wedge
   collisions are skipped entirely (a convex ring is not clearance-perfect and jams the joint).
3. **A designed open-stop** (the hinge lug hard-stop, formalized). V-A's stop is the joint range;
   V-B leans on a backstop ledge at ~107°. The follower reverse **HOLDS −F_MAX** (no coast — a coast
   lets an over-centre lid fling round past 180°).
4. **Stratified verdict (D22).** Only non-intended **travel** interference gates. The closing seat,
   the open-stop, the pin/bore interface, and the **0–10° latch-release band** (AR1's finding) are
   intended contacts (observables). Pin retention is read during **operation**; the stop-impact jolt
   (radial 0.31–0.65 mm at ~107°) is an observable — the seat-impact ruling, applied to the pin.

## For the reviewer

- **B3 is absent by design** — it is the reserved **stop-variant slot** (the rotation *ceiling*
  imposed by a `stop_flange`, ≤108.85°, `imposed_by F1`); the Easy anchor has no stop flange, so its
  behaviours are B1,B2,B4,B5,B6. Not a dropped behaviour.
- **V-B is 4/5, not 5/5.** The one failing seed exceeds the pin/bore *operation*-phase interface
  limit by a hair (0.40 vs 0.30 mm); the retention gate itself passes on all five. ≥4/5 is the
  §6.4 verdict rule. The pin/bore fit is thus flagged **marginal**, honestly, in the per-seed record.
- Guard trio on every verdict JSON: `decision_row` + `compile_hash` + a shape assertion.

## Reproduce

```
./bin/py tasks/run_m8_t2.py verify/t2_physics/out_easy   # t2 V-A + V-B (5 seeds each)
./bin/py tasks/run_m8_t1.py verify/t2_physics/out_easy   # t1 re-measure (both elements)
./bin/py m8_pin_hinge_easy/build_review.py               # renders + IR + t0 ARs
./bin/py m8_pin_hinge_easy/build_report.py               # report.html
```

Decisions this milestone: **D-ONT-11** (element-provided pieces), **D-ONT-12** (AssemblyRule),
**D-M2-1** (physics harness), **D-M1-8** (R2b deferred option 3). See `DECISIONS_LOG.md`.
