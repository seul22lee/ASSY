# DECISIONS_LOG — Running record of decisions & theses (separate add-on file)

Yes — proceed with V-B on the hinge. But fix the experimental protocol before running:

**Setup**: same hand-built box. All bodies free (6-DOF), no declared joints. Pin, lid,
box are separate free bodies. Bore must be present in the collision model — that's the
whole point.

**Pass criteria (defined now, not after seeing results)**:
1. Pin retention: pin stays in the bore for the full run — radial drift from the hinge
   axis ≤ clearance + 0.1 mm, no escape along the axis beyond insertion depth.
2. θ_max ≥ 90° under follower force (per D16).
3. Penetration ≤ 0.2 mm outside the pin–bore interface; at the interface, report the
   value but treat ≤ clearance as acceptable.
4. Return-to-closed ≤ 5° on reverse ramp.
5. Multi-seed: 5 seeds, ≥4 pass. Same contact preset as M0 — do NOT retune per-run
   (R5). If the preset must change, change it globally and re-run M0 V-A as a
   regression check before accepting the new preset.

**Collision strategy — try in this order, and record results for each attempted**:
(a) CoACD on the knuckles/bore (this is the untested code we need data on — record
    piece count, and produce the visual-vs-collision overlay zoomed on the bore, per D15).
(b) If the bore is mangled: MuJoCo SDF collision for the knuckle parts.
(c) If both fail: primitive ring approximation of the bore (collision_hint pathway).
Whichever level works becomes the documented default for P-GEAR planning — say so
explicitly in FINDINGS.

**Timebox**: if a level clearly fails, capture the failure mode (screenshots, penetration
traces) and move to the next — the experiment pays out either way. Don't grind on solver
tuning beyond the §6.4 timestep fallback.

**Deliverables**: standard artifact set (video, θ/F/pin-drift plots, overlay, verdict
JSON, CSVs), FINDINGS section, and a draft D18 row for DECISIONS_LOG stating which
collision pathway retires R1 fully (or that none does, and what that means for P-GEAR).
Keep the V-A and V-B runs side by side in the report — the comparison itself is paper
material.


> Continues D1–D12 from MECHSYNTH_SPEC_v0.1 §0.
> Convention: whenever a decision or thesis is settled during implementation or an
> experiment, record it here immediately — one row per item — with evidence
> (experiment, anecdote, or document) linked. This file is source material for the
> paper's Introduction/Discussion.

| # | Decision / Thesis | Evidence | When |
|---|---|---|---|
| D13 | **Ontology is a precondition for verifiability.** Verification is a function of representation: every checker question ("is the pin insertable?", "what is the hook strain?") requires a referent, and an unstructured blob contains no nouns to check — hence no predicates. This is why "naive generation + downstream checker" cannot work. | M0 pin-bore anecdote (m0/FINDINGS.md): constraint imposed by the card → registered in IR → caught by Tier0 boolean check. V-A simulation is blind to it in principle (bore absent from collision model). phase=assembly | M0 |
| D14 | No collision primitive of a moving piece may share a face plane or tangency with a static piece (invariant for `collision_hint()`). | M0: degenerate flush lid–wall contact launched the lid at 214 rad/s. Expected to recur at M3 (drawer-in-cabinet is flush-panel-in-flush-opening geometry) | M0 |
| D15 | G-CONV must additionally assert visual bbox ≈ collision bbox. Divergence between video and physics is the most dangerous bug class here, because it poisons G-H (human visual approval). | M0: mm/m unit mismatch — physics correct, video wrong by 1000× | M0 |
| D16 | P-HINGE actuation must be a follower force (normal to the lid face). A world-vertical force has moment arm cos θ·F·R → exactly zero at θ=90°, the criterion angle: unsatisfiable as written. **The verification suite is itself subject to verification.** | M0 measurements: vertical force stalls at 78.4°; follower force passes at 102.2° | M0 |
| D17 | R1 is retired only for mode V-A. Full retirement requires a bore holding a pin through contact alone (V-B) — the same capability P-GEAR mandates. | M0 "honest limit" section; next experiment = V-B hinge | M0 |

<!-- Append new rows above. Instances of the phase-verification division of labor
(which tier caught which phase's defect) are Discussion material for the paper —
always note the phase in the Evidence column. -->
