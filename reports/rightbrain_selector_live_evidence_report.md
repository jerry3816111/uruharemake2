# RightBrain Selector Live Evidence

## 一句話結論

目前狀態：`waiting_for_live_shadow_data`。這份報告只計入正式 web log 中實際存在的 active shadow trace，不把舊對話或 11 題重播冒充 live 證據。

## 現況

| 指標 | 數值 |
|---|---:|
| logged records | 0 |
| active shadow cases | 0 |
| multi-candidate cases | 0 |
| multi-candidate coverage | n/a |
| disagreements | 0 |
| disagreement rate | n/a |
| learned invalid | 0 |
| selected gate-rejected | 0 |
| visible-output violations | 0 |

## 進入品質比較的門檻

| 條件 | 結果 |
|---|---|
| source_log_has_no_invalid_lines | PASS |
| safety_has_multi_candidate_observations | WAIT/FAIL |
| enough_multi_candidate_cases | WAIT/FAIL |
| enough_disagreements_for_quality_comparison | WAIT/FAIL |
| learned_invalid_count_is_zero | PASS |
| learned_never_selects_gate_rejected_candidate | PASS |
| shadow_never_changes_visible_output | PASS |

quality comparison ready: `False`

## 解讀

- `0` 筆 live shadow 代表尚未收集，不代表 selector 成功或失敗。
- 至少需要 100 筆真實多候選案例與 20 筆分歧，才值得比較哪個回答更自然。
- 任一污染誤選或 shadow 改動可見輸出，都會阻止進入下一階段。
- 下一階段先做自動 pairwise quality comparison；不會立刻要求人工逐題盲測。
