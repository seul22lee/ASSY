# M0 Findings — hand-built hinged box → STEP → MJCF → P-HINGE

## M0-STRETCH CLOSED — verdict

| Result | Evidence |
|---|---|
| **R1 (STEP→MJCF destroys the mechanism) RETIRED** | Bore holds pin, revolute DoF emerges from contact alone |
| **V-A (constraint-assisted)** | follower P-HINGE **5/5**, both variants (§1) |
| **V-B (contact-only), stop variant** | **PASS 5/5** — pin held, opens 115°, settles closed (§4.4) |
| **V-B (contact-only), no-stop baseline** | **FAIL 1/5** by design — the control (§4.4) |
| **Collision pathway** | ring decomposition via `collision_hint()`; CoACD swallows the bore, SDF unavailable (§4.1, D18) |
| **Decisions** | **D13–D23 all CONFIRMED** (`../DECISIONS_LOG.md`) |

The no-stop baseline failing while the stop variant passes is the load-bearing result: the suite
**discriminates a correct design from a defective one**, so D13–D23 are corrections, not
relaxations. M1 (gear / P-GEAR) is a separate session; D21 and D23 carry forward as hard
constraints on it.

> Per spec §12, this file is the input to the next spec revision. Items tagged **[SPEC]**
> are proposed amendments to `MECHSYNTH_SPEC_v0.1.md`. **G-CONV green, P-HINGE V-A green 5/5.**

---

## 1. Result

| Gate | Criterion | Measured | Verdict |
|---|---|---|---|
| Tier0-lite | 3 solids, watertight, positive volume | 31109 / 14433 / 385 mm³ | PASS |
| Tier0-lite | no closed-state interference | 0.000000 mm³ | PASS |
| Tier0-lite | lid sweep 0–95°, N=36, no interference | 0.000000 mm³ | PASS |
| G-CONV (a) | mass > 0 | 39.51 / 18.33 / 0.49 g | PASS |
| G-CONV (b) | no initial penetration | 0.0000 mm | PASS |
| G-CONV (c) | at rest 1 s under gravity | drift 0.000 mm, peak \|v\| 0.11 | PASS |
| P-HINGE | θ_max ≥ 90° | **102.2°** | PASS |
| P-HINGE | sweep penetration ≤ 0.2 mm | **0.104 mm** | PASS |
| P-HINGE | θ_final ≤ 5° (returns closed) | **−0.0°** | PASS |
| P-HINGE | multi-seed verdict (≥4/5) | **5/5** | PASS |

Artifacts in `m0/out/`: `t2_P-HINGE_follower.mp4`, `t2_P-HINGE_follower.png` (θ/F/penetration
vs t), `t2_conv_overlay_V-A.png` (visual vs collision), `t2_verdict.json`, `*.csv`, `*.step`.

The geometry is a *real* printed pin hinge — 3 interleaved knuckles, 0.30 mm PETG print
clearance, separate insertable pin, chamfer per the card rule — not an idealized joint.
That was the point: an idealized hinge would have passed and proved nothing.

---

## 2. The contact preset (spec §6.2 / R5) — FROZEN

```
timestep  0.0005 s        integrator  implicitfast     cone  elliptic    impratio  10
solref    (0.001, 1.0)    solimp      (0.99, 0.9999, 0.0001)             condim    4
friction  mu = 0.30 (PETG)
```

**Fixed by a physical requirement, not by what made the test go green.** The rule:

> Contact stiffness must make penetration under the assembly's own working loads negligible
> against the smallest feature the design is built from — the **0.30 mm PETG print
> clearance**. Target: steady-state penetration ≤ 0.05 mm (≤ 1/6 of clearance).

Tuning history (the only preset change made, and why):

| # | solref | solimp | penetration | Why changed |
|---|---|---|---|---|
| 1 | (0.002, 1.0) | (0.95, 0.99, 0.001) | **0.284 mm** | Rejected: the sim squashed parts by ~the entire print clearance. Clearances become meaningless — the model cannot resolve the features the project exists to verify. |
| 2 | (0.001, 1.0) | (0.99, 0.9999, 0.0001) | **0.104 mm** | **Adopted.** timeconst = 2×timestep (MuJoCo's recommended floor = stiffest stable value); impedance saturates within 0.1 mm. |

Note preset #1 *also* failed the 0.2 mm criterion, so the change was forced by the gate, not
chosen to satisfy it. **[SPEC]** Record this preset in §6.2 at M1 and do not vary it per
experiment.

---

## 3. Bugs and design errors found (the actual value of M0)

### 3.1 The pin had no through-bore — caught by Tier0, before any simulation
The box lugs and lid tab ran straight through the space the pin occupies (7.3 mm³ and 43.0 mm³
of overlap). The pin was *embedded in solid plastic* — un-insertable, violating the pin_hinge
card's own `assembly` constraint (§3.3). Fixed by a **bore keep-out radius**: nothing but the
knuckles may enter `bore_d/2 + clearance` of the axis; lugs approach from below, tabs from the
front, and the bore is cut once from the finished part.

**Lesson:** running exact-B-rep Tier0 *before* Tier2 was worth it. Had this gone straight to
MuJoCo, the primitive collision hints would have hidden it completely (a solid knuckle
primitive has no bore to be blocked), and the sim would have happily reported a working hinge
for a part that cannot be assembled. **[SPEC]** This is a strong argument for §5's ordering
being load-bearing, not bureaucratic.

### 3.2 Degenerate box–box contact launched the lid at 214 rad/s — G-CONV caught it
Under gravity alone, the lid settled correctly for 30 steps (penetration decaying to
−0.0002 mm, ω → 0.001) and then, in a **single 0.5 ms step**, jumped to +6.1° with a
**−57.7 mm / 362 N** contact between parts 0.0002 mm apart.

Cause: the lid is flush with the box walls, so its collision box was coplanar with the wall
tops (z = 40, the real contact) **and** with the wall sides (x = ±40). Two tied separating
axes → MuJoCo's box–box routine flipped its normal and reported penetration straight through
the wall.

Fix — a rule for `collision_hint()`, not a magic number:

> **No collision primitive of a moving piece may share a face plane with, or be exactly
> tangent to, a primitive of a static piece.** Inset the *moving* piece's primitives by
> `COLLISION_EPS = 0.2 mm` in the tied directions. Leave the load-bearing plane exact.

This cannot hide a real interference, because Tier0 has already proved in exact B-rep that
there is none. **[SPEC]** §3.2's `collision_hint()` contract must state this invariant —
every card that emits box primitives (`box_shell`, `lid_panel`, `drawer_tray`,
`cabinet_shell`, `rack_bar`) can hit it, and the drawer/cabinet pair in the Hard anchor is
*exactly* this flush-panel-in-flush-opening geometry. **Expect this to bite again at M3.**

### 3.3 Visual meshes were 1000× too large — the sim was right and the video was lying
build123d exports STL in **mm**; MuJoCo reads mesh files as **m**. Collision primitives and
inertias were computed in metres and were correct — so *every gate passed* — but the visual
meshes were 1000× oversized and the camera was rendering from inside an 80-metre box.

This is the most dangerous class of bug this project can have: **numerically correct, visually
false.** Gate G-H (§5) is a human looking at a video; a wrong video means a human approving the
wrong thing with full confidence. Caught only because a human actually looked.

**[SPEC]** Two consequences:
- The §6.2 visual-vs-collision overlay is **mandatory and load-bearing** — it is the artifact
  that makes this class of bug visible. Implemented as `m0/overlay.py`.
- Add to G-CONV: **assert the visual mesh bbox matches the collision bbox** to within the
  approximation tolerance. A pure unit-mismatch is then impossible to ship.

### 3.4 Force applied at a fixed world point instead of a material point
`mj_applyFT` was given a constant world coordinate, so the moment arm never changed as the lid
rotated — silently turning *any* force mode into a constant-moment-arm actuator and masking
§3.5 entirely. Fixed by reading the lid tip's site position each step. **Any force-driven
protocol must apply force at a moving material point** — this will recur in P-SLIDE (drawer
front) and P-FULL (knob).

### 3.5 **[SPEC] P-HINGE's actuation is unsatisfiable as written**
§6.3 specifies a force ramp in the *"vertical opening direction"*. Taken literally (world +Z),
the torque it exerts about the hinge is

```
tau  =  cos(theta) * (F * R_tip  -  m * g * R_com)
```

The moment arm collapses as the lid rises and is **exactly zero at θ = 90°** — the very angle
the protocol requires the lid to reach. The actuator has no authority precisely where the
criterion lives. Measured: `world_z` stalls at **78.4°** and cannot certify θ_max ≥ 90°.
Pushing harder does not fix it; it only buys ballistic overshoot, not controlled opening.

A **follower force** (normal to the lid face — what a finger does) has constant moment arm
`F·R` in both directions and certifies cleanly: **102.2°**, closes to −0.0°.

Both modes are implemented and both are run every time, so this is demonstrated rather than
asserted (`t2_P-HINGE_world_z.*` vs `t2_P-HINGE_follower.*`).

> **Proposed amendment to §6.3 P-HINGE:** *Actuate: force ramp F: 0→F_max applied normal to
> the lid face at the midpoint of the lid's free edge, then reversed.*

---

## 4. Mode V-B (contact-only) — R1 retired, and V-A shown to be blind

Run after V-A, per your protocol. No joints declared: box, lid and pin are three free 6-DoF
bodies, and the revolute DoF must **emerge from the pin sitting in the bore**. Full decision
record and the P-GEAR consequences are in [`../DECISIONS_LOG.md`](../DECISIONS_LOG.md) (D18).

### 4.1 The collision ladder — every level attempted, recorded

| Level | Pathway | Bore patency | G-CONV | Verdict |
|---|---|---|---|---|
| (a) | CoACD | **SWALLOWED**: best of 5 configs → wall at 2.014 mm vs 2.000 mm pin = **10% of clearance retained**. Default `threshold=0.03` → wall at 1.083 mm, *inside* the pin. | FAIL | **REJECTED** |
| (b) | MuJoCo SDF | **UNAVAILABLE**: the plugin ships analytic shapes only (`bolt/bowl/gear/nut/torus`). No mesh-SDF exists, so a carved bore is inexpressible. | n/a | **UNAVAILABLE** |
| (c) | **Ring of convex wedges** (card `collision_hint()`) | **OPEN**: wall at 2.192 mm, **128% of nominal clearance** (bounded +0.042 mm generous, never tight) | **PASS** | **ADOPTED** |

CoACD parameter sweep (all 5 attempted, per your instruction):

| config | hulls | min wall r | |
|---|---|---|---|
| `threshold=0.03` (default) | 8 | 1.083 mm | swallowed |
| `threshold=0.01, res=4000` | 11 | 1.821 mm | swallowed |
| `threshold=0.005, res=10000, merge=False` | 25 | 2.014 mm | open, but 10% clearance |
| `threshold=0.01, res=20000, preprocess=off` | 12 | 1.913 mm | swallowed |
| `threshold=0.02, res=20000, preprocess=on` | 9 | 1.345 mm | swallowed |

**"Does the pin fit" is the wrong test.** A bore whose clearance has been eaten is a seized
hinge, and it passes a naive patency check while being physically wrong. The gate is
*clearance retention* (≥50% of nominal), measured by ray-casting outward from the axis — the
bore is internal, so **no camera angle can see it**, and the overlay PNG cannot catch this.

### 4.2 R1 is retired — the geometry *is* a hinge

Pathway (c): the pin is held by the bore alone. Pin radial drift **0.32–0.46 mm**, axial drift
**0.09–0.30 mm**, θ reaching 115° with **no joint declared**. The revolute DoF emerges from the
geometry. That is the strict form of the R1 question, and the answer is yes.

### 4.3 The big one: **V-A cannot see a missing end stop; V-B can**

The baseline lid is *over-centre* — past 90° gravity pulls it further open — and it has **no
end stop**. It folds right over. But:

> **V-A passes 5/5 on both the no-stop design and a stop-flange variant.** It cannot tell them
> apart, because MuJoCo's joint `range` silently supplies the very feature one design lacks.
> V-B separates them instantly: **220° (folds flat) vs 115° (stops)**.

A constraint-assisted simulation will confirm any mechanism whose missing features its own
joint declarations happen to supply. This is an argument for V-B being **required rather than
optional**, and it is paper material.

Per D19, the missing stop is reported as an **observable, not a criterion** — the Easy anchor's
behaviour spec asks for ≥90° opening and a click shut; it never asks for an angular limit:

```json
"observables": {"overtravel_check": {
    "theta_overtravel_max_deg": 220.47, "hard_stop_contact": true,
    "flag": "no angular limit -- lid free to fold flat" }}
```

The `stop` variant is carried **alongside** the baseline, not substituted for it, so the intent
layer can decide with evidence rather than inherit a design decision I smuggled in under cover
of a bug fix.

### 4.4 V-B PASSES (stop variant) — R1 retired, M0-stretch closed

Final protocol: gentle quasi-static open → release at θ_target → reverse-ramp, releasing again
at the over-centre point so gravity seats the lid → base welded (D23) → penetration stratified
by contact intent (D22), intended-contact impact *magnitude* recorded as an observable.

**Hard criteria are functional outcomes the geometry answers (D22 amended):**

| Criterion | no-stop | stop | |
|---|---|---|---|
| pin radial drift ≤ 0.40 mm | 0.34–0.50 | 0.24–0.26 | fail (nostop) / **pass** |
| pin axial drift ≤ 3.0 mm | 0.08 | 0.03 | pass |
| θ_max ≥ 90° | 220 | 115 | pass |
| travel interference (non-intended) ≤ 0.2 mm | 0.10 | 0.00 | pass |
| pin/bore interface ≤ clearance (0.30) | **0.32** | 0.07 | fail (nostop) / **pass** |
| settles closed: θ_final ≤ 5°, no bounce | 0.0 / 2.7 | 0.0 / 2.8 | pass |
| **verdict** | **FAIL 1/5** | **PASS 5/5** | |

**Observable — closing-seat impact magnitude:** stop 0.18–0.53 mm, nostop up to 0.91 mm.
Flagged (> 0.30 mm clearance scale), never gated: in a soft-constraint engine this depth
measures the frozen quasi-static preset's compliance (D17), not the geometry. An
impact/durability spec would instrument peak contact force / impulse with an impact-validated
preset instead of depth (D22 amended).

**R1 is fully retired for the pin hinge.** The bore holds the pin, the revolute DoF emerges
from contact alone, and the corrected design certifies clean across 5 seeds.

**The control holds.** The no-stop baseline **fails 1/5 under every amendment** — the fold-flat
jostles the pin radial past 0.40 mm (seeds 2–4) and the pin/bore past clearance (seed 1). That
is the suite's discriminative power: these decisions are **corrections, not relaxations**. A
suite that passed both designs would be worthless; this one separates them.

Each lever, and what it did:
- **D19 release-at-target** — fixed drive-momentum overshoot and the 123 mm box-slide bug.
- **D22 stratification** — separated stray travel interference (defect) from intended
  seat/stop/bore contacts; travel interference is now 0.00 mm on the stop variant.
- **release-at-over-centre close** — stops driving the lid *through* its seat; fixed bounce.
- **D23 welded base** — removed the unfixtured-box tumble that broke pin retention (a seed
  drifted to 0.52 mm) and inflated seat variance. Necessary at M0, not just an M1 nicety.
- The seat-impact *magnitude* is the one thing no protocol lever moved — correctly, because it
  is a preset-compliance artefact (D17/D22 amended), now an observable.

### 4.5b G-H admissibility (D15, from a live provenance scare)

During G-H review the reviewer saw a "flung" object in `t2_V-B_ring.mp4` and could not tell
which run it was. Root cause: the video name carried no variant, so **two different runs**
(stop, no-stop) wrote to the same basename in different directories, and a bare render carries
no evidence tying its motion to the scored numbers. The flung object was the no-stop fold-flat
(expected) — but nothing in the artifact *proved* that.

> **G-H admissibility rule (D15):** a video is admissible for human approval only if
> (a) its filename is **variant- and seed-explicit** (`t2_VB_ring_<variant>_seed<k>.mp4`), and
> (b) it carries a **HUD burned from the scored series** — the same per-step values the verdict
> is built from, not a re-derivation. A bare render is **inadmissible**: it cannot be shown to
> be the run it claims to be.

Implemented as `vb.py relabel`. The three approved videos: `t2_VB_ring_stop_seed0.mp4` (PASS,
opens 115°, seats), `t2_VB_ring_nostop_seed0.mp4` (the passing no-stop outlier, folds to 220°),
`t2_VB_ring_nostop_seed3.mp4` (a **failing** seed — HUD shows pin radial crossing 0.40 mm during
the fold, the actual defect). **G-H APPROVED on all three.**

### 4.5 Runner bug found: finite-but-absurd divergence

A blow-up need not produce NaN. One V-B seed put the pin **405 metres** from its bore with every
value finite, and an `isfinite` gate waved it through as a real measurement. Divergence
detection now carries a **model-scaled sanity bound** — pin travel past `10 × model.stat.extent`,
or |qvel| > 1e3, trips the §6.4 half-timestep retry. This is a runner bug class, not a physics
result: any observable read off a diverged state is noise wearing a number's clothes and must be
caught before it reaches a verdict.

## 5. What M0 still did NOT prove — honest limits

- One material, one element, one anchor task. **Nothing here has been demonstrated for gears** —
  and D18/D21 warn that CoACD will do to an involute flank exactly what it did to the bore, and
  that `mujoco.sdf.gear` would verify a gear we did not design.
- The box slides 2–5 mm under load (all bodies free in V-B). Recorded as an observable.
- **V-B setup noise (candidate refinement for M1):** with *every* body free, opening the lid
  applies reaction torque to an unfixtured box and it visibly tips/rotates (the box_slid_mm
  metric only catches COM translation, not this rotation). The R1 question — "does the pin+bore
  geometry produce the DoF" — needs the lid and pin free, but freeing the *base* too adds noise
  that is not part of that question. A cleaner V-B would **weld the box to the world** (a
  fixture, not a joint declaration, so still honest contact-only for the pin/bore). Not changed
  this session; flagged for M1.

---

## 5. Environment (reproducibility)

- Env: `psed310` (conda, Python 3.11.14). Run everything through **`./bin/py`**.
- **`LD_PRELOAD=$psed310/lib/libexpat.so.1` is mandatory.** Importing OCP (the OpenCascade
  kernel under build123d) drags in the system libexpat 2.2.x via its X11/fontconfig
  dependencies; Python's `pyexpat` then binds to that instead of the env's 2.7.4 and dies with
  `undefined symbol: XML_SetReparseDeferralEnabled`. This breaks **all XML in-process — which
  includes MJCF.** `bin/py` handles it.
- **`MUJOCO_GL=egl`** — headless box, renders on the A6000s. `bin/py` handles it.
- Everything written to `meshes/` is in **metres**. No exceptions (see §3.3).

## 6. Reproduce

```bash
./bin/py m0/hinge_box.py      # build 3 STEP files + manifest
./bin/py m0/sweep_check.py    # Tier0-lite: solids, interference, clearances, 36-step sweep
./bin/py m0/step2mjcf.py V-A  # STEP -> MJCF (primitive collision hints)
./bin/py m0/overlay.py V-A    # mandatory visual-vs-collision overlay
./bin/py m0/p_hinge.py V-A    # G-CONV + P-HINGE, 5 seeds, both force modes
```
