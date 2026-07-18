# External Review 1 — MechSynth (pre-submission internal review)

- **Date received:** 2026-07-18
- **Status:** pre-submission internal review (not a venue review)
- **Original language:** Korean. This is the faithful English translation; sentences the reviewer
  quoted in English in the original are reproduced verbatim.
- **Archived by:** D-REV-1

---

## Verbatim review text

1. THE NEW BENCHMARK IS AN EXTENSION OF DEVELOPMENT, NOT AN INDEPENDENT
EVALUATION SET. The 16 tasks are built around the three already-verified
base designs (snap-lid box, hinged latch box, crank lift) plus one
out-of-vocabulary infeasible. Base tasks reuse existing milestone verdicts;
variants parameterize existing golden builders; infeasible tasks are
hand-constructed wrong IRs demonstrating deterministic rejection. This is
good as a regression suite but risky as an ML benchmark, because the
evaluation tasks, golden builders, cards, and verifiers were all produced
in the same development process. A reviewer can read it as: "The benchmark
mostly parameterizes the three systems used to develop the method." Most
variants are size changes, force-window changes, open-angle changes,
load/stroke changes, element prohibitions, or physically contradictory
inputs — i.e., parameter perturbation and rule rejection rather than
compositional generalization. Needed: a held-out task set frozen after
development ends — requirements written by other people; host-element
combinations not seen during development; new spatial arrangements; a
different mechanism family for the same function; paraphrases; incomplete
or ambiguous requests; assemblies the cards can express but no existing
golden builder constructs. Keep the current benchmark as the
training/development set and build a separate blind set.

2. THE LLM END-TO-END SAMPLE IS TOO SMALL. The m9 qwen-vs-gemini result is
a good qualitative demonstration — the physics verifier catching the LLM's
design omission is a strong message — but as statistical evidence it is
essentially: two models, one (or very few) central commands, one
small-model failure, one frontier success. From this one cannot conclude:
that staged decomposition beats direct prompting; that KG narrowing
improves accuracy; that frontier models generally infer passive features
like the stop; that validator repair raises success rates; that structured
IR beats direct CadQuery generation; or that results are stable to prompt
wording. Reviewers will require at minimum: direct text→CadQuery;
text→DesignPlan in a single prompt; stages ①–④ decomposition;
decomposition + KG narrowing; decomposition + validator retry; the full
method — each with multiple paraphrases and sampling seeds per task. The
current two-model result is safer used as a motivating example than as the
paper's central result.

3. THE SYSTEM IS CLOSER TO CLOSED-WORLD CONFIGURATION THAN OPEN-ENDED
SYNTHESIS. The LLM makes discrete choices (ontology verb, phase/motion,
host template, card, port, anchor); dimensions are computed by
deterministic code. Excellent for reliability, but it limits what
"synthesis" means. A screw-jack request is defined as out-of-vocabulary
infeasible because there is no leadscrew card — so what the system can do
is select and combine solution primitives already in the registry.
Reviewers will ask: can it propose a new solution principle without a
card? does it compare trade-offs among multiple cards realizing the same
function? does it compose new topologies? new host layouts without
existing builders? how does search complexity grow with library size? The
accurate description is library-constrained configuration. Not necessarily
a weakness, but the claim must be sharpened to: verified assembly
synthesis within an executable engineering knowledge library — not
open-ended mechanical invention.

4. THE ELEMENT CARD HOLDS BOTH GENERATIVE KNOWLEDGE AND VERIFICATION
CRITERIA — CIRCULARITY REMAINS. The same card can provide geometry
generation, parameter ranges, collision approximation, expected behavior,
the verification protocol, and pass thresholds. The system then risks
evaluating agreement with the world its own cards define rather than real
mechanical function. The sharpest reviewer critique: "The system may be
verifying compliance with its own executable specification rather than
independently establishing physical validity." Post-compile re-measurement
catches shape drift but does not make the verifier independent. Needed:
checkers authored independently of card authors; a separate physics
engine; commercial CAD/CAE; real fabrication experiments; external
evaluators who do not know the cards; randomized tolerance and material
perturbations. At least some results should be confirmed by evidence
outside the cards.

5. THE HARD ANCHOR'S KEY TRANSMISSION IS STILL NOT CONTACT-VERIFIED. The
Hard anchor is much improved (slide V-A 5/5, slide V-B 5/5, rack-pinion
V-A 5/5, the hold failure discovered, pawl added, hold 5/5, full cycle
5/5). But rack-pinion V-B — power transmitted by actual tooth contact —
remains deferred on the contact-formulation limit. So the anchor's most
important function, crank rotation → rack translation, effectively rests
on a declared kinematic relation. "The complete mechanism is physically
verified from geometry alone" would be an overclaim. Accurate: "The
assembly is verified through a mixture of contact-derived constraints and
declared mechanism relations; rack-pinion contact-only transmission
remains unresolved." This must appear as a front-and-center limitation,
and representative figures must clearly distinguish V-A from V-B.

6. DISCOVERING FAILURES AND FIXING CARDS IS SCIENTIFICALLY INTERESTING BUT
CAN LOOK LIKE EVALUATION LEAKAGE. The pawl story (back-drive found by
physics; element added; 0/5 → 5/5) is a good case of verification-aware
design. But an alternative reading exists: after seeing a verification
failure, the cards and geometry were adjusted until the same evaluation
passed. In particular, setting the retention-stop gap to print_clearance/4
so slide V-B went 0/5 → 5/5 is not yet separated into "real design
principle" vs "tuning to a particular MuJoCo contact setup." To make it
scientific, test the modified rules under different loads, orientations,
clearances, frictions, timesteps, simulators, real prints, and unseen
slide dimensions. Showing 0/5→5/5 on the same fixture reads as a patch;
robustness across conditions makes it a discovered general design rule.

7. ROBUSTNESS AND UNCERTAINTY ANALYSIS OF THE SIMULATION SETUP IS
LACKING. Results are mostly 5-seed pass rates, but simulation reliability
also depends on timestep, friction coefficient, contact stiffness,
damping, mesh decomposition, mass/inertia, initial pose, actuator profile,
and collision margins. The repository itself already hit timestep and
contact-formulation limits on the gear — so reviewers will ask whether the
other protocols share such sensitivities: are P-SLIDE 5/5 and P-HOLD 5/5
robust designs, or optimizations to the frozen preset? Needed sweeps per
representative design: μ at 0.5–1.5× nominal; mass/load variation;
clearance variation; timestep variation; collision tessellation variation;
initial misalignment; manufacturing-tolerance Monte Carlo. Success should
hold over a region, not a point, for "functional verification" to be a
strong claim.

8. PHYSICAL FABRICATION IS NOW NEARLY MANDATORY, NOT OPTIONAL. At the
prototype stage simulation-only was understandable, but the claims now
cover PETG designs, snap forces, print clearances, retained slides, hinge
fits, pawl-detent hold, and 0.5 kg lifting. At this point the absence of a
real build is conspicuous. Relatively low-cost experiments: snap
insertion/retention force; hinge open angle; slide retention and off-axis
motion; the 0.5 kg lift and back-drive; pawl release/hold; assembly
success rate by clearance. The strongest paper story is already: "Physics
found that a rack-pinion lift would back-drive, and the system introduced
a pawl-detent that fixed it." Verifying that on a real print makes it very
strong; if the real part fails, that exposes the simulation's limits —
either way it is scientifically valuable.

9. CARD COUNT HAS GROWN BUT INDEPENDENT ELEMENT FAMILIES REMAIN LIMITED.
Of the six cards, pawl-detent reuses the snap-hook formula family
asymmetrically, and stop-flange is a relatively simple passive constraint.
The genuinely distinct engineering-knowledge families are roughly:
compliant snap, rotational joint, prismatic guide, gear transmission,
passive stop. A generality claim wants elements with genuinely different
character: screw/leadscrew, cam, belt or chain, spring, bearing, flexure,
over-center latch, four-bar linkage, fastener, compliant hinge. Defining
the screw jack as "infeasible for lack of a card" shows the system's
honest limits — and also shows the coverage is small.

10. CARD AUTHORING COST AND EXPERT DEPENDENCE REMAIN UNMEASURED. How long
did the slide-rail card take? How much code does rack-pinion require?
Which fields demand an expert? How much of the card API was reused? Does
each new card need a new verifier? How much new anchor code per host? The
milestone record shows each new mechanism needs substantial work (card,
carve, collision hint, verification protocol, host template, anchors,
assembly rules, custom physics scripts). If all of that is required, the
scalability bottleneck may be knowledge-engineering cost, not the LLM.
Measure it rather than hide it: a per-card table (LOC, development time,
new API, new verifier, new template) would substantially raise the paper's
credibility.

11. THE CURRENT "ANTI-RAG" CLAIM IS SOMEWHAT OVERSTATED. The core idea is
good, but framing it as "things RAG structurally cannot do" invites
attack. RAG and executable cards are not mutually exclusive: retrieval can
find candidate handbook sections; an LLM or expert compiles them into a
card; the card executes and verifies. Retrieval also stays useful when a
new request falls outside current card coverage. The stronger scientific
claim: "Retrieved prose alone is insufficient as the execution substrate;
engineering knowledge should be compiled into typed, executable and
verifiable artifacts." Role separation between retrieval and the execution
substrate is more defensible than "anti-RAG."

12. THE CORE NOVELTY IS STILL SPREAD ACROSS THREE STRANDS — compiled
engineering knowledge cards; LLM→typed IR→deterministic CAD compiler;
multi-tier geometry/formula/physics verification. With the Hard anchor and
benchmark added, the system is richer but the central message risks
blurring. Claiming ontology + LLM stages + KG narrowing + cards + compiler
+ simulation + benchmark + repair + infeasibility detection all as primary
contributions at an ICML-class venue reads as "large-scale engineering
integration" with weak independent ML novelty. The strongest, most
distinctive central claim is probably: "Heterogeneous executable verifiers
expose design errors that syntactic validity and declared kinematic
constraints cannot detect." The examples already exist: the LLM design
missing the stop (validator-clean, hard to distinguish under V-A, caught
by V-B); the rack-pinion lift that moves but back-drives; the pawl fixing
hold; the geometry bug V-A passed and V-B found. Center the paper on this
story, with cards and compiler as the enabling infrastructure.

THE MOST DANGEROUS REVIEW SENTENCES, AS A CRITICAL REVIEWER WOULD WRITE
THEM: "The artifact has developed into an impressive and carefully
documented closed-world engineering system. However, the empirical
evaluation remains largely co-developed with the method: the benchmark
consists primarily of parameterized variants of three milestone
assemblies, and many expected outcomes are produced through existing
golden builders or manually constructed invalid IRs. It is therefore
unclear whether the reported performance reflects generalization from
natural-language functional requirements or successful execution within a
hand-authored library of templates, cards, and verifiers." On the physics:
"The most complex anchor is only partially geometry-driven: the slide is
verified contact-only, while rack-pinion transmission still relies on a
declared kinematic relation. Thus, the claim of physical verification
should be carefully qualified." At ICML, additionally: "The work currently
contributes a system and evaluation environment rather than a new learning
principle, and the LLM evaluation is too small to establish statistical or
compositional generalization."

THE BEST-DEFENDED CLAIM AT PRESENT: "Typed executable engineering
knowledge and post-compilation behavioral verification can detect and
localize functional design errors that schema validation, CAD compilation,
and declared-joint simulation miss." This matches the repository's actual
evidence (the omitted stop; V-B finding fold-over; back-drive discovery;
the pawl fix; the slide geometry bug; compile drift blocked by
re-measurement). Claims still weak: general-purpose mechanical synthesis;
benchmark-scale generalization; geometry-only verification of complete
mechanisms; open-ended functional design; a new ML or representation-
learning method.

PRIORITY: if choosing one next study, do a blind generalization evaluation
before any representation learning — freeze the three base assemblies as
the development set; have external people write 30–50 requirements; run
end-to-end without directly calling existing builders; repeat with
paraphrases and seeds; compare direct CAD / monolithic IR / staged IR /
KG-card ablations; hold out an unseen-composition subset; fabricate some
results; run the simulator parameter sweeps. If those results hold, ASSY
moves from "a well-built system" to a generalizable research method. The
most fundamental critique is no longer "there is no implementation" — it
is: the implementation has advanced so fast that the development cases,
cards, verifiers, and benchmark were co-optimized together, and there is
not yet independent evidence that the method works outside this
co-designed region. Resolve that, and the work's persuasiveness rises
substantially.

---

## Response-tracking table

| # | point (summary) | verdict | action (milestone / log ref) | status |
|---|---|---|---|---|
| 1 | Co-developed benchmark (not blind/held-out) | **ACCEPT** | m14 relabeled **DEV SET**; a blind held-out set authored by external people is planned (pending user recruitment) | table seeded; m14 relabel pending |
| 2 | LLM sample too small | **ACCEPT** | **m15 4-rung ablation ladder RUN** (direct-CAD / monolithic-IR / staged-no-KG / full), 6-task core × 2 paraphrases × N=3 = 144 cells. Clean adjacent-delta ladder: **B−A** = the IR buys a scoreable structure; **C−B** = staging+gates buys BUILDABILITY (design_ok 0.00→0.67, the biggest jump); **D−C** = the KG buys element/binding correctness (model-dependent effect, reported). Bulk on local qwen (Gemini spend-cap exhausted mid-run); flash-vs-pro gate captured as frontier reference (flash el/bd F1 = 1.00) | **DONE** ([m15_ablation/REVIEW.md](../m15_ablation/REVIEW.md)); Pro frontier column awaits cap raise |
| 3 | "Closed-world" claim overreaches | **WORDING** | reframe to *"verified assembly synthesis within an executable knowledge library"* | wording rule recorded |
| 4 | Card circularity | **ACCEPT-PARTIAL** | goldens pin to an **external handbook** (Bayer); the **preset is card-independent** (R5). Mitigations: cross-engine spot-check (D-M1-8), fabrication (pending), robustness sweeps (m16) | mitigations tracked |
| 5 | Mixed-verification overclaim | **WORDING RULE** | every representative figure **marks V-A vs V-B per axis**; phrasing *"contact-derived + declared relations"* | rule recorded; applies to all figures |
| 6 | Fix-after-failure leakage | **ACCEPT** | **m16 DONE** — the vertical-retention rule generalizes to **UNSEEN dimensions** (6×10 rail no milestone used) + across load/clearance/misalignment → a design RULE, not a fixture patch | **DONE** ([m16_robustness/REVIEW.md](../m16_robustness/REVIEW.md)) |
| 7 | Robustness sweeps missing | **ACCEPT** | **m16 DONE** — sweeps report success **REGIONS** (heatmaps). Honest finding surfaced: lift retention is physically robust but **numerically dt-sensitive** (holds at frozen dt, fails at finer dt); Easy hinge broadly robust (14/15) | **DONE** ([m16_robustness/REVIEW.md](../m16_robustness/REVIEW.md)) |
| 8 | No physical fabrication | **ACCEPT-PENDING** | user decision on printer access | awaiting user |
| 9 | Element families limited | **ACCEPT** | honest **coverage table** in the paper; VISION-6 (spring, gear train) stands as the extension path | coverage table pending |
| 10 | Card authoring cost unmeasured | **ACCEPT** | **card cost table** this session (LOC, sessions, new schema/API, new verifier vs reused, templates) — sourced to commit refs | **DONE** ([card_cost.md](card_cost.md)) |
| 11 | Anti-RAG framing overclaims | **WORDING** | reframe: *"retrieved prose is insufficient as an execution substrate"*; retrieval and execution substrate are **complementary roles** | wording rule recorded |
| 12 | Novelty diffuse | **ACCEPT** | center claim: *"heterogeneous executable verifiers expose design errors that syntactic validity and declared kinematics cannot detect"*; cards/compiler positioned as **infrastructure** | claim recorded |

---

### Point-10 card cost table (ITEM 3 — done)

Full table + provenance: **[reviews/card_cost.md](card_cost.md)**. Headline (sourced to commits):
the marginal card gets cheaper as the scaffolding amortizes — **LOC 731 (snap) → 286 (pawl, ~40%)**,
**sessions ~3 → ~0.5**, **new schema/API front-loaded then ~zero** (slide/rack/pawl added none), and
**3 of 6 verifiers reuse/adapt** an existing protocol (hinge←m0, rack←M1, pawl delegates snap's
formulas). This quantifies VISION-3's 3→1→0.5-session claim. Honest limit: still hand-authored.
