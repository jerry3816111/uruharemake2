# V60 predicate-morphology independent holdout

Both conditions used one shared fresh local-model fallback per target and the same V57 compiler.

| Metric | V59 control | V60 candidate |
|---|---:|---:|
| State commitments | 84/120 (70.00%) | 113/120 (94.17%) |
| Ordered exact cases | 86/117 (73.50%) | 115/117 (98.29%) |
| False-action cases | 31 | 2 |
| Required-call recall | 100.00% | 100.00% |
| External exact cases | 17/19 | 18/19 |

- V60 controlled morphology slots: 588/588 (100.00%)
- State fixes / regressions: 29 / 0
- Case fixes / regressions: 29 / 0
- Exact McNemar p: 0.000000
- Gate: FAIL
- Decision: `reject_v60_independent_advancement_and_attribute_failure`

A pass supports only this bounded Japanese action-authorization slice. Runtime and physical execution remain unauthorized.
