# P4 profile 選中 plan 來源權限：第二批八輪 Safari 產品結果

**限定結論：本批事前定義的 selected-plan／profile 記憶承諾 strict gate PASS。**
前批十一輪仍是 strict FAIL，不重判、不重播。這次新八輪最關鍵的差異是：
朋友傳話 T1 的 M29 泛用字面投影原本確實會要求接管，但在選 plan 之前
被來源受限的 profile memory act 撤權；真正 `selected_plan` 和後續
prediction、日文回覆都選「不把朋友好惡寫成本人」。不再只靠最後一層
surface guard 救回。這是限定句型與產品入口的修正，**不是**一般人類語用
理解、同模型強 LLM 優勢、真人被理解感或全系統正式完成的證據。

## 事前凍結與操作程序

- 設計 `research/p4_profile_plan_authority_repair_2026-10-02.md`；新 source-only
  資料 `datasets/p4_profile_plan_authority_fresh_probe_2026-10-02.json` 與
  `research/p4_profile_plan_authority_fresh_probe_plan_2026-10-02.md`。
  `research/p4_profile_plan_authority_fresh_probe_freeze_2026-10-02.sha256`
  的 18 個程式／資料／設計／依賴 hash 在首輪前全數 `OK`；freeze commit
  `1375376` 在首輪前完成並推上既有 branch。首輪後沒有改金標或程式。
- 聚焦＋受影響相鄰回歸在測試進程 FD soft limit 4096 下
  `185 passed, 8 dependency warnings in 79.69s`；新安全 launcher 的 0-turn
  check 通過、overlay 安裝且只指向 isolated runtime。獨立唯讀 freeze
  review 核對 8/8 純規則 owner/extraction gold 與 M29→plan 時序，未見
  blocker；它不是 Safari 或模型品質證據。
- 新隔離 root：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-71a0xxs1`；
  起始 Chroma 五個 collection 均零列。只在一個**新** Safari 分頁逐字
  送 T1–T4 各一次，舊 PID `55367` 退出且 port `7892` 不再 LISTEN；
  同一 root／DB 由新 PID `55872` 起服務，重載同一 Safari 分頁取得新
  session，再送 T5–T8 各一次。兩個 PID 末了皆已退出、port 已關，
  隔離 root 保留覆核；沒有回答 retry 或額外使用者輪次。
- raw JSONL：上述 root 的 `web_logs/conversation.jsonl`，8 行，SHA-256
  `ffd7bc3fda55b6c41e2592c3922529c9648f5ac1a6cb4e871f7745820ce6011a`。
  `diff` 對凍結八個 input 為零差。兩個 session ID 分別
  `20261002_045146_bda3b3b4`（T1–T4）和
  `20261002_045556_7218e19f`（T5–T8）；SQLite 同時保留兩段
  episode/profile。每輪實際在 Safari 觀察泡泡和 node graph；原始圖像
  的工具觀察並未另存成 screenshot artifact，以下精確節點核對可由 raw
  和 DB 重算，不把 raw 假稱 UI 本身。

## 逐輪結果與真正改變之處

| 輪 | 來源／行為 | 事前→實際 profile 增量 | Safari 最終日文與真 selected plan |
|---|---|---:|---|
| T1 | 璃帆傳話，拒當本人 | 0→0 | `ん、その話は聞いた。お前の好みとしては覚えない。`；plan `profile_write_ack_rejected` |
| T2 | 本人飲品 | 1→1 | `ん、その好みは覚えとく。`；plan `explicit_preference_memory_write` |
| T3 | 本人同 scope 訂正 | 2→2 | `ん、訂正の内容はそのまま覚えとく。`；plan `explicit_preference_memory_correction` |
| T4 | Norah 引文 | 0→0 | 日文拒寫；plan `profile_write_ack_rejected` |
| T5 | 重啟後中文本人點心 | 1→1 | 日文承諾；plan `explicit_preference_memory_write` |
| T6 | 若晞轉述「使用者喜歡」 | 0→0 | 日文拒寫；plan `profile_write_ack_rejected` |
| T7 | 英文本人音樂 | 1→1 | 日文承諾；plan `explicit_preference_memory_write` |
| T8 | 英文兩個本人飲品候選 | 0→0 | `ん、好みが複数あるな。今のはどれか教えて。`；plan `profile_write_ack_rejected` |

八輪真正 blackboard `selected_plan` 都恰一個，intent 和
`core_message_jp` 與事前 gold **8/8 精確一致**；`logic` 同樣 8/8，
`prediction_hint.source_plan_intent` 8/8 等於選中 intent，graph
`utterance.reply`、JSONL reply 與 Safari 泡泡 8/8 一致。每輪恰一個
`profile_write_ack_truth_p4` graph node，`status=matched` 且
`checks.selected_plan_authority=matched` 皆 8/8。T1 M29 trace 明確記錄
`pre_veto_projection_required=true`、`pre_veto_status=projection_candidate`，
post-veto `status=superseded_by_profile_memory_act_p4`、
`projection_required=false`、`surface_authority=false`；這才是本批
介入遇到實際因果風險的證據。T4 原 M29 不需要投影，但不影響 T1 的檢驗。

writer 的逐輪實際 profile delta 為 `[0,1,2,0,1,0,1,0]`。SQLite
`user_profile` 正好五筆，均 `subject=user`：`柚香麦茶` like/drink、
`金柑玄米茶` like/drink、`柚香麦茶` dislike/drink、`杏仁酥`
like/點心、`lo-fi piano` like/music；四個拒寫輪沒有把第三人稱／歧義
值寫入，五個事前禁值也沒有出現在 profile value 或其子字串。
T3 物理舊正向列仍標 active，但新列以 `previous_current_memory_id`
指向它；後續讀取 snapshot 只把金柑玄米茶列為當前 like、柚香麦茶
列 dislike，符合原先「resolver historical、非物理改 metadata」判準。

持久 `source=turn_episode` 恰八筆且 ID 互異。測後閒置背景整理另新增
一筆 `episodic_consolidation` 摘要、一筆 procedural、一筆 wisdom；
摘要與 wisdom 只提及已由 T7 本人確認的 `lo-fi piano`，不包含被拒寫
的候選。故 SQLite episodic collection 最終 **9 列不等於 9 個對話回合**；
本項只驗 profile truth，不宣稱跨層背景整理已全面安全。八輪
`user_wait_seconds` 總和 `21.5208s`、最大 `3.0928s`、8/8 ≤20s。
M21 此八輪是 deterministic rule plan、沒有嘗試 general model call；
整個產品的可信 token／call／價格 ledger 未備齊，標 `unavailable`，
不可稱「完整系統零模型成本」。

## 證據分層、剩餘問題與下個必要 gate

以上 strict PASS 只適用開發者自製、事前凍結的這八個產品輪次。
獨立唯讀稽核另從 raw＋SQLite 核對八個 input/final/plan/logic、
prediction、truth node、writer delta、profile、episode、兩 session
與成本，未見 blocker；Safari 泡泡、PID/port 真重啟及 0 retry 由主
操作者的 UI／程序觀察補足，不能僅從 log 自稱已證。未做正式
temporal holdout、強 LLM 同模型公平對照、人評、VRM/tool 完整驗收，
也未處理前批來源問答 intent drift、owner 句末否認誤准入或一般
背景整理在未解訂正後的跨層副作用。下一張獨立工作卡應選其中一個
已有真 before 的最小產品問題，先凍結單一變因與新反例；不得把
此八輪當新問題的重跑題或把前批 FAIL 抹掉。
