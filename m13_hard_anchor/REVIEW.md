# M13 · THE HARD ANCHOR — REVIEW (rack-pinion drawer cabinet, §8.2)

**Outcome: the second benchmark anchor is assembled and verified through the declared-pair physics.**
A cabinet + drawer on **two slide rails** driven by a **rack-and-pinion**: the pipeline's first
multi-card mechanism (`slide_rail` ×2 + `rack_pinion`), and the **first real firing of the alignment
AssemblyRule** (D-E-10). The deterministic spine is complete and both V-A protocols pass 5/5; the V-B
contact layer is checkpointed honestly (see the end).

| what | artifact | result |
|---|---|---|
| the cabinet | [4-view](out/anchor_hard_4view.png) · [exploded](out/anchor_hard_exploded.png) | drawer in cabinet, two carriages on the rails, knob+pinion, rack in the drawer |
| section | [one figure](out/anchor_hard_section.png) | rail↔carriage engagement (x=0) **and** pinion↔rack mesh (x=76) |
| the chain | [s5 table](out/s5_chain.md) | drawer_w / L_rack / axis_offset / engagement all **derived + cited** |
| alignment firing | [t0 report](out/t0_assembly_rules.json) | parallel/level on real geometry — **PASS, 0.00° / 0.00 mm** |
| it moves | [P-SLIDE V-A](out/p_slide_VA.png) · [mp4](out/p_slide_VA.mp4) | drawer reaches the 120 mm stroke, off-axis 0.00° — **5/5** |
| it transmits | [P-GEAR V-A](out/p_gear_VA.png) · [mp4](out/p_gear_VA.mp4) | knob→drawer on the π·m·z line, 120 mm, ratio resid 0.01% — **5/5** |

## The kinematic finding (why the frame was corrected)

m12 declared a complete anchor *set*, but assembling the mechanism — which is exactly where kinematic
closure gets tested — surfaced two orientations that don't close the loop for a drawer:

1. **The knob axis.** m12's knob ran along **Y** (into the front). A spur pinion on a Y-axis shaft
   rotates about Y and **cannot** drive a **Y-translating** drawer (the pinion axis must be ⊥ to the
   travel it drives).
2. **The rail mount.** m12 mounted the rails on the **vertical side walls**, but the proven
   `slide_rail` T-rail (m10, V-B 5/5) is a **floor rail with the carriage on top** — a wall mount is
   an unvalidated geometry change.

**Correction — reframe to the axes the proven carves realize, so m10/m11 geometry + physics carry
over verbatim (zero carve-physics risk):** pull-out along **+X**, two **floor rails** running +X at
±40 mm (matched height → the alignment subjects), a **vertical +Z knob** whose pinion meshes an **+X
rack** integrated into the drawer. The m12 templates were reframed to this (the anchor names and the
matched-level-pair property preserved; `test_hard_templates.py` still 7/7), and the m12 renders
regenerated. Two carve facts made this compose with **no card-geometry rewrite**:

- `slide_rail.carve` only read the mount anchor's *height*, so both rails landed at Y=0. Fixed to
  place each rail at its anchor's X/Y — **m10 is unchanged** (its anchor is at the origin → zero
  offset), and the Hard anchor's two rails now land at ±40.
- `slide_rail.carve` REPLACES its mover piece, so it can't also BE the drawer. Each rail therefore
  owns its own **carriage piece** (P2/P3, `slide_carriage`); the `drawer_tray` (P4) rides both,
  welded to them in physics. The rack is **integrated into the drawer** (§8.2 blesses this branch
  explicitly — "both answers golden"), so `rack_pinion.carve` unions it into P4.

## ⑤ — the §8.2 constraint chain (each number derived)

The golden is validator-CLEAN; `resolve_params` runs per card, and the §8.2 equalities resolve:

| symbol | formula | substituted | value |
|---|---|---|---|
| `drawer_w` | cab_inner_w − 2·(rail_w+cl) | 132 − 2·(8+0.35) | **115.30 mm** |
| `L_rack` | ≥ stroke + π·m·z/4 | 120 + 188.50/4 | **167.12 mm** |
| `axis_offset` | rack_pitchline + d/2 (= rp) | 60/2 | **30.0 mm** |
| `engagement` | ≥ 0.35·stroke | 0.35·120 | **42.0 mm** |
| `transmission` | π·m·z per rev | π·5·12 | **188.50 mm/rev** |

**Stroke is scaled from the §8.2 nominal 300 mm to 120 mm**, and here is why: the m12 desktop cabinet
is 200 mm deep, so a 300 mm extension would pull the drawer clean out of the cabinet. 120 mm keeps
≥45 mm of the 150 mm drawer engaged at full extension.

## ⑥ — compile + t0 alignment (the first real firing)

`compile_assembly` carves in motion-before-fastener order (`['E1','E2','E3']`) into **5 bodies**:
cabinet (base) · carriage_L · carriage_R · drawer(+rack) · knob(+pinion). The 4-view/exploded/section
renders confirm the geometry — the top view shows the involute pinion meshing the rack on the
drawer's +Y edge.

The **alignment AssemblyRule fires on the compiled geometry for the first time** and PASSES:

> `parallel: max axis angle 0.00° (tol 1.0°), level Δz 0.00 mm (tol 0.5) → ALIGNED`

This is the falsifiable t0 form of "the drawer's two rails must line up" (D-E-10, Option A): the two
`travel_axis` bindings resolve to the cabinet's `rail_axis_L/R` frames, which are parallel and level
by construction — and a skewed or stepped pair would fail (pinned by `test_alignment_rule.py`).

## t2 — the physics (declared V-A pairs)

Both mechanisms are verified as **declared kinematic pairs** on the frozen preset (R5). V-A declares
no tooth contact — the joints ARE the mechanism (D-M1-7) — so the result turns on the joint axes,
the units, and the card's rp/π·m·z formulas, checked end-to-end.

- **P-SLIDE V-A — 5/5 PASS.** The drawer (carriages + tray + rack, one welded body) on a declared
  +X prismatic joint reaches its **120 mm design stroke** under an axial pull, off-axis **0.00°**.
- **P-GEAR V-A — 5/5 PASS.** A declared knob hinge (+Z) coupled to the drawer slide by a near-rigid
  equality at the pitch radius rp. Turning the knob drives the drawer **120.0 mm**, matching the
  independent §3.6 prediction `π·m·z·rev` to **0.01%** — the measured curve lies exactly on the
  π·m·z line.

Guard trio on both verdict JSONs ([spine](out/s5_verdict.json), [physics](out/t2_hard_verdict.json)):
`decision_row`, `compile_hash`, `shape_assert` (two rails ∧ one pinion ∧ alignment present+passed;
V-A present ∧ V-B named-deferred). G9 G-CONV passes.

## Honest checkpoint — what is NOT closed (V-B)

Per the brief ("if t2 physics fights, checkpoint honestly rather than force it"), the **contact-level
V-B** is deferred, not faked:

- **P-GEAR V-B** (emergent tooth contact) rides the standing **R2b-open flag** (D-M1-5/-7):
  bidirectional meshing diverges at the frozen preset — a contact-formulation limit, `pending
  preset_v2`. Named in the verdict's `v_b_gap`.
- **P-SLIDE V-B** (contact-only, the two-rail welded drawer) is one step past m10's single-rail V-B
  (which passed 5/5). It is a legitimate next target — the T-rail geometry is proven — but a
  four-body welded drawer on two rails at the frozen preset is a new multi-body contact problem, and
  standing it up rigorously is scoped as the next session rather than rushed to a green here.
- **P-FULL** (both mechanisms co-driven in one contact run) likewise follows once P-SLIDE V-B lands.

So the Hard anchor is **assembled, validator-clean, alignment-verified, and V-A-complete**; its
contact-level (V-B) verification is the named, evidence-standard-held remaining work — the same
discipline the m8 lesson requires of every deferral.

## Status

- Golden: `tasks/build_goldens.py::anchor_hard` → `tasks/anchor_hard.json` (validator-CLEAN).
- Spine: `m13_hard_anchor/build_review.py` → ⑤ table, t0 alignment, renders, IR graph, `s5_verdict.json`.
- Physics: `m13_hard_anchor/p_full.py` → P-SLIDE V-A + P-GEAR V-A, plots + mp4, `t2_hard_verdict.json`.
- Suite: 72/72 (m10 unchanged; m12 tests updated to the corrected frame).
- **Open:** P-SLIDE V-B (two-rail contact) · P-GEAR V-B (R2b/D-M1-7) · P-FULL.
