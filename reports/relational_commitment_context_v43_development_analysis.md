# V43 relational commitment-context development result

| condition | parse | commitment | requested P/R | frame exact | call exact | evidence | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| v42_evidence_index_control | 94.7% | 79.0% | 100.0% / 72.7% | 80.6% | 86.1% | 89.5% | 3.52s |
| commitment_only_candidate | 2.6% | 2.6% | 100.0% / 4.5% | 30.6% | 58.3% | 2.6% | 3.22s |
| relational_context_candidate | 10.5% | 7.9% | 0.0% / 0.0% | 36.1% | 55.6% | 10.5% | 4.21s |

- Relational candidate passed: `False`
- Failed checks: `['classifier_parse_success_rate', 'commitment_accuracy', 'requested_commitment_precision', 'requested_commitment_recall', 'supported_frame_case_exact_rate', 'selected_evidence_support_rate', 'compiled_call_exact_accuracy', 'required_action_recall']`
- Fixed commitments: `[{'case_id': 'v34c_action_none_hypothetical', 'target_id': 'expression.happy'}, {'case_id': 'v34c_action_negated_happy', 'target_id': 'expression.happy'}, {'case_id': 'v34c_action_ambiguous_if', 'target_id': 'gaze.down'}]`
- Regressed commitments: `[{'case_id': 'v34c_action_single_neutral', 'target_id': 'expression.neutral'}]`
- Decision: `do_not_advance_v43_relational_commitment_context`
