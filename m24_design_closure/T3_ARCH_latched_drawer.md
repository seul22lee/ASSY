# T3-ARCH · latched_drawer (pull-snap) — archetype brief

_Committed BEFORE geometry (spec §14 T3-ARCH, D-M24-4). The configuration is stated + cited here, not
derived — the card library has no embodiment knowledge yet._

## Archetype
**"Bottom-clip organizer drawer"** — a desktop parts-drawer that slides on a centre rail and is held
shut by a cantilever clip snapping over a floor bump, entirely hidden under the tray. Pull to release.

**Source / citation:** the bottom-mounted centre-rail organizer drawer is a standard injection-moulded
housing form (Pahl & Beitz §6–7 embodiment; the "catch bump + moulded clip" retention is the Bayer
Snap-Fit Design Guide cantilever archetype, p.5 Fig.1, applied to a translation path). Not from a card —
supplied per T3-ARCH as the reviewer-approved configuration.

## Zero-protrusion rule
The **entire latch lives in the gap between the drawer-tray underside and the cabinet floor** — no hook
on a wall, no receiver ledge in the opening. The face is clean; the front panel's bottom edge is the pull
lip.

## Pieces & roles
- **P1 cabinet** (base): floor + two side walls + back wall + a **face frame** around the front opening
  + ONE **T-rail** centred on the floor (running front↔back) + a **double-ramped catch bump** on the
  floor near the front.
- **P2 drawer**: tray + an **oversized front panel** (4 mm proud each side, covers the opening) + a
  **groove** under the tray floor riding the rail + a downward cantilever **clip** (beam + barb) under
  the floor near the front, offset laterally from the groove.

## Mating-face map (the interfaces the fit schedule dimensions)
| # | drawer face | cabinet face | relation | at closed | while riding |
|---|---|---|---|---|---|
| M1 | front-panel back face | face-frame front face | **LANDING** (closed hard stop) | contact, gap 0 | — |
| M2 | tray under-groove | centre T-rail | **RIDE** (slide DoF) | seated | 0.35 mm slide clearance |
| M3 | clip barb | floor catch bump | **CATCH** (retention) | barb behind bump, +undercut overlap | 0.35 mm clearance |
| M4 | tray side walls | cabinet opening | **FIT** | 1.0 mm side gap | 1.0 mm |
| M5 | (rail end) | (travel) | **STROKE LIMIT** | — | finite rail |

## Section sketch — closed state (XZ, looking along +Y; +X = pull-out / front)

```
        front (pull) ->                                    back
   ┌──────┐                                             ┌─────┐
   │ front│░ face frame                                 │ back│   ← cabinet side/back walls
   │ panel│░┌─────────────────────────────────────────┐│ wall│
   │  (4mm│░│  drawer tray  (rides the rail)            ││     │
   │ proud│░│                                           ││     │
   │  lip)│░│   ┌clip┐                                  ││     │
   └──────┘░└───│beam│──────────────────────────────────┘│     │
     M1 ▲   M4  │barb│v                                    │     │
   landing      └─┐┌─┘   ┌──T-rail──────────────────────┐ │     │
   ═══════════════██═════╪══════════════════════════════╪═╪═════╪══  cabinet floor
                  ▲bump   └ groove rides here (M2) ┘      │     │
                 M3 catch: barb snapped BEHIND the bump
```

- **M1** the front panel lands flat on the face frame (gap 0) — the closed stop is a PART, not the drive.
- **M3** the clip barb has ridden up the bump's near ramp and dropped behind it; pulling out (+X) it must
  climb back over → the sourced separation force W_out.
- Everything M2/M3 is in the tray-underside ↔ floor gap (zero protrusion).

## What T3 must now derive (fit chain, three free inputs W_i=60 / D=60 / H=25)
tray/opening/cabinet widths from wall + clearance; groove from rail; **clip L·b·undercut by inverse
Bayer to W_out ≈ 30 N** (h_root, P, W_in ≤ 20 by formula); **bump height = undercut + 0.35**; bump x from
the barb-at-closed position; front-panel-to-face gap = 0; stroke from D. Every number cites its mate or
formula — see the fit schedule.
