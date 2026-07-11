# RightBrain V26 群組訓練前 Probe

## 結論

未見來源含多個 V10 錯排回答，固定 reference 已建立，可進行一次保守的群組偏好訓練。

| 未見指標 | 結果 |
|---|---:|
| 群組 | 4 |
| 回答 | 24 |
| 正負配對 | 34 |
| V10 正回答勝率 | 26.5% |
| V10 錯排 pair | 25 |
| 正回答為組內最高 | 0.0% |
| authorize training | YES |

## Gate

| 條件 | 結果 |
|---|---|
| dataset_authorized_for_group_probe | PASS |
| train_eval_source_overlap_is_zero | PASS |
| unseen_source_count_at_least_2 | PASS |
| train_group_count_at_least_6 | PASS |
| unseen_group_count_at_least_3 | PASS |
| unseen_candidate_count_at_least_18 | PASS |
| all_reference_log_probs_are_finite | PASS |
| unseen_pairwise_preference_is_not_saturated | PASS |
| unseen_contains_at_least_3_misranked_pairs | PASS |

研究邊界：This probe measures frozen V10 likelihood over unordered positive and negative response sets. It establishes training headroom and reference scores, not generated-response improvement.
