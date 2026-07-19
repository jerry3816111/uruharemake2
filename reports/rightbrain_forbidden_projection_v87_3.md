# V87.3 Normalized-Scope Forbidden-Conflict Projection Regression

- Decision: `authorize_fresh_v88_full_pipeline_holdout_only`
- Integrity: PASS
- Model calls: 0

| Metric | Result |
|---|---:|
| Required contract match | 12/12 |
| Control gate accept | 10/12 |
| Treatment gate accept | 12/12 |
| Recovered conflict-only rejections | 2 |
| New rejections | 0 |
| Nonconflict decision identity | 100.0% |
| Projected stale markers | 4 |
| Projection scope mismatches | 0 |

A pass closes only the known-reply candidate-gate mechanism check. It does not test fresh generation or authorize production; only a disjoint V88 full-pipeline holdout may follow.
