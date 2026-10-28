# M50：完整任務來源已組成；planner 仍只會重述任務

日期：2026-08-30。安全 worktree、隔離 Web session、Safari 外部瀏覽器。
結論：**M50 exact source-bundle contract PASS；practical-help pipeline FAIL**。

## 改了什麼

M49 已讓嵌入 task span 到達 M46，但 planner 可以任選一段而丟掉同輪其他條件。M50 將同一
current-user turn 中、已通過 M45.1/M49、offset 不重疊且無 observable correction 的 exact
fragments，按原順序組成唯一 `current_task_bundle_m50`。它不翻譯、不補任務語意；component
ID／offset／digest 留在 trace，raw text 不寫長期模型。結構共現不冒稱語意相容證明。

## 開發失敗與測試

- 第一個 Web 啟動曾因 wrapper 呼叫不存在的 chained `main()` 而失敗；改回既有 `build_demo`
  啟動契約後才進 Safari。
- 首次合併測試有兩個 M49 失敗，原因是 M50 測試模組全域安裝污染同一 pytest process；改為
  測試局部 patch 後，M49 舊契約與 M50 新契約同時成立。
- M50 聚焦：54/54。M16–M50 選定回歸：**298/298，43.03 秒**，3 個既有依賴警告。

## Safari 五輪

session `20260830_155659_16416b2e`；trace 5/5、自然日文 5/5。

| 輪 | M50 | M46／輸出 | 誠實判定 |
|---|---|---|---|
| 日文三個見出し | 2 fragments → 1 bundle | `先寫一個` 被判 nonprogress | 正確拒絕弱步驟 |
| 日文依顏色分紙 | 2 fragments → 1 bundle | 只重述 `分開` 且漏 stop | planner FAIL |
| 英文建立三個見出し | 單一來源，不強行 bundle | action relabel，拒絕 | planner FAIL |
| 英文只要求一步 | 0 source | 不猜任務 | safety PASS |
| 日文明確不要方法 | M50/M46 不介入 | 自然日文陪伴 | safety PASS |

完整 bundle ledger 2/2，且兩輪都只剩一個 planner source；但三個有任務案例交付 0/3。
這不是倒退：M49 曾把「先寫一個」錯標為 scaffold 並交付，M50 讓完整來源出現在同一審核面後，
模型這次把它標成 `same_task_smaller_unit`，M46 正確拒絕。五輪共 3 次完成模型呼叫、2623 prompt
+ 697 completion tokens，路徑累計 43.46428 秒。

## 下一步

M51 只修 **state-changing candidate generation**：在不放寬 M46 gate 的前提下，先產生少量來源
綁定的候選，再由既有 M46 規則選擇真正比原任務更具體的 operation；找不到就維持拒絕。不能
用物件白名單硬寫答案，也不能把 same-model reviewer 當人評。
