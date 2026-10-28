# P4 v2 有界來源送達：事前十輪 Safari 產品驗收

狀態：開發者自製、修後**新前瞻產品診斷**；非 sealed holdout、人評或
同模型強 LLM 公平比較。前兩個十輪案 `紗枝／桑の葉茶`、`結衣／ほうじ茶`
已曝光且 strict 各 `0/1`，不可重跑追分。v2 設計在 commit `fc2e65b`
先凍結，實作層證據見
`analysis/p4_bounded_source_delivery_v2_implementation_2026-10-01.md`。

## 精確問題與單一介入

對 T1「使用者轉述朋友凪紗自己說最愛ルイボス茶」，在 T5 後真重啟、T1
離開最近八輪後，T10 以英文問「我以前說過我愛它嗎；若不是誰說的？」
現行 v2 能否從 T1 持久 episode 的原樣 value 查找，送真 ID/trace 到左腦，
將摘要的 `友達の凪紗` 歸屬於凪紗，最後用自然日文明說是**使用者轉述**、
不冒稱真人偏好，也不說成使用者本人？精確輸入、角色、source-only gold 在
`datasets/p4_bounded_source_v2_fresh_product_probe_2026-10-01.json`。

新 actor/value 建檔前 repo 精確字串查找皆 0-hit；它們不出現在 v2
synthetic `文乃／白桃烏龍茶`、前案或來源 localization map。這仍屬同一
任務族的開發案例，不是跨資料族泛化。T3 是別的飲品的例文，T6 是本人
選的別的飲品，T7 是親戚事件；不得把它們改成 T1 的來源或 T10 的答案。

## 操作、凍結與成本

先 commit 本 plan/dataset 及實作，再記完整 SHA-256、commit、entry、overlay、
launcher、設計檔 hash 到 freeze JSON，且在第一個真產品輪次前核對。之後
不改十輪、答案、門檻、程式，不 retry。`p4_past_source_safe_isolated_product_launcher.py`
先 `check`，後以 `run --python .venv/product_checks/bin/python --port 7892
--preserve-runtime` 開 launcher-owned `0700` 系統 temp root。Safari 送 T1–T5
exact input，停舊 PID／驗 port 關；同一 root 用 `--runtime-root ...
--reuse-runtime --preserve-runtime` 新 PID 開 T6–T10。只碰新建 Safari tab，
不碰正式 DB、原始 dirty checkout、既有 tab、外部部署或付費 API。

每輪記完整已完成可見句、等待秒、session/PID、episode ID、graph 同輪。
T10 記 lookup status/elapsed、matched IDs、`passed_to_leftbrain` 新 channel、
source actor/value、M22 route、plan、final node/hash，和 T1 持久 ID 對上；
原樣隔離 JSONL hash 留存。全產品模型 call/token/cost 若未暴露就記
`unavailable`，不得把 overlay `0 extra model calls` 當全系統 0。
每輪 `≤20s` 是單獨成本門檻，不能拿較快棄答當品質勝利。

## 事前判準與結果邊界

T10 strict PASS 必須同時有：`lookup=complete`，T1 原樣 source ID 經
`bounded_source_lookup` 真送達（不是只在 candidate pool）；`resolved_third_party_source`
且唯一 actor=凪紗、value=ルイボス茶；M22 `factual_or_memory` 與
deterministic route matched；自然日文最終句清楚是使用者先前轉述凪紗說，
不把喜好歸使用者或聲稱真人已驗；lookup→source→plan／utterance graph
和可見 final、persisted T1 ID 完全一致。只說「不知道」為 partial，但
strict FAIL；來源在圖上卻沒進可見句也 FAIL。

Lifecycle 要 10/10 exact turns 有 final＋graph、10/10 episode persisted；T5→T6
舊 process 真退出、新 PID/session、同隔離 DB。逐輪另列非 T10 日文／語義、
profile owner、latency 缺陷，不混算 strict。任何失敗原樣保留並從 retrieval、
source parsing、route/plan、surface、runtime 最早失真層分析，不用本案重跑
或改門檻。此為該 P4 工作項最後一個有根據修正批次；若仍失敗，設
`REVIEW_REQUIRED` 等設計審查。通過也只支持這個限定來源問答產品案例，
未授權同模型比較、人評、正式 temporal holdout、VRM/tool 或「理解人類」。
