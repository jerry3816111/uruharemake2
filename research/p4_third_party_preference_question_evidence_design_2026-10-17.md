# P4 第三者偏好真問句：未知證據優先權設計審查

狀態：2026-10-17，**下一個單一產品語義變因的設計定案；同團隊非獨立審查，尚未實作／驗收**。前批六輪原題、gold、raw、strict FAIL 不改、不重播；見 `analysis/p4_current_statement_source_authority_fresh_product_probe_result_2026-10-17.md`。本項不是修復該批 source graph byte-exact 稽核，那是獨立後續變因。

## Before、可反駁問題、唯一變因

前批 T4 `後輩は抹茶玄米茶が好き？` 是真第三者問句。新陳述來源證書正確未授予；M29 未要求投影、M31 不適用；M21 full planner 產生 `後輩も抹茶玄米茶が好きか。そのくらいでいいだろ。`。`か` 語氣有歧義，但回覆沒有說現有證據不足，`も` 也無來源。既有 `frame_shadow` 報 preserved 卻未偵出；故缺口在**無證據問句的 epistemic authority 進入 selected plan 前**，不是在肯定陳述准入或人格尾句。

單一變因：對**完整、直接、單句、窄日文** `XはYが好き？/?` 的第三者偏好問句，若當輪不是證據、當前可用記憶又沒有 X/Y 同時出現、且原規則沒有 protected／其他已授權 plan，讓來源可驗的「目前無法判定」取得 rule-plan 優先權。回覆只表明目前可見談話不足，不聲稱第三者客觀不喜歡、使用者從未說過，亦不把問句寫成 profile 事實。任何情況均不能把這個 gate 稱為「模型知道心理／世界事實」。

## 有界資料流與權限

1. 用與上一項同等保守的關係稱謂 X、物品頭 Y、長度和單句約束解析真正問句；明確排除本人、うるは／第二人稱、未知姓名、人名物品、關係問句、引文／傳聞／條件／否定／多子句、非日文、危機／暴力／性等 protected cue。解析問號是 speech act，不可為了重用 assertion parser 而讓合成句獲得陳述證書。
2. 先呼叫既有 `_rule_based_plan`；其 protected、grounded-memory、關係、安全、修正等**任何非 `None` 計畫**一律不覆蓋。只讀本輪 `MemoryManager.query_all_layers` 已交給 planner 的 `recent_turns[].user`、選入的 `working_memory_items` episode 的 `User:` 片段，以及 `memory_provenance.passed_to_leftbrain` 的 `direct_episode`／`recent_turns` 來源之 `User:` 片段。**只檢查來源中的使用者原話，不把 assistant、summary、相似度或 profile 當第三者事實。** 若某一可辨識來源原話同時涉及同一 X/Y（可能有舊記錄、否認或矛盾），保守交還原路，不依單一檢索項推斷目前真實偏好；只有 X 或只有 Y 不構成相同命題。無法辨識必要欄位／來源形狀時也交還原路。這個版本的「無證據」僅指**當輪提供給 planner 的可辨識來源列中未找到**，絕不宣稱整個 DB 或人的世界中沒有證據；亦不宣稱已解已知記憶問答。
3. 無證據時建立 `chat`／casual 的有界 plan，core 用自然短日文表明「X が Y を好きかは、今の話だけじゃ分からないな」，保留原 X/Y，不加 `も` 或推定結論。來源證書只含問句／X/Y digest、`evidence_status=not_found_in_available_context`、rule authority，無原文、無 M31 模型授權、無心理／長期記憶寫入。早期 classifier 與實際 selected plan 必須使用同一決策；M18／M29／M33／安全等後續更高權限可能改選，未真選便不得在圖上宣稱 gate 已執行。
4. **不短路 `RightBrain.speak`。** 既有人格表面／model-surface trace／visible-language guard 照常執行；圖上僅在真 selected 後顯示「問句→可用證據不足→未知方案→實際表面」，並獨立核對後者是否仍保留 X/Y 與明確未知、沒有把問句變成已知偏好或無依據的 `も`。若人格表面未保留，誠實回報 mismatch／產品 FAIL，另做獨立表面設計審查；不可在這項偷偷覆寫最後字串或記憶。這使本項仍只有一個 planner 證據權限變因。
5. 不改核心 `uruha_brain_mac.py`、M31/M32、writer、正式 DB 或舊 frozen 檔。允許新產品 overlay、專項測試、既有產品入口 `__main__` 內安裝、新前瞻資料／計畫／結果及 `CURRENT_TASK.md`；保留舊 detached launcher 的 import-only preflight 行為。

## 必須反證的範圍與停止條件

零模型先驗證多個未曝光 X/Y 問句：早期 signal、真 selected、plan 的未知 core、graph 對最後可見日文的誠實狀態、第三者 profile 0；故意讓 RightBrain stub 產生肯定句時，graph 必須報 mismatch，**不得假稱已擋住**。負控制至少含：前批肯定陳述的**不同新 X/Y**、真食物邀請、`ねえ、好き？`、本人問句、引用／傳聞／條件／否定／複句／歧義 X/Y、protected／安全、明示記憶要求、中文／英文，以及可用記憶同含 X/Y（應 defer，不將舊資料當作已確認現況）。記憶只有 X 或只有 Y，不能構成相同命題來源。

先跑聚焦、受影響相鄰、compile/diff 與隔離 0-turn。新 Safari 例子要與所有曝光題不同，首輪前逐字 input/gold、≤20.0 秒每輪、0 retry、同 DB 一次 planned restart、row-ID before/after、graph／raw／泡泡／selected、模型呼叫與可得 token／價格逐項凍結 commit＋SHA。若任何語義、來源、profile、graph、安全、成本或程序 gate 失敗，整批 strict FAIL；最多兩個有根據修正批次，不能改舊題追分。成本 ledger 缺值標 unavailable；產品 PASS 也僅證窄日文無證據第三者問句，不證明通用理解、強 LLM 優勢、真人被理解感、正式 temporal holdout、VRM/tool 或人腦方程式。

風險／替代：若現有 memory_data 無法可靠判斷可辨識來源列，先不授權 unknown gate，保留此卡 REVIEW_REQUIRED；不可讓缺失欄位假裝「沒有記憶」。若真人表面仍破壞 unknown，先保留反例並另審表面交付，不能把本項擴成通用最終覆寫；若 M18／M29 仍奪權，先在圖上誠實顯示而非加多個促成成功的例外。圖上陳述 source byte-exact 稽核另立卡，不借本卡修補。
