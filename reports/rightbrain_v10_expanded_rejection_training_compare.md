# RightBrain Matched Holdout Comparison

## 一句話結論

在相同 holdout、seed、候選數與 gate 下，raw model 候選通過率由 40.0% 提升至 50.0%（+10.0 個百分點）。最終品質仍為 100%，表示嚴格 gate 與 deterministic fallback 沒有被放寬；這次量到的是模型候選可靠度的小幅提升，不是整體認知能力已完成。

## 公平比較條件

- baseline adapter: uruha_rightbrain_plan_sft_lora_v9_rejection_v1
- trained adapter: uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1
- scope: rightbrain_model_blend_surface_holdout_eval
- seed: 20260624
- candidate_count_per_case: 1
- runtime_contract_version: plan_surface_contract_v1

## 訓練摘要

- rows: 1061
- supplemental rows: 36
- optimizer updates: 15
- nonfinite skips: 0
- learning rate: 3e-07
- initial eval loss: 3.0603
- sampled eval loss: 3.0563

## Holdout 指標

| metric | baseline | trained | delta |
|---|---:|---:|---:|
| generated_candidate_count | 10 | 10 | 0 |
| accepted_candidate_count | 4 | 5 | 1 |
| raw_candidate_acceptance_rate | 40.0% | 50.0% | 10.0% |
| model_selected_case_count | 1 | 1 | 0 |
| model_selected_case_rate | 9.1% | 9.1% | 0.0% |
| final_quality_pass_rate | 100.0% | 100.0% | 0.0% |
| final_language_clean_rate | 100.0% | 100.0% | 0.0% |
| final_forbidden_surface_leak_rate | 0.0% | 0.0% | 0.0% |
| final_generic_template_hit_rate | 0.0% | 0.0% | 0.0% |
| final_normalized_duplicate_reply_rate | 0.0% | 0.0% | 0.0% |

## 個案差異

- `support_read_receipt_self_blame` (support): 新增通過; accepted 0 -> 1; resolved=polite_tone_drift, semantic_slots_missing:2/3; new=-
