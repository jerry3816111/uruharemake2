# P3-B5 frozen adapter normalization 驗收

日期：2026-09-14（Asia/Taipei）

結論：**PASS（只限 zero-generation experimental adapter normalization）**。

## 前後差異

同一個真實產品 native M31 request：

| 欄位 | before | after |
|---|---:|---:|
| model | qwen2.5:7b | qwen2.5:7b |
| temperature | 0 | 0 |
| seed | missing | 20260909 |
| top_p | missing | 1 |
| num_ctx | missing | 8192 |
| think | false | false |
| completion cap | 280 | 280 |
| prompt tokens | 432 | 432 |

adapter 只插入 `options.seed`、`options.top_p`、`options.num_ctx`；messages hash 與 completion cap 保持不變。normalized request 的 7 個 generation checks 全部精確通過，drift count 從 3 降到 0。

## 驗收證據

- artifact：`analysis/p3_b5_product_normalized_shape_audit_2026-09-14.json`
- artifact SHA-256：`df8c6235d6f1034fff09db4956db0d3c84229e688b61fd81f0bc2f2a5182dbb1`
- P3 tests：71 passed
- 相鄰 regressions：32 passed；8 個既有 dependency warnings
- real model／network／paid calls：0／0／0
- production DB／developer smoke access：false／0
- ephemeral workspace removed：true

另有負案例證明錯誤 seed、未知 OpenAI key、錯誤 temperature、缺 cap／超 cap 會在 transport 前拒絕。B3 舊 execution release 因 worker SHA 已改變而不能重跑；歷史 result 改由其保存的 release SHA 驗證。

## 證據邊界

這只證明第一個已觀察 native shape 能被公平正規化，尚未證明真實 provider 回覆後才會觸發的其他 call shape，也沒有回覆品質、基線比較、Safari、人評或優勢結果。
