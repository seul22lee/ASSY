# E-track run 2 — scorecard (LLM: qwen3-coder:latest)

## Per-stage agreement with the golden

| axis | matched | missing | spurious | recall | precision | F1 |
|---|---:|---:|---:|---:|---:|---:|
| ① functions (by verb) | 1 | 1 | 1 | 0.50 | 0.50 | **0.50** |
| ② behaviors (by phase+motion.kind) | 4 | 2 | 4 | 0.67 | 0.50 | **0.57** |
| ③ pieces (by template_ref) | 2 | 0 | 0 | 1.00 | 1.00 | **1.00** |
| ③/④ hardware pieces (by role, D-ONT-11) | 1 | 0 | 0 | 1.00 | 1.00 | **1.00** |
| ④ elements (by card_ref) | 2 | 1 | 0 | 0.67 | 1.00 | **0.80** |
| ④ bindings (by card_ref+port+anchor) | 1 | 5 | 4 | 0.17 | 0.20 | **0.18** |

**macro F1: 0.676**

- `① functions (by verb)` — missing: `['allow_access']` · spurious: `['position']`
- `② behaviors (by phase+motion.kind)` — missing: `[('static', 'snap_event'), ('use', 'rotation')]` · spurious: `[('static', 'fixed'), ('use', 'snap_event'), ('assembly', 'rotation'), ('assembly', 'snap_event')]`
- `④ elements (by card_ref)` — missing: `['stop_flange']` · spurious: `[]`
- `④ bindings (by card_ref+port+anchor)` — missing: `[('pin_hinge', 'mount_A', 'rear_wall_outer'), ('snap_hook_cantilever', 'catch_window', 'front_wall_inner'), ('snap_hook_cantilever', 'beam_root', 'front_edge_underside'), ('stop_flange', 'contact', 'stop_flange_face'), ('pin_hinge', 'mount_B', 'rear_edge_underside')]` · spurious: `[('snap_hook_cantilever', 'beam_root', 'rim_underside_right'), ('snap_hook_cantilever', 'catch_window', 'side_wall_right'), ('pin_hinge', 'mount_B', 'side_wall_left'), ('pin_hinge', 'mount_A', 'rim_underside_left')]`

## Physics-implied requirement (scored separately)

| in golden | in LLM IR | LLM has a rotation ceiling | **missed** |
|---|---|---|---|
| True | False | True | **YES** |

> The command never mentions a stop; the golden carries one because PHYSICS showed 'opens>=90 AND returns closed' is unsatisfiable without it (D-M8-5). Not scored as a field mismatch: an IR without it is still valid, and its t2 fold-over is the benchmark's own point (D20).

## Validators on the LLM's IR

- **clean: False** — rules hit: `['V-01']`
  - V-01: use-phase behavior 'B2' has no verified_by
  - V-01: use-phase behavior 'B3' has no verified_by
  - V-01: use-phase behavior 'B8' has no verified_by

## Pipeline survival

- **LLM ①–④**: PASS
- **s5_resolve**: PASS
- **s6_compile**: PASS (3 parts)
- **t0_assembly_rules**: n/a (no AssemblyRules in IR)
- **t2_physics**: {'V-A': '5/5', 'V-B': '0/5'}
- **t2_verdict**: False
