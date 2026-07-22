# M24 · design_closure — REVIEW

**Outcome: the two m22/m23 composition tasks are re-delivered to spec §14 (the Task D-track) — DESIGN
COMPLETENESS (parts derive dimensions from their mates, every joint has a physical carrier, fits are
scheduled + verified) and FULL REVIEWER VISUALIZATION (IR diagram, section views from the compiled
solids, transparency/cutaway + zoom, exploded).** The physics is unchanged — the declared joints and
sourced parameters are the same; only the *geometry* becomes design-complete and the *visuals* become
compiled meshes, proven physics-identical. §14 exists so the m22/m23 review's failure chain (missing
assembly physics → missing t0 → missing latch → illegible geometry → missing IR diagrams →
primitive-proxy rendering → FUNCTION WITHOUT DESIGN) cannot recur — each link is now a stage gate
(**D-M24-0**).

The starting inventory is [`DESIGN_AUDIT.md`](DESIGN_AUDIT.md) (task × T1–T7, done/partial/missing).

---

## A · screw_lift — §14 T1–T7 (AWAITING REVIEW)

**The design gap the audit named:** the jack was function-verified (m22 P-LIFT 5/5) but the platform
SLIDE joint had **no physical carrier** — nothing in the geometry stopped the platform co-rotating with
the screw — and the crank/frame were MJCF visual stand-ins, so it "does not read as a hand-crank jack."

### T3 — design closure (in the host templates, LIVE code; m19 byte-identical, gated)
- **`screw_base(frame=True)`** grows the two declared joints' carriers: a central bearing **boss** (the
  screw hinge) + two **guide columns** at ±15 mm spanning the lift travel — the platform slide's
  anti-rotation posts. New anchors `guide_col_L/R`.
- **`nut_carriage`** (platform) widened to 44 mm so both column bores sit inside; a **nut boss** (thread
  engagement length) + two **column bores** ⌀ = col_d + 2·col_clear — the fit DERIVES from the column.
- **`shaft_carrier_out(crank=True)`** — a legible **hand crank**: radial arm + grip knob.
- Golden stays 3 one-solid pieces, validator-CLEAN.

### T3b/T4/T6 — fit schedule + re-measure · [`out/screw_lift_fits.txt`](out/screw_lift_fits.txt)

| interface | inner ⌀ | outer ⌀ | clearance | source |
|---|---|---|---|---|
| screw major ⌀ in nut bore | 8.00 | 9.00 | 0.50 | lead_screw d_major=8; nut gap=1.0 (m19) |
| guide column ⌀ in platform bore | 6.00 | 6.70 | 0.35 | col_d=6; bore=col_d+2·col_clear, col_clear=0.35 A-PETG-1 |
| coupling bore on crank shaft ⌀ | 8.00 | 8.60 | 0.30 | coupling clearance 0.30 (D-M8-4) |
| coupling grip on screw shaft ⌀ | 8.00 | 8.00 | 0.00 | coupling FUSED to input (rigid grip, m20) |

**Re-measured from the compiled solids (TRUE mm):** P1×P2 = **−0.350 mm** (= the 0.35 column fit
exactly) · P1×P3 = 0.000 (fused grip) · P2×P3 = −22.5 mm (clear) → **max intended-fit COMPILE_DRIFT
0.000 mm**. The units caveat on the reused m22 `t0_gate` (metres, not mm) is recorded as **D-M24-1** and
fixed here (mm-correct).

### T5 — physics from the compiled meshes · [`out/t2_screw_lift_mesh_verdict.json`](out/t2_screw_lift_mesh_verdict.json)

The m22 physics is kept EXACTLY (joints, equalities, sourced thread friction, actuator; per-body
mass+inertia **pinned via explicit `<inertial>`** so the physics is independent of the geoms). The
visual geoms become the compiled per-body meshes (world = base+boss+columns; screw = rod; nut =
platform; crank = P3), collision off, density 0.

**PHYSICS-IDENTICAL ASSERT** — a BARE declared-joint rig (no visual geoms) vs the mesh rig:

| criterion | bare | mesh | recorded m22 |
|---|---|---|---|
| platform reaches height | 40.0 | 40.0 | 40.00 |
| end-to-end formula resid | 0.000 % | 0.000 % | 0.000 % |
| back-drive (hold) | 0.08 mm | 0.08 mm | 0.080 mm |
| discrimination — coupling broken | 0.00 mm rise | 0.00 mm | 0.00 |
| discrimination — friction weak | sinks 9.20 mm | 9.20 mm | 9.20 |

**Criteria BYTE-IDENTICAL bare vs mesh, and every number matches the recorded m22 verdict — the T5 STOP
condition (no criterion may shift) HOLDS.** 5/5 seeds.

### T5v — reviewer visualization pack
![section](out/section_screw_lift.png)
- [`out/section_screw_lift.png`](out/section_screw_lift.png) — YZ section from the compiled solids: the
  screw-in-bore (0.50) and guide-column-in-bore (0.35) fits, clearance annotated on the geometry.
- [`out/exploded_screw_lift.png`](out/exploded_screw_lift.png) — the four compiled pieces along +Z.
- ![transparency](out/transparency_screw_lift.png) [`out/transparency_screw_lift.png`](out/transparency_screw_lift.png)
  — translucent-frame cutaway; it **reads as a hand-crank screw jack with guide columns**.
- [`out/portrait_screw_lift.png`](out/portrait_screw_lift.png) · [`out/zoom_screw_lift.png`](out/zoom_screw_lift.png)
  · [`out/t2_screw_lift_mesh.mp4`](out/t2_screw_lift_mesh.mp4) (real geometry moving) ·
  [`out/ir_screw_lift.svg`](../m22_composition/out/ir_screw_lift.svg) (T1 IR diagram).

### T7 — bookkeeping
- **D-M24-2 CONFIRMED (§14 T1–T6)** — screw_lift design-complete, fits drift 0.000, physics byte-unchanged.
- **D-M24-1 CONFIRMED (finding)** — the t0_gate metres/mm units bug; no false PASS in m22/m23; mm-correct here.
- All m24 work free/local (no LLM/API). **Still HELD:** the lite admission gate + the m15 Pro/flash
  frontier column. **AWAITING REVIEW.**

---

## B · latched_drawer (+m23) — §14 T1–T7

_(in progress — see the redesign commits)_
