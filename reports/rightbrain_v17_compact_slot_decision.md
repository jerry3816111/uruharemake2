# RightBrain v17 Compact Slot Decision

## 結論

v17 不建議升版。它證明「把 v16 的正例目標改成 compact runtime payload 再做 SFT」不是有效方向。

## 這次測什麼

- 目的：測試短契約是否比 v16 長 watchlist 更適合小型右腦模型。
- 訓練起點：`uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1`
- 輸出 adapter：`uruha_rightbrain_plan_sft_lora_v17_compact_slot_v1`
- 訓練 epoch：`0.04`
- 訓練資料：主資料 1025 筆，加上 v17 compact slot 補強資料 32 筆。
- payload：不含 `surface_failure_watchlist`，對齊目前預設 runtime。

## 結果

| 指標 | 目前預設右腦 | v17 |
|---|---:|---:|
| raw 候選接受率 | 32/60 (53.3%) | 20/60 (33.3%) |
| 模型實際接管 | 4/22 | 1/22 |
| 最終品質通過率 | 100.0% | 100.0% |
| semantic slot missing | 10 | 18 |
| polite tone drift | 7 | 14 |
| unexpected ascii leak | 12 | 19 |

## 判斷

v17 的最終品質仍是 100%，但這不是 v17 模型變好，而是 deterministic fallback 保住了最後輸出。模型本身的候選品質明顯下降，且左右腦語意槽位保留問題更嚴重。

這代表目前的 32 筆 SFT 補強資料，不管使用長 watchlist 或短 compact payload，都不足以讓 Qwen2.5-7B 右腦穩定學會「不要漏 required_marker_groups」。

## 下一步

下一輪不應繼續做同類 SFT。更合理的工程方向是：

1. 把 required_marker_groups coverage 放到 selector/verifier 的硬檢查中，讓候選缺槽位時永遠不能接管。
2. 對 accepted candidate 做更細的排序，不只看自然度，也要優先看完整語意槽位。
3. 若要再訓練模型，改做 pairwise preference 或 DPO 類資料，讓模型比較「漏槽位」與「完整保留槽位」的差異，而不是只看正例 SFT。

## 研究邊界

這次評估測的是右腦候選生成可靠度，不是 ToMBench 推理能力，也不是完整聊天自然度。v17 的負結果是有效證據：它幫助排除一條不值得繼續投入的訓練路線。
