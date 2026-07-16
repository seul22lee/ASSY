# M1 gear-pair — ladder verdict (P-GEAR, frozen preset R5 + §6.4 single retry)

Pass = converges + meets criteria within the frozen dt (5e-4) or the ONE §6.4 retry (2.5e-4). Going finer than that violates R5 and is recorded as a rung FAIL.

| Rung | profile | wedges/flank | G-CONV | frozen dt | §6.4 retry | verdict | note |
|---|---|---|:--:|:--:|:--:|:--:|---|
| L1 | trapezoid | 2 | PASS | DIVERGED | DIVERGED | **FAIL** | trapezoid needs op_cd +0.9mm (backlash 0.85mm) to seat |
| L2 | trapezoid | 4 | PASS | DIVERGED | DIVERGED | **FAIL** | trapezoid needs op_cd +0.9mm (backlash 0.85mm) to seat |
| L3 | involute | 4 | PASS | DIVERGED | DIVERGED | **FAIL** | meshes clean at ideal cd, backlash 0.20mm |
| L4 | involute | 6 | PASS | DIVERGED | DIVERGED | **FAIL** | meshes clean at ideal cd, backlash 0.20mm |

## Out-of-bounds conjugate probe (evidence, NOT a pass)

Involute n4 **forward** roll at dt=2e-05 (25× below the frozen preset): **ratio −0.501**
(ideal −0.500, err **−0.2%**), peak transmission error **1.05°** (< half a tooth pitch = 15°, so no
slip). It rolled ~0.5 rev in perfect conjugate lock before diverging (marginally stable even here).

**The tooth profile IS geometrically conjugate — it meshes and transmits at exactly the right
ratio.** It is simply not numerically stable within the frozen contact preset: the faceted tooth
contact needs a timestep ~25× finer than the frozen dt (and far below the single §6.4 retry) to
avoid the tangent-facet blow-up. Under R5 that is out of bounds → every rung FAILS.

See conjugate_roll.png (measured gear angle lies on the ideal −z1/z2 line) and
t_gear_conjugate_roll.mp4 (80-frame HUD roll).