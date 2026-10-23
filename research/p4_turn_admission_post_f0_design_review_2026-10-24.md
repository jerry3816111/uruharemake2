# P4 f0 後的逐輪入口設計審查：分開「純淨起點」與「可歸因真產品」

狀態：**事後讀審，下一題前的設計決策**；不是對 f0 的修正、放行或重送授權。f0 在 `analysis/p4_turn_admission_f0_pre_send_failure_2026-10-24.md` 固定為 pre-Send strict FAIL。舊 d0/d1/e0/f0 的輸入、門檻、結果與私有原件不改。此審查只依已提交原件與產品 source，不做新模型生成／Safari Send，不改 runtime、背景排程、資料庫、baseline 或評分。

## 研究問題與 before 證據

當前要證的是：「真 Safari 送來的一輪，在現有背景循環和記憶系統下，能否留下同 session／DB、無並行背景干擾、可核對回覆和成本的逐輪因果鏈？」這**不是**「有背景活動仍等價於 pristine tick0」，更不是 UruhaBrain 優於同模型 LLM。f0 的事前 gate 把這三者壓成同一關：journal 首筆必須 arrival、全程 tick0／無 background row；實際 Web 在 Brain ready 後每約 10 秒輪詢，尚未滿約 45 秒 idle 也會記完整 `background_start/end (idle_noop)`，其後 `passive_decay` 使 tick0→1→2 且 in-memory fingerprint 改變。因此單靠更快操作 Safari 不足以保證「第一筆 arrival」，反覆換近似題追純淨 tick0 既耗費題本，也無助於驗真正輪次歸因。

## 兩個不同主張的判準

| 層 | 可驗主張 | 必要 gate | 不得外推 |
| --- | --- | --- | --- |
| A：pristine 起點 | 使用者到達前沒有任何背景 cycle 或狀態改變，之後完整輸出 | 與 f0 類似的 tick0、首筆 arrival、ready/Tpre DB tree、同 PID/session/reset；必須前瞻新題/新 root 一次，不改判舊題 | 現有 Web 10 秒 poll 使此路徑可操作性低；成功仍不等於真人偏好或公平 LLM 比較 |
| B：實際狀態下的逐輪歸因 | 允許 Tpre **之前**已完成且可歸因的背景狀態，從 browser arrival 到 server terminal 無背景交錯，輸出/圖/episode/成本可核 | 新題事前獨立凍結；背景事件成對且無錯誤／未知 worker；arrival 核 opaque ID/PID/session/reset，Brain snapshot→cognition start/end→terminal 再核 live DB/tick/fingerprint；使用者輪的 native Safari 視覺與 DB 成本 gate | 到達前的 tick／內存漂移可以影響回覆；不能稱 pristine、durable 全局無寫入、click-time 原子或同模型優勢 |

**選擇下一個必要工作為 B**。理由是產品本來會有背景循環，B 能直接驗 Web admission、真模型表面、原生 graph 與 memory writeback 是否形成完整鏈；A 可保留為未來純淨介入題，不作 B 的前置阻塞。這是縮小可驗 claim，不是把 f0 的 FAIL 變 PASS。

## B 的前瞻最小設計（凍結新題時須具體化）

1. 使用全新、與 d/e/f 題原話與語義情境分離的作者開發題；先選擇單輪可觀察 gold，再只用 0-call route/fake full-turn go/no-go。題本、輸入 SHA、同一 `qwen2.5:7b` digest、product options、最多 3 completed generations／2,000 provider tokens／20 秒等待與一次 Send／0 retry，**必須先凍結／commit/push**。這仍不是獨立 holdout。
2. 新 0700 root、新 session／DB；官方 ONNX 私有封網預熱、same-final-PID HTTP ready、正式 DB 0 access。ready/T0 即保存 active DB regular-file tree 的路徑／大小／SHA；Send 前保存 Tpre 同樣 tree，拒絕 symlink、檔案取樣漂移、DB byte 差、非空 user episode/profile、PID/session/reset/DB drift。此檢查只證隔離 DB 在取樣時未見變化，不證所有 writer 不存在。
3. Tpre 的 `autonomous_tick_index` 可以是已知非負數，不拿它冒充0；須在報告明列。Tpre **之前** journal 只能有完整成對、same PID/session/reset/DB、raw-free、完整方法 ledger 的 `background_start/end`，每對 event／submission ID／狀態／SHA／錯誤／向量操作數均記錄（這兩種 row 沒有 `source` 欄）。已完成 `idle_noop` 或 `passive_decay` 可作**明示的 pre-state**；有任何未配對、error、unknown worker、無法核對的持久變化即不 Send／strict FAIL。`memory_diff_nonempty=true` 不隱藏、不作非干擾主張。保存 Tpre 取樣的 monotonic 前後界線並在 ≤10 秒內由 Safari Send；若 Tpre 到 server-arrival 之間又有背景 start/end，或事件與取樣排序不明，**該題 strict FAIL**，不把 Tpre DB tree 冒稱 arrival 基線。
4. browser Send 後，journal 必須有唯一 `source=browser` 的 `arrival`，同 opaque ID 的 Brain-lock `admission_snapshot`、`cognition_start`、`cognition_end(status=completed)`、`terminal(status=delivered)`；序號連續。`arrival` 依 schema 的 `active_db_path`／tick 刻意為 null，只核它的 PID/session/reset/ID；從 `admission_snapshot` 起再核 live DB、tick、fingerprint 與後續穩定性，不回填 arrival 的 DB/tick。arrival 到 terminal 期間不可有 background/proactive start/end 或獨立 worker，也不可有錯誤、timeout、invalid、state drift。`delivered` 只表示 server generator 結束，Safari DOM/泡泡另核。
5. 保存 Safari 原生頁面可重核證據：輸入、泡泡、可見日文、guard final、runtime node graph 的 input→retrieval→decision→utterance→writeback 及 episode 同輪對上；只看 source/假 client 或 HTML replay 不放行。需要獨立取得 Safari UI 證據、對照私有 Web raw/trace/DB，而不能把 CUA 當已保存 screenshot。route／語義／人格／來源／句末標點各照新題 gold 計，錯即 FAIL。成本分開列 user generation、背景 read、Web delivery 額外 vector operations；缺帳為 unknown/FAIL。正式 private DB、原始 dirty checkout、外部部署與既有 Safari tabs 不碰。

## 停止規則與下一步

新 B 題只送一次。Tpre 硬 gate 失敗即不 Send；Send 後任何硬 gate 失敗保留原件／最小反例、停止該題，不換近同義題追分。至多兩個有根據的修正批後仍失敗進 `REVIEW_REQUIRED`。先完成新 source-disjoint 題、gold、完整可執行 gate／SHA 的前瞻凍結，再做 0-call route 和 isolated 真 Safari；不得為達標停 scheduler、延長 idle 門檻、清空或重用 f0 journal。B 若通過只放行「stateful Web 逐輪歸因／可見品質」的局部主張；同模型公平對照、正式 temporal holdout、人評與完整 Goal 仍需各自驗收。
