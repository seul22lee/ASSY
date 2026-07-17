"""Few-shot example selection — and the leakage rule that governs it (D-E-1).

**D-E-1 (few-shot / leakage policy).** A stage prompt may carry exactly ONE worked example, and it
must come from a DIFFERENT task than the one being solved. For the Easy-anchor run the example is
the T-S1 golden (`snap_starter`); the Easy golden (`anchor_easy`) is NEVER shown at any stage.

Why this is a rule and not a preference: the Easy golden IS the grading key. Showing it — even
"just the behaviours", even at a different stage — turns the scorecard from a measurement of
synthesis into a measurement of copying, and the number would look BETTER while meaning LESS. The
demand is that the model generalize the FORM of a correct IR from one task to another, which is the
capability the E-track is actually claiming.

`assert_no_leakage()` enforces it mechanically rather than by care: any prompt is checked against
distinctive strings from the forbidden golden, so a future edit that quietly pastes the answer in
fails loudly instead of scoring well.
"""

from __future__ import annotations

import json

FORBIDDEN_TASK = "anchor_easy"


def _plan_json(plan) -> dict:
    return json.loads(plan.model_dump_json())


def tsl_functions_example() -> str:
    """T-S1 ①: command → functions."""
    from tasks.build_goldens import snap_starter
    p = snap_starter()
    fns = [{"verb": f.verb, "object": f.object, "qualifier": f.qualifier} for f in p.functions]
    return (f'command: "{p.command}"\n'
            f'answer: {json.dumps({"functions": fns}, indent=2)}')


def tsl_behaviors_example() -> str:
    """T-S1 ②: functions → behaviors."""
    from tasks.build_goldens import snap_starter
    p = snap_starter()
    fns = [{"verb": f.verb, "object": f.object, "qualifier": f.qualifier} for f in p.functions]
    bs = []
    for b in p.behaviors:
        m = {k: v for k, v in json.loads(b.motion.model_dump_json()).items() if v is not None}
        bs.append({"id": b.id, "phase": getattr(b.phase, "value", b.phase), "motion": m})
    return (f'functions: {json.dumps(fns)}\n'
            f'answer: {json.dumps({"behaviors": bs}, indent=2)}')


def tsl_pieces_example() -> str:
    """T-S1 ③: behaviors → pieces."""
    from tasks.build_goldens import snap_starter
    p = snap_starter()
    ps = [{"id": x.id, "role": x.role, "template_ref": x.template_ref, "is_base": bool(x.is_base)}
          for x in p.pieces if x.provenance != "hardware"]
    return f'answer: {json.dumps({"pieces": ps}, indent=2)}'


def tsl_interface_example() -> str:
    """T-S1 ④: pieces+behaviors → elements + bindings (+ a rationale citing card knowledge)."""
    from tasks.build_goldens import snap_starter
    p = snap_starter()
    els = [{"id": e.id, "card_ref": e.card_ref, "host_pieces": list(e.host_pieces)}
           for e in p.elements]
    bds = [{"element_id": b.element_id, "port": b.port, "piece_id": b.piece_id,
            "anchor": b.anchor, "mate": b.mate} for b in p.bindings]
    attrib = [{"behavior_id": b.id, "realized_by": b.realized_by, "imposed_by": b.imposed_by}
              for b in p.behaviors if b.realized_by or b.imposed_by]
    return ('answer: ' + json.dumps({
        "elements": els, "bindings": bds, "attributions": attrib,
        "rationale": ("snap_hook_cantilever realizes the fastening: its selection_notes say a "
                      "cantilever beam over a catch gives a hand-fastenable click with no added "
                      "parts, cited BASF/Bayer Snap-Fit Design Guide p.5 Fig.1.")}, indent=2))


def assert_no_leakage(prompt: str, forbidden_plan=None) -> None:
    """Fail loudly if a prompt contains the grading key (D-E-1).

    Checks distinctive strings from the forbidden golden — its task_id, its exact command, and its
    element/feature ids paired with their card_refs. Cheap, mechanical, and it turns a silent
    scoring inflation into a crash.
    """
    if forbidden_plan is None:
        from tasks.build_goldens import anchor_easy
        forbidden_plan = anchor_easy("stop")
    hay = prompt.lower()
    tripwires = [forbidden_plan.task_id]
    # the golden's own attributions, e.g. "E1"+"pin_hinge" appearing together as an answer
    for e in list(forbidden_plan.elements) + list(forbidden_plan.features):
        tripwires.append(f'"{e.id}", "card_ref": "{e.card_ref}"')
    hits = [t for t in tripwires if t and t.lower() in hay]
    if hits:
        raise AssertionError(
            f"D-E-1 LEAKAGE: the prompt contains the grading key ({hits}). A stage prompt may carry "
            f"one worked example from a DIFFERENT task only; the Easy golden is never shown.")
