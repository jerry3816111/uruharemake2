# P4 來源問答：修後全新隔離 Safari 診斷

狀態：開發者自製、事前定稿的**前瞻產品診斷**，不是獨立 sealed holdout、
同模型公平 LLM 對照或真人評分。舊 `p4_current_relation_recall_probe` 十輪已曝光且
T10 嚴格失敗，不重跑追分。修正版本是 commit `4cfe082` 的 additive
`uruha_web_ui_product_p4_past_source.py`，只檢驗已設計的**受限**來源問答介面。

## 問題與唯一介入

將先前有來源的第三者自述送入當輪已傳給左腦的持久記憶後，產品能否在
跨 process/session 重啟、T1 脫離最近八輪後，用英文詢問過去第一人稱最愛時，
以自然日文回答「使用者先前**報告**結衣本人說喜歡ほうじ茶」，而不改成
「使用者自己喜歡」、不從當前 query 猜人名？介入是已提交的 bounded
query→source→actor/value→route/plan→final surface/graph 整體介面；不把
一個 gate 的結果拆稱多個獨立因果增益。

精確十輪與答案 source-only 欄位在
`datasets/p4_past_source_fresh_product_probe_2026-10-01.json`。新人物/值
`結衣／ほうじ茶` 不等於已曝光 before `紗枝／桑の葉茶` 或單元正例；來源改成
日文、最後 query 改成英文。T3 引用別的飲品，T6 是使用者自己的不同飲品，
T7 是老師的單次行為。這仍是開發者構造且同一任務族的診斷，不是獨立泛化。

## 事前操作與凍結

1. 在任何真實產品輪次前 commit 本 plan/dataset，記完整 SHA-256 和 commit，
   與 `4cfe082` entry/overlay/launcher 的檔案 hash 綁成 freeze artifact；之後
   不改 exact turns、答案、門檻或程式去重跑本案。
2. 對 `p4_past_source_safe_isolated_product_launcher.py` 執行 `check`，再用同
   launcher `run --python .venv/product_checks/bin/python --port 7892
   --preserve-runtime`；不傳 root，由 launcher 產生有 manifest 的 `0700`
   系統 temp 隔離 root。Safari 送 T1–T5 exact input。確認舊 PID 退出且
   port 關閉；再用**同一精確 root** 加 `--runtime-root ... --reuse-runtime
   --preserve-runtime` 啟新 PID，Safari 送 T6–T10。0 retry、0 人工 seed，
   不碰正式／原始 dirty DB、外部部署、付費 API 或既有使用者 Safari tabs。
3. 每輪保存原樣可見句、end-to-end 秒數、session/PID、最後儲存 episode ID
   和 runtime graph 是否同輪可見。T10 另查 route/plan、`past_statement_source_answer_p4`
   node/source trace/actor/status/final hash，和隔離 DB 的 T1 episode 對上。
   全產品 model call/token/cost 欄位若不存在則記 `unavailable`，不填 0。
   初始繼承 import preflight 不完全 sandbox，只主張 launcher 新 entry probe
   與 server 的已驗證邊界。

## 判準、失敗與 claim 邊界

T10 strict PASS 同時要求：`resolved_third_party_source`、source memory ID
為真正 T1 持久 episode、source trace ID 確實在 T10 `passed_to_leftbrain`、
route `factual_or_memory` 且 contract matched、最終句和 graph node 一致、
明確說是**使用者先前轉述**結衣說喜歡ほうじ茶（不冒稱系統驗證真人發言）、
不把喜好放到使用者本人，且人工讀起來是自然日文。只說沒資料、不說來源，
或圖有答案但可見句不同，均 fail。

Lifecycle：10/10 exact turns 有同輪可見句和 graph，10/10 episode persisted；
T5→T6 舊 process 確實消失、新 PID/session、同隔離 DB；非 T10 也逐輪人工
標明可見語義／日文缺陷。成本門檻每輪 `≤20s`，另列超時，不用成本失敗
抹消品質結果。無真 Safari 圖就保持 Safari pending，不能拿假記憶 unit
或 localhost API 代替。若某輪失敗，保留原樣並繼續其餘輪定位，絕不 retry。

即使 T10/整體通過，只能說此受限問句族在這一個新的隔離產品案例有實測
支持；不代表一般人類理解、同模型強 LLM 優勢、正式 temporal holdout、
人評或 VRM/Function Calling 全產品就緒。若失敗，固定原始結果並分
retrieval、source parsing、route/plan、surface、runtime 五層找最早失真；
最多再有一個有根據的前瞻修正批次，不能重用此案例作新 confirmation。
