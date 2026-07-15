# V59 event-role independent holdout

Both conditions used one shared fresh local-model fallback per target and the same V57 compiler.

| Metric | V58 control | V59 candidate |
|---|---:|---:|
| State commitments | 46/73 (63.01%) | 67/73 (91.78%) |
| Ordered exact cases | 48/72 (66.67%) | 68/72 (94.44%) |
| False-action cases | 24 | 4 |
| Required-call recall | 100.00% | 100.00% |

- Event-role relation coverage: 42/42 (100.00%)
- Role-slot accuracy: 261/280 (93.21%)
- Direct-request recall: 78.57%
- Case fixes / regressions: 20 / 0
- Exact McNemar p: 0.000002
- Gate: FAIL
- Decision: `reject_v59_independent_advancement_and_attribute_failure`

A pass supports only this project-fresh Japanese event-role slice. Runtime and physical execution remain unauthorized.
