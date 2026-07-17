# E-track run 1 — scorecard (qwen3-coder:latest)

## Per-stage agreement with the golden

| axis | matched | missing | spurious | recall | precision | F1 |
|---|---:|---:|---:|---:|---:|---:|
| ① functions (by verb) | 2 | 0 | 0 | 1.00 | 1.00 | **1.00** |
| ② behaviors (by phase+motion.kind) | 4 | 2 | 4 | 0.67 | 0.50 | **0.57** |
| ③ pieces (by template_ref) | 2 | 0 | 0 | 1.00 | 1.00 | **1.00** |
| ③/④ hardware pieces (by role, D-ONT-11) | 1 | 0 | 0 | 1.00 | 1.00 | **1.00** |
| ④ elements (by card_ref) | 2 | 1 | 0 | 0.67 | 1.00 | **0.80** |
| ④ bindings (by card_ref+port+anchor) | 1 | 5 | 4 | 0.17 | 0.20 | **0.18** |

**macro F1 — alias-aware: 0.759 · strict: 0.676** (D-E-2; delta +0.083)

- `① functions (by verb)` — matched via DECLARED ALIAS (D-E-2): ['allow_access ~ position']
- `② behaviors (by phase+motion.kind)` — missing: `[('use', 'rotation'), ('static', 'snap_event')]` · spurious: `[('assembly', 'rotation'), ('use', 'snap_event'), ('static', 'fixed'), ('assembly', 'snap_event')]`
- `④ elements (by card_ref)` — missing: `['stop_flange']` · spurious: `[]`
- `④ bindings (by card_ref+port+anchor)` — missing: `[('pin_hinge', 'mount_A', 'rear_wall_outer'), ('pin_hinge', 'mount_B', 'rear_edge_underside'), ('snap_hook_cantilever', 'beam_root', 'front_edge_underside'), ('snap_hook_cantilever', 'catch_window', 'front_wall_inner'), ('stop_flange', 'contact', 'stop_flange_face')]` · spurious: `[('pin_hinge', 'mount_A', 'rim_underside_left'), ('pin_hinge', 'mount_B', 'side_wall_left'), ('snap_hook_cantilever', 'beam_root', 'rim_underside_right'), ('snap_hook_cantilever', 'catch_window', 'side_wall_right')]`

## Physics-implied requirement (scored separately)

| in golden | in LLM IR | LLM has a rotation ceiling | **missed** |
|---|---|---|---|
| True | False | True | **YES** |

> The command never mentions a stop; the golden carries one because PHYSICS showed 'opens>=90 AND returns closed' is unsatisfiable without it (D-M8-5). Not scored as a field mismatch: an IR without it is still valid, and its t2 fold-over is the benchmark's own point (D20).

## Validators on the LLM's IR

- **clean: True**

## Pipeline survival

- **LLM ①–④**: PASS
- **s5_resolve**: PASS
- **s6_compile**: PASS (3 parts)
- **t0_assembly_rules**: n/a (no AssemblyRules in IR)
- **t2_physics**: {'V-A': '5/5', 'V-B': '0/5'}
- **t2_verdict**: False
