# P4 第三者陳述 speech-act：修後前瞻 Safari 產品驗收

狀態：2026-10-17，**未送 Safari／未做真實模型生成**。五個逐字
input、語義 gold、20 秒上限、0 retry、T3 後同庫重啟已事前寫入
`datasets/p4_source_bound_third_party_statement_act_fresh_probe_2026-10-17.json`。
在寫入前以 repository `rg -F -l` 查五句全文均無命中；它們仍是
開發者撰寫，非獨立 holdout。舊兩批曝光題與失敗結果不改、不重播。

單一變因與邊界見 `research/p4_source_bound_third_party_statement_act_plan_2026-10-17.md`。
先做零模型來源／M31／M32／產品鏈測試，再做受影響相鄰回歸、
Python compile、launcher 0-turn check。這些通過只是送模型的前提。
首輪前需以 Git commit 固定程式、測試、本資料／plan、SHA-256
manifest，核對所有 hash；看到任何回覆後不可改門檻或答案。

使用全新 0700 私有 root、單一 localhost listener、正式 DB 不碰；
controller `start` 後另以 `verify-ready` 確認同一 final Python PID、
loopback 和 HTTP 200，再開新 Safari 測試分頁。每輪 exact input
只按一次，前後各用隔離 snapshot 留 profile row-ID／turn_episode
集合差；逐輪核 raw JSONL、真正 selected plan、M31 的來源約束
trace／response、M32 是否奪權、profile owner、Safari 泡泡與 graph
utterance 一致。T1/T3/T5 要保留第三者、物品及肯定陳述，不能
變問句；若模型本來就忠實，可不觸發 repair，但不能假稱 guard
被實際用到。T2 本人來源快路不退化，T4 真問句不得被當成已知
第三者事實。profile row-ID 差應為 `[0,1,0,0,0]`，五個不同
episode；每輪 user wait ≤20.0s，包括冷啟。記實際模型呼叫數、
完整可得 token、延遲；缺值 unavailable。

T3 後恰一次 planned stop，需原 PID 退出且 port 無 live LISTEN，
原 stop metadata 真記 planned=true；同一 root/DB 只重啟一次，
核新 PID/run ID/session、同庫 snapshot ID 不變，再送 T4/T5。
T5 後 planned stop、隔離 root 保留。服務意外消失、額外重啟、
任何輪未送或任一語義／成本／記憶／選路／圖／安全條件失敗，
本批 strict FAIL，曝光題不重送。Safari 截圖若未留存，不能把
AX 觀察稱封存影像。

若本第二批 strict FAIL，依工作流程交 `REVIEW_REQUIRED`，以
最小反例和單一變因取捨供下一次設計審查，不另造第三批追分。
即使全過，也只支持有界第三者直接陳述的產品忠實性，不支持
一般人類語用理解、強 LLM 對照優勢、人評、正式 temporal
holdout、VRM/tool 完整交付或生物人腦方程式聲稱。
