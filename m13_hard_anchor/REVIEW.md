# M13 · THE HARD ANCHOR — REVIEW (crank-operated lift platform, §8.2 retargeted)

**Outcome: the second benchmark is a crank-driven vertical LIFT PLATFORM, assembled and V-A-verified,
and the physics discovered a real design requirement (a holding brake).** Same mechanism as the
drawer (`slide_rail` ×2 + `rack_pinion`), the verified geometry rotated so **travel is vertical and
gravity acts along it** — the case where the rack-pinion is *functionally necessary*, not
over-engineered. The deterministic spine carries over verbatim; P-SLIDE + P-GEAR pass V-A under
gravity; the new P-HOLD test fails honestly, revealing the lift needs a brake.

| what | artifact | result |
|---|---|---|
| the platform | [4-view](out/anchor_hard_4view.png) · [exploded](out/anchor_hard_exploded.png) | platform on **vertical rails**, side crank, rack up the platform's back |
| section | [one figure](out/anchor_hard_section.png) | rail↔carriage engagement + pinion↔rack mesh |
| the ⑤ chain | [s5 table](out/s5_chain.md) | drawer_w / L_rack / axis / engagement derived + cited (carries over) |
| alignment firing | [t0 report](out/t0_assembly_rules.json) | parallel/level on real geometry — **PASS, 0.00° / 0.00 mm** |
| it raises | [P-SLIDE V-A](out/lift_pslide_VA.png) · [mp4](out/lift_pslide_VA.mp4) | platform + 0.5 kg raised 128 mm **against gravity**, off-axis 0.00° — **5/5** |
| it transmits under gravity | [P-GEAR V-A](out/lift_pgear_VA.png) · [mp4](out/lift_pgear_VA.mp4) | crank→lift on the π·m·z line, 119.9 mm, ratio resid 0.01% — **5/5** |
| it does NOT hold | [P-HOLD V-A](out/lift_phold_VA.png) · [mp4](out/lift_phold_VA.mp4) | crank released → back-drives **62 mm** — **0/5, the finding** |

## Why a lift, not a drawer (D-M13-2)

A rack-pinion **drawer** is over-engineered: a capable model would correctly *omit* the gear and just
pull the drawer, so a drawer golden would **punish good judgement**. A **vertical lift** flips this —
gravity acts along the travel axis, so the transmission is load-bearing: it both raises the load and
(ideally) holds it. Here the gear is *necessary*, and the benchmark rewards including it.

The mechanism is unchanged — the **verified** drawer geometry rotated −90° about Y so travel is +Z.
The carves, the T-rail, the involute pinion, the L3 collision hint, and the equality coupling are
reused **verbatim**; only the physics layer applies the tilt. What does **not** carry over is named:
gravity is now a **load along travel** (P-SLIDE must overcome weight to *raise*, not just friction),
and the **static/hold** behaviour is new (a drawer never had to resist back-drive).

## Ruling record

- **D-M13-1 (reframe approved):** the m13 kinematic finding was real — pinion axis ⊥ travel, and the
  proven T-rail is a floor rail. Reusing the carves verbatim was correct. "Front-knob + wall-rail" is
  logged as a future carve-generalization item, not now.
- **D-M13-2 (retarget):** the lift, as above. Drawer kept as the labeled alternate
  (`tasks/anchor_hard.json`).
- **D-M13-3 (DRAFT — static/hold schema):** see the last section.

## ⑤ + t0 — carry over identically

The lift golden is validator-CLEAN; ⑤ resolves the same §8.2 chain (drawer_w 115.30 · L_rack 167.12 ·
axis_offset 30 · engagement 42 · transmission 188.50 mm/rev; **stroke 120 mm** — the 200 mm tower
raises the platform 120 mm leaving ≥45 mm engaged). ⑥ compiles the same 5 bodies. The **alignment
AssemblyRule fires and PASSES on the real geometry — `parallel 0.00°, level Δz 0.00 mm → ALIGNED`** —
because the two rail axes are still the matched pair; the vertical reframe doesn't disturb it.

## t2 — the physics, gravity along travel

- **P-SLIDE V-A — 5/5 PASS.** The platform (carriages + tray + rack + **0.5 kg load**, welded) on a
  declared +Z prismatic joint is **raised against gravity** to 128 mm (past the 120 mm stroke), off
  axis 0.00°. The declared joint carries the vertical load without racking.
- **P-GEAR V-A — 5/5 PASS.** A declared crank hinge (horizontal axis) coupled to the platform slide
  by a near-rigid equality at rp. **Turning the crank raises the load, and the height tracks π·m·z
  per rev to 0.01% — with gravity now along travel.** This is the retarget's headline question, and
  the answer is yes: the ratio holds under load (the constraint force counters gravity). The measured
  curve lies exactly on the §3.6 line.
- **P-HOLD V-A — 0/5 FAIL, and this is the finding.** With the crank *released* (no drive) and
  physically-**sourced** Coulomb friction on the hinge (μ·W·rp = 0.059 N·m), the platform under the
  0.5 kg load **back-drives 62 mm** (falls). It cannot self-lock, because the gravity torque
  (W·rp = 0.198 N·m) far exceeds any friction a μ = 0.30 mesh provides. **A plain rack-pinion crank
  lift is not self-locking; it REQUIRES a holding brake or pawl** — a design requirement the system
  discovered from its own physics (the pin_hinge-stop pattern, D-M8-5). This is reported as a FAIL,
  not tuned to a pass (the m8 lesson: a value chosen to make a gate go green is a fabrication).

Guard trio on the verdict ([t2_lift_verdict.json](out/t2_lift_verdict.json)): `decision_row`,
`compile_hash`, `shape_assert` (P-SLIDE + P-GEAR + P-HOLD present, gravity along travel). G9 G-CONV ok.

## D-M13-3 DRAFT — does "holds under load without input" need first-class schema?

The static/hold requirement **is already expressible** — no hard gap:
`phase=static` + `motion=fixed` + `Behavior.load={mass_kg, direction}` (all existing fields), with the
"resists back-drive" requirement carried as a **P-HOLD criterion** (`backdrive_mm ≤ ε`; the
measurement is registered). The open question is only whether back-drive-resistance deserves
first-class status. Three options:

- **(A, recommended)** keep it in the verification layer — static/fixed + load + a P-HOLD criterion.
  No schema change; the load already lives on the behaviour, "without input" is a verification
  *actuation* (release-and-watch), and "must not back-drive" is a *criterion*. None of that is a new
  motion type.
- **(B)** a new `MotionKind = "hold"`/`"self_lock"` — first-class, but adds a kind for one behaviour
  and conflates "no motion" with "resists motion under load".
- **(C)** a `MotionSpec.holds_under_load` / `HoldSpec` attribute — first-class without a new kind, but
  unused elsewhere so far.

Recommendation A; **flagged, not smuggled** — awaiting ruling.

## Honest checkpoint — V-B follows

Per the standing rule: **P-SLIDE V-B** (two-rail welded-platform contact) + **P-FULL** are the next
scoped step (m10's lesson set applies — all_parts_retained, declared seat contacts, sourced
friction). **P-GEAR V-B** stays R2b-deferred (D-M1-7). And the **holding brake** the P-HOLD finding
demands is a new element to add before a lift is a complete product.

## Status

- Goldens: `tasks/anchor_lift.json` (PRIMARY, validator-CLEAN) + `tasks/anchor_hard.json` (drawer alternate).
- Spine: `m13_hard_anchor/build_review.py` (VARIANT="lift") → ⑤ table, alignment, renders, IR graph.
- Physics: `m13_hard_anchor/p_lift.py` → P-SLIDE + P-GEAR + P-HOLD V-A, plots + mp4, verdict.
- Suite: 72/72; both goldens build clean.
- **Open:** P-SLIDE V-B · P-FULL · P-GEAR V-B (R2b) · a holding brake element (P-HOLD finding) · the D-M13-3 ruling.
