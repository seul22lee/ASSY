# ASSUMPTION Register

Assumptions baked into the code that are **not** yet backed by primary data. Per SNAPFIT_STARTER
§7 and the m3-cards G-H ruling, these **ship with the paper as declared limitations** until
their gate is discharged. This register is permanent: a row leaves it only when its gate closes
(with a citation), never by being quietly dropped.

Each row: what is assumed · where it lives in code · the gate that would retire it · citation.

| ID | Gate | Assumption | Where (code) | What retires it |
|----|------|-----------|--------------|-----------------|
| A-PETG-1 | **G-S4** | **PETG material constants are stand-ins — PETG appears nowhere in the Bayer PDF's tables/curves.** `Es_petg ≈ 0.75·E` (Fig.16 carries Bayer PC resins only); `EPS_PERM_PETG = 0.04` (borrowed from PC's Table 2 4%, *not* computed from PETG yield strain; p.11 says amorphous ≈70% of yield); `MU_PETG = 0.35` (Table 3 has no PETG; extrapolated from PC 0.45–0.55). | `knowledge/cards/snap_hook_cantilever.py` (`Es_secant`, `EPS_PERM_PETG`, `MU_PETG`) | A PETG datasheet (or Fig.16-equivalent secant curve, yield strain, and a measured PETG-on-PETG μ). **Until then this row ships with the paper as a declared limitation.** The Bayer golden (G-S1) is *independent* of this row — it uses PC values directly — so the formulas are validated even while these constants are not. |

> **Note on scope.** A-PETG-1 affects only *material inputs*, never the *formulas*. The formulas
> are anchored by Calc Example I (PC) to <0.2% (`tests/test_golden_bayer.py`). When A-PETG-1 is
> discharged, re-run the snap task's dimensioning; the golden does not change.

_Cross-ref: `DECISIONS_LOG.md` D-BAYER-1 (CONFIRMED). SNAPFIT_STARTER §2.3, §7._
