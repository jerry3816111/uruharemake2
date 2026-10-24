# P4 第三者偏好真問句：未知證據優先權設計審查

狀態：2026-10-17，**下一個單一產品語義變因已實作並通過零模型聚焦測試，尚未進行新 Safari 產品驗收；同團隊非獨立審查**。前批六輪原題、gold、raw、strict FAIL 不改、不重播；見 `analysis/p4_current_statement_source_authority_fresh_product_probe_result_2026-10-17.md`。本項不是修復該批 source graph byte-exact 稽核，那是獨立後續變因。

## Before、可反駁問題、唯一變因

前批 T4 `後輩は抹茶玄米茶が好き？` 是真第三者問句。新陳述來源證書正確未授予；M29 未要求投影、M31 不適用；M21 full planner 產生 `後輩も抹茶玄米茶が好きか。そのくらいでいいだろ。`。`か` 語氣有歧義，但回覆沒有說現有證據不足，`も` 也無來源。既有 `frame_shadow` 報 preserved 卻未偵出；故缺口在**無證據問句的 epistemic authority 進入 selected plan 前**，不是在肯定陳述准入或人格尾句。

單一變因：對**完整、直接、單句、窄日文** `XはYが好き？/?` 的第三者偏好問句，若當輪不是證據、當前可用記憶又沒有 X/Y 同時出現、且原規則沒有 protected／其他已授權 plan，讓來源可驗的「目前無法判定」取得 rule-plan 優先權。回覆只表明目前可見談話不足，不聲稱第三者客觀不喜歡、使用者從未說過，亦不把問句寫成 profile 事實。任何情況均不能把這個 gate 稱為「模型知道心理／世界事實」。

## 有界資料流與權限

1. 用與上一項同等保守的關係稱謂 X、物品頭 Y、長度和單句約束解析真正問句；明確排除本人、うるは／第二人稱、未知姓名、人名物品、關係問句、引文／傳聞／條件／否定／多子句、非日文、危機／暴力／性等 protected cue。解析問號是 speech act，不可為了重用 assertion parser 而讓合成句獲得陳述證書。既有 `_normalize_plan` 將 `core_message_jp` 截為 40 字，故候選 core 須在准入前保證 ≤40 字；過長就交還舊路，不讓主語、物品或「未知」被截斷。
2. 先呼叫既有 `_rule_based_plan`；其 protected、grounded-memory、關係、安全、修正等**任何非 `None` 計畫**一律不覆蓋。只讀本輪 `MemoryManager.query_all_layers` 已交給 planner 的 `recent_turns[].user`、選入的 `working_memory_items` episode 的 `User:` 片段，以及 `memory_provenance.passed_to_leftbrain` 的 `direct_episode`／`recent_turns` 來源之 `User:` 片段。**只檢查來源中的使用者原話，不把 assistant、summary、相似度或 profile 當第三者事實。** 若某一可辨識來源原話同時涉及同一 X/Y，且不是另一個完整的同命題問句（可能有舊陳述、否認或矛盾），保守交還原路，不依單一檢索項推斷目前真實偏好；只有 X 或只有 Y、或只有先前相同問句，都不構成偏好證據。無法辨識必要欄位／來源形狀時也交還原路。這個版本的「無證據」僅指**當輪提供給 planner 的可辨識來源列中未找到**，絕不宣稱整個 DB 或人的世界中沒有證據；亦不宣稱已解已知記憶問答。
3. 無證據時建立 `chat`／casual 的有界 plan，core 用自然短日文表明「X が Y を好きかは、今の話だけじゃ分からないな」，保留原 X/Y，不加 `も` 或推定結論。來源證書只含問句／X/Y digest、`evidence_status=not_found_in_available_context`、rule authority，無原文、無 M31 模型授權、無心理／長期記憶寫入。早期 classifier 與實際 selected plan 必須使用同一決策；M18／M29／M33／安全等後續更高權限可能改選，未真選便不得在圖上宣稱 gate 已執行。
4. **不短路 `RightBrain.speak`。** 既有人格表面／model-surface trace／visible-language guard 照常執行；圖上僅在真 selected 後顯示「問句→可用證據不足→未知方案→實際表面」。成功稽核不能只檢查 core 是可見字串的子字串、X/Y 和「分から」同時出現，因後面仍可能加相反的「好きみたい」。僅裸 core 或經事前明列、無新命題的短人格開頭／尾句可標保留；其餘一律 mismatch，並逐輪人工核對。若人格表面未保留，誠實回報 mismatch／產品 FAIL，另做獨立表面設計審查；不可在這項偷偷覆寫最後字串或記憶。這使本項仍只有一個 planner 證據權限變因。
5. 不改核心 `uruha_brain_mac.py`、M31/M32、writer、正式 DB 或舊 frozen 檔。允許新產品 overlay、專項測試、既有產品入口 `__main__` 內安裝、新前瞻資料／計畫／結果及 `CURRENT_TASK.md`；保留舊 detached launcher 的 import-only preflight 行為。

## 必須反證的範圍與停止條件

零模型先驗證多個未曝光 X/Y 問句：早期 signal、真 selected、plan 的未知 core、graph 對最後可見日文的誠實狀態、第三者 profile 0；故意讓 RightBrain stub 產生肯定句時，graph 必須報 mismatch，**不得假稱已擋住**。負控制至少含：前批肯定陳述的**不同新 X/Y**、真食物邀請、`ねえ、好き？`、本人問句、引用／傳聞／條件／否定／複句／歧義 X/Y、超過 40 字 core 的輸入、protected／安全、明示記憶要求、中文／英文，以及可用記憶同含 X/Y（應 defer，不將舊資料當作已確認現況）。記憶只有 X 或只有 Y，不能構成相同命題來源。

先跑聚焦、受影響相鄰、compile/diff 與隔離 0-turn。新 Safari 例子要與所有曝光題不同，首輪前逐字 input/gold、≤20.0 秒每輪、0 retry、同 DB 一次 planned restart、row-ID before/after、graph／raw／泡泡／selected、模型呼叫與可得 token／價格逐項凍結 commit＋SHA。若任何語義、來源、profile、graph、安全、成本或程序 gate 失敗，整批 strict FAIL；最多兩個有根據修正批次，不能改舊題追分。成本 ledger 缺值標 unavailable；產品 PASS 也僅證窄日文無證據第三者問句，不證明通用理解、強 LLM 優勢、真人被理解感、正式 temporal holdout、VRM/tool 或人腦方程式。

風險／替代：若現有 memory_data 無法可靠判斷可辨識來源列，先不授權 unknown gate，保留此卡 REVIEW_REQUIRED；不可讓缺失欄位假裝「沒有記憶」。若真人表面仍破壞 unknown，先保留反例並另審表面交付，不能把本項擴成通用最終覆寫；若 M18／M29 仍奪權，先在圖上誠實顯示而非加多個促成成功的例外。圖上陳述 source byte-exact 稽核另立卡，不借本卡修補。

開發期修訂紀錄：設計 commit `dcd095c` 後首次零模型聚焦為 4/5；同隔離 DB 中前一輪**相同問句**被當作 X/Y 既有證據，使第二輪退回無模型 full planner。問句本身不提供偏好事實，故在任何新生成／Safari 之前將「先前相同完整問句」排除於 evidence deferral，另加回歸。原 4/5 失敗保留，不把它說成產品觀察或在曝光題上追分。

首輪前獨立唯讀 preflight 另發現：若可見字串是完整 unknown core **再接**一個「第三者似乎喜歡」新命題，舊圖節點的字串包含／有限正則仍可能標 true。此為稽核真實性缺陷，不改輸出或 gold；在第一次新模型／Safari 前將成功條件縮成明列無新命題的表面語法，補一個對抗測試。發現與修補屬同一工作項、第二個有根據的開發期修正；若仍無法誠實稽核，停在 REVIEW_REQUIRED。

同一首輪前來源稽核還發現：既有 episode 以未跳脫的 `User: ... | Summary: ... | Uruha: ...` 串接，惡意或偶然出現在使用者原話中的欄位分隔符可使正則提早截斷，讓後段已有 X/Y 的原話被誤當成「沒有證據」。這不授權修補整個記憶格式；本 gate 對欄位標籤數量／順序歧義的 episode 與 recent-turn provenance **fail closed**，交回舊路，並加注入型反例。此修補屬上述同一第二批 preflight 稽核完整性修正，沒有改問題、gold、表面生成或先前案例。最新零模型聚焦 6/6；Safari 產品結果仍未知。
