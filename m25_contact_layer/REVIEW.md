# M25 · contact_layer — REVIEW

**Outcome: the reviewer's ask — verify landings/stops by ACTUAL CONTACT, not a declared joint range that
silently stands in for the part — is delivered as a GENERIC protocol (resolves DRAFT D-M19-3).** The §14
fit schedule supplies what was missing (a generic source of WHICH pairs mate); the contact layer enables
real MuJoCo contact for the class-② limit carriers on the frozen R5 preset, and judges by the IR-declared
criteria + the generic guard suite ONLY. Both Phase-A assemblies pass.

## The contact doctrine (①/②/③) — the framework's honest contact map
Every mating pair falls into one class; the runner PRINTS the map and collides ONLY class ②:

- **① driving curved contact** (gear teeth in mesh, thread flanks, cam curves) → **R2b, V-B deferred**
  (m17/D-M1-7). The *driven* make-break is what blows up a rigid-body engine; excluded, with the reason
  printed per pair.
- **② landings / stops / retention-ride** (flat, rigid interfaces) → **verified HERE by real contact.**
  A class-② pair that carries a **LIMIT** (a stop, a landing) gets the contact; the declared joint range
  that stood in for it is **widened (limited=false)** so the PART does the stopping. A class-② pair that
  is a continuous **DoF** (ride/guidance) carries no limit — it stays the declared joint + fit clearance,
  and is printed as `(dof)`.
- **③ elastic members** (snap beams, leaf springs) → **D3, forces by formula** (Bayer), not rigid-body
  sim; excluded, printed (e.g. the clip×bump retention is the sourced Bayer W_out, m23).

This runs on the frozen R5 preset (dt 5e-4, solref 0.001/1.0, solimp 0.99/0.9999/1e-4, µ 0.30, condim 4)
— contacts exist now, so the R5 clock applies (D-M19-2 scope). Precedents: the **m8 lid-fold STOP** and
the **m10 T-rail retention** both ran class-② contact on this preset successfully; R2b's blow-up is the
*driven* flank make-break, not a static landing.

## MACHINERY — `verify/contact_layer.py` (reusable, element-agnostic)
Takes a compiled assembly's bodies + a contact schedule; builds an MJCF where the class-② limit pairs
collide via explicit `<pair>` (everything else contype/conaffinity 0 — nothing auto-collides), runs the
task's declared use-phases under gravity + declared loads, and judges: **the IR-declared criteria +
G-CONV + all_parts_retained + divergence.** Nothing element-specific lives in the runner; the
classification is DATA ([`contact_schedule.py`](contact_schedule.py)).

## screw_lift · [`out/t2_contact_screw_lift_verdict.json`](out/t2_contact_screw_lift_verdict.json)

| class-② limit carrier | was | now | result |
|---|---|---|---|
| platform × TOP collar (thread runout) | nut_slide range [0, 40] | collar CONTACT (limited=false) | **overcranked → stops at 40.02 mm** |
| platform × BOTTOM stop (base landing) | nut_slide lower bound 0 | base CONTACT | **lands at −0.52 mm (s≈0)** |
| platform × guide columns | — | the slide DoF + 0.35 fit clr | (dof) |
| screw × nut thread | — | ① EXCLUDED — R2b driven flank (m17) | — |
| coupling × crank | — | fused rigid grip (m20) | — |

The overcrank drives the platform **past** target; the collar PART carries the limit (subsumes the m22
overcrank probe). Video [`out/t2_contact_screw_lift.mp4`](out/t2_contact_screw_lift.mp4) — HUD names the
carrier ("STOP: TOP collar contact"). The coupling chain is inherited (m22 P-LIFT 5/5; its rigid
equalities need dt 1e-4, which fights the R5 contact clock, so the platform is driven directly); the
self-lock HOLD is separate physics (m19). PASS, G-CONV ok.

## latched_drawer · [`out/t2_contact_latched_drawer_verdict.json`](out/t2_contact_latched_drawer_verdict.json)

| class-② limit carrier | was | now | result |
|---|---|---|---|
| panel × face frame (closed stop) | drawer_slide lower bound 0 | face-frame CONTACT (limited=false) | **driven shut → lands at −0.20 mm (s≈0)** |
| tray × rail | — | the slide DoF + 0.35 fit clr | (dof) |
| clip × bump | — | ③ EXCLUDED — elastic D3; sourced Bayer W_out 30.4 N (m23) | — |

Video [`out/t2_contact_latched_drawer.mp4`](out/t2_contact_latched_drawer.mp4) — HUD "STOP: panel on
FACE FRAME". PASS, G-CONV ok.

## Bookkeeping
- **D-M19-3 DRAFT → CONFIRMED** (this milestone is its resolution; m8/m10 class-② precedents cited).
- **§13 S4** + **§14 T5** each gained a one-line pointer: class-② interfaces are verified by the contact
  layer where the fit schedule declares them.
- **Phase B note:** the push_latch notch seating is class-② — its S4 inherits this machinery.
- All m25 work free/local (no LLM/API). **Still HELD:** the lite admission gate + the m15 frontier
  column. **AWAITING REVIEW.**
