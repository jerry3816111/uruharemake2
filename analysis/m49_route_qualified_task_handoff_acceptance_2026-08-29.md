# M49：任務條件能到達 planner，但還沒有穩定組成完整任務

日期：2026-08-29。安全 worktree、隔離 Web session、Safari 外部瀏覽器。
結論：**M49 exact handoff contract PASS；source-aligned practical-help pipeline FAIL**。

## 這一個 M 改什麼

M47 已能把「想要哪種回覆」和同一句裡的任務片段分開，M45.1 卻可能把整個含 request 的
clause 排除。M49 只把 M47 找到、且和 response-form evidence 不重疊的 current-user task span，
以原始 offset／digest 交給 M46。它不翻譯、不推論缺少的任務、不改 M46/M48，也不把 raw text
寫進長期 person model。

資料流是：

`current user 原文 → M47 response/task span → M45.1 既有來源 + M49 exact span → M46 plan/review`

## 開發中抓到並保留的失敗

第一輪 selected regression 是 **289/290**。英文 `You misunderstood; give me a method.` 的
`You misunderstood` 被 M47 當成 task prefix，會錯誤觸發模型。修正不是加任務白名單，而是讓
候選 span 還必須通過 M45.1 已有的 response/correction classifier；修後聚焦 **47/47**，全選定
回歸 **291/291**。新的 Safari 隔離輪顯示 added_count 0、模型呼叫 0、狀態 awaiting_context。

## Safari 六輪結果

正式 session `20260829_223229_256b70e0`：trace 6/6、可見日文 6/6。

| 輪 | 來源交接 | planner／輸出 | 判定 |
|---|---|---|---|
| 日文三個見出し | embedded span exact 到達並被選 | 保留三個的 goal，交付「先寫一個」 | M49 PASS；步驟仍普通 |
| 日文依顏色分紙 | embedded span exact 到達 | planner 未選、拒絕回答 | M49 PASS；pipeline FAIL |
| 中文按日期分兩堆 | 已由既有獨立來源覆蓋 | 正確交付日文分兩堆 | bounded pass |
| 英文建立三個見出し | 已由既有獨立來源覆蓋 | planner 拒絕 | pipeline FAIL |
| 英文只要求一步 | 無任務來源 | 不猜任務，要求補內容 | safety PASS |
| 日文明確不要方法 | M49/M46 不介入 | 自然日文陪伴 | safety PASS |

新增 exact span 交接 2/2；其中 planner 真正選新增 span 1/2。四個有任務的正向案例只交付 2/4。
六輪共完成 6 次模型呼叫、5362 prompt + 1487 completion tokens，M45 路徑累計 85.46056 秒。
這證明資料可達，不證明模型一定會使用，也不證明回答有用。

## 圖像與證據邊界

- `m49_actual_turn2_observatory_2026-08-29.html` 與 Safari 截圖直接由正式 turn 2 的凍結 JSONL
  runtime trace 渲染，展示「span 已到達，但 planner 沒選」；不是重新生成。
- 正式六輪與 postfix correction raw 分開保存；沒有用修正版覆蓋首次回歸失敗。
- 這不是 holdout、人類偏好、felt-understanding 或人腦方程式證據。

## 下一個必要 M

M50 只修 **compatible current-task source composition**：同一輪中彼此相容的情境、物件、數量、
規則與目標不能讓 planner 任選一段後丟掉其餘片段；要形成可追溯 composite task bundle，且原始
來源仍可逐段核對。M50 不改 M47 路由、不改 M48 表面修補，也不把 same-model review 當人評。
