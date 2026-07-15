# V40 domain-separated action-contract development result

Only the model-facing output contract changed. The 4B model, retired cases, generation settings, action ontology, and V39 compiler stayed fixed.

| condition | exact calls | no-action | recall | false action | execution parse | trace wellformed | median | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| v39_replay_control | 100.0% | 100.0% | 100.0% | 0.0% | 100.0% | 88.9% | 3.53s | n/a |
| v40_domain_separated_candidate | 55.6% | 100.0% | 0.0% | 0.0% | 41.7% | 8.3% | 3.48s | 5.41s |

- Fixed prior warning cases: `['v34c_action_none_explicit_none', 'v34c_action_none_expression']`
- Persistent warning cases: `['v34c_action_invalid_camera', 'v34c_action_negated_nod_shake']`
- New warning cases: `['v34c_action_invalid_arms', 'v34c_action_invalid_kick', 'v34c_action_multi_sad_down', 'v34c_action_negated_angry_neutral', 'v34c_action_negated_happy', 'v34c_action_none_music', 'v34c_action_single_neutral', 'v34c_action_single_nod_colloquial', 'v34c_action_single_point', 'v34c_action_single_wave']`
- Action regressions: `['v34c_action_single_wave', 'v34c_action_single_nod_colloquial', 'v34c_action_single_point', 'v34c_action_single_smile_colloquial', 'v34c_action_single_eyes_colloquial', 'v34c_action_single_neutral', 'v34c_action_multi_happy_user', 'v34c_action_multi_surprised_right', 'v34c_action_multi_sad_down', 'v34c_action_multi_neutral_idle', 'v34c_action_multi_angry_shake', 'v34c_action_multi_wave_user', 'v34c_action_negated_down_user', 'v34c_action_negated_nod_shake', 'v34c_action_negated_angry_neutral', 'v34c_action_negated_point_wave']`
- Candidate passed: `False`
- Failed checks: `['compiled_call_exact_accuracy', 'required_action_recall', 'execution_parse_success_rate', 'trace_wellformed_rate']`
- Decision: `do_not_advance_v40_domain_separated_contract`
