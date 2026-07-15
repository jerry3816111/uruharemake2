# V59 event-role governor development replay

This matched replay reused frozen V58 model outputs and made zero model calls.

| Metric | V58 + V57 control | V59 + V57 candidate |
|---|---:|---:|
| State commitments | 82/87 (94.25%) | 85/87 (97.70%) |
| Ordered exact cases | 60/64 (93.75%) | 63/64 (98.44%) |
| False-action cases | 3 | 0 |
| No-action specificity | 94.12% | 100.00% |
| Required-call recall | 94.12% | 94.12% |

- Target fixes / regressions: 3 / 0
- Case fixes / regressions: 3 / 0
- Gate: PASS
- Decision: `authorize_independent_v59_event_role_holdout`

This is consumed-data development evidence only. It cannot authorize runtime or broad cognition claims.
