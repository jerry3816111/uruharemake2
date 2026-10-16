# P4 本人偏好快路 selected-plan 競權：第一個前瞻修正批次

狀態：2026-10-17 先定案，已按此單一變因修改語義程式並做無生成模型測試；
**尚未送新模型案例**。
這是 `analysis/p4_source_bound_preference_fresh_product_probe_result_2026-10-17.md`
的下一個產品修正，不改既有五輪 frozen input/gold/結果；該批三輪
已曝光且 strict FAIL，不用作修後 fresh PASS。設計審查是同工作團隊
的非獨立唯讀路徑檢查，不冒充外部研究審查。

## Before、唯一變因與取捨

舊產品 T1 來源本人 `like`、M31 拒權後選 `chat`／fallback，
等待 `26.6754s`；T3 同類來源本人 `like`、M31 11.6307s 授權並由
M32 selected `deterministic_semantic_commit_m32`，既有 fallback 根本
未被選中。T3 仍建立正確本人 profile row，但 selected 契約失敗。
路徑位於 `uruha_brain_mac.py`：M29 candidate 若標
`projection_required=true`，先觸發 M31/M32；後者有權時排在
`LeftBrain.think` 的 rule fallback 前。既有
`uruha_source_bound_preference_fallback_p4.source_bound_preference_plan_p4`
已要求完整單句日文／有物品形態線索／唯一 `subject=user` positive
`like`／postposed denial 後准入／source span 與 value hash 同源。

唯一語義變因：在目前產品 additive overlay 中，僅當**原 M29
candidate 本來要求 projection**且上述同源確定性 rule seed 可建立，
將該 M29 candidate 標為「來源准入 rule 優先」、
`projection_required=false`；其餘欄位保留，audit 僅用 hash／count
不含原句。由 core 原本選路自然落到既有 rule，真 selected 仍須
由原 materializer 依 logic／M21／writer／graph 一致性確認；若前面
有 protected low-road、grounded profile、M33 或其他更高權限，
不得強搶。舊 question overlay 的 `ask_like_me` 優先與 owner writer
均不改。M31/M32 **程式不改**，但對此極窄來源准入類型不再呼叫
M31；這是語義授權策略的明確改變，不隱藏。若來源／物品分類不確定，
保留原 M29→M31/M32 路徑，而非擴詞表追分。

此選擇比「M31 跑完才覆蓋 selected」更能檢驗快路的成本主張；
代價是 bounded grammar/owner admission 必須承擔這類來源語義判定。
不能把 T1 冷啟超時歸因於本競權，亦不能預告此修正必過 20s。

## 範圍與門檻

允許修改：`uruha_source_bound_preference_fallback_p4.py`、相應
`test_p4_source_bound_preference_fallback.py`、必要的產品入口
0-turn/graph 契約測試；**不修改** core `uruha_brain_mac.py`、
M31/M32/M33、writer、問句 matcher、人格、final guard、舊 probe
資料／manifest／結果、正式 DB 或原始 dirty checkout。

先做零模型單元與接線：發展用新正例在原 M29 true 時只改這一
candidate 的 authority 訊號；源准入相同、rule seed same hash、
真選中 `chat`／fallback marker、M21 general planner model call=false，
M31 呼叫數從原 1 降為 0；graph selected 與 utterance 對齊。
負例至少涵蓋第三人稱、引文、本人否認、關係問句／人名、明示
記憶行為、非日文、複句、未知物品型態、原 M29 不需 projection；
不得使 protected route、M28 已有 authority、M33 source atoms、
普通聊天／關係問句選路或 profile writer 改變。先聚焦後受影響
相鄰回歸、0-turn 隔離入口，再做全新 source-only 產品案例。

產品驗收在程式和事前資料／gold／門檻／隔離 lifecycle 均固定後
另建 SHA manifest 並 commit。全新案例不復用上述三句或其物品；
至少兩個不同本人正例、第三人稱與問句負例、一次 planned same-DB
重啟；各輪 0 retry、逐 ID profile/episode delta、真正 selected、
Safari 可見日文與 graph utterance 一致、user wait ≤20s；任一
越界 strict FAIL。若冷啟仍 >20s，成本失敗繼續保留。token 缺值
明記 unavailable。這只可能建立窄範圍產品 route/cost 證據，
不等於同模型強 LLM 優勢、人評、正式 temporal holdout 或完整 P4。

失敗分支：最多兩個有根據的新前瞻修正批次；仍失敗則
`REVIEW_REQUIRED`，保留最小反例與簡化／撤回快路的選項。不可
在看輸出後改 gold、重送曝光輪、加一堆物品專用表面答案。
