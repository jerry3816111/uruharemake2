# LongMemEval Evidence Ledger 一次性 Held-out 實驗

- 狀態：`complete`
- 題型：`knowledge-update`
- 完成：54/54 題
- 三組固定同一模型、同一 top-5 記憶與同一生成參數。
- 唯一自變變因：檢索後如何整合跨時間證據。
- 本機 Qwen judge 與嚴格字面支持率都是診斷，不是官方 LongMemEval 分數。

## 結果

| 條件 | 嚴格答案支持率 | 本機診斷 judge | 平均端到端延遲 |
|---|---:|---:|---:|
| direct_chronological | 68.52% | 74.07% | 66.7s |
| grounded_notes | 61.11% | 68.52% | 81.5s |
| versioned_ledger | 68.52% | 70.37% | 95.4s |

## 配對比較

| 比較 | 修正 | 弄錯 | 差異 | 95% bootstrap CI | McNemar p |
|---|---:|---:|---:|---:|---:|
| ledger_vs_direct_strict | 5 | 5 | +0.00 pp | [-11.11, +11.11] pp | 1 |
| ledger_vs_direct_local_judge | 4 | 6 | -3.70 pp | [-14.81, +7.41] pp | 0.753906 |
| ledger_vs_grounded_notes_strict | 7 | 3 | +7.41 pp | [-3.70, +18.52] pp | 0.34375 |

## 決定

一次性 held-out 未通過預先設定的顯著正增益門檻；不得宣稱 evidence ledger 已被外部資料支持，也不得修改正式 runtime。

正式 runtime 修改：**未授權**。
