# T3-ARCH · angled_screw_lift — archetype brief

_Committed BEFORE geometry (spec §14 T3-ARCH, D-M24-4). An INCREMENT on the screw_lift jack archetype._

## Archetype
**"Angled-drive screw jack"** — the screw_lift jack, but the input crank axis TILTS **β = 30°** from the
vertical screw axis (the side space is blocked), the two axes joined by a **universal joint** (Cardan) at
their intersection. Same base frame + guide columns + top-stop collars + platform/nut boss; the coupling
hub is REPLACED by the u-joint.

**Source / citation:** the screw_lift jack (m22/m24, D-M24-2) + the Cardan universal joint across
intersecting axes at β (Pahl & Beitz §8.1, Hooke; the m21 universal_joint card, D-M21-1). Task-track
composition of two VERIFIED elements — universal_joint (m21) + lead_screw (m19); no new element.

## Why the angle (the command constraint → axis-2)
The command says *"the crank must come out at a 30° angle"* — a CONSTRAINT on the input axis, not a change
of function (still "lift + hold"). It reads onto the m18 **axis-2 (axis_relationship)**: intersecting, not
parallel — which is exactly what selects the universal_joint over the coupling. This is the Phase-2 seed
where the CONSTRAINT, not the function, discriminates the element choice.

## Pieces & roles
- **P1 cabinet/base** (base): the screw_lift base frame + guide columns + top-stop collars + the screw
  (fused, lead_screw carve), REUSED. Plus a NEW **angled bearing boss** carrying the input crank shaft at
  β=30° — the input hinge's physical carrier (T3c).
- **P2 platform/nut**: the screw_lift nut carriage (nut boss + column bores), REUSED.
- **P3 crank**: the input hand crank, its shaft on the β=30° axis, carrying the u-joint INPUT yoke.
- **cross/spider** (u-joint): the rigid cross with two orthogonal trunnions; the OUTPUT yoke is on the
  screw top. (Whether the cross is its own piece or carved onto the yokes is a T3 decision — see the fit
  chain.)

## Mating-face map (the interfaces the fit chain dimensions)
| # | face A | face B | relation | class | source |
|---|---|---|---|---|---|
| M1 | crank shaft ⌀ | angled bearing-boss bore | **input hinge** (pin-in-bore) | declared hinge | pin_hinge-class clearance; boss bore = shaft⌀ + fit |
| M2 | input-yoke bores | cross trunnions | **cross bearing** (pin-in-bore) | ① / declared | m21 card pin-in-bore rows; yoke bore = trunnion⌀ + fit |
| M3 | output-yoke bores | cross trunnions | **cross bearing** (pin-in-bore) | ① / declared | m21 card pin-in-bore rows |
| M4 | output yoke | screw top | rigid (yoke fused to screw) | — | D-D-1 one-solid (yoke on shaft, m21 carve) |
| M5 | screw major ⌀ | nut bore | thread (self-lock) | ① R2b | inherited screw_lift (m19) |
| M6 | guide column ⌀ | platform bore | **ride** (slide DoF) | ② dof | inherited screw_lift (0.35 A-PETG-1) |
| M7 | platform | TOP collar | **top stop** (thread runout) | ② limit | inherited (m24/m25 contact layer) |
| M8 | platform | base | **bottom landing** (s=0) | ② limit | inherited (m24/m25 contact layer) |

**Cross-center = a DERIVED placement, not a free choice:** the u-joint lives where the two axis LINES
INTERSECT — the crank axis (β=30° through the boss) and the screw axis (+Z) meet at one point; that point
is the cross center (a fit-chain row).

## Honest idealizations (named, T3c)
- The **angled bearing boss** now carries the input hinge as a DESIGNED part (the m21 rig's world-connect
  idealization gets a physical carrier). The boss BORE is still a **declared hinge** (a frictionless
  revolute) — `journal_bearing` remains PARKED (D-M20-0); the boss is its host geometry, not its physics.
- The **cross-trunnion bearing** (M2/M3) is pin-in-bore (pin_hinge class); its emergent contact stays
  V-B deferred (m21 emergent_check, R2b) — the DECLARED-pair Cardan kinematics (incl. the fluctuation) IS
  physics-verified.

## Section sketch — engaged, β=30° (XZ plane; +Z up, screw axis)

```
            crank (β=30°, comes out to +X-up)
              \\  M1 angled bearing boss (input hinge carrier)
               \\ []___
      input yoke \\[cross]  ← M2/M3 the u-joint at the AXIS INTERSECTION (cross center, derived)
                  [====]    ← M4 output yoke fused to the screw top
       ┌────────┐  ||  ┌────────┐
       │ column │  ||  │ column │   guide columns (M6 ride) + TOP collars (M7 stop)
       │        │  ||S │        │
       │      ┌─┴──╫╫──┴─┐       │   platform / nut (M6 bores, M5 thread on the screw S)
       │      │  nut boss │      │
       └──────┴────╫╫────┴───────┘   M8 bottom landing on the base
       ════════════════════════════  base frame  (P1)
```

- The crank enters at 30°; the u-joint turns the corner at the axis intersection; the screw (vertical)
  drives the platform up/down on the guide columns; the platform holds by the screw's self-lock (M5).

## What T3 must derive (fit chain, additions to the screw_lift rows)
angled boss bore = crank shaft ⌀ + pin-hinge fit; yoke bores = trunnion ⌀ + fit (m21 pin-in-bore); the
cross-center coordinates from the two axis-lines' intersection; the yoke reach so the cross clears BOTH
shafts at β=30° AND β=0 (the m21 addendum clearance lesson). Everything else inherits the screw_lift
fit chain. See the fit schedule.
