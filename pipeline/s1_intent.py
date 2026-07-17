"""Stage ① Function interpretation (MECHSYNTH §4-①) — LLM.

in: `command: str`  ·  out: `functions[]` mapped onto the Functional Basis verb subset.

Gate **G1**: (a) every function.verb is in the vocabulary; (b) quantitative phrases in the command
("300 mm") are captured as qualifiers — missing = fail.

G1b is the interesting half. A command's numbers are the only hard requirements a user states
outright; if ① drops "300 mm" on the floor, every downstream stage optimises a problem the user did
not ask for, and nothing later can notice. So the gate re-reads the command for quantities and
insists each one survives into a qualifier.
"""

from __future__ import annotations

import re

from ontology.functional_basis import check_functions, vocabulary_prompt_block
from ontology.schema import Function
from pipeline.fewshot import assert_no_leakage, tsl_functions_example
from pipeline.llm_client import call_structured

SCHEMA = {
    "type": "object",
    "properties": {
        "functions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "verb": {"type": "string"},
                    "object": {"type": "string"},
                    "qualifier": {"type": "string"},
                },
                "required": ["verb", "object", "qualifier"],
            },
        }
    },
    "required": ["functions"],
}

# a number with an optional unit, or a bare count — the quantities a command can state
_QTY = re.compile(r"\b\d+(?:\.\d+)?\s*(?:mm|cm|m|deg|degrees?|°|N|kg|g|x|×)?\b", re.I)


def quantities(command: str) -> list[str]:
    """Quantitative phrases in the command (G1b's referents)."""
    out = []
    for m in _QTY.finditer(command):
        t = m.group(0).strip()
        if re.fullmatch(r"3\s*d", t, re.I):        # "3D printing" is not a requirement quantity
            continue
        out.append(t)
    return out


def _prompt(command: str) -> str:
    return f"""You map a design command onto FUNCTIONS from a controlled vocabulary.

# The Functional Basis verb subset — you MUST choose verbs from this list ONLY
{vocabulary_prompt_block()}

# Rules
- Output one function per distinct user-level purpose in the command. Usually 1-3.
- `verb` MUST be exactly one of the vocabulary terms above (lowercase, as written).
- `object` is the thing acted on, in the command's own words (e.g. "lid", "contents").
- `qualifier` carries HOW/how-much: any quantity stated in the command (sizes, angles, counts,
  forces) MUST appear in a qualifier verbatim. If the command states no quantity, use the
  qualifier for the manner ("repeated open/close", "hand-releasable").
- Describe the PURPOSE, not the mechanism. Do not name hinges, latches, or parts.

# Worked example (a DIFFERENT task)
{tsl_functions_example()}

# Now solve this one
command: "{command}"
Answer with the JSON object only."""


def run(ir, ctx=None):
    """① — returns a copy of `ir` with functions[] filled. Raises StageFailure('s1','G1')."""
    command = ir.command
    prompt = _prompt(command)
    assert_no_leakage(prompt)                      # D-E-1, enforced mechanically
    qtys = quantities(command)

    def parse(d):
        return [Function(**f) for f in d["functions"]]

    def validate(fns):
        errs = list(check_functions(fns))                                   # G1a
        if not fns:
            errs.append("no functions produced; a command always states at least one purpose")
        for q in qtys:                                                      # G1b
            if not any(q.lower() in (f.qualifier or "").lower() for f in fns):
                errs.append(
                    f"G1b: the command states the quantity {q!r} but no function qualifier carries "
                    f"it. Every quantity in the command must survive into a qualifier verbatim.")
        return errs

    fns = call_structured(ir=ir, stage="s1", gate="G1", prompt=prompt, schema=SCHEMA,
                          parse=parse, validate=validate)
    out = ir.model_copy(deep=True)
    out.functions = fns
    out.stage_log = ir.stage_log
    return out


def viz(ir) -> str:
    """s1_functions.md — command text ↔ function mapping (§4-① viz requirement)."""
    from ontology.functional_basis import FUNCTIONAL_BASIS
    L = ["# Stage ① — function interpretation", "", f"**command:** `{ir.command}`", "",
         f"**quantities detected (G1b referents):** {quantities(ir.command) or '(none stated)'}", "",
         "| verb | Functional Basis class | object | qualifier |", "|---|---|---|---|"]
    for f in ir.functions:
        cls = FUNCTIONAL_BASIS.get(f.verb, ("?",))[0]
        L.append(f"| `{f.verb}` | {cls} | {f.object} | {f.qualifier or ''} |")
    return "\n".join(L) + "\n"
