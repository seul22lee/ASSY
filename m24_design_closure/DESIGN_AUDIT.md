# M24 · Design-closure audit — screw_lift & latched_drawer against spec §14 (Task D-track)

**Purpose:** before redesigning, an honest inventory of where each task stands against the seven §14
stages. `done` = the deliverable exists and meets the §14 bar; `partial` = exists but below the bar (one
gap named); `missing` = not present. One line of evidence each. The redesign (this milestone) executes
every `partial`/`missing` **in stage order per task**.

The two §14 bars: **DESIGN COMPLETENESS** (compiled pieces — no world-geometry stand-ins; dimensions
derive from mates via a FIT SCHEDULE; every joint names a physical carrier; elements impose+carve) and
**FULL REVIEWER VISUALIZATION** (IR diagram, section views from compiled solids, transparency+zoom video,
exploded view).

## A · screw_lift (m22 Task A)

| stage | status | evidence / gap (one line) |
|---|---|---|
| **T1** golden IR + `ir_<task>.{mmd,svg}` | ✅ done | `tasks/screw_lift.json` by construction (validator-CLEAN); `m22_composition/out/ir_screw_lift.{mmd,svg}` rendered by `tools/render_ir.py`. |
| **T2** validate | ✅ done | `build_goldens.main()` validates CLEAN; compiles to 3 solids (`compile_assembly` → P1/P2/P3). |
| **T3** design closure | 🔶 **partial** | 3 compiled solids exist, BUT: **(a)** the crank/base-frame/coupling-hub the reviewer sees on film are **MJCF visual stand-ins** in `p_lift_va.py` (reshape), not all compiled features; **(c)** the platform **slide joint has NO physical carrier** — nothing in the geometry prevents the platform co-rotating with the screw (anti-rotation is *declared-only*); **(b)** **NO fit schedule** — bore/boss/column clearances not derived from mates. |
| **T4** t0 gate | 🔶 partial | `t0_gate.screw_lift_gate` runs (P1×P2, P1×P3 intended; swept over the lift) — but intended pairs are hand-listed, **not tied to a fit-schedule row set**. |
| **T5** physics (visual = compiled meshes) | 🔶 partial | P-LIFT V-A **5/5** exists (reaches 40.00 / formula 0.000% / backdrive 0.080 / discrimination 9.20 mm), BUT visual bodies are **MJCF primitives**, not `_to_trimesh(compiled part)`; **no physics-identical assert** vs the mesh rig. |
| **T5v** reviewer visualization pack | 🔶 partial | have: `ir_screw_lift.svg`, `screw_lift_assembly.png` portrait, `t2_screw_lift.mp4`. **Missing: section views** (screw-in-bore, guide-column, coupling bores) from compiled solids w/ clearance annotated; **transparency/cutaway** video; **exploded view**. |
| **T6** reproduction + fits re-measured | 🔶 partial | `reproduce_screw_lift.py` reproduces the composed chain; **fit schedule RE-MEASURE (COMPILE_DRIFT on fits) missing** (no schedule yet). |
| **T7** REVIEW + decisions + STATUS | 🔶 partial | `m22_composition/REVIEW.md` Task A exists; needs the §14 pack + fit schedule folded in. |

## B · latched_drawer (m22 Task B + m23_latch_physics)

| stage | status | evidence / gap (one line) |
|---|---|---|
| **T1** golden IR + `ir_<task>.{mmd,svg}` | ✅ done | `tasks/latched_drawer.json` validates CLEAN; `m22_composition/out/ir_latched_drawer.{mmd,svg}` rendered. |
| **T2** validate | ✅ done | validates CLEAN (note: `snap_hook_cantilever.resolve_params` is a `_not_yet` stub, so the snap does **not** compile — see T3). |
| **T3** design closure | ❌ **missing** | The **cabinet is MJCF world-geometry** in `m23/p_latch_va.py` (floor+walls+ramped receiver), **not a compiled piece**; the drawer has **no carved cantilever/barb** — `snap_hook_cantilever` carve is a **stub** and a naive carve **HANGS** (recorded D-M22-2c); `slide_base` is a **flat plate** with no receiver ledge; **NO fit schedule**; the latch constraint has **no compiled physical carrier**. |
| **T4** t0 gate | 🔶 partial | `t0_gate.latched_drawer_gate` runs **only with the snap REMOVED** (P1×P2 over the stroke); the **latch/receiver interface is not in the compiled t0**. |
| **T5** physics (visual = compiled meshes) | 🔶 partial | P-SLIDE **5/5** + P-LATCH **5/5** (engage 0.399 / hold 0.449 / release 59.73) exist, BUT visual bodies are **MJCF primitives**; the latch is a **reshaped MJCF body**, not a compiled barb. |
| **T5v** reviewer visualization pack | 🔶 partial | have: `ir_latched_drawer.svg`, `t2_latch.mp4` cutaway, `t2_latch_zoom.mp4`, `engaged_closeup.png`. **Missing: section view** through the barb-under-ledge interface from **compiled solids** w/ clearance annotated; **exploded view**; a **compiled** assembly portrait. |
| **T6** reproduction + fits re-measured | 🔶 partial | `reproduce_latch.py` reproduces the sourced Bayer chain; **fit schedule RE-MEASURE missing**. |
| **T7** REVIEW + decisions + STATUS | 🔶 partial | `m22 REVIEW` (Task B) + `m23 REVIEW` exist; the §14 pass **consolidates** them (cabinet+drawer as designed pieces, fit schedule, section/exploded). |

## Redesign scope (what this milestone executes, in stage order)

**screw_lift** — T3: a **base frame** piece (bearing boss carrying the screw hinge) + **guide columns**
(the platform slide's physical carrier — anti-rotation posts the platform rides) + **platform** with an
imposed **nut boss/bore** and **column bores** + a legible **crank** piece (arm+handle) + a **coupling
hub** with bores to *both* the crank and screw shafts. **FIT SCHEDULE** (screw-in-nut, column-in-bore,
hub-on-crank, hub-on-screw). Then T4 (t0 on the fit rows) → T5 (physics from compiled meshes,
physics-identical assert; criteria must stay within tolerance of 40.00 / 0.000% / 0.080 / 9.20) → T5v
(section + exploded + transparency) → T6 → T7.

**latched_drawer** — T3: the **cabinet** as a DESIGNED compiled piece (reuse/extend `cabinet_shell`
with a **receiver ledge**) + a **drawer tray** with a **carved cantilever + ramped barb** (host-template
geometry — the snap FORCES stay Bayer-sourced per M3/D3, closing D-M22-2c at the template level where
host geometry belongs, since the card carve is a stub). **FIT SCHEDULE** (rail-in-groove, barb-under-
ledge engagement, drawer-in-opening). Then T4 (t0 including the latch interface) → T5 (latch sourced
W_out = 32.81 N unchanged; criteria within tolerance of 0.399 / 0.449 / 59.73) → T5v → T6 → T7.

**STOP condition (both, at T5):** criteria are expected unchanged (the physics is the same declared
joints / sourced parameters; only the *visual bodies* become compiled meshes). If any criterion shifts
beyond tolerance, STOP and report — a shift means the mesh geometry changed the physics, which it must
not.
