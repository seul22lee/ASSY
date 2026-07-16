# Variant sweep smoke test

| Variant | W_in (per hook) | n·W_in (total mate) | ≤ 80 N | W_out | verdict |
|---|---:|---:|:--:|---|---|
| T-S1a (n=2) | 17.82 N | 35.63 N | ✓ | 31.84 N | FEASIBLE |
| T-S1c (n=4) | 17.82 N | 71.26 N | ✓ | 31.84 N | FEASIBLE |
| T-S1d (α_out=90, permanent) | 17.82 N | 35.63 N | ✓ | permanent (self-locking) | FEASIBLE |

- **T-S1c (n=4)**: the per-hook force is unchanged, but the total-mating-force constraint `n·W_in ≤ 80 N` is TIGHTER (71.3 N vs 35.6 N for n=2) — the effect SNAPFIT §0 calls out. With 4 hooks the design sits closer to the ceiling.
- **T-S1d (α_out=90°)**: α_out ≥ self-lock ⇒ the joint is classified **permanent (self-locking)** — `W_sep` reports the classification, NOT a bogus finite force, and the hand-open ceiling + self-lock cap are waived (permanent is intentional here).
