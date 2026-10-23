# P4 真 Web 逐輪入口歸因：前瞻量測計畫

凍結於本項程式修改與任何新題真模型生成之前。d0/e0 在 Send 前的 v1 receipt 已有 `autonomous_tick_index=1`，d1 則 Tpre 0／Tpost 1；三者舊門檻與 FAIL 均不改判。e0 ready file mtime→Tpre mtime 約 62 秒，與 Web 每 10 秒輪詢、Brain 閒置 45 秒後可跑背景週期相容，但檔案時間不能證明 click 與 tick 的先後。背景週期即使 `memory_writes=[]` 仍會改 runtime、衰減短期記憶，也可能寫 Chroma metadata。因此不得以「tick1 但 0 embeddings／0 reported writes」自行放行。

## 只改的變因、真正要回答的問題

單一核心變因是**測量的線性化與歸因**，不是回覆政策、背景排程、題目或評分門檻。問題是：一次 Safari Send 在伺服器 queue-free 登記、取得 Brain lock、生成及交付結束的邊界，是否有背景週期或重設改變它實際可見的狀態？目前 opt-in `active_db_receipt.json` 是事件後發布的 latest file，不是 click-time／turn-time 原子樣本；`finish_human_turn` 先放 waiter 再發布，Tpost 可被下一個 tick 覆蓋。源碼入口：`uruha_web_ui.py` 的 `begin_human_submission_with_session`、`RuntimeManager.run_background_once`、`_run_turn`、`finish_human_turn` 與 text/audio browser wiring；Brain 的 `run_background_cycle`。這是足以阻礙真產品驗收的量測缺口，不另開 M 或永久網站。

## 最小產品量測契約

- 新增**可選、隔離、私有、raw-free** per-turn admission journal／certificate。未啟用時一般 Web 行為、UI 與 v1 receipt schema/內容不變。檔案僅可在控制器指定的 0700 root、同 root 的 `memory_db`／`session_db` 旁，以 0600 寫入；不含原文、回覆、prompt 或路徑外的私有資料。持久化失敗時本次 opt-in 驗收 fail closed，不能把缺失解作 0。
- queue-free callback 在 `_human_gate_lock` 中登記 waiter、opaque submission ID、單調 arrival sequence/time，再傳到 queued handler；它是**伺服器登記點**，不是物理 Safari click。現有 `_lock` 才是 Brain／背景互斥邊界；不可先持 gate lock 等 Brain lock（背景 lock 順序為 Brain lock→gate lock）。
- 背景週期在第二次 waiter 檢查同一 gate critical section 記 start sequence；在 Brain lock 仍持有時記 end sequence、前後 tick、goal、狀態／記憶差異、writeback、例外／unknown。若 `background_start < arrival < background_end`，明標 server-arrival 時已有 in-flight 背景，不能把它稱為 pre-click。產品 compute ledger 已啟用時，背景使用獨立 item ID 核對五個 instrumented Chroma collection 的 add/update/upsert/delete **方法返回或例外**；`memory_writes` 只是描述。這仍不證明磁碟 durable，也不覆蓋未 instrument 的 client/外部 worker；相關持久寫入狀態標 unknown，絕不主張全域零寫入。
- queued handler 在 `_lock` 下消耗一次 submission ID，於 `run_turn_debug` **之前**記同 PID、session、reset generation、live Chroma path、tick、背景序號與可得的 state fingerprint；生成後仍持鎖記 `cognition_end`。`_run_turn` 此後會釋放鎖、串流並寫私有對話 log，所以 wrapper 在 delivery／log 階段結束後、放 waiter **之前**再於同鎖記 terminal event，明分 cognition、delivery、episode/log 與錯誤／取消／空輸入／純轉錄狀態，不把 finish count 當成功輪次。缺 token、重複、session/reset/path 漂移、背景 start/end 未成對、獨立 Brain worker 活躍或 journal／audit 不可用時，opt-in trial 明確 invalid；已知的 pre-generation invalid 須在模型呼叫前停止，不能偷偷重送。
- `reset_brain_session()` 目前不持 `_lock`。本項需把其 live Brain reset 與 session/reset-generation 更新序列化在**同一 Brain lock**（正常 UI human lane 順序不變），否則不得主張 entrance→cognition_end 原子隔離；同時驗證任何 reset/path drift 仍 fail closed。若狹窄同步無法安全加入，就在 `REVIEW_REQUIRED` 停止，不能以只有事後偵測的資料放行。
- 背景 compute item 只在該 event 的 raw-free 私有 journal 寫入且驗讀成功、ledger attribution complete 後，才使用既有 `retire_item_snapshot` 釋放已核對呼叫；寫入失敗／歸因模糊則保留 evidence 並標 invalid，不能無界地在長 session 累積未結案呼叫。入口本身只限 opt-in 的隔離驗收，不能暗中變成常駐 telemetry。
- 原有 `submit_text`／`submit_audio` 直接函式呼叫及未 opt-in 的 UI 簽名須保持相容；直接呼叫若在 opt-in 模式自動登記，證書必須標 `direct_no_browser_admission`，不得進 Safari gate。空輸入、純轉錄、取消／generator 中斷要有獨立 terminal status，不能用 finish count 當成功輪次。
- 舊 `active_db_receipt.json` 與 c/d/e0 的 tick0 gate 原封不動。新題須另立 source-disjoint freeze 與新 gate；本工具只能說明 tick 在 server-arrival 前／已開始未結束／生成期間／finish 後何時發生，以及觀察到什麼改變。**不能因記錄得更清楚，就預設 tick1 等同 tick0**。若沒有可檢核的回覆相關狀態等價與持久寫入完整覆蓋，仍 fail closed。

## 驗收、成本與停止規則

先以 barrier fake Brain 做 deterministic before/after：背景先完成、到達時背景已持鎖、human 先登記阻止新背景、Gradio queue wait、生成期、finish 前後、reset/path drift、token 缺失／重複、背景例外、decay-only 但 runtime 改變、Chroma update 方法返回／例外、journal 不可寫及無 raw／0700／0600。UI wiring 需確證 text 與 audio 的 token 傳遞；v1 receipt 和 scheduler 相鄰測試不退步。程式只允許 `uruha_web_ui.py`、必要時既有計算 ledger 的狹窄補充、聚焦測試、本計畫／結果／`CURRENT_TASK.md`。新題的具體 state fingerprint 欄位與等價條件**另在生成前凍結**；本計畫不自行批准 tick1。不得改 `uruha_brain_mac.py` 回覆、排程週期／idle 門檻、P2/guard、正式資料、舊 frozen 題，或碰原始 dirty checkout。

零模型契約每個案例 0 provider calls；附 instrument 本身的事件數、檔案位元組、同步寫入延遲。真 Safari 後續最多一個新 source-disjoint 題／0 retry，仍需官方 ONNX 私有隔離、same PID/session/DB、原生 node graph、final/episode/guard、日文／persona/source、實際 token/vector/延遲及可見品質。若 instrument 所見是 response-relevant drift／未知寫入，或真輪未行使標點分支，保留負結果；不調弱 gate、換題追分。正式人評、temporal holdout、同模型強 LLM 優勢、VRM+Function Calling 與 Goal 完成不由這項量測授權。

流程：本 source-only 計畫先 commit/push 並核 PR → failing focused test 與前後差異 → 最小 instrument → 受影響回歸／獨立只讀審查 → 私有產物、成本與失敗報告 → scoped commit/push/PR 核對 → **再**凍結新題與新 Safari gate。若兩次有根據的修正仍不能閉合量測，保存 `REVIEW_REQUIRED`，不無限擴張。
