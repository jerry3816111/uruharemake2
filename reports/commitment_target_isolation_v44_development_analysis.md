# V44 carrier and target-isolation development result

Selected non-semantic carrier: `two_field_object_schema`

| condition | parse | commitment | requested P/R | frame exact | call exact | evidence | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| target_only_control | 100.0% | 89.5% | 95.5% / 95.5% | 88.9% | 94.4% | 97.4% | 4.08s |
| all_targets_relational | 100.0% | 86.8% | 91.7% / 100.0% | 86.1% | 94.4% | 97.4% | 4.37s |
| isolated_other_targets | 100.0% | 84.2% | 91.7% / 100.0% | 83.3% | 97.2% | 97.4% | 4.69s |
| isolated_scope_signals_candidate | 100.0% | 94.7% | 100.0% / 100.0% | 94.4% | 100.0% | 97.4% | 5.47s |

## Causal transitions

- `target_only_control_to_all_targets_relational`: fixed 1, regressed 2
- `all_targets_relational_to_isolated_other_targets`: fixed 0, regressed 1
- `isolated_other_targets_to_isolated_scope_signals_candidate`: fixed 4, regressed 0

- Candidate passed: `False`
- Failed checks: `['commitment_accuracy']`
- Decision: `stop_v44_before_holdout_and_runtime`
