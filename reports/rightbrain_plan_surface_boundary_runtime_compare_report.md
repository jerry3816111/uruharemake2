# RightBrain Runtime Adapter Multi-seed Promotion Gate

## 結論

本批 actual-model 樣本沒有命中待修正缺陷，因此不能單獨證明修復效果；但兩個 matched seeds 的 raw candidates 完全相同、未新增表面問題且最終品質維持 100%，可作為 runtime 安全非劣證據。

## 控制變因

- baseline adapter: `configured_default`
- candidate adapter: `configured_default`
- comparison mode: `same_adapter_runtime_gate_check`
- seeds: `[20260708, 20260709]`
- candidates per case: `3`
- raw candidates identical: `True`
- raw candidates fully accounted: `True`
- metric gate pass: `False`
- runtime shadow safety pass: `True`
- final quality guard: `True`
- diagnostic only: `False`

## 合計結果

| 指標 | baseline adapter | candidate adapter |
|---|---:|---:|
| raw 候選接受 | 26/60 (43.3%) | 26/60 (43.3%) |
| 模型實際接管 | 3/22 | 3/22 |
| 最終品質通過率 | 100.0% | 100.0% |
| 同版 checker 重評的表面通過率 | 100.0% | 100.0% |

## Rejection Reason 解讀

baseline 與 candidate 使用同一個 adapter，且本報告要求每題 raw candidates 完全相同。因此新增 rejection reason 代表 checker 新抓到的表面問題，不代表模型生成能力退步；是否採用改動由配對後的壞輸出修正數、零新增問題與最終品質防線共同決定。

## 各 Seed

| seed | raw 相同 | baseline surface | candidate surface | 修正 | 新增問題 |
|---:|---|---:|---:|---:|---:|
| 20260708 | yes | 100.0% | 100.0% | 0 | 0 |
| 20260709 | yes | 100.0% | 100.0% | 0 | 0 |

研究邊界：此 gate 在相同 seed、相同候選數下進行配對比較；同 adapter 的 runtime checker 比較還要求每題 raw candidates 完全相同。它只證明已定義表面缺陷的攔截與受保護整合，不等同完整的人類自然度。若提供 curriculum report，會檢查 holdout overlap；有重疊時會阻止升版。
