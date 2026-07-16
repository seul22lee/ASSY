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
