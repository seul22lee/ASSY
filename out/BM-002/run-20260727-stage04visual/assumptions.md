# Assumptions

Everything this run assumed rather than derived or measured.
Stated explicitly so a reviewer can challenge the inputs, not just the outputs.

## Requirement interpretation

- `AS-001` The hand crank rotation will produce sufficient mechanical advantage to lift the specified payload over the required distance — stands in for `U-001`

### Unknowns not resolved

- `U-001` mechanical advantage required for hand crank operation — The request does not specify the required mechanical advantage or transmission ratios needed to achieve the desired lifting capability (resolved by: User should provide information about required torque or transmission ratios)
- `U-002` required housing dimensions — The request does not specify the exact dimensions of the desktop-sized product or housing (resolved by: User should provide specific size requirements)
- `U-003` required transmission mechanism type — The request does not specify what type of transmission mechanism to use (e.g., screw, gear, chain) (resolved by: User should specify preferred transmission type or provide performance requirements)

### Inferred rather than stated

- (none)

## Engineering commitments held as assumptions

- (none)

## Modelling limitations

- the screw drive is lumped into joint friction and a position servo; thread contact, wear, and efficiency are not modelled

## Implementation maturity

Stage 02 is a strict consumer of the Stage 01 structured contract: it selects
candidate principles from declared transformation signatures and never reads
request prose. It is `provisional` because a candidate set is a proposal,
not a verified commitment. Stages 03-04 remain deterministic placeholders
in `run_manifest.json`. They must not be read as engineering judgement.
