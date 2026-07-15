# V37 selective action deliberation development analysis

All 36 items are retired V36 development cases. These results can authorize only the creation of a frozen fresh holdout, never runtime integration.

| policy | exact | no-action | recall | false action | frame F1 | escalated | mean passes | mean latency |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| single_pass_v37_control | 91.7% | 95.0% | 90.9% | 2.8% | 65.9% | 0.0% | 1.00 | 4.08s |
| selective_three_pass_v37_candidate | 91.7% | 95.0% | 90.9% | 2.8% | 65.9% | 63.9% | 2.28 | 7.33s |
| always_three_pass_v37_cost_reference | 91.7% | 95.0% | 90.9% | 2.8% | 65.9% | 100.0% | 3.00 | 9.50s |

## Candidate gate

- Passed: `False`
- Failed checks: `['compiled_call_exact_accuracy', 'no_action_specificity', 'required_action_recall', 'false_action_rate', 'parse_success_rate', 'commitment_frame_micro_f1']`
- Decision: `do_not_advance_v37_selective_deliberation`

## Selective candidate action failures

- `v34c_action_none_music`: expected `[]`, got `[{'name': 'play_motion', 'arguments': {'motion': 'idle'}}]`; risk={'escalate': False, 'reasons': []}.
- `v34c_action_negated_nod_shake`: expected `[{'name': 'play_motion', 'arguments': {'motion': 'shake_head'}}]`, got `[]`; risk={'escalate': True, 'reasons': ['input_conflict_marker', 'primary_parse_failure']}.
- `v34c_action_negated_angry_neutral`: expected `[{'name': 'set_expression', 'arguments': {'expression': 'neutral'}}]`, got `[]`; risk={'escalate': True, 'reasons': ['input_conflict_marker', 'requested_frame_blocked_by_negation_or_cancellation_guard']}.

## Evidence boundary

A passing development gate means only that a new holdout may be authored, frozen, and run. It does not prove generalization or authorize VRM execution.
