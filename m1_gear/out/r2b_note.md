# What R2b looks like

`r2b_frozen_vs_fine.mp4` · `r2b_frozen_vs_fine.png` — the SAME involute pair (z=12/z=24, 4
wedges/flank, ideal centre, **same seed**), driven identically. The only difference is the solver
timestep: **frozen preset dt = 5e-4** vs **dt/25 = 2e-5**.

- The geometry is identical and conjugate — **R2a is retired**, and this is the proof that R2b is a
  *simulation-parameter* risk, not a geometry one: nothing about the teeth changed.
- **Frozen dt (left / red):** the faceted tooth contact makes and breaks between facets, the pinion
  velocity chatters ±20 rad/s around the 3 rad/s target, and at t ≈ 0.24 s the contact force spikes
  to **~2×10¹⁶ N** and the pinion is flung — divergence.
- **dt/25 (right / green):** the same pair rolls calmly, contact force peaks at **0.6 N**, pinion
  tracks the target — ratio −0.501.

Sixteen orders of magnitude of contact force separate the two runs of *identical geometry*. That gap
is R2b. The mitigation queue (D-M1-2) attacks it geometry-side first (larger module, m=2→3) before
any preset change.

## Mitigation queue (D-M1-2, extended)

1. **Larger module** (m=2→3→…, geometry-side, R5 intact) — probed through m=6; monotonic dt relaxation
   but never reached in-bounds (D-M1-3/-4/-5). Exhausted within the usable envelope.
2. **Formally versioned preset change** (`preset_v2`, per R5's amendment procedure, full V-A/V-B
   regression) — D-M1-5 found NO viable candidate: the limit is contact *formulation*, not a tunable
   preset parameter.
3. **[DEFERRED] Alternative backend — PhysX 5 SDF contacts** as a `preset_v2`-time candidate.
   Evaluated against the *same* V-A/V-B regression set as any preset amendment (M0 hinge both
   variants, M0-stretch V-B, snap-box t0 contact equivalents). Rationale: R2b is a convex-facet
   contact-formulation limit (D-M1-5) — a signed-distance-field contact solver addresses the
   formulation, not a parameter. Because the `collision_hint` and protocol layers are **engine-neutral
   by design (D12)**, the swap surface is confined to `verify/t2_physics` only; the ontology, cards,
   and compile stay untouched. Note the tension with D21/D-M1-5's caution (MuJoCo's own analytic SDF
   gear is forbidden for our *compiled-geometry* philosophy) — an SDF *contact* over our own compiled
   meshes is a different thing from an analytic gear primitive, and that distinction is what a G-H
   sign-off on this option would have to rule on.
