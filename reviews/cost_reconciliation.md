# Gemini spend reconciliation (log arithmetic — no API calls)

**Reconstructed 2026-07-18 from on-disk logs.** Goal: explain the dashboard's ~$15 vs the ~$3–4.5
all-Pro *upper bound* I quoted for m15.

## 1. Per-session token counts × published prices

Only `gemini-*` calls bill (ollama/qwen is local/free). Pre-fix logs (m9) recorded **output tokens
only** — the token-instrumentation fix (D-M16-2) landed after them — so their **prompt tokens are
RECONSTRUCTED from the stored prompt text (chars/4)**; post-fix logs carry the API's real
usageMetadata. Prices are published Gemini rates, **approximate** (gemini-3.x-preview pricing is
unconfirmed → shown as a low/high bracket).

| session | model | calls | prompt tok | output tok | note |
|---|---|---:|---:|---:|---|
| m9 run1 (E-track) | gemini-3.1-pro-preview | 5 | 3,289* | 427 | *prompt reconstructed (pre-fix) |
| m9 run2 (E-track) | gemini-3.1-pro-preview | 6 | 6,999* | 2,356 | *prompt reconstructed (pre-fix) |
| m9 run3 (E-track) | gemini-3.1-pro-preview | 7 | 9,496* | 3,022 | *prompt reconstructed (pre-fix) |
| m15 gate — flash | gemini-3.5-flash | 6 | 8,012 | 2,343 | real usageMetadata |
| m15 gate — pro | gemini-3.1-pro-preview | 5 | 4,949 | 1,083 | real usageMetadata |
| m15 naive pilot | gemini-3.x | 1 | ~1,146 total | (split n/a) | cell-level only |
| **TOTAL LOGGED** | | **29** | **32,745** | **9,231** | **41,976 tok total** |

**Cost of all logged Gemini usage: `$0.12` (low rates) … `$0.32` (high/premium rates).**

Sanity check: if the full $15 came from our 41,976 logged tokens, that implies **$357 per million
tokens** — no Gemini model is priced within ~25× of that. So the logged calls are not the source.

## 2. Code paths that can BILL without landing in a stage_log

| path | bills? | max plausible $ | reasoning |
|---|---|---|---|
| **Killed / timed-out processes** (flash-vs-pro attempt #1's ~25-min wedge; the nohup bulk that died; the two aborted bulk relaunches) | maybe | **< $0.50 total** | stage_log is flushed at the END of a tier/run; a process killed mid-run bills any completed call but writes no file. But each died with ~0–few completed calls (14s CPU over 25 min = wedged, not working). At most ~one gate-run of tokens each. |
| **Retries on HTTP 429 before the fail-fast fix** | **no** | **$0** | a 429 is a *rejection* — the request is refused, Google does not bill it. My old backoff re-sent the prompt up to 6×, but every attempt was a 429. |
| **Deleted cells** (429-poisoned flash cells I `rm`'d; the A-cell gen call) | tiny | **< $0.02** | the D-cells were 429s (no bill); one rung-A `gen_code` flash call may have billed a few hundred tokens. |
| **Overwritten dev-loop runs** (E-track saves only the last 3; earlier `--frontier` runs this month are gone from disk) | maybe | **unknowable, but bounded** | this is the ONLY category that could be non-trivial. Each E-track gemini run ≈ $0.07–0.10; reaching $15 needs ~150–200 such runs. The dev loop **defaults to local qwen** (D-E-9); gemini is opt-in via `--frontier`, so a large hidden count is unlikely — but I cannot prove it from deleted logs. |
| Model-list / reachability probes | **no** | $0 | metadata endpoint, unbilled. |
| CoACD / MuJoCo / build123d / local qwen | **no** | $0 | all local. |

**Maximum plausible unlogged MechSynth billing: ~$0.5–3** (dominated entirely by the hypothetical
overwritten dev runs, which default to qwen anyway).

## 3. The gap

| | amount |
|---|---|
| Reconstructed logged spend | **$0.12 – $0.32** |
| + max plausible unlogged (§2) | **+ up to ~$3** |
| **Our-side total (generous ceiling)** | **≤ ~$3.3** |
| Dashboard (user-reported) | **~$15.00** |
| **UNACCOUNTED GAP** | **~$11.7 – $14.9  (≈ 80–99% of the bill)** |

**The gap is not explained by any logged or reconstructable MechSynth call.** MechSynth's entire
Gemini footprint on disk is ~42k tokens ≈ **$0.3**, and even the most generous accounting for
killed processes and deleted dev runs cannot exceed a few dollars. The dominant share of the $15 is
billing our logs never saw.

Leading candidates for the gap, to confirm against the dashboard:
1. **Shared billing / key on a multi-user server.** This host runs other users' workloads (jupyter
   kernels under a different UID were live during the run). If the Gemini API key or the Google Cloud
   billing project is shared, *their* Generative Language API usage bills the same cap.
2. **Prior-month or non-MechSynth usage** on the same project/key, unrelated to this session.
3. **A dashboard-metric mismatch** — "$15" may be the **cap you set** (the ceiling), an
   **account-wide** total across all Google Cloud services, or a **cumulative** (not
   today/this-project) figure, rather than this project's actual generation spend.

**What localizes it (please provide):** the dashboard's **per-day totals** and, if available, the
**per-API / per-project breakdown**. If the $15 accrued on days *before* 2026-07-18, it cannot be m15
or today's work. A day-by-day view will immediately show whether today's activity even registers
against it — our logs predict today added **≤ ~$0.05** (the gate: 11 calls, ~14k tokens).

**Recommendation:** keep the frontier column on HOLD (no cap raise) until the per-day breakdown
names where the $15 actually accrued. Our instrumentation is now correct going forward (every call
logs real prompt+output tokens with a self-check), so from here on the logs and the dashboard should
track — any divergence *after* today points at a shared-key/other-user source, not MechSynth.
