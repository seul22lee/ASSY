# Assumptions

Everything this run assumed rather than derived or measured.
Stated explicitly so a reviewer can challenge the inputs, not just the outputs.

## Requirement interpretation

- `AS-001` The box will be used primarily in a desktop environment with typical handling conditions.
- `AS-002` The user will be able to operate the latch with reasonable force and dexterity.

### Unknowns not resolved

- `U-001` specific dimensions of the box — The request only states that it should be desktop-sized (roughly hand-held) but does not specify exact dimensions. (resolved by: user to provide specific size requirements)
- `U-002` exact manufacturing cost constraints — The request states the product should be suitable for low-cost manufacturing but does not specify what constitutes 'low-cost'. (resolved by: user to define acceptable manufacturing cost range)
- `U-003` specific force requirements for operation — The request states that the latch should be easy to operate but does not specify what constitutes 'easy' in terms of force or effort required. (resolved by: user to define acceptable operating force requirements)
- `U-004` specific durability requirements for repeated use — The request states that the box should open and close repeatedly but does not specify how many times or what level of durability is required. (resolved by: user to define number of expected operations or durability requirements)

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

## Implementation maturity

Stage 02 is a strict consumer of the Stage 01 structured contract: it selects
candidate principles from declared transformation signatures and never reads
request prose. It is `provisional` because a candidate set is a proposal,
not a verified commitment. Stages 03-04 remain deterministic placeholders
in `run_manifest.json`. They must not be read as engineering judgement.
