# M26 · requirement_sizing — REVIEW

**Outcome: ⑤ DESIGNS the lead_screw from the declared load, not a default lookup — the same command at
three loads yields three different resolved screws.** This is the Phase-2 division made concrete: the LLM
CHOOSES the element (lead_screw), the pipeline SIZES it from the requirement. Precedent: the m24 snap CLIP
inverted the Bayer chain to a target W_out ([[D-M24-5]]); here the lead_screw inverts its own mechanics to
a target stress.

## What changed in the card
`lead_screw.resolve_params` now SIZES `d_major` from the IR's declared load when it is UNSPECIFIED (an
explicit `d_major` is a fixed design decision — honoured, so every existing golden is byte-unchanged):

- **d_major from shear** — the drive-torque torsional shear on the core (Shigley §8-1 raise torque
  `T=(W·d_mean/2)·(tanλ+µ)/(1−µtanλ)` + §3-12 `τ=16T/πd³`), sized so `τ ≤ τ_design/SF`. Closed form
  `d = √(16·(F/2)·W·SF/(π·τ))`, F the self-lock raise factor `2µ/(1−µ²)`. `τ_design = 4.0 MPa` — an FDM
  **design shear** for a sustained-load printed screw (bulk shear yield 0.5·σ_y = 25 MPa, knocked down by
  interlayer adhesion + creep to ~σ_y/12) — an **ASSUMPTION** (gate G-S4, parallels EPS_PERM/Es_secant).
- **pitch bounded above by self-lock** (`tan λ ≤ µ`, the existing enforcement) and **below by a declared
  drive-speed** (`min_mm_per_rev`) if present — a conflict is recorded, not patched (**D-M26-1a DRAFT**:
  the schema has no first-class drive-speed field).
- bounds enforced (`d_major ∈ [5, 20] mm`).

## THE EVIDENCE — load sweep · [`out/load_sweep.txt`](out/load_sweep.txt) · [`out/load_sweep.json`](out/load_sweep.json)

| W (kg) | T (N·mm) | d_shear | **d_major** | governed | pitch | λ (deg) | self-lock | t0 | hold (mm) | weak (mm) | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 9.5 | 2.87 | **5.00** | min bound | 2.0 | 9.04 | ✅ | CLEAN | 0.158 | 36.29 | PASS |
| 5 | 57.5 | 6.42 | **6.42** | shear | 2.0 | 6.70 | ✅ | CLEAN | 0.786 | 99.38 | PASS |
| 20 | 417.3 | 12.83 | **12.83** | shear | 2.0 | 3.08 | ✅ | CLEAN | 3.080 | 17.48 | PASS |

**Reading:** `d_major` GROWS with the load (5.0 → 6.42 → 12.83 mm) — each SIZED from W, not a default. At
1 kg the printability MIN bound governs (shear needs only 2.87 mm); above it, shear governs. T and d grow
together; λ shrinks as d grows (more self-locking). Each design COMPILES (one solid per piece, the nut
bore tracking the sized d_major) and its t0 is CLEAN, and the **V-A HOLD is re-run at its own W**.

**Self-lock is judged by DISCRIMINATION, not an absolute gate.** The sourced "hold" back-drive is the
declared-coupling elastic **COMPLIANCE** (∝ W: ~0.08 mm@0.5 kg → 3 mm@20 kg — a rig stiffness, NOT thread
slip; a stiffer equality drives it to 0). The proof of self-lock is the **weak** column: a sub-back-drive
friction SLIPS far more (36 / 99 / 17 mm) than the sourced hold at every W — so the hold IS the self-lock
(the m19/D-M19-2 companion discipline, now shown to hold across a 40× load range).

## Bookkeeping
- **D-M26-1 CONFIRMED** — requirement-driven sizing demonstrated (⑤ sizes lead_screw d_major from the
  declared load; the same command → three designs; each compiles/t0/self-locks). `τ_design` is a G-S4
  assumption. Precedent: [[D-M24-5]] (the inverse-Bayer snap CLIP).
- **D-M26-1a DRAFT** — the pitch drive-speed LOWER bound has no first-class schema field (read from
  `transmission.min_mm_per_rev`, not a declared `MotionSpec` speed); a conflict with self-lock is recorded
  but the input has nowhere clean to live. Folds into [[ir-expressiveness-assembly-design]] (D-IR-EXPR-1).
- All existing goldens byte-unchanged (explicit d_major honoured); `test_lead_screw` green.
- Free/local (no LLM/API). **Still HELD:** the lite gate + the m15 frontier column. **AWAITING REVIEW.**
