# V58 relation-safety independent holdout

Both conditions used one shared fresh local-model fallback per target and the same V57 compiler.

| Metric | V56 control | V58 candidate |
|---|---:|---:|
| State commitments | 47/87 (54.02%) | 82/87 (94.25%) |
| Ordered exact cases | 42/64 (65.62%) | 60/64 (93.75%) |
| False-action cases | 21 | 3 |
| No-action specificity | 58.82% | 94.12% |
| Required-call recall | 94.12% | 94.12% |

- Expected relation coverage: 100.00%
- Contrast false-positive targets: 0
- State fixes / regressions: 35 / 0
- Case fixes / regressions: 18 / 0
- Gate: FAIL
- Decision: `reject_v58_holdout_advancement_and_attribute_failure`

A pass supports only this project-fresh Japanese relation-safety slice. Runtime and physical execution remain unauthorized.
