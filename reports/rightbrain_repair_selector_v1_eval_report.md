# RightBrain Learned Repair Selector v1 - Held-out Eval

## 一句話結論

合成契約 gate 通過，但人類偏好 gate 未通過；selector 能排除明顯污染，不代表會選出更自然的回答，因此維持 observe-only。

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
- gate passed: `False`

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
| human_preference_report_present | PASS |
| human_preference_takeover_recommended | FAIL |

## 先前模型真實生成候選

這批包含 11 個未參與 curriculum 的合約、21 個真實候選，其中 5 個違反合約。

| 方法 | 選到有效候選 | 選到無效候選 |
|---|---:|---:|
| seeded_random | 63.6% | 36.4% |
| deterministic_fallback | 100.0% | 0.0% |
| learned_selector | 100.0% | 0.0% |
| deterministic_contract_oracle | 100.0% | 0.0% |

## 人類偏好 Gate

- strict tasks: 12
- strict candidates: 48
- takeover recommended: `False`

| 方法 | 最高人類分數命中 | 平均自然度 |
|---|---:|---:|
| learned selector | 25.0% | 2.5/5 |
| runtime heuristic proxy | 41.7% | 2.916667/5 |
| S0 full-system candidate | 75.0% | 3.166667/5 |

不可接管：learned selector 在零文字重疊人類盲評中仍落後現行 heuristic 或完整 S0 候選，維持 observe-only。

## 重要邊界

- 這是未見合約的 held-out 評測，不是把同一題換順序再測。
- 這是合約特徵的學習式校準器；規則 oracle 仍保留為安全上限與比較基準。
- 語意誘餌由跨合約、低文字重疊方式建立；22/22 是受控測試結果，仍需真實模型候選驗證。
- 通過後只代表值得進入 runtime shadow mode，不代表應立即取代正式回答。
