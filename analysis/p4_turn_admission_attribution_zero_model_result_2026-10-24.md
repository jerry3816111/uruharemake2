# P4 逐輪入口歸因：零模型程式／契約結果（2026-10-24）

狀態：**source-only / partial；尚無新真模型、Safari、native graph 或回覆品質放行。**
事前設計在 `research/p4_turn_admission_attribution_plan_2026-10-23.md`，已先於本項程式以 `bda04b5` 推 PR #435。舊 d0/d1/e0 的 strict FAIL 不改；尤其 e0 在 Send 前 Tpre tick1，0 user-turn generation，不能因本工具現在能解釋先後就改成 PASS。

## 要解決的真問題與單一變因

原 v1 `active_db_receipt.json` 是事件後的 latest snapshot，不能證明 Safari click、queue-free 伺服器登記、Brain lock 取得及背景 tick 的順序；`finish_human_turn` 原本先放 waiter 再發布 receipt，Tpost 也可被下一個 tick 覆寫。唯一核心變因是**隔離、opt-in 的逐輪測量歸因**，沒有改正常回覆政策、模型、背景週期或 45 秒 idle 門檻。

新 `uruha_web_ui.py` 的私有 raw-free JSONL 依序記 server-arrival、Brain-lock admission snapshot、background start/end、cognition start/end、server generator terminal。它不是物理 click 或 Safari DOM ACK。Brain reset 與 cognition 現在共用 Brain lock；terminal 在放 waiter 前寫入；伺服器到達時若已有 in-flight 背景，依序號可辨。未知／重複 token、重設／DB path／tick／進程內狀態漂移、背景 write attribution 不全、記錄檔損壞、逾時等都會令 opt-in trial invalid，不能作為「零背景影響」證明。

持久化只接受同一 0700 私有 root 與其配置 `memory_db`／`session_db`，live Chroma path 必須是已存在、非 symlink、0700 的其中一個 DB；未建立的非 live `session_db` 可保持不存在。opt-in 模式在 Brain 建構／預熱與 Reset 的資料庫副作用前，先查這個隔離邊界及 Brain 模組實際使用的 `DB_PATH`。JSONL 為 0600、owner-only、非 link，append 後 fsync、原位讀回、驗全檔同 PID／連續序號與當輪 event lineage；未配對的背景 start/end 在下一輪生成前拒絕。首次啟動不接受已非空的舊 journal。背景 compute item 只有在五個 Chroma wrapper 與 Brain 使用同一 ledger、start/end journal 配對讀回、歸因完整、路徑和狀態完整且無例外時才退休；先在 end event 保留 raw-free call/token/vector-operation 摘要。這些是**已包裝方法的回傳／例外**，不是所有磁碟持久寫入、未包裝存取、外部 worker 或 embedding token 的完整證據。

獨立讀審發現真 `MemoryManager.get_runtime_snapshot()` 會透過 procedural summary 查 Chroma。原初補丁若直接取它，會增加 unscoped query，污染回合 compute receipt；現已改為只 hash 明列的進程內 memory 欄位，標 `memory_fingerprint_scope=in_memory_only`。審查亦定位原有 `poll_proactive_turn()` 可消耗 pending proactive 並寫 episode：opt-in 現在把該操作放在 Brain lock→human gate 的邊界內；若真有 proactive 交付或偵測到狀態改變，即把 trial 標 invalid，而非假稱是使用者輪次的乾淨前狀態。這不聲稱 Chroma durable state 等價；向量操作仍需 ledger 和後續真正 full-pipeline 驗證。

## 可重現證據、成本與限制

- 受影響合併命令：`PYTHONDONTWRITEBYTECODE=1 .venv/product_checks/bin/python -m pytest -q -p no:cacheprovider test_p4_turn_admission_attribution.py test_p4_product_active_db_receipt.py test_human_priority_scheduler_m19.py test_p4_browser_bound_graph_hydration.py test_p4_web_final_graph_evidence_delivery.py test_p4_direct_chat_terminal_punctuation.py test_proactive_dialogue.py` → **146 passed，9 個既有警告，0 provider calls**；其中新聚焦 **60/60**。涵蓋 text/audio token 傳遞、背景／proactive poll 與 queue 交錯、Reset／Brain 初始化前 DB 預檢、live DB 外逃／symlink、錯 ledger、背景 malformed/例外／孤立 end／>64 舊未知事件、破損或重用 journal、取消/逾時、delivery 中 drift，以及不得因量測查 Chroma 的反例。
- 可重跑輕量同步寫入成本：`URUHA_REPORT_ADMISSION_COST=1 PYTHONDONTWRITEBYTECODE=1 .venv/product_checks/bin/python -m pytest -q -s -p no:cacheprovider test_p4_turn_admission_attribution.py::test_waiting_human_prevents_new_background_and_records_generation_bounds`。本機 fake Brain 一輪 **5 events、3,598 bytes、append+fsync+readback median 0.362 ms、max 0.526 ms**（單次樣本；不含真 Brain state hashing、模型、Safari、OS 波動）。
- `git diff --check` 應在提交前複核；本結果只說零模型與 source contract。opt-out 的原 UI callback shape 保持測試覆蓋，但真 Safari 未驗。v1 receipt **仍**可能在 waiter 釋放後被背景覆蓋；新判定依 terminal journal，不把 v1 Tpost 說成原子 click-time。
- timeout 只是 `admission_timeout_unknown`，不推定是 Safari 取消；晚到 queued handler 必須在生成前拒絕。server `delivered` 須有完整 cognition start/end 與正常終點，但仍僅代表 generator 完整跑完，**不是瀏覽器已顯示**。進程內指紋不覆蓋 Chroma durable state；ledger 只覆蓋 instrumented methods。原有 Web `_status_markdown()` 在 cognition 收據後仍可能查 Chroma，因此單靠該收據不得當「整個 Web 輪次」向量成本。近乎同時的多次瀏覽器送出尚未驗證 token 與輸入逐一綁定；新 Safari gate 只能先做單一送出。startup、speech/TTS、CPU/RSS/能耗與正式語用品質不由此項證明。

下一步須在此產品 code/test/source 範圍完成獨立讀審、diff review、精確提交推送及 PR head 核對；然後**另行事前凍結** source-disjoint 新題、狀態等價／持久寫入的嚴格 gate，才准新私有 root 的真模型/Safari 一次。若觀察到 response-relevant drift／unknown writes，保留 FAIL；不能拿 tick1＋`memory_writes=[]` 放行舊 d/e0。正式人評、temporal holdout、同模型強 LLM 優勢及 VRM+Function Calling 統一產品驗收仍 pending。
