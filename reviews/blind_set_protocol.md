# Blind held-out benchmark — authoring protocol (external review point 1)

**Why this exists.** Our current 16-task ladder (m14) was authored by the system's builders, so it is
a **development set**, not a blind test — the reviewer's point 1. To claim generalisation we need a
test set written by people who have **never seen the system, its vocabulary, or its examples**, then
frozen and scored once. This document is (A) the one-page sheet we hand each external author, and (B)
our internal notes for recruitment and sealing. **Part A must be shown to authors; Part B must not.**

---

## PART A — instruction sheet for authors (this is all they see)

**Your task.** Write **30–50 short design requests** for small mechanical objects that could be
**3D-printed in plastic** and have **at least one moving or working part** — the kind of everyday
gadget you might ask a designer to make.

**Write each request the way you'd describe it to a person**, in one or two plain sentences. Say
*what it should do*, not how to build it. Add any specific numbers that matter to you (size, force,
angle, how far something travels, how much it should hold).

Good examples (yours should be different):
- "A pill box with a lid that clicks shut so it won't pop open in a bag."
- "A phone stand whose arm tilts back and stays wherever I set it."
- "A tape dispenser where a lever pushes the tape forward when I press it."
- "A desk drawer that slides out when I turn a small knob on the front."
- "A vent cover whose flap opens no more than 30 degrees, then stops."

**Please deliberately include a few requests you suspect are hard or even impossible** — e.g. asking
for something to hold a heavy load with no visible mechanism, or two requirements that seem to fight
each other. We want those. Mark them with `(I think this may be impossible)` if you like — a guess,
not a certainty.

**For each request you may optionally add 1–3 "done when…" lines** in your own words — how you'd know
it works ("done when the lid stays shut if I shake it", "done when it opens at least 90 degrees").

**Please do NOT:**
- look up or reference any CAD tool, part library, mechanism catalogue, or engineering handbook;
- name specific parts or features (no "add a snap-fit / living hinge / rack and pinion") — describe
  the *behaviour* and let the design be someone else's job;
- ask for electronics, motors, springs you'd buy, adhesives, or non-mechanical objects;
- copy requests from a website or from each other.

**Spread your requests around** — vary the size of the object, how it moves (things that swing, slide,
lift, turn, click, or just hold still), and how strict you are (some loose, some with exact numbers).
Aim for variety over cleverness.

**Format.** One request per line (or short paragraph), numbered. Plain text or a doc is fine. Put your
name/initials at the top so we can credit you; the requests themselves stay anonymous in the paper.

---

## PART B — internal notes (NOT shown to authors)

**Held-out discipline.**
- Authors are recruited by the user; the system's builders (us) do **not** contact them about
  mechanism vocabulary and do **not** see the requests until the set is **frozen**.
- On receipt, each batch is committed to a **sealed** location (`tasks/blindset/sealed/`, gitignored
  or encrypted) with a hash recorded. Scoring happens **once** on the frozen set; no iterating the
  system against it. Any request we later exclude is logged with a reason (auditable).
- Goldens for the blind set are authored **after** freezing, by us, blind to model output — or, where
  possible, the request is scored on physics (V-B) + feasibility, not against a hand golden, to avoid
  re-introducing builder bias.

**Coverage we will MEASURE post-hoc** (we do NOT steer authors toward these — we report how the
organic set landed against them; this doubles as the review-point-9 coverage table):
- **Motion type** — fasten/click, rotate (hinge/flap), translate (slide/drawer), rotate→translate
  (knob-driven slide, crank-lift), hold/static. *(Expected gaps vs our card set become honest
  "not-yet-covered" rows, not hidden.)*
- **Constraint type** — none, dimensional (mm), force (N), angle (deg), travel (mm), hold/drift.
- **Difficulty** — single-behaviour vs multi-constraint vs tightened-spec.
- **Feasibility** — buildable vs **deliberately infeasible** (over-constrained / contradictory /
  out-of-vocabulary) → tests the refusal path, not just synthesis.
- **Phrasing** — terse vs verbose, layperson vs semi-technical, with/without acceptance criteria.

**Targets.** 30–50 requests total; ≥3 independent authors (so no single person's style dominates);
≥15% deliberately-infeasible; every motion type above represented by ≥2 requests if the organic set
allows (if not, that absence is a reported finding).

**What we do with it.** Run the frozen set through the pipeline **once** at the recorded tier
(D-E-9c), score: (a) refusal correctness on the infeasible subset, (b) gate-pass + build + V-B on the
feasible subset, (c) coverage — fraction of requests whose behaviours our vocabulary can express at
all (the honest denominator). Report all three; a low coverage number is a result, not a failure to
hide.

**Consent / credit.** Authors are told their requests may appear (anonymised) in a research paper and
dataset; names credited in acknowledgements only. No PII in the requests.

---

## Status

Protocol drafted. **Recruitment is the user's step** (external volunteers). The moment authors are
lined up, Part A goes to them verbatim; batches land in the sealed location; scoring runs once at the
D-E-9c tier. Tracks review point 1 (blind/held-out) and feeds point 9 (coverage table).
