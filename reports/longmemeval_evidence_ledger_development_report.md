# LongMemEval 記憶證據整合 Development 實驗

- 範圍：`longmemeval_evidence_ledger_development_only_v3`
- 題型：`knowledge-update`
- 題數：18/18
- Development population 覆蓋：18/18 (100.0%)
- 測試集使用：0 題
- 模型 digest：`845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`
- 注意：本機 Qwen judge 只是診斷，不是官方 LongMemEval 分數。

## 結果

| 條件 | 嚴格答案支持率 | 本機診斷 judge | 查詢延遲 | 端到端延遲 | Frame | Note JSON | Quote 來源 | Ledger JSON | Ledger 來源 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| direct_chronological | 72.2% | 88.9% | 67.2s | 67.2s | - | - | - | - | - |
| grounded_notes | 94.4% | 94.4% | 1.8s | 80.7s | 100.0% | 100.0% | 94.4% | - | - |
| versioned_ledger | 94.4% | 100.0% | 16.5s | 95.3s | 100.0% | 100.0% | 94.4% | 100.0% | 100.0% |

- 抽取 facts：39；逐字來源驗證通過：38；拒絕且未進入 ledger：1。
- Ledger 採用/省略已驗證 facts：34/4；coverage=89.5%。此 coverage 僅報告資訊壓縮程度，不作為任意通過門檻；所有實際採用事件仍必須逐字對應來源。
- 僅引號標點等價並回填原文：4 次。
- Note 來源角色回填：1 次；聚焦重試嘗試/採用：21/4 次。
- Note→Ledger 引號/角色回填：2/0 次。
- Ledger 內部一致性修復：5 次；修復規則不讀取 gold answer。
- 衍生數字與逐字來源衝突：2 次；衍生 claim/value 已隔離，不會送進回答 prompt。

## Retrieval 分層

- Top-k 已包含全部 gold sessions：17/18 (94.4%)

| 條件 | 證據已取回題數 | 嚴格答案支持率 | 本機診斷 judge |
|---|---:|---:|---:|
| direct_chronological | 17 | 70.6% | 88.2% |
| grounded_notes | 17 | 94.1% | 94.1% |
| versioned_ledger | 17 | 94.1% | 100.0% |

## 成對差異

| 指標 | Ledger 修正 | Ledger 弄錯 | 淨增 | Exact McNemar p |
|---|---:|---:|---:|---:|
| 嚴格答案支持 | 4 | 0 | +4 | 0.1250 |
| 本機診斷 judge | 2 | 0 | +2 | 0.5000 |

## 因果邊界

三組固定同一模型、同一題、同一批 v2 top-k 記憶與時間順序；唯一變因是檢索後如何整合證據。
Gold answer 只在生成後評分使用，不會放進回答 prompt。
單題獨立執行時，direct 至少需 1 次生成、notes 至少需 7 次、ledger 需 8 次；聚焦重試會增加呼叫，延遲成本必須與正確率一起判斷。
實際單次呼叫最大 token 使用為 17078 / 32768，最小觀察 context 餘裕為 15690 tokens。

結論：完整 development 診斷通過；只授權一次凍結後 held-out test，不授權正式 runtime 修改。
