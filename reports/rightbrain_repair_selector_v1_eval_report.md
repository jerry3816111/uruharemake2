# RightBrain Learned Repair Selector v1 - Held-out Eval

## 一句話結論

測試的是 F 右腦能否在未見過的輸出合約中，從多個回答候選挑出保留左腦語意且無污染的版本；這不會讓 ToMBench 推理本身變強，但可降低正確答案在最終表達時消失的風險。

## 未見合約測試結果

| 方法 | 選中乾淨候選 | 錯選壞候選 | 定位 |
|---|---:|---:|---|
| first_candidate | 9.3% | 90.7% | 不判斷，取第一個 |
| seeded_random | 9.3% | 90.7% | 固定種子隨機 |
| length_only | 0.0% | 100.0% | 只看長度 |
| learned_selector | 100.0% | 0.0% | 本次學習式排序器 |
| deterministic_contract_oracle | 100.0% | 0.0% | 規則 oracle 上限 |

## 模型可信度檢查

- test contracts: 43
- candidate Brier score: 0.207349
- candidate log loss: 0.601441
- semantic drift decoys: 22
- semantic drift decoy rejection: 100.0%
- gate passed: `True`

| 門檻 | 結果 |
|---|---|
| no_contract_fingerprint_overlap | PASS |
| test_gold_selection_rate_at_least_95pct | PASS |
| test_invalid_selection_rate_at_most_5pct | PASS |
| gain_over_first_candidate_at_least_50pp | PASS |
| test_contains_semantic_drift_decoys | PASS |
| test_semantic_drift_decoy_rejection_rate_is_100pct | PASS |
| natural_holdout_contract_overlap_is_zero | PASS |
| natural_holdout_valid_selection_rate_is_100pct | PASS |

## 先前模型真實生成候選

這批包含 11 個未參與 curriculum 的合約、21 個真實候選，其中 5 個違反合約。

| 方法 | 選到有效候選 | 選到無效候選 |
|---|---:|---:|
| seeded_random | 63.6% | 36.4% |
| deterministic_fallback | 100.0% | 0.0% |
| learned_selector | 100.0% | 0.0% |
| deterministic_contract_oracle | 100.0% | 0.0% |

## 重要邊界

- 這是未見合約的 held-out 評測，不是把同一題換順序再測。
- 這是合約特徵的學習式校準器；規則 oracle 仍保留為安全上限與比較基準。
- 語意誘餌由跨合約、低文字重疊方式建立；22/22 是受控測試結果，仍需真實模型候選驗證。
- 通過後只代表值得進入 runtime shadow mode，不代表應立即取代正式回答。
