# Semantic memory recall support V1 holdout result

- Decision: `holdout_reject_or_inconclusive`
- Questions / decisions: 8 / 32
- Wrong trace selections: 9
- Target-removed selections: 6

| Condition | Safe | Selected | Ambiguous | Unsupported |
|---|---:|---:|---:|---:|
| c0_intact_target_and_hard_negative | 87.5% | 12.5% | 75.0% | 12.5% |
| t1_remove_exact_target | 25.0% | 75.0% | 0.0% | 25.0% |
| t2_replace_exact_target | 37.5% | 37.5% | 37.5% | 25.0% |
| n1_remove_exact_hard_negative | 75.0% | 75.0% | 0.0% | 12.5% |

## Gates

- row_count_exact: PASS
- question_count_exact: PASS
- no_wrong_trace_selection: FAIL
- target_removal_never_selects: FAIL
- intact_safe: FAIL
- replacement_safe: FAIL
- irrelevant_removed_selects_target: FAIL
- no_sensitive_fast_path: PASS
- no_non_recall_fast_path: PASS
- no_broad_presence_fast_path: PASS
- no_transport_errors: PASS
- no_production_writes: PASS
- no_vrm_actions: PASS

## Evidence boundary

This is a selector safety holdout, not official LongMemEval answer accuracy. Production remains disabled.
