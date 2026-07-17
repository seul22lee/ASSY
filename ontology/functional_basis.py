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

DOMAIN EXTENSION — honesty note (D-E-2 DRAFT): `allow_access` is NOT canonical NIST. The nearest
canonical terms are Channel→Export ("send a material outside the system boundary") and
Provision→Supply, but neither names the USER-LEVEL AFFORDANCE the anchors are actually about ("a
lid you can open to reach the contents"). The project's goldens use `allow_access`, so it is carried
here as an explicit, flagged extension rather than silently mapped onto Export — mislabelling it
canonical would make the vocabulary's provenance a lie. Flagged for G-H ruling.
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
    # --- DOMAIN EXTENSION (flagged, not canonical NIST) ---------------------------------
    "allow_access": ("Provision (domain extension)",
                     "to make contained material reachable by a user on demand — the user-level "
                     "affordance an opening lid/door provides. NOT canonical NIST; see module "
                     "docstring (D-E-2 DRAFT).",
                     "project extension over " + NIST_TN1447),
}

VERBS: frozenset[str] = frozenset(FUNCTIONAL_BASIS)
CANONICAL_NIST: frozenset[str] = frozenset(
    v for v, (cls, _g, _p) in FUNCTIONAL_BASIS.items() if "extension" not in cls)


def is_valid(verb: str) -> bool:
    return verb in VERBS


def gloss(verb: str) -> str:
    cls, g, _ = FUNCTIONAL_BASIS[verb]
    return f"{verb} [{cls}] — {g}"


def vocabulary_prompt_block() -> str:
    """The verb list as the LLM sees it at stage ① — the closed set it must choose from."""
    return "\n".join(f"  - {gloss(v)}" for v in FUNCTIONAL_BASIS)


def check_functions(functions) -> list[str]:
    """G1a: every function.verb is in the vocabulary. Returns violation strings ([] = clean)."""
    bad = []
    for f in functions:
        v = getattr(f, "verb", None) if not isinstance(f, dict) else f.get("verb")
        if v not in VERBS:
            bad.append(f"function verb {v!r} is not in the Functional Basis subset "
                       f"(allowed: {sorted(VERBS)})")
    return bad
