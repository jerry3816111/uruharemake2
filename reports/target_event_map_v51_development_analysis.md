# V51 target-event-map development result

This is a matched comparison on retired development data, not a fresh holdout.

| condition | parse | commitment | requested P/R | call exact | false actions | median / p95 |
|---|---:|---:|---:|---:|---:|---:|
| v48_six_way_control | 100.0% | 82.0% (50/61) | 93.9% / 88.6% | 87.5% (42/48) | 2 | 2.29s / 4.72s |
| target_event_map_candidate | 100.0% | 88.5% (54/61) | 100.0% / 94.3% | 95.8% (46/48) | 0 | 2.50s / 5.66s |

- Commitment delta: `+4` targets.
- Exact-call delta: `+4` cases.
- False-action delta: `-2` cases.
- Semantic fixes/regressions: `5` / `1`.
- Call fixes/regressions: `5` / `1`.
- Development gate passed: `False`.
- Decision: `reject_v51_due_to_regression_or_gate_failure`.
- Interpretation: The candidate changed behavior but failed the preregistered safety, regression, or quality boundary. Retain V48 and do not tune V51 on these consumed examples.
- Runtime remains unchanged and physical VRM execution remains disabled.
