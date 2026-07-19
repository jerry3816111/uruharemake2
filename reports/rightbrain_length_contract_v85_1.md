# V85.1 Explicit Length Contract Regression

- Decision: `authorize_fresh_v86_holdout_only`
- Integrity: PASS

| Metric | Implicit length | Explicit length |
|---|---:|---:|
| Clean semantic recall | 100.0% | 100.0% |
| Surface pass | 62.5% | 100.0% |
| Over max length | 37.5% | 0.0% |
| Mean overage | 1.75 chars | 0.00 chars |
| Transcript-label leak | 0.0% | 0.0% |
| Median latency | 3.21s | 3.92s |

A pass authorizes only a fresh V86 holdout; the production default remains disabled.

A pass can show that the explicit length contract repairs the eight known V85 regression cases. It cannot establish generalization or authorize production activation without a fresh disjoint holdout.
