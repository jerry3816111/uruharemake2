# Qwen3 bfloat16 / float16 梯度重現結果

- 判定：`float16_does_not_eliminate_gradient_drift`

| base compute dtype | 十次重複判定 | gradient CV | max/min |
|:---|:---:|---:|---:|
| bfloat16 | 不穩定 | 0.06285123479328746 | 1.2007968997419864 |
| float16 | 不穩定 | 0.02901573267069816 | 1.1011484135547647 |

- float16 正式訓練授權：`False`
- 人格訓練授權：`False`
