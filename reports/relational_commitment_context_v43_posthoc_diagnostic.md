# V43 post-hoc carrier diagnostic

> Exploratory only. This does not alter the preregistered V43 failure or authorize holdout/runtime use.

| condition | strict object | unique label recoverable | post-hoc correct/all | correct/recoverable |
|---|---:|---:|---:|---:|
| commitment_only_candidate | 1/38 | 34/38 | 27/38 | 79.4% |
| relational_context_candidate | 4/38 | 35/38 | 26/38 | 74.3% |

- Output shapes: `{"commitment_only_candidate": {"invalid_json_other": 7, "json_string_enum": 6, "nested_commitment_object": 15, "plain_enum_token": 9, "strict_object": 1}, "relational_context_candidate": {"invalid_json_other": 16, "nested_commitment_object": 18, "strict_object": 4}}`
- Relational fixes: `[{'case_id': 'v34c_action_single_smile_colloquial', 'target_id': 'expression.happy'}, {'case_id': 'v34c_action_multi_surprised_right', 'target_id': 'expression.surprised'}, {'case_id': 'v34c_action_multi_sad_down', 'target_id': 'expression.sad'}, {'case_id': 'v34c_action_multi_angry_shake', 'target_id': 'expression.angry'}, {'case_id': 'v34c_action_multi_angry_shake', 'target_id': 'motion.shake_head'}, {'case_id': 'v34c_action_negated_nod_shake', 'target_id': 'motion.shake_head'}]`
- Relational regressions: `[{'case_id': 'v34c_action_multi_happy_user', 'target_id': 'expression.happy'}, {'case_id': 'v34c_action_multi_neutral_idle', 'target_id': 'expression.neutral'}, {'case_id': 'v34c_action_negated_down_user', 'target_id': 'gaze.down'}, {'case_id': 'v34c_action_negated_angry_neutral', 'target_id': 'expression.angry'}, {'case_id': 'v34c_action_negated_point_wave', 'target_id': 'motion.point'}, {'case_id': 'v34c_action_ambiguous_direction', 'target_id': 'gaze.left'}, {'case_id': 'v34c_action_ambiguous_direction', 'target_id': 'gaze.right'}]`
- Conclusion: The one-field carrier failed structurally. Relational context recovered several coordinated requests but also spread request force into locally negated targets, so both carrier design and target isolation require a new preregistered experiment.
