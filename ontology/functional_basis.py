"""NIST Functional Basis vocabulary subset (MECHSYNTH §4-① gate G1a).

The controlled verb list stage ① must map a free-text command onto. Constraining ① to a closed
vocabulary is the first place the "LLM makes discrete choices only" thesis bites: the model may not
invent a function name, so downstream stages always receive a term the KG can reason about.

Provenance — Hirtz, Stone, McAdams, Szykman & Wood, "A functional basis for engineering design:
reconciling and evolving previous efforts", NIST Technical Note 1447 (2002). The full basis is 8
primary classes; this subset carries the CLASSES AND SECONDARIES REACHABLE IN THIS DOMAIN (rigid
assemblies of a few plastic pieces), which is what the v0.1 anchors exercise. Each entry cites its
class so a report footnote can trace the term (§2 "no constant without provenance", applied to
vocabulary).

DOMAIN EXTENSION — **D-E-2 CONFIRMED (G-H)**: `allow_access` is an OFFICIAL member of this subset,
carried as an explicitly FLAGGED extension with its nearest-NIST mapping annotated (NEAREST_NIST).
It is not canonical NIST: the nearest canonical terms are Channel→Export and Provision→Supply, but
neither names the USER-LEVEL AFFORDANCE the anchors are about ("a lid you can open to reach the
contents"). Annotated, never substituted — silently mapping it onto Export would make the
vocabulary's own provenance a lie, the same error class as a constant without a citation (§2).

ALIASES (D-E-2): a verb may declare aliases — other subset terms that name the SAME decision closely
enough that choosing either is a vocabulary ambiguity, not a model error. The scorer counts a
declared alias as a match and reports BOTH numbers (strict and alias-aware), so the concession is
always visible rather than baked into one figure. Every alias needs a stated ALIAS_REASON: an alias
is a claim about the vocabulary, never a way to make a score look better.
"""

from __future__ import annotations

NIST_TN1447 = "NIST TN 1447 (Hirtz et al. 2002) — A Functional Basis for Engineering Design"

# verb -> (primary class, gloss, provenance)
FUNCTIONAL_BASIS: dict[str, tuple[str, str, str]] = {
    # --- Support: hold a part in place -------------------------------------------------
    "secure": ("Support", "to fasten a part into a fixed position (a latch, a clip, a fastener)",
               NIST_TN1447),
    "position": ("Support", "to place a part into a specific location or orientation", NIST_TN1447),
    "stabilize": ("Support", "to prevent a part from changing position", NIST_TN1447),
    # --- Channel: route a material/part through the system -----------------------------
    "guide": ("Channel", "to direct the path of a part along a specific course", NIST_TN1447),
    "transfer": ("Channel", "to move a part from one place to another", NIST_TN1447),
    "export": ("Channel", "to send a part outside the system boundary", NIST_TN1447),
    "import": ("Channel", "to bring a part in from outside the system boundary", NIST_TN1447),
    # --- Connect: join parts -----------------------------------------------------------
    "couple": ("Connect", "to join parts so they act as one", NIST_TN1447),
    # --- Control Magnitude: govern how much motion happens -----------------------------
    "actuate": ("Control Magnitude", "to commence the flow of energy/motion", NIST_TN1447),
    "regulate": ("Control Magnitude", "to adjust the flow of energy/motion", NIST_TN1447),
    "stop": ("Control Magnitude", "to cease the flow of energy/motion (an end stop, a limit)",
             NIST_TN1447),
    # --- Provision: contain -------------------------------------------------------------
    "store": ("Provision", "to accumulate or contain a material", NIST_TN1447),
    "supply": ("Provision", "to provide a material for use", NIST_TN1447),
    # --- DOMAIN EXTENSION — official, flagged, nearest-NIST annotated (D-E-2 CONFIRMED) ---
    "allow_access": ("Provision (domain extension)",
                     "to make contained material reachable by a user on demand — the user-level "
                     "affordance an opening lid/door provides. NOT canonical NIST; nearest "
                     "canonical: Channel→Export / Provision→Supply (see NEAREST_NIST).",
                     "project extension over " + NIST_TN1447),
}

# D-E-2: the nearest canonical NIST term(s) for each domain extension. Annotated, never substituted
# — the mapping is "closest relative", not "is a".
NEAREST_NIST: dict[str, tuple[str, ...]] = {
    "allow_access": ("export", "supply"),
}

# D-E-2: declared aliases — verbs in this subset that name the SAME decision closely enough that
# picking either is a vocabulary ambiguity rather than an error. Symmetric. Each needs a reason.
ALIASES: dict[str, tuple[str, ...]] = {
    "allow_access": ("position",),
    "position": ("allow_access",),
}
ALIAS_REASON: dict[frozenset, str] = {
    frozenset({"allow_access", "position"}):
        "For an opening lid, 'allow_access: contents' (the user-level affordance) and 'position: "
        "lid' (the physical placement that provides it) name the same design decision from two "
        "legitimate viewpoints; the subset offers both and does not disambiguate. Charging the "
        "difference to the model would score our vocabulary's ambiguity as its error.",
}


def aliases_of(verb: str) -> frozenset[str]:
    """The verb plus any declared alias — the equivalence class the scorer may match within."""
    return frozenset({verb, *ALIASES.get(verb, ())})


def alias_match(a: str, b: str) -> bool:
    return a == b or b in ALIASES.get(a, ())

VERBS: frozenset[str] = frozenset(FUNCTIONAL_BASIS)
CANONICAL_NIST: frozenset[str] = frozenset(
    v for v, (cls, _g, _p) in FUNCTIONAL_BASIS.items() if "extension" not in cls)


def is_valid(verb: str) -> bool:
    return verb in VERBS


def gloss(verb: str) -> str:
    cls, g, _ = FUNCTIONAL_BASIS[verb]
    return f"{verb} [{cls}] — {g}"


def vocabulary_prompt_block() -> str:
    """The verb list as the LLM sees it at stage ① — the closed set it must choose from.
    Domain extensions carry their nearest-NIST annotation so the model sees the same provenance a
    reviewer would (D-E-2)."""
    out = []
    for v in FUNCTIONAL_BASIS:
        line = f"  - {gloss(v)}"
        if v in NEAREST_NIST:
            line += f"  [domain extension; nearest canonical NIST: {', '.join(NEAREST_NIST[v])}]"
        out.append(line)
    return "\n".join(out)


def check_functions(functions) -> list[str]:
    """G1a: every function.verb is in the vocabulary. Returns violation strings ([] = clean)."""
    bad = []
    for f in functions:
        v = getattr(f, "verb", None) if not isinstance(f, dict) else f.get("verb")
        if v not in VERBS:
            bad.append(f"function verb {v!r} is not in the Functional Basis subset "
                       f"(allowed: {sorted(VERBS)})")
    return bad
