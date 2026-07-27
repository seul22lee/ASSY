"""Stage 01 deterministic validation.

Implements the acceptance rules, diagnostics, and cross-product warning defined in
`STAGE_01_REQUIREMENT_INTERPRETER.md` §9. Rule identifiers here are the rule
identifiers there; the specification is authoritative.

Three severities, and the distinction is deliberate:

- **acceptance (A-n)** — binding. A failure means the stage contract is unsatisfied.
- **diagnostic (D-n)** — signals a probable defect. Obliges investigation, never fails
  a stage on its own. Treating a heuristic as a gate invites tuning output to satisfy
  the heuristic.
- **warning (W-n)** — cross-product signal requiring investigation. Escalates to a
  failure (A-15) only when materially different input is not reflected in output.

This module judges an artifact. It contains no product, benchmark, or mechanism
knowledge beyond the prohibited-solution lexicon of §9.3, which is illustrative and
extensible rather than a closed vocabulary.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from assy.domain.upstream import (
    ClauseDisposition,
    QuantityKind,
    RequirementKind,
    RequirementOrigin,
    RequirementSpec,
    VerificationKind,
)


class Severity(str, Enum):
    ACCEPTANCE = "acceptance"
    DIAGNOSTIC = "diagnostic"
    WARNING = "warning"


@dataclass
class RuleResult:
    rule: str
    severity: Severity
    passed: bool
    detail: str = ""

    def __str__(self) -> str:  # pragma: no cover - display only
        mark = "PASS" if self.passed else ("FAIL" if self.severity is Severity.ACCEPTANCE else "FLAG")
        return f"[{mark}] {self.rule:<5} {self.detail}"


@dataclass
class ValidationReport:
    results: list[RuleResult] = field(default_factory=list)

    @property
    def accepted(self) -> bool:
        """Acceptance rules only. Diagnostics and warnings never block."""
        return all(r.passed for r in self.results if r.severity is Severity.ACCEPTANCE)

    def failures(self) -> list[RuleResult]:
        return [r for r in self.results if r.severity is Severity.ACCEPTANCE and not r.passed]

    def flags(self) -> list[RuleResult]:
        return [r for r in self.results if r.severity is not Severity.ACCEPTANCE and not r.passed]

    def summary(self) -> str:
        a = [r for r in self.results if r.severity is Severity.ACCEPTANCE]
        return (
            f"{sum(1 for r in a if r.passed)}/{len(a)} acceptance rules pass; "
            f"{len(self.flags())} diagnostics/warnings raised"
        )


# STAGE_01 §9.3 — illustrative, extensible, never tuned to a benchmark.
SOLUTION_LEXICON = (
    "hinge", "latch", "snap", "gear", "rack", "pinion", "screw", "thread", "cam",
    "spring", "bearing", "bushing", "linkage", "lever", "pulley", "belt", "chain",
    "drum", "cable", "pawl", "detent", "ratchet", "clutch", "coupling", "piston",
    "damper", "geneva", "worm", "crank",
)

UNIT = r"(?:mm|cm|m|kg|g|N|Nm|deg|°|s|min|h)"
# A range writes its unit once. Parsed as an object BEFORE literal scanning, so
# both endpoints are visible; scanning literals first loses the lower endpoint.
RANGE_WITH_UNIT = re.compile(rf"(\d+(?:\.\d+)?)\s*[-–—]\s*(\d+(?:\.\d+)?)\s*({UNIT})\b", re.I)
NUMERIC_WITH_UNIT = re.compile(rf"(\d+(?:\.\d+)?)\s*({UNIT})\b", re.I)


def source_quantities(text: str) -> set[tuple[str, str]]:
    """Every quantity a source states, ranges included.

    Invariant: a range contributes BOTH endpoints. The consumed span is removed
    before scanning singles so the upper endpoint is not double counted.
    """
    found: set[tuple[str, str]] = set()
    remainder = text
    for m in RANGE_WITH_UNIT.finditer(text):
        unit = m.group(3).lower()
        found.add((f"{float(m.group(1)):g}", unit))
        found.add((f"{float(m.group(2)):g}", unit))
        remainder = remainder.replace(m.group(0), " ")
    for m in NUMERIC_WITH_UNIT.finditer(remainder):
        found.add((f"{float(m.group(1)):g}", m.group(2).lower()))
    return found
BEHAVIOURAL_VERB = re.compile(
    r"\b(lift|raise|lower|rotate|turn|slide|open|clos\w*|latch\w*|releas\w*|hold\w*|"
    r"retain\w*|index\w*|advance\w*|stay\w*|remain\w*|support\w*|transmit\w*|guide\w*|"
    r"prevent\w*|avoid\w*|enclos\w*|drive\w*|actuat\w*|engage\w*|disengag\w*)\b",
    re.I,
)


def _lexicon_hits(text: str) -> list[str]:
    low = text.lower()
    return [w for w in SOLUTION_LEXICON if re.search(rf"\b{w}", low)]


# --------------------------------------------------------------------------
# Acceptance rules
# --------------------------------------------------------------------------
def _acceptance(spec: RequirementSpec) -> list[RuleResult]:
    out: list[RuleResult] = []
    add = out.append

    def rule(rid: str, ok: bool, detail: str = "") -> None:
        add(RuleResult(rid, Severity.ACCEPTANCE, ok, detail))

    rids = spec.requirement_ids
    cids = spec.clause_ids
    unknown_ids = {u.id for u in spec.unknowns}

    # A-1 functional intent is solution-independent.
    # Applies ONLY to product_intent, which is the abstraction Stage 02 reasons
    # from. Fidelity is A-32's obligation, on a different field - one field could
    # not carry both, which is what made this rule unsatisfiable (F-09).
    intent = (spec.product_intent or "").strip()
    hits = _lexicon_hits(intent)
    rule(
        "A-1",
        bool(intent) and intent.count(".") <= 1 and not hits,
        f"functional_intent={'empty' if not intent else 'ok'}"
        + (f", names solution(s): {', '.join(hits)}" if hits else ""),
    )

    # A-32 user fidelity: a solution term the user imposed survives somewhere.
    # Abstraction must not silently delete a user-imposed design constraint.
    src_terms = set(_lexicon_hits(spec.source_text))
    if src_terms:
        preserved = set(_lexicon_hits(spec.user_intent_summary))
        for r in spec.requirements:
            preserved |= set(_lexicon_hits(r.statement))
        lost = sorted(src_terms - preserved)
        rule(
            "A-32",
            not lost,
            f"user-imposed terms erased: {lost or 'none'} (of {sorted(src_terms)})",
        )
    else:
        rule("A-32", True, "request imposes no solution terms")

    # A-2 at least one functional requirement
    functional = [r for r in spec.requirements if r.kind is RequirementKind.FUNCTIONAL]
    rule("A-2", bool(functional), f"{len(functional)} functional requirement(s)")

    # -- A-3 split into four independent obligations (contract r3) ---------
    # One rule previously mixed semantic coverage, function coverage, disposition
    # correctness, and generation completeness, so a failure never said WHICH had
    # gone wrong. A clause may be covered yet misclassified; it may be correctly
    # classified yet generate nothing. Those are different defects.
    fn_clauses = spec.clauses_with(ClauseDisposition.FUNCTION)
    treatable = [c for c in spec.clauses if c.disposition is not ClauseDisposition.NON_ENGINEERING]

    # every record type that can discharge a clause
    cited_by_any: dict[str, set[str]] = {}
    for kind_name, objs in (
        ("requirement", spec.requirements),
        ("freedom", spec.freedoms),
        ("scenario", spec.operating_scenarios),
        ("assumption", spec.assumptions),
        ("unknown", spec.unknowns),
    ):
        for o in objs:
            for cid in getattr(o, "derived_from", []):
                cited_by_any.setdefault(cid, set()).add(kind_name)

    # A-3a semantic coverage: every treatable clause reaches SOME record.
    uncovered = [c.id for c in treatable if c.id not in cited_by_any]
    rule(
        "A-3a",
        not uncovered,
        f"{len(treatable) - len(uncovered)}/{len(treatable)} treatable clauses reach a record"
        + (f"; unreached: {', '.join(uncovered[:6])}" if uncovered else ""),
    )

    # A-3b function coverage: behavioural clauses reach a behavioural requirement.
    behavioural = {
        cid
        for r in spec.requirements
        if r.kind in (RequirementKind.FUNCTIONAL, RequirementKind.PERFORMANCE)
        for cid in r.derived_from
    }
    unfunc = [c.id for c in fn_clauses if c.id not in behavioural]
    rule(
        "A-3b",
        not unfunc,
        f"{len(fn_clauses) - len(unfunc)}/{len(fn_clauses)} function clauses reach a behavioural requirement"
        + (f"; missing: {', '.join(unfunc[:6])}" if unfunc else ""),
    )

    # A-3d generation completeness: a disposition implies a record TYPE.
    # freedom -> DesignFreedom, constraint/function -> Requirement.
    wrong_type = []
    for c in treatable:
        kinds = cited_by_any.get(c.id, set())
        if not kinds:
            continue
        if c.disposition is ClauseDisposition.FREEDOM and "freedom" not in kinds:
            wrong_type.append(f"{c.id}(freedom->{sorted(kinds)})")
        elif (
            c.disposition in (ClauseDisposition.FUNCTION, ClauseDisposition.CONSTRAINT)
            and "requirement" not in kinds
        ):
            wrong_type.append(f"{c.id}({c.disposition.value}->{sorted(kinds)})")
    rule("A-3d", not wrong_type, f"clauses generating the wrong record type: {wrong_type or 'none'}")

    # A-4 bound triple invariant.
    # Invariant: a quantitative requirement carries a complete interval.
    # The previous rule guarded on `target is not None`, so a bound with a null
    # lower endpoint skipped the very check it existed to perform (F-02). The
    # invariant is now checked on the bound OBJECT, which cannot construct in an
    # incomplete state (SD-8) - this rule therefore proves the type held rather
    # than re-deriving it, and additionally catches an absent unit.
    bad = []
    for r in spec.requirements:
        b = r.bound
        if b is None:
            continue
        if not b.unit.strip():
            bad.append(f"{r.id}(no unit)")
        elif b.comparator == "between" and (b.lower is None or b.upper is None):
            bad.append(f"{r.id}(incomplete range)")
        elif b.lower is None and b.upper is None:
            bad.append(f"{r.id}(no endpoint)")
    rule("A-4", not bad, f"malformed bounds: {bad or 'none'}")

    # A-5 range-aware quantity coverage.
    # Invariant: every quantity the source states survives into the spec, both
    # endpoints of a range included. Ranges are parsed as objects before literal
    # scanning; the previous scan could not see a range's lower endpoint (F-03).
    src_q = source_quantities(spec.source_text)
    captured: set[tuple[str, str]] = set()
    for r in spec.requirements:
        if r.bound is None:
            continue
        unit = r.bound.unit.lower()
        for v in (r.bound.lower, r.bound.upper):
            if v is not None:
                captured.add((f"{float(v):g}", unit))
    unknown_text = " ".join(f"{u.subject} {u.reason}" for u in spec.unknowns).lower()
    missing = [
        f"{v} {u}" for (v, u) in sorted(src_q)
        if (v, u) not in captured and v not in unknown_text
    ]
    rule("A-5", not missing, f"source quantities not captured: {missing or 'none'}")

    # A-6 provenance-gated solution terms (STAGE_01 §3.4).
    # Invariant: a solution term may appear only where it is traceable to a clause
    # containing it - recording the user's wording is required, inferring a
    # mechanism is prohibited. The previous rule rejected all solution terms and
    # so rejected the behaviour PD-1 requires (F-01). False-failure risk removed;
    # false-pass risk retained and recorded: a term quoted from an unrelated cited
    # clause would pass.
    clause_text = {c.id: c.text.lower() for c in spec.clauses}
    ungrounded: dict[str, list[str]] = {}
    for r in spec.requirements:
        cited = " ".join(clause_text.get(cid, "") for cid in r.derived_from)
        inferred = [w for w in _lexicon_hits(r.statement) if not re.search(rf"\b{w}", cited)]
        if inferred:
            ungrounded[r.id] = inferred
    rule("A-6", not ungrounded, f"solution terms not traceable to a cited clause: {ungrounded or 'none'}")

    # A-7 assumptions imply a supplied origin somewhere
    supplied = [
        r
        for r in spec.requirements
        if r.origin in (RequirementOrigin.INFERRED, RequirementOrigin.PROJECT_DEFAULT)
    ]
    rule(
        "A-7",
        (not spec.assumptions) or bool(supplied) or bool(spec.unknowns),
        f"{len(spec.assumptions)} assumption(s), {len(supplied)} supplied-origin requirement(s)",
    )

    # A-8 supplied content is marked as supplied.
    # Invariant: whatever the interpreter added, rather than read, carries a
    # supplied origin. That is the genuine content of trap T4.
    # Two false-failure sources removed (validated against 15 runs):
    #   - it triggered on `unknowns`, but an unknown means information is MISSING,
    #     not that anything was supplied. 5 of 15 runs had zero assumptions and
    #     still failed.
    #   - it inspected only requirement origins, ignoring that supplied content
    #     lives in `assumptions`, which carry their own origin. Runs that were
    #     honouring the boundary failed anyway.
    # Requirement traceability is A-18's obligation and is not duplicated here.
    unmarked = [
        a.id
        for a in spec.assumptions
        if a.origin not in (RequirementOrigin.INFERRED, RequirementOrigin.PROJECT_DEFAULT)
    ]
    rule(
        "A-8",
        not unmarked,
        f"{len(spec.assumptions)} assumption(s); not marked as supplied: {unmarked or 'none'}",
    )

    # A-9 structural groundedness (SD-7).
    # Invariant: every context object is anchored to this request by citation.
    # Lexical overlap was a proxy and produced false failures on ordinary
    # morphology ("manufacturing" vs "manufacture", F-04). An unknown may anchor
    # via `affects` instead of `derived_from`, because a gap arises in the context
    # of a requirement rather than of a clause that mentions the missing thing.
    loose: list[str] = []
    loose += [x.id for x in spec.operating_scenarios if not x.derived_from]
    loose += [
        a.id for a in spec.assumptions
        if not a.derived_from
        and a.origin not in (RequirementOrigin.PROJECT_DEFAULT, RequirementOrigin.INFERRED)
    ]
    loose += [u.id for u in spec.unknowns if not u.derived_from and not u.affects]
    rule("A-9", not loose, f"context objects with no anchor: {loose or 'none'}")

    # A-10 priority discriminates
    prios = {r.priority for r in spec.requirements}
    rule(
        "A-10",
        len(spec.requirements) <= 3 or len(prios) >= 2,
        f"{len(spec.requirements)} requirements across priorities {sorted(prios) or 'none'}",
    )

    # A-11 no duplicate statements
    seen: dict[str, int] = {}
    for r in spec.requirements:
        seen[r.statement] = seen.get(r.statement, 0) + 1
    dupes = [s for s, n in seen.items() if n > 1]
    rule("A-11", not dupes, f"duplicate statements: {len(dupes)}")

    # A-12 verification intent present and coherent
    missing_v = [r.id for r in spec.requirements if r.verification is None]
    rule("A-12", not missing_v, f"requirements without verification intent: {missing_v or 'none'}")

    # A-13 source preserved
    rule("A-13", bool((spec.source_text or "").strip()), "source_text present")

    # A-14 an unknown may not name a resolved quantity
    conflict = [
        u.id
        for u in spec.unknowns
        for r in spec.requirements
        if r.target is not None and u.subject and u.subject.lower() in r.statement.lower()
    ]
    rule("A-14", not conflict, f"unknowns contradicting resolved targets: {conflict or 'none'}")

    # -- rules enabled by the cleared schema debts -------------------------
    # A-16 ledger covers request and clarifications
    have_request = any(c.source.value == "request" for c in spec.clauses)
    rule(
        "A-16",
        bool(spec.clauses) and have_request,
        f"{len(spec.clauses)} clause(s); request covered={have_request}",
    )

    # A-17 derived_from references resolve
    dangling = sorted(
        {
            cid
            for obj in (*spec.requirements, *spec.freedoms, *spec.assumptions,
                        *spec.operating_scenarios, *spec.unknowns)
            for cid in getattr(obj, "derived_from", [])
            if cid not in cids
        }
    )
    rule("A-17", not dangling, f"dangling clause refs: {dangling or 'none'}")

    # A-18 no orphan requirements
    orphans = [
        r.id
        for r in spec.requirements
        if not r.derived_from
        and r.origin not in (RequirementOrigin.INFERRED, RequirementOrigin.PROJECT_DEFAULT)
    ]
    rule("A-18", not orphans, f"untraceable requirements: {orphans or 'none'}")

    # A-19 verification coherence
    bad_v = []
    for r in spec.requirements:
        v = r.verification
        if v is None:
            continue
        if v.kind is VerificationKind.NOT_YET_VERIFIABLE and not (v.reason or "").strip():
            bad_v.append(f"{r.id}(no reason)")
        elif v.kind is not VerificationKind.NOT_YET_VERIFIABLE and not (v.observable or "").strip():
            bad_v.append(f"{r.id}(no observable)")
    rule("A-19", not bad_v, f"incoherent verification intent: {bad_v or 'none'}")

    # A-20 freedoms preserved, never invented
    freedom_clauses = {c.id for c in spec.clauses_with(ClauseDisposition.FREEDOM)}
    invented = [
        f.id
        for f in spec.freedoms
        if not (set(f.derived_from) & freedom_clauses)
        and f.origin not in (RequirementOrigin.INFERRED, RequirementOrigin.PROJECT_DEFAULT)
    ]
    rule("A-20", not invented, f"freedoms without a stated basis: {invented or 'none'}")

    # A-21 freedom must not silently duplicate a requirement
    stmts = {r.statement.strip().lower() for r in spec.requirements}
    related = {rel.source for rel in spec.relations} | {rel.target for rel in spec.relations}
    dup_f = [
        f.id for f in spec.freedoms if f.statement.strip().lower() in stmts and f.id not in related
    ]
    rule("A-21", not dup_f, f"freedoms duplicating requirements: {dup_f or 'none'}")

    # A-22 relations resolve and are irreflexive
    bad_rel = [
        f"{rel.kind.value}:{rel.source}->{rel.target}"
        for rel in spec.relations
        if rel.source not in rids or rel.target not in rids or rel.source == rel.target
    ]
    rule("A-22", not bad_rel, f"invalid relations: {bad_rel or 'none'}")

    # A-23 conflicts require rationale
    no_why = [
        f"{rel.source}->{rel.target}"
        for rel in spec.relations
        if rel.kind.value == "conflicts_with" and not rel.rationale.strip()
    ]
    rule("A-23", not no_why, f"conflicts without rationale: {no_why or 'none'}")

    # A-24 scenario bindings resolve
    bad_scn = sorted(
        {rid for s in spec.operating_scenarios for rid in s.applies_to if rid not in rids}
    )
    rule("A-24", not bad_scn, f"scenario refs not resolving: {bad_scn or 'none'}")

    # A-25 at least one scenario binds something
    bound = any(s.applies_to for s in spec.operating_scenarios)
    rule(
        "A-25",
        (not spec.requirements) or bound,
        f"{len(spec.operating_scenarios)} scenario(s), any bound={bound}",
    )

    # A-26 assumptions pair with unknowns
    bad_a = [a.id for a in spec.assumptions if a.stands_in_for and a.stands_in_for not in unknown_ids]
    rule("A-26", not bad_a, f"assumptions with unresolved stands_in_for: {bad_a or 'none'}")

    # A-27 unknown.affects resolves
    bad_u = sorted({rid for u in spec.unknowns for rid in u.affects if rid not in rids})
    rule("A-27", not bad_u, f"unknown.affects not resolving: {bad_u or 'none'}")

    # A-28 unknowns are substantive
    thin = [u.id for u in spec.unknowns if not u.subject.strip() or not u.reason.strip()]
    rule("A-28", not thin, f"unknowns missing subject/reason: {thin or 'none'}")

    # -- rules enforcing the unknown/freedom boundary (STAGE_01 §6.8b) ------
    # A-34 behavioural requirements carry their transformation.
    # Invariant: a consumer can determine what a behaviour transforms without
    # re-reading the request (STAGE_01 §5). Evidence for the rule: across six
    # generic probes the INPUT quantity was recoverable from structured output in
    # only 2 of 6, so the downstream stage had to re-parse source text.
    missing_beh = [
        r.id
        for r in spec.requirements
        if r.kind in (RequirementKind.FUNCTIONAL, RequirementKind.PERFORMANCE)
        and r.behaviour is None
    ]
    vague = [
        r.id
        for r in spec.requirements
        if r.behaviour is not None
        and r.behaviour.input_kind.value == "none"
        and r.behaviour.output_kind.value == "none"
    ]
    rule(
        "A-34",
        not missing_beh and not vague,
        f"behavioural requirements without a transformation: {missing_beh or 'none'}"
        + (f"; transformation unspecified on both sides: {vague}" if vague else ""),
    )

    # A-29 BR-1/BR-2: explicit non-prescription is a freedom, never an unknown.
    # Invariant: one clause does not yield both a freedom and an unknown about the
    # same subject. This is the direct cause of the observed instability (F-05):
    # both readings were compliant, so implementations oscillated.
    # Known limitation: subject overlap is lexical, so the same subject expressed
    # in different words escapes. Recorded rather than hidden.
    def _subject_words(text: str) -> set[str]:
        return {w for w in re.findall(r"[a-z]{4,}", text.lower())}

    freedom_by_clause: dict[str, list] = {}
    for f in spec.freedoms:
        for cid in f.derived_from:
            freedom_by_clause.setdefault(cid, []).append(f)
    collisions = []
    for u in spec.unknowns:
        u_words = _subject_words(u.subject)
        for cid in u.derived_from:
            for f in freedom_by_clause.get(cid, []):
                if u_words & _subject_words(f.subject + " " + f.statement):
                    collisions.append(f"{u.id}~{f.id}@{cid}")
    rule(
        "A-29",
        not collisions,
        f"clauses yielding both a freedom and an unknown: {collisions or 'none'}",
    )

    # A-30 BR-4: an unknown is obligatory only where a requirement depends on it,
    # so every unknown must name what it affects or say why it affects nothing.
    unanchored = [
        u.id
        for u in spec.unknowns
        if not u.affects and "affect" not in u.reason.lower() and len(u.reason.strip()) < 12
    ]
    rule("A-30", not unanchored, f"unknowns with no affected requirement: {unanchored or 'none'}")

    # A-31 every required discovery reaches a completion state.
    # Absence is a STATE, not a closing action (SD-9 revised). An empty list is
    # ambiguous between "none exist" and "the pass never ran"; a state is not.
    REQUIRED_DISCOVERIES = ("requirements", "freedoms", "relations", "unknowns",
                            "assumptions", "operating_scenarios")
    produced = {
        "requirements": bool(spec.requirements),
        "freedoms": bool(spec.freedoms),
        "relations": bool(spec.relations),
        "unknowns": bool(spec.unknowns),
        "assumptions": bool(spec.assumptions),
        "operating_scenarios": bool(spec.operating_scenarios),
    }
    stated = {o.discovery.strip().lower(): o for o in spec.discovery_outcomes}
    missing_state = [d for d in REQUIRED_DISCOVERIES if not produced[d] and d not in stated]
    no_reason = [
        o.discovery for o in spec.discovery_outcomes if o.needs_reason and not o.reason.strip()
    ]
    rule(
        "A-31",
        not missing_state and not no_reason,
        f"empty with no completion state: {missing_state or 'none'}"
        + (f"; states lacking a reason: {no_reason}" if no_reason else ""),
    )

    # A-33 unknown obligation and semantic equivalence.
    # Count is NOT the objective - two runs may express one uncertainty at
    # different granularity. What must hold is that no two unknowns are the same
    # unresolved quantity, and none contradicts a freedom or an assumption.
    def _key(u) -> frozenset:
        words = {w for w in re.findall(r"[a-z]{4,}", (u.subject + " " + u.resolvable_by).lower())}
        return frozenset(words)

    dupes = []
    seen_keys: list[tuple] = []
    for u in spec.unknowns:
        k = _key(u)
        for prev_id, prev_k, prev_aff in seen_keys:
            overlap = len(k & prev_k) / max(1, len(k | prev_k))
            if overlap >= 0.5 and (set(u.affects) & prev_aff or not u.affects):
                dupes.append(f"{u.id}~{prev_id}")
        seen_keys.append((u.id, k, set(u.affects)))

    assumed_subjects = {a.stands_in_for for a in spec.assumptions if a.stands_in_for}
    contradicted = [
        u.id for u in spec.unknowns
        if u.id in assumed_subjects and not any(
            a.stands_in_for == u.id and a.statement.strip() for a in spec.assumptions
        )
    ]
    rule(
        "A-33",
        not dupes and not contradicted,
        f"semantically duplicate unknowns: {dupes or 'none'}"
        + (f"; unknowns assumed away without a statement: {contradicted}" if contradicted else ""),
    )

    return out


# --------------------------------------------------------------------------
# Diagnostics
# --------------------------------------------------------------------------
def _diagnostics(spec: RequirementSpec) -> list[RuleResult]:
    out: list[RuleResult] = []
    verbs = {m.group(0).lower() for m in BEHAVIOURAL_VERB.finditer(spec.source_text)}
    behavioural = [
        r
        for r in spec.requirements
        if r.kind in (RequirementKind.FUNCTIONAL, RequirementKind.PERFORMANCE)
    ]
    out.append(
        RuleResult(
            "D-1",
            Severity.DIAGNOSTIC,
            len(behavioural) >= len(verbs),
            f"{len(behavioural)} behavioural requirement(s) vs {len(verbs)} distinct source verb(s)"
            + (f": {sorted(verbs)}" if verbs else ""),
        )
    )
    ratio = len(spec.requirements) / len(spec.clauses) if spec.clauses else 0.0
    out.append(
        RuleResult(
            "D-2", Severity.DIAGNOSTIC, ratio >= 0.5,
            f"requirements/clauses = {ratio:.2f}",
        )
    )
    # D-4 disposition/generation mismatch. A `function` clause covered only by
    # non-behavioural records is EITHER misclassified (it was never a function) OR
    # under-generated (it is, and no behavioural requirement was made). Which one
    # cannot be decided without ground truth, so this flags the ambiguity rather
    # than blaming either.
    fn_ids = {c.id for c in spec.clauses_with(ClauseDisposition.FUNCTION)}
    behav = {
        cid
        for r in spec.requirements
        if r.kind in (RequirementKind.FUNCTIONAL, RequirementKind.PERFORMANCE)
        for cid in r.derived_from
    }
    any_req = {cid for r in spec.requirements for cid in r.derived_from}
    ambiguous = sorted(fn_ids - behav)
    out.append(
        RuleResult(
            "D-4", Severity.DIAGNOSTIC, not ambiguous,
            "; ".join(
                f"{cid}: {'covered by a non-behavioural requirement (misclassified or under-generated)' if cid in any_req else 'no requirement at all'}"
                for cid in ambiguous[:4]
            ) or "no disposition/generation mismatch",
        )
    )

    stated = sum(
        1 for r in spec.requirements if r.origin is RequirementOrigin.USER_STATED
    )
    frac = stated / len(spec.requirements) if spec.requirements else 0.0
    out.append(
        RuleResult(
            "D-3", Severity.DIAGNOSTIC, frac < 1.0 or not spec.requirements,
            f"{frac:.0%} of requirements are USER_STATED",
        )
    )
    return out


def validate(spec: RequirementSpec) -> ValidationReport:
    """Acceptance rules plus diagnostics for one RequirementSpec."""
    return ValidationReport(results=_acceptance(spec) + _diagnostics(spec))


# --------------------------------------------------------------------------
# Cross-product warning (W-1) and its escalation (A-15)
# --------------------------------------------------------------------------
def cross_product(specs: list[RequirementSpec]) -> list[RuleResult]:
    """W-1 warning, escalating to A-15 only when input difference is unreflected.

    Identical context across two products is a *signal*, not a defect: products may
    legitimately share an environment, duty class, or open question. It becomes a
    failure only when the requests differ materially and no difference survives into
    the outputs.
    """
    out: list[RuleResult] = []
    for i, a in enumerate(specs):
        for b in specs[i + 1 :]:
            if a.product_intent == b.product_intent:
                continue

            def ctx(s: RequirementSpec) -> tuple:
                return (
                    tuple(sorted(x.name for x in s.operating_scenarios)),
                    tuple(sorted(x.statement for x in s.assumptions)),
                    tuple(sorted(x.subject for x in s.unknowns)),
                )

            pair = f"{a.product_intent[:28]!r} vs {b.product_intent[:28]!r}"
            if ctx(a) != ctx(b):
                continue

            out.append(
                RuleResult("W-1", Severity.WARNING, False, f"identical context: {pair}")
            )

            # Escalation test: did the inputs differ materially, and did anything
            # in the outputs record that difference?
            va = {m.group(0).lower() for m in BEHAVIOURAL_VERB.finditer(a.source_text)}
            vb = {m.group(0).lower() for m in BEHAVIOURAL_VERB.finditer(b.source_text)}
            inputs_differ = bool(va ^ vb)

            def signature(s: RequirementSpec) -> tuple:
                return (
                    tuple(sorted(r.statement for r in s.requirements)),
                    tuple(sorted(f.statement for f in s.freedoms)),
                )

            outputs_differ = signature(a) != signature(b)
            out.append(
                RuleResult(
                    "A-15",
                    Severity.ACCEPTANCE,
                    (not inputs_differ) or outputs_differ,
                    f"{pair}: inputs differ={inputs_differ}, outputs differ={outputs_differ}",
                )
            )
    return out
