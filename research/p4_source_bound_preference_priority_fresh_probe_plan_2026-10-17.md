# P4 本人偏好快路競權：修後新五輪 Safari 產品驗收契約

狀態：2026-10-17，**尚未送 Safari／真實生成**。與舊五輪失敗資料分開；
exact input/gold 在
`datasets/p4_source_bound_preference_priority_fresh_probe_2026-10-17.json`，
程式範圍與單一語義變因在
`research/p4_source_bound_preference_priority_repair_plan_2026-10-17.md`。
寫入新資料前對五句全文及四個物品值以 repository `rg -F -l`
查無命中（exit 1）；這只是目前 repository 搜尋範圍，不是外界獨立
holdout。問句測的是既有優先權負控制，語用類型已在先前開發曝光。

本次唯一語義介入：已准入、完整單句、日文本人肯定物品偏好若原
M29 原本要求模型語義投影，先讓既有 rule fast path 取得選中機會；
第三人稱／問句等依原路。M31/M32 本體、writer、人格與 final
guards 不改。listener/TIME_WAIT controller 修正是必要操作前提，
其 unit/inert 證據單列，不算語義 lift。先跑 0-generative-model
契約與受影響回歸、隔離入口 0-turn；失敗不可送新五輪。

首輪前凍結 code、tests、資料、gold、此計畫、上層 manifest 和
隔離 launcher/controller 的 SHA-256 manifest，提交 Git 後核對，
不在看輸出後補規則或改門檻。全新 controller root 必須 0700、
正式 DB／原始 dirty checkout／無關 output 不碰；服務只能 localhost
`127.0.0.1:7894`。一次 `start --mode product --python
.venv/product_checks/bin/python` 後，獨立呼叫 `verify-ready`，需
唯一 PID 的 final Python／loopback listener／HTTP 200 前後同源，
再在 Safari 開**新的**測試 tab。原有 Safari tab 不關。

五輪 exact input 依資料集順序各一次、0 retry；每輪 before/after
用 `p4_preference_fallback_snapshot.py --runtime-root <新隔離 root>
--save before-tN|after-tN` 留 0600、不可覆寫的 profile row-ID／metadata
和 turn_episode ID；snapshot 只呼叫 Chroma 查詢 API，不能聲稱
DB bytes OS 級唯讀。核 raw JSONL、真 selected plan、M29 priority、
M31、M21、owner admission、fallback／graph utterance 與 Safari 泡泡。
T1/T3/T5 真 selected `chat`＋fallback，M29 priority status 對應，
M31 不完成模型呼叫，M21 general planner call=false；profile 增量
`[1,0,1,0,1]`，只寫三個本人值。T2 不得誤准入、不得把朋友偏好
寫成本人或在可見回覆省略朋友歸屬；T4 `ask_like_me` 仍優先。
五輪 bubble 都自然日文、逐字等於 graph/raw utterance，不能
說成「她本人」、捏造私事、倒出 debug 或承諾未觀察記憶寫入。
每輪 `user_wait_seconds ≤20.0`，T1 也不豁免冷啟；先前 79.3MB
Chroma ONNX 下載可能再現，不能事後用熱路徑抹除。token／價格
缺欄記 unavailable。量測總啟動時間、M31／M21 呼叫、每輪等待，
但不得把舊批不同句子秒數差當因果加速。

T3 後恰一次 controller planned stop，核舊 PID 退出、全埠沒有
LISTEN；只有原 `stop.json` 真記 planned=true，才可用同一私有
root/DB `start --reuse-runtime-root ...`，核新 PID/run ID/session 和
HTTP/loopback owner，再送 T4/T5。controller 若拒 stop/reuse、
服務意外死掉或 status 歸屬不明，**程序 strict FAIL**，原輪不重送、
後輪不造。正負結果均留 raw JSONL、DB、快照、stop/start metadata
SHA-256；T4/T5 未測就寫未測。T5 後 exact stop，保留隔離 root，
不以 0-turn 或 mock 代替真產品。

本批任一 selected、表面語義、記憶 ID、成本、生命週期或安全
界線失敗即整批 strict FAIL。尤其 T2 主語是上一批已知負例，
這次沒有修；若再失敗不得降低 T2 rubric 或稱整批 PASS。
即使全過，也只證明這個有界產品類型；不構成強 LLM 公平對照、
真人被理解感、正式 M55/M56、VRM／Function Calling 完整驗收
或人類方程式成立。結果封存後更新 `CURRENT_TASK.md`、review
diff、commit/push、核 PR #435；原已曝光兩批不重播追分。
