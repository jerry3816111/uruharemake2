# Reflection Causal Replay V2

- decision: `working_memory_channel_repair_confirmed_but_reflection_redesign_required`
- evidence: exact seen V1 replay, not an independent holdout

## V1 -> V2

- valid_rule_retrieval_rate: `0.0` -> `1.0` (delta `1.0`)
- control_behavior_success_rate: `0.4444` -> `0.4444` (delta `0.0`)
- treatment_behavior_success_rate: `0.3333` -> `0.3333` (delta `0.0`)
- treatment_behavior_delta: `-0.1111` -> `-0.1111` (delta `0.0`)
- paired_behavior_gains: `0` -> `0` (delta `0.0`)
- paired_behavior_regressions: `2` -> `1` (delta `-1.0`)
- paired_behavior_net_gain: `-2` -> `-1` (delta `1.0`)

## V2 Gates

- expected_rule_write_recall: `FAIL`
- valid_rule_precision: `FAIL`
- no_rule_specificity: `FAIL`
- valid_rule_retrieval_rate: `PASS`
- treatment_behavior_delta: `FAIL`
- paired_behavior_net_gain: `FAIL`
- interaction_category_paired_gains: `FAIL`
- paired_behavior_regressions: `FAIL`

## Cases

- `semantic_zh_evening_coffee` write=True valid=True retrieved=True control=False treatment=False gain=False regression=False
- `semantic_en_small_steps` write=True valid=True retrieved=True control=True treatment=False gain=False regression=True
- `semantic_ja_horror_sleep` write=True valid=True retrieved=True control=True treatment=True gain=False regression=False
- `strategy_zh_one_question` write=False valid=False retrieved=False control=True treatment=True gain=False regression=False
- `strategy_zh_answer_before_rest` write=True valid=True retrieved=True control=False treatment=False gain=False regression=False
- `strategy_ja_conclusion_first` write=False valid=False retrieved=False control=False treatment=False gain=False regression=False
- `interpretation_zh_suanle_angry` write=False valid=False retrieved=False control=False treatment=False gain=False regression=False
- `interpretation_zh_haha_awkward` write=False valid=False retrieved=False control=False treatment=False gain=False regression=False
- `interpretation_ja_betsuni` write=False valid=False retrieved=False control=True treatment=True gain=False regression=False
- `negative_zh_transient_cola` write=False valid=True retrieved=False control=True treatment=True gain=False regression=False
- `negative_en_third_party_always` write=True valid=False retrieved=True control=True treatment=True gain=False regression=False
- `negative_zh_hypothetical_like` write=True valid=False retrieved=True control=True treatment=True gain=False regression=False
