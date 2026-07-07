# RightBrain Matched Holdout Comparison

## 一句話結論

在相同 holdout、seed、候選數、repair 開關與嚴格 gate 下，首次 raw 通過率由 40.0% 變為 40.0%；repair 成功數由 0/6 變為 0/6，有效候選通過率由 40.0% 變為 40.0%（+0.0 個百分點）。最終品質仍須通過原 gate，未放寬語意、語言或記憶權限。這次訓練未證明 repair 能力有淨改善，runtime repair 不應預設開啟。

## 公平比較條件

- baseline adapter: uruha_rightbrain_plan_sft_lora_v8_contract_v1_from_v5
- trained adapter: uruha_rightbrain_plan_sft_lora_v8_contract_v1_from_v5
- baseline repair adapter:
- trained repair adapter: uruha_rightbrain_repair_lora_v1_base
- scope: rightbrain_model_blend_surface_holdout_eval
- seed: 20260704
- candidate_count_per_case: 1
- runtime_contract_version: plan_surface_contract_v1
- baseline repair enabled: True
- trained repair enabled: True

## 訓練摘要

- dataset: rightbrain_repair_curriculum_v1.json
- rows: 720
- supplemental rows: 0
- init adapter: base_model_new_lora
- output adapter: uruha_rightbrain_repair_lora_v1_base
- optimizer updates: 17
- nonfinite skips: 0
- nonfinite loss skips: 0
- nonfinite gradient skips: 0
- learning rate: 3e-07
- optimizer epsilon: 1e-05
- max observed gradient norm: 1170039.875
- initial eval loss: 3.4490
- sampled eval loss: 3.0309

## 防止小抄

- repair curriculum rows: 720
- holdout cases: 11
- holdout input overlap: 0
- holdout contract overlap: 0
- holdout target overlap: 0
- rejected draft exposed during training: False

## 執行時間

- baseline case eval: 155.116 seconds
- trained case eval: 136.384 seconds
- delta: -18.732 seconds
- boundary: Single-run wall-clock evidence; use repeated runs before making a latency claim.

## Holdout 指標

| metric | baseline | trained | delta |
|---|---:|---:|---:|
| generated_candidate_count | 10 | 10 | 0 |
| initial_accepted_candidate_count | 4 | 4 | 0 |
| accepted_candidate_count | 4 | 4 | 0 |
| raw_candidate_acceptance_rate | 40.0% | 40.0% | 0.0% |
| repair_attempt_count | 6 | 6 | 0 |
| repair_accepted_count | 0 | 0 | 0 |
| repair_success_rate | 0.0% | 0.0% | 0.0% |
| effective_candidate_acceptance_rate | 40.0% | 40.0% | 0.0% |
| model_selected_case_count | 1 | 1 | 0 |
| model_selected_case_rate | 9.1% | 9.1% | 0.0% |
| final_quality_pass_rate | 100.0% | 100.0% | 0.0% |
| final_language_clean_rate | 100.0% | 100.0% | 0.0% |
| final_forbidden_surface_leak_rate | 0.0% | 0.0% | 0.0% |
| final_generic_template_hit_rate | 0.0% | 0.0% | 0.0% |
| final_normalized_duplicate_reply_rate | 0.0% | 0.0% | 0.0% |

## 個案差異

- `background_family_pressure` (audited_memory): 行為改變; accepted 0 -> 0; resolved=-; new=polite_tone_drift
- `private_do_not_mention` (audited_memory): 行為改變; accepted 0 -> 0; resolved=polite_tone_drift; new=semantic_slots_missing:0/1
