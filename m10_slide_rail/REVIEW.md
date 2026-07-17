# M10 · slide_rail — REVIEW (G-H entry point)

**Outcome: the card is built and the required mode passes.** `slide_rail` (§3.5) — a rectangular
**T-rail** retaining slide — is a full card (ports, bounds, the §3.5 rule chain, imposes, carve,
collision_hint, resolve_params, verification). The minimal two-piece fixture compiles and runs
P-SLIDE: **V-A 5/5 PASS** (required); **V-B G-CONV trips on the drop-in settling transient** —
recorded, not tuned, per the R2b precedent — with an **observed-not-gated** run showing the geometry
itself does slide and retain.

## The card (§3.5)

A drawer slide must run free on one axis and be captured on the other two. A plain tongue-in-groove
runs free but isn't captured against lift; a dovetail captures but has angled faces. The **T-rail**
does both and stays **all-boxes** (no curves — §3.5's "groove as box primitives, cheap"): a narrow
neck carries a wide head, and the carriage's lips tuck under the head shoulders.

- **ports** `rail_mount` / `carriage_mount` / `travel_axis` · **param_bounds** rail_h/w [4,10],
  clearance [0.25,0.45], engagement_len, stroke.
- **§3.5 rule chain, reproduced numerically by the fixture** (build_review prints it):
  `engagement_len 21 ≥ 0.35·stroke 21` ✓ · `rail_len 84 = stroke 60 + engagement 21 + stop-tab` ·
  `drawer_w(body_inner 100) = 100 − 2·(8+0.35) = 83.3` ← ⑤ **derives** geometry from this equality (D6).
- **imposes** an assembly-phase axial insertion path + a use-phase travel keep-out (V-08).
- **collision_hint** = 3 rail boxes (neck, head, stop-tab) + 5 carriage boxes (top, 2 sides, 2 lips),
  every prim `source`-stamped (D-M8-4).
- **verification** = P-SLIDE V-A + V-B, plus PR-KEEPOUT for the imposed keep-out (so no use behaviour
  is left unverified — V-01 clean). Protocols are **card knowledge** (D5), never LLM-authored.

![section + clearance](out/slide_section_clearance.png)

The section shows the retention design: the carriage **rests on the head-top** (Z load path, kept
**exact** — the M0 lid-on-box lesson, one tied plane only), the sides hold Y with clearance `c`, and
the lips sit `c` below the head shoulders so the carriage lifts at most `c` before they catch.
Retention verified by boolean at build time: lift > 0.35 mm → the lips capture the head (0→45 mm³).

![3-view](out/slide_3view.png)

## P-SLIDE (§6.3) — [`out/t2_slide_verdict.json`](out/t2_slide_verdict.json) (guard trio)

| mode | result | s_max | off-axis | derail | back-drift |
|---|---|---|---|---|---|
| **V-A** (declared prismatic joint) | **5/5 PASS** | 66.2 mm | 0.00° | no | 4.35 mm |
| **V-B** (contact-only) | **G-CONV settling-transient (recorded, not tuned)** | — | — | — | — |
| V-B *observed, not gated* | would-gate **PASS** | 60.5 mm | 2.03° | no | — |

![V-A s(t)](out/t2_slide_V-A.png)

**V-A** (required): an axial force ramp drives the carriage past the 60 mm stroke; the joint's travel
range models the physical stop; **joint frictionloss** (a slide's real Coulomb friction — a physical
property, not a preset knob) holds it after release, so back-drift is 4.35 mm ≤ 5. It tracks dead
straight (off-axis 0°). Video: [`out/t2_slide_V-A.mp4`](out/t2_slide_V-A.mp4).

**V-B** (target): G-CONV — M0's *coherence* gate — fails at-rest with peak-velocity 2.13 > 0.5 and
drift 0.0085 > 0.005. **This is not a jam and not a broken model:** the carriage settles to a stable
rest (0.36 mm drop, 0.49° pitch, `ncon`=6 constant). It is the **settling transient of a drop-in
assembly meeting the stiff frozen preset** — a sub-mm drop into the groove gives a brief velocity
spike that M0's hinge-tuned thresholds reject. Per the brief and the R2b precedent, this is
**RECORDED, not tuned** — the frozen preset (R5) is untouched.

To characterise the geometry rather than stop at "G-CONV failed," an **observed-not-gated** run
(seat the carriage first — the honest initial condition for a drop-in slide — then actuate) shows the
**T-rail geometry does produce and retain the slide DoF**: s_max 60.5 mm (reaches stroke), off-axis
2.03° (< 3°), no derail. It *would* pass the P-SLIDE gates if G-CONV admitted the settled start.
Video: [`out/t2_slide_V-B.mp4`](out/t2_slide_V-B.mp4).

**Honest reading:** V-A (required) is a clean pass. V-B's geometry works when observed, but does not
clear M0's coherence gate at the frozen preset from a floating start. The gap is the same *class* as
R2b — a frozen-preset interaction — but milder (a settling transient, not a divergent instability),
and it is a candidate for the same `preset_v2`-time revisit, or for a G-CONV that admits a bounded
settle-in for drop-in assemblies. Neither is done here; both are recorded.

## DRAFT (D-E-10) — the alignment ontology gap, for your ruling

The Hard anchor's drawer runs on **two** slide_rail instances that must be **parallel and level**.
That is an **instance↔instance** constraint (E_left ∥ E_right, same height) — a relationship between
two *elements*, which the current ontology has no first-class way to state. AssemblyRule (D-ONT-12)
is the natural home, but its two kinds don't obviously fit:

- `exclusion` = a sweep non-interference (latch ∉ lid-sweep) — a *negative* volume constraint.
- `resource` = a scalar budget (Σ contributors ≤ budget) — a *scalar* constraint.

Parallel-and-level is neither: it is a **pose relation** between two elements' travel axes (their
directions must be equal, their mount planes coplanar). Three options:

| # | option | what it is | cost |
|---|---|---|---|
| **A** | **third AssemblyRule kind: `alignment`** | predicate `{axes:[E1.travel_axis, E2.travel_axis], relation:"parallel", level:true}`, checked at t0 by comparing the two bound anchor frames. First-class, symmetric, provenance-tagged like the others. | one new `kind` + one validator arm + one t0 checker. Keeps all instance↔instance constraints under AssemblyRule (the D-ONT-12 home). |
| B | **a shared datum both rails bind to** | introduce a `datum`/reference feature; both rails' `travel_axis` bind to it, so parallelism is *by construction* (they reference the same axis) rather than checked. | new ontology entity (datum) + binding semantics; parallelism becomes unfalsifiable (can't be violated → can't be a graded requirement). Loses the "physics discovers the requirement" property. |
| C | **`resource` with an angle/offset budget** | encode as Σ|axis-angle-difference| ≤ ε and Σ|height-difference| ≤ ε, reusing the existing `resource` kind. | no new kind, but abuses `resource` (it's a *pose* relation, not a shared budget) — the predicate would misname what it checks, the m8-class error of a label that lies about its content. |

**Recommendation: A (`alignment` kind).** It is the honest first-class form: the constraint IS a
relation between two elements, AssemblyRule IS the instance↔instance home (D-ONT-12), and a t0
checker comparing the two axis frames makes it *checkable and falsifiable* (a mis-aligned pair fails,
the way a physics-derived requirement should). B makes it unfalsifiable; C makes `resource` lie about
what it holds. Flagged as DRAFT — **your ruling** before it lands (not smuggled, per the brief).

## Decisions

**D-E-9** (API economy — logged separately) · **D-D-1** slide_rail card built (T-rail, all-boxes,
§3.5 chain; V-A 5/5, V-B settling-transient recorded) · **D-E-10 DRAFT** the alignment ontology gap
(three options, recommend the `alignment` AssemblyRule kind).

Suite **54/54**.

## Reproduce

```
./bin/py tasks/build_goldens.py                       # writes slide_fixture.json (CLEAN)
./bin/py tasks/run_m10_slide.py verify/t2_physics/out_slide   # P-SLIDE V-A + V-B
./bin/py m10_slide_rail/build_review.py               # section + 3-view renders
```
