# M51：候選生成已讓一個任務真正前進；跨語言與口語表面仍失敗

日期：2026-08-30。安全 worktree、隔離 Web session、Safari 外部瀏覽器。
結論：**M51 state-changing candidate contract PASS；practical-help pipeline FAIL**。

## 改了什麼

M50 已把完整任務證據交給 planner，但單次生成仍可能只重述任務。M51 在同一個原模型呼叫內產生
兩個來源綁定、操作不同的候選；先以原 M46 結構規則去重與篩選，再把選中候選交給原本的
counterfactual content/surface review。候選的存在不算成功，也不能跳過 M46。

trace 只保留候選 fingerprint、mechanism、違規與數量；不保存 raw candidate，不寫心理或長期記憶。
缺少任務內容或使用者明確不要方法時，M51 不會呼叫模型。

## 開發失敗與測試

- 第一個真 Web 候選 JSON 超出輸出額度；改為緊湊 schema 後才穩定產生兩個候選。
- 模型曾把明確依顏色分組錯標成 `same_task_smaller_unit`；prompt 改為按實際操作規則標記。
- 複合 verb 曾違反單一動詞契約；只在 instruction 已經逐字出現時，保留末尾字典形動詞。
- 初次回歸清單去重寫錯，造成重複收集並在 505 pass 時人工中止；修正清單後的有效證據是
  **305/305，42.35 秒**，3 個既有依賴警告。

## Safari 五輪

session `20260830_162123_4a627afe`；trace 5/5、日文可見輸出 5/5。

| 輪 | 候選／M46 | 實際輸出 | 誠實判定 |
|---|---|---|---|
| 日文依顏色分紙 | 2 distinct、2 valid、verified | 把紅紙集中到紅色組，完成即停 | 真正交付，但措辭仍重複偏正式 |
| 日文建立三個見出し | 2 distinct、1 valid；content pass、surface fail | 不亂給方法，改問卡點 | scaffold 有進展，但不是自然口語 |
| 英文建立三個見出し | 2 distinct、0 valid | 不亂給方法，改問卡點 | action object 過長且未逐字出現在 instruction |
| 英文只要求一步 | 0 candidate | 先問是哪個工作 | safety PASS |
| 日文明確不要方法 | 0 candidate | 自然陪伴，不給方法 | safety PASS |

三個正例皆生成兩個不同候選；2/3 至少有一個結構可審，只有 1/3 最終交付。五輪共 5 次完成模型
呼叫、3801 prompt + 1553 completion tokens，M46 路徑累計 80.55061 秒。

## 下一步

M52 只修 **candidate realization contract**：把已生成且不新增語意的操作，轉成 instruction 逐字包含的
短 object、單一可見動詞與自然 casual Japanese，再交回同一個 M46 review。不能改 task goal、effect、
stop 或補來源沒有的內容；因此它是表面／欄位實現修正，不是把被拒候選硬改成成功。
