# P4-C × exact-input claim：產品 wrapper 相容性修正

狀態：source-only 前瞻計畫；不是新的 M，也不變更 P4 A/B 凍結題、gold 或成本門檻。

## 問題與修改前證據

2026-10-25 在安全 worktree 的 `d6e1644`，執行
`.venv/product_checks/bin/python -m pytest -q test_p4_admission_token_function_wrapper_contract.py`
得到 **3 passed / 2 failed**。真 `uruha_web_ui` 文字送出目前固定將
`exact_input_claim=None` 傳給 `_run_turn`；外層 truth overlay 透傳，但 P4-C
`wrapped()` 不接受該 keyword。普通 journaled text 與選中工具的負控都在
認知／預期 fail-closed 前變成 `TypeError: ... unexpected keyword argument
'exact_input_claim'`。音訊沒有此 keyword，所以同測試通過。這是現行統一
入口的跨 wrapper 退步，亦會阻止未來 B Safari；不是 A 的模型品質失敗。

修改前來源 SHA 在同名 `.sha256` 檔；既有 P4-C admission 計畫與 result 保留。

## 單一變因與邊界

唯一變因是 P4-C wrapper 對 Web 新增的 `exact_input_claim` 做明確介面承接。
普通非工具路由：非 `None` claim 必須以**同一物件、僅一次**傳給原 Web
`_run_turn`，由原 Web 進行 capability 驗證；`None`／無此參數時維持舊
keyword 形狀。選中 read-only status 工具：只要有非空 admission token **或**
非 `None` claim，就在 activity、provider factory／invoke、status reader 與
原 turn 前明確 `tool_route_admission_unavailable`；不能讓工具假冒 Web
cognition journal。無 token、無 claim 的既有工具路由不變。

只允許修改 `uruha_product_function_calling_p4.py`、
`test_p4_admission_token_function_wrapper_contract.py`、本計畫／SHA／結果與
`CURRENT_TASK.md`。不得改 Web、Brain、ledger、capability verifier、工具
provider、A/B source/gold、模型參數、正式 DB 或原始 dirty checkout。

## 成功、失敗與順序

1. 先提交本計畫與修改前 SHA、核對 PR #435 head；再補 identity-forward、
   tool-selected+claim 負控。原 2 個 Web text 失敗在產品修改前保留。
2. 做最小 P4-C 介面修正。聚焦測試須全過：真 Web browser-bound ordinary
   text journal `arrival→admission_snapshot→cognition_start→cognition_end→terminal
   delivered`；音訊不退步；工具＋token／claim 仍是 `terminal error`、0
   provider/status/Brain。新增普通 claim identity 與舊 keyword 形狀斷言。
3. 跑 P4-C／truth overlay／admission／exact-input 相鄰零模型回歸、compile、
   diff review；只有 scoped files 可 commit/push，核 PR exact head。

任何 claim 被丟棄／改寫、工具繞過、provider 呼叫、正式資料寫入、原
Web 參數或 A/B 凍結物漂移，均 FAIL。資源上限：0 真 provider、0 Safari
Send、0 paid、0 正式 DB writes；本批只證 wrapper 與 fake-Web journal
contract，不宣稱真 A、B、工具輪 admission、完整成本硬上限、自然日文或
runtime/production PASS。A 人評及 B hard-cap 設計缺口仍各自 pending。
