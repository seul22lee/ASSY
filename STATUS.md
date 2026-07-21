# MechSynth — STATUS

Single-glance state of the research artifact: what each milestone produced, and what the system can
do right now. Milestones close with `mN_<name>/REVIEW.md` as the G-H entry point (D-ONT-7); this file
is the index over them. **No milestone folders are ever moved or renamed** — history stays put.

## Milestones

| # | Folder | Scope | Outcome |
|---|---|---|---|
| M0 | [`m0/`](m0/) | The MuJoCo reference rig: STEP→MJCF, the **frozen contact preset (R5)**, G-CONV gate, P-HINGE V-A/V-B on a hand-built hinge box. | ✅ The rig + preset that everything downstream reuses. |
| M1 | [`m1_gear/`](m1_gear/) | Gear-pair risk-retirement (R2, the tooth-profile analog of M0's bore). | ✅ **R2a RETIRED** (involute is conjugate, ratio −0.5%); **R2b OPEN/FROZEN** — contact-*formulation* limit, stable only at dt/25 (D-M1-2/-5/-7). |
| M2 | [`m2_ontology/`](m2_ontology/) | Pydantic ontology / IR (`DesignPlan`), validators V-01…, the IR graph. | ✅ APPROVED — the discrete decision surface the LLM is constrained to. |
| M3 | [`m3_cards/`](m3_cards/) | Element cards: `snap_hook_cantilever` formulas (Bayer). | ✅ APPROVED — knowledge grounded in the handbook, formulas deterministic. |
| M4 | [`m4_templates/`](m4_templates/) | Host templates + `carve()` (snap-box compile). | ✅ APPROVED — the same carve attaches via anchors to different hosts (D-GEN-1). |
| M5 | [`m5_resolve_t0/`](m5_resolve_t0/) | Stage-⑤ resolution + Tier0 three-way + Tier1 re-measure. | ✅ APPROVED — resolved params carry citations; COMPILE_DRIFT guard closes the blind spot. |
| M6 | [`m6_ms_closeout/`](m6_ms_closeout/) | The **snap-fit-only track (M-S)** end-to-end: IR → ⑤ → ⑥ → t0 → t1. | ✅ Close-out of the single-element snap pipeline. |
| M7 | [`m7_rack_pinion/`](m7_rack_pinion/) | `rack_pinion` card attempt under R2b. | ⚠️→✅ **Superseded by M11.** The M7 attempt correctly found R2b is a contact-formulation limit; M11 (D-D-2) builds the card anyway with **V-A verification** and the V-B contact gap named-deferred — the standing-flag design the ontology always intended. |
| M8 | [`m8_pin_hinge_easy/`](m8_pin_hinge_easy/) | **B-track**: `pin_hinge` + `stop_flange` cards, the **multi-element Easy anchor** (box + lid + hardware pin + snap latch) compiled and verified t0→t1→t2, and the **D20 no-stop/stop pair**. | ✅ **Benchmark PASS** (t0 ARs · t1 0 mm drift · V-A 5/5 · V-B 5/5). D20 demo golden `anchor_easy_nostop` = **EXPECTED_FAIL** (V-B 1/5, folds over). An earlier V-B PASS was **retracted** (D-M8-4) — it rested on an invented stop; the rule is now mechanized as a build error. |

| M9 | [`m9_llm_stages/`](m9_llm_stages/) | **E-track 1 + frontier follow-up**: LLM stages ①–④, the KG narrowing, the grader, and the command→IR→physics run on **two models** (local qwen3-coder + Gemini). | ✅ **The loop closes, and scales.** Local qwen: ①②③④ PASS → V-B **0/5 folds over** (omits the stop). Frontier Gemini: declares the stop, **V-B 4/5 PASS** — machine-made, physics-verified. **Bindings-blindness (0.18) is a small-model artefact** — Gemini 6/6 (D-E-8). D-E-2/-5/-7 CONFIRMED & FIXED; generated IRs now validate_all CLEAN. |
| M10 | [`m10_slide_rail/`](m10_slide_rail/) | **D-track 1**: the `slide_rail` card (§3.5, T-rail retaining slide, all-boxes) + the P-SLIDE physics — Hard-anchor prerequisite #1. | ✅ Card built (§3.5 rule chain, carve, collision_hint, verification); fixture CLEAN. **P-SLIDE V-A 5/5 PASS** (required). **V-B 5/5 PASS** (contact-only; the geometry produces + retains the DoF). A G-H-caught disjoint-carriage geometry bug that had tripped V-B is fixed; P-SLIDE gained an all_parts_retained coverage criterion. Alignment ontology gap flagged **D-E-10 DRAFT** (since CONFIRMED Option A, implemented). |
| M11 | [`m11_rack_pinion/`](m11_rack_pinion/) | **D-track 2**: the `rack_pinion` card (§3.6 amended, involute pinion + straight rack) + P-GEAR V-A — Hard-anchor prerequisite #2; retires M7's NOT-built. | ✅ Card built (§3.6 formulas self-derived + pinned 6/6; module bounds {5,6} with the WHY = contact-sim stability in selection_notes; carve reuses M1's involute; collision_hint = L3 flank-wedge decomposition). Fixture CLEAN. **P-GEAR V-A 5/5 PASS** (declared kinematic pair; rack reaches its 120 mm design stroke, matches the §3.6 formula to 0.01%). **V-B named-deferred** (R2b/D-M1-7) — carried in the verdict's `v_b_gap` + `shape_assert` (no V-B pass claimed). |
| M12 | [`m12_templates/`](m12_templates/) | **D-track 3**: the four **Hard-anchor host templates** (`cabinet_shell`, `drawer_tray`, `knob_shaft`, `rack_bar`) + labelled anchor overlays. Templates only — the assembly is m13. | ✅ All four built, valid, one-solid (the knob's shaft+grip fuse). **Every m13 anchor declared + labelled**: matched level rail/carriage L/R pairs (the alignment subjects), the pinion `shaft_seat`, the underside `rack_mount`. Collision hints self-sourced (D-M8-4). Reframed at m13 to +X-pull/floor-rails/vertical-knob (kinematic closure — see M13); `test_hard_templates.py` 7/7. |
| M13 | [`m13_hard_anchor/`](m13_hard_anchor/) | **THE HARD ANCHOR (§8.2, retargeted D-M13-2)**: a **crank-operated LIFT PLATFORM** (2× `slide_rail` + `rack_pinion`, travel VERTICAL, gravity along it — where the gear is *necessary*, not over-engineered). Drawer kept as the labeled alternate. | ✅ **Assembled, validator-CLEAN, V-A-verified under gravity.** ⑤ §8.2 chain resolves + **alignment AR fires PASS (0.00°/0.00 mm)** — both carry over from the drawer verbatim (geometry rotated −90° about Y; carves reused). **P-SLIDE V-A 5/5** (raises the 0.5 kg load 128 mm against gravity) + **P-GEAR V-A 5/5** (crank→lift on the π·m·z line, 0.01% — ratio holds with gravity along travel). **P-HOLD V-A 0/5 FAIL = the finding:** a plain rack-pinion is not self-locking (μ·W·rp ≪ W·rp) — the released platform back-drives 62 mm, so **a lift REQUIRES a holding brake** (discovered from physics, not tuned to pass). static/hold expressible today (static+fixed+load+criterion); **D-M13-3 DRAFT** asks if it should be first-class. **BRAKE ADDED (D-M13-4):** the `pawl_detent` card — snap_hook's cousin (asymmetric Bayer angles; the m3 self-lock cliff used as the FEATURE) — **flips P-HOLD 0/5 → 5/5** (back-drive 3.4 mm, caught in one detent). The golden now PASSES ITS OWN PROTOCOLS (raises, transmits under gravity, holds). **P-FULL 5/5** (raise→hold→lower cycle). **P-SLIDE V-B 5/5 (D-M13-6):** the clearance-fit T-groove was gravity-seated horizontally; a card-level vertical-retention rule (tight retention-stop gap = print_clearance/4 = 0.075 mm, sourced) makes the contact-only slide retain through raise/hold/lower under gravity-along-travel (off-axis 0.67°) — preset untouched, no criteria weakened. **Hard anchor CLOSED** (V-A + P-FULL + P-SLIDE V-B; only P-GEAR V-B R2b-deferred). |
| M14 | [`m14_task_ladder/`](m14_task_ladder/) | **Benchmark construction**: the 16-task ladder over the 3 verified bases (dimensional / constraint / spec-tightening / infeasible axes) + certification. | ✅ **All 16 CERTIFIED.** Feasible tasks validator-CLEAN + ⑤ resolve + ⑥ compile + physics (base verdict reused or a measured number); 4 infeasibles each refused at a DISTINCT layer/code (⑤ INFEASIBLE force-window · ④ KG no-realizer · V-04 stroke · V-02/V-03 out-of-vocab). Builders parameterized (no new cards/templates); scorer gains forbidden-element + spec-number axes (5/5). Ready for the baseline LLM eval (spec M6). |
| M17 | [`m17_gear_vb/`](m17_gear_vb/) | **R2b risk-retirement probe**: does an SDF contact formulation retire the frozen-preset gear-mesh blow-up? | ⚠️ **NO — SDF is necessary-not-sufficient.** Reproduces R2b (wedge **2.09e16 N DIVERGED** vs **0.605 N clean roll** at dt/25). **F1:** the mujoco pip wheel ships only analytic SDF plugins — **no `mujoco.sdf.sdflib`**, so a D21-legal own-mesh SDF needs a MuJoCo **source build** (updates D-M1-8). **F2/F3:** the analytic SDF gear (zero facets, **ORACLE only — D21-forbidden as a collider**) STILL diverges at dt=5e-4 under **rigid AND soft** contact; only dt/25 survives. R2b = two coupled limits — facet make/break (SDF removes) **+** stiff-contact small-dt integration (SDF does **not**). **No preset_v2, no V-B pass claimed.** D-M17-1/-2/-3(DRAFT). |

| M18 | [`m18_element_expansion/`](m18_element_expansion/) | **Element taxonomy + Tier-1 expansion** (schema/ontology only, NO new physics; grounded in **Pahl & Beitz**, cited per axis). The taxonomy elements grow along + 8 Tier-1 cards to sit on it. | ✅ **7-axis taxonomy** (axes 1–5 real fields: motion nature, axis_relationship, connection_principle, self_locking, **emergent_check** (a struct carrying deferred+why+risk, D-M18-4); axis 6 compliance RESERVED; axis 7 kinematic_dof a note). **Third card category — ConnectionCard** (§8.1: fastens parts, realizes nothing; `connection_principle` form/force/material — a PROPERTY, orthogonal to the OBJECT and to hardware provision). **8 Tier-1 cards**: lead_screw/coupling/universal_joint (Mech) · journal_bearing/bushing (Passive) · dowel_pin/screw_boss/press_fit (Connection), each with cited P&B/Shigley/Bayer formulas + carve (one solid) + V-A/static verification (**no curved-contact V-B — next milestone**). **KG = morphological matrix** (§3.2.3 Zwicky): self_lock→lead_screw, intersecting→universal_joint, form→dowel_pin. **V-08 extended** (a connection may not be realized_by) + **V-17** (reject compliance=compliant with a P-SPRING message). **self_locking promoted first-class → resolves D-M13-3.** 15 test files green (79→94 asserts); goldens untouched (defaults). D-M18-1/-2/-3. |
| M19 | [`m19_lead_screw/`](m19_lead_screw/) | **D-track 3**: the `lead_screw` element (§8-2 power screw) completed through the FULL D-track — card → templates → golden → **P-SCREW V-A physics** → numeric reproduction — exactly as m10 (D-D-1) and m11 (D-D-2). The first element to earn axis-4 `self_locking` by physics. | ✅ **Card built + P-SCREW V-A 5/5 PASS.** §8-2 rule chain (lead=starts·pitch, d_mean, λ, tan λ ≤ µ self-lock) self-derived + pinned (`test_lead_screw.py` 6/6, with the coarse back-driving counter-example). Two templates (`screw_base`, `nut_carriage`); golden compiles CLEAN. **V-A (declared kinematic pair, polycoef=lead/2π in metres):** (a) nut travel 40.00 mm matches the INDEPENDENT §8-2 formula to **0.000%** (non-tautology gate); (b) **self-lock HOLD is SOURCED** — released load held by `T_friction=µ·W·d_mean/2=0.00515 Nm ≥ back-drive 0.00156 Nm` (µ from the R5 preset, d_mean from the card, **not invented** — the D-D-1 lesson) to **0.079 mm** back-drive, and a **non-tautology probe** confirms a sub-back-drive friction slips **18.4 mm** (233×) so the hold is friction winning, not a solver artifact. **V-B (emergent curved thread-flank contact, R2b/m17) NAMED-DEFERRED** — verdict `shape_assert` (V-A present ∧ V-B named ∧ no V-B pass claimed) all true; card `emergent_check` risk narrowed (criterion+torque now physics-backed, flank effects remain). Physics-of-verification lessons (rigid coupling vs equality-spring stretch, tiny damping so Coulomb friction governs not viscous) all documented + forced by measured failures. **The V-A rig runs a dt=1e-4 SOLVER clock (D-M19-2), distinct from the frozen R5 CONTACT preset (dt=5e-4, untouched)** — joint frictionloss creeps at 5e-4 for small inertias; V-A declares no contacts so R5 never applied, and the REQUIRED discrimination probe running at the *same* dt (holds 0.079 / slips 18.4 mm) proves the clock is not manufacturing the hold — it caught two masked-hold tautologies (soft-equality compliance; viscous damping) before they shipped. This is the standing recipe for future declared-joint D-tracks. Numeric reproduction (`reproduce.py`) CLEAN incl. t1 COMPILE_DRIFT 0.0000 mm. All work free/local (no LLM/API). **DRAFT D-M19-3** parks a generic settle/retention-contact protocol (gravity-hold within R2b limits — cf. m8/m10) that could narrow the V-B gap for all deferred curved-contact elements, deliberately NOT built here. D-M19-0 (audit retag) + D-M19-1 + D-M19-2. |

## Current system state

**The full loop is demonstrated end-to-end (M9):** a one-sentence command → LLM stages ①–④ →
deterministic ⑤ resolve → ⑥ compile → t2 physics, with no human in the loop. The LLM makes only
discrete ontology choices (verb / phase+motion / template / card+port+anchor); every dimension is
code's. Its IR compiled and ran — and V-B caught the design flaw it contained.

**Two tracks are demonstrated end-to-end:**
- **M-S (snap-fit, single element)** — golden IR → ⑤ resolve → ⑥ compile → t0 three-way → t1
  re-measure. Closed at M6.
- **M-M (mechanism, multi-element)** — the **Easy anchor** at M8: a `pin_hinge` and a
  `snap_hook_cantilever` on shared host pieces, an **element-provided hardware pin** (D-ONT-11), and
  two **first-class AssemblyRules** (D-ONT-12) evaluated on the compiled geometry, verified through
  physics in both V-A (declared joint) and V-B (DoF from geometry alone).

**Built and green (suite 81/81):**
- **Ontology/IR** — `DesignPlan` with pieces (provenance functional/hardware), elements, features,
  behaviours, protocols, **AssemblyRules**; validators V-01…V-16.
- **Cards** — `snap_hook_cantilever` (Bayer), `pin_hinge` (M0 hinge), `stop_flange` (rotation
  ceiling), `slide_rail` (§3.5 T-rail retaining slide, all-boxes), `rack_pinion` (§3.6 involute
  pinion + straight rack — **V-A built, V-B named-deferred, R2b/D-M1-7**), `pawl_detent` (D-M13-4 ratchet brake — Bayer
  formulas reused asymmetrically, self-lock cliff as the feature; flips the lift's P-HOLD 0/5→5/5). The card API
  carries `provides_pieces` (hardware), `interaction_rules` (AssemblyRules), and `verification()`
  (P-HINGE/PR-LATCH/PR-SWEEP/P-SLIDE/**P-GEAR** — protocols are card knowledge, D5).
- **Templates** — `box_shell`, `lid_panel`, `flat_panel_mount`, `retained_board`, `slide_base`/
  `slide_carriage`/`slide_base_dual`, `pinion_carrier`/`rack_carrier`, and the **Hard-anchor set**
  `cabinet_shell`/`drawer_tray`/`knob_shaft`/`rack_bar` (M12); template collision hints for the
  seating load path (D14 inset), each self-sourced (D-M8-4).
- **Pipeline** — stages ①–④ (LLM: `s1_intent`/`s2_behavior`/`s3_decompose`/`s4_interface` +
  `llm_client` with structured output, validator-repair retries ≤3, and a verbatim `stage_log`
  audit); stage-⑤ resolve; stage-⑥ `compile_assembly` (motion → fasteners → passive features).
- **Knowledge** — `ontology/functional_basis.py` (NIST TN 1447 subset), card `selection_notes` +
  `citations`, `knowledge/kg.py` (§3.7 `candidates()` narrowing; gate G3.2 tested).
- **Verify** — t0 (`t0_static` three-way + `assembly_rules`), t1 (`t1_remeasure`, COMPILE_DRIFT),
  t2 (`t2_physics`: G-CONV + P-HINGE V-A/V-B, the frozen preset R5, guard trio on verdicts,
  collision-provenance gate).

**Known limitations / open items:**
- **R2b** (gear contact-only meshing) is FROZEN — a MuJoCo convex-facet contact-formulation limit.
  The `rack_pinion` card IS built (M11/D-D-2) and verified **V-A** (declared kinematic pair); only
  its **V-B** (emergent tooth contact) is deferred to a `preset_v2`-time decision, and that deferral
  is carried in every rack_pinion verdict (`v_b_gap` + `shape_assert`). Mitigation queue in
  `m1_gear/out/r2b_note.md`: (1) larger module — exhausted; (2) versioned preset — no candidate;
  (3) **[deferred] PhysX 5 SDF backend** (D-M1-8).
- **Collision provenance is enforced (D-M8-4)** — every collision geom must trace to a declared IR
  entity (card / template / D23 fixture); an unsourced prim is a BUILD ERROR. The physics driver
  cannot author geometry, only route what cards and templates emit.
- **A stop is a DISCOVERED requirement, not an option (D-M8-5).** Honest V-B proved "opens ≥90° AND
  returns closed" is unsatisfiable for an over-centre lid with no stop, so the benchmark golden
  carries one. `anchor_easy_nostop` is kept as the D20 demo/EXPECTED_FAIL: V-A passes both designs
  5/5, only V-B separates them.
- **Standing rule (D-M8-4):** a physics collision prim may only proxy REAL carved geometry the IR
  declares. A prim with no solid and no IR entity behind it voids any verdict resting on it.
- **Two backends wired (D-E-6/-8)** — local Ollama (qwen3-coder-30B) and Gemini
  (`gemini-3.1-pro-preview`), selected by env var; keys in gitignored `.env`, `_redact`ed from logs.
  Frontier passes physics; local folds over. Bindings-blindness is a small-model artefact (D-E-8).
  **Gemini is the DEFAULT backend; qwen is the cheap regression backend.** Gemini's ②-flakiness
  (1/3 runs failed G2) is recorded, deferred to pre-benchmark hardening.
- **`verification()` now implemented on the three anchor cards (D-E-5 FIXED)** — ④ attaches
  protocols FROM the cards (D5), so generated IRs are `validate_all` CLEAN.
- **§4-③'s six-template vocabulary is 2/6 implemented (D-E-3 DRAFT)** — the Hard anchor needs all
  four missing (`drawer_tray`, `cabinet_shell`, `knob_shaft`, `rack_bar`).

## Update rule

When a milestone closes, add/refresh its row in the table above and touch the **Current system
state** bullets it changes — nothing else. Folders are append-only (never moved/renamed); this file
and `DECISIONS_LOG.md` are the two indices kept current across sessions.
