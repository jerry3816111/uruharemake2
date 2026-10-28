# P4 repair-cue 既有模組接入 M29 優先產品鏈：單變因事前計畫

狀態：**code 前凍結**。before 是 `analysis/p4_turn_admission_stateful_f1_zero_model_route_failure_2026-10-24.md`：f1 僅零模型完整輪次就出現 `終えた`→`repair_check`，故 f1 沒有 Safari Send；原 f1 gold 不改。既有 `uruha_repair_cue_boundary_p4.py` 已有引號外獨立 `え` 邊界，`test_p4_repair_cue_boundary.py` 和 2026-10-20 Safari 探針證明分類局部效果，但**舊六輪整批 strict FAIL**，不得把它包成完整回覆品質。現行 `uruha_web_ui_product_p4_direct_reply_act_m29_priority.py` 未安裝該 overlay，現行 controller 亦未傳 `URUHA_P4_REPAIR_CUE_BOUNDARY=1`。重寫核心 `uruha_brain_mac.py` 會重做已有算法、擴大影響並使歷史鎖檔失效；本批不採。

## 單一變因、允許檔與拒絕條件

唯一功能變因：讓**現行 M29 優先產品入口**可顯式 opt-in 啟用**既有** repair-cue overlay。入口無論 flag 是否開都只安裝一次 wrapper；flag off 不改任何行為。控制器新增 `--repair-cue-boundary`，只准 `start --mode product`；僅該 product child env 設 `URUHA_P4_REPAIR_CUE_BOUNDARY=1`。預設、inert、prepare/status/stop、shell 偽造 env、既有 journal/port/direct-act arm、其他控制器都不變。不得改 overlay regex、`uruha_brain_mac.py`、planner/候選/guard/記憶、背景 scheduler、模型參數、原 f1 題／gold、舊結果與正式資料。允許追蹤檔：本計畫、preimplementation SHA、上述入口／控制器、其聚焦 tests（含 f1 開關雙臂）、必要結果報告、`CURRENT_TASK.md`。

失敗須保留：f1 的第一次 `1 failed` 與其作為產品 go/no-go 的 FAIL 不改判。修後在新變因下 f1 只作**歷史失敗的開發 regression**；不能重送它、也不稱 f1 product PASS。若 opt-in wrapper 對任何更高優先分支、其他五個 repair cue、真正 `え？`／`え、`、引號內「え？」、受保護情境造成未預期改動，或 controller 違反 action 範圍，就不進新 Safari。真模型、native graph、人評、比較、完整 Goal 均未由本 code 批放行。

## before／after 契約與測試順序

1. 凍結本計畫及入口、控制器、既有 overlay、既有 overlay tests、f1 route test 的 SHA；提交推送 PR #435 並核 exact head。先新增 failing focused tests：控制器僅 product start 注入 flag、默認與其他 action 拒絕、shell injection 不漏；f1 isolated fake full-turn 在 opt-in 後應由同一 `brief_encouragement`→M21 full/compact→`direct_chat_answer` 且 final＝episode、one fake model call。不能只在假 harness 開 flag 而產品 child 不開，也不能只改 gold。
2. 實作最小入口安裝與 controller flag/env。0 真 provider calls 先跑 focused 再跑受影響相鄰：`test_p4_repair_cue_boundary.py`、M29 direct act、controller opt-in/journal/port、f1 route、guard/表面。至少驗 opt-out 原 `終えた`→`repair_check` 與 opt-in `direct_chat_answer`，真 `え？` 仍 repair、詞內 `見える／教えて／言い換える／終えた` 不 repair，quote-only 的 `え？` 不被當使用者追問；其他語言 cue 和高優先分支不變。舊 overlay suite 若只因 entry composition 新增而變，要逐項解釋，不鬆舊 fixture。
3. 結果核實：diff review、受影響測試與實際 fake full-turn、source SHA，只有局部 opt-in route 成立才能寫 code PASS。不得把新 wrapper 0 模型呼叫當整體節省，也不得把 selected act 正確當可見回覆品質。先 scoped commit/push/PR head；下一個產品題另做 source-disjoint、gold/資源/Safari gate 事前凍結，才准隔離真 Safari 一次／0 retry。至多兩批有根據修正；仍失敗列 `REVIEW_REQUIRED`，不無限加規則。
