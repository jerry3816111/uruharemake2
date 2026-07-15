# V45 fresh matched holdout result

The 48-case internal holdout was frozen before either model condition saw it. It is now consumed and cannot be used for tuning.

| condition | parse | commitment | boundary | requested P/R | frame exact | call exact | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| v44_scope_control | 100.0% (63/63) | 82.0% (50/61) | 58.3% (7/12) | 94.3% / 94.3% | 75.0% | 91.7% | 4.60s |
| v45_discourse_candidate | 100.0% (63/63) | 83.6% (51/61) | 83.3% (10/12) | 93.9% / 88.6% | 77.1% | 85.4% | 4.70s |

## Frozen comparison

- Commitment delta: `+1.64 pp` (+1 correct targets).
- Taxonomy-boundary correct-count delta: `+3`.
- Fixed targets: `4`; regressed targets: `3`.
- Extra candidates classified as requested: `1`.

## Gate

- Absolute gate passed: `False`; failures: `['commitment_accuracy', 'requested_commitment_precision', 'requested_commitment_recall', 'supported_frame_case_exact_rate', 'compiled_call_exact_accuracy', 'no_action_specificity', 'false_action_rate', 'extra_candidate_requested_count']`.
- Matched comparison passed: `False`; failures: `['commitment_accuracy_delta_vs_control', 'semantic_regression_count']`.
- Decision: `stop_v45_without_tuning_on_consumed_holdout`.
