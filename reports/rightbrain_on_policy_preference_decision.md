# RightBrain On-Policy Preference 訓練決策

## 結論

沒有候選通過未見偏好學習 gate；不執行昂貴 runtime holdout，正式右腦維持 V10。

| 候選 | epoch | updates | unseen preference | target margin | mean margin delta | preferred log-prob delta | gradient max | holdout |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| V21 1-epoch | 1.0 | 5 | 40% → 30% | 20% | +0.011435 | +0.004696 | 9.896 | BLOCK |
| V22 3-epoch | 3.0 | 14 | 40% → 40% | 20% | +0.012514 | +0.014739 | 771824.812 | BLOCK |
| V23 prompt-balanced | 3.0 | 14 | 40% → 30% | 20% | -0.005576 | +0.004660 | 4693620.500 | BLOCK |
| V24 balanced + chosen-NLL | 3.0 | 14 | 40% → 40% | 20% | +0.013748 | +0.015020 | 2702753.000 | BLOCK |
| V25 pairwise + chosen-NLL | 3.0 | 13 | 40% → 40% | 20% | +0.011596 | +0.006140 | 376961.438 | BLOCK |

## 2×2 單一變因設計

固定 V10 起點、資料、切分、seed、epoch、學習率、beta 與 batch 設定，只切換 prompt 平衡與 chosen NLL。

| 實驗格 | prompt 平衡 | chosen NLL | unseen preference | target margin | margin delta | updates | 數值完整 |
|---|---|---:|---:|---:|---:|---:|---|
| V22 3-epoch | OFF | 0.0 | 40% | 20% | +0.012514 | 14/14 | YES |
| V23 prompt-balanced | ON | 0.0 | 30% | 20% | -0.005576 | 14/14 | YES |
| V25 pairwise + chosen-NLL | OFF | 1.0 | 40% | 20% | +0.011596 | 13/14 | NO |
| V24 balanced + chosen-NLL | ON | 1.0 | 40% | 20% | +0.013748 | 14/14 | YES |

| 單一變因比較 | 對照 → 處理 | preference 差 | margin gain 差 | 可作因果解讀 |
|---|---|---:|---:|---|
| prompt balance | V22 3-epoch → V23 prompt-balanced | -10.0 pp | -0.018090 | YES |
| chosen NLL | V22 3-epoch → V25 pairwise + chosen-NLL | +0.0 pp | -0.000918 | NO |
| chosen NLL | V23 prompt-balanced → V24 balanced + chosen-NLL | +10.0 pp | +0.019325 | YES |
| prompt balance | V25 pairwise + chosen-NLL → V24 balanced + chosen-NLL | +0.0 pp | +0.002152 | NO |

## 診斷

單獨加入 prompt 平衡後，未見偏好率變化 -10.0 pp，沒有形成正向證據。在 prompt 平衡固定開啟時，chosen NLL 使未見偏好率變化 +10.0 pp，但仍須通過絕對 gate 才能上線。含數值異常候選的比較已排除因果解讀，不用不完整訓練替候選加分。目前證據只支持 chosen NLL 可降低退化風險，不支持這批 pairwise 資料已讓右腦學會穩定偏好排序；正式右腦維持 V10。

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

### V23 prompt-balanced

| 條件 | 結果 |
|---|---|
| train_eval_source_overlap_is_zero | PASS |
| all_optimizer_updates_completed | PASS |
| nonfinite_training_events_are_zero | PASS |
| train_chosen_preference_rate_at_least_75pct | FAIL |
| unseen_chosen_preference_rate_at_least_75pct | FAIL |
| unseen_mean_margin_improved | FAIL |
| unseen_target_margin_rate_at_least_50pct | FAIL |
| preferred_likelihood_evidence_is_complete | PASS |
| unseen_mean_preferred_log_prob_non_decreasing | PASS |
| unseen_preferred_likelihood_decrease_rate_at_most_50pct | PASS |

### V24 balanced + chosen-NLL

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

### V25 pairwise + chosen-NLL

| 條件 | 結果 |
|---|---|
| train_eval_source_overlap_is_zero | PASS |
| all_optimizer_updates_completed | FAIL |
| nonfinite_training_events_are_zero | FAIL |
| train_chosen_preference_rate_at_least_75pct | FAIL |
| unseen_chosen_preference_rate_at_least_75pct | FAIL |
| unseen_mean_margin_improved | PASS |
| unseen_target_margin_rate_at_least_50pct | FAIL |
| preferred_likelihood_evidence_is_complete | PASS |
| unseen_mean_preferred_log_prob_non_decreasing | PASS |
| unseen_preferred_likelihood_decrease_rate_at_most_50pct | PASS |

研究邊界：Automatic strict-contract labels measure semantic and surface contract realization, not broad human preference. Failing this gate blocks promotion; passing it would still require independent multi-seed generation and the untouched promotion holdout.

2×2 邊界：This is a one-seed local 2x2 ablation. Only comparisons with complete optimizer updates and zero non-finite events support a single-factor interpretation; none establish broad human preference.

參考：https://github.com/princeton-nlp/SimPO、https://proceedings.mlr.press/v267/gupta25c.html、https://arxiv.org/abs/2604.15602
