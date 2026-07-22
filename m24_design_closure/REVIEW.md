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

## B · latched_drawer (+m23) — §14 T1–T7 (AWAITING REVIEW)

**The design gap the audit named:** the cabinet was MJCF world-geometry (not a piece), the drawer had
no compiled cantilever/barb, and the flat slide_base had no receiver wall — **DRAFT D-M22-2c** parked
exactly this (the snap carve needs a mating receiver wall + growth-aligned anchors; a naive carve HANGS;
the `snap_hook_cantilever` card carve is a `_not_yet` stub).

### T3 — design closure (host templates; closes D-M22-2c at the template level)
- **`latch_cabinet`** (is_base) — a designed box shell: floor + back(−X) + two side walls(±Y) + a
  front lintel carrying a downward **RECEIVER LEDGE** the barb tucks under.
- **`latch_drawer`** — a tray (floor + back + two side walls + front panel) with a **carved CANTILEVER
  arm + up-hook ramped BARB** rooted in the front panel (one solid).
- **`latch_design_parts()`** — the four compiled sub-solids (cabinet_body, receiver, drawer_body, barb)
  for D22-grouped t0 + per-body meshes.
- Golden rebound P1→latch_cabinet (role **cabinet**) / P2→latch_drawer; `tray_w` = opening 28 − 2·1.0;
  validator-CLEAN; IR regenerated.
- **The honest split:** the snap GEOMETRY is now a compiled host-template solid (D-M22-2c closed); the
  snap FORCES stay Bayer-sourced (M3/D3) — the card carve remains a stub, recorded not faked. The
  slide_rail rail-in-groove fit stays inherited (m22 P-SLIDE 5/5).

### T3b/T4/T6 — fit schedule + re-measure · [`out/latched_drawer_fits.txt`](out/latched_drawer_fits.txt)

| interface | clearance | source |
|---|---|---|
| rail ⌀/width in carriage groove | 0.35 | slide_rail rail_w=8; groove=rail_w+2·clearance (A-PETG-1, M10) |
| barb tip under receiver ledge (engagement) | 0.30 | snap_hook interlock; approach clearance A-PETG-1 (Bayer forces, D3) |
| drawer body in cabinet opening | 1.00 | tray_w = cabinet inner opening − 2·1.0 (drawer-fits-opening) |

**Re-measured from the 4 compiled sub-solids (TRUE mm, D22-grouped, swept):** cabinet×drawer = **−1.000
mm** (= the 1.0 mm side gap exactly) · receiver×barb = **+0.608 mm** (the INTENDED interlock; 5 mm
engagement zone) · every other cross-group pair clears → **VERIFIED**.

### T5 — physics from the compiled meshes · [`out/t2_latch_mesh_verdict.json`](out/t2_latch_mesh_verdict.json)

The m23 latch physics is kept EXACTLY (the drawer slide + the rigid latch equality whose **breakaway =
SOURCED Bayer W_out = 32.807 N**; the drawer mass+inertia **pinned via `<inertial>`**). Visuals become
the compiled sub-solid meshes (cabinet body + receiver → world, translucent cutaway; drawer body + barb
→ the slide body).

| criterion | bare | mesh | recorded m23 |
|---|---|---|---|
| CLOSE engages at closed | 0.399 mm | 0.399 mm | 0.399 |
| HOLD at 0.5·W_out (16.4 N) | 0.449 mm | 0.449 mm | 0.449 |
| RELEASE at 1.5·W_out (49.2 N) → rail | 59.73 mm | 59.73 mm | 59.73 |

**Criteria BYTE-IDENTICAL bare vs mesh, and every number matches the recorded m23 verdict — the T5 STOP
condition HOLDS.** 5/5 seeds.

### T5v — reviewer visualization pack
![section](out/section_latched_drawer.png)
- [`out/section_latched_drawer.png`](out/section_latched_drawer.png) — XZ section from the compiled
  solids: the **barb-under-receiver interlock** (+0.6 mm overlap annotated).
- [`out/exploded_latched_drawer.png`](out/exploded_latched_drawer.png) — the drawer pulled +X from the cabinet.
- ![engaged](out/engaged_closeup_mesh.png) [`out/engaged_closeup_mesh.png`](out/engaged_closeup_mesh.png)
  — the blue barb tucked under the red receiver ledge (translucent cutaway).
- [`out/t2_latch_mesh.mp4`](out/t2_latch_mesh.mp4) (close→hold→release, translucent cutaway) ·
  [`out/t2_latch_mesh_zoom.mp4`](out/t2_latch_mesh_zoom.mp4) (engagement zoom) ·
  [`out/portrait_latched_drawer.png`](out/portrait_latched_drawer.png) ·
  [`out/ir_latched_drawer.svg`](../m22_composition/out/ir_latched_drawer.svg).

### T7 — bookkeeping
- **D-M24-3 CONFIRMED (§14 T1–T6)** — latched_drawer design-complete; **DRAFT D-M22-2c CLOSED** at the
  template level (snap geometry compiled; forces Bayer-sourced); physics byte-unchanged.
- All m24 work free/local (no LLM/API). **Still HELD:** the lite admission gate + the m15 Pro/flash
  frontier column. **AWAITING REVIEW.**
