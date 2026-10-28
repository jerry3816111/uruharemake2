# P4 本地時間／位置問答：來源授權前瞻計畫

狀態：2026-10-19，**實作與新 Safari 首輪前凍結**。資料為開發者設計的 fresh 產品探針，不是正式 holdout／人評／同模型 A/B。先前 `reference_probe` 批的 raw SHA `892e98fb2dc29531e5b0f518cfeea3a1f935aa8b679251ad901d001e8dfa9618`、路由 4/4／2/2 與整批 strict FAIL 原封不動；A3/B1 不重播計分。

## Before 與單一變因

隔離 Safari A3 問預約開始時間，B1 問幕的儲位。前一個 opt-in 證書都正確拒絕舊 `reference_probe` seed；M22 卻將兩者標為 `general_conversation`，M21 full planner 被選 `core_message_jp` 已含無來源的「午前中」「机の下」。planner tick 無修訂，末端 `visible_language_guard` 與 M39 接受；`constraints.forbid_knowledge=true` 不足以阻擋。原 trace 不存三個候選的 core，所以不能區分候選生成與 rerank 的相對責任，卻已能證明被選計畫缺少事實來源授權。舊 assistant 答案會隨 episode 回流，不能因被檢索就升格為證據。

唯一產品變因：**在 opt-in 入口，對「本地事件何時開始／物件放在哪」的具體值施加來源授權**。當輪問句只提供主題與 slot，不提供答案。可授權的值限於當輪直接使用者陳述，或已**實際傳給決策**的原始 User turn（同 session `recent_turns` 加精確 provenance，或 Chroma `direct_episode` 的 `turn_episode` 且能精確解析 User 欄）；不得取 episode time、summary、assistant answer、第三者引述、猜測、否定或未檢索的 DB 資料。多個不同 User 值衝突時拒絕具體答；缺來源只能說「目前對話中無法確認」，不說世界上不存在。來源匹配應依 subject／slot 的通用有界文法，不得把題句、值或 gold 寫入程式或 prompt。支持值要答出並在 graph 留 trace ID／digest；不可「全部不知道」。

同一證書在選定計畫交給 speech 前和最終可見句後核對，避免末端再添無來源值。新 graph node 顯示 query slot → examined source classes → admitted/rejected evidence → selected-plan authority → visible status；舊 pre-gate nodes 若被覆寫須標 shadow，而計算成本仍保留。候選 core／選擇後 core 的有界 digest 與來源判決可做診斷，但不持久化三個模型候選原文或把 trace 本身當效果。保護路由、真正尋曲、建議問句、一般敘述、既有記憶寫入與原 reference gate 不改。新 gate 不加模型呼叫，不用另一個 LLM 作答案修理。

允許檔案：新 opt-in source-authority adapter、其聚焦測試、薄產品 entry/controller、新資料／SHA、此計畫、結果報告及 `CURRENT_TASK.md`。不改舊 core、M22/M21 scorer、M39／共用語言 guard、既有凍結資料／報告、正式 DB、原始 dirty checkout或無關 `output/graduate_application_report/`。若無法在不改共用 core 的情況下讓 selected／visible／graph 同源，記錄失敗與 `REVIEW_REQUIRED`，不偽裝通過。

## 前瞻十一輪與硬門檻

資料：`datasets/p4_local_time_place_answer_authority_fresh_probe_2026-10-19.json`。全新 0700 隔離 root、0-turn readiness／planned stop、官方 SHA ONNX 私有離線預熱及空 profile；真 Safari 兩 session，同 DB 在 A4 後 planned restart，A1–A4／B1–B7 各句一次、0 retry。A1 無來源時間不能編；A2 直接使用者時間陳述後 A3 應答 `14時`，重啟後 B1 仍須在已交給決策的原始 User episode 找到相同來源並答 `14時`（若 retrieval 缺席，**產品 FAIL**，不偷讀 DB 補題）。A4 的朋友「かも」不是 User 肯定儲位，B2 不能編北棚；B3 直接 User 置放後 B4 應答西倉庫。B5 問「放哪裡較好」屬建議，不可被 fact-answer 閘改成不知道；B6 真參照與 B7 受保護辱罵保持原路由，惟全批自然日文品質仍獨立要求。

硬門檻：A1/B2 **2/2** 無來源不編，A3/B1/B4 **3/3** 有來源答值且記錄真 User trace ID／slot，A4 不把第三方推測升為事實，B5/B6/B7 **3/3** 不越權；**11/11** Safari 泡泡＝raw＝graph UTTERANCE＝guard、自然日文／行動忠實／無內部分析；十一個不同持久 episode，T0–T11 profile 0 rows／同 digest；每輪 user wait ≤20.0 秒；gate 0 新模型呼叫，列出可得 M21/M31、token／延遲和 PID／port。任何一項失敗即整批 **strict FAIL**，不得補送／改 gold；若來源缺失、路由錯、語言不自然與 latency 失敗分別歸因。這些數字不是正式因果增益，只有已凍結正負控的產品層證據。

順序：凍結計畫／資料 SHA 與精確 git commit；做零模型聚焦與受影響回歸、語法、product SHA、diff review、code commit/push/PR head；再 fresh local model／真 Safari 一次性輪次；逐輪圖與原始記錄核對；報告成本、失敗、存儲邊界。若首批失敗，至多兩個有根據且新題的修正批；不得用同一十一句追分。正式強 LLM／真人／temporal holdout／VRM／Function Calling gate 繼續 pending，Goal active。
