# M22 · composition — REVIEW

**Outcome (Task A verified; Task B in progress): the pipeline composes VERIFIED ELEMENTS into a working
assembly, golden-first, and verifies the COMBINATION as physics.** m22 is a TASK-track milestone (no new
element; the m8/m13 anchor-task precedent, not the §13 D-track). Phase 1 (golden verification) only — the
LLM design-choice evaluation (Phase 2) stays HELD with the lite/frontier column until user release.

This is the milestone where the framework's per-element verification pays off: two independently-verified
declared pairs (m20 coupling, m19 lead_screw) chain into a hand-crank screw jack, and the **assembly-level
non-tautology** — the *composed* formula chain vs the measured end-to-end motion — passes at 0.000%.

---

## Task A — screw_lift (motion-transmission composition)

**Command:** *"A hand-crank jack that raises a small platform and holds it when released. Plastic, 3D
printing."* Chain: crank → **coupling** (1:1) → **lead_screw** (self-locking) → nut platform.

![composed jack](out/t2_screw_lift.png)

### The two ontology questions (the point of the task)

**q1 — element chaining: how does the IR state that `coupling.shaft_out` and the lead_screw's screw axis
are the SAME physical axis?** **Answer: a SHARED PIECE bound to the SAME anchor.** The screw shaft is ONE
piece (P1); both `E1.shaft_out` and `E2.screw_axis` bind to `P1.screw_axis`. They are the same physical
axis **by construction** — there is nothing to check and nothing to violate (the strongest form). This
reuses only the existing binding mechanism and is precedented: `anchor_hard`'s `E3.mesh_line` and
`E4.ratchet_line` both bind `P4.rack_line`. An `AssemblyRule` (coaxial) would be needed only for elements
on *different* pieces that must be made collinear — and the current `alignment` kind is *parallel+level*,
**not coaxial**, so that path is a gap → **DRAFT D-M22-1a** (extend alignment to a coaxial relation), not
needed here.

**q2 — protocol composition: per-element or end-to-end?** **Answer: BOTH.** The per-element protocols
(P-COUPLING for E1, P-SCREW for E2) are inherited — those pairs are already verified (m20, m19). The NEW
verification is one **END-TO-END P-LIFT**: crank *N* rev → platform rises *H = N × coupling(1:1) × lead*;
release → holds. The **composed formula chain vs the measured rise is the assembly-level non-tautology**
(the anchor_lift P-HOLD/P-FULL precedent). Declaring the chain and measuring the chain would be
tautological *if* either ratio were trivially 1 — but the lead (2 mm/rev) is real card arithmetic, and the
end-to-end path exercises **both** ratios and the mm→m unit path through two coupled equalities.

### C2 — the compiled-assembly t0 gate (§13 S5, applied to a task)

The compiled screw_lift (P1 base+screw, P2 platform, P3 crank), swept through the 40 mm lift, is CLEAN
per D22: `P1×P2` (nut on the threaded screw) and `P1×P3` (crank at the coupling grip) are intended
clearance pairs; `P2×P3` clear. No unintended penetration over the sweep. (`out/screw_lift_t0.txt`.)

### C3 — P-LIFT V-A · [`out/t2_screw_lift_verdict.json`](out/t2_screw_lift_verdict.json)

| criterion | result | value | gate |
|---|---|---|---|
| platform reaches height | ✅ | 40.0 mm | = stroke |
| **end-to-end composed formula** | ✅ | **0.000%** | ≤ 0.1% |
| **holds released load** (sourced) | ✅ | **0.081 mm** back-drive | ≤ 1 mm |
| converged / all parts retained | ✅ | — | — |
| **V-A overall** | **5/5 PASS** | G-CONV ok | ≥ 4/5 |

**The rig CHAINS the two verified rigs:** the m20 coupling (a 1:1 equality between the crank and screw
hinges) feeds the m19 lead_screw (a lead/2π equality screw→nut, with the SOURCED thread friction on the
screw hinge). Drive the **crank**; the platform rise (top plot, blue) overlays the **composed formula**
(crank·rev × 1:1 × lead, red dashed) to **0.000%**. Release the crank under the load and the sourced
friction `T_f = µ·W·d_mean/2 = 0.00515 N·m ≥ back-drive 0.00156 N·m` holds it to 0.081 mm (bottom plot).

**Both discrimination probes fire at the ASSEMBLY level** (`discrimination_probes.discriminates = true`):
- **coupling BROKEN** (the 1:1 equality inactive): the crank spins 20 rev but the platform rises **0.00 mm**
  — the chain is doing the work, not a solver artifact;
- **friction WEAK** (0.5·T_backdrive): the released platform **SINKS 9.57 mm** (vs 0.081 mm held) — the
  hold is the sourced friction, not the rigid coupling. (The extra crank inertia slows the sink vs m19's
  18 mm, but it is still 118× the held value.)

Video ([`out/t2_screw_lift.mp4`](out/t2_screw_lift.mp4), 1133 frames, 4× slow-mo) with a marker per moving
body (red crank / gold screw / blue platform), the HUD crank-rev + rise counters, and the full drive →
release → hold window.

### V-B disposition — does the COMBINATION create a new gap?

**No.** The two declared pairs are coupled by rigid equalities; the coupling is V-B-verified (m20, no
curved contact), and the only deferred piece is the lead_screw thread contact (R2b/m17), **inherited
unchanged**. The composition adds no new emergent contact surface, and the assembly-level non-tautology
(the end-to-end rise) IS verified. Stated honestly, not assumed.

### C4 — numeric reproduction · [`out/reproduce_screw_lift.txt`](out/reproduce_screw_lift.txt)

```
[1] chain: coupling 1:1, lead=starts×pitch=2.0, self-locks (tanλ=0.091≤µ=0.30)
[2] composed: H = 20 × 1 × 2 = 40.00 mm  vs measured 40.00 mm = 0.0000%
[3] sourced hold: T_f=0.00515 ≥ T_bd=0.00156 Nm (3.30×); back-drive 0.081 mm
[4] discrimination: coupling broken → 0.00 mm rise ; friction weak → 9.57 mm sink
[5] t0 gate CLEAN
========== reproduction CLEAN — every number checks out ==========
```

## Morphological twins — the Phase-2 benchmark seed

"Lift + hold" now has **TWO physics-verified solutions**: **rack_pinion + pawl_detent** (anchor_lift,
m13) and **lead_screw + coupling** (screw_lift, m22). This is the Zwicky morphological matrix realized —
`kg.candidates()` already offers both for a hold-under-load intent. That is exactly the **design-choice**
the Phase-2 LLM evaluation will test (which mechanism does the model pick, and can it justify it), and it
is now seeded with two verified ground-truth answers. Recorded as **D-M22-1**.

## Stage checklist (Task A)

| stage | done | evidence |
|---|---|---|
| C1 golden IR (q1/q2 answered) | ✅ | `tasks/screw_lift.json` CLEAN, 3 parts (commit e1d1ca6) |
| C2 compiled t0 gate | ✅ | `out/screw_lift_t0.txt` CLEAN over the lift sweep (commit 90fb855) |
| C3 P-LIFT V-A | ✅ | 5/5; end-to-end 0.000%; hold 0.081 mm; both discriminations (commit 9804cf2) |
| C4 reproduction + REVIEW + decisions | ✅ | `reproduce_screw_lift.txt` CLEAN; D-M22-1 (+DRAFT D-M22-1a) |

**Still HELD:** the lite admission gate + the m15 Pro/flash frontier column (Phase-2 LLM eval). All m22
work is free/local (golden construction, composed-formula arithmetic, MuJoCo joint physics; no LLM/API).
