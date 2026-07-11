# RightBrain V28 人類偏好校準

## 結論

現有盲評足以證明自動 contract pass 不等於人類偏好，但不能直接拿來訓練 V28：同一題只有一個 S0 右腦候選，within-policy 偏好對為 0，而且 programmatic pass 與 S0 系統身分完全重合。正式右腦維持 V10。

| 證據 | 結果 |
|---|---:|
| 完成題目 | 19 |
| 真人候選評分 | 76 |
| 題內不重複回答 | 57 |
| S0 同 policy 偏好對 | 0 |
| 相同文字評分不一致 | 11/19 |
| 相同文字最終判定矛盾 | 7/19 |
| 可直接用於偏好訓練 | NO |

## 最重要的混淆變因

- programmatic pass 的系統：`S0_URUHA_RIGHTBRAIN`
- pass 是否完全等同 S0 身分：`True`
- S0 內部自動標籤值：`[True]`
- S0 的真人最終判定：`{'borderline': 8, 'no': 2, 'yes': 9}`

因此下表只能描述現有四種候選的關係，不能證明自動 gate 能預測任意右腦回答的人類偏好。

| 人類標準 | TP | FP | TN | FN | precision | recall | balanced accuracy | MCC |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 嚴格 YES | 9 | 10 | 50 | 7 | 0.474 | 0.562 | 0.698 | 0.373 |
| 可接受（YES+borderline） | 17 | 2 | 24 | 33 | 0.895 | 0.340 | 0.632 | 0.288 |

## 分批多維結果

v15 與 v16 使用不同問題與量表，所以分開列出，不做跨量表總分。

### v15_fresh_after_reply_priority_repair_partial_2026_05_24

| system | n | naturalness_1_5 | semantic_completeness_1_5 | style_consistency_1_5 | user_facing_ok_1_5 |
|---|---:|---:|---:|---:|---:|
| C1_GENERIC_PARAPHRASE_PROXY | 12 | 2.417 | 2.250 | 2.333 | 2.417 |
| C2_TEMPLATE_RESPONSE | 12 | 1.833 | 1.583 | 1.750 | 1.500 |
| C3_DIRECT_LEFTBRAIN_OUTPUT | 12 | 2.500 | 2.167 | 2.333 | 2.167 |
| S0_URUHA_RIGHTBRAIN | 12 | 3.167 | 3.250 | 3.083 | 3.000 |

### v16_followup_compact_partial_2026_05_24

| system | n | human_likeness_1_5 | semantic_understanding_1_5 |
|---|---:|---:|---:|
| C1_GENERIC_PARAPHRASE_PROXY | 7 | 2.571 | 2.571 |
| C2_TEMPLATE_RESPONSE | 7 | 3.000 | 1.857 |
| C3_DIRECT_LEFTBRAIN_OUTPUT | 7 | 2.571 | 2.429 |
| S0_URUHA_RIGHTBRAIN | 7 | 3.429 | 3.429 |

## 明示成對偏好

v16 共留下 `7` 組明示 best/worst；這些是跨系統評價證據，不是同 policy 訓練對。

| task | best system | worst system |
|---|---|---|
| rb_unseen15_0013 | S0_URUHA_RIGHTBRAIN | C2_TEMPLATE_RESPONSE |
| rb_unseen15_0016 | S0_URUHA_RIGHTBRAIN | C2_TEMPLATE_RESPONSE |
| rb_unseen15_0017 | C2_TEMPLATE_RESPONSE | C1_GENERIC_PARAPHRASE_PROXY |
| rb_unseen15_0022 | C1_GENERIC_PARAPHRASE_PROXY | C2_TEMPLATE_RESPONSE |
| rb_unseen15_0024 | C2_TEMPLATE_RESPONSE | C1_GENERIC_PARAPHRASE_PROXY |
| rb_unseen15_0028 | C2_TEMPLATE_RESPONSE | C3_DIRECT_LEFTBRAIN_OUTPUT |
| rb_unseen15_0031 | C1_GENERIC_PARAPHRASE_PROXY | S0_URUHA_RIGHTBRAIN |

## Training gate

| 條件 | 結果 |
|---|---|
| source_hashes_match_existing_evidence_report | PASS |
| all_completed_rows_have_key_labels | PASS |
| all_source_joins_are_complete | PASS |
| every_completed_task_has_four_candidate_ratings | PASS |
| promotion_holdout_input_overlap_is_zero | PASS |
| promotion_holdout_output_overlap_is_zero | PASS |
| explicit_best_worst_pairs_have_no_errors | PASS |
| within_policy_pair_count_is_positive | FAIL |
| within_policy_programmatic_label_has_both_values | FAIL |
| programmatic_pass_is_not_identical_to_system_identity | FAIL |
| exact_duplicate_human_decisions_are_consistent | FAIL |

## 下一步

先在全新 development prompts 上由 V10 每題產生多個匿名候選，再收集同 policy 的成對偏好；promotion holdout 保持未觸碰。建立至少兩位獨立評分者後，才可主張一般人類偏好而非單一使用者偏好。

研究邊界：This is a partial single-rater pilot. Cross-system confusion metrics are descriptive and confounded by candidate-system construction. The report authorizes neither preference training nor a population-level claim about human likeness.
