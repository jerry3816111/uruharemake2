# P4 逐輪歸因產品 opt-in 接線：零模型結果

狀態：**接線契約 PASS；真 Web／Safari、模型、視覺與產品品質 pending**。新題與嚴格 gate 已於程式修改前以 `93f4963` 推 PR #435；舊 d0/d1/e0 strict FAIL 不變。

## Before／單一改動

`uruha_web_ui.py` 已接收 `URUHA_WEB_TURN_ADMISSION_JOURNAL_PATH`，但目前使用的 `p4_direct_reply_act_m29_priority_detached_control.py` 從未設定它；底層只放行 `_isolated_env` 明列的鍵，shell export 不能代替。新增聚焦斷言後，修改前 2/2 fail（產品子程序 env 無 journal、flag 被轉發給 base CLI）。修改只在該控制器加入 `--turn-admission-journal`：僅 `start --mode product` 可用，子程序路徑固定為 launcher-owned root/`turn_admission_journal.jsonl`；沒有 flag、非 product action、其他入口及原認知／回覆／scheduler/journal code 皆不變。

## 可重現檢查

- `PYTHONDONTWRITEBYTECODE=1 .venv/product_checks/bin/python -m pytest -q -p no:cacheprovider test_p4_direct_reply_act_planner_handoff.py test_p4_isolated_product_port_lifecycle.py test_p4_turn_admission_attribution.py test_p4_product_active_db_receipt.py test_human_priority_scheduler_m19.py`：**88 passed、9 既有 warnings、0 真 provider calls**。覆蓋 opt-out、shell-injected env 不漏入、兩個 port、five other CLI actions 拒絕 flag、finally 還原、原 admission/receipt/scheduler 契約。
- 新作者題 `長い小説を最後まで読み切れた。今は一言だけ励まして。` 的隔離 fake-client 完整 `run_turn_debug`：M29 `brief_encouragement`、M33 `not_applicable`、M18 不接管、M21 `full_planner` 且 compact completed、`support/direct_chat_answer`、final=episode，1 假模型呼叫。這只是路由 go/no-go，不預告真模型 core 或可見品質。
- 改前先凍結的 6 個檔案 SHA 在 `research/p4_turn_admission_fresh_single_probe_preimplementation_2026-10-24.sha256` 均已核對；`git diff --check` clean。0 真生成／0 paid／0 正式 DB。新接線本身沒有新增常駐產品成本；真輪的 journal 同步成本仍待實測，不能把上一批 fake Brain 單次 median 0.362 ms 外推。

## 仍未取得的證據

目前沒有真產品 child env、同 PID ready、官方私有 ONNX 預熱、Safari click、原生 graph/PNG/AX、真模型 token、可見回覆或 DB／背景狀態通過證據。mocked base CLI 證明 scope，不是 launchd 實際交付。下一步只准按事前 `research/p4_turn_admission_fresh_single_probe_plan_2026-10-24.md` 在新隔離 root 做零輪準備及單次真輪；Tpre/tick0/journal/持久狀態任一硬 gate 不符就不送或判 FAIL，絕不以 tick1＋reported writes0 放行。即使接線 PASS，也不證明正式人評、同模型強對照、VRM+Function Calling 完成或人類反應方程式。
