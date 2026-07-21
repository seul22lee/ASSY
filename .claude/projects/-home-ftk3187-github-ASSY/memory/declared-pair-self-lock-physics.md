---
name: declared-pair-self-lock-physics
description: How to model a self-lock HOLD as a declared kinematic pair in MuJoCo (the m19 lead_screw technique)
metadata:
  type: project
---

Verifying a **self-lock hold** for a declared kinematic pair (hinge⊕slide coupled by an `equality` with
`polycoef`) in MuJoCo needs four choices, each forced by a *measured* failure in m19 `p_screw_va.py`.
Future transmission-card D-tracks (coupling, universal_joint — D-M19-0 says they earn their own — and
cam/worm/bevel) will hit the same wall; reuse this rather than rediscovering it.

**Why:** the naive rig (dt=5e-4, soft positive-timeconst equality, normal joint damping) gives a load
that back-drives >12 mm even though the sourced friction (T_f=µ·W·d_mean/2) exceeds the back-drive
torque (W·lead/2π) by 3.3×. The friction never engages because (a) MuJoCo joint `frictionloss` leaks
per-step for small plastic-part inertia at 5e-4, and (b) a soft equality is a *spring the load stretches*
while the coupled body never rotates.

**How to apply:**
- `dt = 1e-4` (not the R5 5e-4). R5 is a CONTACT preset; a joint-only rig (contype/conaffinity=0) has
  no contact, so R5 doesn't fix the clock — set it fine enough that frictionloss is rigid.
- Rigid coupling via **negative** solref = direct stiffness: `solref="-1e8 -1e4"` (not a positive
  timeconst, even at the 2·dt floor — that stays a spring).
- `armature≈1e-5` on the driven joint (driven-train rotor inertia): static-neutral, needed for
  frictionloss numerical rigidity.
- Joint damping **tiny** (1e-5): high viscous damping holds ANY load transiently and MASKS self-lock.
- **Non-tautology probe (mandatory, the [[D-D-1]] standard):** re-run the hold with friction below the
  back-drive torque and assert it slips ≫ tol. m19: sourced holds 0.079 mm, weak(0.5·T_bd) slips 18.4 mm.
  Without this the "hold" could be a solver artifact, not physics.
- Per-seed model-state restore: `run_va` mutates gain/mass/gravity at release; snapshot+restore or
  seed>0 inherits the released model (travel 0).

Ratio non-tautology is separate + easy: drive N revs, measured travel must match `lead·rev` to ≤0.1%
(polycoef = lead/2π in **metres**). See [[full-d-track-milestone-shape]] for the enclosing stage flow.
