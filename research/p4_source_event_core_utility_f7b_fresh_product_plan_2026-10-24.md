# P4 f7b：相同來源效用的全新一輪產品驗收計畫

狀態：**source-only freeze；0 f7b product edit／0 f7b provider generation／0 f7b Safari Send**。f7a 原題只預填、未送出，因 Tpre 後背景交錯及額度中斷而 pre-Send strict FAIL；保留 `analysis/p4_source_event_core_utility_f7_presend_failure_2026-10-24.md`，不重送、不改事前 gold。f7b 是**同一個已提交 f7 產品變因**的新作者診斷題，不是新的能力里程碑或正式 holdout。

## 問題、資料與不可變邊界

仍問：在 M29 已驗證當輪 User 直接要求一句鼓勵、M33 不適用、M21 full compact 實際完成時，opt-in 來源事件效用會否把**模型已生成的**帶物件／動作事件核心選到最終可見回答，且回答保留事件與自然日文？其他程式、模型、prompt、schema、生成參數、fallback、final guard、記憶與人格不改。固定 `--direct-act-arm control --repair-cue-boundary --compact-json-schema --source-event-core-utility --turn-admission-journal`；不能混入 handoff treatment。以已推 `3ef6a55f4d5b5f04c294220864ffa65b36b5d271` 的 f7 code/契約及 `research/p4_source_event_core_utility_f7_design_2026-10-24.md` 判操弄。

本輪唯一新刺激在 `datasets/p4_source_event_core_utility_f7b_probe_2026-10-24.json`：`初めて自分で木の小箱を作った。今は一言だけ励まして。`。事前對 `HEAD` tracked 檔的完整原句與 `木の小箱` 查找 0 命中；f7 單測有近鄰 `木の椅子を磨いた`，所以只稱原句／事件來源不重用，**不稱詞彙獨立**。只讀 source-only 檢查得 M29 `direct/brief_encouragement`，現有有限 grammar 可抽出 `木の小箱`、`作った`；這不是 fresh model 或真選句結果。gold 固定為：短、自然日文，一句低壓鼓勵，明確接住首次自己做木小箱；純泛稱、教學、追問、混語、捏造 FAIL。f7 grammar 只證候選核心中的原文物件／動作字面；`初めて`／`自分で` 和 final surface 仍要另看可見結果，不能用 `grounded` 標籤代替 gold。

## 隔離操作與硬 gate

1. 在新 0700 controller-owned 私有 root、目前空閒的 port **7935** 做官方 ONNX 私有封網 warm 與同 PID zero-turn rehearsal；核本機 `qwen2.5:7b` digest、f7 product SHA、模型設定、child flags、正式 DB 完全隔離。零輪 planned stop 後，另啟正式 PID；same-PID HTTP ready，active DB 必須 `memory_db`、reset0、tick0、finish0、空隔離 DB、Web log 空。任一不合格即停，不送題。
2. 原生 Safari **只新開本輪分頁**，先預填凍結原句；所有靜態核對在 Tpre 之前完成。等一個完整 background start/end pair 結束，立即保存 0600+fsync Tpre 快照並按 Send **最多一次／0 retry**。從同 PID journal 事後核 Tpre end→human arrival ≤10 秒、0 背景 interleave、同 opaque ID 完整 delivered、reset0、active DB 不漂移、finish0→1。任何 pre-Send 或 arrival gate 失敗就停止，不把 off-gate 回答重判成 PASS，不同題再試也需先新設計審查。
3. 真輪須核 M29 direct `brief_encouragement`、M33 not applicable、M21 full/compact `completed=true`、3 原始 candidates、`fallback_used=false`、單一模型 call；f7 utility `eligible=true`、至少一個 grounded candidate。只有同一**最終**候選集 old→new winner 不同、selected core hash 等於 utility winner、其後無 revision/final repair，才判 `manipulation_exercised`；否則 `not_exercised`／`no_grounded_candidate`，不得宣稱效用因果改變最終回覆。即使操弄成立，可見 gold 不過仍整體 strict FAIL。
4. 核 Safari 泡泡＝raw＝guard＝graph UTTERANCE＝隔離 episode；graph 需同輪可見 input→retrieval→decision→utterance→writeback 與事件證書、候選覆蓋及舊／新選擇。保留可重核的 native visual 原件；若工具無法保存，visual/full-product gate 明列未達。記實際 generation 次數、prompt/completion token、latency、vector/Web/背景成本；上限 1 Send、3 completed generations、2000 provider tokens、20 秒 user wait。超額或任何品質／隔離／時序硬 gate 失敗即 strict FAIL。
5. 結束只關本次新 Safari tab，exact PID planned stop，核 7935 vacant；私有 T0/Tpre/Tpost/journal/receipt SHA 留證。只提交 scope 內報告與 `CURRENT_TASK.md`，不提交私有對話或 cache、不碰原始 dirty checkout、正式 DB 或無關 `output/`。

此輪若通過，最多證明有限日文直述＋明示鼓勵場景中，已存在候選的來源覆蓋效用在一次真產品生成裡實際作用；不能稱全面人類理解、同模型 LLM 優勢、正式 temporal prediction、人評或完整 P4。若 3 候選都泛稱，保留候選生成瓶頸；若 selected grounded 但 final 漏事件，保留 surface 保真瓶頸；若證書誤授權，縮窄來源解析。一次失敗不重試、不為追分改題或改 gold。
