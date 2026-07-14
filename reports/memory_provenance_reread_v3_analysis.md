# Memory provenance and adaptive reread V3 analysis

## Decision

**Reject V3 runtime integration.** The experiment preserves useful negative evidence instead of promoting a feature merely because one aggregate score rose.

## Condition results

| Condition | Answerable | Unanswerable abstention | Overall | Mean latency | Mean prompt tokens |
|---|---:|---:|---:|---:|---:|
| A: full-session freeform | 31/36 (86.11%) | 0/12 (0.00%) | 31/48 (64.58%) | 14.864s | 1575.4 |
| P: provenance gate | 31/36 (86.11%) | 12/12 (100.00%) | 43/48 (89.58%) | 12.170s | 1470.3 |
| R: provenance + adaptive reread | 31/36 (86.11%) | 12/12 (100.00%) | 43/48 (89.58%) | 14.584s | 1785.6 |
| S: adaptive reread + span contract | 27/36 (75.00%) | 12/12 (100.00%) | 39/48 (81.25%) | 15.675s | 1758.6 |

## What actually caused the score changes

- P beat A on `12` cases: `12` unanswerable and `0` answerable.
- A and P had the same answerable failures. P therefore improved explicit uncertainty handling, not memory reasoning.
- Every condition admitted zero assistant events, so V3 did not observe assistant-source contamination.
- R triggered `15` second reads and recovered `0`. Relative to P it added `2.414s` mean latency and `315.3` mean prompt tokens; evidence recall rose by `4.17 pp` without changing answer accuracy.
- S fixed `2` cases but regressed `6` cases.

## Localized failures

| Failure | Cases | Root cause |
|---|---:|---|
| Mug current count | 3 | Both full and highlighted extraction missed grounded user evidence; reread could not recover it. |
| Pre-harp violin polarity | 3 | The binder treated a source sentence's corrective `No` as the answer's polarity. |
| Takeout frequency relation | 3 | The deterministic scalar reader did not resolve `twice`. |

## Evidence boundary

- Source monitoring is a relevant human-memory function, but this experiment found no assistant-fact contamination to remove.
- A provenance sufficiency gate improved calibrated uncertainty only: answerable accuracy stayed 31/36 while unanswerable abstention rose from 0/12 to 12/12.
- Adaptive highlighted rereading raised evidence recall from 68.75% to 72.92%, but this produced no answer recovery in the frozen V3 cases.
- The current span contract confuses discourse correction with answer polarity and cannot resolve frequency words such as twice.

## Next experiment constraints

- Do not modify runtime from V3; both preregistered promotion gates failed.
- Treat all V3 scenarios as consumed development evidence.
- Evaluate explicit abstention separately on new untouched cases; do not attribute its gain to source filtering.
- Test a deterministic query-aligned user-turn candidate path against the mug extraction blind spot before attempting another model reread.
- If span binding is revisited, preregister discourse-marker-aware polarity and frequency-word normalization on new cases.

## Audit

- Source report SHA-256: `0d709949ca490c3110970911932d6c716cb39ef6e0c2d96a138869993d122e31`.
- Source results SHA-256: `703e7b2efd20ae7877ec7b464efcc8b533e1a681b9f79c8d67a54045af4ff12d`.
- Metric recomputation made `0` model calls and changed no dataset, prompt, or response.
- Failed promotion gates: `adaptive_answerable_false_abstention_rate_equals_zero, span_overall_cognitive_pass_not_lower_than_adaptive`.
