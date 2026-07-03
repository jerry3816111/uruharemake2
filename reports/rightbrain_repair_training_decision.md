# RightBrain Repair Training Decision

## 結論

這一輪沒有得到可上線的 repair adapter。正式 runtime 繼續使用原本穩定 adapter，且 `URUHA_RIGHT_BRAIN_MODEL_REPAIR_ENABLED` 預設維持關閉。

## 為什麼值得保留

- 建立 720 筆跨 18 類對話情境的通用 repair curriculum。
- 11 題 holdout 的輸入文字、完整契約指紋、標準回覆重疊都是 0。
- 訓練與 runtime 使用相同 repair prompt、task 與 feedback schema。
- 被拒絕的草稿沒有放進訓練 prompt，模型不能直接照著錯誤答案改字。
- 訓練器現在會在 optimizer update 前拒絕非有限梯度，並分開記錄 loss 與 gradient 異常。

## 實際嘗試

| 嘗試 | 設定 | 數值結果 | 行為結果 | 決定 |
|---|---|---|---|---|
| 高訊號初試 | v8 起跑；repair-only；`lr=3e-7`；`eps=1e-6` | 第 17-19 步連續 NaN，未儲存 adapter | 未評估 | 停止 |
| v11 低學習率 | v8 起跑；720 rows；120 microsteps；15 updates；`lr=1e-7` | non-finite 0；eval loss 3.0157 | raw 40%→30%；repair 0/6→0/7 | 不上線 |
| v12 guarded | v8 起跑；720 rows；80 microsteps；10 updates；`lr=3e-7`；`eps=1e-5` | loss/gradient non-finite 都是 0；eval loss 3.0208 | raw 40%→30%；repair 0/6→0/7 | 不上線 |

## 可以主張什麼

提高 AdamW epsilon 與加入 gradient guard 解決了 repair-only 微調的數值崩潰，但「同一個 v8 LoRA 進行少量 repair SFT」沒有形成可用的失敗後修正能力，也使初次候選可靠度下降 10 個百分點。

## 不能主張什麼

- 不能說 repair 訓練提高右腦品質。
- 不能因 final pass 仍是 100% 就說模型成功；100% 來自嚴格 gate 與 deterministic fallback。
- 不能開啟 runtime repair，因為修正成功率仍是 0% 且增加延遲。

## 下一個工程方向

下一輪不再調同一條 LoRA 的學習率。應將「第一次生成」與「失敗後修正」拆成可獨立切換、獨立訓練、獨立消融的 policy，再用同一組 holdout 比較：

1. v8 generation adapter + 無 repair。
2. v8 generation adapter + prompt-only repair。
3. v8 generation adapter + 獨立 repair adapter。

只有第三組同時提高 repair success、保住 raw acceptance、final gate 與延遲門檻，才允許上線。
