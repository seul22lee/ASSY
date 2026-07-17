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
| M8 | [`m8_pin_hinge_easy/`](m8_pin_hinge_easy/) | **B-track**: `pin_hinge` + `stop_flange` cards, the **multi-element Easy anchor** (box + lid + hardware pin + snap latch) compiled and verified t0→t1→t2, and the **D20 no-stop/stop pair**. | ✅ **Benchmark PASS** (t0 ARs · t1 0 mm drift · V-A 5/5 · V-B 5/5). D20 demo golden `anchor_easy_nostop` = **EXPECTED_FAIL** (V-B 1/5, folds over). An earlier V-B PASS was **retracted** (D-M8-4) — it rested on an invented stop; the rule is now mechanized as a build error. |

| M9 | [`m9_llm_stages/`](m9_llm_stages/) | **E-track 1**: the LLM stages ①–④ (functions / behaviours / pieces / elements+bindings), the KG narrowing (§3.7), the grading harness, and the first fully-automatic command→IR→physics run (N=3). | ✅ **The loop closes.** ①②③④ PASS → ⑤ → ⑥ (3 parts) → t2 **V-A 5/5, V-B 0/5**: on an IR no human touched, the physics caught the missing stop (D-M8-5 rediscovered). macro F1 **0.676**; elements 0.80 vs bindings 0.18 — it knows *what*, not *where*. Local qwen3-coder-30B (no frontier key — D-E-6). |
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

**Built and green (suite 54/54):**
- **Ontology/IR** — `DesignPlan` with pieces (provenance functional/hardware), elements, features,
  behaviours, protocols, **AssemblyRules**; validators V-01…V-16.
- **Cards** — `snap_hook_cantilever` (Bayer), `pin_hinge` (formalizes M0's hinge), `stop_flange`
  (PassiveFeature: a rotation ceiling, real flange geometry); the card API carries
  `provides_pieces` (hardware) and `interaction_rules` (AssemblyRules).
- **Templates** — `box_shell`, `lid_panel`, `flat_panel_mount`, `retained_board`; template collision
  hints for the seating load path (D14 inset).
- **Pipeline** — stages ①–④ (LLM: `s1_intent`/`s2_behavior`/`s3_decompose`/`s4_interface` +
  `llm_client` with structured output, validator-repair retries ≤3, and a verbatim `stage_log`
  audit); stage-⑤ resolve; stage-⑥ `compile_assembly` (motion → fasteners → passive features).
- **Knowledge** — `ontology/functional_basis.py` (NIST TN 1447 subset), card `selection_notes` +
  `citations`, `knowledge/kg.py` (§3.7 `candidates()` narrowing; gate G3.2 tested).
- **Verify** — t0 (`t0_static` three-way + `assembly_rules`), t1 (`t1_remeasure`, COMPILE_DRIFT),
  t2 (`t2_physics`: G-CONV + P-HINGE V-A/V-B, the frozen preset R5, guard trio on verdicts,
  collision-provenance gate).

**Known limitations / open items:**
- **R2b** (gear contact-only meshing) is FROZEN — a MuJoCo convex-facet contact-formulation limit;
  gear V-B verification is deferred to a `preset_v2`-time decision. Mitigation queue in
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
- **No frontier LLM in this environment (D-E-6)** — E-track ran on local Ollama (qwen3-coder-30B-Q4;
  ~30B is the ceiling here). Scores mean "this model + this scaffolding", not "LLM stages don't
  work". A frontier re-run is one env var.
- **`verification()` is unimplemented on every card (D-E-5 DRAFT)** — so no stage can emit
  protocols and V-01 is unsatisfiable for any generated IR. A card-layer hole, not an LLM failure.
- **§4-③'s six-template vocabulary is 2/6 implemented (D-E-3 DRAFT)** — the Hard anchor needs all
  four missing (`drawer_tray`, `cabinet_shell`, `knob_shaft`, `rack_bar`).

## Update rule

When a milestone closes, add/refresh its row in the table above and touch the **Current system
state** bullets it changes — nothing else. Folders are append-only (never moved/renamed); this file
and `DECISIONS_LOG.md` are the two indices kept current across sessions.
