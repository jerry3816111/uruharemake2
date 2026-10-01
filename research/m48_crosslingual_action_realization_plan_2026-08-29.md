# M48 下一步：跨語言 task plan 必須落成同一個自然日文動作

狀態：M47 後問題定義；尚未實作。先讀交接 §7.61、M47 acceptance 與三個 M46 rejected
diagnostics。M47 route 及 M46 content/usefulness gate 固定，不用結果回寫舊里程碑。

## 單一核心變因

只修 **structured action plan → final Japanese instruction 的一致實現**：

- 內部 `action_object_jp`、`action_verb_jp`、`action_step_jp`、`completion_jp` 已形成時，
  visible instruction 必須實現同一 object／operation／stop；
- 可做 bounded deterministic surface repair，但不能新增 task object、進展機制、排序規則、
  工具、期限或私人事實；語義欄位不完整時 fail closed；
- 中文、英文、日文 source 都只走同一 realization contract，不加報告／書架／信件答案白名單；
- M47 route、M46 goal/criterion/mechanism/content review、同模型 reviewer 與 34 秒 budget 不改。

## 最小驗收

1. 先以保留的 M47 Web failure 形成 structural fixtures：缺 visible object、缺 visible stop、
   內部 action verb 未實現、nonprogress mechanism。只允許修前兩類 surface mismatch；後兩類
   仍拒絕。
2. repair 產物需是自然、簡短日文，exact object 在句中、operation 可觀察、停止點可見；
   `before/after` trace 同時保留 digest、修正類型與「沒有改內容語義」的限制。
3. 新增獨立 M48 runtime node／圖卡，顯示 plan fields → surface repair → M46 content review →
   delivery，不能把 repaired candidate 自動寫成成功。
4. 新隔離 Safari 至少跑中／日／英正向 task、nonprogress 反例、不要方法反例；逐輪分開報
   route、realization、review、delivery、時間與日文。不重跑 M47 六輪去改它的 0/3。

## 不在 M48 範圍

中文 no-method 多餘澄清、review timeout／整體 latency、progress-mechanism 選擇品質、長對話、
holdout、人評、persona provenance。M48 通過也只代表表面實現契約，不代表 action 有用或
人腦方程式完成。
