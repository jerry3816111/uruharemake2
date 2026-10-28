# P4 逐輪入口歸因：新題、接線與單次 Safari 嚴格驗收

狀態：**事前 source-only 凍結**。本計畫及題本必須先提交／推送至 PR #435，然後才可修改接線或作本題真模型生成。這是作者開發診斷，不是獨立 holdout、正式人評或強 LLM 比較。d0/d1/e0 的原始題、門檻及 strict FAIL 不重判、不重送。既有逐輪量測只有 source-only/zero-model 證據；新 journal 的 `delivered` 是 server generator 完成，並非 Safari DOM ACK。

## Before 與本次唯一變因

`uruha_web_ui.py` 已有 opt-in `URUHA_WEB_TURN_ADMISSION_JOURNAL_PATH`；現用的 `p4_direct_reply_act_m29_priority_detached_control.py` 只交給子程序 compute ledger、prewarm 與 active-DB receipt。底層啟動器還會只保留 `_isolated_env()` 明列的鍵。因此從 shell 匯出 journal 路徑無效；不修接線就做 Safari 只會再得到沒有歸因憑證的輪次。此項唯一程式變因是**現有隔離產品控制器的顯式 opt-in 接線**：新增 `--turn-admission-journal`，只允許 `start --mode product`，使其僅在這次 product child 的 `_isolated_env` 指向同一 0700 root 下的 `turn_admission_journal.jsonl`。預設、其他 action、inert、其他控制器與 opt-out callback 完全不變；不可改 Brain、planner、回覆、背景 scheduler、journal schema、舊題、評分或正式 DB。

允許改的追蹤檔：本計畫、單題 source-only JSON、preimplementation SHA、上述控制器、該控制器聚焦 test、必要的一個結果報告及 `CURRENT_TASK.md`。不改原始 dirty checkout 或無關 `output/graduate_application_report/`。啟動驗收只用新 0700 私有 root；zero-turn rehearsal 如需重開同 root，不能在預熱階段留下非空 journal。執行前先證新題與先前 c/d/e0 source 精確字串無碰撞；使用既有零模型 classifier/fake full-turn 驗 route，不把 mock core 當真模型品質。

## 凍結 gate：資料、狀態、持久寫入、產品

1. 接線契約：flag 對 product start 才生效；未給 flag 的 child env 不含 journal；shell 偽造的 journal env 不可漏入；prepare/status/stop/inert 帶 flag 必須在啟動前拒絕；所選 port、root、finally 還原正確。新 journal 必須是 same-root、0600、owner-only、非 symlink，初始不存在／空白，實際 process 首筆為本輪 `arrival`。在此之前只有 0-call tests，依最小 focused→受影響回歸順序，不重跑無關長套件。
2. 模型前 go/no-go：新 0700 root／新 session／正式 DB 0 access，官方 SHA ONNX 私有離線預熱，同一 final PID HTTP ready；驗本機 `qwen2.5:7b` digest 與原 product options。真正 Send 前解析獨立 Tpre receipt，要求同 PID/session/active `memory_db`、`reset_generation=0`、`autonomous_tick_index=0`、`finish_human_turn_count=0`、空 user episode/profile。Tpre 到 Safari Send 動作目標 ≤10 秒；沒有可核時間證據則該時間 gate 為 unknown，不冒稱 click-time 原子。Tpre 不合格就**不按 Send**，保留 FAIL，不重啟同題追分。
3. 這次**不授權 tick1 等價替代**。從 ready/T0 到 server-arrival、Brain-lock snapshot、`cognition_start`、`cognition_end`、`terminal` 均須同 PID/session/reset0/DB、tick0；journal 需同一 opaque submission ID、嚴格連續順序、`source=browser`、完整 `completed` cognition 與 `delivered` terminal，無 `invalid`／timeout／error、背景 start/end、proactive delivery 或 independent worker。任何已完成或 in-flight 背景 tick、缺 event、狀態指紋 unknown、時間無法排序都 strict FAIL。新 journal 證 server-arrival 之後，**不是物理 Safari click**。
4. 持久資料的保守 gate：ready/T0 與 Tpre 前對新 root 的 active DB regular-file tree 記相對路徑、大小、SHA-256 並要求相等，拒絕 symlink、root 外路徑、取樣中檔案漂移；兩時點各核 0 user episode/profile。journal 背景方法歸因必須完整，並為 0 background Chroma add/update/upsert/delete（含 exception）；若 ledger 未涵蓋任何已觀察背景／proactive／外部 worker 或無法驗證，strict FAIL。使用者輪次後的 episode／Web log 寫入是預期結果，**不要求**整個 DB post-turn byte-equal。這個 gate 只對隔離 root、取樣區間與已知 writer 成立；若 tick1 即使 reported writes0 或 in-memory hash相同，依第3點 FAIL，不能聲稱已證全域 durable 等價。
5. 單次真輪／0 retry：只送題本一輪。route 預期 M29 `brief_encouragement`、M33 不接管、M18 不接管、M21 full/compact planner；不符標 `route_fail`，仍保留真結果。可見答案要短、自然日文、公開 persona 邊界內，接住「讀完長篇小說」的可觀察進展並鼓勵；不編疲勞、睡眠或心情、不改成建議。若實際 selected core 有句末 `。！？`，須無雙標點、guard 無因標點 fallback、final 保留 core；否則此機制 `not_exercised`，不得重送。泡泡＝私有 raw＝guard final＝graph utterance＝episode，原生 node graph 的順序與內容須在 Safari 可核並保留可重核 PNG/AX 或同等原生視覺證據；純 HTML replay 不代替。缺任一項產品 strict FAIL。
6. 成本／資料隔離：真輪最多 3 completed model generations、2,000 provider tokens、20 秒 user wait；actual prompt/completion、向量操作、call latency、journal bytes/event count 與額外 Web delivery Chroma 操作分項列出，缺核帳不寫 PASS。不得碰正式長期 DB、外部部署、付費端點；只在 localhost。若 Safari 工具拒絕，Web 層保持 pending，不以其他 UI 手段繞過。

## 順序與結果判定

先 commit/push 本 source-only 凍結與 SHA／核 PR head → 加 failing controller-focused test → 最小 flag/env 接線 → focused/相鄰與 diff review → scoped code commit/push／核 head → 新隔離 root 做零輪 preflight，再於同 run 一次 Safari Send（任何 hard gate 失敗即停止、不重送）→ 結果逐項標 `PASS/FAIL/unknown/not_exercised`、保留 private raw hash、更新任務卡並提交報告。若真輪未選已修句末 core，只能驗 admission/visible 路徑，不能稱標點產品驗證；若 gate 失敗，保留 `REVIEW_REQUIRED` 或獨立後續設計，不換相似題追分。正式 M55–M58、人評、temporal holdout、同模型強 baseline、VRM+Function Calling 統一交付與完整 Goal 均不由這一輪放行。
