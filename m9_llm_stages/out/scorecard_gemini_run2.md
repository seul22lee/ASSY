# E-track run 2 — scorecard (gemini-3.1-pro-preview)

## Per-stage agreement with the golden

| axis | matched | missing | spurious | recall | precision | F1 |
|---|---:|---:|---:|---:|---:|---:|
| ① functions (by verb) | 2 | 0 | 0 | 1.00 | 1.00 | **1.00** |
| ② behaviors (by phase+motion.kind) | 5 | 1 | 1 | 0.83 | 0.83 | **0.83** |
| ③ pieces (by template_ref) | 2 | 0 | 0 | 1.00 | 1.00 | **1.00** |
| ③/④ hardware pieces (by role, D-ONT-11) | 1 | 0 | 0 | 1.00 | 1.00 | **1.00** |
| ④ elements (by card_ref) | 3 | 0 | 0 | 1.00 | 1.00 | **1.00** |
| ④ bindings (by card_ref+port+anchor) | 6 | 0 | 1 | 1.00 | 0.86 | **0.92** |

**macro F1 — alias-aware: 0.959 · strict: 0.959** (D-E-2; delta +0.000)

- `② behaviors (by phase+motion.kind)` — missing: `[('use', 'rotation')]` · spurious: `[('assembly', 'snap_event')]`
- `④ bindings (by card_ref+port+anchor)` — missing: `[]` · spurious: `[('stop_flange', 'contact', 'rear_wall_outer')]`

## Physics-implied requirement (scored separately)

| in golden | in LLM IR | LLM has a rotation ceiling | **missed** |
|---|---|---|---|
| True | True | False | **no** |

> The command never mentions a stop; the golden carries one because PHYSICS showed 'opens>=90 AND returns closed' is unsatisfiable without it (D-M8-5). Not scored as a field mismatch: an IR without it is still valid, and its t2 fold-over is the benchmark's own point (D20).

## Validators on the LLM's IR

- **clean: True**

## Pipeline survival

- **LLM ①–④**: PASS
- **s5_resolve**: PASS
- **s6_compile**: PASS (3 parts)
- **t0_assembly_rules**: n/a (no AssemblyRules in IR)
- **t2_physics**: {'V-A': '5/5', 'V-B': '4/5'}
- **t2_verdict**: True
