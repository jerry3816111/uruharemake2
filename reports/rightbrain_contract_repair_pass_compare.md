# RightBrain Matched Holdout Comparison

## 一句話結論

在相同 adapter、holdout、seed、候選數與 gate 下，首次 raw 通過率維持 50.0%；開啟一次契約修正後，有效候選通過率由 50.0% 變為 50.0%（+0.0 個百分點）。最終品質仍須通過原 gate，未放寬語意、語言或記憶權限。這個 repair prompt 沒有產生淨改善，不應預設開啟；下一步需要先訓練修正能力。

## 公平比較條件

- baseline adapter: uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1
- trained adapter: uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1
- scope: rightbrain_model_blend_surface_holdout_eval
- seed: 20260624
- candidate_count_per_case: 1
- runtime_contract_version: plan_surface_contract_v1
- baseline repair enabled: False
- trained repair enabled: True

## 固定模型背景

- rows: 1061
- supplemental rows: 36
- optimizer updates: 15
- nonfinite skips: 0
- learning rate: 3e-07
- initial eval loss: 3.0603
- sampled eval loss: 3.0563

## 執行時間

- baseline case eval: 93.791 seconds
- trained case eval: 165.715 seconds
- delta: 71.924 seconds
- boundary: Single-run wall-clock evidence; use repeated runs before making a latency claim.

## Holdout 指標

| metric | baseline | trained | delta |
|---|---:|---:|---:|
| generated_candidate_count | 10 | 10 | 0 |
| initial_accepted_candidate_count | 5 | 5 | 0 |
| accepted_candidate_count | 5 | 5 | 0 |
| raw_candidate_acceptance_rate | 50.0% | 50.0% | 0.0% |
| repair_attempt_count | 0 | 5 | 5 |
| repair_accepted_count | 0 | 0 | 0 |
| repair_success_rate | - | 0.0% | - |
| effective_candidate_acceptance_rate | 50.0% | 50.0% | 0.0% |
| model_selected_case_count | 1 | 1 | 0 |
| model_selected_case_rate | 9.1% | 9.1% | 0.0% |
| final_quality_pass_rate | 100.0% | 100.0% | 0.0% |
| final_language_clean_rate | 100.0% | 100.0% | 0.0% |
| final_forbidden_surface_leak_rate | 0.0% | 0.0% | 0.0% |
| final_generic_template_hit_rate | 0.0% | 0.0% | 0.0% |
| final_normalized_duplicate_reply_rate | 0.0% | 0.0% | 0.0% |

## 個案差異

- `background_family_pressure` (audited_memory): 行為改變; accepted 0 -> 0; resolved=unexpected_ascii_leak; new=-
- `explicit_stomach_coffee` (audited_memory): 行為改變; accepted 0 -> 0; resolved=-; new=polite_tone_drift
- `no_memory_plain_question` (audited_memory): 行為改變; accepted 0 -> 0; resolved=unexpected_ascii_leak; new=-
- `private_do_not_mention` (audited_memory): 行為改變; accepted 0 -> 0; resolved=cjk_language_leak, nonstandard_cjk_surface, semantic_slots_missing:0/1; new=polite_tone_drift
