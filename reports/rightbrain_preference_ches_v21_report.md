# RightBrain V21 Preference Pair CHES 診斷

## 結論

這份報告先量化偏好 pair 的 likelihood-displacement 風險，不訓練新 adapter。

| 資料 | pairs | CHES median | CHES mean | 高風險 quartile |
|---|---:|---:|---:|---:|
| v18_deleted_clause | 32 | +122.812500 | +305.308167 | 8 |
| v20_length_matched | 32 | -699.441406 | -637.295044 | 8 |

較高 CHES 代表 chosen/rejected 在目前模型的 hidden geometry 中更相似，依論文是 likelihood displacement 風險訊號；它不是自然度分數，也沒有跨模型通用的絕對門檻。

V20 的 median CHES 低於 V18，且在僅 8 組可配對未見資料中，CHES 與 preferred log-prob 變化的 Pearson 只有 +0.131；本地證據不支持用 CHES 單獨解釋 V20 退步。

## V20 未見 Pair 的訓練變化

| 指標 | 值 |
|---|---:|
| 可配對 rows | 8 |
| preferred likelihood 下降 | 7 |
| mean preferred log-prob delta | -0.010851 |
| CHES vs preferred delta Pearson | +0.1306 |

## 各資料最高 CHES Quartile

| dataset | id | source | CHES |
|---|---|---|---:|
| v18_deleted_clause | rb_semantic_preference_v18_0006 | v18_manga_fragment_source | +4085.042969 |
| v18_deleted_clause | rb_semantic_preference_v18_0013 | v18_sleep_debt_boundary | +3768.578125 |
| v18_deleted_clause | rb_semantic_preference_v18_0014 | v18_sleep_debt_boundary | +3023.652344 |
| v18_deleted_clause | rb_semantic_preference_v18_0026 | v18_absurd_train_moon | +1777.855469 |
| v18_deleted_clause | rb_semantic_preference_v18_0016 | v18_sleep_debt_boundary | +1627.468750 |
| v18_deleted_clause | rb_semantic_preference_v18_0005 | v18_manga_fragment_source | +1306.417969 |
| v18_deleted_clause | rb_semantic_preference_v18_0020 | v18_private_school_topic | +1015.054688 |
| v18_deleted_clause | rb_semantic_preference_v18_0015 | v18_sleep_debt_boundary | +841.513672 |
| v20_length_matched | rb_hard_negative_preference_v20_0031 | v20_uncertain_weekend_plan | +3964.593750 |
| v20_length_matched | rb_hard_negative_preference_v20_0022 | v20_throat_coffee_update | +2714.666016 |
| v20_length_matched | rb_hard_negative_preference_v20_0008 | v20_manga_fragment_source | +2501.695312 |
| v20_length_matched | rb_hard_negative_preference_v20_0020 | v20_private_school_topic | +1424.074219 |
| v20_length_matched | rb_hard_negative_preference_v20_0032 | v20_uncertain_weekend_plan | +1112.550781 |
| v20_length_matched | rb_hard_negative_preference_v20_0014 | v20_sleep_debt_boundary | +1039.605469 |
| v20_length_matched | rb_hard_negative_preference_v20_0003 | v20_group_reply_delay | +908.781250 |
| v20_length_matched | rb_hard_negative_preference_v20_0016 | v20_sleep_debt_boundary | +459.953125 |

## V21 資料准入規則

- 使用產生資料的同一個 adapter 計算 length-normalized CHES。
- 保留原始 CHES 與資料集內 percentile，不設定未校準的絕對 cutoff。
- 訓練前未見 pair 偏好正確率若已是 100%，不得單獨作為 promotion gate。
- 未見 mean preferred log-prob 不得下降，且 preferred likelihood 下降的 pair 不得超過一半。
- 優先收集與 promotion holdout 分離的 V10 實際錯誤候選，再以 CHES 排序審核。
- 任何訓練仍須通過雙 seed actual-model holdout 才能升級。

研究邊界：CHES is a model-dependent risk diagnostic. This small local comparison cannot reproduce the paper's large-scale causal result or establish a universal filtering threshold.
