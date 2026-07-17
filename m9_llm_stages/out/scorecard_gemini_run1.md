# E-track run 1 — scorecard (gemini-3.1-pro-preview)

## Per-stage agreement with the golden

| axis | matched | missing | spurious | recall | precision | F1 |
|---|---:|---:|---:|---:|---:|---:|
| ① functions (by verb) | 2 | 0 | 0 | 1.00 | 1.00 | **1.00** |
| ② behaviors (by phase+motion.kind) | 0 | 6 | 0 | 0.00 | 1.00 | **0.00** |
| ③ pieces (by template_ref) | 0 | 2 | 0 | 0.00 | 1.00 | **0.00** |
| ③/④ hardware pieces (by role, D-ONT-11) | 0 | 1 | 0 | 0.00 | 1.00 | **0.00** |
| ④ elements (by card_ref) | 0 | 3 | 0 | 0.00 | 1.00 | **0.00** |
| ④ bindings (by card_ref+port+anchor) | 0 | 6 | 0 | 0.00 | 1.00 | **0.00** |

**macro F1 — alias-aware: 0.167 · strict: 0.167** (D-E-2; delta +0.000)

- `② behaviors (by phase+motion.kind)` — missing: `[('use', 'rotation'), ('use', 'rotation'), ('assembly', 'translation'), ('assembly', 'translation'), ('static', 'snap_event'), ('use', 'fixed')]` · spurious: `[]`
- `③ pieces (by template_ref)` — missing: `['box_shell', 'lid_panel']` · spurious: `[]`
- `③/④ hardware pieces (by role, D-ONT-11)` — missing: `['pin']` · spurious: `[]`
- `④ elements (by card_ref)` — missing: `['pin_hinge', 'snap_hook_cantilever', 'stop_flange']` · spurious: `[]`
- `④ bindings (by card_ref+port+anchor)` — missing: `[('pin_hinge', 'axis', 'rear_top_edge'), ('pin_hinge', 'mount_A', 'rear_wall_outer'), ('pin_hinge', 'mount_B', 'rear_edge_underside'), ('snap_hook_cantilever', 'beam_root', 'front_edge_underside'), ('snap_hook_cantilever', 'catch_window', 'front_wall_inner'), ('stop_flange', 'contact', 'stop_flange_face')]` · spurious: `[]`

## Physics-implied requirement (scored separately)

| in golden | in LLM IR | LLM has a rotation ceiling | **missed** |
|---|---|---|---|
| True | False | False | **YES** |

> The command never mentions a stop; the golden carries one because PHYSICS showed 'opens>=90 AND returns closed' is unsatisfiable without it (D-M8-5). Not scored as a field mismatch: an IR without it is still valid, and its t2 fold-over is the benchmark's own point (D20).

## Validators on the LLM's IR

- **clean: True**

## Pipeline survival

- **LLM ①–④**: FAIL — {'s1': 'PASS', 's2': 'FAIL(G2)'}
