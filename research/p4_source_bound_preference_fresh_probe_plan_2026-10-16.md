# P4 來源綁定本人偏好快路：新五輪 Safari 產品 probe 事前契約

狀態：2026-10-16，**尚未送 Safari／模型**。這是
`p4_source_bound_preference_fallback_plan_2026-10-16.md` 及
`p4_source_bound_preference_object_boundary_review_2026-10-16.md` 的
developer-authored 產品驗收；不是 formal temporal holdout、人評或
同模型強 LLM 對照。exact input/gold 在
`datasets/p4_source_bound_preference_fresh_probe_2026-10-16.json`。
寫入前已以 repository `rg -F` 核對五句全文和四個物品值皆無命中；
這只能證明本 repository 未用過，不能稱獨立未見資料。

2026-10-17 事前生命週期修訂：下文「GUI launchd job」要求已因
模型前 Python 啟動探針失敗，由
`research/p4_preference_fallback_lifecycle_amendment_2026-10-17.md`
取代為有精確身份／listener／HTTP／stop 證據的 exec-context detached
controller；其餘 gold、門檻、0 retry 與失敗分支不變。新資料尚未
freeze／曝光，修訂不是根據五輪回覆調整。

## 問題、變因、模型前證據

舊問句六輪產品 probe 僅 T1/T2 完成，T2 正確路由／writer 但
等待 `26.5627s`，M31 約 `12.8828s` 後又進 general planner
約 `10.3953s`。本卡唯一語義／成本變因是：只有已經過 source owner
admission 的單句日文、帶有一般物品類別形態線索的本人肯定偏好，
而且舊規則會返回 None、原產品確實走一般 planner fallback 時，
從當輪來源值產生確定性的 `chat` plan。M31/M32/M33、writer、問句
matcher、人格與 final surface guards 均不變。沒有任何新模型呼叫
或 Safari 結果前，純 route/source 預檢：T1/T3/T5 為
`chat`＋`planner_path=source_bound_preference_fallback_p4`＋唯一本人
`like`；T2 既有 rule 返回 None／source 無准入；T4 既有 rule 為
`ask_like_me`／source 無准入。這些預檢不是 selected runtime 結果。
可重現的 exact-input 命令與逐輪表保存在
`analysis/p4_source_bound_preference_prefreeze_route_check_2026-10-16.md`。

聚焦與相鄰回歸、入口 0-turn 安全 preflight、獨立 launchd inert
dry-run 都需先通過。產品服務必須在有標籤的 launchd GUI job 下
運行；單純 bootstrap 不算存活，先核埠未被占、new PID/PPID、
HTTP 實際屬於新 job、私有 stdout/stderr 與狀態。T3 後只停唯一
label，核原 PID/埠退出並保存 exit/log；同一私有 root/DB 下用
新 label/PID/session 起第二服務，不覆寫第一段證據。非預期
中斷則封存並標程序 FAIL，不重送。只能 localhost、0700
launcher-owned root、寫入沙盒、新 Safari tab；正式 DB、原始 dirty
checkout、無關 `output/graduate_application_report/` 與既有 tab 不碰。
兩次啟動各記 `launchctl print` 的唯一 label/PID/state、`ps` 的
PID/PPID/UID、`lsof -nP -iTCP:<port> -sTCP:LISTEN` 的 listener PID
與服務 PID 一致、localhost HTTP GET 可達及相同 root 的 log／
session 身分；任一歸屬不明就不送 Safari。停止前後重查同一
label/PID/port，保留 stop 證據；不能用 HTTP 可達單獨當作本服務
存活，亦不能因 launchctl 的暫時觀察錯誤推斷 job 已卸載。

## 每輪觀察與 strict 判準

五個 exact input 依序各送一次，0 retry；T3 後恰一次計畫重啟、
總計恰兩個 session。每輪**送出前後**從 Chroma 唯讀保存
`subject=user` profile row-ID 集合與 metadata，核對新增 ID
`[1,0,1,0,1]`；不能用 collection count 代替。三筆最終本人
`like` 值與 `preference_scope` metadata 缺鍵（JSON `null` 僅為
預期表示）、五個互異且重啟後持久 `turn_episode` ID 須同時成立。
每輪保存 `Tn.before.json`／`Tn.after.json` 的不可覆寫 snapshot，
含 collection 名、row ID、`subject`、`fact_type`、`value`、
`preference_scope` 是否缺鍵與可用 source hash，以及 episodic
`turn_episode` ID；逐 ID 做集合差，不能只留最後狀態。
使用 `p4_preference_fallback_snapshot.py --runtime-root <已驗證隔離根> \
--save before-t1`（各輪標籤依次替換）以 0600、不可覆寫方式保留；
它只用 Chroma 查詢 API，Chroma PersistentClient 本身沒有 OS 層
read-only 保證，故「唯讀」僅指不呼叫寫入 API，不能宣稱 DB bytes
絕不改動。
記 exact input、Safari 泡泡或截圖、raw JSONL/session/PID/時間、
真 selected plan 與 logic、prediction、M31/M42、owner admission、
fallback 節點、graph utterance、單輪 user wait、可用模型 call/token
欄位。raw JSONL／DB 留 SHA-256。token/價格若缺記 `unavailable`，
不能說成本為零。

T1/T3/T5 真 selected `chat`、fallback marker 與 node、M21
general planner call `false`；T2 既不能是 fallback 也不能選
`ask_like_me`，不把朋友偏好寫進本人 profile；T4 保留既有
`ask_like_me` 優先，不被 fallback 奪權。所有泡泡均自然日文、
逐字等於各輪 graph `utterance.reply` 與 raw assistant reply；
語義符合 JSON 逐輪 rubric，不捏造 private facts、不傾倒 debug、
不宣稱記住了未觀察的寫入。**每一輪 user wait ≤20 秒**；任一
超過就成本 FAIL，即使正例 general planner call 減少也不能放行。
多輪對話可見品質亦須觀察，不能只憑 call count 推稱被理解感。

舊設計的 T2 等待與新 T1/T3/T5 的時間是**不同輸入**，只能比較
機制 call path，不能直接把不同句子的秒數相減主張因果加速。
本次若仍有 T2 第三者慢路徑或錯來源，明列舊路徑負結果，
整體 strict FAIL，不靠縮小 gate 追認通過。真正延遲改善須對
同樣來源與條件做可重現受控對照，Safari 本批只驗產品可用性。

graph 只主張真 selected fallback/owner admission 各有節點和時間
順序；若沒有專屬因果邊，不稱 graph 已證明完整來源因果。
fallback audit 的 raw-free 不代表全圖或 episodic memory 不含原文。
就算本限定 gate PASS，未知物品/人名、跨語普通聊天、舊 10/2
後句否認批次 FAIL、正式 M55/M56、真人被理解感、VRM/tool 等
目標仍 pending。不能稱人類方程式、全面較強 LLM 優越或整個
P4 完成。

先等實作、controller/tests 穩定，製作 SHA-256 manifest（本資料、
本計畫、10/17 生命週期修訂、審查、新 module/entry/launcher、
detached controller／診斷與 tests、上層
凍結 manifest 與受影響基礎檔）並 commit；首輪前核對本層與
上層 manifest，不能在看到模型答案後改資料、gold、門檻、程式
或補送已曝光輪次。結果不論正負，保存最早失真、圖／raw／DB／
成本，更新任務卡、review diff、commit/push、核 PR。
