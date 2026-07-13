# LongMemEval 記憶注意力 Development 消融

## 邊界

- 只測 development：95 題
- test 評分：0 題
- 凍結 Dense top-20 候選；只改排序規則。
- 正式基線重現：通過

## 結果

| Variant | recall all@5 | nDCG@5 | 相對 Dense |
|---|---:|---:|---:|
| dense_chroma | 69.47% | 78.00% | +0.00 pp |
| legacy_wall_clock | 27.37% | 42.64% | -42.11 pp |
| query_time_only | 23.16% | 34.26% | -46.32 pp |
| inverse_distance_only | 33.68% | 46.72% | -35.79 pp |
| normalized_overlap_only | 23.16% | 38.18% | -46.32 pp |
| explicit_self_only | 33.68% | 50.88% | -35.79 pp |
| explicit_self_inverse_distance | 71.58% | 81.08% | +2.11 pp |
| explicit_self_normalized_overlap | 70.53% | 79.63% | +1.05 pp |
| explicit_self_query_time | 33.68% | 49.34% | -35.79 pp |
| explicit_self_inverse_overlap | 78.95% | 83.45% | +9.47 pp |
| explicit_self_inverse_query_time | 66.32% | 74.11% | -3.16 pp |
| explicit_self_overlap_query_time | 58.95% | 62.07% | -10.53 pp |
| all_component_fixes | 72.63% | 75.50% | +3.16 pp |
| runtime_v2 | 78.95% | 83.45% | +9.47 pp |
| generative_agents_normalized | 71.58% | 78.70% | +2.11 pp |

## 判定

development 已完成單變因與交互作用消融；若 test gate 為 true，只允許凍結後做一次 held-out test，仍不能直接升級 runtime。

目前 development 最佳：`explicit_self_inverse_overlap`。
凍結 runtime：`runtime_v2`。
與選定實驗逐題同排序：是。
允許一次 held-out test：是。
