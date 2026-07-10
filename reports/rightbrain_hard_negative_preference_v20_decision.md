# RightBrain V20 Hard-Negative SimPO 決策

## 結論

允許 V20 進入 V10 對照的雙 seed 真實模型 holdout。

| 指標 | 結果 |
|---|---:|
| hard-negative pairs | 32 |
| mean char delta | +1.34 |
| max absolute char delta | 6 |
| optimizer updates | 6/6 |
| non-finite skips | 0 |
| train chosen preference | 79.2% |
| unseen chosen preference | 100.0% -> 100.0% |
| unseen mean margin | +1.259030 -> +1.273806 |

## Gate

| 條件 | 結果 |
|---|---|
| dataset_pairs_are_single_slot_omissions | PASS |
| dataset_pairs_are_length_matched | PASS |
| dataset_promotion_holdout_overlap_is_zero | PASS |
| train_eval_source_overlap_is_zero | PASS |
| all_optimizer_updates_completed | PASS |
| nonfinite_training_events_are_zero | PASS |
| train_chosen_preference_rate_at_least_75pct | PASS |
| unseen_eval_chosen_preference_rate_at_least_75pct | PASS |
| unseen_eval_mean_margin_improved | PASS |
| unseen_eval_target_margin_rate_at_least_50pct | PASS |

## 研究邊界

V20 uses manually authored, length-matched synthetic hard negatives. Passing this gate only authorizes actual-model evaluation; it does not promote the adapter.
