# Qwen3 Metal free-cache 梯度重現結果

- 判定：`disabling_metal_free_cache_does_not_eliminate_drift`

| cache mode | 十次重複判定 | gradient CV | max/min |
|:---|:---:|---:|---:|
| default_cache | 不穩定 | 0.11294782346433253 | 1.3697697374625897 |
| disabled_cache | 不穩定 | 0.2201410699770045 | 2.4508531448525908 |

- cache-disabled 正式訓練授權：`False`
- 人格訓練授權：`False`
