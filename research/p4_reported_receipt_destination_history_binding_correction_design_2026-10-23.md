# P4 接收地點角色：首批失敗後的第一個前瞻修正設計

日期：2026-10-23。本項只修新 opt-in adapter 的當輪短期 history 綁定，不改舊 P4-Z/D、M31/M32、模型、prompt、來源語義規則、正式資料、baseline 或圖拓撲。舊 r0 產品 strict FAIL 與錯誤收據固定見 `analysis/p4_reported_receipt_destination_first_fresh_failure_2026-10-23.md`，不得重送追分。

## Before 與可反駁原因

Safari r0 在 `emit_response_if_ready → _attach_reply_post_check` 被 `reported receipt destination pre-episode mismatch` 擋下，沒有可見最終句、episode 或 graph。這個錯誤彙集多個 predicate，故不能憑 stderr 指稱唯一原因。零模型重現了一條**確定存在**的失敗路徑：上游已把 `reply` 改為來源一致句、adapter 的 guard 返回相同字串，`trace.changed=False`，但 `RightBrain.speak` 留在當輪 assistant history 的仍是較早候選句；adapter 只在 `visible != reply` 時同步 history，pre-episode 因而擋下。此重現可證程式缺口，不是 r0 全因果鑑定。修正後測試要明確覆蓋這條反例；若 fresh Safari 仍失敗，保留反證，不改稱成功。

## 單一變因與允許範圍

只在既有 full-string source grammar、未保護 route 且最後 guard/來源關係核對後，檢查當輪 `history[-1]` 是否與 **最終 visible** 相同。若不同，沿用 `_sync_selected_short_history` 對當輪 matching intent/assistant row 和四類 variant counters 做精確同步；若已相同則不重複改計數。history 缺失、錯輪、錯 intent、計數不一致仍 fail-closed。`trace.changed` 保留「本 adapter 對進入 guard 的回覆是否改字」語義，不拿它當 history 是否已綁定的代理。pre-episode 需給不含原話的失配原因碼以便定位，不放寬任何核對。異常回滾仍維持。

允許改 `uruha_reported_receipt_destination_relation_p4.py` 與新聚焦 `test_p4_reported_receipt_destination_history_binding_correction.py`；結果、凍結 SHA、`CURRENT_TASK.md` 可記錄。不能改歷史 product SHA、old test/gold、核心 `uruha_brain_mac.py`、其他 adapter、原始 dirty checkout，亦不能靠特定地名／日期答案補洞。這是本產品項第一次有根據的修正批次，若產品仍不過，最多再一次因果明確的修正，之後 `REVIEW_REQUIRED`。

## 事前題本與驗收

新 `datasets/p4_reported_receipt_destination_history_binding_probe_2026-10-23.json` 固定 h0–h3，一個新隔離 session 各送一次、0 retry；兩個不同正例，一個 decision-site 負控，一個第三者引用負控。新日期／物件／地點在寫題前對 repository `rg` 搜尋 0 命中。它們是作者開發題，不是 formal temporal holdout，不能與 r0 或 f2 合併宣稱泛化。r0 只用於零模型回歸，不再當 prospective Web 分數。

1. 先測零模型：舊 r0 shape 的 `accepted_verified + stale short history` 由失敗轉為末端精確綁定；四類計數各減舊增新一次；已綁 history 不改計數；錯 intent／錯 role／缺 history 仍拒絕；後續修改 visible、guard digest 失配、protected route、第三者 profile 抑制仍維持原門檻。P4-Z/D historical SHA 不變。focused、P4-Z/guard/D/graph/Web 相鄰回歸、compile、`git diff --check` 全過才進產品。
2. 產品先核新 0700 私有 root、官方 SHA ONNX 私有獨立 inode、封下載預熱、zero-turn 同 PID ready/planned stop、T0 空 memory/session DB。程式／產品 SHA、測試結果先 commit/push PR #435 exact head，再用**原生 Safari**按 h0–h3 一次一題。每題核真實泡泡、自然日文、來源角色／hearsay、不造日期附著、raw＝guard＝history＝graph utterance＝episode、profile 0、reload、原生節點內容與連線、≤20 秒及實際可得的 model/token/latency 成本。負控不得被新 adapter 誤修或當成本人事實。任一 hard gate fail 整批 strict FAIL，立即停而非重試。
3. 沒有持久 native Safari PNG/AX 仍標 saved-visual FAIL；沒有完整 token ledger 仍標 full-cost pending。零模型、真 Safari、正式同模型對照、人評、holdout 各自分層，不把短句模板修復稱為廣義語義理解或人腦方程式。

停條件：隔離／下載失敗、guard/source/history/episode 任一綁定不明、模型回覆或 UI 錯誤、角色錯、資料污染、超時。保留失敗原件，停止題本且不追分。
