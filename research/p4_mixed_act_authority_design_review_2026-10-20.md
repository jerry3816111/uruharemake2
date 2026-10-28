# P4 mixed-act 權限：七輪失敗後的 0-call 設計審查

狀態：只讀設計審查，**不是新實作、不是前瞻資料凍結、不是產品 PASS**。上一批 W1–W7 的 strict FAIL、raw SHA、gold 與一次性輪次維持不變；證據見 `analysis/p4_mixed_past_place_source_authority_fresh_product_probe_result_2026-10-20.md`。

## Before：真正斷點

四個 mixed query 都由 `current_turn_source_role_p4` 判 `mixed_request`，但新 gate 0/4 出現在最終 logic／graph。不是條件字串解析失敗：`uruha_mixed_past_place_source_authority_p4.py` 的 `_has_competing_authority` 依凍結設計在 M31 `surface_authority=true` 時 fail closed；真 W2/W3/W5/W7 全符合，W2/W3/W5 的 M32 也 true。舊 M31 是 source-first 的當輪**字面語義表面**憑證；`uruha_adaptive_person_model.py` 的 `apply_semantic_authorization_m31` 在權限成立時覆蓋整輪 core，M32 又可用 canonical fields 覆蓋一次。它們目前沒有明確證明自己完成了「引述改寫」及「回憶過去本人選的地點」兩個外層行動。W2 的 W1 直接 User 原話可見於隔離 recent／episode，卻無法因此推論現在就可覆寫 M31：來源可用性與**本輪行動權限**是不同命題。

`uruha_brain_mac.py:18019` 的 `ingest_event` 回傳 `user_input`、`memory_data` 等，runtime 有 `cycle_index`，但無當輪不可重用 event ID。M31 呼叫位於 `cognitive_tick`，原憑證的 input digest 只證相同文字；M32 在同一程序中直接以 M31 結果為參數建立，也有 `source_m31_status`、`source_m31_surface_authority`、canonical fields 與檢查欄位，但**沒有可持久稽核的 parent receipt**。current-turn role 自述 `same_text_but_event_and_parent_lineage_unproven`。Web 的投影線也不是原生 parent edge。不能事後拿同一句 digest、模型自報的 confidence 或 W2 失敗答句，推定 M31/M32 權限應讓給新 gate。

## 單一核心變因候選：typed multi-act coverage 與產生時 lineage

要改的是「目前以一個 literal surface 權限代表整輪」這個變因，而非偷偷把 M31/M32 設成 false。下一批若能安全實作，需在**產生當時**記錄不可重用當輪 `event_id`、raw input digest、引述改寫與過去地點回憶兩個 `action_id`／原文 spans；M31 憑證連 `parent_event_id`、自家 proposal/contract ID 與其實際涵蓋的 action 集，M32 連 `parent_m31_id`。M33 在 M31/M32 後仍可施加語義／表面約束，也必須列入權限稽核。仲裁只可在 event→M31→M32（及適用的 M33）鏈、span／action 型別和 protected route 均驗真後判定舊表面只完成其聲稱的 action，保留舊授權／成本收據作 shadow，而非清除它們。若 parent 缺失、重複／不同事件、M31/M32/M33 真已涵蓋行動、來源不明或 protected route，必須 fail closed，沿用原權限。

兩個行動還需各自有交付憑證：回憶子句只可引用已交付的直接 User 來源，絕不由 current query presupposition、第三者引述、assistant 或摘要授權；改寫子句需維持原引述意思且成為自然、朋友向日文。**僅使過去事實 gate 取得權限仍不能完成整個 mixed request**，不得以「M31 被 shadow」或「沒有假地點」當產品 PASS。若選擇先單獨驗 lineage，應明定那是工程中間 gate，完整 mixed-act 產品仍 FAIL；若要求此下一批作為產品 gate，便須有原子式兩子任務合成及最後可見表面／episode 同步驗證。這兩種設計不可以混用判準。

## 前瞻准入條件，不是本批新資料

實作前另凍結未曝光、與 W1–W7/舊 A 題來源不重疊的原句、地點及日期，至少含直接 User 同 session、typed episode 重啟、無來源、同日矛盾、第三人引述、assistant／summary-only、相對日、撤回、protected route、非 mixed 保留 M31/M32；零模型注入缺 parent／錯 parent／重複 parent。每題明列兩個子任務的 conditional gold、最後自然日文與未知邊界；來源／action receipt、圖上真節點與可核原生 parent、raw＝guard＝Safari＝graph utterance＝episode、profile 隔離、逐輪 ≤20 秒、新增／總呼叫成本另列。未先凍結，不送 fresh model／Safari；舊 W1–W7 絕不重播追分。即使新批通過，也只是 bounded mixed-act 權限與交付，不可外推為一般語用、真人偏好或強 LLM 優勢。

風險：若無法在 producer-side 實際攔截 M31/M32 建立 parent links，或原有 protected／M33／記憶回憶權限無法無歧義仲裁，則這條候選不得實作為 bypass；保存 `REVIEW_REQUIRED`，轉其他獨立必要交付。W1/W6 主語歸屬、一般改寫品質與 W7 殘句各是獨立失敗，不得以這份設計抹除。
