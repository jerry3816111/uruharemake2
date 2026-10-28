# P4-D-G：當輪決定權限的圖表投影（實作前凍結）

日期：2026-10-23。此項是 D 首批 strict FAIL 後的**新單變因圖表修正**；不重跑或修改已曝光 D0–D10，不改其 gold、回覆或結論。D 原始結果仍是 3/3 普通承接、1/1 明示訂正承接的狹義效果，whole-batch FAIL。

## Before 與因果定位

- D 真 Safari 的四個准入輪次，`logic`、`runtime_trace` 和 blackboard D row 均有 `current_user_decision_ack_authority_p4` 終端憑證，`selected_status=source_authorized_plan_selected`、`terminal_status=trace_and_episode_reported_match`。但 blackboard `selected_plan` 的 `intent` 沿用 `deterministic_semantic_commit_m32`，圖表 `_graph_signal()` 優先顯示此欄，D row 則退化為 `36 fields`。旁觀者因而看不出已選的 D 路徑。
- `uruha_current_decision_ack_authority_p4.py` 會在選定時保留舊 intent、寫入黑板的 `post_gate_selected_plan_authority`，最後以 source／reply／episode 核對憑證。`uruha_memory_observatory.collect_cognitive_graph()` 卻逐 row 使用泛用 signal；Web 僅呈現該圖。這是 presentation projection 落差，不代表已證明 D 決策錯誤。
- 非 D 輪次也可能有別的 `post_gate_selected_plan_authority`。**不可**全域把 marker 排到 `intent` 之前，更不可改 D 的生成、路由、guard、DB 或 trace。D2 日文自然度、D5 衝突值、原生 Safari 可保存視覺、完整 token ledger 是獨立問題。

## 唯一變因與允許檔案

僅在現有 graph collector 的 D 專屬投影加兩個 bounded signal：D 憑證 node 顯示「當輪本人申告／訂正；來源與回覆已核對」，`selected_plan` node 顯示「已選 D 當輪承接」。**只改顯示 signal**，不改 node/edge 數量、kind、detail、raw trace、reply、episode、memory、DB、其他 route 或原有 D 產品四檔。允許檔案：`uruha_memory_observatory.py` 的局部 graph helper／collector、全新 `test_p4_current_decision_graph_authority_projection.py`、本研究文件／凍結 SHA／結果報告、`CURRENT_TASK.md`。不修改 Web 或 D gate；既有 D opt-in entry 使用同一 graph renderer。

投影准入採 fail-closed 的同輪一致性檢查：result 有當輪 `user_text`／`reply`；D cert 在 `logic`、`runtime_trace`、唯一 blackboard D row 完全一致；用 D 純函式依當輪 raw 與 cert stamp 重算 binding／source 欄位；terminal／pre-episode／visible／profile status 正確；cycle、raw SHA、authorized/pre-episode/terminal/final reply SHA 與當輪文字一致；`selected_plan` 唯一 row 的 D marker 與 D 回覆一致；logic 的 planner path／core message 是 D；guard 的 final reply 與唯一 utterance row 也一致。任何缺失、重複 row、stale cycle、偽 marker、cross-route、混合 cert、reply mismatch 都退回既有圖訊號，不提升 authority。Web 的一般 D `episode_doc` 在 observatory payload 可為空；此處不得再假裝核 episode，只能依賴 D 交付時已產生的 terminal status 並核當輪 raw/reply/cycle/utterance。這只是內部 trace 一致性，不是對外部世界真實性的密碼學證明。

## 凍結的新案例與判準

`datasets/p4_current_decision_graph_authority_projection_probe_2026-10-23.json` 在實作前固定純結構、零模型案例，使用未出現在 D 題本或 repo 的 2081 年／地點：一個普通 User 決定、一個明示訂正；負控包含缺 cert、缺 terminal、舊 cycle、來源 SHA 錯、回覆 SHA 錯、同輪 D row 不一致、非 D route 偽 marker、原有其他 gate marker、重複 D／selected row、utterance／guard 不符及 binding SHA 錯。資料只生成隔離測試結果，不送入正式長期記憶。凍結前對新日期／地點排除本檔搜尋 repo，逐字碰撞 0。

成功：新正例 2/2 的 graph node signal、HTML 可見 D 已選且來源核對；負控 13/13 不顯 D authority；正負例的 node/edge topology、非 D signal、`result` 原件完全不變；圖細節預算不退化。若任一失敗則本項 FAIL。先零模型 focused tests 與受影響 graph/Web 回歸，再從**新的隔離 root、全新 prospective source** 做真 Safari 當輪與 reload 觀察（0 retry、記錄可保存性與實際成本），不得以舊 D log 回放作 fresh product 證據。上限：新增模型呼叫 0（契約），真 Safari 每個 prospective 題各 1 次、≤20 秒/輪的既有產品門檻；無原生 PNG/AX 持久證據就標 saved-visual 未達，不冒稱 full product PASS。

若第一批無法在 frozen 范圍內成立，最多兩個有原因的修正批次，仍失敗則 `REVIEW_REQUIRED`；不得修改 D 原題或把 graph 投影視為人類理解、同模型優勢或整個 Goal 完成。
