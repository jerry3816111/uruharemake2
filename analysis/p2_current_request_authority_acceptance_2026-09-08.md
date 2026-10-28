# P2 Current Request Authority 驗收報告

日期：2026-09-08

## 結論

本工作項 **通過 bounded product acceptance**：當使用者在上一輪要求「只聽」後，又於當輪以自然中文、英文或日文
明確改成「幫我想／找／決定一個做法」，產品現在會讓當輪要求取得優先權，選擇 `solve_regulation`。若當輪沒有可獨立
還原的任務內容，系統沿既有 M47→M45.1→M46 路徑停止在 `awaiting_context`，不從舊對話捏造任務，也不呼叫行動生成模型。

這不是 open-domain 語用理解、人類偏好或完整 P2 通過證據。它只證明一個已重現、可歸因的 current-request authority 缺口已修正。

## 單一變因與邊界

- 新增產品限定 adapter `uruha_current_request_authority_p2.py`，擴充 M47 的中／英／日自然求助句法 family。
- 產生既有 M47 可消費的 typed route、offset、span digest 與 `solve_regulation` policy；不產生回答、不推測私人心理。
- response-form clause 與純謝詞不再被當成 task evidence；真正獨立的當輪 task clause 保留。
- 未命中新句法 family 時，M47 route 與 task-source gate 逐欄維持原結果。
- 沒有改模型、prompt、temperature、token budget、凍結 M47–M54 source、正式資料或長期記憶規則。

## 修改前問題證據

同一隔離產品控制：

1. 前輪：`今日はただ聞いてほしい。`
2. 當輪：`謝謝。不過現在請幫我想一個做法。`

修改前 M47 沒有辨識當輪求助，policy 為空，compact planner 呼叫 qwen2.5:7b 後仍得到中文 core；日文 guard 最後只輸出
`ん、その話もう少し聞かせて。`。這沒有回應「現在改成要方法」，也沒有指出缺少的是哪個任務。

原始證據：`analysis/p2_current_product_controls_local_run1_2026-09-08.json/html`。

## 實作中保留的失敗

- 第一輪 focused 測試為 9/11：日文頓號未納入 clause start，另有測試把 contract-layer trace 誤當 materialized runtime trace。
- 修正後發現 `謝謝` 仍被 M45.1 當成 task，會不當授權行動模型。沒有隱藏此失敗；加入 source gate adapter，將純謝詞與
  response-form clause 排除。
- 混合相鄰測試曾 116 pass／1 fail：測試依賴安裝順序所造成的 `removed_count` 差異。最終斷言改為檢查語義不變量
  （最後無 task、謝詞與 response form 都被排除），沒有放寬產品安全條件。

## 測試證據

Focused：14/14 pass。覆蓋三語 positive family、negative scope、普通提及、後句覆蓋前句、無 task fail-closed、獨立 task
保留、未命中路徑逐欄相同、trace 唯一且無 raw dialogue 複製，以及隔離兩輪產品 contract。

相鄰組：119/119 pass，8 個既有 dependency warnings，28.66 秒。包含 M45.1、M45、M46、M47、M48、M49、M50、P2
expression、compact planner、grounded validation 與 P1 identity。

JUnit：`analysis/p2_current_request_authority_tests_2026-09-08.xml`。

## 本機真實產品輪次

最終 run 使用本機 qwen2.5:7b、隔離 memory/session，沒有 mock model、沒有正式 DB／holdout／人評。

| 指標 | 修改前控制 | 修改後控制 | 觀察差異 |
|---|---:|---:|---:|
| 目標輪 policy | 無 | `solve_regulation` | 當輪求助取得權限 |
| 目標輪 final | `ん、その話もう少し聞かせて。` | `今、どの作業で困ってる？ そこだけ教えて。` | 精確詢問缺少的 task |
| 目標輪一般 planner call | 1 | 0 | -1 |
| 目標輪 latency | 9.035225 s | 1.749318 s | -7.285907 s（觀察值 -80.64%） |
| 全 5 sessions／9 輪 calls | 4 | 3 | -1（-25%） |
| 全 run tokens | 6,096 | 4,471 | -1,625（-26.66%） |
| 全 run model-call seconds | 31.579485 s | 22.995762 s | -8.583723 s（-27.18%） |
| 全 run elapsed | 45.554864 s | 37.170483 s | -8.384381 s（-18.41%） |
| 結構 checks | 4/4 | 4/4 | 保持 |

全 run 時間與非目標生成含本機及生成隨機性，只是觀察成本，不把百分比外推為一般效能。可直接歸因的是：目標輪改走
deterministic fast path、沒有一般 planner call、M46 action model calls 為 0。

目標圖實際包含 `current_request_authority_p2 → crosslingual_help_routing_m47 →
route_qualified_task_handoff_m49 → current_task_source_bundle_m50 → goal_progress_delivery_m46 →
actionable_help_delivery_m45 → visible_language_guard`。節點顯示：三語 route 為 authorize、task 為空、M46 介入但停在
`awaiting_task`、M45 為 `awaiting_context`、0 model calls；上一輪 M27 結果為 `uncertain`，沒有假記 `supported`。

原始證據：`analysis/p2_current_request_authority_local_run1_2026-09-08.json/html`。

## 未通過與下一個單一問題

- Safari：未驗收。既有 Computer Use 已拒絕目前網址並結束 session，本批不繞過工具限制。
- control 1 的模型 core 已是貼題的 `また今度ね。`，但 active validation 仍覆蓋成不相關的二選一；這是下一個最小產品問題。
- control 3 仍在使用者要求獨處後追加無來源的「沒睡／想事情」二選一。
- quoted-source 與 cross-session correction/source recall 仍失敗；本批沒有一起修。
- 沒有真人主觀評分、未消耗 holdout、不是 same-model baseline superiority、不是 production readiness。
