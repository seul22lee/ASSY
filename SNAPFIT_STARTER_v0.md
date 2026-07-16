# SNAPFIT STARTER v0.1 (EN) — Snap-fit-only task + ontology slice

> Precursor milestone **M-S (Snap Starter)** to MECHSYNTH_SPEC_v0.1.
> Purpose: drive the ENTIRE symbolic stack — ontology → Element Card → constraint
> resolution → compile → Tier0/Tier1 verification → visualization — through a single
> snap-fit task, with no physics engine involved (Tier2 N/A).
> Knowledge source: **Bayer MaterialScience, "Snap-Fit Joints for Plastics — A Design
> Guide"** (hereafter [Bayer]; page citations refer to this file:
> `knowledge/refs/Plastic_Snap_fit_design.pdf`)
>
> Language convention: everything is English, including the `command` field
> (benchmark commands are English by default). Non-English commands are a possible
> future variant axis (multilingual intent parsing), out of scope for v0.

---

## 0. Starter task definition: T-S1 "snap-on lid box"

- **command**: `"Design a snap-lid box I can push shut and pull open by hand. Plastic, for 3D printing."`
- Composition: 2 pieces (box_shell + lid_panel), elements = **cantilever snap hook × N**
  (N∈{2,4}, on opposing sides). Exactly the pattern of [Bayer p.5 Fig.2–3]:
  "cap with cantilever lugs / separable chassis cover".
- No hinge, no motion DoF → **Tier2 (physics) not applicable.** Verification completes
  with Tier0 (geometry) + Tier1 (formulas).
- Task variants (for the benchmark ladder; schema must be identical):
  - T-S1a: separable (default) / T-S1b: **frequent re-open** — triggers the 60%
    permissible-strain rule [Bayer p.12 Table 2 footnote]
  - T-S1c: hook count N=2 vs 4 (effect of the total-mating-force constraint on params)
  - T-S1d: permanent (non-separable) — return angle α′=90° [Bayer p.14: separation
    force uses the same equation with α′]

### What this task verifies (definition of done for M-S)
1. The ontology can express "functions without motion" (fastening / retention / release events)
2. Card formulas reproduce the [Bayer] worked example (golden test G-S1)
3. Formula checks run on dimensions **re-measured from compiled geometry** (not IR values)
4. Tier0 distinguishes intentional interference (undercut) from defect interference (§5.2 — the key technical challenge)
5. Every stage produces visualization artifacts + report.html

---

## 1. Ontology slice (schema per v0.1, plus exactly 2 extensions needed for snap-fits)

### 1.1 Extension ①: event-type behavior in MotionSpec
A snap-fit's function is not continuous motion but a **force-threshold event**
("state is the function", not "motion is the function").
```python
class MotionSpec(BaseModel):
    kind: Literal["rotation","translation","rot_to_trans","fixed",
                  "snap_event"]                    # ← added
    # snap_event only:
    event_force_window_N: Optional[tuple[float,float]] = None
    #   assembly phase: (0, W_in_max)  — hand-assembly upper bound
    #   static/use    : (W_out_min, W_out_max) — retention floor & hand-open ceiling
```

### 1.2 Extension ②: undercut directionality in Binding.offset_params
```python
# snap hook catch: which wall, engaging in which direction
{"u": 0.5, "v": 0.9, "undercut_dir": "insertion_axis_neg"}
```

### 1.3 T-S1 golden IR (tasks/snap_starter.json — authoritative)
```json
{
  "task_id": "T-S1",
  "command": "Design a snap-lid box I can push shut and pull open by hand. Plastic, for 3D printing.",
  "functions": [
    {"verb": "secure",  "object": "lid", "qualifier": "hold closed"},
    {"verb": "allow_access", "object": "contents", "qualifier": "repeated hand open/close"}
  ],
  "behaviors": [
    {"id":"B1","phase":"assembly","motion":{"kind":"snap_event","event_force_window_N":[0,80]},
     "realized_by":"E1","verified_by":"PR-T1-MATE",
     "_note":"hand-close: total mating force <= 80 N (assumption A1, not from Bayer)"},
    {"id":"B2","phase":"static","motion":{"kind":"snap_event","event_force_window_N":[15,60]},
     "realized_by":"E1","verified_by":"PR-T1-SEP",
     "_note":"retention >= 15 N AND hand-open <= 60 N"},
    {"id":"B3","phase":"use","motion":{"kind":"fixed"},"imposed_by":"E1",
     "verified_by":"PR-T0-SWEEP",
     "_note":"hook must not defect-interfere with anything outside the insertion path"}
  ],
  "pieces": [
    {"id":"P1","role":"base","template_ref":"box_shell"},
    {"id":"P2","role":"lid","template_ref":"lid_panel"}
  ],
  "elements": [
    {"id":"E1","card_ref":"snap_hook_cantilever","host_pieces":["P2","P1"],
     "params":{"n_hooks":2,"design_type":2,"alpha_in_deg":30,"alpha_out_deg":45}}
  ],
  "bindings": [
    {"element_id":"E1","port":"beam_root","piece_id":"P2","anchor":"rim_underside_left",
     "mate":"on_face_uv","offset_params":{"u":0.5,"v":1.0}},
    {"element_id":"E1","port":"beam_root","piece_id":"P2","anchor":"rim_underside_right",
     "mate":"on_face_uv","offset_params":{"u":0.5,"v":1.0}},
    {"element_id":"E1","port":"catch_window","piece_id":"P1","anchor":"side_wall_left",
     "mate":"offset_face","offset_params":{"undercut_dir":"insertion_axis_neg"}},
    {"element_id":"E1","port":"catch_window","piece_id":"P1","anchor":"side_wall_right",
     "mate":"offset_face","offset_params":{"undercut_dir":"insertion_axis_neg"}}
  ],
  "material": "PETG"
}
```
Note: with the ontology session's D-ONT decisions applied, this IR additionally carries
`is_base: true` on P1 and the HostTemplate anchor interface (D-ONT-1/-3); protocols
referenced (PR-*) follow the criteria/observables split (D-ONT-2).

---

## 2. Knowledge base: Element Card `snap_hook_cantilever`

### 2.0 Principle — separate knowledge by consumer
| Knowledge kind | Form | Consumer |
|---|---|---|
| Selection heuristics (trade-offs) | KG edges + card `selection_notes` text | LLM (stage ④) |
| Governing formulas | **Python functions** (`formulas` methods) | ⑤ parameter resolution, Tier1 checks |
| Valid ranges / allowables | `param_bounds` dict | validators, ⑤ |
| Placement rules | `placement_rules` (Rule objects) | ⑤ |
| Verification protocols | `verification()` → VerificationProtocol | Tier1/Tier2 |
| Provenance | `citations` | report footnotes (auditable design) |

### 2.1 Knowledge extraction map (source → card field; **every constant/formula must carry a citation**)

| [Bayer] location | Content | Card field |
|---|---|---|
| p.9 Table 1, shape A design 1 | constant-section permissible deflection `y = 0.67·ε·l²/h` | `formulas.y_perm(design=1)` |
| p.9 Table 1, shape A design 2 | tapered (h→h/2) `y = 1.09·ε·l²/h` — deflection +60% [p.13] | `formulas.y_perm(design=2)` **default** |
| p.9 Table 1 bottom row | deflection force `P = (b·h²/6)·(Es·ε/l)` | `formulas.P_deflect` |
| p.14 Mating Force | `W = P·(μ+tanα)/(1−μ·tanα)`; separation force uses α′ | `formulas.W_mate`, `W_sep` |
| p.11 Fig.12 | **deflection y = undercut** (the identity Tier0 measures) | Tier0 measurement definition |
| p.12 Table 2 + footnote | permissible strain (single op); **×0.60 for frequent re-joining** | `eps_pm`, `freq_factor` |
| p.7 Assumptions | rigid mating-part assumption (conservative); equal stiffness halves deflection | `assumption: rigid_catch=True` |
| p.7 Assumptions | non-linear regime → **use secant modulus Es** | `Es_of_eps()` (§2.3) |
| p.8 Fig.9 | root fillet `R ≥ 0.38 mm (0.015 in)`, R/h compromise (~0.5) | `placement_rules` |
| p.8 Design Hints | prefer tapered design (uniform strain, −17% material) | `selection_notes` |
| p.15 Table 3 | friction coefficients (plastic-on-steel basis; same-plastic × factor) | basis for `mu` |
| p.16 Calc Example I | **golden test values** (§3) | `tests/test_golden_bayer.py` |
| p.4 | type taxonomy: cantilever/U/torsion/annular | ontology enum (only cantilever implemented) |

### 2.2 Parameters and valid ranges
```python
param_bounds = {
  "L_mm":       (8, 25),      # cantilever length l
  "h_mm":       (1.2, 4.0),   # root thickness (design 2: tapers to h/2 at tip [Bayer p.8])
  "b_mm":       (4, 12),      # width
  "y_mm":       (0.8, 2.5),   # undercut (= max deflection) [Bayer p.11 Fig.12]
  "alpha_in_deg":  (25, 35),  # insertion angle
  "alpha_out_deg": (30, 90),  # retraction angle (90 = permanent)
  "root_R_mm":  (0.38, 2.0),  # [Bayer p.8: >= 0.015 in]
  "n_hooks":    (2, 4),
  "design_type": {1, 2},      # default 2 [Bayer p.13: +60% deflection]
}
```

### 2.3 Material handling — honest treatment of the secant modulus
[Bayer p.12] requires the strain-dependent secant modulus Es (Fig.16), but this PDF
carries curves for Bayer PC resins only — no PETG curve.
```python
# v0 treatment: conservative approximation + explicit gate
Es_of_eps = lambda eps: 0.75 * PETG.E_MPa      # rationale: PC drops to ~60-75% of E
                                                # at eps=2% [Bayer p.16 example: 1815 MPa class]
# ⚠ ASSUMPTION tag required. Gate G-S4: replace with a table once a PETG datasheet
#   (or Fig.16-equivalent) is obtained.
eps_pm_single = 0.04            # PETG single operation (amorphous: ~70% of yield strain [Bayer p.11])
freq_factor   = 0.60            # frequent re-joining [Bayer p.12 Table 2 footnote]
mu            = 0.35            # PETG-on-PETG estimate (extrapolated from PC 0.45–0.55 ×1.2
                                #  [p.15 Table 3]; replace with literature value. ASSUMPTION tag)
```

### 2.4 resolve_params logic (called by stage ⑤)
[Codifies the p.16 worked procedure — "solve h from y and ε"]
```
inputs: insertion/retraction angles (LLM/default), y (undercut; back-solved from the
        retention floor, or default 1.2), working strain
        ε = eps_pm × (freq_factor if frequent-reopen else 1.0) × safety (0.5 default,
        matching the p.16 example)
order:
  1. h = C(design)·ε·L² / y      (C: design1=0.67, design2=1.09, inverted form)
  2. P = b·h²·Es(ε)·ε / (6·L)
  3. W_in  = P·(μ+tanα_in)/(1−μ·tanα_in)   → check n_hooks·W_in ≤ B1 ceiling (80 N)
  4. W_out = P·(μ+tanα_out)/(1−μ·tanα_out) → check B2 window (15–60 N); if violated,
     adjust α_out / y in a bounded loop
infeasible: StageFailure(INFEASIBLE, listing which inequality is violated and by how much)
```

### 2.5 ports / placement_rules
- ports: `beam_root` (face — grows from the lid rim underside), `catch_window`
  (face — window or undercut lip in the box side wall)
- rules: hooks placed symmetrically on opposing sides (u=0.5) / hook width b ≤ 1/3 of
  the anchor face length / root fillet R = clamp(0.5·h, 0.38, 2.0) [Bayer p.8] /
  for a window-type catch, window width = b + 2·PETG.print_clearance

---

## 3. Golden test G-S1 — reproduce [Bayer p.16 Calculation Example I]

Validates the formula implementation against the handbook's hand calculation.
**If this test fails, the card implementation is wrong (not the book).**
```python
def test_bayer_example_I():
    # Given (Makrolon PC): l=19, b=9.5, y=2.4, α=30°, ε=2% (=½·4%), Es=1815 MPa, μ=0.6
    h = solve_h(design=2, eps=0.02, L=19, y=2.4)          # expect: 3.28 mm (±1%)
    P = P_deflect(b=9.5, h=h, Es=1815, eps=0.02, L=19)     # expect: 32.5 N (±2%)
    W = W_mate(P, mu=0.6, alpha_deg=30)                    # expect: 58.5 N (±2%) [factor 1.8, p.15 Fig.18]
```
Additional golden: p.17 Example II (ring segment cross-section) is out of scope for v0
— rectangular sections only. Note the skip explicitly.

---

## 4. Pipeline application (T-S1 specializations of MECHSYNTH §4)

| Stage | Expected behavior on T-S1 | Gate additions/specials |
|---|---|---|
| ① | extract secure + allow_access | G1 as spec'd |
| ② | **B1 (assembly) · B2 (static) · B3 (imposed use constraint)**, snap_event windows included | G2: snap_event requires force_window (V-11) |
| ③ | fixed 2 pieces | G3 as spec'd |
| ④ | KG: "fasten + separable + plastic" → snap family candidates; type choice (cantilever) cites [Bayer p.4] | G4 as spec'd |
| ⑤ | run §2.4 logic | G5 + **G-S2**: all four W-window inequalities satisfied |
| ⑥ | box/lid templates + carve (hook & window) | G6 as spec'd; **output must include tagged sub-solids** (§5.2) |
| ⑦ | special interference checks of §5 | **G-S3** (below) |
| ⑧ | re-measure geometry → formula checks | G8 + re-measurement rule §5.3 |
| ⑨ | — N/A (no use-phase motion) | report records "T2: N/A" |

## 5. Tier0/Tier1 detail — snap-fit-specific verification

### 5.1 Assembly insertion path
Insertion = lid descends straight along −Z. Sweep sampled at K=40 steps.

### 5.2 **Intentional vs defect interference** (G-S3 — the technical heart of this starter)
In rigid geometry, during the insertion sweep the hook MUST interfere with the catch by
exactly y [Bayer p.11: deflection = undercut]. So "interference = failure" is wrong;
split the check in three:
- **(a) assembled state**: mutual penetration = 0 (hook returns stress-free [Bayer p.3])
  — violation = FAIL(INTERFERENCE)
- **(b) insertion sweep, hook region**: max penetration ∈ [0.9·y, 1.1·y] —
  **measured validation of the undercut** (a measurement AND a criterion)
  - outside the band = FAIL(UNDERCUT_MISMATCH): compiled geometry disagrees with IR's y
- **(c) insertion sweep, everywhere else**: penetration 0 — violation = FAIL(SWEEP_HIT)
  → rollback to ④/⑤
- Implementation: compile the hook as a separately TAGGED solid (⑥'s carve returns
  tagged sub-solids) so interference sites can be classified hook / non-hook.
- Post-M0 note: this is an instance of D22 contact-intent stratification (see §12 A3).

### 5.3 Tier1 re-measurement rule
Check inputs (L, h, b, y) come **from the STEP geometry** (OBB of the tagged hook solid
+ catch-face distances), NOT from the IR. |IR − measured| > 0.05 mm is itself
FAIL(COMPILE_DRIFT) — catches compiler bugs.

### 5.4 Verdict summary (report's verdict block)
```
PASS(T-S1) :=  G1..G6 ∧ (a)(b)(c) ∧ eps_measured ≤ eps_pm_effective
             ∧ n·W_in ≤ 80 N ∧ 15 N ≤ W_out ≤ 60 N ∧ golden G-S1 (in CI)
```

## 6. Visualization (per v0.1 §7, plus two snap-specific views)
- `s6_hook_closeup.png`: hook/catch section close-up with y, h, L, α dimension overlays
  (⑥ emits the dimension metadata alongside geometry)
- `t1_force_window.png`: computed W_in/W_out plotted against the B1/B2 windows
  (red if outside)
- Everything else (IR mermaid, 4 views, exploded, report.html) per the standing spec.

## 7. ASSUMPTION register — track in paper & code
| ID | Content | Resolution condition |
|---|---|---|
| A1 | hand forces: assembly ≤80 N / open window 15–60 N — ergonomic assumption, not [Bayer] | replace with literature values |
| A2 | PETG Es=0.75E, eps_pm=4%, μ=0.35 — extrapolated from PC | PETG datasheet / Fig.16-equivalent |
| A3 | rigid catch assumption (conservative [Bayer p.7]) | both-parts-elastic (p.24 §E) in paper 2 |
| A4 | rectangular cross-sections only (ring segment C/D excluded) | on coverage expansion |

## 8. M-S completion checklist (in this order)
- [x] schema extensions (§1.1–1.2) + validators (V-11)   ← done in the ontology session
- [ ] materials.py: PETG + ASSUMPTION tag fields          ← data-only version exists; verify tags
- [ ] snap_hook_cantilever card: formulas → **G-S1 golden passes** (FIRST: formulas before anything)
- [ ] box_shell/lid_panel templates + anchors + hook carve (tagged solids)
- [ ] ⑤ resolve loop + ⑦ three-way interference check (§5.2) + ⑧ re-measured checks
- [ ] golden IR (T-S1) end-to-end → report.html + G-H visual approval
- [ ] variants: T-S1b (does the 60% rule actually thicken h? show the diff) / T-S1d (α′=90 handling)
- [ ] only then wire stages ①–④ (LLM) — measure command → IR agreement

---

## 9. Demo A — T-S1e "the battery cover that doesn't break" (the failure story)

Goal: **"looks right ≠ works" in a single figure.** Headline demo for contribution 1
(physics/formula verification) and contribution 2 (knowledge grounding).

- command: `"Design a battery cover for 2 AA cells. I'll open and close it often."`
- Key trigger: "open and close it often" → stage ② formalizes frequent re-opening →
  **freq_factor 0.6 fires** [Bayer p.12 Table 2 footnote] → eps_pm 4%→2.4% → ⑤
  back-solves a thicker h.
- Template addition: `battery_bay` (2×AA, standard dimensions with source tag) —
  implemented as a box_shell variant.
- Demo composition (to be scripted: `demos/battery_cover.py`):
  1. **naive baseline**: same command, frozen LLM writes CadQuery directly × N=10
     samples → re-measure hook dimensions per sample → strain distribution histogram
     + fraction in the failure region (>2.4%).
     ⚠ risk: a sample may be accidentally safe → the DISTRIBUTION is the design.
     Counter for passing samples: "passed without grounds (unauditable)" — point at
     the absent rationale sheet.
  2. **this system**: same command → design rationale sheet (§9.1) + passing verdict.
  3. **render-comparison slide**: the two designs side by side — visually
     indistinguishable → reproduce a MUSE-style VLM judge passing BOTH to complete
     the argument.
  4. **physical validation (stretch)**: print both in PETG → 100 hand open/close
     cycles → 10-second fracture video. Protocol: cycle count, fracture onset,
     fracture-site photo (the root — exactly where [Bayer p.8] predicts).

### 9.1 Design rationale sheet output format — report.html subsection
Every decided dimension gets the triple [value | governing equation | citation]:
```
h = 2.8 mm   ← back-solved from y=1.09·ε·l²/h [Bayer p.9 Table 1, design 2]
             ← ε = 2.4% = 4.0% × 0.6 (frequent re-open) [Bayer p.12 Table 2 + footnote]
W_out = 22 N ∈ [15, 60] (retention & hand-open window) [assumption A1]
```
> Positioning: this sheet is the automated answer to the design-review question a
> senior engineer always asks: "what's the basis for this thickness?"

---

## 10. Demo B — T-S2 "Raspberry Pi case" (the real-design story)

Goal: capstone showing **real design = constraint satisfaction around a fixed external
component**. Demonstrates contribution 3 (interface-first pipeline) and one ontology
extension. No motion → stays within Tier0/1 scope.

- command: `"Design a Raspberry Pi 4B case. Screw-free assembly; the lid must open for board access."`
- Composition: cabinet (lower) + lid (snap-on) + **board retention = 4 snap clips**
  ([Bayer p.5 Fig.1: "module held by four cantilever lugs" — the handbook's first
  worked example IS this pattern]). No screws = keeps the pure-snap-fit scope.

### 10.1 Ontology extension ③: ExternalComponent / ComponentCard
```python
class ExternalComponent(BaseModel):
    """Fixed geometry we must design AROUND, not design. Datasheet is the anchor source."""
    id: str
    card_ref: str                       # "rpi4b"
    # ComponentCard provides: envelope (OBB), anchors (holes/ports/board faces),
    #                          keepouts (connector insertion volumes etc.), citations (datasheet)
```
- ElementCard (things we generate; knowledge = design formulas) vs **ComponentCard
  (things we fit around; knowledge = interface dimensions)** — the knowledge base
  gains its second document type (datasheets). Strengthens the grounding claim.
- No Binding extension needed: an ExternalComponent's anchors are ordinary Anchors →
  existing mate predicates reused. (That reuse is itself a test of the ontology.)
- Post-D-ONT-4 note: board-support bosses land in the PassiveFeature card class.

### 10.2 ComponentCard `rpi4b` (v0 data)
```python
# Public mechanical spec — only settled values; the rest gated:
board_mm = (85.0, 56.0)                 # board outline
hole_grid_mm = (58.0, 49.0)             # 4× M2.5 hole spacing
hole_offset_mm = 3.5                    # from corner
hole_d_mm = 2.7
anchors = ["hole_1..4", "board_top", "board_bottom", "edge_ports_A", "edge_ports_B"]
# ⚠ Exact per-port coordinates (USB/HDMI/power cutouts) must be transcribed from the
#   official mechanical drawing — gate G-RPI: port-cutout features stay DISABLED until
#   the drawing is obtained and transcribed (demo runs with lid+clips only).
```

### 10.3 What this demo additionally shows
1. **Necessity of interface-first**: clip positions bind to board hole/edge anchors
   FIRST → case inner width = board_w + 2·(clip margin + wall) is DERIVED. Geometry-first
   would almost surely fail to fit.
2. **Keep-out constraints**: no snap hooks near port edges (keepout ∩ binding check — V-12).
3. **INFEASIBLE demo**: "make the case 20% smaller" → `envelope ⊄ inner_volume`,
   immediate rejection with grounds ("85×56 board does not fit [rpi4b datasheet]").
4. **Clip-fatigue story reused**: with/without "I'll access the board often" the clip h
   differs — the 60% rule re-fires in a new context, evidencing generality.

### 10.4 Implementation order (after the M-S checklist)
- [ ] ExternalComponent + ComponentCard schema + V-12 (keepout)
- [ ] rpi4b card (settled values only; ports behind G-RPI)
- [ ] cabinet template = box_shell + internal boss/clip anchors
- [ ] T-S2 golden IR → end-to-end → INFEASIBLE scenario script
- [ ] shared with Demo A: promote the rationale-sheet renderer to a standard report block

## 11. Division of labor between the demos (paper/talk planning memo)
| | Demo A battery cover | Demo B RPi case |
|---|---|---|
| Audience hook | everyone's taped-shut remote | the maker/designer hello-world |
| Contribution shown | verification (formulas) + knowledge (60% rule) | interface-first + ExternalComponent + INFEASIBLE |
| Extra infrastructure | battery_bay template only (~0) | ComponentCard layer (1 ontology extension) |
| Failure narrative | fatigue fracture (invisible to visual judging) | dimensional misfit · groundless approval |
| Order | first (reuses infra) | capstone |

---

## 12. POST-M0 AMENDMENTS (added after M0/M0-stretch closed and the ontology session)

The main body (§0–11) predates M0. Where they conflict, **this table wins.**

| # | Amendment | Basis |
|---|---|---|
| A1 | `snap_hook_cantilever` has `has_functional_clearance=True` → **`collision_hint()` REQUIRED** (convex approximations of hook & catch). Automatic decomposition (CoACD) forbidden for functional clearances — it swallows them. | D18/D21; enforced at class-definition time by base.py |
| A2 | Every VerificationProtocol splits **criteria (gates) vs observables (recorded, flagged)** at the type level. Protocol references in §1.3 follow this. Measurement names must be in the `ontology/measurements.py` registry (V-13). | D19/D22, D-ONT-2/-6 |
| A3 | §5.2's intentional-interference check is an instance of **D22 contact-intent stratification**: travel-defect interference vs intended interfaces (hook–catch) judged separately. Event magnitudes are observables. | D22 |
| A4 | A **`PassiveFeature`** card class exists for elements that CONSTRAIN or SUPPORT behaviors rather than realize them (stops, bosses, ribs). snap_hook itself is a MechanicalElement (realizes assembly/static behaviors); T-S2/T-S3 bosses and stops are PassiveFeatures. | D-ONT-4 |
| A5 | `Piece.is_base` exists — P1 (box_shell) is base in T-S1. No Tier2 here, but the IR carries it. | D23, D-ONT-3 |
| A6 | Milestone outputs live in numbered folders `mN_*/out` + `REVIEW.md`. "Tests pass" without a REVIEW.md is an incomplete milestone. | D-ONT-7 |
| A7 | Reference PDF path settled: `knowledge/refs/Plastic_Snap_fit_design.pdf`. Constants are verified against the PDF itself, not the mapping table (G3.1). | file move done |
