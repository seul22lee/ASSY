# MechSynth — Design & Implementation Spec v0.1 (EN)

> **One-line claim (novelty statement)**
> The first framework/benchmark that, from functional intent, grounded in an element
> library compiled from handbook knowledge, generates mechanism assemblies realized as
> real machine elements — and verifies their function by force-driven physics simulation.

This document is an **implementation spec**. Every section is a target for code; every
pipeline stage must have (a) typed inputs/outputs, (b) a verification gate, and (c)
visualization artifacts. There is no such thing as a stage that "just passes through" —
a stage without a gate is not considered implemented.

> STATUS NOTE: decisions D1–D12 below are locked. Post-M0 decisions live in
> DECISIONS_LOG.md (D13+ and D-ONT-*), which extends — and where noted supersedes —
> this document. M0 and M0-stretch are CLOSED (R1 retired via the collision_hint
> pathway); the ontology package is implemented (m2_ontology).

---

## 0. Locked scope (Decision Log summary)

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | Task: functional intent → mechanism assembly (forward design) | MUSE is spec-following; we include intent→spec |
| D2 | Elements are realized as **real machine-element geometry**, not idealized joints | Differentiator vs ArtiCAD; prerequisite for physics verification |
| D3 | Verification = **force-driven physics engine** (use phase) + **handbook formulas** (assembly/static) | Differentiator vs MUSE's VLM visual judging |
| D4 | Phase formalization: use / assembly / static | "motion is the function" vs "state is the function" |
| D5 | Knowledge compiled into **ontology + executable Element Cards**, not RAG | Formulas must be executed, not retrieved |
| D6 | Interface-first: Binding (④) precedes geometry resolution (⑤) | ArtiCAD's Connector lesson |
| D7 | CadQuery/build123d code is emitted by an **IR→code compiler**, not an LLM | Eliminates the code-execution failure mode by construction |
| D8 | Material: **single PETG instance** (Material class kept in the schema) | Cuts ontology combinatorics; PETG > PLA for snap-fits |
| D9 | Four elements: pin hinge / slide rail / rack-pinion (spur) / cantilever snap latch | Minimal set covering both anchor tasks |
| D10 | Anchor tasks: Easy = snap-latched hinged box, Hard = rack-pinion drawer cabinet | §8 |
| D11 | Fine-tuning/RLVR, editing, FEA, RAG automation, injection DFM → **deferred to paper 2** | Protect MVP scope |
| D12 | Physics engine: MuJoCo (SDF / convex decomposition to be evaluated) | §6; resolved by D18: card collision_hint |

**Out of scope (v0.1):** metals/wood, FEA, assembly-sequence planning, freeform surfaces,
multimodal input (images), LLM training, intent-level editing (schema kept compatible).

---

## 1. Repository layout

```
mechsynth/  (repo: ASSY)
├── ontology/
│   ├── schema.py            # All Pydantic classes (§2)
│   ├── validators.py        # Consistency rules (§2.5) + V-11..V-13
│   ├── measurements.py      # Controlled registry of measurement names (D-ONT-6)
│   └── functional_basis.py  # NIST Functional Basis vocabulary subset
├── knowledge/
│   ├── cards/               # Element Card = code (§3)
│   │   ├── base.py          # ElementCard ABC (+ PassiveFeature, D-ONT-4)
│   │   ├── pin_hinge.py
│   │   ├── slide_rail.py
│   │   ├── rack_pinion.py
│   │   ├── snap_latch.py
│   │   └── stop_flange.py   # PassiveFeature (D-ONT-4)
│   ├── materials.py         # PETG constants (§3.1)
│   ├── refs/                # source PDFs (Bayer snap-fit guide, Pahl & Beitz, ...)
│   └── kg.py                # mini knowledge graph (networkx, §3.7)
├── pipeline/
│   ├── s1_intent.py         # ① function interpretation
│   ├── s2_behavior.py       # ② behavior derivation
│   ├── s3_decompose.py      # ③ piece decomposition
│   ├── s4_interface.py      # ④ element selection + Binding
│   ├── s5_geometry.py       # ⑤ geometry parameter resolution (constraints)
│   ├── s6_compile.py        # ⑥ IR → build123d compiler
│   ├── llm_client.py        # LLM wrapper (structured output enforced)
│   └── rollback.py          # failure attribution → retry routing
├── verify/
│   ├── t0_static.py         # Tier0: execution/watertight/interference/clearance
│   ├── t1_formula.py        # Tier1: element formula checks
│   ├── t2_physics/          # Tier2: MuJoCo behavioral tests
│   │   ├── step2mjcf.py     # STEP→MJCF converter (§6.2)
│   │   ├── protocols.py     # actuate-observe-judge protocols (§6.3)
│   │   └── runner.py        # multi-seed execution + verdicts
│   └── gates.py             # unified per-stage gate definitions (§5)
├── viz/
│   ├── ir_graph.py          # IR → mermaid/graphviz (§7.2)
│   ├── cad_view.py          # 3D snapshots/GLB export (§7.3)
│   ├── sim_video.py         # MuJoCo render → mp4 with HUD (§7.4)
│   ├── plots.py             # θ(t), s(t), ratio plots (§7.5)
│   └── report.py            # per-run HTML report (§7.6)
├── tasks/
│   ├── anchor_easy.json     # snap-latched hinged box (golden IR, §8.1)
│   ├── anchor_hard.json     # rack-pinion drawer cabinet (golden IR, §8.2)
│   └── snap_starter.json    # T-S1 (SNAPFIT_STARTER §1.3)
├── m0/, m2_ontology/, m3_cards/, ...   # numbered milestone snapshots: out/ + REVIEW.md (D-ONT-7)
├── runs/                    # run artifacts (git-ignored, §7.1)
└── tests/                   # unit/golden tests (§10)
```

Pinned dependencies: `build123d`, `ocp-tessellate`, `mujoco>=3.x`, `trimesh`, `coacd`
(kept for comparison only — see D18), `networkx`, `pydantic>=2`, `matplotlib`,
`imageio[ffmpeg]`, `jinja2`.
VS Code extension: **OCP CAD Viewer** (live 3D view for build123d — §7.3).

---

## 2. Ontology v0.1

### 2.1 Design principles
- ~12±3 classes, ~8±2 relations. **Only what the two anchor tasks require.**
- No OWL/RDF. Pydantic v2 = schema, runtime type, and validator in one.
- Every geometric decision is expressed as **reference (Anchor) + predicate (Mate) +
  bounded parameter** — never raw coordinates.
- What the LLM touches: ontology instances (discrete decisions) only. It never emits
  coordinates or code.

### 2.2 Class definitions

| Class | Definition | Key attributes |
|---|---|---|
| `DesignPlan` | IR root; single source of truth for the pipeline | task_id, everything below |
| `Function` | user-level purpose | verb (Functional Basis), object, qualifier |
| `Behavior` | kinematic/mechanical specification | phase, motion (DoF pattern), range, load, transmission |
| `Phase` | enum: `use` / `assembly` / `static` | — |
| `Piece` | independent rigid body (one output STEP per Piece) | id, role, template_ref, **is_base** (D23) |
| `HostTemplate` | parametric skeleton of a piece (box, drawer, …) | params (dict), **anchors (declared list)** |
| `MechanicalElement` | machine-element instance (realizes behaviors) | card_ref, params, ports |
| `PassiveFeature` | constrains/supports behaviors, does not realize them (stops, bosses, ribs) — D-ONT-4 | card_ref, params, ports, imposes |
| `Port` | named interface geometry of an element | name, kind (axis/face/edge/point) |
| `Anchor` | named geometric feature of a host template | name, kind — **auto-assigned at template birth** |
| `Binding` | Port ↦ Anchor attachment | port, anchor, mate (predicate), offset_params |
| `Mate` | relational predicate enum | `coincident_axis` / `flush_face` / `offset_face` / `concentric` / `on_face_uv` |
| `Parameter` | named continuous value + unit + valid range | name, value, unit, bounds, resolved_by |
| `Rule` | parameter constraint (equality/inequality, card-sourced) | expr, source_citation |
| `VerificationProtocol` | actuate–observe–judge triple; **criteria (gates) split from observables** (D19/D22, D-ONT-2) | actuation, criteria, observables |
| `Material` | material properties | E, eps_allow, mu, density (v0.1: PETG only) |
| `Citation` | knowledge provenance | doc, section |

### 2.3 Relations (edges)

```
Function      —decomposes_to→  Behavior            (1:N)
Behavior      —realized_by→    MechanicalElement    (N:1, use/assembly phase)
Element/PassiveFeature —imposes→ Behavior           (imposed constraints; e.g., latch → use-phase non-interference)
Element       —has_port→       Port
Binding:      Port —binds_to→  Anchor  (+ Mate)
Rule          —constrains→     Parameter
Behavior      —verified_by→    VerificationProtocol (mandatory for use phase)
Element       —requires→       Material property predicates (e.g., snap_latch requires eps_allow ≥ 3%)
```

### 2.4 Pydantic schema (schema.py — implementation target, abridged)

```python
from pydantic import BaseModel, Field, model_validator
from enum import Enum
from typing import Literal, Optional

class PhaseE(str, Enum):
    use = "use"; assembly = "assembly"; static = "static"

class MotionSpec(BaseModel):
    kind: Literal["rotation", "translation", "rot_to_trans", "fixed", "snap_event"]
    axis_hint: Optional[str] = None          # semantic hint ("horizontal_rear") — not coordinates
    range_value: Optional[float] = None      # deg or mm
    range_unit: Optional[Literal["deg","mm"]] = None
    transmission: Optional[dict] = None      # e.g. {"mm_per_rev": 60.0}
    event_force_window_N: Optional[tuple[float, float]] = None   # snap_event only

class Behavior(BaseModel):
    id: str
    phase: PhaseE
    motion: MotionSpec
    load: Optional[dict] = None              # {"mass_kg": 0.5, "direction": "-z"}
    realized_by: Optional[str] = None        # element id
    imposed_by: Optional[str] = None         # constraint-imposing element id
    verified_by: Optional[str] = None        # protocol id

class Port(BaseModel):
    name: str
    kind: Literal["axis","face","edge","point"]

class Binding(BaseModel):
    element_id: str
    port: str
    piece_id: str
    anchor: str                              # must exist in the piece's HostTemplate anchors
    mate: Literal["coincident_axis","flush_face","offset_face","concentric","on_face_uv"]
    offset_params: dict = Field(default_factory=dict)   # {"edge_margin_mm": 15.0} / {"u":0.5,"v":0.9,"undercut_dir":...}

class Parameter(BaseModel):
    name: str; value: Optional[float] = None
    unit: str; lo: float; hi: float
    resolved_by: Literal["rule","formula","solver","user","default"]

class Piece(BaseModel):
    id: str; role: str
    template_ref: str                        # "box_shell" | "lid_panel" | "drawer_tray" | ...
    is_base: bool = False                    # D23 fixture rule
    params: dict[str, float] = Field(default_factory=dict)

class ElementInstance(BaseModel):
    id: str; card_ref: str                   # "pin_hinge" etc.
    params: dict[str, float] = Field(default_factory=dict)
    host_pieces: list[str]                   # pieces this element carves into

class DesignPlan(BaseModel):
    task_id: str
    command: str                             # verbatim user command (English by default)
    functions: list[dict]
    behaviors: list[Behavior]
    pieces: list[Piece]
    elements: list[ElementInstance]
    bindings: list[Binding]
    parameters: list[Parameter]
    protocols: list[dict]                    # typed VerificationProtocol in implementation
    material: str = "PETG"
    stage_log: list[dict] = Field(default_factory=list)   # per-stage decision audit trail
```

### 2.5 Consistency rules (validators.py — all implemented; violations raise `IRValidationError`)

| ID | Rule |
|----|------|
| V-01 | every `use`-phase Behavior has a `verified_by` protocol |
| V-02 | every Binding's `anchor` exists in the target Piece's HostTemplate anchors |
| V-03 | every Binding's `port` exists in the element card's declared ports |
| V-04 | every Parameter satisfies `lo ≤ value ≤ hi` (after resolution) |
| V-05 | element `requires` material predicates hold for the current Material |
| V-06 | `rot_to_trans` Behaviors must carry a transmission dict |
| V-07 | every Piece participates in ≥1 Binding or has role="base" (no orphan pieces) |
| V-08 | behaviors imposed by a card are registered in the IR (no dropped latch constraints); applies to both card classes (D-ONT-4) |
| V-09 | mate `on_face_uv` requires offset_params u,v ∈ [0,1] |
| V-10 | DesignPlan JSON round-trip is lossless |
| V-11 | `snap_event` motions must carry event_force_window_N |
| V-12 | (reserved) keepout ∩ binding checks (T-S2/T-S3) |
| V-13 | every criterion/observable measurement key is in the measurements registry (D-ONT-6) |

---

## 3. Knowledge base: Element Cards (knowledge/cards/)

### 3.0 Principle — knowledge separated by consumer
| Knowledge kind | Form | Consumer |
|---|---|---|
| Selection heuristics (trade-offs) | KG edges + card `selection_notes` text | LLM (stage ④) |
| Governing formulas | **Python functions** (`formulas` methods) | ⑤ parameter resolution, Tier1 |
| Valid ranges / allowables | `param_bounds` dict | validators, ⑤ |
| Placement rules | `placement_rules` (Rule objects) | ⑤ |
| Verification protocols | `verification()` → VerificationProtocol | Tier1/Tier2 |
| Provenance | `citations` | report footnotes (auditable design) |

### 3.1 Material constants (materials.py) — single PETG instance

```python
PETG = Material(
    name="PETG", E_MPa=2100.0, eps_allow_pct=4.0,   # short-term permissible strain (snap-fits)
    mu_friction=0.30, density_kg_m3=1270.0,
    yield_MPa=50.0, print_min_wall_mm=1.2, print_clearance_mm=0.30,
    citations=["Bayer Snap-Fit Design Guide (analogy)", "generic PETG datasheet range"])
```
> Gate G3.1: every constant cross-checked against ≥2 source documents within ±20%,
> with citations filled. (No constant may be hard-coded without provenance.)

### 3.2 ElementCard abstract interface (base.py)

```python
class ElementCard(ABC):
    card_id: str
    ports: list[Port]
    param_bounds: dict[str, tuple[float, float, str]]   # name -> (lo, hi, unit)
    requires: dict                            # material predicates etc.
    imposes: list[Behavior]                   # imposed constraints (templates)
    selection_notes: str                      # trade-off text for the LLM
    citations: list[Citation]
    has_functional_clearance: bool = False    # if True, collision_hint() is REQUIRED (D18/D21)

    @abstractmethod
    def resolve_params(self, ir, inst) -> dict: ...
        # compute unresolved params via formulas/rules. NO coordinates (that's ⑤/⑥).
    @abstractmethod
    def carve(self, host_parts, inst, bindings) -> dict: ...
        # carve/attach element geometry into build123d parts; returns TAGGED sub-solids
    @abstractmethod
    def formula_check(self, inst) -> list[CheckResult]: ...
        # Tier1 checks (e.g., recompute strain)
    @abstractmethod
    def verification(self, ir, inst) -> VerificationProtocol | None: ...
        # returns the physics protocol for use-phase elements
    def collision_hint(self, inst) -> list[Primitive]: ...
        # convex primitive approximation of functional clearances (bores, slots, teeth).
        # base.py raises CollisionHintRequired at class-definition time if
        # has_functional_clearance=True and this is missing. (D18/D21)

class PassiveFeatureCard(ElementCard):        # D-ONT-4
    """Constrains or supports behaviors (stops, bosses, ribs, guides); never realizes them."""
```

### 3.3 Card 1 — `pin_hinge`
- **ports**: `axis` (axis), `mount_A` (face), `mount_B` (face)
- **params**: pin_d [2,6] mm, knuckle_w [4,12] mm, knuckle_n {3,5}, clearance [0.2,0.4] mm, edge_margin ≥ knuckle_w
- **key rules**: rotational clearance = PETG.print_clearance; lid edge chamfer ≥ pin_d/2 + clearance for sweep clearance
- **imposes**: `assembly` behavior — pin insertion path must be open along the axis
- **verification (use)**: torque-driven open/close (§6.3 P-HINGE)
- **has_functional_clearance = True** → collision_hint(): ring of convex wedges for the bore (validated in M0-stretch; D18)
- optional PassiveFeature companion: `stop_flange` (end stop; imposes a use-phase rotation limit)

### 3.4 Card 2 — `snap_hook_cantilever` (cantilever snap hook)
> **Renamed & corrected per D-ONT-8 (was `snap_latch`).** Canonical name and full treatment
> live in SNAPFIT_STARTER §2 (authoritative for the snap task). The `snap_latch` name is a
> deprecated alias retained only until the card session lands, then removed.
- **ports**: `beam_root` (face — grows from the lid rim underside), `catch_window` (face — window/undercut lip in the box side wall)
- **params**: L [8,25], h [1.2,4], b [4,12], y (undercut/deflection) [0.8,2.5], α_in [25,35]°, α_out [30,90]°, root_R [0.38,2.0], n_hooks {2,4}, design_type {1,2} (see SNAPFIT §2.2)
- **formulas (Bayer)** — implemented in `formulas`; every constant cites its Bayer page/table (SNAPFIT §2.1, §2.4). Governing shapes: permissible deflection `y_perm` (design 1/2 coefficients, Bayer p.9 Table 1), deflection force `P` (Table 1), mating/separation force `W` (p.14, separation uses the return angle α′).
- **has_functional_clearance = True** → **collision_hint() REQUIRED** (D18/D21). The catch window carries a geometric clearance a generic CoACD would swallow, exactly as it swallowed the M0 bore — so any conversion to MJCF must use card-supplied convex approximations of the hook and catch. (This corrects the earlier `clearance=False` reading: the engagement *event* being formula-checked, not physics-checked, is a separate concern from the geometry's integrity in any downstream sim.)
- **imposes**: `assembly` behavior (pin/hook insertion path must be open) + `use` behavior (hook must not defect-interfere with the lid sweep — Tier0 sweep check, §5.2 intentional-vs-defect).
- **phase**: the function itself is assembly (fastening event) + static (retention). **Not a physics-engine target** — Tier1 formulas + Tier0 geometry complete it (rigid-body sim cannot express elastic deflection: D3).

### 3.5 Card 3 — `slide_rail` (rectangular slide)
- **ports**: `rail_mount` (face), `carriage_mount` (face), `travel_axis` (axis)
- **params**: rail_h [4,10], rail_w [4,10], clearance [0.25,0.45], engagement_len, stop_tab
- **rules**: `engagement_len ≥ 0.35 * stroke` (moment resistance);
  `drawer_w = body_inner_w − 2*(rail_w + clearance)` ← **⑤ derives geometry from this equality** (D6 in action)
- **verification (use)**: force-driven slide (§6.3 P-SLIDE)
- **has_functional_clearance = True** → collision_hint() required (groove as box primitives)

### 3.6 Card 4 — `rack_pinion` (spur rack & pinion)
- **ports**: `pinion_axis` (axis), `rack_mount` (face), `mesh_line` (edge)
- **params**: module m **[3.0,4.0] provisional** (raised from [1.0,2.5]; standard 3.0/4.0) — R2b/D-M1-2: modules ≤2 are dt-unstable at the frozen preset, so the lower bound is provisionally raised until the m=3 mitigation probe is tested; restore the range once R2b is retired. z_pinion [10,24], pressure_angle 20° (fixed), face_w [4,10], backlash [0.1,0.25]
- **formulas**:
  - pitch diameter `d = m * z`; travel per rev `= pi * m * z`
  - target transmission ("N revs per stroke") back-solves `m*z` → snap to integer z, standard m (1.0/1.5/2.0/2.5)
  - rack length `L_rack ≥ stroke + pi*m*z/4` (engagement margin)
  - axis-to-rack distance `a = d/2 + backlash correction`
- **tooth profile**: ~~v0.1 allows an involute approximation (trapezoidal + tip round)~~ **the trapezoidal approximation is DEAD (D-M1-1, M1).** At z=12 it is not conjugate — its constant-slope flanks cause facet-to-facet contact jumps that diverge in rigid contact (`m1_gear/out/l1_contact_jump.png`, L1), and it is too fat in the dedendum to seat at the designed backlash (needs +0.9 mm centre → backlash 0.85 mm, 4×). **The tooth profile is the true involute; `collision_hint()` defaults to an involute wedge decomposition** (convex prism per flank segment). Wedge count TBD at the passing rung once R2 is retired in-bounds.
  - **R2 status (M1, D-M1-7):** R2a RETIRED — the involute is geometrically conjugate and **forward V-B meshing is sim-demonstrable** (ratio −0.50, 4/5 at frozen/5). R2b **FROZEN/DEFERRED** — the module route is exhausted (m≤6 all 0/5) and no preset param helps; D1 isolates the killer as the **reversal backlash-crossing impact** (formulation, a 0.5 s dwell does not help). Revisit only via a versioned preset_v2 or a pitch-cylinder contact proxy (future G-H).
- **verification (use)**: **V-A (declared-shaft) transmission-ratio check is the standing requirement** — the emergent-travel-ratio **V-B P-GEAR is DOWNGRADED (D-M1-7)** with a documented gap: bidirectional contact meshing (the reversal/backlash-crossing impact) is not stable in the rigid rig. Forward V-B is demonstrable; the reversal is the gap. A `rack_pinion` design carries a standing **R2b-open** flag until a preset_v2 or contact-proxy retires it.
- **has_functional_clearance = True** → **card-supplied convex tooth-flank decomposition via collision_hint() is MANDATORY; `mujoco.sdf.gear` is FORBIDDEN** (it simulates an ideal analytic gear, not our compiled geometry — D21)

### 3.7 Mini knowledge graph (kg.py)
- networkx DiGraph. Nodes = {4 behavior patterns, 4+1 element cards, 1 material, 1 process}.
- Edges = realizes / imposes / requires / substitutes (hinge ↔ snap-open, etc.).
- **Query API**: `candidates(behavior) -> list[card_id]` — narrows LLM choices at ④.
- Gate G3.2: for every behavior in both anchor tasks, candidates() contains the correct card (unit test).

---

## 4. Pipeline spec (①–⑥ generation, ⑦–⑨ verification)

Shared conventions:
- Each stage is a pure function `run(ir: DesignPlan, ctx) -> DesignPlan`, returning a copy.
- Each stage appends {stage, decisions, llm_raw, timestamp} to `ir.stage_log`.
- Gate failure raises `StageFailure(stage, code, detail)` → routed by rollback.py.
- All LLM calls use structured output (JSON schema enforced, pydantic parse retries ≤3).
- **Every stage writes visualization artifacts to runs/** (§7). A stage without
  visualization is not considered implemented.

### ① Function interpretation (s1_intent.py) — LLM
- in: `command: str` / out: `functions[]` (mapped to the Functional Basis verb subset)
- Gate **G1**: (a) every function.verb is in the vocabulary; (b) quantitative phrases
  in the command (e.g., "300 mm") are captured as qualifiers — missing = fail.
- Viz: `s1_functions.md` (source-text highlighting ↔ function mapping table)

### ② Behavior derivation (s2_behavior.py) — LLM + phase rules
- out: `behaviors[]` — each with a phase; use-phase MotionSpec fully populated.
- Gate **G2**: V-01 precheck (protocol slots reserved for use behaviors), V-06, V-11,
  unit checks. **Easy-anchor expectation: use (rotation ≥90°) + static (hold closed) +
  assembly (2-piece fastening) — fewer = fail.**
- Viz: `s2_behaviors.mmd` (Function→Behavior mermaid graph, phase-colored)

### ③ Piece decomposition (s3_decompose.py) — LLM (KG-informed)
- out: `pieces[]` (role + template_ref). Template vocabulary (v0.1, fixed 6):
  `box_shell / lid_panel / drawer_tray / cabinet_shell / knob_shaft / rack_bar`.
- Gate **G3**: V-07, template_ref existence, piece count ≤ 6.
- Viz: `s3_pieces.md`

### ④ Interface design (s4_interface.py) — **precedes ⑤ (D6)** — KG query + LLM
- procedure: per behavior, `kg.candidates()` → LLM selects citing selection_notes →
  Bindings fixed (port ↦ anchor + mate + offset_params).
- Gate **G4**: V-02, V-03, V-05, V-08; every use behavior has realized_by;
  selection rationale text contains ≥1 citation (auditable design).
- Viz: `s4_bindings.mmd` + `s4_rationale.md` (choices + citations)

### ⑤ Geometry parameter resolution (s5_geometry.py) — symbolic (no LLM)
- procedure: (1) card `resolve_params` (formulas), (2) collect card placement_rules +
  template constraints into an equality/inequality system, (3) solve: propagate
  equalities → midpoint defaults for free vars → bisect adjustments on violations
  (~10 constraints; no general solver needed).
- Gate **G5**: V-04 exhaustive; every Parameter.resolved_by set; zero free variables.
  **Infeasible system → StageFailure(INFEASIBLE, violated Rule list attached)** → roll back to ④.
- Viz: `s5_params.html` (value/range/resolved_by/source-rule table; violations in red)

### ⑥ IR → CAD compilation (s6_compile.py) — deterministic (no LLM, D7)
- procedure: instantiate HostTemplates (build123d) → bind anchors to real coordinates →
  apply card `carve()` in sequence → per-Piece STEP export + assembly placement JSON.
- Gate **G6**: (a) no exceptions; (b) piece count = STEP count; (c) every solid volume > 0;
  (d) **determinism**: same IR compiled twice → identical STEP hashes.
- Viz: `s6_parts/*.glb` + `s6_assembly.glb` + 4-view PNGs + **exploded view** (§7.3)

### ⑦ Tier0 static verification (t0_static.py)
- checks: watertight/manifold per solid; pairwise interference; specified clearances
  measured (hinge pin–bore, rail–carriage, latch overhang); **sweep interference**
  (use-phase paths sampled N=36, stratified by contact intent per D22 — intended
  interfaces are judged separately from travel defects).
- Gate **G7**: all pass. Failure-code routing: INTERFERENCE→⑤, SWEEP_HIT→④.
- Viz: `t0_report.html` (per-check pass/fail + interference highlight PNGs + measured clearances)

### ⑧ Tier1 formula checks (t1_formula.py)
- run each element's `formula_check()`: snap strain / W_out ratio, gear m·z consistency,
  rail engagement ratio.
- **Inputs are re-measured from ⑥'s geometry, not read from the IR** (catches compiler bugs;
  |IR − measured| > 0.05 mm = FAIL(COMPILE_DRIFT)).
- Gate **G8**: all CheckResults pass. Failure → ⑤.
- Viz: `t1_report.html` (formula / substituted values / result / allowable / citation table)

### ⑨ Tier2 physics verification (t2_physics/) — §6
- Gate **G9**: per-protocol verdicts (multi-seed majority).
- Viz: `t2_<protocol>.mp4` (HUD burned from the scored series — D15/G-H admissibility)
  + verdict plots + tables.

### Rollback routing (rollback.py)
| Failure code | Retry target | Info passed |
|---|---|---|
| G1–G4 validation | same stage, LLM re-call | full validator error text |
| INFEASIBLE (G5) | ④ | violated Rule list |
| INTERFERENCE (G7) | ⑤ | interfering pair + depth |
| SWEEP_HIT (G7) | ④ | angle/displacement + site |
| FORMULA_FAIL (G8) | ⑤ | failing formula + margin |
| PHYSICS_FAIL (G9) | ④ (default) | protocol observation summary |
- Retry caps: 3 per stage, 10 total. Beyond that the run is recorded as failed
  (scored as a benchmark fail).

---

## 5. Gate roster (verify/gates.py — single source)

| Gate | Stage | Auto/manual | On failure |
|---|---|---|---|
| G1–G4 | ①–④ | auto | retry same stage |
| G3.1/3.2 | knowledge layer | unit tests (CI) | fix implementation |
| G5 | ⑤ | auto | roll back to ④ |
| G6 | ⑥ | auto | compiler bug = code fix (never an LLM retry) |
| G7 | ⑦ | auto | see routing table |
| G8 | ⑧ | auto | roll back to ⑤ |
| G9 | ⑨ | auto | roll back to ④ |
| G-CONV | STEP→MJCF | auto | includes bore/slot clearance-retention ray-cast (D18) and visual-bbox ≈ collision-bbox (D15) |
| G-H | per run | **manual (human eyes)** | approve via REVIEW.md checklist; videos admissible only with HUD from scored series + variant-explicit filenames |

> G-H: even with all automatic gates green, a run is promoted to golden only after a
> human reviews the report/videos. The last line of defense against "nonsense that
> passes checks".

---

## 6. Tier2 physics verification detail

### 6.1 Two verification modes (implement both, distinctly)
- **Mode V-A (constraint-assisted)**: IR-known joints (hinge axis, slide axis) declared
  as MuJoCo joints; everything else contact. Stable, fast. Verifies range/interference/
  operation under load.
- **Mode V-B (contact-only)**: no joint declarations; free bodies + contact. Strict test
  of whether the element **geometry itself** produces the DoF. Gears MUST be V-B
  (meshing must emerge or the test is meaningless).
- **Post-M0 hardening (D20): V-A alone is structurally blind** — it confirms any
  mechanism whose missing features its own joint declarations supply (proven: no-stop
  vs stop-flange both pass V-A; V-B separates them). **V-B is required, not optional,
  for card-realized joints. V-A/V-B disagreement is diagnostic signal — triage, never
  average.**
- **Fixture rule (D23)**: the designated base piece (`is_base`) is welded to world —
  a boundary condition, not a joint on the mechanism under test. Free everything the
  behavior spec claims moves, plus its realizing elements.
- v0.1 assignment: P-HINGE = V-A + V-B (both demonstrated in M0/M0-stretch);
  P-SLIDE = V-A required / V-B target; P-GEAR = **V-B required**.

### 6.2 STEP→MJCF converter (step2mjcf.py) — was top risk R1; **resolved by D18**
1. STEP → trimesh per piece; mm→m conversion explicit (G-CONV asserts visual bbox ≈
   collision bbox — D15).
2. Collision strategy (settled order, per M0-stretch data):
   - (a) **card `collision_hint()` primitives** — DEFAULT for all functional
     clearances (bores, grooves, teeth). Ring-of-wedges validated: 128% clearance
     retention, emergent revolute DoF.
   - (b) CoACD — **rejected for functional clearances** (best config retained 10% of
     clearance = seized hinge; 239 hulls; G-CONV reject). Kept only for blobby
     non-functional shapes.
   - (c) MuJoCo SDF — unreachable for arbitrary meshes (plugin ships analytic shapes
     only).
3. Inertia: trimesh volume × PETG density.
4. Contact parameter preset: ONE preset, frozen (quasi-static calibration: penetration
   ≤ 0.05 mm under operating loads ≪ print clearance 0.30 mm). Never retuned per run
   (R5); a global change requires re-running all prior V-A/V-B regressions.
- Gate **G-CONV**: (a) mass > 0; (b) no initial penetration; (c) gravity-only 1 s
  settle without divergence; (d) visual bbox ≈ collision bbox (D15); (e) functional
  bore/slot clearance retention ≥ 90% by axis ray-cast (D18).
- Viz: visual-vs-collision overlay PNG per converted model (mandatory), zoomed on
  functional clearances.

### 6.3 Protocol definitions (protocols.py) — actuate·observe·judge triples
All protocols split **criteria** (gates) from **observables** (recorded, flagged,
never silently promoted or discarded — D19/D22). Measurement names come from the
registry (V-13).

**P-HINGE (Easy anchor, use: lid open/close)**
- actuate: **follower force** (normal to lid face — D16; world-vertical has zero moment
  arm at 90°) ramped until θ ≥ θ_target + 15°, then immediately reverse-ramp to close
  (no zero-force hold; over-centre lids free-fall — D19).
- observe: θ(t), penetrations stratified by contact intent, pin drift; overtravel probe
  as a separate labeled segment (observable).
- judge: `θ_max ≥ 90°` / travel-defect penetration ≤ 0.2 mm / intended-contact
  (seat/stop) judged separately: settles closed (θ_final ≤ 5°), no bounce-open, pin
  retention held through events (D22) / multi-seed 4/5.

**P-SLIDE (Hard anchor sub, use: drawer extraction)**
- actuate: horizontal force ramp at the drawer front (or IR grip anchor); loaded
  condition = 0.5 kg dummy mass inside.
- observe: s(t), off-axis rotations, derail events; box slide (observable).
- judge: `s_max ≥ stroke (=300 mm)` / off-axis ≤ 3° / no derail or drop / back-drift
  after stop ≤ 5 mm.

**P-GEAR (Hard anchor sub, use: rotation→translation, Mode V-B)**
- actuate: velocity actuator on the pinion shaft, N = 3 revolutions.
- observe: rack (or drawer) displacement s(t), slip events (angle-displacement residual
  jumps), contact forces.
- judge: `|s/(θ·r_pitch) − 1| ≤ 5%` (emergent transmission ratio) / no slip/jam/tooth
  escape / sustained over 3 revolutions.

**P-FULL (Hard anchor integrated)**
- actuate: torque ramp on the knob (force-driven — full chain incl. friction & load).
- judge: k knob revolutions produce s ≥ 300 mm; all chain criteria pass simultaneously.

### 6.4 Execution conventions (runner.py)
- multi-seed: 5 seeds × 1 preset; **verdict = ≥4/5 pass**.
- timestep 0.5 ms default; on divergence, one automatic retry at 0.25 ms.
- divergence detection includes finite-but-absurd states (pin travel > 10× model
  extent, |qvel| > 1e3) — not just NaN.
- outputs: HUD mp4 per protocol (variant-explicit filenames; HUD burned from the SAME
  per-step series the verdict is built from), observation CSVs, verdict JSON
  `{criterion: {value, threshold, pass}}` + `{observables: {...}}`.

---

## 7. Visualization system (viz/) — "every task, every stage"

### 7.1 Artifact directory conventions
```
runs/<task_id>/<run_id>/          # pipeline runs (git-ignored)
├── ir/            # per-stage DesignPlan snapshots s1.json ... s6.json (diffable)
├── s1_functions.md   s2_behaviors.mmd   s3_pieces.md
├── s4_bindings.mmd   s4_rationale.md    s5_params.html
├── s6_parts/*.glb  s6_assembly.glb  s6_views_{front,top,right,iso}.png  s6_exploded.png
├── t0_report.html  t1_report.html
├── t2_conv_overlay.png  t2_*.mp4  t2_*.csv  t2_verdict.json
└── report.html    # single report binding everything (§7.6)

mN_<name>/                        # milestone snapshots (D-ONT-7)
├── out/           # reviewable artifacts for that milestone
└── REVIEW.md      # the human's single G-H entry point + approval checklist
```
Code and living data stay in unnumbered directories; numbered folders hold reviewable
snapshots only. **"Tests pass" without a REVIEW.md is an incomplete milestone.**

### 7.2 IR graphs (ir_graph.py)
- DesignPlan → mermaid (+ SVG when tooling allows; .mmd alone acceptable — VS Code
  previews it). Nodes: Function/Behavior/Element/PassiveFeature/Piece/Binding; phase
  colors (use=blue, assembly=orange, static=gray); imposes edges dashed; is_base pieces
  marked with a ground symbol.
- Stage-diff view: nodes added between s(n) and s(n+1) emphasized.

### 7.3 3D views (cad_view.py)
- **Live during development**: VS Code *OCP CAD Viewer* + `ocp_vscode.show()` behind a
  `--live` flag.
- **For the record**: ocp-tessellate → GLB; offscreen 4-view PNGs + exploded PNG
  (pieces offset 1.5× along binding axes).
- anchor overlay: `s6_anchors.png` — anchors as labeled colored points (the key
  Binding-debugging view).

### 7.4 Simulation video (sim_video.py)
- offscreen 640×480@60fps → mp4; HUD text burned per frame from the scored series
  (t, θ/s, pin drift, penetration, current verdict state). Camera presets: fixed iso +
  one close-up on the interface of interest. Variant-explicit filenames.

### 7.5 Verdict plots (plots.py)
- P-HINGE: θ(t) with the 90° threshold; P-SLIDE: s(t) + off-axis(t); P-GEAR: s vs θ
  scatter with the ideal slope r_pitch. All plots carry pass/fail badges and threshold
  shading.

### 7.6 Run report (report.py, jinja2)
- single `report.html`: verbatim command → per-stage decisions (with citations) → 3D →
  gate results → embedded videos → final verdict → design rationale sheet →
  **G-H manual approval checklist**.
- This report is the source of paper figures and the single venue for human review.

---

## 8. Anchor task walkthroughs (tasks/*.json = golden IRs)

### 8.1 Easy — snap-latched hinged box
- command: `"Design a small box whose lid opens and closes and latches shut. Plastic, for 3D printing."`
- expected golden IR (abridged):
```json
{
  "functions": [{"verb":"import/allow_access","object":"contents","qualifier":"repeated open/close"},
                 {"verb":"secure","object":"lid","qualifier":"hold closed"}],
  "behaviors": [
    {"id":"B1","phase":"use","motion":{"kind":"rotation","axis_hint":"horizontal_rear","range_value":90,"range_unit":"deg"},"realized_by":"E1","verified_by":"P-HINGE"},
    {"id":"B2","phase":"static","motion":{"kind":"fixed"},"realized_by":"E2"},
    {"id":"B3","phase":"assembly","motion":{"kind":"fixed"},"realized_by":"E2"},
    {"id":"B4","phase":"use","motion":{"kind":"fixed"},"imposed_by":"E2","_note":"latch must not interfere with the lid sweep (Tier0)"}],
  "pieces": [{"id":"P1","role":"base","template_ref":"box_shell","is_base":true},
              {"id":"P2","role":"lid","template_ref":"lid_panel"}],
  "elements": [{"id":"E1","card_ref":"pin_hinge","host_pieces":["P1","P2"]},
                {"id":"E2","card_ref":"snap_hook_cantilever","host_pieces":["P1","P2"]}],
  "bindings": [
    {"element_id":"E1","port":"axis","piece_id":"P1","anchor":"rear_top_edge","mate":"coincident_axis","offset_params":{"edge_margin_mm":15}},
    {"element_id":"E1","port":"mount_B","piece_id":"P2","anchor":"rear_edge_underside","mate":"flush_face"},
    {"element_id":"E2","port":"beam_root","piece_id":"P2","anchor":"front_edge_underside","mate":"on_face_uv","offset_params":{"u":0.5,"v":0.9}},
    {"element_id":"E2","port":"catch_window","piece_id":"P1","anchor":"front_wall_inner","mate":"offset_face"}]
}
```
- pass requirement: G1–G9 + P-HINGE + Tier1 latch checks (eps ≤ 4%, W_out/W_in ≥ 2).
- variant: + `stop_flange` PassiveFeature (rotation limit ~109°) — the M0 pair
  no-stop/stop is retro-expressed in tasks/ as schema stress tests.

### 8.2 Hard — rack-pinion drawer cabinet
- command: `"Design a desktop cabinet whose drawer slides out when you turn the knob. The drawer should extend about 300 mm."`
- golden IR skeleton: pieces = {cabinet_shell, drawer_tray, knob_shaft, rack_bar —
  integration into the drawer is legitimate LLM discretion, both answers golden};
  elements = {slide_rail ×2, rack_pinion}; behaviors = use:rot_to_trans
  (transmission {"mm_per_rev": π·m·z}) + use:translation (stroke 300) + assembly
  (shaft insertion path); PassiveFeature: drawer stop-tab (D-ONT-4 class).
- constraint chain (what ⑤ must solve; explicitly unit-tested):
  `drawer_w = cab_inner_w − 2(rail_w+cl)` / `L_rack ≥ 300 + πmz/4` /
  `axis_height = rack_pitchline + d/2` / `engagement ≥ 0.35·stroke`
- pass requirement: P-SLIDE + P-GEAR (V-B) + P-FULL.
- known hazard (D14): drawer-in-cabinet is flush-panel-in-flush-opening geometry —
  collision primitives of the moving piece must be inset (COLLISION_EPS) to avoid the
  degenerate flush-contact blow-up observed in M0.

---

## 9. Milestones (gate-based; order and definitions of done, not dates)

| M | Definition of done | Verified by | Status |
|---|---|---|---|
| M0 | hand-built hinged box passes STEP→MJCF→P-HINGE (no pipeline) | G-CONV + P-HINGE video | **DONE** (+ stretch: V-B, R1 retired, D14–D23) |
| M-S | snap-fit starter: full symbolic stack, no physics (SNAPFIT_STARTER doc) | G-S1 golden + T-S1 e2e + REVIEW.md | ontology portion DONE (m2_ontology); cards next |
| M1 | contact preset reconfirmed + gear pair standalone V-B | P-GEAR pass, preset values recorded here | **CLOSED (m1_gear, D-M1-1..7)**: R2 split — R2a RETIRED (involute conjugate, forward V-B sim-demonstrable ratio −0.50); R2b FROZEN/DEFERRED (module route exhausted m≤6; reversal backlash-crossing impact is a rigid-contact formulation limit, D1). Trapezoid DEAD. Hard-anchor gear verification downgraded to V-A + documented V-B gap. Preset UNTOUCHED (R5). Returning to main line (B-track: pin_hinge + stage-⑨ + Easy anchor) |
| M2 | ontology + validators + 4 cards implemented | V-01..V-13 unit tests, G3.1/3.2 | ontology DONE; cards partial |
| M3 | ⑤⑥ (symbolic) implemented: golden IR → CAD → Tier0/1 | both anchors G5–G8 | pending |
| M4 | ①–④ (LLM) implemented: command → IR | Easy anchor end-to-end once | pending |
| M5 | Hard anchor end-to-end + report.html complete | G1–G9 + G-H approval | pending |
| M6 | benchmark variants (15±5) + baseline LLM evaluation | results table draft | pending |

> Original strategy held: retire risk by experiment first (M0), deterministic parts
> before LLM parts, benchmark last. Numbered milestone folders (mN_*) snapshot each.

## 10. Test strategy
- unit: all validators (one violation case each); card formulas (handbook worked
  examples as goldens — Bayer p.16 Example I); ⑤ constraint chains (the 4 Hard-anchor
  equalities); ⑥ determinism (hash).
- golden: `tasks/*.json` → full-pipeline artifact/verdict regression.
- LLM stages: field-level agreement vs golden IRs (`tests/eval_llm_stages.py`) —
  regression detection across model/prompt changes.

## 11. Risk register
| R | Risk | Mitigation | Status |
|---|---|---|---|
| R1 | STEP→MJCF mangles grooves/teeth | card collision_hint (validated), CoACD rejected with data, SDF ruled out | **RETIRED** (D18) |
| R2a | gear GEOMETRY: does a tooth profile survive hint-approximation and mesh conjugately? | involute wedge decomposition (validated); trapezoidal rejected; D21 forbids sdf.gear | **RETIRED (M1/D-M1-2)**: involute proves conjugate action (ratio error −0.5%); trapezoidal DEAD (contact-jump evidence, `l1_contact_jump.png`) |
| R2b | gear SIMULATION: is bidirectional tooth-contact meshing stable in the rigid rig? | frozen as a known limitation; preset_v2 deferred. Forward V-B meshing IS demonstrable (frozen/5); the gap is the backlash-crossing/reversal IMPACT | **FROZEN / DEFERRED (M1/D-M1-7)**: module route exhausted (m≤6, all 0/5) and no preset param helps; D1 isolates the killer as the reversal backlash-crossing impact (formulation, not actuation — a 0.5 s dwell does not help). Hard-anchor P-GEAR **downgraded to V-A** with the V-B gap documented. Preset UNTOUCHED (R5). Revisit only via a versioned preset_v2 or a contact-representation change (pitch-cylinder proxy) — a future G-H item |
| R3 | MUSE v2 ships physics-aware evaluation first | element realization + force-driven verification is our identity; speed on M-S/M3 | open |
| R4 | LLM structured output can't fill the ontology | validator-error-feedback retries; golden IRs as few-shots | open |
| R5 | contact-parameter tuning contaminates results | ONE frozen preset + multi-seed verdicts; global change ⇒ rerun all regressions | enforced |

## 12. Rules for updating this document
- If code and spec diverge, **update this document first**, then link the commit.
- Contact preset values (§6.2), template anchor lists, and card parameter defaults are
  recorded here as they are finalized (M1/M2).
- Amendments and experiment-driven decisions accumulate in DECISIONS_LOG.md (D13+);
  where they conflict with this body, the log wins and this body is edited to match at
  the next revision bump.

**Changelog (this revision):** added §13 (Element D-track, six stages + definition-of-done,
incl. the S5 fixture t0 gate) — formalizes the process m10/m11 (D-D-1/-2) and m19/m20/m21
(D-M19-1/D-M20-1/D-M21-1) already practiced; recorded as **D-M21-4**. The t0 gate is NEW
(it closes a gap the m21 video review exposed: no prior stage checked compiled-fixture
interference — the m19/m20/m21 REVIEWs contained zero t0 evidence).

## 13. Element D-track (per-element milestone shape)

A new mechanical element earns admission to the library by passing a **six-stage D-track**.
Each stage has a **definition-of-done (DoD)**; no stage may be skipped, and a stage's DoD must
be evidenced (a test count, a CLEAN validation, a verdict, a reproduction) before the next
begins. This formalizes m10 (`slide_rail`, D-D-1), m11 (`rack_pinion`, D-D-2), m19
(`lead_screw`), m20 (`coupling`), m21 (`universal_joint`).

- **S1 — Card.** Complete the element card to the library standard. **DoD:** every param resolves
  (zero None — the m18-audit class of bug); ports declared; a CITED rule chain (handbook §, e.g.
  Shigley/P&B) reproduced against a HAND-WORKED numeric anchor in the test docstring ("if this
  fails the CODE is wrong, not the arithmetic"); `imposes` (V-08); `carve` producing ONE solid
  (the D-D-1 lesson); `collision_hint` source-stamped (D-M8-4); `verification()` returning the
  element's P-protocol with criteria split from observables. Card test green.
- **S2 — Fixture templates.** The minimal host templates (reuse existing where possible, STATE the
  choice). **DoD:** each one solid; anchors declared; `is_base` per D23; collision hints self-sourced.
- **S3 — Golden IR.** `tasks/<elem>_fixture.json` by construction (functions → behaviours → pieces →
  element + bindings → protocol). **DoD:** validator-CLEAN; compiles to the expected one-solid parts;
  any expressiveness gap is a DRAFT decision row, NOT a silent patch.
- **S4 — Physics (V-A).** The element's declared-pair/kinematic rig. **DoD:** V-A ≥4/5 seeds; guard
  trio + G-CONV + all_parts_retained; the criterion is NON-TAUTOLOGICAL (measured vs an INDEPENDENT
  formula, or an emergent property); a **discrimination probe** (break the mechanism / null the
  parameter → the property must vanish); contact-free joint rigs use the D-M19-2 clock (dt=1e-4,
  R5 untouched); video per the standing rule (D-M20: an asymmetric marker per moving body, the HUD
  primary-DoF counter, the FULL criterion window). V-B / emergent_check decided honestly per the
  element's contact class (argued, not copied).
- **S5 — Numeric reproduction + FIXTURE t0 GATE.** **DoD (reproduction):** the rule chain, the
  measured-vs-formula numbers, and a t1 COMPILE_DRIFT re-measure (≤0.05 mm) reproduced free/local.
  **DoD (t0 gate, NEW — D-M21-4):** a **pairwise interference/clearance table on the compiled
  fixture** at the initial pose AND swept poses through the mechanism's motion, judged **per D22**
  (contact-intent stratification): *intended* contact pairs (e.g. a trunnion in a yoke bore, teeth
  in mesh) report **positive clearance**; every *unintended* inter-body pair reports **zero
  penetration**. **No verdict ships over geometry that failed the table.** A failure is a carve/geometry
  bug: fix the geometry, recompile, re-run the table CLEAN, and re-stamp the S4 verdict's
  `compile_hash` on the fixed geometry (declared-joint V-A numbers are expected unchanged).
- **S6 — REVIEW + decisions + STATUS.** **DoD:** `mN_<elem>/REVIEW.md` (outcome first, per-stage
  evidence with paths, plots/videos inline, the t0 table); the D-track decision row (CONFIRMED) +
  any DRAFT rows; the STATUS milestone row; full suite green (report the count). Commit per stage.
