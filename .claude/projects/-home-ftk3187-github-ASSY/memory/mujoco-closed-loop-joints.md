---
name: mujoco-closed-loop-joints
description: How to model a closed-loop spatial joint (e.g. Cardan/universal joint) in MuJoCo without locking
metadata:
  type: project
---

Modeling a closed-loop spatial linkage (a universal/Cardan joint, and the future double-Cardan CV
driveshaft of [[D-M21-2]]) in MuJoCo hinges on a **DoF count**, not solver tuning. This cost several
m21 prototype iterations before it worked.

**The trap:** the intuitive topology — input hinge + output hinge as two *world branches* + a cross,
closed by `connect` equalities — LOCKS. A `connect` removes 3 scalar DoF (a point weld); the loop only
has ~2 to give, so one connect → 0 DoF (rigid), two → over-constrained. Verify at t=0 by printing
`nv` and the connect residual `d.efc_pos[:d.nefc]` before stepping — if the residual isn't ~0 the
initial pose is inconsistent (connect anchors are in body1's LOCAL frame, mapped through the initial
pose), and no solver setting will save it.

**What works (m21 P-UJOINT, rig option i):** a **serial chain** `input(hinge A) → cross(hinge pin1) →
output(hinge pin2)` — a TREE, `nv=3` — closed by **ONE** `connect` pinning the output-shaft *tip* to a
world anchor on the output axis B. That connect's radial component is redundant against the rigid shaft
length, so it nets **−2 DoF**, leaving exactly the 1 loop mobility. Stable (loop residual ~5e-6 m, no
drift over 3 rev at dt=1e-4). The Cardan velocity fluctuation then EMERGES — do NOT impose it with a
`polycoef=cosβ` equality (that declares the average and erases the physics you're verifying).

**Readout of the driven roll:** put an off-axis site on the output body (⊥ B) and take
`atan2(site·e2, site·e1)` with `e1=Y, e2=B×Y` — gives θ_out directly.

**Phase (for a formula overlay):** the geometric phase φ0 (min-speed point) is PREDICTED from the
assembly (input yoke pin in the bend plane at θ=0 → min at θ=90°), not fit; then report the measured
argmin location to VERIFY phase (m21: predicted 90° vs measured 90.0°, err 0.03°). Pairs with the
[[declared-pair-self-lock-physics]] recipe (same dt=1e-4 clock, same discrimination discipline: β=0
must flatten the fluctuation) and the [[va-video-evidence-rule]].
