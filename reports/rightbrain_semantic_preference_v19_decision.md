# RightBrain V19 SimPO 訓練決策

## 結論

不允許 V19 進入真實模型 holdout：SimPO 未形成穩定的未見家族偏好改善。

| 指標 | 結果 |
|---|---:|
| optimizer updates | 6/6 |
| non-finite skips | 0 |
| max gradient norm | 9106.717 |
| train chosen preference | 87.5% |
| unseen eval chosen preference | 100.0% -> 100.0% |
| unseen eval mean margin | +2.654062 -> +2.630264 |
| unseen target margin rate | 100.0% |

## 診斷

刪句 rejected 對 V10 已經太容易：訓練前 unseen chosen preference 就是 100%，訓練後平均 margin 還略降，因此不能把穩定訓練誤報成泛化提升。

下一資料改動：建立長度相近、文法自然、只替換一個必要語意槽位的 hard negatives，避免用刪句產生可由長度直接識別的 rejected。

## Gate

| 條件 | 結果 |
|---|---|
| train_eval_source_overlap_is_zero | PASS |
| all_optimizer_updates_completed | PASS |
| nonfinite_training_events_are_zero | PASS |
| train_chosen_preference_rate_at_least_75pct | PASS |
| unseen_eval_chosen_preference_rate_at_least_75pct | PASS |
| unseen_eval_mean_margin_improved | FAIL |
| unseen_eval_target_margin_rate_at_least_50pct | PASS |

## 研究邊界

這是訓練穩定性與未見 synthetic preference family 的前置 gate；即使通過也不代表 adapter 可上線。
