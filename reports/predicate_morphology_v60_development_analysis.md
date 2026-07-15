# V60 predicate-morphology development replay

This matched replay reused the frozen V59 model fallback and made zero model calls.

| Metric | V59 control | V60 candidate |
|---|---:|---:|
| State commitments | 67/73 (91.78%) | 71/73 (97.26%) |
| Ordered exact cases | 68/72 (94.44%) | 72/72 (100.00%) |
| False-action cases | 4 | 0 |
| V60 direct-request role recall | n/a | 14/14 |
| V60 role-slot accuracy | n/a | 280/280 (100.00%) |

- State fixes / regressions: 4 / 0
- Case fixes / regressions: 4 / 0
- Gate: PASS
- Decision: `authorize_second_fresh_v60_independent_holdout`

This consumed-data replay can authorize only a second fresh holdout, not runtime deployment.
