# M49 下一步：M47 找到的 task constraint 必須真的交給 M46

狀態：M48 後問題定義，尚未實作。M47 route、M48 surface、M46 reviewer 全部固定。

## 單一核心變因

只修 **route-qualified task evidence handoff**：M47 已用不重疊 offset 分開 desired-response
span 與 task spans；M49 將同一 current-user source 中這些 task spans 以 exact offset／digest
轉成 M46 合法 `current_user_task_span`，不再因「任務內容與請求一步在同一 clause」而丟掉：

- `見出しを三つ作るために、今できる一歩を教えて` 應保留 `見出しを三つ作るために`；
- `色ごとに分ける手順を一つだけ教えて` 應保留 `色ごとに分ける`；
- 純 `Give me one step`、`不要方法`、普通提到方法不產生 task source；
- span 必須來自 current user 原文且不與 M47 response-form evidence 重疊；只保存 digest/offset
  到 trace，raw text 只在當輪模型 source packet，不能進 long-term person model。

## 最小驗收

1. task handoff 前後 source packet 對照；embedded constraint 被補入，原獨立 task clause 不重複。
2. tampered offset/digest、response-form overlap、negative/no-request 一律拒絕；不使用 task白名單。
3. M46 plan/reviewer schema 只能引用 handoff 後的 exact source，M48 不改內容。
4. 新 M49 node／圖卡顯示 M47 task span → M46 source → goal/criterion/action → source-alignment結果。
5. 新隔離 Safari 重跑新的中／日／英 embedded-task 案例與 negative；舊 M48 seven-turn 只能當
   exposed development evidence。成功只代表 constraint 到達；若 planner仍忽略，另列 plan failure。

## 不在 M49 範圍

不修 same-model reviewer 的一般語義可靠度、不加物件／數量翻譯白名單、不改 progress taxonomy、
不修 no-method 澄清、延遲、長對話或人評。
