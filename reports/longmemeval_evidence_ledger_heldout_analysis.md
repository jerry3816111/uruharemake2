# LongMemEval Evidence Ledger Held-out 事後審計

## 結論

- Direct 嚴格支持率：68.52%
- Ledger 嚴格支持率：68.52%
- 配對結果：修正 5 題、弄錯 5 題、淨增 +0 題、McNemar p=1.0000。
- 結論：未支持 ledger 優於 direct；正式 runtime 不修改。

## 17 個 Ledger 嚴格失敗的層級診斷

| 可觀察邊界 | 題數 |
|---|---:|
| Top-5 未取回全部 gold session | 2 |
| Notes 未保留 gold 支持值 | 9 |
| Ledger 未保留 notes 支持值 | 0 |
| Ledger 有支持值但回答未說出 | 6 |

此分層使用凍結 strict scorer，只能定位可觀察邊界，不能當作因果證明。

## 操作分組

| 操作 | 題數 | Direct | Notes | Ledger | Ledger 修正/弄錯 |
|---|---:|---:|---:|---:|---:|
| compare | 2 | 100.0% | 50.0% | 100.0% | 0/0 |
| count | 24 | 62.5% | 58.3% | 70.8% | 2/0 |
| locate | 4 | 100.0% | 50.0% | 25.0% | 0/3 |
| lookup | 22 | 72.7% | 68.2% | 72.7% | 2/2 |
| yes_no | 2 | 0.0% | 50.0% | 50.0% | 1/0 |

## 來源完整性

- 模型抽出 119 facts；接受 117，拒絕 2 個未逐字落地 fact。
- 實際進入 ledger 的事件來源驗證率：100.0%。
- 但預先設定的原始抽取全通過 gate 仍失敗，不能事後改門檻翻案。

## 評分邊界

- Strict scorer 對同義格式可能 false negative。
- 本機 Qwen judge 對矛盾推論可能 false positive。
- 兩者均未提供 ledger 優於 direct 的可靠證據。

## 下一輪

1. 在新的 development cases 做 session 內 utterance-level attention。
2. 加入 count/location/time/yes-no typed answer contract。
3. 新 held-out 前先凍結並校準 scorer；這 54 題不得再作調參後泛化證據。

Ledger 在一次性 held-out 沒有勝過 direct；不得上正式 runtime，也不得使用這 54 題調參後重新宣稱泛化。下一輪只能在新的 development cases 驗證 session 內注意力與 typed answer contract。
