# ASSY Ver1 — Critical Evidence Audit

> **Ver1 is not the target.**
>
> This document audits ASSY_Ver1.0 as *partial engineering evidence produced under a
> narrower and more constrained system*. Nothing here licenses copying its code,
> architecture, mechanism cards, templates, prompts, CAD construction logic, or
> benchmark assumptions.
>
> The output of the audit is two-sided: what ASSY-Next must **recover**, and what it
> must explicitly **surpass** — followed by an Engineering Output Quality Framework
> that is independent of both Ver1 and the current benchmarks.

**Source examined:** `/home/ftk3187/github/ASSY_Ver1.0` (110 MB, 28 milestone folders,
`STATUS.md`, `MECHSYNTH_SPEC_v0.1.md` §14, `DECISIONS_LOG.md`, `ASSUMPTIONS.md`, 19
element cards, per-milestone `REVIEW.md`, verdict JSON, and physics artifacts).

---

# 1. The headline finding

Ver1 is best understood as **a strong embodiment-*verification* system attached to a
human-supplied embodiment-*configuration* step.**

Its own specification says so plainly. Stage T3-ARCH of `MECHSYNTH_SPEC_v0.1.md` §14:

> "the element cards carry FORMULA knowledge (Bayer forces, Shigley torque) but no
> CONFIGURATION knowledge — the Pahl & Beitz *embodiment* layer (how parts are arranged
> into a working product) is absent from the library. Until a configuration-knowledge
> milestone lands … T3-ARCH is the **human/reviewer-supplied stopgap**: the archetype is
> stated and cited, **not derived**."

And the M24 IR-truth table:

> "**Most design decisions land in template params or hardcoded geometry, NOT IR fields**
> — the schema carries element CHOICE, not assembly DESIGN."

Everything below follows from that split. Where Ver1 verified an embodiment it had been
given, the work is excellent and worth recovering in full. Where Ver1 appears to have
*designed* a product, the configuration almost always arrived from outside the system.

---

# 2. Per-result audit

Each result is separated into **A** capability genuinely demonstrated · **B** hidden prior
knowledge · **C** remaining limitations · **D** evidence value for ASSY-Next.

Evidence-value classes: `PRESERVE` general engineering principle · `FAILURE-MODE` useful
failure to keep detecting · `METHOD` useful evaluation method · `NARROW` implementation
technique not to inherit · `OPEN` unresolved question.

---

## 2.1 Latching storage box (M8 `anchor_easy`)

The multi-element benchmark: box + lid + hardware pin + snap latch, compiled and verified
t0 → t1 → t2.

**A · Genuinely demonstrated**

- A multi-element assembly compiled from a validated IR and driven through geometric,
  re-measurement, and physics tiers without a human in the loop *at execution time*.
- Two verification modes with genuinely different authority: **V-A** (declared kinematic
  joint) and **V-B** (contact-only — the DoF must *emerge* from geometry). V-A 5/5 and
  V-B 5/5 on the stop variant.
- An element-provided **hardware pin** as a first-class piece, not a fused feature.
- **The retraction.** An earlier V-B PASS was withdrawn because it rested on a stop that
  existed only in the contact model — "no solid in the compiled STEP and no entity in the
  IR". The correct answer was the one previously treated as failure: θmax 272°, the
  over-centre lid folds flat. The rule is now mechanized: unsourced collision geometry is
  a **build error**, with the retracted primitive kept as a regression test.
- **A design requirement discovered from physics.** Honest V-B proved "opens ≥90° AND
  returns closed" is physically unsatisfiable for an over-centre lid without a stop. The
  stop entered the benchmark because the system's own physics demanded it.
- A deliberately kept **EXPECTED_FAIL** golden (`anchor_easy_nostop`, V-B 1/5) — a
  negative control carried in the verdict rather than deleted.

**B · Hidden prior knowledge**

- Topology was given: box + lid + pin + latch, with the hinge axis and latch location
  fixed by the golden IR (`tasks/anchor_easy.json`), authored by construction.
- `pin_hinge` and `stop_flange` cards prescribe the embodiment (interleaved knuckles,
  n ∈ {3,5}, bore = pin + clearance, chamfer rule) — lifted from M0's hand-built hinge.
- Host templates (`box_shell`, `lid_panel`) are hand-authored, with anchors pre-labelled.
- The choice *that a stop is needed* was discovered by physics; the choice *that the stop
  is a `stop_flange` at that location* came from the card and template library.

**C · Limitations**

- All-box geometry with a single revolute DoF; no structural sizing of the box itself.
- One material (PETG), one process implied; no material or process alternatives explored.
- No product-level reasoning about use, service access, or manufacture beyond printability.

**D · Evidence value**

| finding | class |
|---|---|
| Geometry-emergent DoF (V-B) as a separate, higher bar than declared-joint (V-A) | `PRESERVE` |
| Unsourced collision geometry must be a build error, not a modelling convenience | `PRESERVE` |
| "A declared range silently substituting for a physical part" as a recurring trap | `FAILURE-MODE` |
| Negative controls (`EXPECTED_FAIL` goldens) kept as first-class artifacts | `METHOD` |
| Card-prescribed hinge embodiment | `NARROW` |
| Where should configuration knowledge live, if not in cards? | `OPEN` |

---

## 2.2 Pin hinge (M0 → M8)

**A · Genuinely demonstrated**

- STEP → mesh → MJCF with the bore surviving convex decomposition (the ring-of-wedges
  collision hint retained 128% of the bore where CoACD swallowed it) — a real,
  non-obvious geometry-to-physics fidelity result.
- An explicit **hinge embodiment**: interleaved knuckle stack, clearance bore, separate
  pin, lid-edge chamfer — a hinge that could be printed, not a joint annotation.
- A **frozen contact preset (R5)** reused unchanged across every downstream milestone, so
  results are comparable rather than each individually tuned.
- M0's own warning, which became the framework's most useful sentence:
  *"V-A hid this — MuJoCo's joint `range` acted as a stop the part does not physically have."*

**B · Hidden prior knowledge**

- The hinge was hand-built first, then "lifted into card knowledge". The card formalizes a
  known-good embodiment; it does not synthesize one.
- Knuckle count restricted to {3,5}; wall, protrusion, and clearance are constants in the
  card.
- The card cannot emit its own pin as a `Piece` — the docstring records that "the caller
  must currently declare it as a plan-level Piece **by hand**." Manual intervention inside
  the supposedly automatic path.

**C · Limitations**

- Cylindrical pin-in-bore only; no bushing/bearing selection, no wear or life reasoning.
- Clearance is a single print-clearance constant, not a fit class chosen from duty.
- The pin is rigid; no press-fit or retention analysis in the loop.

**D · Evidence value**

| finding | class |
|---|---|
| A joint must have a manufacturable physical carrier, not just a DOF | `PRESERVE` |
| Collision-geometry fidelity is a real risk between CAD and simulation | `PRESERVE` |
| Frozen, shared contact preset so results are comparable across experiments | `METHOD` |
| Hand-built-then-formalized card as the source of embodiment | `NARROW` |
| Fixed knuckle counts and constant clearances | `NARROW` |
| Manual piece declaration inside an automated pipeline | `FAILURE-MODE` |

---

## 2.3 Latch physics (M23)

**A · Genuinely demonstrated**

- A complete **CLOSE → HOLD → RELEASE** sequence on one continuous run, with the click
  logged as an event and the pop visible.
- The breakaway threshold is **SOURCED, not tuned**: `solve_h → 2.09 mm ; P_deflect →
  17.67 N ; W_sep(α_out = 45°, µ = 0.30) = 32.81 N`, with the derivation chain printed in
  the verdict.
- **Bidirectional discrimination**: a 0.5·W_out pull (16.4 N) holds with 0.45 mm creep; a
  1.5·W_out pull (49.2 N) releases to the rail stop. If the threshold were invented, one
  of the two would fail.
- Hand-releasability argued from the self-lock angle: `atan(1/µ) = 73.3° > 45°`.

**B · Hidden prior knowledge**

- **The latch is not simulated as a latch.** It is a *declared rigid equality* pinning the
  drawer at s = 0 that activates at engagement; the elastic hook is never in contact.
- The engagement position is a template parameter (`bump_x = barb_x`), recorded in the
  IR-truth table as **hardcode** with the debt "no scalar snap-position".
- Cantilever geometry and the α_in/α_out angle pair come from the Bayer-derived card.

**C · Limitations**

- Compliant-beam engagement is **Tier-3 deferred** — the elastic deflection is
  formula-only. The physics run cannot contradict the formula, because the formula *is*
  the model. This is a genuinely honest construction, but it is not independent evidence.
- No cycling, creep, or fatigue; PLA/PETG creep under sustained deflection is unaddressed.
- Material constants are declared stand-ins (see §2.9).

**D · Evidence value**

| finding | class |
|---|---|
| Thresholds must be sourced from a cited relation, with the chain printed | `PRESERVE` |
| Bidirectional discrimination (holds below / releases above) as the real test | `METHOD` |
| Full behavioural sequence on one continuous run, not per-phase snapshots | `METHOD` |
| Declaring plainly that a phenomenon is modelled by substitution, not simulated | `PRESERVE` |
| A rigid equality standing in for a compliant element | `NARROW` |
| How is a compliant element verified *independently* of the formula that sized it? | `OPEN` |

> **Direct relevance to ASSY-Next.** Our current BM-001 path splits this into two
> backends — closed-form for the compliant element, rigid-body for motion and contact —
> and refuses `pass` unless both have valid evidence. Ver1 collapsed both into one MuJoCo
> rig with an imposed threshold. The split is an improvement, but it inherits the same
> unresolved question: neither system verifies beam compliance against anything but its
> own formula.

---

## 2.4 Gear assemblies (M1, M11, M13, M17)

**A · Genuinely demonstrated**

- **R2a retired honestly**: a generated involute pair is conjugate, transmission ratio to
  −0.5%. Real geometric verification of a real gear property.
- **R2b characterized, not hidden**: the same conjugate pair diverges to **2.09e16 N at
  dt = 5e-4** but rolls at **0.605 N at dt/25** — sixteen orders of magnitude between two
  runs of identical geometry.
- **M17 answered its own question NO.** An SDF contact formulation — even the zero-facet
  analytic best case, under both rigid and soft contact — still diverges at the frozen
  timestep. The milestone explicitly claims "**no preset_v2, no V-B pass**".
- dt/25 shown to be **metastable**, not a fix: it survives ~5.6× longer, then also blows
  up (4.5e17 N at 1.33 s). A weaker system would have shipped dt/25 as the solution.
- **M13's negative result is the best engineering in Ver1**: P-HOLD 0/5 FAIL because a
  plain rack-and-pinion is not self-locking (µ·W·r_p ≪ W·r_p); the released platform
  back-drives 62 mm. The conclusion — *a lift REQUIRES a holding brake* — was discovered
  from physics, then answered with a `pawl_detent` that flips P-HOLD 0/5 → 5/5
  (back-drive 3.4 mm).

**B · Hidden prior knowledge**

- Module bounds restricted to {5, 6} with the stated reason "contact-sim stability" — a
  *simulator* constraint presented inside the design vocabulary.
- Tooth count, pressure angle, and the involute construction are card knowledge reused
  from M1; the pinion carve is literally "reuses M1's involute".
- The brake is a card (`pawl_detent`) that already existed as "snap_hook's cousin"; the
  system selected from a library, it did not synthesize a holding principle.

**C · Limitations**

- **Curved driving contact was never verified.** Every gear result is V-A (declared
  kinematic pair) with V-B named-deferred. The core physics of a gear is outside the
  demonstrated envelope.
- Bending/contact stress, face width, backlash under load, and lubrication are absent.
- The stability limit leaks upward into design freedom: the design space was narrowed to
  keep the simulator alive.

**D · Evidence value**

| finding | class |
|---|---|
| A negative physics result treated as a design finding, not a bug to tune away | `PRESERVE` |
| Refusing to claim a pass when the mechanism's core physics is unverified | `PRESERVE` |
| Naming a deferred verification gap in the verdict, machine-checkable (`shape_assert`) | `METHOD` |
| Reproducing a known failure to the digit before claiming any improvement | `METHOD` |
| Distinguishing "delayed" from "fixed" (dt/25 metastability) | `METHOD` |
| Restricting the design vocabulary to protect the simulator | `NARROW` |
| How should ASSY-Next verify curved driving contact at all? | `OPEN` |

---

## 2.5 Universal joint (M21)

**A · Genuinely demonstrated**

- The strongest verification in Ver1. The Cardan velocity fluctuation
  `ω_out/ω_in = cos β / (1 − sin²β sin²θ)` was verified as an **emergent** result: the rig
  is a serial chain with one tip connection and **no** `polycoef = cos β` imposed.
- Measured overlay to **0.08%**, band `[0.866, 1.155]` exact, and — the part that matters —
  **phase predicted from geometry (90°) matched to 0.03°**. Amplitude *and* phase.
- **Discrimination**: β = 0 flattens the band to `[0.9993, 1.0]`.
- `emergent_check` was **argued deferred, not copied** — cross-trunnion bearing contact is
  idealized, and the review says so and explains why it is earnable and not R2b-class.

**B · Hidden prior knowledge**

- Yoke/cross topology is card knowledge; β arrives as a command constraint, and M21's own
  DRAFT D-M21-3 records that `axis_relationship` carries no scalar angle — so β lives
  outside the schema.
- Templates (`shaft_carrier_in`, `shaft_carrier_out_angled`) are hand-authored per case.

**C · Limitations**

- Trunnion bearing contact idealized; no needle bearings, no lubrication, no life.
- No torque capacity, no yoke strength, no phasing of a second joint (parked as a DRAFT).
- Single-joint only: the constant-velocity double-Cardan case is future work.

**D · Evidence value**

| finding | class |
|---|---|
| Verify an **emergent law** rather than a value the model was told to produce | `PRESERVE` |
| Match amplitude *and phase*, and predict phase from geometry beforehand | `METHOD` |
| Structural discrimination (β = 0 collapses the effect) as a built-in control | `METHOD` |
| Arguing a deferral case-by-case instead of inheriting a blanket exclusion | `PRESERVE` |
| Hand-authored per-case templates | `NARROW` |

> This is the single result ASSY-Next should treat as the quality bar for *dynamic*
> verification: a law the model was not told, matched in amplitude and phase, with a
> structural control that collapses it.

---

## 2.6 Element expansion (M18)

**A · Genuinely demonstrated**

- A **7-axis element taxonomy** grounded in Pahl & Beitz with per-axis citations: working
  motion (type × nature), axis relationship, connection principle, self-locking, and an
  `emergent_check` struct carrying *deferred + why + risk*.
- A third card category (`ConnectionCard`) recognising that fastening is a *property*
  (form / force / material), orthogonal to the object.
- A **morphological matrix** (Zwicky) as the selection surface: self_lock → lead_screw,
  intersecting → universal_joint, form → dowel_pin.
- `self_locking` promoted to a first-class field — a physics-discovered property (M13/M19)
  becoming schema.
- A validator that **refuses** what cannot be verified: V-17 rejects `compliance =
  compliant` with a "P-SPRING" message.

**B · Hidden prior knowledge**

- The matrix maps a *requirement token* to a *specific card*. That is a lookup table over
  a closed library, not mechanism synthesis. Eight cards were added, all pre-chosen.
- No axis expresses configuration, arrangement, or spatial relationship.

**C · Limitations**

- Axis 6 (compliance) is **RESERVED — field exists, value fixed**; axis 7 (kinematic DOF)
  is a note with no field.
- "Schema/ontology only — NO new physics"; none of the eight Tier-1 cards has
  curved-contact verification.
- The taxonomy classifies *elements*. There is no taxonomy of *products*, *architectures*,
  or *embodiments* — the acknowledged D-M24-4 gap.

**D · Evidence value**

| finding | class |
|---|---|
| Classifying elements along cited, orthogonal engineering axes | `PRESERVE` |
| `emergent_check` carrying deferred + why + risk as structured data | `PRESERVE` |
| A validator that refuses to accept what the system cannot verify | `PRESERVE` |
| Promoting a physics-discovered property to first-class schema | `METHOD` |
| Requirement-token → card lookup presented as selection | `NARROW` |
| What is the equivalent taxonomy for *configurations*, not elements? | `OPEN` |

---

## 2.7 Design closure (M24)

**A · Genuinely demonstrated**

The three T3 rules are the most transferable engineering content in Ver1:

- **(a) Everything on film is a compiled PIECE** — no MJCF world-geometry standing in for
  parts. A cabinet is a piece; frames, guides, and enclosures are pieces.
- **(b) Every mating dimension DERIVES from its mate** plus the card's fit formula, and a
  **FIT SCHEDULE** lists every interface as `{nominal, clearance, source}`. *Dimensions
  picked independently of their mate = failure.*
- **(c) Every declared joint names its PHYSICAL CARRIER.** *A joint with no carrier =
  failure.* The audit's key catch was exactly this: the platform slide had no
  anti-rotation carrier until guide columns were added.
- The fit schedule is **re-measured from the compiled solids**: max COMPILE_DRIFT
  **0.000 mm**, with P1×P2 = −0.350 reproducing the 0.35 mm column fit exactly.
- A **physics-identical assert**: the bare declared-joint rig and the compiled-mesh rig
  produce byte-identical criteria — so swapping in real geometry provably changed nothing.
- **T3c end-stops**: travel limits became *parts* (a base landing and a thread-runout
  shoulder) while the hold stayed *physics*.

**B · Hidden prior knowledge**

- **T3-ARCH is explicitly a human stopgap** (§1). The archetype — "bottom-clip organizer
  drawer", the mating-face map, the closed-state section — is supplied and cited, not
  derived.
- The IR-truth table lists panel-on-face landing, bump position, and the zero-protrusion
  rule as **hardcode geometry**, each with a named schema debt.
- Fit chains start from "3 free inputs" chosen by the author.

**C · Limitations**

- Design closure is *checked*, not *achieved*, by the system: it verifies that a
  human-supplied configuration is internally consistent.
- Only two assemblies, both box-like, both single-DOF.
- No alternatives are generated or compared; there is one archetype per task.

**D · Evidence value**

| finding | class |
|---|---|
| Every joint must name a physical carrier | `PRESERVE` |
| Every mating dimension derives from its mate; a fit schedule makes this auditable | `PRESERVE` |
| Everything visible in simulation must be a real compiled part | `PRESERVE` |
| Re-measuring fits from compiled solids (COMPILE_DRIFT) as a CAD/sim consistency gate | `METHOD` |
| Physics-identical assert between abstract and meshed rigs | `METHOD` |
| Limits are parts; holds are physics | `PRESERVE` |
| Human-supplied archetype | `NARROW` — and the central thing to surpass |
| Design decisions living in template params rather than the IR | `FAILURE-MODE` |

---

## 2.8 Contact-layer work (M25)

**A · Genuinely demonstrated**

- The **①/②/③ contact doctrine**, with the classification printed per pair and a reason
  given for every exclusion:
  - **① driving curved contact** (gear teeth, thread flanks, cams) → R2b, excluded;
  - **② landings / stops / retention** (flat, rigid) → **verified by real contact**;
  - **③ elastic members** (snap beams, springs) → formula-only (Bayer).
- Where a class-② pair carries a limit, the declared joint range is **widened
  (`limited = false`) so the PART does the stopping** — the direct institutional answer to
  M0's "joint range acted as a stop the part does not have".
- Results: overcranked screw lift stops at **40.02 mm** on the collar; base landing at
  **−0.52 mm**; drawer panel lands on the face frame at **−0.20 mm**.
- The runner is element-agnostic; the classification is **data**, and judgement uses only
  IR-declared criteria plus generic guards.

**B · Hidden prior knowledge**

- The contact schedule (which pairs mate, and their class) is authored data derived from
  the human-supplied fit schedule.
- Only two assemblies exercise it.

**C · Limitations**

- The doctrine is honest about excluding ① and ③ — but ① and ③ are precisely the physics
  of gears, threads, and snaps, i.e. most of Ver1's own mechanisms. What is contact-verified
  is the *static furniture* of each design.
- Everything runs on one frozen preset in one simulator; portability is untested.

**D · Evidence value**

| finding | class |
|---|---|
| Classify every mating pair and print the class with a reason | `PRESERVE` |
| A limit must be carried by a part; widen the declared range to prove it | `PRESERVE` |
| Excluding what cannot be trusted, visibly, rather than silently including it | `PRESERVE` |
| Element-agnostic runner with classification as data | `METHOD` |
| Single frozen preset in a single simulator | `NARROW` |
| How do we verify ① and ③ at all? | `OPEN` |

---

## 2.9 Cross-cutting: sourcing, sizing, and declared ignorance

**A · Genuinely demonstrated**

- **Requirement-driven sizing** (M26): the same command at 1 / 5 / 20 kg produces
  `d_major` = 5.0 → 6.42 → 12.83 mm, each compiled, gated, and re-verified at its own
  load — with the min-bound governing at 1 kg and shear above.
- **Non-tautology discipline** (M19, M20). A lead screw's hold is sourced
  (`T_friction = µ·W·d_mean/2 = 0.00515 N·m ≥ 0.00156 N·m` back-drive) and then *probed*:
  a sub-back-drive friction slips **18.4 mm** against the sourced case's **0.079 mm** —
  a 233× separation proving the hold is friction, not a solver artifact. A coupling is
  broken to show input 6 rev → output 0 rev.
- **A permanent assumption register.** `ASSUMPTIONS.md` states that PETG constants are
  stand-ins — `E_s ≈ 0.75·E`, `ε_perm = 0.04` borrowed from PC, `µ = 0.35` extrapolated —
  and that the row "leaves only when its gate closes, never by being quietly dropped."

**C · Limitations**

- Sizing is per-card and one-directional; the review itself records this as V1, with the
  general inverse-solver parked as a DRAFT.
- Material data is thin and admittedly unsourced for the material actually used.

**D · Evidence value**

| finding | class |
|---|---|
| Deliberately break the mechanism to prove the measurement is not tautological | `METHOD` — **the single most valuable method in Ver1** |
| Sweep the requirement and show the design *changes* | `METHOD` |
| A permanent, append-only assumption register with explicit retirement gates | `PRESERVE` |
| Per-card, one-directional sizing | `NARROW` |

---

# 3. What ASSY-Next must recover from Ver1

Ordered by how much is currently missing from ASSY-Next.

| # | To recover | Ver1 evidence |
|---|---|---|
| R1 | **Every declared joint names a physical carrier; a joint without one is a failure.** | M24 T3(c); the missing anti-rotation carrier |
| R2 | **Every mating dimension derives from its mate**, recorded in an auditable fit schedule with sources. | M24 T3(b) |
| R3 | **Everything visible in simulation is a compiled part** — no world-geometry stand-ins. | M24 T3(a); the M8 retraction |
| R4 | **Limits are parts; holds are physics.** Widen the declared range and let the part stop it. | M25; M24 T3c |
| R5 | **Non-tautology probes.** Break the mechanism and show the measurement collapses. | M19 (233×), M20 (6 rev → 0), M21 (β = 0) |
| R6 | **Verify emergent laws**, matched in amplitude *and* phase, not values the model was given. | M21 (0.08%, 0.03°) |
| R7 | **Sourced thresholds with the derivation chain printed in the verdict.** | M23 (Bayer W_out = 32.81 N) |
| R8 | **CAD/simulation consistency measured, not assumed** — re-measure fits from compiled solids; assert physics-identical between abstract and meshed rigs. | M24 (COMPILE_DRIFT 0.000 mm) |
| R9 | **Classify every contact pair and print the class with a reason for each exclusion.** | M25 ①/②/③ |
| R10 | **Honest negative results as findings**, including retractions and kept `EXPECTED_FAIL` controls. | M8, M13, M17 |
| R11 | **A permanent assumption register** with explicit retirement gates. | `ASSUMPTIONS.md` |
| R12 | **Refuse to claim a pass when the mechanism's core physics is unverified.** | M11/M17 V-B named-deferred |

---

# 4. What ASSY-Next must explicitly surpass

| # | To surpass | Where Ver1 falls short |
|---|---|---|
| S1 | **Human-supplied configuration.** The archetype, mating-face map, and closed-state section must be *derived*, not stated. | T3-ARCH is a declared human stopgap |
| S2 | **Design decisions living outside the schema.** Landings, engagement positions, and envelope rules were hardcode. | M24 IR-truth table; D-IR-EXPR-1 |
| S3 | **Mechanism-card dependence.** Selection was a lookup over a closed library of 19 hand-authored cards. | M18 morphological matrix |
| S4 | **Known-topology dependence.** Golden IRs authored by construction; the LLM chose from a narrowed candidate set. | M9 "KG narrowing (what the LLM was allowed to pick from)" |
| S5 | **Simple-shape limitation.** Boxes, cylinders, one involute profile; "all-boxes" stated in the slide-rail card. | M10, M12 templates |
| S6 | **Simulator coupling.** One frozen preset, one engine; module bounds narrowed *for contact-sim stability*. | M11 selection notes; R5 preset |
| S7 | **Unverified core physics.** Curved driving contact (①) and elastic members (③) — the physics of gears, threads, and snaps — never verified. | M17, M25 |
| S8 | **Thin material/process reasoning.** One material with admittedly borrowed constants; process = FDM printability. | `ASSUMPTIONS.md` A-PETG-1 |
| S9 | **No alternatives.** One archetype per task; no comparison, no trade study, no rejected-candidate record. | M24 tasks |
| S10 | **Scale.** Largest assembly ≈ 6 pieces, single-DOF. No evidence for dense multi-part systems. | M22, M24, M27 |
| S11 | **Manual intervention inside the automated path.** Cards that cannot emit their own pieces. | `pin_hinge.py` third-piece wall |
| S12 | **Uncertainty handling.** Deferrals are named but not quantified; no tolerance-driven confidence on any result. | `emergent_check` |

---

# 5. Engineering Output Quality Framework (provisional)

Independent of Ver1 and of any current benchmark. Ver1 examples are used **only to
illustrate** each dimension — they are not the standard.

Each dimension has four levels:

**L0 absent** · **L1 asserted** (claimed, unsupported) · **L2 derived** (follows from
stated inputs by a cited rule) · **L3 verified** (independent evidence that could have
falsified it).

A product's score is the **vector**, never a single number, and any L0 or L1 on a
functional dimension blocks a completeness claim.

---

### D1 · Functional completeness
Every required function has a realizing mechanism; every mechanism traces to a function.
*L3 requires: measured behaviour satisfying each functional requirement.*
> Ver1 at L3 for "opens and stays closed" (M8), L0 for anything the command did not name.

### D2 · Mechanism completeness
Motion chain closed from input to output; all DOFs accounted; holding/locking behaviour
explicit.
*L3 requires: the chain measured end-to-end, not per-element and inferred.*
> M13 is the model: P-HOLD 0/5 exposed a missing holding function no per-element check saw.

### D3 · Physical embodiment
Every functional entity is a manufacturable solid with real geometry — knuckles, bosses,
columns, flanges. Nothing exists only as an annotation, a joint, or a contact primitive.
*L3 requires: the compiled solid is what simulation and manufacture both consume.*
> The M8 retraction is the canonical L1-masquerading-as-L3.

### D4 · Spatial coherence
Parts occupy a consistent space: no interpenetration in any pose, declared clearances
everywhere, and reserved volumes (access, sweep, service) respected.
*L3 requires: swept over the full motion domain, not sampled at extremes.*

### D5 · Support and load-path closure
Every applied force reaches ground through sized material; every rotating or translating
body is located and retained.
*L3 requires: reactions computed and members sized against a stated allowable.*
> Ver1 L2 at best: carriers are present and named, but not sized against stress.

### D6 · Motion completeness
Axis, range, limits, and the carrier of each limit are defined; end-stops are parts.
*L3 requires: motion driven to and past its limits, with the part doing the stopping.*
> M25 at L3 — overcrank stopped by the collar at 40.02 mm.

### D7 · Contact and interface completeness
Every mating pair is classified, given a fit, and either verified or explicitly excluded
with a reason.
*L3 requires: contact verified for the class; exclusions named, not silent.*
> M25's ①/②/③ map is the right shape; ① and ③ sit at L1.

### D8 · Assembly feasibility
A valid assembly order exists; every part is insertable; tools and hands reach; the product
can be taken apart for service where required.
*L3 requires: insertion simulated or geometrically proven, not asserted.*
> Ver1 L1 — assembly order is implied by the archetype, never demonstrated.

### D9 · Manufacturing feasibility
Process bound per part; process rules (wall, draft, overhang, tool reach, minimum feature)
satisfied; build orientation chosen and justified.
*L3 requires: rules checked against the actual solid.*
> Ver1 L2 for FDM clearance; L0 for orientation, supports, and anisotropy.

### D10 · Material and process justification
Material chosen against duty with cited properties; incompatibilities detected; borrowed or
estimated constants declared.
*L3 requires: properties from primary data for the material actually used.*
> Ver1 L1 with an exemplary declaration — `ASSUMPTIONS.md` A-PETG-1 is how L1 should be reported.

### D11 · Force and strength evidence
Loads derived from duty; stresses and deflections checked against allowables with margins;
failure modes identified.
*L3 requires: margins stated per critical member.*
> Ver1 L2 on the elements it sized (M26 shear-driven `d_major`), L0 on housings and carriers.

### D12 · CAD/simulation consistency
The simulated model and the manufacturable model are provably the same object.
*L3 requires: a measured drift and an identity assert, not an assumption.*
> M24 at L3 — COMPILE_DRIFT 0.000 mm plus the physics-identical assert. **Ver1's best dimension.**

### D13 · Traceability
Every dimension, threshold, and decision names its source: requirement, rule, or measurement.
*L3 requires: the derivation chain machine-readable and printed with the result.*
> M23's printed Bayer chain is L3 for the threshold; the IR-truth table shows L0 for configuration.

### D14 · Uncertainty and unresolved-risk reporting
Assumptions, deferrals, and validity domains are explicit; results outside a method's
validity domain are refused, not reported.
*L3 requires: quantified confidence or a stated bound, and automatic refusal outside it.*
> Ver1 L2 — deferrals are named and structured (`emergent_check`) but never quantified.

### D15 · Scalability beyond simple geometry
The result holds for freeform surfaces, dense multi-part assemblies, and multi-DOF systems.
*L3 requires: demonstrated on a product materially more complex than the benchmark.*
> Ver1 L0 — boxes, cylinders, one involute, ≤ 6 pieces, single-DOF.

---

## 5.1 Using the framework

1. **Score the vector, not a total.** A design at L3 on physics and L0 on assembly is not
   "average" — it is unbuildable.
2. **L1 is the dangerous level, not L0.** An absent claim is visible; an asserted one looks
   like an answer. The M8 retraction and the peak-to-peak metric error in our own BM-002
   work are both L1 masquerading as L3.
3. **Promotion requires falsifiability.** A dimension reaches L3 only if the evidence could
   have come out the other way. This is why non-tautology probes (R5) are load-bearing.
4. **Report the vector with every product.** The quality claim is the vector plus its
   assumption register, not a pass/fail.

---

# 6. Open questions this audit could not settle

| # | Question | Why it matters |
|---|---|---|
| Q1 | Where does **configuration knowledge** live, if not in cards or a human archetype? | S1/S2 are the central gap; nothing in Ver1 answers it |
| Q2 | How is **curved driving contact** (①) verified at all? | Gears, threads, cams — unverified in Ver1 after a dedicated milestone said no |
| Q3 | How is a **compliant element** verified independently of the formula that sized it? | Both Ver1 and ASSY-Next currently check a formula against itself |
| Q4 | What replaces a closed card library for **mechanism synthesis**? | A morphological matrix over 19 cards is lookup, not synthesis |
| Q5 | How is **uncertainty quantified** rather than named? | D14 cannot reach L3 without this |
| Q6 | What is the smallest product that would genuinely test **D15**? | Needed before any scaling claim |

---

# 7. Conclusion

Ver1's transferable value is concentrated in **verification discipline**, not in design
capability: physical carriers for every joint, dimensions derived from mates, limits as
parts, contact classes named with reasons, thresholds sourced with printed chains,
non-tautology probes, and negative results kept as findings. Those twelve items (§3) are
worth more than the entire card library.

Its defining limitation is equally clear and is stated in its own specification: **the
configuration came from a human.** Ver1 verified embodiments; it did not produce them.
Everything in §4 follows from that, and S1 is the one that makes the rest tractable.

ASSY-Next should therefore adopt Ver1's evidence standards immediately and treat its design
mechanism — cards, templates, goldens, narrowed candidate sets — as explicitly superseded.

**Next step:** agree this framework as the engineering target, then reopen Stage 01 against
D1, D13, and D14 — the dimensions a requirement interpreter actually governs.
