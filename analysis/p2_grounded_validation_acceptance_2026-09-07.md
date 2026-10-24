# P2 第一批：澄清資格修正，對話品質仍未通過

本文件保留第一批當時結果；第二批 compact planner 的新生成證據見 `p2_compact_planner_acceptance_2026-09-07.md`。

## 實際完成

產品限定 adapter `uruha_grounded_validation_p2.py` 檢查新澄清的 typed source。未知 slot、來源 schema／欄位缺失、
value 不匹配或沒有 evidence，不得把原回覆替換成具體二選一；保留舊 pending、層次記憶、confidence 與 M27。
沒有匹配測試用語、追加 prompt／答案或把致謝改判為 supported。凍結 M 模組與正式資料未改。

- focused 10/10，7.73 秒；相鄰 P1／M43／V2.13 共 51/51，17.79 秒（8 個既有依賴 warnings）。
- 完整 mock 與本機 runtime 各 2 sessions、6 輪。P1 的 8 項 identity／persistence／graph 檢查仍通過。
- 兩個問題輪次都留下 `grounded_validation_p2.blocked=true`，撤回新 validation；實際 graph 有來源與連線。
- 本機前後六輪 **全部 M27 ledger 逐欄相同**，沒有用表面回覆修飾 outcome。
- 新增模型呼叫 0。50 對交錯 microbenchmark：舊中位 0.0290 ms、gate 0.03694 ms；不含模型／磁碟／瀏覽器。

## 回覆前後：不能只看單元通過

| 輸入（前輪已要求傾聽） | 本機修改前 | 本機修改後 |
|---|---|---|
| そう、それでいい。 | 一回、今は放っといてほしいのか、少し聞いてほしいのかだけ教えて。 | ん、そこもう少しだけ聞かせて。 |
| うん、聞いてくれてありがとう。 | まあ、今は放っといてほしいのか、少し聞いてほしいのかだけ教えて。 | ん、そこもう少しだけ聞かせて。 |

無根據的二選一已移除，**通用追問仍在**。mock 回覆「分かった。」不等於真實模型表現。
本機六輪 37.38622 秒，兩次一般 planner 仍 APITimeoutError，0 完成的 OpenAI-compatible 對話生成。
帳本只涵蓋 OpenAI-compatible；右側 native urllib 呼叫不在此帳本，不能將 0 推成全系統 0 生成。
本機六輪皆日文，但語用品質未過；沒有進行真人偏好、正式 holdout 或 Safari 驗收。

## 新開發控制揭露的限制

`p2_development_controls_run1_2026-09-07.json/html` 是新增 5 sessions、9 輪 **mock runtime**，不是 fresh model。
四項保存／graph 結構檢查通過；檔內沿用 runner 的 `bounded_identity_pass` 名稱，**不代表以下語意通過**。

| 控制 | 實際觀察／判定 |
|---|---|
| 考えとく → また今度にしようかな | typed 婉拒假設仍被問獨處／傾聽；證明來源資格不是問題內容正確性的保證，FAIL |
| 致謝但追加方法請求 | mock 只說「分かった。」；沒有交付方法，FAIL，不算成功 acknowledgement |
| 改成希望獨處 | 舊 correction surface 附加「沒睡／想事情」二選一，無當輪依據，FAIL |
| 引述中的ありがとう與來源問題 | mock 只说「分かった。」；無正確來源回答，FAIL |
| 無上下文「那個」 | mock 只說「分かった。」；不足以理解，FAIL |

這些負例不被寫入 runtime 關鍵字或答案。P2 尚缺「選項內容對齊來源」及一般 planner 真正工作後的對話驗收；
不能因 51 個測試而稱 P2 完成。當前 typed gate 刻意不更動上游推測／confidence；既有 influence_count 仍是
候選參與計數，不能當實際改變最終行動的因果證據。

## 模型載入診斷與接續

Ollama 服務日誌的兩次對話請求都在約 8 秒被取消，當時 qwen2.5:7b 的 llama-server 還沒載入完成。
一次獨立 45 秒上限、max_tokens=1 的啟動診斷成功：19.547616 秒，32 prompt＋1 completion tokens。
這不是對話驗收，也不改原先逾時結果。下一步先做一次暖機後原 8 秒預算的兩輪探測，若仍失敗才另定
單一 budget 診斷；不默默放寬原來的驗收，不換弱 baseline，也不新增 M。

證據：`p2_focused_tests_run1_2026-09-07.xml`、`p2_adjacent_tests_run1_2026-09-07.xml`、
`p2_product_stack_contract_run1_2026-09-07.json/html`、`p2_product_stack_local_run1_2026-09-07.json/html`、
`p2_validation_cost_2026-09-07.json`。隔離暫存記憶已由 runner 清理，未讀寫正式 DB。
