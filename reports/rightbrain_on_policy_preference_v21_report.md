# RightBrain V21 On-Policy Preference Dataset

## 結論

V21 on-policy 資料通過來源、多樣性與 holdout 邊界 gate，可進入訓練前偏好難度 probe。

| 指標 | 值 |
|---|---:|
| source adapter | uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1 |
| seeds | [20260712, 20260713] |
| development cases | 16 |
| cases with strict chosen | 13 |
| preference pairs | 28 |
| source families | 7 |
| holdout chosen overlap | 0 |

## Gate

| 條件 | 結果 |
|---|---|
| source_adapter_is_current_v10 | PASS |
| source_report_count_is_two | PASS |
| every_source_report_covers_all_cases | PASS |
| every_source_report_loaded_real_model | PASS |
| every_source_report_has_48_candidates | PASS |
| development_case_contract_valid | PASS |
| promotion_holdout_case_overlap_is_zero | PASS |
| promotion_holdout_input_overlap_is_zero | PASS |
| promotion_holdout_chosen_text_overlap_is_zero | PASS |
| pair_count_at_least_24 | PASS |
| source_family_count_at_least_6 | PASS |
| strict_chosen_case_count_at_least_8 | PASS |
| failure_family_count_at_least_4 | PASS |
| all_chosen_are_v10_on_policy | PASS |
| all_rejected_are_v10_on_policy | PASS |

## Failure Families

| family | count |
|---|---:|
| language_pollution | 32 |
| semantic_slots_missing | 24 |
| ascii_leak | 17 |
| polite_tone_drift | 11 |
| over_max_chars | 1 |

研究邊界：Both chosen and rejected completions are sampled from the current V10 policy. Chosen labels are automatic strict-contract labels, not human preference ratings. This authorizes only a pre-training preference probe, never adapter promotion.
