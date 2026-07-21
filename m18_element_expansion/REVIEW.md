# M18 · ELEMENT TAXONOMY + TIER-1 EXPANSION — REVIEW (design doc)

**Scope: schema/ontology only — NO new physics.** This milestone lays the taxonomy the element
library will grow along, adds a THIRD card category (ConnectionCard), and ships 8 Tier-1 elements
that are V-A- or static-verifiable (no curved-contact V-B — that is the *next* milestone). Grounded
in **Pahl & Beitz, *Engineering Design: A Systematic Approach*** (in project knowledge); every axis
traces to a section, cited here and in the card comments.

This doc is written **before the code** (per the milestone brief) so the ontology stays legible as
elements multiply. Append-only: existing cards (`snap_hook_cantilever`, `pawl_detent`, …) are **not
re-filed** — only tagged, with reclassification candidates noted in §5.

---

## 1. The 7-axis element taxonomy

Every element card is tagged along 7 axes. **Axes 1–5 are IMPLEMENTED as real fields this milestone;
axis 6 is RESERVED (field exists, value fixed); axis 7 is a documented note, no field yet.**

| # | axis | values | source | status |
|---|---|---|---|---|
| 1 | **working_motion** | `type` ∈ {rotation, translation, rot_to_trans, snap_event, fixed} × `nature` ∈ {regular, irregular} | P&B **§2.1.4** (type + nature of motion) | **IMPLEMENT** — `MotionSpec.nature` (cam needs irregular) |
| 2 | **axis_relationship** | parallel \| intersecting \| crossed | P&B **§2.1.4** (relative arrangement of axes) | **IMPLEMENT** — `Behavior.axis_relationship` (worm=crossed, bevel=intersecting) |
| 3 | **connection_principle** | form \| force \| material | P&B **§8.1** (types of connection) | **IMPLEMENT** enum; only form/force used now (material = welding/adhesive, future) |
| 4 | **self_locking** | bool | P&B **§7.4.3** (self-help / self-locking) | **IMPLEMENT** — `Behavior.self_locking` (lead_screw; resolves D-M13-3) |
| 5 | **emergent_check** | `EmergentCheck{status, reason, risk}` — status ∈ {verified, deferred, not_applicable} | **OUR contribution (cite m17)**, not P&B | **IMPLEMENT** (D-M18-4) — a STRUCT, not a bool: it carries WHY a check is deferred and WHAT risk that leaves |
| 6 | **compliance** | rigid \| compliant | P&B **§8.1.3** (elastic force connection) | **RESERVE** — field on ElementCard, value fixed `rigid`; `compliant` needs a P-SPRING protocol not built here (spring/damper/living_hinge are the future compliant=true) |
| 7 | **kinematic_dof** | Roth joint matrix | P&B **§8.1.1 p.439** (joint / DoF matrix) | **RESERVE as a note only** — no field; documented so future linkage/4-bar multi-DoF work does not reinvent it |

**Axis 5 (`emergent_check`) is ours, not P&B's — and it is a STRUCT, not a bool (D-M18-4).** The
distinction it encodes: formula/geometry checks verify a SINGLE element is built to spec (necessary);
**V-B physics is the DISCRIMINATING gate** — it verifies the ASSEMBLY actually functions and surfaces
**emergent requirements the spec never stated**. V-B is what found the **stop** a lid needs to not
fold flat (m8) and the **brake** a lift needs to not back-drive (m13). m17 proved the frozen-preset
rigid rig is metastable on *curved* contact (R2b: even dt/25 only delays the blow-up), so a
curved-contact element **cannot get that safety net** — and must say so.

A bool ("verifiable?") cannot express "deferred + why + what's unverified"; the struct
`EmergentCheck{status, reason, risk}` can, and a `deferred` status **requires both reason and risk**
(build-enforced — see the validator below). Meaning:

| status | meaning | example |
|---|---|---|
| **verified** | the emergent safety net is PRESENT (V-B, or V-A fully covers the declared pair) — this is what catches the m8 stop and the m13 brake | pin_hinge, slide_rail (V-B 5/5), coupling / universal_joint (V-A covers the declared pair, no curved-contact emergence) |
| **deferred** | the net is ABSENT by a TOOL LIMIT; the risk is carried EXPLICITLY (reason+risk required) | **lead_screw** (curved thread, R2b — self-lock is formula-only, hold under load not physics-verified); **rack_pinion** (curved tooth, R2b — bidirectional meshing unverified); **snap_hook** (elastic beam, D3 — snap event Bayer-formula-only) |
| **not_applicable** | a static element with no assembly-level emergent DoF — formula/geometry/t0 closes it | journal_bearing, bushing, dowel_pin, screw_boss, press_fit |

This **generalises rack_pinion's existing `v_b_gap`/`shape_assert`** (M11) to *every* element: the
curved-contact prototype rack_pinion already carried its gap in prose; `EmergentCheck` makes it a
structured, build-enforced field every curved-contact element (and the future cam/worm/bevel
milestone) uses. **coupling / universal_joint** are marked `verified` (not `deferred`): their function
is a DECLARED kinematic pair fully covered by V-A with no curved-contact emergent gap — the Cardan
velocity fluctuation is a known analytic property (recorded as an observable), not an unverified risk.

**Axis 7 intent (reserved, no field).** A future linkage/4-bar/slider-crank element has a
**multi-DoF kinematic pair matrix** (Roth, P&B §8.1.1 p.439): each joint contributes a 6-vector of
permitted/blocked translations+rotations. Today every element realises a single scalar DoF, so a
Literal motion.kind suffices; when multi-DoF linkages arrive, `kinematic_dof` becomes a 6×N matrix
field. Documented now so it is not reinvented as an ad-hoc dict.

---

## 2. The THREE-category card ontology (the anti-confusion core)

The card ABC (`knowledge/cards/base.py`) had **two** concrete kinds; this milestone adds a **third**.
The split is by **what the card DOES to the assembly**, and it is a *knowledge property of the
element type*, not of any instance:

| category | role — what it DOES | referenceable by | examples |
|---|---|---|---|
| **MechanicalElementCard** | **REALIZES** a DoF / behaviour (moves something) | `Behavior.realized_by` | pin_hinge, slide_rail, rack_pinion, **lead_screw, coupling, universal_joint** |
| **PassiveFeatureCard** | **SUPPORTS / CONSTRAINS** a behaviour, realizes nothing | `Behavior.imposed_by` (never realized_by, V-08) | stop_flange, **journal_bearing, bushing** |
| **ConnectionCard** *(NEW, §8.1)* | **FIXES / FASTENS** parts together (no DoF, no support-of-a-DoF — a *joint between parts*) | neither realized_by nor imposed_by-of-a-motion (V-08 extended) | **dowel_pin, screw_boss, press_fit** |

### 2.1 `connection_principle` is a PROPERTY (axis 3); a ConnectionCard is an OBJECT — they are not the same level

This is the one conflation to prevent. They **share a word, not a level**:

- **`connection_principle`** (axis 3) is an **attribute** with values {form, force, material}. It
  classifies *how* a connection transmits load: **form** = geometric interlock (a dowel located in a
  bore), **force** = friction/preload (a press-fit, a screw's clamp), **material** = fused
  substance (weld/adhesive — future). It is a *field*.
- **`ConnectionCard`** is a **card class** — an *object* in the registry with ports, params,
  formulas, a carve. A ConnectionCard *carries* a `connection_principle`, the same way a
  MechanicalElementCard *carries* a `working_motion`.

A screw_boss (object: ConnectionCard) has connection_principle=force (property). A dowel_pin (object:
ConnectionCard) has connection_principle=form (property). Spelling this out so no future milestone
writes "the form connection card" as if the principle were the class.

### 2.2 Hardware-question resolution: connection role and hardware piece are ORTHOGONAL

A threaded fastener is a **ConnectionCard** (its job is to fasten) that **also declares
`provides_pieces`** — the physical screw body is **hardware** (D-ONT-11), exactly like the pin_hinge
provides its pin. **"Connection role" and "hardware piece" are two independent axes** — one card can
be both:

| | provides hardware | provides no hardware |
|---|---|---|
| **realizes a DoF** | pin_hinge (pin) | slide_rail |
| **fastens (connection)** | **screw_boss (the screw)** | **dowel_pin, press_fit** (no separate part) |

So `screw_boss.provides_pieces = [the screw]`; `dowel_pin` and `press_fit` provide none (the dowel is
itself the located feature; the press-fit is interference between two existing parts). Both remain
ConnectionCards. This settles the standing "is a fastener an element or a piece?" question: it is a
**ConnectionCard** (role) that may **entail a hardware Piece** (D-ONT-11).

---

## 3. Parked-element roadmap (Roth catalogue, P&B Table 3.2)

The full map so future milestones don't re-derive it. Rows = Roth catalogue categories (P&B
Table 3.2); cells marked **have** / **adding-now (m18)** / **parked (Tier2/3)**.

| Roth category (P&B Table 3.2) | have (pre-m18) | adding-now (m18, Tier-1) | parked |
|---|---|---|---|
| **connections / fasteners** (§8.1) | — | **dowel_pin** (form), **screw_boss** (force), **press_fit** (force) | rivet, clip, weld/adhesive (material) → Tier3 |
| **guides / bearings** (§8.2) | (slide_rail is a guide-realizer) | **journal_bearing**, **bushing** (rotational supports) | thrust bearing, linear ball guide |
| **power transmission — parallel axes** | rack_pinion (rot→trans) | **coupling** (1:1 rotation, parallel/coaxial) | spur/belt/chain gear pair → Tier2 (curved contact) |
| **power transmission — intersecting axes** | — | **universal_joint** (rotation across an angle) | bevel gear → Tier2 (curved contact) |
| **power transmission — crossed axes** | — | — | **worm gear** → Tier2 (crossed, self-locking, curved) |
| **screw / motion conversion** | rack_pinion | **lead_screw** (rot→trans, self-locking) | ball screw |
| **mechanisms / linkages** (multi-DoF) | — | — | 4-bar, slider-crank, cam-follower → Tier2/axis-7 |
| **cams** (irregular motion) | — | — | **cam** → Tier2 (needs `nature=irregular`, curved contact) |
| **springs / elastic** (§8.1.3) | (snap/pawl are compliant beams, V-B-exempt) | — | spring, damper, living_hinge → Tier3 (compliant=true, P-SPRING) |
| **joints (revolute/prismatic)** | pin_hinge, slide_rail | (coupling/uni-joint declare pairs) | — |

**Tier boundaries.** Tier-1 (m18) = planar/joint or static, V-A/static, `vb_verifiable=True or
static`. Tier-2 (next) = **curved contact** (cam, worm, bevel, spur pair) — `vb_verifiable=False`,
V-B deferred behind a preset_v2 (the m17 dt* question). Tier-3 = **compliant** (spring/damper) —
`compliance=compliant`, needs a P-SPRING protocol. m18 deliberately does not touch cam/worm/bevel.

---

## 4. The KG narrowing = the morphological matrix (P&B §3.2.3 Zwicky)

Extending `kg.candidates()` to filter on the new axes (axis_relationship, self_locking,
connection_principle) is exactly the **morphological-matrix / Zwicky-box** step (P&B §3.2.3): a
requirement is a set of axis values, and the matrix narrows to the elements that carry them. Two
worked narrowings this milestone must show:

- "**orthogonal-axis rotation transfer + self-lock**" → (axis2=crossed, axis4=self_locking) → **worm**
  (once Tier-2 lands); today the closest in-vocab is flagged and the crossed+self_lock combination is
  reserved.
- "**locate two parts, no DoF**" (a fixed relation, form principle) → **dowel_pin**.
- "**rotation→translation that HOLDS under load without a brake**" → (rot_to_trans, self_locking=True)
  → **lead_screw** (vs rack_pinion which is self_locking=False and needs a pawl — D-M13-4).

---

## 5. Reclassification candidates (noted, NOT acted on — append-only)

Existing cards are only **tagged** this milestone; re-filing is deferred (would churn goldens):

- `snap_hook_cantilever` — currently MechanicalElementCard. It **realizes** a snap_event *and*
  **fastens** — arguably a ConnectionCard (connection_principle=form, the catch interlock) with a
  compliant beam. **Reclassification candidate → ConnectionCard**, deferred: it realizes a genuine
  assembly-phase snap_event DoF-event, so the two-role tension (§2.2) applies; ruling it needs the
  compliant-connection (Tier-3) work. Tagged `connection_principle=form`, `compliance` stays `rigid`
  at the field (the beam's compliance is handled by its Bayer-formula exemption, not axis 6, until
  P-SPRING exists).
- `pawl_detent` — a compliant ratchet; **reclassification candidate** alongside the Tier-3 spring
  work. Tagged, not moved.
- `stop_flange` — stays PassiveFeatureCard (constrains a rotation limit; the model case for the class).

---

## 6. Open decisions

- **D-M18-1** — **ConnectionCard added** (P&B §8.1). Third card category: fastens/fixes parts,
  realizes nothing and supports no DoF. Carries `connection_principle` ∈ {form, force, material}.
  Orthogonal to hardware provision (a screw_boss is a ConnectionCard that also provides_pieces).
- **D-M18-2** — **7-axis element taxonomy adopted from P&B** (§2.1.4, §8.1, §7.4.3, §8.1.3,
  §8.1.1); axis 5 (`vb_verifiable`) is our m17-grounded contribution. Axes 1–5 implemented as fields;
  axis 6 (`compliance`) reserved (fixed `rigid`, validator rejects `compliant` with a P-SPRING
  message); axis 7 (`kinematic_dof`) a documented note only.
- **D-M18-4** — **axis-5 is an `EmergentCheck` struct, not a bool.** `EmergentCheck{status ∈
  {verified, deferred, not_applicable}, reason, risk}`. A `deferred` status **requires reason+risk**
  (enforced at construction), and every card **must** declare an `emergent_check` (build-enforced in
  `__init_subclass__`, mirroring the D18/D21 collision_hint rule) — so no curved-contact element can
  ship without naming its unverified emergent gap. Generalises rack_pinion's `v_b_gap`/`shape_assert`
  (M11) to all elements; the future cam/worm/bevel milestone uses the same struct.
- **D-M18-3** — **`self_locking` promoted to first-class** (P&B §7.4.3), a `Behavior` field. This
  **resolves the DRAFT D-M13-3**: whether "holds under load" deserved first-class ontology status.
  It does — a lead_screw's self-lock and a plain rack_pinion's *lack* of it (needing the pawl,
  D-M13-4) are now a checkable axis, not prose.

---

## 7. What ships (parts B–D)

- **Schema (B):** `MotionSpec.nature`, `Behavior.axis_relationship`, `Behavior.self_locking`,
  `ConnectionCard.connection_principle`, `ElementCard.compliance` (reserved). All defaults keep every
  existing golden IR valid.
- **Cards (C):** 8 Tier-1 — lead_screw, coupling, universal_joint (Mechanical); journal_bearing,
  bushing (Passive); dowel_pin, screw_boss, press_fit (Connection). Each: param_bounds, ports,
  resolve_params, carve (one solid), formula_check (cited formula), verification (V-A/static, no
  curved V-B), and 7-axis tags.
- **Validators + KG + tests (D):** V-08 extended (a ConnectionCard may not be realized_by);
  compliance=`compliant` rejected with the P-SPRING message; `candidates()` narrows on the new axes
  (≥2 narrowings tested); golden-style unit tests per card. Everything stays green.
