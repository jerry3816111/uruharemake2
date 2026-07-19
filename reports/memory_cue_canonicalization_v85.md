# V85 Memory Cue Canonicalization Regression

- Decision: `inconclusive_effect_between_preregistered_gates`
- Integrity: PASS

| Metric | Legacy cue | Canonical cue |
|---|---:|---:|
| Clean semantic recall | 87.5% | 100.0% |
| Surface pass | 0.0% | 62.5% |
| Transcript-label leak | 100.0% | 0.0% |
| Over max length | 87.5% | 37.5% |
| Median latency | 4.09s | 3.19s |

A pass authorizes only a fresh V86 holdout; the production default remains disabled.

A pass can show that the repair fixes the eight known V84 failures without losing the clean planner contract. It cannot establish generalization or authorize production activation without a fresh holdout.
