# RightBrain V26 多回答群組資料

## 結論

V10 真實候選已形成來源隔離的多回答群組，可進入凍結 V10 的訓練前群組 probe。

| 指標 | 數量 |
|---|---:|
| 原始不重複回答 | 94 |
| 可訓練情境群組 | 12 |
| 合格回答 | 33 |
| 失敗回答 | 37 |
| 可訓練回答總數 | 70 |
| 每組回答數 | 4–6 |
| 來源能力家族 | 7 |

同一情境可以有多個合格說法；正集合與負集合內部都不指定唯一排名。

## Gate

| 條件 | 結果 |
|---|---|
| source_adapter_is_current_v10 | PASS |
| source_report_count_is_two | PASS |
| source_seeds_are_unique | PASS |
| every_source_report_covers_all_cases | PASS |
| every_source_report_loaded_real_model | PASS |
| every_source_report_has_48_candidates | PASS |
| development_case_contract_valid | PASS |
| promotion_holdout_case_overlap_is_zero | PASS |
| promotion_holdout_input_overlap_is_zero | PASS |
| promotion_holdout_candidate_text_overlap_is_zero | PASS |
| candidate_label_conflict_count_is_zero | PASS |
| group_count_at_least_10 | PASS |
| candidate_count_at_least_60 | PASS |
| source_family_count_at_least_6 | PASS |
| every_group_has_positive_and_negative | PASS |
| minimum_group_size_at_least_4 | PASS |
| all_candidates_are_v10_on_policy | PASS |

研究邊界：Responses are grouped by automatic strict-contract pass/fail labels from the current V10 policy. Multiple positives are intentionally unordered so training does not force one canonical reply. These labels measure contract realization, not broad human preference.
