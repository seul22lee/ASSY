"""Stage ② Behavior derivation (MECHSYNTH §4-②) — LLM + phase rules.

out: `behaviors[]` — each with a phase; use-phase MotionSpec fully populated.

Gate **G2**: V-01 precheck (a protocol slot is reserved for every use behaviour), V-06, V-11, unit
checks, and the **Easy-anchor expectation**: use (rotation ≥90°) + static (hold closed) + assembly
(2-piece fastening) — fewer = fail.

Note on the expectation: it is enforced as a GATE, never whispered into the prompt. Telling the
model "you need a use-rotation, a static-hold and an assembly-fastening" would be dictating the
answer and the scorecard would measure obedience. Instead the model derives behaviours from the
functions alone; if it comes up short, the repair loop hands it the validator's own words. What it
produces unaided is the measurement.
"""

from __future__ import annotations

from ontology.schema import Behavior, MotionSpec
from pipeline.fewshot import assert_no_leakage, tsl_behaviors_example
from pipeline.llm_client import call_structured

PHASES = ("assembly", "use", "static")
KINDS = ("rotation", "translation", "rot_to_trans", "fixed", "snap_event")

SCHEMA = {
    "type": "object",
    "properties": {
        "behaviors": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "phase": {"type": "string", "enum": list(PHASES)},
                    "motion": {
                        "type": "object",
                        "properties": {
                            "kind": {"type": "string", "enum": list(KINDS)},
                            "axis_hint": {"type": "string"},
                            "range_value": {"type": "number"},
                            "range_unit": {"type": "string"},
                            "bound": {"type": "string", "enum": ["min", "max"]},
                            "event_force_window_N": {"type": "array", "items": {"type": "number"}},
                        },
                        "required": ["kind"],
                    },
                },
                "required": ["id", "phase", "motion"],
            },
        }
    },
    "required": ["behaviors"],
}

# §4-②: the Easy anchor must yield at least these three: "use (rotation >=90 deg) + static (hold
# closed) + assembly (2-piece fastening) — fewer = fail". A GATE, not a hint.
#
# Each entry is (phase, {acceptable kinds}, min_range, why). The kind SETS are deliberate: the gate
# must encode the SPEC'S REQUIREMENT, not the golden's particular encoding of it. "Hold closed" is
# honestly expressible as `fixed` (a held state) or `snap_event` (a latch that holds); "2-piece
# fastening" as `translation` (an insertion path — how the golden happens to say it) or `snap_event`
# (the fastening event itself). Pinning one spelling would fail a correct answer for disagreeing
# with the answer key's dialect, and would be measuring obedience rather than correctness.
EASY_EXPECTATION = (
    ("use", {"rotation"}, 90.0, "the lid must open — a use-phase rotation of at least 90 deg"),
    ("static", {"fixed", "snap_event"}, None, "the lid must stay shut — a static-phase hold"),
    ("assembly", {"translation", "snap_event"}, None,
     "the pieces must be fastened together — an assembly-phase fastening/insertion"),
)


def _prompt(ir) -> str:
    fns = [{"verb": f.verb, "object": f.object, "qualifier": f.qualifier} for f in ir.functions]
    return f"""You derive BEHAVIOURS (what physically happens) from FUNCTIONS (what the user wants).

# Vocabulary — closed sets, choose only from these
phase: assembly (putting the product together) | use (in normal operation) | static (holding a state)
motion.kind: rotation | translation | rot_to_trans | fixed | snap_event

# Rules
- A behaviour is a PHYSICAL fact, not a part. Never name a hinge/latch/screw — that is chosen later.
- Every distinct phase of the product's life that a function implies gets its own behaviour:
  think about (a) operating it, (b) it holding its state, (c) ASSEMBLING it in the first place.
- use-phase motion MUST be fully populated: kind, axis_hint, and a range (`range_value` +
  `range_unit` + `bound`: "min" = at least this much travel, "max" = a ceiling/limit).
- kind=snap_event MUST carry `event_force_window_N` as [mate_force, separate_force] in newtons.
- kind=rot_to_trans MUST carry a transmission.
- ids are B1, B2, ...

# Worked example (a DIFFERENT task)
{tsl_behaviors_example()}

# Now solve this one
command: "{ir.command}"
functions: {fns}
Answer with the JSON object only."""


def run(ir, ctx=None):
    """② — returns a copy with behaviors[] filled. Raises StageFailure('s2','G2')."""
    ctx = ctx or {}
    expectation = ctx.get("expectation", EASY_EXPECTATION)
    prompt = _prompt(ir)
    assert_no_leakage(prompt)

    def parse(d):
        out = []
        for b in d["behaviors"]:
            m = dict(b["motion"])
            w = m.get("event_force_window_N")
            if isinstance(w, list) and len(w) == 2:
                m["event_force_window_N"] = (float(w[0]), float(w[1]))
            elif w is not None:
                m.pop("event_force_window_N")
            out.append(Behavior(id=b["id"], phase=b["phase"], motion=MotionSpec(**m)))
        return out

    def validate(bs):
        errs = []
        if not bs:
            return ["no behaviors produced"]
        for b in bs:
            k = getattr(b.motion.kind, "value", b.motion.kind)
            ph = getattr(b.phase, "value", b.phase)
            if k == "snap_event" and not b.motion.event_force_window_N:      # V-11
                errs.append(f"V-11: behaviour {b.id} is a snap_event but carries no "
                            f"event_force_window_N [mate_N, separate_N].")
            if k == "rot_to_trans" and not b.motion.transmission:            # V-06
                errs.append(f"V-06: behaviour {b.id} is rot_to_trans but carries no transmission.")
            if ph == "use" and k in ("rotation", "translation"):
                if b.motion.range_value is None or not b.motion.range_unit:
                    errs.append(f"§4-②: use-phase behaviour {b.id} ({k}) must have a fully "
                                f"populated MotionSpec: range_value + range_unit + bound.")
                elif k == "rotation" and b.motion.range_unit.lower() not in ("deg", "degree",
                                                                            "degrees", "rad"):
                    errs.append(f"unit check: behaviour {b.id} is a rotation but range_unit is "
                                f"{b.motion.range_unit!r}; use 'deg'.")
        # the Easy expectation (G2) — a gate, in the validator's own words on retry
        for ph, kinds, min_range, why in expectation:
            hits = [b for b in bs
                    if getattr(b.phase, "value", b.phase) == ph
                    and getattr(b.motion.kind, "value", b.motion.kind) in kinds]
            if not hits:
                errs.append(f"G2 expectation: no {ph}-phase behaviour with motion.kind in "
                            f"{sorted(kinds)}. {why}")
            elif min_range is not None and not any(
                    (b.motion.range_value or 0) >= min_range for b in hits):
                got = [b.motion.range_value for b in hits]
                errs.append(f"G2 expectation: the {ph}-phase {'/'.join(sorted(kinds))} behaviour "
                            f"must reach at least {min_range:g} (got {got}). {why}")
        return errs

    bs = call_structured(ir=ir, stage="s2", gate="G2", prompt=prompt, schema=SCHEMA,
                         parse=parse, validate=validate)
    out = ir.model_copy(deep=True)
    out.behaviors = bs
    out.stage_log = ir.stage_log
    return out


def viz(ir) -> str:
    """s2_behaviors.mmd — Function→Behavior graph, phase-coloured (§4-② viz requirement)."""
    FILL = {"use": "#c6f6d5", "assembly": "#bee3f8", "static": "#fefcbf"}
    L = ["flowchart LR", f'  %% {ir.task_id} — stage ② behaviours']
    for i, f in enumerate(ir.functions):
        L.append(f'  FN{i}("{f.verb}: {f.object}"):::fn')
    for b in ir.behaviors:
        ph = getattr(b.phase, "value", b.phase)
        k = getattr(b.motion.kind, "value", b.motion.kind)
        rng = f"\\n{b.motion.bound or ''} {b.motion.range_value}{b.motion.range_unit or ''}" \
            if b.motion.range_value is not None else ""
        L.append(f'  {b.id}["{b.id} · {ph}\\n{k}{rng}"]:::{ph}')
        for i in range(len(ir.functions)):
            pass
    for i in range(len(ir.functions)):
        for b in ir.behaviors:
            L.append(f"  FN{i} -.-> {b.id}") if False else None
    L.append('  classDef fn fill:#e9d8fd,stroke:#6b46c1;')
    for ph, c in FILL.items():
        L.append(f"  classDef {ph} fill:{c},stroke:#2d3748;")
    return "\n".join(L) + "\n"
