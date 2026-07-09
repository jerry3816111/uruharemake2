# RightBrain v16 Contrast Watchlist Decision

## 結論

v16 不建議升版。它沒有破壞最終品質，但候選可靠度沒有穩定勝過目前預設右腦。

## 這次測什麼

- 目的：測試右腦在看到 `surface_failure_watchlist` 後，是否更能保留左腦語意槽位，並減少不該出現的語言污染或模板化。
- 訓練起點：`uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1`
- 輸出 adapter：`uruha_rightbrain_plan_sft_lora_v16_contrast_watchlist_v1`
- 訓練 epoch：`0.04`
- 訓練資料：主資料 1025 筆，加上 v16 對比補強資料 32 筆。
- token 上限：`1024`。v16 payload 比舊資料長，若沿用 `720` 會截斷答案。

## 結果

| 指標 | 目前預設右腦 | v16 |
|---|---:|---:|
| raw 候選接受率 | 32/60 (53.3%) | 31/60 (51.7%) |
| 模型實際接管 | 4/22 | 5/22 |
| 最終品質通過率 | 100.0% | 100.0% |
| holdout case overlap | - | 0 |
| holdout target overlap | - | 0 |

## 判斷

v16 在 seed `20260708` 變好，但在 seed `20260709` 變差。合併後 raw 候選接受率低於目前預設右腦，因此不應把 v16 設為預設 adapter。

主要問題是 `semantic_slots_missing` 從 10 次增加到 16 次。也就是說，watchlist 訓練沒有穩定解決「右腦漏掉左腦必要意思」這個核心問題。

## 下一步

下一輪不應繼續直接把更長 watchlist 塞進 prompt。比較合理的方向是：

1. 把 watchlist 壓縮成更短的固定欄位，避免右腦被規則文字干擾。
2. 將「語意槽位檢查」放在 selector/verifier 端做硬檢查，而不是期待模型自己讀完長規則後穩定遵守。
3. 用失敗 case 做更小、更乾淨的 contrast pair，專門訓練「同一句話保留所有 required_marker_groups」。

## 研究邊界

這次評估測的是右腦候選輸出的可靠度，不是 ToMBench 推理能力，也不是完整聊天自然度。v16 沒有升版，代表目前證據不足以說它比預設右腦更適合上線。
