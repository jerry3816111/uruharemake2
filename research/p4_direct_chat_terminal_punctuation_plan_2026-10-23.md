# P4 direct-chat 已選核心的句末標點保全：前瞻單變因計畫

本計畫在本項 code／新題模型生成前凍結。d1 是 developer-authored、off-gate Safari 輪次：Tpost autonomous tick1，不能作產品通過證據，也不得重播。它仍提供一個可核對的 before：compact 選 `頑張って！`，legacy `direct_chat_answer` 表面拼成 `頑張って！。そのくらいでいいだろ。`，語言 guard 因畸形標點改為與明示鼓勵不相符的 `support` fallback。原始 d1/c0/d0 判定不變。

## 唯一變因與邊界

- 只改 `uruha_brain_mac.py` 的 `_speech_plan_variants` 內 `direct_chat_answer` 預設分支如何把既有 `core_message_jp` 與固定尾句接合：核心已以 `。！？` 結束就不再插一個 `。`；沒有句末標點時維持原字節。不得改核心、候選選擇、persona 字句、M29/M33/M18/M21、P2 expression eligibility、M39、語言 guard 或 scene fallback。這是機械性的標點修復，**不是**承認固定尾句或核心內容符合使用者期待。
- 新作者題只在 `datasets/p4_direct_chat_terminal_punctuation_probe_2026-10-23.json`。它與先前 c/d 題逐字不同，但結構接近 d1，只是診斷題、不是獨立 holdout，也不能用於同模型優勢比較。零模型測試可注入 developer-authored core；不得把這些 fixture 寫入 prompt、正式記憶或標註資料。
- 只允許上述 core 檔、新聚焦 test、本計畫／dataset／SHA、後續結果報告與 `CURRENT_TASK.md` 改動。私有 DB、原始 dirty checkout、凍結 c/d 題、正式資料、外部部署不碰。

## 預註冊判定

1. Before：對 `！`、`？`、`。` 結尾 developer core，舊分支確實產生多餘 `。`；無標點 core 與特殊 topic 分支記錄原字節。先保存失敗，不以寬鬆 regex 掩蓋。
2. After zero-model：三種句末標點均保留 core 原字節作前綴，恰接既有尾句且沒有 `！。`／`？。`／`。。`；無標點 core 與 topic 特例保持原輸出。直接送入 `！。`／`？。` 的 guard 仍 fail closed，不可因修拼接而放寬。特別測 `support + direct_chat_answer`：它是 d1 實際交集，P2 原本排除 `support`，所以此分支**預期**變化；其他 protected dialogue acts、quoted／identity 及 P2 已接管的 compact 路徑不退化。每個測試明列改動前後通過數。
3. 新隔離真 Safari 僅在前項通過、source freeze 與 product SHA 完成後最多送新題一次／0 retry。新 0700 root、官方 ONNX 私有離線預熱、same PID ready、空 DB；Safari Tpre 複本在 Send 前解析同 PID/session/`memory_db`/reset0/tick0/finish0，Tpre→click 目標 ≤10 秒，Tpost 仍須同 PID/session/DB/reset0/tick0/finish1，不能因背景 `writes=0` 放行或重送。click-time 非原子收據限制仍列明。圖核 compact route、selected core、表面、guard/M39/final/episode、source、token/vector/延遲；原生 PNG/AX 未可保存就 visual gate FAIL。
4. 機制 PASS 只在真輪**實際選到句末標點 core**、表面沒有混合雙標點、guard 沒因標點走 fallback、final 保留該 core 時成立；若真輪不選此型 core，記 `not_exercised`。可見品質是另一個 hard gate：自然短日文、承接可觀察進展、鼓勵而不編心理／睡眠背景。即使標點修好，核心若只說泛泛 `頑張って！` 或尾句使人感到貶低，品質仍 FAIL，不能拿機制通過抵銷。任何 Tpost tick 漂移＝整輪產品 strict FAIL，僅能保留 off-gate trace。
5. 此項不增加模型呼叫，zero-model 成本 0 provider token；真輪最多 3 generations／2000 provider tokens／20 秒 user wait。缺 ledger、digest 或 source/route mismatch 停；超額記 fail。正式 human preference、temporal holdout、同模型強 LLM 比較、VRM／Function Calling 統一入口及完整方程式均不由本項證明。最多兩個有根據的修正批，仍失敗就 `REVIEW_REQUIRED`，不改舊題／舊 gate 追分。

流程：source-only plan／dataset／SHA 先 commit/push/PR 核對 → failing zero-model before → 單行實作與聚焦／受影響測試 → product SHA／scoped commit/push → 新隔離 Safari 或保存 gate FAIL → 成本／圖／失敗分析 → result／task card／Git review／PR 核對。
