---
name: composition-task-patterns
description: How to compose verified elements into an assembly task (m22 screw_lift + latched_drawer)
metadata:
  type: project
---

Composition tasks (m22) combine already-verified elements into an assembly, golden-first (m8/m13
anchor-task precedent, NOT the §13 D-track). Reusable patterns:

**Element chaining (same physical axis):** bind BOTH elements' axis ports to the SAME anchor on a
SHARED piece → coaxial by construction, nothing to check (screw_lift: E1.shaft_out + E2.screw_axis both
→ P1.screw_axis). Precedent: anchor_hard E3/E4 both bind P4.rack_line. An AssemblyRule "coaxial" would
only be needed for elements on DIFFERENT pieces — and current `alignment` is parallel+level, not coaxial
(DRAFT D-M22-1a).

**Protocol composition:** inherit the per-element protocols (verified) AND add ONE end-to-end protocol
whose criterion is the COMPOSED formula chain vs the measured end-to-end motion — the assembly-level
non-tautology. screw_lift P-LIFT: platform rise H = N_crank_rev × coupling(1:1) × lead, measured to
0.000%. Build the rig by CHAINING the verified rigs (m20 coupling 1:1 equality → m19 lead_screw
lead/2π equality + sourced friction). Run BOTH inherited discrimination probes at assembly level
(coupling broken → no output; friction weak → sinks). Reuses [[declared-pair-self-lock-physics]] +
[[va-video-evidence-rule]].

**Snaps compose by FORMULA, not physics (M3 division, D3):** an elastic cantilever is not rigid-body
expressible, so the snap's forces (W_in insertion, W_out separation) are Bayer-formula-verified; the
engagement is rigid geometry. Verify BIDIRECTIONALLY: a pull < W_out holds, a pull > W_out opens; check
hand-releasable (α_out < atan(1/µ) self-lock angle). Call `knowledge.cards.snap_hook` functions
solve_h → P_deflect → W_mate/W_sep directly (`formula_check` is stubbed).

**Latch / breakaway physics (m23) — declared constraint + SOURCED threshold, NOT frictionloss:** a
constant applied force ALWAYS defeats joint `frictionloss` (the m19 finding — friction opposes velocity,
a constant force keeps re-accelerating; verified: 10 N pull drifts through a 30 N frictionloss). So model
a latch/detent as a RIGID declared equality (pin the joint at the engaged position, `solref="-1e8 -1e4"`)
that ACTIVATES at engagement (the click, log it) and DEACTIVATES when the applied pull reaches the SOURCED
breakaway (Bayer W_out for a snap, m19-style: formula-verified value as a rig parameter, print the chain,
label SOURCED). Then hold@0.5·W_out stays, release@1.5·W_out opens — discrimination is the two jointly.
Add joint damping (~150) so the release POP is a visible ~0.2 s motion, not a 2-frame blur (reviewer:
click + pop must both be visible). Elastic deflection stays Bayer-only (D3); compliant-beam engagement is
Tier-3 deferred. A verified assembly needs the ELEMENT the task is about run as physics — travel+stop is
not the latch (the m22→m23 reviewer lesson: an element-verdict citation is not an assembly run).

**Compositions SURFACE gaps — record them, don't patch (the point of these tasks):** m22 found that
`stop_flange` is rotation-only (imposes `_imposed_rotation_limit`) and cannot express a drawer
TRANSLATION pull-out stop (V-08 fail) — use the finite rail instead (D-M22-2b); and the snap CARVE needs
a receiver wall the flat slide_base lacks (D-M22-2c, formula-verified regardless). A verified element
does not automatically carry to a new motion axis.

**Morphological twins = the Phase-2 benchmark seed:** each intent should get ≥2 verified solutions so
the LLM design-choice eval has ground truth — "lift+hold" (rack+pawl vs screw+coupling), "retain+release"
(hinge+snap vs slide+snap). kg.candidates() already offers both. Phase 2 (LLM eval) is HELD with the
lite/frontier column until user release.
