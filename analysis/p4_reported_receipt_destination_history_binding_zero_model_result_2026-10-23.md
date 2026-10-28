# P4 接收地點角色：第一次 history 綁定修正的零模型結果

日期：2026-10-23。失敗原件與第一批 strict FAIL 保持在 `analysis/p4_reported_receipt_destination_first_fresh_failure_2026-10-23.md`。這裡只記錄下一批 h0–h3 真 Safari **之前** 的程式及零模型結果，不能當作產品 PASS。

## 改動與反例

修正前，只在本 adapter 改動 `reply` 字面時同步短期 history；即使上游先把字面修正成 source-correct，`accepted_verified + changed=False` 仍可能保留舊 assistant 候選，隨後 pre-episode 拒絕。新邏輯改為以**最後可見句與當輪 assistant row 是否相同**決定是否同步，沿用既有 intent／四類 variant-counter 核驗；已一致時不改計數。前一筆 user row 必須是同 intent；若 `jp_summary` 可用，另核當輪摘要，防止把上一輪同意圖的紀錄改掉。歷史極簡 fixture 沒有該摘要時仍沿用舊相容路徑；因此不能宣稱所有無摘要路徑都有獨立錯輪證明。pre-episode 失配會給非原文原因碼，但仍 fail-closed；來源語法、renderer、guard/episode 門檻、模型呼叫與舊模組不變。

新零模型測試直接重現 `accepted_verified + changed=False + stale history`，現在最後 history＝visible 且四類 counter 各精確移動一次，pre-episode 對同一 visible 放行；已綁定不重複變更，assistant 或 user 列錯 intent、缺 counter、錯 summary、錯 role、缺 history 仍阻止。原有下游篡改、guard digest、保護路由、第三者 profile、graph/entry 契約續跑。

## 驗證與成本界線

- 新＋舊聚焦：**31/31 passed**（0.32 秒）。受影響 P4-Z/D、graph、Web、visible guard 等相鄰集合：**183/183 passed**、9 warnings（105.29 秒）。兩者是本機零模型／契約，不是 fresh generation。
- `py_compile` 通過；`git diff --check` 通過。原 P4-Z SHA `e181d1c...`、D authority SHA `c0e2bef...`、D entry/controller 不變。新 product manifest 列 7 檔；舊 product manifest 留作第一批歷史快照，不覆寫。
- 新增模型呼叫 **0**、網路下載 **0**、正式資料寫入 **0**；零模型測試耗時不等於使用者等待。完整 token/latency 成本要以新隔離真 Safari 輪次另記。已知舊 `test_p4_ab_source_proposition_graph_summary.py` 硬編過時 observatory SHA 的單條失敗未納入本受影響集合，不能稱整 repo 全綠。

**產品狀態：pending。** 必須先 commit/push 精確程式與 SHA，再用事前 h0–h3 新題各一次，逐輪核實回覆、graph、history/guard/raw/episode/DB、日文與成本。即使產品通過，也只支持此受限 source-role 接線修復，不支持廣義人類語用理解、正式同模型優勢、完整 P4 或長期 Goal 完成。
