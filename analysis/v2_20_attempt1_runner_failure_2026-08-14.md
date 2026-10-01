# V2.20 Attempt 1 — Runner Failure（2026-08-14）

V2.20 已完成五個 repaired-Uruha checkpoint 的生成，但在組裝 summary 時，沿用的 V2.18 summary 函式要求 `uruha_primary_source_grounded_recall_min`，V2.20 prereg 使用了重新命名的 `repaired_primary_source_grounded_recall_min`，因此以 `KeyError` 結束。

```text
KeyError: 'uruha_primary_source_grounded_recall_min'
run_v2_20_relational_polarity_remediation.py:177 -> base.run_fresh
run_v2_18_fifty_turn_memory_comparison.py:683 -> summarize
```

- 沒有產生 `analysis/v2_20_relational_polarity_remediation_raw.json`。
- 沒有改動 V2.20 locked case、runtime、baseline raw 或 scorer。
- 沒有可評分結果，因此不得稱 pass／fail，也不得引用此次未保存的模型回答。
- 下一版本只修正 prereg／summary 介面相容性；研究變因與成功條件不變。
