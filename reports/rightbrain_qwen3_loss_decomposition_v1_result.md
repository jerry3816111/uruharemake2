# Qwen3 loss 分解梯度定位結果

- 判定：`drift_precedes_loss_decomposition_or_is_in_shared_model_backward`

| loss mode | 18 次判定 | gradient CV | max/min | hash 相同 |
|:---|:---:|---:|---:|:---:|
| masked_cross_entropy | 不穩定 | 2.3028678867461156 | 494111.7716988456 | False |
| target_score_only | 不穩定 | 0.2305138561178652 | 4.32116324998502 | False |
| logsumexp_only | 不穩定 | 1.7447102514332615 | 278972.3369253028 | False |

- 正式訓練／人格訓練／上線授權：`False`
