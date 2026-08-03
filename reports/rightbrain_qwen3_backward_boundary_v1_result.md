# Qwen3 反向傳播邊界定位結果

- 判定：`tied_lm_head_backward_is_sufficient_to_reproduce_drift`

| 反向路徑 | 18 次判定 | gradient CV | max/min | hash 相同 |
|:---|:---:|---:|---:|:---:|
| full_chain_control | 不穩定 | 1.5240853306395812 | 531358.5110362535 | False |
| head_boundary_vjp | 不穩定 | 1.8836255554950305 | 14591.549879588312 | False |
| transformer_boundary_vjp | 穩定 | 0.0 | 1.0 | True |

- 正式訓練／人格訓練／上線授權：`False`
