# RightBrain Matched Holdout Comparison

## 一句話結論

在相同 holdout、seed、候選數與 gate 下，raw model 候選通過率由 16.7% 變為 26.7%（+10.0 個百分點）。最終品質仍為 100%，表示嚴格 gate 與 deterministic fallback 沒有被放寬；這次量到模型候選可靠度提升，但不是整體認知能力已完成。

## 公平比較條件

- baseline adapter: uruha_v10_all_linear_lora
- trained adapter: uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1
- baseline repair adapter: (none)
- trained repair adapter: (none)
- scope: rightbrain_model_blend_surface_holdout_eval
- seed: 20260708
- candidate_count_per_case: 3
- runtime_contract_version: plan_surface_contract_v1
- baseline repair enabled: False
- trained repair enabled: False

## 訓練摘要

- dataset: rightbrain_plan_surface_contract_v1_train.json
- rows: 1061
- supplemental rows: 36
- init adapter: uruha_rightbrain_plan_sft_lora_v8_contract_v1_from_v5
- output adapter: uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1
- optimizer updates: 15
- nonfinite skips: 0
- nonfinite loss skips: None
- nonfinite gradient skips: None
- learning rate: 3e-07
- optimizer epsilon: None
- max observed gradient norm: None
- initial eval loss: 3.0603
- sampled eval loss: 3.0563

## 執行時間

- baseline case eval: 227.69 seconds
- trained case eval: 248.664 seconds
- delta: 20.974 seconds
- boundary: Single-run wall-clock evidence; use repeated runs before making a latency claim.

## Holdout 指標

| metric | baseline | trained | delta |
|---|---:|---:|---:|
| generated_candidate_count | 30 | 30 | 0 |
| initial_accepted_candidate_count | 5 | 8 | 3 |
| accepted_candidate_count | 5 | 8 | 3 |
| raw_candidate_acceptance_rate | 16.7% | 26.7% | 10.0% |
| repair_attempt_count | 0 | 0 | 0 |
| repair_accepted_count | 0 | 0 | 0 |
| repair_success_rate | - | - | - |
| effective_candidate_acceptance_rate | 16.7% | 26.7% | 10.0% |
| model_selected_case_count | 0 | 1 | 1 |
| model_selected_case_rate | 0.0% | 9.1% | 9.1% |
| final_quality_pass_rate | 100.0% | 100.0% | 0.0% |
| final_language_clean_rate | 100.0% | 100.0% | 0.0% |
| final_forbidden_surface_leak_rate | 0.0% | 0.0% | 0.0% |
| final_generic_template_hit_rate | 0.0% | 0.0% | 0.0% |
| final_normalized_duplicate_reply_rate | 0.0% | 0.0% | 0.0% |

## 個案差異

- `absurdity_mirror_quantum_police` (tease): 行為改變; accepted 1 -> 1; resolved=polite_tone_drift; new=-
- `background_family_pressure` (audited_memory): 行為改變; accepted 1 -> 1; resolved=cjk_language_leak; new=-
- `daily_state_answer` (daily): 行為改變; accepted 2 -> 2; resolved=unexpected_ascii_leak; new=duplicate_candidate
- `explicit_spicy_food_update` (audited_memory): 行為改變; accepted 0 -> 0; resolved=semantic_slots_missing:3/4; new=-
- `explicit_stomach_coffee` (audited_memory): 行為改變; accepted 0 -> 0; resolved=-; new=cjk_language_leak, semantic_slots_missing:1/4
- `no_memory_plain_question` (audited_memory): 行為改變; accepted 0 -> 0; resolved=nonstandard_cjk_surface, unicode_replacement_character; new=over_max_chars
- `private_do_not_mention` (audited_memory): 行為改變; accepted 1 -> 1; resolved=semantic_slots_missing:0/2; new=cjk_language_leak, nonstandard_cjk_surface, over_max_chars, polite_tone_drift
- `support_read_receipt_self_blame` (support): 新增通過; accepted 0 -> 1; resolved=polite_tone_drift; new=over_max_chars
- `support_tired_no_closing_template` (support): 新增通過; accepted 0 -> 2; resolved=over_max_chars, polite_tone_drift; new=-
