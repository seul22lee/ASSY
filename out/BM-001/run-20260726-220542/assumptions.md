# Assumptions

Everything this run assumed rather than derived or measured.
Stated explicitly so a reviewer can challenge the inputs, not just the outputs.

## Requirement interpretation

- `AS-001` single user, manual actuation — stands in for `U-001`

### Unknowns not resolved

- `U-001` acceptable input effort — no effort or force target appears in the request (resolved by: a stated maximum operating force or torque)

### Inferred rather than stated

- (none)

## Engineering commitments held as assumptions

- (none)

## Modelling limitations

- MuJoCo is rigid-body: the snap beam is a lumped torsional spring (k = 3EI/L = 0.7560 N.m/rad), not a flexing beam
- contact timing, engagement sequence, and gross retention are represented; strain, stress, creep, and fatigue are NOT, and come from the analytical backend
- beam armature 2.0e-06 kg.m2 is added for numerical integrability and exceeds the physical beam inertia; beam natural frequency is therefore not physical
- the hook/lip pair is an idealised rigid engagement; real face friction and edge rounding will shift the measured contact forces
- the lid plate is on a separate contact group so it does not rest on the walls; lid/wall interference is not evaluated by this model
- compliant retention requires BOTH backends: neither rigid-body contact nor closed-form beam analysis is sufficient alone

## Implementation maturity

Stages 01-04 are deterministic placeholders standing in for LLM reasoning.
Their outputs are structurally valid but shallow, and are marked `placeholder`
in `run_manifest.json`. They must not be read as engineering judgement.
