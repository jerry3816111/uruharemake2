# Qwen3 有效 token LM head VJP 結果

- 判定：`projecting_ignored_positions_is_sufficient_to_reproduce_drift`
- loss 語意等價門檻：`True`

| mask / head 路徑 | 18 次判定 | gradient CV | max/min | hash 相同 |
|:---|:---:|---:|---:|:---:|
| dense_mask_after_loss | 不穩定 | 1.93406127452774 | 13901.319245740899 | False |
| dense_gather_before_loss | 不穩定 | 1.783109172264478 | 10944.550021760306 | False |
| active_gather_before_head | 穩定 | 0.0 | 1.0 | True |

- 正式訓練／人格訓練／上線授權：`False`
