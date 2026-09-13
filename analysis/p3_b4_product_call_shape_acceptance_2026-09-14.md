# P3-B4 isolated product call-shape audit 驗收

日期：2026-09-14（Asia/Taipei）

結論：**PASS（只限 zero-generation call-shape audit）**。

## 實際 before 證據

真實 `uruha_web_ui_product` 在 ephemeral memory 中實例化 brain，使用一個不屬於 P3 smoke 的 synthetic turn 走 `run_turn_debug`。所有模型路徑在 transport 前被拒絕；產品以 deterministic fallback 完成該輪。

觀察到 1 個 native M31 call attempt：

- model：`qwen2.5:7b`，符合 frozen design
- prompt：432 tokens（只留 messages hash，不留 raw text）
- temperature：0，符合
- think：false，符合
- completion cap：280，存在且低於 system per-call cap 320
- 缺少：seed 20260909、top_p 1、num_ctx 8192
- forwarded to transport：false

第一次診斷發現 Chroma 匿名 telemetry 有 2 次 socket attempt，均被 block、實際 network calls 仍為 0。設定 `ANONYMIZED_TELEMETRY=False` 後重跑，socket attempts 降為 0；這個 isolation 修正保留在 worker，沒有修改產品回答邏輯。

## 驗收數據

- artifact：`analysis/p3_b4_product_call_shape_audit_2026-09-14.json`
- real model／network／paid calls：0／0／0
- developer smoke／production DB access：0／false
- brain instantiated：true；ephemeral workspace removed：true
- P3 tests：68 passed
- 相鄰 regressions：32 passed；8 個既有 dependency warnings

## 下一個有限修正

P3-B5 只在實驗 adapter 補齊已觀察到的三個缺失 generation fields，保持原 messages、model、temperature、think 與 cap。完成後先用同一 zero-generation product turn 證明 normalized request 精確符合 frozen design；未通過前不執行 developer smoke generation。

## 證據邊界

這證明產品第一個實際模型呼叫形狀與所需 adapter 差異，不證明後續所有 route、生成品質、比較優勢、Safari、人評或人類反應方程式。因模型回覆被刻意阻擋，之後依回覆條件才會出現的 call shape 仍可能尚未觀察。
