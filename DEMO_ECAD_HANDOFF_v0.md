# DEMO C — T-S3 "ECAD→MCAD handoff automation" (separate add-on spec, EN)

> **This file is an ADD-ON to SNAPFIT_STARTER_v0.md. It does not modify existing files.**
> Ontology, gates, and visualization conventions follow SNAPFIT_STARTER (§1–8, §12)
> and MECHSYNTH_SPEC_v0.1. Only the new material is defined here.

## 0. Use-case narrative (one paragraph for the paper/talk)

Circuit design and mechanical design always work as a pair. The ECAD team hands over a
board outline, component placement, and connector positions; the mechanical designer
**weaves around** the components (heights, keepouts), **protects** them (supports,
openings, retention), and designs the enclosure. And the board always changes — a
capacitor moves in rev B, a connector shifts in rev C, and the case chases every
revision. **This demo automates the handoff and the revision chase**: board data in →
ComponentCards derived automatically → constraint-satisfying case out → every decision
carries a rationale → on a new rev, re-run + a design diff report.

- Relation to Demo B (RPi): T-S2 proves the schema with a **hand-written card for a
  known component**; T-S3 proves automation with **auto-derived cards for arbitrary
  boards**. A natural promotion.
- Scope guard: board retention = snap clips/bosses, lid = snap-on. No motion →
  completes within Tier0/1.

## 1. Input: Board Handoff schema (new file `knowledge/board_handoff.py`)

Real-world handoff formats are IDF, ECAD STEP exports, centroid (pick&place) + BOM.
v0 defines a **neutral JSON schema** capturing their common denominator; a KiCad
importer is gated for later.

```python
class ConnectorEntry(BaseModel):
    ref: str                       # "J1"
    kind: str                      # "usb_c" | "barrel_jack" | "pin_header" | ...
    position_mm: tuple[float, float]
    rotation_deg: float
    body_mm: tuple[float, float, float]        # connector body envelope
    mating_dir: Literal["+x","-x","+y","-y","+z"]   # cable/plug approach direction
    plug_envelope_mm: tuple[float, float, float]     # plug (incl. overmold) envelope
    plug_travel_mm: float                            # insertion stroke

class ComponentEntry(BaseModel):
    ref: str                       # "C12", "U3"
    position_mm: tuple[float, float]
    rotation_deg: float
    courtyard_mm: tuple[float, float]   # rectangular footprint approximation
    height_mm: float
    side: Literal["top", "bottom"]
    fragile: bool = False          # protection-required tag (set by the ECAD team;
                                   # e.g., electrolytic caps, crystals)

class BoardHandoff(BaseModel):
    board_id: str; revision: str            # "widget_v1", "revB"
    outline_mm: list[tuple[float, float]]   # polygon (v0: rectangles + chamfers)
    thickness_mm: float
    mounting_holes: list[dict]              # {pos, dia, plated}
    components: list[ComponentEntry]
    connectors: list[ConnectorEntry]
    citations: list[str]                    # source file/drawing identifiers
```

- **Gate G-C1 (importer)**: v0 writes JSON by hand (sample boards, §5). The KiCad
  `.kicad_pcb` importer (outline/courtyard/centroid/hole extraction) is a separate
  checkbox — until done, the demo is scoped to "JSON handoff".
- **Gate G-C2 (input validation)**: closed outline, components inside the outline,
  hole–component non-interference, etc. ECAD data is NOT trusted unvalidated (exactly
  as in practice).

## 2. Automatic ComponentCard derivation (`knowledge/cards/auto_board.py`)

BoardHandoff → ComponentCard instance (same interface as the hand-written rpi4b card
in T-S2):

```
envelope   = outline × (bottom_clear .. max(top heights))
anchors    = holes ("hole_J{n}"), board top/bottom faces, per-connector edge faces
             ("conn_{ref}_face"), edge segments ("edge_N/E/S/W")
keepouts   = ① per component: courtyard × height + margin (STATIC keepout)
             ② per connector: plug_envelope swept along mating_dir by plug_travel
                          (**DYNAMIC keepout** — the space of the act of plugging in)
             ③ fragile parts: courtyard × height + expanded margin (protection marking)
citations  = inherited from handoff.citations (rationale lines like
             "J1 position [widget_v1 revB handoff]")
```

- Ontology-consistency note: ② is the geometric expression of a behavior the connector
  **imposes** in assembly/use phase ("plug-insertion event"). The phase formalization
  covers external interfaces with NO schema extension — that reuse is itself a test.
- Post-D-ONT-4 note: board-support bosses/clips are `PassiveFeature` cards.

## 3. Formalizing the mechanical response — "avoid" and "protect" as rules

The mechanical designer's tacit moves compiled into explicit Rules (each a Rule object
with source/assumption tags):

| Move | Rule (v0 defaults) | Tag |
|---|---|---|
| avoid: heights | lid inner z ≥ max(top height) + 2.0 mm | A-C1 (shop practice) |
| avoid: side walls | inner wall to component courtyard ≥ 1.5 mm | A-C2 |
| avoid: plugs | case solid ∩ dynamic keepout = ∅ (**openings are DERIVED**) | by definition |
| protect: support | boss or snap clip at every mounting hole; zero unsupported holes | [Bayer p.5 Fig.1 pattern] |
| protect: openings | opening = plug section + 2×print_clearance; residual wall around opening ≥ min_wall | A-C3 |
| protect: fragile | no lid ribs over fragile keepouts; margin 1.5→3.0 mm | A-C4 |
| board insertion | the board's own assembly path (−z descent) sweeps with zero interference outside clip undercuts — reuse the 3-way check (SNAPFIT §5.2 / D22) | existing |

Key observation: **port cutouts are not drawn; they are DERIVED from non-interference
with dynamic keepouts.** This is interface-first in its handoff form — the functional
requirement of connector access determines the geometry (the hole), not the reverse.

## 4. Pipeline specializations (T-S3)

| Stage | Specialization |
|---|---|
| ⓪ ingest (new) | load BoardHandoff → G-C1/C2 → derive auto ComponentCard. Viz: `s0_board.png` (board plan view + component height heatmap + keepout overlay) |
| ① | command: `"Design a case for this board (widget_v1 revB). Cables stay plugged in during use; the board mounts without screws."` |
| ④ | clip binding candidates = auto-generated hole/edge anchors. V-12 (keepout ∩ binding) extends to auto keepouts |
| ⑤ | §3 rules join the constraint system. Inner width/height are DERIVED values (verify in s5_params) |
| ⑦ | Tier0 additions **G-C3**: (a) case ∩ static keepouts = ∅, (b) case ∩ dynamic keepouts = ∅ (plug sweeps), (c) unsupported mounting holes = 0, (d) residual wall ≥ min_wall around every opening |
| ⑧ | snap clip formula checks reuse SNAPFIT_STARTER §2 unchanged (reuse is the test) |

## 5. Sample boards (hand-authored: `tasks/board_widget_v1_revA.json` / `_revB.json` / `_revC.json`)

A fictional "widget" board in three revisions — the demo narrative is BUILT INTO the
revisions:
- **revA**: 60×40 mm, 4 holes, USB-C (edge E, mating +x), electrolytic cap h=8 mm
  (fragile), 6 components
- **revB**: cap moved + height 8→11 mm, pin header added → **re-run demo**: lid inner
  height rises + one clip relocates automatically; the diff report names the causes
- **revC (INFEASIBLE demo)**: USB-C moved to 3 mm from a corner →
  "residual wall 1.1 mm < min_wall 1.2 mm [A-C3]. Alternatives: increase wall
  (+1.6 mm outline) or request ≥4 mm connector offset" — **the system generates the
  feedback sentence the mechanical team sends back to the ECAD team.**
  (Automating the REVERSE arrow of ECAD↔MCAD collaboration — the demo's apex.)

## 6. Revision diff report (`viz/rev_diff.py`, new)

Compares two runs' IR, parameters, and geometry (a report.html subpage):
- input diff: moved/added/changed components (handoff comparison)
- decision diff: changed Bindings/Parameters with **cause tracing** ("inner height
  12→15 mm ← C7 height 8→11 [revB handoff] ← rule A-C1") — the rationale sheet's diff
  form
- geometry diff: revA/revB case overlay PNG (changed regions highlighted)
- verdicts: revB PASS / revC INFEASIBLE + feedback sentence

> Positioning line (for the paper): "The real work of mechanical design is not the
> first design but the revision chase. An explicit IR makes change propagation
> diffable — this is what makes it design rather than regeneration."

## 7. Assumption register additions
| ID | Content | Resolution |
|---|---|---|
| A-C1..C4 | §3 shop-practice numbers (2 mm top clearance etc.) — practice, not standards | replace with corporate DFM / IPC literature values |
| A-C5 | plug_envelope provided by the ECAD team (v0 samples carry representative USB-C overmold dims) | connector datasheet cards (paper 2) |
| A-C6 | rectangular courtyard approximation | extend to polygons later |

## 8. Checklist (start after M-S and T-S2)
- [ ] BoardHandoff schema + G-C1/C2 + sample boards revA/B/C JSON
- [ ] auto ComponentCard derivation (static/dynamic keepouts) + `s0_board.png`
- [ ] §3 rules as Rule objects, joined at ⑤
- [ ] G-C3 four checks (dynamic-keepout sweep reuses the SNAPFIT §5.2 sweep code)
- [ ] revA end-to-end PASS → revB re-run + rev_diff → revC INFEASIBLE + feedback sentence
- [ ] (stretch) KiCad importer / (stretch) print revA·revB + assembly photos with a board stand-in
