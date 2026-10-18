# P4 關係問句的泛用短期記憶答案權限：前瞻計畫

狀態：2026-10-18，設計與新題在本項實作／首輪生成前凍結。本項是同團隊自編的產品開發探針，不是獨立 temporal holdout、人評或同模型 LLM 比較。上一批八輪 strict FAIL、raw 與 gold 不改、不重播追分。

## Before 與因果邊界

`analysis/p4_quoted_line_act_scope_fresh_product_probe_result_2026-10-18.md` 的已曝光 T6：selected `ask_miss_me`／core `少しくらいは思ってる`，但 `memory_anchor.kind=context` 取自上一輪 `quoted_line_feedback` 的 `short_term`；`memory_use_expected=true` 使泛用 `_memory_grounded_reply` 在關係 act 前接管，最終 `前に:「うちのこと、今も覚えてる？」って台詞、って言ってたろ。`。這是答案權限錯置，不是檢索缺失。T7 又有獨立的整句 frame 誤判；只修本項不能把 T7 認成 PASS。T8 的具體改寫、T1 的 21.7664 秒及敬體也分開。

唯一核心變因：**已選的直接關係 act `ask_miss_me` 不得讓 `kind=context` 的泛用檢索錨點取得可見答案權限**。這個錨點仍在檢索資料與審計圖中；只撤銷本輪 `memory_use_expected`／可見 anchor，讓已選的關係回覆繼續。不得改候選排序、top-k、profile／episode、selected intent/core、舊 quoted-line scope、M22 路由、保護性路由或最終日文 guard。`recall_context` 等真正事實回憶、結構化 profile、來源限定顯性 episode 契約維持原權限。缺證據不能聲稱有具體記憶；不因本修正新增個人事實、心理事實或固定「記得你」句。

實作只新增 opt-in 權限模組、聚焦測試、薄 Web 入口與必要的隔離 controller 繼承；可更新本計畫、前瞻資料／SHA、任務卡與結果報告。舊 frozen code／資料／raw 不改；不碰原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/`。如需改舊 frozen 檔或通用記憶架構，先停止並重審設計。

## 新資料與嚴格 gate

`datasets/p4_relationship_context_answer_authority_fresh_probe_2026-10-18.json` 六句事前對 repository 做逐字搜尋，除既有題的語義類型外，exact overlap 為 0。T1→T2 與重啟後 T5→T6 測引述台詞被檢索但不能回答真關係問句；T3→T4 測直接可核對的事實回憶仍可用。兩個 Safari session，T4 後 planned stop、同隔離 DB 重啟；每句一次、0 retry。零模型負控另涵蓋：`ask_miss_me` 無錨點、有 generic context、profile-grounded；`recall_context` generic context；quoted-line 編輯當輪；保護性 scene／intent、low-road；第三者或敏感 generic context、來源缺失／歧義；不改本輪 selected core。開發 fixture 不採用六句逐字文本。

首發 strict PASS 必須同時達到：聚焦與受影響相鄰測試全過；T2/T6 實際 selected `ask_miss_me`，T1/T5 generic context 實際進入檢索且原來源可追溯、可見答案權限撤銷，graph receipt 與 final 一致，最終自然 casual 日文答真關係問句，不輸出 `User:`／`Uruha:`／引用台詞為自己的記憶；若 selected 或來源未出現，記 coverage FAIL，不猜測 gate 成功。T4 事實回憶的來源 episode ID／內容／可見值與 T3 同源；T1/T5 仍答引述外層評價。六輪 6/6 raw `assistant_reply`＝graph `UTTERANCE`＝Safari 泡泡；T0–T6 七份 full profile 0 rows／同 digest、六個不同 episode、planned restart／兩 PID 退出／port vacant；每輪 user wait ≤20.0 秒。新權限 gate 新增模型呼叫 0；全管線 token 無可信 ledger 則標 unavailable。

任何門檻失敗整批 strict FAIL，保留 raw、原因與成本，不改題重播追分。先提交本計畫／資料與 SHA、核 PR head，才寫 opt-in code；code、相鄰測試與依賴再另作首輪前 product freeze，核 Git 後才啟全新隔離 Safari。需要兩個有根據修正批仍失敗就 `REVIEW_REQUIRED`，不加任意例外。即使本批通過，也只證明 selected 關係 act 對泛用 context 答案權限的有界控制，不證明 T7 混合 frame、T8 改寫、冷啟性能、普遍語用理解或同模型優勢。
