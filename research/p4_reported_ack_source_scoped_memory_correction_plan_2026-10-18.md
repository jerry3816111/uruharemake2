# P4 reported-ack B：來源限定／背景記憶修正批（首輪前）

狀態：同團隊前瞻設計；不是獨立 holdout。首發 B Safari 原件 SHA `020de8e7a6b526e03b15f4f0a1a28bbaa2efc9bf6037786692ad86907e817c7e`、正例 1/2／strict FAIL 保留，不重播舊 T5、不改舊 gold。失敗因果與排除方案見 `research/p4_reported_ack_selected_visible_postfailure_review_2026-10-18.md`。

## 唯一核心變因與邊界

把 B 的報告承接改成**只對本輪可見的第三者引文作主張**。這個來源限定同時要求兩個不可拆的實現條件：候選句不得宣稱全局「還不知道確認什麼」；B 可接受有來源 ID 的被動 episode 背景，但不可把它當作答案證據。若只放寬 gate 而保留未知斷言，前文已知對象會被否定；若只改句而保留過寬 gate，跨 session 正例仍遭阻擋。兩個條件同屬「B 最終句的主張來源」，不改記憶檢索、記憶答案、A/M31 路由、persona、語言 guard 或 speech 後驗收。分別以零模型 ablation 驗明必要性，產品主張只限這個組合。

現有 `memory_use_expected=false`、`background_only/latent_ok` 不是「確認對象不存在」。B 只在 `memory_anchor` 缺席，或 anchor 是 `kind=context`、`expected=false`、`source=episode`、有 `trace_id`／`memory_id` 且 `provenance_channel=selected_working_memory`、speakability 為 `background_only/latent_ok` 時准入；其他來源、缺欄位、`memory_use_expected` 非明確 false、顯性 recall、profile/grounding、sensitive/third-party suppression、protected route、來源／selected 不一致，一律維持不接管。receipt 記錄權限種類和 ID digest，不複製原文。當輪可見句最多表示「你說 X 說過 Y」的承接，不把引文當成已驗證的第三者事實，也不捏造接收者、確認對象或結果。

允許檔案：`uruha_reported_ack_selected_visible_p4.py`、`test_p4_reported_ack_selected_visible.py`、本卡／新 dataset／新 SHA manifest、`CURRENT_TASK.md`、結果分析，以及若確有必要的 B 隔離啟動與圖像呈現接線。舊資料、舊結果、A 模組、原 `uruha_brain_mac.py`、`uruha_memory_runtime.py`、正式 DB、原始 dirty checkout、無關 `output/graduate_application_report/` 不改。此修正不建立 typed 確認對象記憶，也不聲稱修好 T2/T3/T6 或所有記憶問題。

## 事前題、gold、成本

新 developer-authored 八輪在 `datasets/p4_reported_ack_source_scoped_memory_fresh_probe_2026-10-18.json`，兩個 Safari session、T4 後同 DB planned restart、每句一次／0 retry。T1 是無相關舊記憶的普通引文；T2 明說確認對象；T3 是已知對象後的普通引文；T5 重啟後再測普通引文。T1/T3/T5 的**條件式**正例只在 A admitted、M31 deferred／0 模型呼叫、high/general、selected ack，且 B 看見無 anchor 或上述可追溯被動 episode 時要求 final visible。任何一個條件沒發生記 coverage FAIL，不把它改列負例。T4 若實際 protected，B 不得接管且原 M31 照跑；若未 protected，保留 coverage missing。T6 顯性回憶、T7 混合直接請求、T8 未知非報告皆不可由 B 接管；其原有答案品質另列，不能借 B 掩蓋。Profile／不完整 anchor／suppressed memory 的 fail-closed 用零模型契約測，不假造正式 profile 來湊 Web 覆蓋。

資料凍結前的零模型預檢發現 `まず確認...`／`先に確認しといて` 雖符合較寬的引文語法，M25→actor 卻沒有 `reported_check_instruction` 動作證明；候選已改成 M25 可觀察的 `先に確認して(ね)` 變體，**不因此擴張分類器**。以下最終題尚未送模型或 Web。

最終 preflight：T1/T3/T4/T5 靜態同輪 source certificate 皆 true，其他四題 false，與事前角色 8/8 一致；T7 的直接請求 M25 cue 有出現，但完整報告 certificate false。逐字檢索歷史 repo 題目發現初稿 T5 已被 P4-AT 用過，已在凍結前換成全新句；最終八句與其他 repo 題目／fixture 逐字碰撞 0。這只驗前置題型，不預支真 runtime high/general、protected 或產品結果。

正例 final 必須自然日文，逐字保留本輪說話者與引文、非命令式承接，不加全局未知、虛構目標、完成確認、私人狀態或 generic fallback；原 guard、P4-T/V/W、M39 均接受，圖 UTTERANCE＝raw＝Safari 泡泡。已知對象反例只驗 B 不否定先前明示資訊；不以這批證明記憶檢索／顯性作答正確。流程門檻：八輪各 ≤20 秒、8 distinct episode、T0–T8 profile 全量 0 rows／同 digest、0 額外 B 模型呼叫、記錄 M21/M31 實際呼叫、token 若無可靠資料標 unavailable。任一 B 正例不達 final／保護誤接管／圖或語言不一致即 strict FAIL。

首輪前先做逐字碰撞、靜態 source/seed 預檢、零模型及相鄰回歸、編譯、diff review、SHA 凍結、commit/push、PR head 核對。只在此後啟動新 0700 隔離 root、空 profile、離線模型預熱與 Safari。保存 raw hash、逐輪圖證、PID/port／profile 收據、失敗與成本。失敗保留；這是 B 唯一有根據的前瞻修正批，若仍失敗即 `REVIEW_REQUIRED`，不再加詞彙 patch 或重播曝光句。通過也只授權有限 reported-ack 路徑，不是完整產品、同模型強 LLM 優勢、人評或 temporal holdout。
