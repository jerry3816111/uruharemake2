# P3-B6 single-turn real product canary 預註冊

日期：2026-09-14（Asia/Taipei）

## 為什麼先跑一輪

P3-B3 已證明 tokenizer 與兩條 provider usage 在 frozen probe 上逐列相等；P3-B5 已讓真實第一個 native call 的 generation fields 全部符合 frozen design。但模型回覆後才會走到的 call shape 尚未被觀察。直接執行 6 cases × 4 turns 會把整批 developer smoke 當整合除錯資料，因此先用一個事前選定的 product-only canary。

## 事前固定選擇

selection rule 是 frozen source manifest 的第一 case、第一 turn，不依內容或預期結果挑題：

- case：`p3-smoke-need-change-zh`
- turn：`p3-smoke-01-u1`
- input：`最近下班後我總是很煩，什麼都不想做。`
- content SHA-256：`75701b9635c545bb6ec8a36d1f4d26be2981ccc6c21dfc9c0ca7eb65b236d55e`
- runtime source：`datasets/p3_product_canary_source_v1.json`
- future turns／annotations：不包含、不授權

canary config SHA-256：`6dbcf9072592437e06d56f81a60b0199a9edaa3f8ff70759dc081ee99eb91b19`。

## 執行與資源上限

- 只跑 `product_system`，不在此步驟生成 baseline 或評分
- model/digest：`qwen2.5:7b` / `2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730`
- temperature 0、seed 20260909、top_p 1、num_ctx 8192、think false
- 最多 4 provider calls、總 completion allocation 768、每 call 最多 320、turn wall 最多 60 秒
- concurrency 1、OpenAI client max_retries 0、整輪 intent 後不自動重試
- 僅 localhost；ephemeral memory；production DB／confirmation／annotations／external deployment 均禁止
- 保留 visible reply、runtime trace、逐 call exact usage/hash；不保留 raw provider payload

## 成功、失敗與 claim

成功需要非空 visible reply、至少一個且最多四個實際 call、所有 normalized options 與 provider prompt usage 精確相等、budget 無 violation、沒有被產品 catch 掉的 transport rejection、只有 loopback sockets、ephemeral workspace 移除。任一錯誤、timeout、未知 call shape、intent-only 或 usage drift 都保留且不重打。

PASS 只表示一個 developer-smoke product full-turn 可以在公平 gate 下執行；FAIL 則指出實際整合反例。兩者都不構成 baseline 比較、品質分數、holdout、人評、Safari 或系統優勢證據。

## 執行前證據

- preflight：`analysis/p3_b6_product_canary_preflight_2026-09-14.json`，0 generation/network/paid calls
- P3 tests：76 passed
- 相鄰 regressions：32 passed，8 個既有 dependency warnings
- review：同一 Codex task 自審，不是獨立 reviewer
