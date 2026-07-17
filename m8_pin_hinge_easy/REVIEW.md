# M8 · pin_hinge Easy anchor — REVIEW (G-H entry point)

> ## ⚠ RETRACTION (D-M8-4) — read this first
>
> **An earlier version of this REVIEW claimed a V-B PASS. It was void, and is withdrawn.** It rested
> on an **open-stop I invented**: a collision primitive in the physics driver with **no solid in the
> compiled STEP and no entity in the IR** — not "a stop that exists only in geometry", but one that
> existed only in the *contact model*.
>
> The result I had treated as a failure — **θmax 272°, travel 0.63 mm** — **was the correct answer.**
> It reproduces M0's own finding, stated there plainly:
> *"no stop: the lid is free to fold flat. **That is the finding**."* A design that declares no stop
> **has** no stop; past 90° the over-centre lid folds right over. I engineered a fake stop until the
> criteria went green — defeating the exact thing V-B exists to expose. M0 had already named the
> trap: *"V-A hid this — MuJoCo's joint `range` acted as a stop the part does not physically have."*
>
> Caught at G-H by the question **"where does the stop live in the IR?"**, which an invented stop
> cannot answer. Three things changed as a result, none of them a patch:
>
> 1. the backstop is **deleted**; the stop angle is **read from the IR** (no B3 ⇒ `inf` ⇒ the
>    fold-over stands);
> 2. the legitimate stop — a `stop_flange` PassiveFeature with a V-08-registered B3 limit and **real
>    flange geometry** — is built, and is now the benchmark (§1);
> 3. the rule is **mechanized** (§2): unsourced collision geometry is a **build error**, with the
>    retracted prim itself as a regression test.

## 1. Golden swap (D-M8-5) — the benchmark now carries the stop

**`tasks/anchor_easy.json` := the STOP variant** (F1 + B3, ceiling card-derived from the real
`axis_z`). **Why:** honest V-B proved the §8.1 spec — *"opens ≥90° AND returns closed"* — is
**physically unsatisfiable** for this over-centre lid without a stop. Past 90° gravity pulls it
further open; no actuation satisfies both clauses on a stop-less design. **The stop is not a
convenience — it is a design requirement the system discovered from its own physics**, and the
benchmark must carry it.

**`tasks/anchor_easy_nostop.json`** is kept as the **D20 demonstration golden**: the same plan with
F1/B3 removed and nothing else. It is validator-CLEAN (a stop-less design is a legal IR); its
*verdict* is an honest **EXPECTED_FAIL** — `"expected: fold-over, no angular limit"` — carried in the
verdict JSON, the snap_panel pattern applied one tier down.

| | `anchor_easy_nostop.json` (D20 demo) | **`anchor_easy.json` (BENCHMARK)** |
|---|---|---|
| IR | no stop_flange, no B3 | **+F1** (`stop_flange`) **+B3** (`bound=max`, ≤120.05°) — *zero other changes* |
| **V-B** (contact-only) | **1/5 — θmax 272°** · EXPECTED_FAIL | **5/5 PASS — θmax 124°**, travel 0.0 mm |
| V-A (declared joint) | 5/5 (θmax 112°) | 5/5 (θmax 112°) |
| reading | **the lid folds over — that is the finding**, reported not fixed | **the flange bottoms out on the box's own rear wall — stops BY CONTACT** |

**V-A passes both — only V-B separates them.** That is **D20** demonstrated end-to-end on *compiled*
output: a declared joint's `range` silently supplies a stop the part may not have, so contact-only
V-B is **required, not optional**, for card-realized joints.

![stop pair](out/stop_pair_theta.png)

Identical until the flange engages (~0.9 s). Red blows through over-centre and folded-flat to 272°,
with the travel spike as it sweeps the box; green arrests at the B3 ceiling and holds.
Videos: [demo V-B (folds over)](out/t2_easy_nostop_V-B.mp4) ·
[benchmark V-B (arrests)](out/t2_easy_V-B.mp4) · data [`stop_pair.json`](out/stop_pair.json)

**Where the stop lives in the IR, now.** `stop_flange` was a shell (ports + `imposes`, no geometry);
it is now real: **F1** (PassiveFeature — constrains, realizes nothing) → **B3** (the use-phase
rotation *ceiling* it imposes, registered per **V-08**) → **a real rearward flange solid** that
bottoms out on the box's own rear wall (no added part). `compile_assembly` now **carves
PassiveFeatures at all** — it previously iterated only `plan.elements`.

**Sub-finding — B3's ceiling was a copied number.** I first typed M0's **108.85°**. M0's scan
hardcodes `dz = −lid_t/2`, silently encoding *M0's* axis at the lid mid-plane; this box's axis sits
at `z=box_h` → **120.05°**. The sim's 124.4° = 120.05 + ~4° contact compliance; against 108.85 it was
an unexplained 15.5° gap — **the pair run caught it**. Now `stop_angle_deg` takes the real `axis_z`,
B3's `range_value` is **derived by calling the card's formula**, and the carve **re-solves and
refuses on disagreement (>0.5°)** — V-08's geometric teeth.

## 2. D-M8-4, mechanized — unsourced collision geometry cannot build

The STEP→MJCF layer now **refuses** any collision geom that does not trace to a declared source.
This is a **build error, not a warning** (`UnsourcedCollisionPrim`), run before a single geom is
emitted:

| source form | meaning |
|---|---|
| `card:<card_ref>@<inst_id>` | an element/feature's own `collision_hint` — the instance must exist in the plan with that card_ref |
| `template:<template_ref>` | host geometry — some piece must use that template |
| `fixture:D23` | the base-weld boundary condition |

Producers stamp their own source; `build_mjcf` **requires the plan** (provenance cannot be checked
against nothing). The driver was also stripped of the ability to author geometry — it now only
**routes** what cards and templates emit (card prims carry an `owner`: A → base host, B → mover host,
**pin → the hardware piece the element provides**). The hand-built pin cylinder is gone; the pin now
comes from the `pin_hinge` card that provides it (D-ONT-11). *(Side effect, reported: the
card-supplied pin sits in the axis frame rather than my hand-placed world cylinder, and the
benchmark's V-B went 4/5 → **5/5** — the seed-0 pin-drift outlier was an artifact of my placement.)*

Negative tests — [`tests/test_collision_provenance.py`](../tests/test_collision_provenance.py), 5/5:
real hints accepted · **no source → refused** · **forged source → refused** · **build_mjcf without a
plan → refused** · and **the retracted backstop, injected verbatim, → refused**. Inventing geometry
now requires forging a provenance the IR would have to back — a deliberate act, not an oversight.

## 3. The ~26° suppression — artefact, measured (D-M8-3)

![proxy artefact](out/proxy_artifact_26deg.png)

Two independent authorities at the jam angle ([`proxy_artifact.json`](out/proxy_artifact.json)):

| authority | tool | result |
|---|---|---|
| **the PARTS** | build123d boolean on compiled solids | box ∩ lid-rotated-26° = **0.00 mm³** — they clear |
| **the PROXIES** | MuJoCo contact detection, classes **merged** | **4** box↔lid contacts — all `P1_c1↔P2_c16` (box rear **wall** vs a lid ring-**wedge**) |

The parts clear where their convex stand-ins collide ⇒ **artefact confirmed**.

**The guard — verified, not asserted.** Suppression is scoped to cross-class pairs between the two
*named* intended-contact classes (`mech` = pin/bore ring-of-wedges; `seat` = seating + floor +
flange). **The travel class is never suppressed:** travel reads base↔mover **seat↔seat** contacts,
live at every angle — instrumenting the fold-over confirms it, the peak travel contact being
`P1_c1↔P2_c0` (rear wall vs lid panel), **both seat-class**, firing **0.99 mm at θ=272.9°**.

**LIMITATION (named, not hidden):** a genuine *mech↔seat* interference — a lid knuckle truly crashing
a wall — would be **invisible to the physics travel gate**. That case is covered at the PARTS level
instead (t0's AR1 exclusion sweep + the real-geometry boolean), which is why the 26° number above is
measured on solids rather than proxies.

## 4. The assembly

2 elements — **E1 `pin_hinge`**, **E2 `snap_hook_cantilever`** · 1 feature — **F1 `stop_flange`** ·
3 pieces — **P1 box [base]**, **P2 lid [mover]**, **P3 pin [hardware ← E1]** · 2 AssemblyRules —
**AR1 exclusion**, **AR2 resource**. Compiled **motion → fasteners → features**.

| view | file | what to look for |
|---|---|---|
| 4-view | [`out/anchor_4view.png`](out/anchor_4view.png) | hinge knuckles + protruding pin at the rear; latch at the front |
| exploded | [`out/anchor_exploded.png`](out/anchor_exploded.png) | the **pin is a separate hardware body** (D-ONT-11) |
| **SECTION** | [`out/anchor_section.png`](out/anchor_section.png) | one x=0 cut — hinge knuckle wraps the pin/bore (rear) **and** latch teeth in the catch window (front) |
| IR graph | [`out/ir_easy.svg`](out/ir_easy.svg) (benchmark: **F1 ⇢ B3**) · [demo](out/ir_easy_nostop.svg) | AR1/AR2 rhombus nodes + subject edges + provenance; **B5→AR1 `checkable form`** |
| HUD | [`out/hud_V-A.png`](out/hud_V-A.png) · [`out/hud_V-B.png`](out/hud_V-B.png) | the scored values burned into the frame (D15) |

**Renderer parity guard** ([`tests/test_ir_graph_parity.py`](../tests/test_ir_graph_parity.py)):
`to_mermaid ≡ to_svg` over the IR-entity node and edge sets. This is the regression that let AR1/AR2
ship missing from a signed-off SVG. It immediately found a **second** drift: mermaid emitted
AR→subject only for `plan.instance()` (so AR2→P2, a *piece* referent, was missing) and had no
B5→AR1 link. Both renderers now derive these from **one shared helper** — parity is structural, not
merely tested.

## 5. Gates (regenerated, guard trio on every verdict)

| gate | result |
|---|---|
| **t0** AssemblyRules | both **PASS** — AR1 exclusion is D22-aware (undercut interferes only through the intended **0–10° release band**; free sweep 0.00 mm³); AR2 resource Σ(12 + 27.7) = **39.7 ≤ 80** |
| **t1** re-measure | both elements, **0.0000 mm** drift |
| **t2** benchmark | **V-A 5/5 · V-B 5/5 → PASS** |
| **t2** D20 demo | V-A 5/5 · **V-B 1/5 → FAIL (EXPECTED)** — annotated in the verdict JSON |

Guard trio present on both verdicts: `decision_row` + `compile_hash` + shape assertion
(`modes_covered`, `g9_all_pass`, `seeds_per_mode` = 5 each).

**Suite 46/46** — 41 + 5 new provenance tests.

## Reproduce

```
./bin/py tasks/build_goldens.py                                   # writes both goldens
./bin/py tasks/run_m8_t2.py verify/t2_physics/out_easy stop       # BENCHMARK -> tag "easy"
./bin/py tasks/run_m8_t2.py verify/t2_physics/out_easy nostop     # D20 demo  -> tag "easy_nostop"
./bin/py tasks/run_m8_t1.py verify/t2_physics/out_easy            # t1 re-measure
./bin/py m8_pin_hinge_easy/build_review.py                        # renders + IR + t0 ARs
./bin/py m8_pin_hinge_easy/build_stop_pair.py                     # the D20 pair figure
./bin/py m8_pin_hinge_easy/build_proxy_overlay.py                 # the 26° artefact evidence
./bin/py m8_pin_hinge_easy/build_report.py                        # report.html
```

Decisions: **D-M8-1** (harness rulings) · **D-M8-2** (stop_flange + the D20 pair) · **D-M8-3** (class
separation: artefact evidence + limitation) · **D-M8-4** (the retraction + the mechanized rule) ·
**D-M8-5** (golden swap) · **D-ONT-11/-12** · **D-M1-8** (R2b deferred option 3). See
`DECISIONS_LOG.md`. **Open [`report.html`](report.html)** for the full run.
