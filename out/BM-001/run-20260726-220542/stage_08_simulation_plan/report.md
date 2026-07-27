# Stage 08 - Simulation Plan

> How should the design be physically tested?

- **status**: ok
- **produces**: `SimulationPlan`
- **object id**: `SIMPLAN-001`
- **authority**: `authoritative`

## Summary

5 tests

## Modelling limitations

- MuJoCo is rigid-body: the snap beam is a lumped torsional spring (k = 3EI/L = 0.7560 N.m/rad), not a flexing beam
- contact timing, engagement sequence, and gross retention are represented; strain, stress, creep, and fatigue are NOT, and come from the analytical backend
- beam armature 2.0e-06 kg.m2 is added for numerical integrability and exceeds the physical beam inertia; beam natural frequency is therefore not physical
- the hook/lip pair is an idealised rigid engagement; real face friction and edge rounding will shift the measured contact forces
- the lid plate is on a separate contact group so it does not rest on the walls; lid/wall interference is not evaluated by this model
- compliant retention requires BOTH backends: neither rigid-body contact nor closed-form beam analysis is sufficient alone
