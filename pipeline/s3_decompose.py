"""Stage ③ Piece decomposition (MECHSYNTH §4-③) — LLM (KG-informed).

out: `pieces[]` (role + template_ref), drawn from the fixed template vocabulary.

Gate **G3**: V-07 (piece participation — precheck only, since bindings arrive at ④), template_ref
existence, piece count ≤ 6.

DRAFT (D-E-3): §4-③ names a fixed SIX-template vocabulary — box_shell / lid_panel / drawer_tray /
cabinet_shell / knob_shaft / rack_bar — but only `box_shell` and `lid_panel` are IMPLEMENTED (plus
flat_panel_mount / retained_board, which are the D-GEN-1 panel hosts, not in the spec's six). This
stage constrains ③ to what ⑥ can actually COMPILE, because offering a template the compiler cannot
build would let ③ emit an IR that is valid and unbuildable — a failure that would surface far away
from its cause. Flagged for G-H: either implement the missing four or amend §4-③'s vocabulary.
"""

from __future__ import annotations

from knowledge.templates import TEMPLATES
from ontology.schema import Piece
from pipeline.fewshot import assert_no_leakage, tsl_pieces_example
from pipeline.llm_client import call_structured

SPEC_VOCAB = ("box_shell", "lid_panel", "drawer_tray", "cabinet_shell", "knob_shaft", "rack_bar")
BUILDABLE = tuple(TEMPLATES)          # what ⑥ can actually compile — the real constraint
MAX_PIECES = 6


def _describe(name: str) -> str:
    return {
        "box_shell": "an open-top box: four walls + a floor. The container body.",
        "lid_panel": "a flat panel that seats on top of a box_shell. The closure.",
        "flat_panel_mount": "a base plate with two upstand rails (a board-clip host).",
        "retained_board": "a flat board held between rails (a foreign/retained part).",
    }.get(name, "(no description)")


SCHEMA = {
    "type": "object",
    "properties": {
        "pieces": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "role": {"type": "string"},
                    "template_ref": {"type": "string", "enum": list(BUILDABLE)},
                    "is_base": {"type": "boolean"},
                },
                "required": ["id", "role", "template_ref", "is_base"],
            },
        }
    },
    "required": ["pieces"],
}


def _prompt(ir) -> str:
    fns = [{"verb": f.verb, "object": f.object, "qualifier": f.qualifier} for f in ir.functions]
    bs = [{"id": b.id, "phase": getattr(b.phase, "value", b.phase),
           "motion": getattr(b.motion.kind, "value", b.motion.kind)} for b in ir.behaviors]
    vocab = "\n".join(f"  - {t}: {_describe(t)}" for t in BUILDABLE)
    return f"""You decompose a product into PIECES — the separate rigid bodies that get manufactured.

# Template vocabulary — you MUST choose template_ref from this list ONLY
{vocab}

# Rules
- One piece per separately-manufactured rigid body. At most {MAX_PIECES}.
- `role` is a short word for what it is in THIS product ("base", "lid", ...).
- EXACTLY ONE piece has is_base=true: the piece everything else is positioned relative to (the
  fixed body — the one a bench vice would clamp).
- Do NOT invent pieces for fasteners, pins or hooks. Those come from elements later, and a hinge
  brings its own pin automatically. Pieces here are only the HOSTS.
- ids are P1, P2, ...

# Worked example (a DIFFERENT task)
{tsl_pieces_example()}

# Now solve this one
command: "{ir.command}"
functions: {fns}
behaviors: {bs}
Answer with the JSON object only."""


def run(ir, ctx=None):
    """③ — returns a copy with pieces[] filled. Raises StageFailure('s3','G3')."""
    prompt = _prompt(ir)
    assert_no_leakage(prompt)

    def parse(d):
        return [Piece(id=p["id"], role=p["role"], template_ref=p["template_ref"],
                      is_base=bool(p.get("is_base", False))) for p in d["pieces"]]

    def validate(ps):
        errs = []
        if not ps:
            return ["no pieces produced"]
        if len(ps) > MAX_PIECES:                                             # G3 count
            errs.append(f"G3: {len(ps)} pieces exceeds the maximum of {MAX_PIECES}.")
        for p in ps:
            if p.template_ref not in TEMPLATES:                              # G3 existence
                errs.append(f"G3: piece {p.id} uses template_ref={p.template_ref!r}, which does "
                            f"not exist. Choose from {list(BUILDABLE)}.")
        nb = sum(1 for p in ps if p.is_base or p.role == "base")
        if nb != 1:
            errs.append(f"G3/D23: exactly one piece must be the base (is_base=true); found {nb}.")
        if len({p.id for p in ps}) != len(ps):
            errs.append("G3: piece ids must be unique.")
        return errs

    ps = call_structured(ir=ir, stage="s3", gate="G3", prompt=prompt, schema=SCHEMA,
                         parse=parse, validate=validate)
    out = ir.model_copy(deep=True)
    out.pieces = ps
    out.stage_log = ir.stage_log
    return out


def viz(ir) -> str:
    """s3_pieces.md (§4-③ viz requirement)."""
    L = ["# Stage ③ — piece decomposition", "",
         "| id | role | template_ref | base? |", "|---|---|---|---|"]
    for p in ir.pieces:
        L.append(f"| {p.id} | {p.role} | `{p.template_ref}` | {'⏚ yes' if p.is_base else ''} |")
    L += ["", f"buildable template vocabulary: {list(BUILDABLE)}",
          f"(spec §4-③ names six: {list(SPEC_VOCAB)} — see D-E-3 DRAFT)"]
    return "\n".join(L) + "\n"
