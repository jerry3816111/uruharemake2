# RightBrain V18 DPO 訓練決策

## 結論

不允許進入真實模型 holdout：V18 DPO 未在未見語意家族上形成穩定正偏好，且訓練出現非有限梯度。

| 指標 | 結果 |
|---|---:|
| optimizer updates | 5/6 |
| non-finite skips | 1 |
| max gradient norm | 153581.8 |
| train positive margin | 45.8% |
| train mean margin | -0.010841 |
| unseen eval positive margin | 50.0% |
| unseen eval mean margin | +0.001773 |

## 為什麼不繼續跑 holdout

chosen 平均 23.2 字，rejected 平均 12.8 字，差 10.3 字。
rejected 是刪掉一個語意子句產生，因此 summed-log-prob DPO 把回答長度與品質混在一起；本輪梯度不穩且未見家族只有一半朝正確方向。

## Gate

| 條件 | 結果 |
|---|---|
| dataset_holdout_overlap_is_zero | PASS |
| train_eval_source_overlap_is_zero | PASS |
| all_optimizer_updates_completed | FAIL |
| nonfinite_training_events_are_zero | FAIL |
| train_mean_reward_margin_is_positive | FAIL |
| unseen_eval_positive_margin_rate_at_least_75pct | FAIL |
| unseen_eval_mean_reward_margin_is_positive | PASS |

## 下一方法

length-normalized preference optimization (SimPO-style)：使用 completion 平均 log-prob，分離語意完整度與回答長度，並移除 reference 重算成本。

論文：https://arxiv.org/abs/2405.14734

## 研究邊界

這個 gate 只檢查最佳化穩定性與未見偏好家族；訓練證據不足時會阻止昂貴的生成評測。即使通過，也仍須完成真實模型 holdout 才能升版。
