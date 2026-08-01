# Qwen3 512 / 640 token 梯度重現結果

- 判定：`compact_length_512_does_not_eliminate_drift`

| allocated tokens | 20 次判定 | gradient CV | max/min | hash 相同 |
|---:|:---:|---:|---:|:---:|
| 512 | 不穩定 | 1.9753936999558075 | 431635.0379109821 | False |
| 640 | 不穩定 | 0.10125515822490135 | 1.8316471468849285 | False |

- 512-token 契約建構授權：`False`
- 512-token 正式訓練授權：`False`
- 人格訓練／上線授權：`False`
