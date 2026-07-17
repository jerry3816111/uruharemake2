# Reflection Layer Audit V1 Calibration

- decision: `reject_atomic_judge_and_do_not_use_for_v5_design`
- all_gates_pass: `False`
- boundary: authored calibration only; not runtime or independent evidence

## Metrics

- case_count: `12`
- atomic_claim_count: `36`
- schema_parse_rate: `0.9167`
- atomic_relation_accuracy: `0.75`
- critical_false_entailment_count: `2`
- candidate_acceptance_accuracy: `0.9167`
- accepted_surface_specificity: `1.0`
- model_call_count: `12`
- accepted_case_count: `5`
- all_gates_pass: `False`

## Gates

- schema_parse_rate: `FAIL`
- atomic_relation_accuracy: `FAIL`
- critical_false_entailment_count: `FAIL`
- candidate_acceptance_accuracy: `FAIL`
- accepted_surface_specificity: `PASS`
- model_call_count: `PASS`

## Cases

- `semantic_zh_music_faithful` expected=True observed=True surface=True
  - `work_context` gold=entailed observed=entailed correct=True
  - `no_lyrics` gold=entailed observed=entailed correct=True
  - `vocals_distract` gold=entailed observed=entailed correct=True
- `semantic_zh_music_negated` expected=False observed=False surface=True
  - `work_context` gold=entailed observed=entailed correct=True
  - `no_lyrics` gold=contradicted observed=contradicted correct=True
  - `vocals_distract` gold=contradicted observed=contradicted correct=True
- `semantic_en_spicy_faithful` expected=True observed=False surface=True
  - `avoid_spicy` gold=entailed observed=entailed correct=True
  - `evening_scope` gold=entailed observed=contradicted correct=False
  - `stomach_reason` gold=entailed observed=missing correct=False
- `semantic_en_spicy_reason_missing` expected=False observed=False surface=True
  - `avoid_spicy` gold=entailed observed=missing correct=False
  - `evening_scope` gold=entailed observed=entailed correct=True
  - `stomach_reason` gold=missing observed=missing correct=True
- `procedural_ja_photo_faithful` expected=True observed=True surface=True
  - `assistant_actor` gold=entailed observed=entailed correct=True
  - `user_target` gold=entailed observed=entailed correct=True
  - `before_sending` gold=entailed observed=entailed correct=True
- `procedural_ja_photo_actor_swap` expected=False observed=False surface=True
  - `assistant_actor` gold=contradicted observed=entailed correct=False
  - `user_target` gold=contradicted observed=contradicted correct=True
  - `before_sending` gold=entailed observed=entailed correct=True
- `procedural_zh_answer_order_faithful` expected=True observed=True surface=True
  - `answer_first` gold=entailed observed=entailed correct=True
  - `reason_after` gold=entailed observed=entailed correct=True
  - `no_background_first` gold=entailed observed=entailed correct=True
- `procedural_zh_answer_order_reversed` expected=False observed=False surface=True
  - `answer_first` gold=contradicted observed=contradicted correct=True
  - `reason_after` gold=contradicted observed=missing correct=False
  - `no_background_first` gold=contradicted observed=entailed correct=False
- `interpretive_en_minute_faithful` expected=True observed=True surface=True
  - `trigger_phrase` gold=entailed observed=entailed correct=True
  - `needs_thinking_time` gold=entailed observed=entailed correct=True
  - `not_leave_request` gold=entailed observed=entailed correct=True
- `interpretive_en_minute_reversed` expected=False observed=False surface=True
  - `trigger_phrase` gold=entailed observed=entailed correct=True
  - `needs_thinking_time` gold=missing observed=missing correct=True
  - `not_leave_request` gold=contradicted observed=contradicted correct=True
- `interpretive_ja_any_faithful` expected=True observed=True surface=True
  - `decision_fatigue` gold=entailed observed=entailed correct=True
  - `preference_may_exist` gold=entailed observed=entailed correct=True
  - `assistant_one_option` gold=entailed observed=entailed correct=True
- `interpretive_ja_any_chinese_surface` expected=False observed=False surface=False
  - `decision_fatigue` gold=entailed observed=None correct=False
  - `preference_may_exist` gold=entailed observed=None correct=False
  - `assistant_one_option` gold=entailed observed=None correct=False
