# P2 表達層架構修正：模型核心不再被無來源固定句覆蓋

日期：2026-09-08
判定：**本工作項的預先條件通過；P2 整體仍 partial。**

## 解決的實際問題

P2 compact planner 已能在 20 秒產品預算內產生三個候選，但選出的自然日文核心還會被舊表達層加上
輸入 hash 決定的前綴、固定 `そのくらいでいいだろ。` 尾句，短句又會被 density-only repair 再加工。
這些字不是來自當輪 plan、記憶、人格證據或安全契約。

本次只在產品入口、且 `compact_general_plan_p2` 真正完成的普通 `direct_chat_answer` 啟用
`uruha_contextual_expression_commit_p2.py`：保留 sanitize、self-monitor、visible-Japanese guard 與所有保護路徑，
但沒有來源的三種 decorator 不得覆蓋模型已選出的完整核心。沒有增加模型呼叫或長期記憶寫入。

## 修改前後的同一六輪本機結果

| 輸入 | 2026-09-07 修改前 final | 2026-09-08 修改後 final |
|---|---|---|
| `そう、それでいい。` | `先に、うん、そのとおりだ。そのくらいでいいだろ。` | `うん、その通りだ。` |
| `うん、聞いてくれてありがとう。` | `いや、ありがとう。そのくらいでいいよ。そのくらいでいいだろ。` | `うん、助かったよ。ありがとう` |

其他四輪 final 逐字相同。六輪 M27 ledger 逐欄相同，P1 八項 identity／restart／persistence assertions
也逐項相同且全過。這表示本輪只證明「已完成 compact direct-chat 的 core-to-surface commit」被修正，
不是整個理解／記憶能力變強的證據。

第一次完整 re-run 仍失敗：自我監控把短核心判為 density 不足，再次呼叫 refinement，得到
`うん、そのとおりだ。そのくらいでいいだろ。` 與 `さっきの:方法はいらない。ただ聞いてほしい。`。
該失敗完整保存在 `p2_contextual_expression_commit_intermediate_failure_2026-09-08.json/html`；之後只補上
「當 candidate 就是已選 core 時，不以 density 為由重新裝飾」這個同一變因，沒有加入測試句或答案規則。

## 圖、模型與成本證據

- 最終六輪本機 probe 有 2 次實際 qwen2.5:7b compact calls，正好 2 個 `compact_general_plan_p2` 節點與
  2 個 `contextual_expression_commit_p2` 節點。
- 兩個表達節點均記錄 selected core、SHA-256、被抑制的 decorator、語言 guard 結果，且
  `final_visible_surface_matched=true`。最終 HTML 是現有 node graph，不是另做結果頁。
- 修改前／後模型呼叫數都是 2；總 tokens 3,124／3,103。差異包含前輪可見文字改變造成的 prompt 差異，
  不能宣稱節省 21 tokens 的普遍效果。
- 模型呼叫時間 15.353957／15.586987 秒；六輪總時間 30.651133／31.687837 秒。單次順序執行未控制
  cold/cache，不能宣稱延遲改善或退步百分比。
- adapter 自身增加 0 模型呼叫、0 retries、0 長期記憶寫入；compute ledger 不含所有 native/embedding 成本。

## 測試證據與誠實限制

- P2 expression＋compact＋grounding＋P1 focused/adjacent：34/34，13.94 秒。
- 首次將下游契約混在同一 process 時是 92 pass／3 fail；原因是新測試在 collection 階段安裝產品 overlay，
  污染後續 class inspection／全域狀態。改成逐測試安裝與還原後，同一 process 完整相鄰組為
  **95/95，18.47 秒**；沒有刪除或放寬原斷言。
- contract 六輪仍通過 P1 八項 assertions，但 mock backend 沒有實際 compact call，故不是此次表達修正證據。
- Safari 控制工具先前拒絕目前網址並終止 session；依交接規則保持 pending，未用其他 UI 技術繞過。
- 第一批 5 sessions／9 輪開發控制尚未用目前 compact 產品重新跑；P2 對新請求、撤回、引述、婉拒與
  無上下文指稱的整體語用品質仍不能宣稱通過。

## 證據檔案

- 修改前：`p2_compact_six_turns_run1_2026-09-07.json/html`
- 中途失敗：`p2_contextual_expression_commit_intermediate_failure_2026-09-08.json/html`
- 最終本機：`p2_contextual_expression_commit_local_run1_2026-09-08.json/html`
- 前瞻工作卡：`research/p2_contextual_expression_commit_plan_2026-09-08.md`

## 下一個唯一工作

不直接寫新規則。先用目前產品入口重跑既有 5 sessions／9 輪開發控制，記錄哪些輪真正走 compact planner、
model core、最終 surface、M27 與成本；將錯誤歸到理解／記憶／決策／表達其中一層。只有得到新的失敗證據後，
才決定 P2 的下一個有限工作項；不進 P3，不新增 M，也不把作者案例改稱 holdout。
