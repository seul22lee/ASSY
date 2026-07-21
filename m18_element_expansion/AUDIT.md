# M18 Tier-1 element audit — coverage matrix

AUDIT-ONLY (surface gaps, do not fix). PASS / WEAK / MISSING / **FALSE** per cell.

## Layer 0 — physics verification  ·  Layer 1 — per-card integrity

| element | phys required | protocol runs | passes | measured vs criterion | emergent honest | resolve params | formula anchored | carve one solid | taxonomy 7axes |
|---|---|---|---|---|---|---|---|---|---|
| `lead_screw` | PASS | MISSING | MISSING | MISSING | WEAK | WEAK | PASS | PASS | PASS |
| `coupling` | PASS | MISSING | MISSING | MISSING | **FALSE** | PASS | PASS | PASS | PASS |
| `universal_joint` | PASS | MISSING | MISSING | MISSING | **FALSE** | WEAK | PASS | PASS | PASS |
| `journal_bearing` | PASS | MISSING | MISSING | MISSING | WEAK | PASS | WEAK | PASS | PASS |
| `bushing` | n/a | n/a | n/a | n/a | PASS | PASS | WEAK | PASS | PASS |
| `dowel_pin` | n/a | n/a | n/a | n/a | PASS | PASS | WEAK | PASS | PASS |
| `screw_boss` | n/a | n/a | n/a | n/a | PASS | PASS | PASS | PASS | PASS |
| `press_fit` | n/a | n/a | n/a | n/a | PASS | PASS | PASS | PASS | PASS |

## Non-PASS reasons (element × check)

- `lead_screw` · **MISSING** protocol_runs: protocol DECLARED but NO harness in verify/ runs it (no card-specific rig; the P-HINGE runner is hinge-only)
- `lead_screw` · **MISSING** passes: no physics executed
- `lead_screw` · **MISSING** measured_vs_criterion: no measured number — physics never ran
- `lead_screw` · **WEAK** emergent_honest: deferred reason is a real tool limit (curved contact, R2b) — HONEST for V-B; but the declared-pair V-A (stroke/self-lock) also never runs, so even the non-curved check is unbuilt (the risk it names is itself unverified)
- `lead_screw` · **WEAK** resolve_params: out-of-bound [] / none ['starts']
- `coupling` · **MISSING** protocol_runs: protocol DECLARED but NO harness in verify/ runs it (no card-specific rig; the P-HINGE runner is hinge-only)
- `coupling` · **MISSING** passes: no physics executed
- `coupling` · **MISSING** measured_vs_criterion: no measured number — physics never ran
- `coupling` · **FALSE** emergent_honest: FALSE 'verified' tag — no V-A/V-B actually runs for this element; 'verified' claims an emergent safety net that does not exist yet
- `universal_joint` · **MISSING** protocol_runs: protocol DECLARED but NO harness in verify/ runs it (no card-specific rig; the P-HINGE runner is hinge-only)
- `universal_joint` · **MISSING** passes: no physics executed
- `universal_joint` · **MISSING** measured_vs_criterion: no measured number — physics never ran
- `universal_joint` · **FALSE** emergent_honest: FALSE 'verified' tag — no V-A/V-B actually runs for this element; 'verified' claims an emergent safety net that does not exist yet
- `universal_joint` · **WEAK** resolve_params: out-of-bound [] / none ['yoke_d']
- `journal_bearing` · **MISSING** protocol_runs: protocol DECLARED but NO harness in verify/ runs it (no card-specific rig; the P-HINGE runner is hinge-only)
- `journal_bearing` · **MISSING** passes: no physics executed
- `journal_bearing` · **MISSING** measured_vs_criterion: no measured number — physics never ran
- `journal_bearing` · **WEAK** emergent_honest: a rotational SUPPORT tagged not_applicable — defensible (realizes no DoF) but its low-friction support behaviour under load is unverified; a V-A drag test would close it
- `journal_bearing` · **WEAK** formula_anchored: clearance=max(d/1000, print_clearance) is a RULE OF THUMB (Shigley §12), not a worked textbook golden — WEAKLY anchored
- `bushing` · **WEAK** formula_anchored: clearance=max(d/1000, print_clearance) is a RULE OF THUMB (Shigley §12), not a worked textbook golden — WEAKLY anchored
- `dowel_pin` · **WEAK** formula_anchored: no numeric golden — 'bore = pin_d + fit_clearance' is a fit rule, not a derived formula (unanchored)

## Layers 2–4 — ontology · KG · regression

| layer | check | verdict | note |
|---|---|---|---|
| ontology | V-08 rejects connection realized_by | PASS |  |
| ontology | V-17 rejects compliant (P-SPRING msg) | PASS |  |
| ontology | connection_principle(property) != ConnectionCard(class) | PASS |  |
| ontology | screw_boss provides screw as hardware (provenance+params) | PASS |  |
| kg | rot_to_trans + self_locking -> ['lead_screw'] | PASS |  |
| kg | rot_to_trans (no self_lock) -> ['rack_pinion', 'lead_screw'] | PASS |  |
| kg | locate two parts (fixed+form) -> ['dowel_pin'] | PASS |  |
| kg | intersecting-axis rotation -> ['universal_joint'] | PASS |  |
| kg | rotational support -> ['pin_hinge', 'stop_flange', 'coupling', 'universal_joint', 'journal_bearing', 'bushing'] | PASS |  |
| regression | suite: test_roundtrip.py | **FALSE** | 3/4 passed |
| regression | full test suite (14/15 files) | **FALSE** |  |
| regression | goldens validate_all clean (17/17) | PASS |  |
| regression | append-only (no moved/renamed) | PASS |  |

## Summary

**46 PASS · 7 WEAK · 12 MISSING · 4 FALSE** (n/a: 16).

## Ordered gaps to fix before Tier-2

1. **[TOP]** FUNCTIONAL elements with NO physics verification (declared protocol, no runner/rig): coupling, journal_bearing, universal_joint, lead_screw. This is where an m8-stop / m13-brake class emergent surprise could hide — the whole point of the framework.
2. **[TOP]** FALSE emergent_check='verified' tags (claims a safety net that never runs): coupling, universal_joint. Either build the V-A rig or retag to deferred/not-built.
3. **[HIGH]** emergent_check WEAK: lead_screw, journal_bearing — deferred elements whose declared-pair V-A also never runs, and supports tagged not_applicable whose low-friction behaviour is unverified.
4. **[MED]** formulas WEAKLY anchored (rule-of-thumb / no textbook golden): journal_bearing, bushing, dowel_pin — add a worked numeric anchor like Bayer's for snaps.
5. **[HIGH]** REGRESSION — full test suite (14/15 files): a previously-green test is now red. test_roundtrip::test_disk_json_is_canonical fails because the on-disk golden JSONs predate the m18 schema fields (nature/axis_relationship/self_locking) — they validate_all CLEAN but their committed serialization is stale (re-dump needed). NOTE: the m18 'all green' claim missed this — a `grep passed` tally matched '3/4 passed'; this audit's returncode check caught it.
6. **[MED]** carve produces a single STANDALONE primitive per element (a cylinder/tube), with NO mating bore or host integration — so press_fit's designed interference overlap, and the dowel/boss fits, cannot be geometrically verified against a mate (t0 interference has nothing to check). Assembly-level geometry is unbuilt.