# Qwen3 完整 LM 序列長度邊界結果

- 判定：`allocated_length_instability_bracket_localized`
- 邊界：`{"highest_tested_stable_length": 640, "lowest_tested_unstable_length": 704}`
- 測試長度呈單調關係：`True`

| allocated tokens | 判定 | gradient CV | max/min |
|---:|:---:|---:|---:|
| 64 | 穩定 | 0.0 | 1.0 |
| 256 | 穩定 | 0.0 | 1.0 |
| 512 | 穩定 | 0.0 | 1.0 |
| 640 | 穩定 | 0.0 | 1.0 |
| 704 | 不穩定 | 0.28536916467191015 | 2.701567538775215 |
| 768 | 不穩定 | 0.24879348023824654 | 2.2379927503185653 |
| 800 | 不穩定 | 0.2752982013948057 | 2.4107728521605636 |

- 人格訓練授權：`False`
