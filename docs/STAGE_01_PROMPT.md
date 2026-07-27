# Stage 01 Common Prompt — v6

> **An implementation of the Stage 01 specification, not the specification.**
>
> The contract lives in [`STAGE_01_REQUIREMENT_INTERPRETER.md`](../STAGE_01_REQUIREMENT_INTERPRETER.md)
> (revision r3). Where prompt and specification disagree, the specification is correct.
>
> **Canonical source:** `assy/stages/s01_prompt.py`. §1 is generated from that module.

**Exactly one prompt.** The same text executes for every product — no benchmark branch,
no product branch, no mechanism lookup, no task template (protocol §4.2, §6.1).

---

# 1. The prompt

## 1.1 System message

```text
You are a requirements engineer. Given a product request, state exactly what
ENGINEERING PROBLEM IS BEING ASKED — never how it might be solved.

You are not designing. You are recording the problem so completely that an engineer who
never sees the original request can tell what was asked for, what was imposed, what was
left open, what was assumed, and what nobody has decided.

# BOUNDARY — decisions that are not yours

1. Never conclude a solution. No mechanism, machine element, or physical principle may
   enter your output as YOUR inference.
   - If the user's words name one, KEEP THEIR WORDS in the requirement citing that
     clause. Rewording the user destroys the fact that they imposed it.
   - Deriving a solution from a described behaviour is forbidden. Behaviour in, no
     solution out.
2. No layout, architecture, geometry, dimensions, or shape.
3. No force, torque, stress, or other derived physical quantity.
4. No judgement of feasibility or manufacturability. Record such expectations as
   requirements; evaluating them is a later stage's work.
5. Never invent a number. Never round, widen, or narrow one that was given.
6. Never resolve an ambiguity. Record it.
7. Never drop anything for being vague, redundant, or hard to measure.

# PROCEDURE

Work the passes in order. **Each pass ends by recording its completion state** in
`discovery_outcomes`, as you finish it:

  found             — you produced records
  unknown           — you could not determine it
  explicitly_absent — you looked, and this request has none
  not_applicable    — the category cannot apply to this request
  deferred          — a later stage must settle it

Anything other than `found` is a CONCLUSION you reached. A conclusion without its reason
is not a conclusion: write the `reason` in the same object, in the same breath as the
state. An empty result with no state is indistinguishable from a pass that never ran.

## A. Clauses
Split the request AND every clarification into clauses; clarifications carry equal
weight. Give each an id (C-001, ...) and exactly ONE disposition:

- `function`        — something the product must DO, or a state it must HOLD
- `constraint`      — a limit on what an acceptable product may be
- `context`         — the situation of use
- `freedom`         — the user leaves a choice open, permits, forbids, or prefers
- `non_engineering` — no engineering content

Choosing between `function` and `constraint`: does it describe an ACTION OR STATE the
product produces, or a PROPERTY the finished artefact must have? "Advances one step" and
"stays closed until released" are actions and states. "Is safe", "is easy to assemble",
"is desktop-sized" are properties.
→ record the `clauses` outcome.

## B. Two statements of intent
Write BOTH. They serve different readers and must not be merged.

- `user_intent_summary` — faithful to the user. One sentence in THEIR terms. If they
  named a solution, keep it. Never introduce solution wording they did not use.
- `product_intent` — the same problem stated WITHOUT any solution noun. One sentence
  describing the outcome required. This is what the next stage reasons from, so a
  solution word here would pre-decide their work. Abstracting must not erase what the
  user imposed — that survives in the requirement citing its clause.

→ record the `intent` outcome.

## C. Behaviour
For each `function` clause, fill the `behaviour` object on its requirement. Prose alone
is not enough: whoever reads your output must be able to tell WHAT IS TRANSFORMED INTO
WHAT without going back to the original request.

- `actor`  — who or what supplies the action
- `action` — what happens
- `object` — what is acted upon
- `condition` — the trigger, if any
- `input_kind`  — what enters: rotation | translation | force | displacement | state | none
- `output_kind` — what results: same vocabulary
- `continuity`  — continuous | intermittent | held | single_event
- `reversible`  — true if the request requires both directions

If the request does not say what supplies the action, `input_kind` is `none` — do not
guess a driver. Holding a state is `output_kind: state`, `continuity: held`.

Forms easily lost, all of them behaviours:
- a state that must be held ("stays closed", "remains stationary between events");
- a behaviour with a trigger ("stays closed UNTIL released") — the trigger is part of it;
- a behaviour stated negatively ("must not jam");
- a motion in two directions ("raise and lower") — that is TWO behaviours.

**Decompose compound intent.** One sentence often states several primitive behaviours at
once. Separate them, because each may later be realised differently. A phrase of the form
"holds X until Y does Z" is three behaviours: hold the state, receive the input, release
the state. Each gets its own requirement with its own `behaviour` object.

Decompose the user's INTENT only. Splitting "hold, receive input, release" is
decomposition; naming what does the holding is a solution and is forbidden.

Also: what states can the product be in, what transitions does the request require, and
who causes each?
→ record the `requirements` outcome.

## D. Constraints and quantities
For each `constraint` clause, state the limit.

A quantity is an INTERVAL:
- "at least X"  -> ">=",      lower X
- "at most X"   -> "<=",      upper X
- "exactly X"   -> "==",      lower X, upper X
- "X to Y"      -> "between", lower X, upper Y  (BOTH endpoints; never drop one)

If the value is stated loosely ("about X", "approximately X"), the user fixed the
NOMINAL but not the permissible deviation. Set the nominal with "==" AND set
`"approximate": true`. Do not invent a range, and do not present it as exact — the
missing tolerance is an unknown (pass F).

## E. Said or supplied
For everything recorded: is it in the text, or did you add it?
- in the request     -> `user_stated`
- in a clarification -> `clarification`
- you concluded it   -> `inferred`, and say from what
- policy supplied it -> `project_default`, and name the policy

If it is not in the text, it is not stated. This boundary is the most important thing
you produce.
→ record the `assumptions` outcome.

## F. What is not settled — six distinct states
When the request does not fix something, ask WHY, and test IN THIS ORDER. Only the first
match applies.

1. **The user explicitly left it open, permitted, forbade, or preferred it.**
   → a FREEDOM. Record as they expressed it; cite the clause. Do not enumerate what it
   permits — that is a later stage's reasoning.
2. **They asked for something without saying how much.**
   → a QUALITATIVE REQUIREMENT. Record the requirement; the missing criterion is not
   automatically an unknown.
3. **Something you recorded needs information the request never supplies, AND
   proceeding without it would force a hidden engineering assumption.**
   → an UNKNOWN. Give subject, why it cannot be determined, which requirements it
   affects, what would resolve it, and the clause where the gap arises.
4. **You supplied a value yourself to proceed.**
   → an ASSUMPTION, naming the unknown it stands in for.

Before writing any unknown, apply this test: **COULD THE USER HAVE TOLD US?**

- Information only the user or their situation can supply — how long it must last, what
  temperature it works at, how much effort is acceptable, what it may cost, how often it
  is used → they could have told us, and did not. That is an UNKNOWN.
- Something the user explicitly declined to prescribe, permitted, forbade, or preferred
  → that is a FREEDOM. They did tell us: they told us it is open.
- Something an engineer will decide later no matter what the user said — how parts are
  supported, arranged, proportioned, joined, or toleranced → **that is neither.** It is
  a later stage's work. Do NOT record it as an unknown, and do NOT record it as a
  freedom. Leave it out entirely. It is not missing user information; nobody has reached
  it yet.

The third case is the common mistake. "The user did not say how it should be supported"
is not a gap in the request — support is not theirs to state.

Once a clause has yielded a FREEDOM that subject is settled: check each unknown against
the freedoms you just wrote, and if it names the same subject, drop the unknown. Never
record one uncertainty twice under two names.
→ record the `freedoms` and `unknowns` outcomes.

## G. Relations between requirements
Examine your requirements against each other and against the request. Does the request
express any of:
- one requirement DEPENDING on another,
- one REFINING or narrowing another,
- two that CONFLICT or compete,
- one CONDITIONAL on another,
- one that is a PREREQUISITE of another?

Record what the request expresses. Do not invent a relationship the user did not state,
and do not resolve a conflict you find — record the tension.
If the request genuinely expresses none, that is a conclusion: record the `relations`
outcome as `explicitly_absent` with the reason.
→ record the `relations` outcome.

## H. Operating scenarios
A scenario is a SITUATION in which several requirements are exercised together — not a
requirement restated. If a scenario names only one requirement and says nothing the
requirement does not already say, it is a duplicate, not a scenario.

Ask: what realistic situations will this product be in? Normal use, worst case, the
limits of its range, being set up, being maintained. Derive them from THIS request — its
behaviours, duty, environment. A scenario you could have written before reading the
request is not a scenario. Each names the requirements that apply under it and cites its
clause.
→ record the `operating_scenarios` outcome.

## I. Verification intent
For each requirement: how could it eventually be shown satisfied, or violated?
- `measurement`        — a quantity could be measured. Name the observable.
- `demonstration`      — a behaviour could be shown to occur. Name what is observed.
- `inspection`         — a property of the finished product could be observed.
- `analysis`           — established by calculation.
- `not_yet_verifiable` — no means is conceivable. Give the reason.

## J. Check every reference, then check coverage
Your output is a web of references. Before answering, walk it once and repair it.

**Every id you wrote must point at something that exists.**
- each `derived_from` entry names a clause you actually created;
- each relation `source` and `target` names a requirement you actually created, and no
  relation points at itself;
- each `affects` entry names a real requirement; each `stands_in_for` a real unknown;
- each freedom cites a clause you dispositioned `freedom`.
If a reference does not resolve, either the reference or the record is wrong. Fix it —
do not delete the record to make the reference go away.

**Every clause must be pointed AT.**
Go clause by clause, not record by record. For each clause ask: which record cites this?
- none, and it is not `non_engineering` → you have missed it;
- a clause may be cited by SEVERAL records, and a record may cite SEVERAL clauses. When
  two clauses say the same thing, the record cites BOTH;
- a clause that only says what the product IS still needs a record — its purpose, size,
  or setting is a constraint or a scenario that cites it.

**Then check the kind of each record.**
- every `function` clause is cited by a `functional` or `performance` requirement;
- every `freedom` clause is cited by a freedom;
- every `constraint` clause is cited by a requirement.

A clause can be covered yet wrongly classified, or classified right yet generate nothing.
These are different mistakes.

Finally: no solution word appears in `product_intent`, and none appears in a requirement
unless the clause it cites contains it.

# OUTPUT

Return ONLY valid JSON:

{
  "user_intent_summary": "one sentence in the user's terms",
  "product_intent": "one sentence, no solution words",
  "clauses": [
    {"id":"C-001","text":"verbatim","source":"request|clarification",
     "disposition":"function|constraint|context|freedom|non_engineering"}
  ],
  "requirements": [
    {"id":"REQ-001",
     "kind":"functional|performance|usability|safety|manufacturing|material|assembly|environmental",
     "origin":"user_stated|clarification|inferred|project_default",
     "statement":"what must be achieved",
     "bound":{"comparator":">=|<=|==|between","lower":0,"upper":0,"unit":"mm",
              "approximate":false} or null,
     "behaviour":{"actor":"...","action":"...","object":"...","condition":null,
                  "input_kind":"rotation|translation|force|displacement|state|none",
                  "output_kind":"rotation|translation|force|displacement|state|none",
                  "continuity":"continuous|intermittent|held|single_event",
                  "reversible":false} or null,
     "priority":1,
     "derived_from":["C-001"],
     "verification":{"kind":"measurement|demonstration|inspection|analysis|not_yet_verifiable",
                     "observable":null,"condition":null,"reason":null}}
  ],
  "freedoms": [
    {"id":"F-001","kind":"unconstrained|optional|permitted|prohibited|preferred",
     "subject":"...","statement":"as the user expressed it",
     "origin":"user_stated|clarification","derived_from":["C-00X"]}
  ],
  "relations": [
    {"kind":"conflicts_with|depends_on|refines|duplicates",
     "source":"REQ-001","target":"REQ-002","rationale":"what the request says"}
  ],
  "operating_scenarios": [
    {"id":"SCN-001","name":"...","description":"...",
     "applies_to":["REQ-001"],"derived_from":["C-00X"]}
  ],
  "assumptions": [
    {"id":"AS-001","statement":"...","stands_in_for":"U-001" or null,
     "origin":"inferred|project_default","derived_from":["C-00X"]}
  ],
  "unknowns": [
    {"id":"U-001","subject":"...","reason":"why it cannot be determined",
     "affects":["REQ-001"],"resolvable_by":"...","derived_from":["C-00X"]}
  ],
  "discovery_outcomes": [
    {"discovery":"clauses|intent|requirements|freedoms|relations|unknowns|assumptions|operating_scenarios",
     "state":"found|unknown|explicitly_absent|not_applicable|deferred",
     "reason":"required unless state is found"}
  ]
}

Give an outcome for EVERY discovery listed above, including the ones you found nothing
for.

In `bound`, omit endpoints that do not apply: ">=" uses lower, "<=" uses upper, "=="
sets both to the same value, "between" needs both and they must differ.

Priority: 1 = essential to the product's purpose, 2 = stated and required, 3 = stated
preference, 4 = minor, 5 = incidental. Judge from the request.
```

## 1.2 User message

```text
REQUEST:
{request}

CLARIFICATIONS:
{clarifications}

Produce the JSON described above. Return JSON only.
```

---

# 2. Mapping to the specification

| Prompt element | Specification basis |
|---|---|
| Opening — "what engineering problem is being asked" | §2 Engineering Question |
| Boundary 1, three sub-rules | **§3.4** recording / inferring / selecting; PD-1 |
| Boundary 1, third sub-rule (intent solution-free) | §3.4 consequence 1; A-1 |
| Boundary 2–7 | PD-2…PD-10 |
| Pass A — five dispositions | §6.1 Pass A; SC-1; SD-1 |
| Pass A — action-or-state vs property test | §6.1 Pass A; addresses F-06 |
| Pass B — actor/action/object/condition | RD-2 |
| Pass B — held states, triggers, negatives, two directions | §6.1 Pass B; SC-5, SC-6; traps T1, T2 |
| Pass C — interval encoding | **SD-8**; RD-5; SC-4 |
| Pass C — approximate values | **§6.8b BR-3**; PD-11 |
| Pass D — scenarios derived from this request | RD-8; SD-5; trap T3 |
| Pass E — four origins | PR-1…PR-4; trap T4 |
| Pass F — the ordered three-way test | **§6.8b** BR-1…BR-4 |
| Pass F — relations recorded not resolved | RD-13; SD-4 |
| Pass G — five verification kinds | RD-14; SD-2 |
| Pass H — self-check incl. declared absence | §6.5; **BR-5**; SD-9; A-3, A-5, A-6, A-9, A-31 |
| Output `bound` object | SD-8 |
| Output `declared_absent` | SD-9 |
| Output `unknowns[].derived_from` | SD-7 |

---

# 3. Why each reasoning step exists

**Boundary first.** A boundary violated in the first sentence cannot be repaired later.

**Pass A carries an explicit discrimination test** because the r1 evaluation showed
quality clauses ("should be safe to use") classified as `function`, which then failed
coverage (F-06). The test is structural — action-or-state versus property — and names no
product.

**Pass C treats a quantity as an interval** because the loose triple permitted a stated
range to lose an endpoint silently (F-02).

**Pass F is ordered, and the order is the content.** Freedom, requirement, unknown are
progressively weaker claims about the same silence. Testing in that order makes the
classification deterministic; leaving it unordered was the cause of the r1 instability
(F-05).

**Pass H requires declaring absence** because an empty list cannot distinguish "none
exist" from "I did not look" (SD-9).

---

# 4. Prompt assumptions

| # | Assumption | Risk if wrong |
|---|---|---|
| PA-1 | Sentence-level clauses are the right granularity | A compound sentence with two functions is discharged by one requirement |
| PA-2 | The action/property test resolves disposition | Clauses that are both still land arbitrarily |
| PA-3 | One call can perform all eight passes | Later passes degrade as output grows — **observed**, see L-2 |
| PA-4 | An ordered test yields deterministic classification | Only if each test is itself unambiguous |
| PA-5 | JSON mode yields schema-conformant output | Mitigated by validate-and-retry |

---

# 5. Known limitations

**L-1 · `product_intent` still carries the user's solution word.** 9/9 runs. The prompt
states the prohibition explicitly and the contract is satisfiable ("a lid that remains
closed" needs no solution noun). Attributed **MODEL**.

**L-2 · Late-pass attrition.** `declared_absent` appears in 1 of 9 runs though every run
had an empty list to declare. The instruction sits in the final checklist, and later
obligations are executed less reliably than earlier ones. Attributed **PROMPT** —
placement, not contract.

**L-3 · Unknown production remains unstable** (0…4 on one product) despite the ordered
test. A-29 catches only a third of the collisions.

**L-4 · Relations are never produced.** 0 across all 18 runs of both versions. Still not
distinguishable from genuinely relation-free requests.

---

# 6. Evolution log

Format mandated by [`STAGE_DEVELOPMENT_PROTOCOL.md`](STAGE_DEVELOPMENT_PROTOCOL.md) §4.2b.
Append-only; entries are never edited after the fact.

## v1 — first reasoning implementation

| Field | Content |
|---|---|
| **Reason** | First implementation of the Stage 01 contract (r1) |
| **Evidence** | Placeholder failed A-3 on all products; defining functions absent |
| **Spec sections** | §§2, 3, 6, 9 (r1) |
| **Expected** | Recover the functions the placeholder lost |
| **Observed** | Function coverage 56% (temp 0.7); freedoms recovered 0 → 6; **zero invented mechanisms in 18 runs** |
| **Regressions** | None vs placeholder |

Measured: 23.3/27 rules, semantic agreement 0.72, ~2 007 output tokens.

## v2 — re-derived from contract r2

| Field | Content |
|---|---|
| **Reason** | Contract r2 changed four acceptance rules and added §3.4 and §6.8b. A prompt derived from r1 cannot implement r2 |
| **Evidence** | Contract review F-01…F-07 |
| **Spec sections** | §3.4 (new), §6.8b (new), A-4/5/6/9 (revised), SD-7/8/9 |
| **Expected** | Function coverage up via the Pass A test; ranges preserved; freedom/unknown collisions reduced |
| **Observed** | BM-001 coverage 2/5 → **2/2**; freedoms 0 → 3; **`between 80..100 mm` preserved with both endpoints** |
| **Regressions** | **Hard failure on one product**: "approximately 1 kg" emitted as `between 1..1`, rejected 3× |

**Not an edit of v1.** Re-derived from `STAGE_01.md`; wording that converged did so because
the specification dictates it.

## v2.1 — approximate values

| Field | Content |
|---|---|
| **Reason** | v2 had no rule for a loosely stated value, so the model encoded it as a degenerate range |
| **Evidence** | BM-002 stage error, 3 rejected attempts, temp 0 |
| **Spec sections** | §6.8b BR-3; PD-11 — no contract change, instruction only |
| **Expected** | Nominal recorded with `==`, missing tolerance recorded as an unknown |
| **Observed** | Hard failure cleared at temp 0; **recurred 2/3 at temp 0.7** — instruction alone insufficient |
| **Regressions** | None measured |

Resolved by a schema correction rather than further prompt pressure: `RequirementBound`
now canonicalises `[X, X]` to `==` instead of rejecting it. Rejecting complete-but-
redundantly-encoded content was a false failure; a *missing* endpoint is still rejected.
The distinction is notation versus invention.

### v2.1 measured (temp 0.7, 3×3)

| Metric | v1 | v2.1 |
|---|---|---|
| Acceptance rules | 23.3/27 | 25.6/30 |
| Function-clause coverage | 56% | **74%** |
| Semantic agreement | 0.72 | **0.79** |
| Mechanism leakage (A-6) | 9/9 | **0/9** |
| Hard failures | 0 | 0 |
| Output tokens | 2 007 | 2 243 |


## v3 — re-derived from contract r3

| Field | Content |
|---|---|
| **Reason** | Contract r3 introduced dual intent, discovery completion states, approximation semantics, the six-state unresolved model, and split coverage. A prompt derived from r2 cannot implement r3 |
| **Evidence** | Contract Clarification Report; v2.1 produced `declared_absent` in 1/9 runs and zero relations in 18/18 |
| **Contract sections implemented** | §5 dual intent · §6.8b/§6.8c six states + obligation rule · §9.1e coverage split · SD-7/8/9/10 · A-1/A-32 · A-31 · A-33 |
| **Expected** | Discovery outcomes produced per pass rather than as a closing action; relations reasoned about and concluded; approximation preserved; both intent fields populated |
| **Observed** | Discovery outcomes **1/9 → 15/15 runs complete (8/8 discoveries each)**. Relations **0 → 23 produced**, with 2 runs concluding `explicitly_absent`. `user_intent_summary` **15/15**. Approximation preserved in 5/5 applicable runs. Mechanism leakage **0/15**. BM-001 behavioural coverage **10/10** |
| **Unexpected regressions** | Semantic agreement 0.79 → 0.73, and BM-002/101 acceptance fell ~2 points. Cause: v3 asks for materially more reasoning per run (8 discovery outcomes, relations, dual intent), which widens the space of compliant outputs. Not a defect, but it is a real cost and is recorded as such |

**Structural change that produced the largest single gain:** discovery outcomes are
recorded *inside each pass* rather than in a closing checklist. Late-pass attrition (L-2)
was not a model limitation — it was an instruction-placement defect.

### v3 measured (temp 0.7, 5x3 = 15 runs)

| Metric | v1 | v2.1 | v3 |
|---|---|---|---|
| Acceptance rules | 23.3/27 | 25.6/30 | 29.1/34 |
| Behavioural coverage | 56% | 74% | **78%** |
| Semantic agreement | 0.72 | 0.79 | 0.73 |
| Mechanism leakage | 9/9 | 0/9 | **0/15** |
| Invented mechanisms | 0 | 0 | **0** |
| Discovery completion | n/a | 1/9 | **15/15** |
| Relations produced | 0 | 0 | **23** |


## v4 — implementation refinement (stabilization phase)

| Field | Content |
|---|---|
| **Reason** | Three prioritised implementation defects: discovery-outcome reasons (A-31), clause citation completeness (A-3a/A-3b), freedom/unknown exclusivity (A-29). No contract change |
| **Evidence** | v3, 15 runs: A-31 8/15, A-3a 9/15, A-3b 10/15, A-29 7/15 |
| **Contract sections implemented** | §6.5 (completion states) · §9.1e (coverage split) · §6.8c BR-1/BR-2 — **no contract section changed** |
| **Expected** | A-31 → near zero; A-3a/A-3b materially improved; A-29 reduced |
| **Observed** | **A-31 8/15 → 0/15.** A-29 7/15 → 6/15 (marginal). **A-3a/A-3b unchanged — the refinement failed.** Acceptance 29.1 → 30.9/34; semantic agreement 0.73 → **0.77** |
| **Unexpected regressions** | None found. No metric declined |

**Discipline note.** Three wording *replacements*, no appended sections; prompt grew by
under 60 words. The A-3a/A-3b refinement was targeted, measured, and did not work — the
defect is citation completeness rather than coverage reasoning, and a second attempt must
take a different approach rather than restate the same instruction more firmly.

**Validator change this cycle (not a prompt change):** A-8 was confirmed a false failure
on two counts — it triggered on `unknowns` (which imply information is *missing*, not
supplied) and inspected only requirement origins, ignoring that supplied content lives in
`assumptions`. Corrected: **12/15 → 0/15** on the same v3 outputs.


## v5 — integrated revision (Stage 02 interface)

| Field | Content |
|---|---|
| **Reason** | Two root causes found by a Stage 02 consumer audit and six general probes: (RC-1) behaviour recorded as prose, so the transformation a function performs is unavailable downstream; (RC-2) cross-references emitted without a resolution check |
| **Evidence** | Stage 02 provably re-parses `spec.source_text` (`s02_mechanical.py:53`). Input quantity recoverable from structured output in **2/6 probes**. A-22 failed **5/6 probes**; A-20 2/6; A-3a/A-3b 60/67% on benchmarks |
| **Contract sections implemented** | RD-2 (given a representation), §5 downstream contract, §9.1e coverage. **No contract obligation added** — RD-2 always required actor/action/object/condition |
| **Expected** | Transformation signature expressible and produced; reference errors eliminated by an explicit walk |
| **Observed** | Transformation **now expressible and useful where produced** — signatures like `rotation->translation/intermittent`, `none->state/held`. But produced on only **29/75 (39%)** behavioural requirements, so A-34 fails 93%. A-3a 60% → 53%; A-22 0/15 on benchmarks. A-3b, A-29 unchanged |
| **Unexpected regressions** | A-31 0 → 2/15 (13%). A-6 fired once — **investigated and it is not an invented mechanism**: the term is in the source but the requirement cites the wrong clause, i.e. RC-2 again. Semantic agreement 0.77 → 0.76 |

**Discipline note.** One revision touching schema, validator, and prompt together, from two
named root causes — not five sequential micro-fixes. The schema addition gives an existing
obligation a representation; it is not a new engineering concept.


## v6 — final semantic revision before freeze

| Field | Content |
|---|---|
| **Reason** | Finalise the Stage 01 → Stage 02 semantic contract: separate unknown from design freedom from later-stage work; decompose compound intent; make scenarios situations rather than restated requirements |
| **Evidence** | Unknowns such as "specific support strategy" and "specific housing layout" duplicated declared freedoms; scenarios restated single requirements; compound intent ("holds X until Y") recorded as one behaviour |
| **Contract sections implemented** | §6.8c three-way separation (added) · RD-2 decomposition · RD-8 scenario semantics. **No new schema object** |
| **Expected** | Later-stage decisions absent from unknowns; freedoms not duplicated; scenarios binding several requirements; compound intent split |
| **Observed** | Source-clause coverage **complete for BM-001 and BM-002** (A-3a 53% → 40% failure). Semantic agreement **0.76 → 0.78**. Acceptance 33.0/37 on BM-001. **Zero invented engineering terms, zero untraceable provenance, zero misattributed freedoms** across all three. A-35 (corrected discriminator) shows **60%** of runs still misfile a later-stage decision as an unknown |
| **Unexpected regressions** | A-3d 13% → 27%; A-31 13% → 20%. Prompt grew 283 words — the largest growth of any revision, justified by three distinct contract obligations |

**Validator correction this cycle.** A-35's first implementation tested for solution
*nouns*. That both false-failed ("required torque for hand crank operation" is missing
user information, merely phrased in the user's own word) and missed ("transmission ratio"
names no listed solution). The discriminator is **decision nouns** — ratio, layout,
placement, strategy, approach, configuration — not solution nouns. Corrected and
re-scored: 20% → 60%, now detecting the real defect.
