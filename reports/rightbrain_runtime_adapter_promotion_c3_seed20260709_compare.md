# RightBrain Matched Holdout Comparison

## 一句話結論

在相同 holdout、seed、候選數與 gate 下，raw model 候選通過率由 30.0% 變為 33.3%（+3.3 個百分點）。最終品質仍為 100%，表示嚴格 gate 與 deterministic fallback 沒有被放寬；這次量到模型候選可靠度提升，但不是整體認知能力已完成。

## 公平比較條件

- baseline adapter: uruha_v10_all_linear_lora
- trained adapter: uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1
- baseline repair adapter: (none)
- trained repair adapter: (none)
- scope: rightbrain_model_blend_surface_holdout_eval
- seed: 20260709
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

- baseline case eval: 216.684 seconds
- trained case eval: 218.774 seconds
- delta: 2.09 seconds
- boundary: Single-run wall-clock evidence; use repeated runs before making a latency claim.

## Holdout 指標

| metric | baseline | trained | delta |
|---|---:|---:|---:|
| generated_candidate_count | 30 | 30 | 0 |
| initial_accepted_candidate_count | 9 | 10 | 1 |
| accepted_candidate_count | 9 | 10 | 1 |
| raw_candidate_acceptance_rate | 30.0% | 33.3% | 3.3% |
| repair_attempt_count | 0 | 0 | 0 |
| repair_accepted_count | 0 | 0 | 0 |
| repair_success_rate | - | - | - |
| effective_candidate_acceptance_rate | 30.0% | 33.3% | 3.3% |
| model_selected_case_count | 1 | 2 | 1 |
| model_selected_case_rate | 9.1% | 18.2% | 9.1% |
| final_quality_pass_rate | 100.0% | 100.0% | 0.0% |
| final_language_clean_rate | 100.0% | 100.0% | 0.0% |
| final_forbidden_surface_leak_rate | 0.0% | 0.0% | 0.0% |
| final_generic_template_hit_rate | 0.0% | 0.0% | 0.0% |
| final_normalized_duplicate_reply_rate | 0.0% | 0.0% | 0.0% |

## 個案差異

- `absurdity_mirror_quantum_police` (tease): 行為改變; accepted 1 -> 2; resolved=unexpected_ascii_leak; new=-
- `daily_state_answer` (daily): 行為改變; accepted 1 -> 2; resolved=duplicate_candidate; new=semantic_slots_missing:0/1, unexpected_ascii_leak
- `explicit_spicy_food_update` (audited_memory): 行為改變; accepted 0 -> 0; resolved=cjk_language_leak, over_max_chars, semantic_slots_missing:2/4; new=-
- `explicit_stomach_coffee` (audited_memory): 行為改變; accepted 0 -> 0; resolved=cjk_language_leak, nonstandard_cjk_surface, semantic_slots_missing:3/4; new=missing_japanese_surface, semantic_slots_missing:0/4, semantic_slots_missing:2/4
- `private_do_not_mention` (audited_memory): 行為改變; accepted 2 -> 1; resolved=-; new=cjk_language_leak, nonstandard_cjk_surface, semantic_slots_missing:0/2
- `reference_fragment_probe` (repair): 行為改變; accepted 2 -> 2; resolved=duplicate_candidate; new=unexpected_ascii_leak
- `support_read_receipt_self_blame` (support): 新增通過; accepted 0 -> 1; resolved=polite_tone_drift, semantic_slots_missing:0/3, semantic_slots_missing:2/3; new=semantic_slots_missing:1/3, unexpected_ascii_leak
- `support_tired_no_closing_template` (support): 行為改變; accepted 1 -> 0; resolved=-; new=-
