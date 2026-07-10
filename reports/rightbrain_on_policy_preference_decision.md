# RightBrain On-Policy Preference 訓練決策

## 結論

沒有候選通過未見偏好學習 gate；不執行昂貴 runtime holdout，正式右腦維持 V10。

| 候選 | epoch | updates | unseen preference | target margin | mean margin delta | preferred log-prob delta | gradient max | holdout |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| V21 1-epoch | 1.0 | 5 | 40% → 30% | 20% | +0.011435 | +0.004696 | 9.896 | BLOCK |
| V22 3-epoch | 3.0 | 14 | 40% → 40% | 20% | +0.012514 | +0.014739 | 771824.812 | BLOCK |

## 診斷

on-policy 資料確實揭露 V10 的自然錯誤，但目前 pair-level SimPO 沒有把未見偏好率推高；增加 epoch 只放大梯度，沒有改善正確排序。下一輪應平衡每個 source prompt 的總梯度，避免同一 prompt 因 rejected 候選較多而被重複加權。

## Gate 明細

### V21 1-epoch

| 條件 | 結果 |
|---|---|
| train_eval_source_overlap_is_zero | PASS |
| all_optimizer_updates_completed | PASS |
| nonfinite_training_events_are_zero | PASS |
| train_chosen_preference_rate_at_least_75pct | FAIL |
| unseen_chosen_preference_rate_at_least_75pct | FAIL |
| unseen_mean_margin_improved | PASS |
| unseen_target_margin_rate_at_least_50pct | FAIL |
| preferred_likelihood_evidence_is_complete | PASS |
| unseen_mean_preferred_log_prob_non_decreasing | PASS |
| unseen_preferred_likelihood_decrease_rate_at_most_50pct | PASS |

### V22 3-epoch

| 條件 | 結果 |
|---|---|
| train_eval_source_overlap_is_zero | PASS |
| all_optimizer_updates_completed | PASS |
| nonfinite_training_events_are_zero | PASS |
| train_chosen_preference_rate_at_least_75pct | FAIL |
| unseen_chosen_preference_rate_at_least_75pct | FAIL |
| unseen_mean_margin_improved | PASS |
| unseen_target_margin_rate_at_least_50pct | FAIL |
| preferred_likelihood_evidence_is_complete | PASS |
| unseen_mean_preferred_log_prob_non_decreasing | PASS |
| unseen_preferred_likelihood_decrease_rate_at_most_50pct | PASS |

研究邊界：Automatic strict-contract labels measure semantic and surface contract realization, not broad human preference. Failing this gate blocks promotion; passing it would still require independent multi-seed generation and the untouched promotion holdout.
