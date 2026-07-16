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
| M7 | [`m7_rack_pinion/`](m7_rack_pinion/) | `rack_pinion` card attempt under R2b. | ⚠️ **Card NOT built** — R2b routing exhausted both routes; it is a formulation limit, deferred to a `preset_v2`-time decision (D-M1-4/-5/-8). |
| M8 | [`m8_pin_hinge_easy/`](m8_pin_hinge_easy/) | **B-track**: `pin_hinge` card + the **multi-element Easy anchor** (box + lid + hardware pin + snap latch), compiled and verified t0→t1→t2; `stop_flange` cardified and the **D20 no-stop/stop pair**. | ✅ t0 ARs PASS · t1 0 mm drift · V-A 5/5. **V-B: baseline 0/5 — the lid FOLDS OVER (the finding, reported not fixed); stop variant 4/5 PASS — stops BY CONTACT.** An earlier “V-B PASS” was **retracted** (D-M8-4): it rested on an invented stop. |

## Current system state

**Two tracks are demonstrated end-to-end:**
- **M-S (snap-fit, single element)** — golden IR → ⑤ resolve → ⑥ compile → t0 three-way → t1
  re-measure. Closed at M6.
- **M-M (mechanism, multi-element)** — the **Easy anchor** at M8: a `pin_hinge` and a
  `snap_hook_cantilever` on shared host pieces, an **element-provided hardware pin** (D-ONT-11), and
  two **first-class AssemblyRules** (D-ONT-12) evaluated on the compiled geometry, verified through
  physics in both V-A (declared joint) and V-B (DoF from geometry alone).

**Built and green (suite 41/41):**
- **Ontology/IR** — `DesignPlan` with pieces (provenance functional/hardware), elements, features,
  behaviours, protocols, **AssemblyRules**; validators V-01…V-16.
- **Cards** — `snap_hook_cantilever` (Bayer), `pin_hinge` (formalizes M0's hinge), `stop_flange`
  (PassiveFeature: a rotation ceiling, real flange geometry); the card API carries
  `provides_pieces` (hardware) and `interaction_rules` (AssemblyRules).
- **Templates** — `box_shell`, `lid_panel`, `flat_panel_mount`, `retained_board`; template collision
  hints for the seating load path (D14 inset).
- **Pipeline** — stage-⑤ resolve, stage-⑥ `compile_assembly` (motion-before-fasteners).
- **Verify** — t0 (`t0_static` three-way + `assembly_rules`), t1 (`t1_remeasure`, COMPILE_DRIFT),
  t2 (`t2_physics`: G-CONV + P-HINGE V-A/V-B, the frozen preset R5, guard trio on verdicts).

**Known limitations / open items:**
- **R2b** (gear contact-only meshing) is FROZEN — a MuJoCo convex-facet contact-formulation limit;
  gear V-B verification is deferred to a `preset_v2`-time decision. Mitigation queue in
  `m1_gear/out/r2b_note.md`: (1) larger module — exhausted; (2) versioned preset — no candidate;
  (3) **[deferred] PhysX 5 SDF backend** (D-M1-8).
- **Easy-anchor pin/bore fit is marginal** — the stop variant's V-B is 4/5 (one seed nicks the
  operation-phase interface limit); flagged honestly in the per-seed record.
- **The baseline Easy anchor has no end stop** — by design it declares none, so its lid folds flat
  past over-centre (V-B 0/5). This is a reported finding, not an open bug; the `stop` variant shows
  what a `stop_flange` buys. Only V-B separates them — V-A's declared joint `range` hides it (D20).
- **Standing rule (D-M8-4):** a physics collision prim may only proxy REAL carved geometry the IR
  declares. A prim with no solid and no IR entity behind it voids any verdict resting on it.

## Update rule

When a milestone closes, add/refresh its row in the table above and touch the **Current system
state** bullets it changes — nothing else. Folders are append-only (never moved/renamed); this file
and `DECISIONS_LOG.md` are the two indices kept current across sessions.
