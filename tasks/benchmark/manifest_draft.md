# m14 task ladder — DESIGN DRAFT (command strings + axes)

16 tasks over the 3 verified bases. Each command reads like a real request. `expected_class` codes
(layer/code) are finalised against the actual pipe in the certification pass.

## Base A — snap-lid box (T-S1 / snap_hook_cantilever on box_shell+lid_panel)

| id | command | axis | expected |
|---|---|---|---|
| A1-snap-base | "Design a snap-lid box I can push shut and pull open by hand. Plastic, for 3D printing." | base | PASS |
| A2-snap-big | "Design a snap-lid storage box about 120 × 90 × 50 mm that pushes shut and pulls open by hand. Plastic." | dimensional | PASS (⑤ re-resolves hook count/geometry, in bounds) |
| A3-snap-force | "Design a push-on snap-lid box that closes with no more than 60 N by hand and needs at least 15 N of pull to open." | spec-tightening | PASS (mating ≤60 N, retention ≥15 N) |
| A4-snap-tooshort | "Design a snap-lid box only 8 mm tall that pushes shut." | dimensional→INFEASIBLE | INFEASIBLE(⑤, hook L>wall — no room for the beam) |

## Base B — hinged latch box (Easy / pin_hinge + snap_hook + stop_flange)

| id | command | axis | expected |
|---|---|---|---|
| B1-hinge-latch-base | "A small hinged box whose lid latches shut at the front. Plastic, 3D printing." | base | PASS (V-A + V-B) |
| B2-hinge-big | "A hinged box with a 100 × 70 mm lid that latches shut at the front. Plastic." | dimensional | PASS |
| B3-hinge-nolatch | "A hinged box whose lid opens and stays open near 110° — no latch, just a stop." | constraint (forbid snap, require stop) | PASS |
| B4-hinge-nostop | "A hinged box whose lid opens 90° and returns closed — no stop tab." | constraint→EXPECTED_FAIL | EXPECTED_FAIL (over-centre lid folds flat, V-B 0/5 — D20) |
| B5-hinge-openangle | "A hinged box whose lid opens at least 100° and settles closed within 5°." | spec-tightening | PASS |

## Base C — crank lift (Hard / slide_rail×2 + rack_pinion + pawl_detent), drawer alternate

| id | command | axis | expected |
|---|---|---|---|
| C1-lift-base | "Design a crank-operated platform that raises and lowers a load to different heights." | base | PASS (V-A + P-FULL + P-SLIDE V-B) |
| C2-lift-load | "Design a crank platform that raises a 1 kg load by about 90 mm." | dimensional (load+stroke) | PASS |
| C3-lift-holddrift | "Design a crank lift whose platform holds within 5 mm of its set height when the crank is released, under a 0.5 kg load." | spec-tightening (hold-drift) | PASS (pawl ≤ one detent) |
| C4-drawer | "Design a desktop cabinet whose drawer slides out horizontally when you turn a knob." | constraint (horizontal, no gravity-hold) | PASS (drawer alternate, V-A) |
| C5-lift-nogear | "Design a crank lift that holds a 0.5 kg load, but without any gear or ratchet." | constraint-contradiction→INFEASIBLE | INFEASIBLE(④/validator — the rot_to_trans + hold behaviours have no realizer once gear+pawl are forbidden) |
| C6-lift-toofar | "Design a crank lift that raises the platform 400 mm inside a 200 mm-tall frame." | physically-contradictory→INFEASIBLE | INFEASIBLE(⑤ — stroke > the frame/rack geometry allows) |

## Out-of-vocabulary infeasible

| id | command | axis | expected |
|---|---|---|---|
| D1-screw-jack | "Design a threaded screw-jack that lifts a load by turning a leadscrew." | out-of-vocab→INFEASIBLE | INFEASIBLE(④ — no leadscrew/screw card in the registry; KG offers nothing) |

## Axis coverage
- **dimensional:** A2, B2, C2 (feasible) · A4, C6 (infeasible-dimensional)
- **constraint:** B3, B4, C4, C5, D1
- **spec-tightening:** A3, B5, C3
- **infeasible (4):** A4 (⑤ geom), C6 (⑤ stroke), C5 (④/validator constraint-contradiction), D1 (④ out-of-vocab)

## Certification approach
- A1/B1/C1 base: reuse the already-certified milestone verdicts (m6 snap tier1, m8 V-A/V-B, m13 V-A/P-FULL/P-SLIDE-VB).
- Variants: build golden from the existing builders (parameterized — NO new cards/templates), run ⑤→⑥→t0(→t1)→t2 V-A; snap = tier1 formula.
- Infeasibles: build the IMPLIED (broken) IR the command entails and show the deterministic layer rejects it at the declared code (no LLM needed — the refusal is a property of the deterministic pipe).
