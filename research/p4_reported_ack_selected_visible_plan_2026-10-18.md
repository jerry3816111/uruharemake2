# P4 reported-ack B：selected → visible 單變因產品卡

狀態：首輪前設計與資料凍結；同團隊、非獨立審查。B 只處理已選中的第三者「先確認」承接，不能改 A 的路由、M31 判斷、既有 guard、記憶或 C 延遲。A 首發 FAIL 與 A 修正批 2/2 准入 PASS／產品 FAIL 均保留；before 原件 SHA `9580fd65f4fd4094ae733e9bdcd12fbefba1190e7723c5b009f956cadcd74236`，只供定位，不拿 T1/T5 重播追分。

## 問題、假設與可改邊界

- before：A 修正批普通 T1/T5 的來源、路由、M31 defer、selected act/core 都正確；舊 speech variant 把 `？。` 接在 core 後，語言 guard 降成泛答。T5 後續又把**同輪泛答**錯包成引文。`research/p4_reported_ack_selected_to_visible_design_review_2026-10-18.md` 有逐層證據與靜態路徑。
- 單一假設：在同輪來源與 A 准入完整證明下，將已選 `ack_reported_check_instruction_p4` 實現成來源綁定、自然且不冒充已完成確認的日文，再由原 guard、P4-T/V/W、M39 檢查，能使 selected act 真正到達最後泡泡。不是重新分類來源或放寬 guard。
- 可改：新的 B opt-in module／入口／detached controller、B 專屬測試、新資料與凍結 manifest、此卡、`CURRENT_TASK.md`、結果與必要的圖像展示接線。不得改 A 模組、A 題目／SHA／結果、原 `uruha_brain_mac.py`、actor 模組、P4-T/V/W、M39、正式 DB、原始 dirty checkout 或無關 `output/graduate_application_report/`。
- 實現位置：A 已決策且 `emit_response_if_ready` 說話前，核對 same-turn certificate、admission、route／M22、selected act、非記憶／profile；只在資格完整時把**selected core 與 speech realization 同步**，不在後段用固定字串覆蓋任何失敗。source quote 只供當輪可見句使用，持久 trace 只存 digest／狀態／成本。最後再按實際 final reply 稽核；legacy actor 的 exact-string audit 若被新版合法句取代，保留其原值為 legacy 並顯示 B 實際判定。

實作更窄地限於既有單句語法下、引文為「先に／まず＋確認／チェック＋して／しといて／してね」的無對象報告；其他來源即使 A admitted，B 也不冒充已驗證。最終 B audit 不用 `core in reply` 的寬鬆判法：必須由原句同輪重建候選，核 speaker／quote digest、selected core、graph UTTERANCE、日文 guard、P4-T/V/W 與 M39，且最後泡泡只能是該自然日文候選或既有短口語前綴＋候選。B receipt 僅存 digest／布林，不另寫事實或 profile；既有 selected／utterance／對話日誌仍會保存使用者可見文字，不能把這說成全管線不留 raw。

首輪前零模型預檢（尚未送任何新題給 Web／模型）：初稿的 `チェック` 未形成 M25 reported action，`話してた` 不符合 actor 既有報告 pattern；`言ってた` 又碰舊 false-premise seed。這是在資料凍結前發現的覆蓋設計錯誤，已更正為兩個 `先に確認してね／言っていた` 普通候選及兩個 `言ってた` protected 候選，並保留混合、非報告、身分、未知負控制。最終八句與既有題／fixture 逐字碰撞 0；靜態 source certificate 依序 `1,1,0,0,1,0,1,0`，seed／actual 依序普通、protected、普通、普通、普通、self-intro、protected、普通。這只證實測例可觸發預期前置條件，不是 runtime 路由或產品結果。

## 首輪前條件式 gold

`datasets/p4_reported_ack_selected_visible_fresh_probe_2026-10-18.json` 是開發者自編、**未見輸出**的 8 句／兩 session（T4 後同 DB planned stop/restart）、0 retry。逐字不得與已曝光 A/P4 題目或 B 零模型 fixture 重合。T1/T5 是普通正例；只在實際 A `admitted`、M31 `deferred`／原呼叫 0、high/deliberative、M22 exclusively general、selected reported act、無 profile/memory 的前提下才要求 B commitment。若任一前提沒發生，記 coverage FAIL，不事後改 gold。T2/T7 是 protected 候選；實際 protected 時 B 必須不接管、原 M31 照跑；若未 protected，記 protected coverage missing。T3 混合直接請求，T4 非報告，T6 身分，T8 未知對象均不可被 B 接管。

正例最後泡泡必須是自然日文，保存「第三者說過先確認／check」而不把它當助手當輪命令、不編確認對象、結果、聽者或動機；有來源可見報告語態，不能是 generic fallback 或把 fallback 包成引文。若日文 guard、P4-T/V/W 或 M39 導致最終句失真，該輪 FAIL，即使 B 預選句正確也不補救。負控制也要自然日文、沒有 B 誤接管、protected 與直接要求既有權限不退化；不把 T6 類記憶 bug 或 C 性能說成 B 修好。

## 執行與停止條件

1. 在任何 B 新生成前，完成題目來源碰撞檢查、靜態 source／seed preflight、B 測試、相鄰 A 36 項與受影響回歸、Python compile、`git diff --check`、SHA manifest；commit/push，核 PR #435 head。只有這些到位才放行一次真 Safari。
2. 新 0700 私有 root、專用本機 opt-in 入口、0-turn readiness、離線 ONNX 預熱、明確空 profile；逐題一次、0 retry，T4 planned stop/restart 後同 DB 新 Safari session。每輪觀察 source → A/M31 → selected core/act → guard → P4-T/V/W/M39 → UTTERANCE、實際泡泡與 raw；保存精簡可追溯圖與原件 hash。T0–T8 profile 全內容 digest／row count、episode IDs、PID/port 啟停皆驗。不得碰正式 DB。
3. 成功門檻：正例 2/2 **final** 忠實、所有 B 正負控制 8/8 判定一致、0 protected 接管、8/8 raw＝graph UTTERANCE＝Safari 泡泡、8/8 可見日文、8/8 等待 ≤20 秒、8 distinct episodes、profile 0 rows／same digest、0 extra B model calls。實際 M21/M31 call、token（若全層可核）及延遲另列；資料缺失寫 unavailable。
4. 一項失敗即 strict FAIL，保留原 raw／gold；最多再做一個有根據且全新先凍結的 B 修正批。仍失敗則 `REVIEW_REQUIRED`，不得重播本批追分、降低 threshold 或把圖表當產品證據。B 通過也只授權有限 reported-ack 產品路徑，不授權同模型強 LLM 優勢、人評、temporal holdout、VRM/Function Calling 或整個 Goal。T6 記憶與 C 延遲之後另卡。
