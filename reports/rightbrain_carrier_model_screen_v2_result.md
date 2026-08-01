# 右腦本機承載模型篩選 V2

**決策：`reject_simple_carrier_swap_and_investigate_role_specialization`**

| 條件 | 嚴格有效 | 原始污染 | 最終語意缺失 | 最終禮貌漂移 | 暖機中位延遲 |
|---|---:|---:|---:|---:|---:|
| Qwen2.5-7B 對照 | 6/10 | 4/10 | 2/10 | 2/10 | 2.26s |
| Qwen3.5-4B | 5/10 | 0/10 | 3/10 | 3/10 | 2.18s |
| Qwen3.5-9B | 3/10 | 2/10 | 2/10 | 7/10 | 3.87s |

## 預註冊門檻

- Qwen3.5-4B：未通過
- 未通過：`strict_valid_minimum, strict_valid_delta, semantic_failure_maximum, semantic_failure_reduction, polite_drift_not_worse`
- Qwen3.5-9B：未通過
- 未通過：`strict_valid_minimum, strict_valid_delta, semantic_failure_maximum, semantic_failure_reduction, polite_drift_not_worse`

## 邊界

V2 只比較現行右腦契約的本機承載能力。即使候選通過，也只可為該模型建立來源獨立 holdout；不代表人格更像、不代表可上線，也不授權訓練。
