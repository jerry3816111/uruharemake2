# RightBrain V21 訓練前偏好難度 Probe

## 結論

未見來源仍有 V10 排錯的真實 pair，可進行一次保守的 on-policy SimPO 訓練。

| 指標 | 結果 |
|---|---:|
| train pairs | 18 |
| unseen eval pairs | 10 |
| source overlap | 0 |
| unseen chosen preference | 40.0% |
| unseen target-margin pass | 20.0% |
| unseen V10 misranked pairs | 6 |
| authorize training | YES |

## Gate

| 條件 | 結果 |
|---|---|
| dataset_authorized_for_probe | PASS |
| train_eval_source_overlap_is_zero | PASS |
| unseen_source_count_at_least_2 | PASS |
| unseen_pair_count_at_least_4 | PASS |
| unseen_preference_is_not_saturated | PASS |
| unseen_target_margin_is_not_saturated | PASS |
| unseen_contains_model_misranking | PASS |

研究邊界：This probe measures likelihood ranking under the frozen V10 policy. It can block an uninformative training run, but it cannot prove that preference training will improve generated replies.
