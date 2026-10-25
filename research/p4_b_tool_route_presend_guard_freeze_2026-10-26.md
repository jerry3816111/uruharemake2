# P4-B 工具分支送出前阻擋：單變因改碼前凍結

狀態：**只准 source／fake 實作與測試；真 Ollama、B Send、Web／Safari 仍 NO-GO。**
此卡不改原 P4-C 非 B 的工具契約，不重判既有 f0–f3 或 B 三次真 zero-turn 負結果。
獨立只讀改碼前審查：**GO 僅此 scope**；若上游把全部 B 前綴鍵移除，此局部 guard 無法識別 B，故仍依賴上游 env/receipt 檢查與後續完整 source/effect closure，不稱全管線網路隔離。

## Before 與研究邊界

- `analysis/p4_b_entry_effect_source_inventory_2026-10-26.md` 的只讀 source trace：固定 B child env 有 `URUHA_P4_B_*`，但沒有 turn admission journal／exact-input arm。Web 可用空 token/claim 走進產品 Function Calling wrapper。
- `uruha_product_function_calling_p4.py` 現只在 selected tool route 且 token／claim 非空時拒絕；空值時於 `mark_activity` 後建 provider，再呼叫 `core.run_function_call_turn`。預設 `LocalOllamaToolsProvider` 會以 urllib POST 共用 `127.0.0.1:11434/api/chat`，繞開 B 私有 binding／ledger／M21 gate。這是**靜態可達反例**，不是已觀測真 POST。
- 前態 HEAD `6c97bb7e3d4534efbacd3e996c730edebf4fdc8c`；產品檔 SHA-256 `d8adc8cc992c578ea43424022ce52372cc0504f60b59c8104e27e54bb58eb3aa`；主測試檔 `24613888a172ba45e61a42b99fdc1e313a3767974fb1a8aa558811da969e6b56`；Web admission 相鄰測試檔 `7440f0f974939e1b806c522ccc2ef75aecc3b6f63120fb1d3b74d82d5688747a`。這些是 before 錨點，不是 formal holdout。

## 唯一改動與允許檔

只在 `run_product_turn_p4_c` 已判為 explicit status 工具分支、且尚未 `mark_activity`／status reader／provider factory／`core.run_function_call_turn` 時，若環境存在任何大小寫不拘的 `URUHA_P4_B_` 前綴鍵，即 `RuntimeError("p4_b_tool_route_unavailable")` fail-closed。B intent 不以 `PRIVATE_CHILD=1` 或完整憑證才成立；缺欄、錯值、lowercase 拼法仍拒絕，防 malformed B 意圖掉回共用 endpoint。非 selected 普通聊天仍先走原 Web route，非 B explicit 工具行為不變。已存在的 admission token／claim 拒絕仍保留；不新接 private 工具 provider，也不修改 B 模型、研究題本、graph、Web handler、Brain、sandbox profile 或正式資料。

允許產品與測試：`uruha_product_function_calling_p4.py`、`test_uruha_product_function_calling_p4.py`；必要相鄰測試只讀執行。`CURRENT_TASK.md` 和 source/fake 結果報告可作本項紀錄。產品檔將是 B 未來 source closure 的具名缺口，這次修補**不**宣稱 closure 已完成。

## 成功、失敗與驗證

1. 先加 red fake negative：B explicit 有合法 B env 與 malformed/lowercase env 時，provider factory、顯式 provider `invoke`、`core.run_function_call_turn`、status reader、`mark_activity`、原 Web route 均為 0；預期固定錯誤。因沒有 live provider，0 HTTP 是 fake scope，不是全機網路證據。
2. B ordinary 即使有 B intent 仍原樣進 original Web route，token/claim 透傳契約不退步；非 B explicit 保留既有一次 fake provider invocation 和日文結果；原 token/claim selected 仍早期拒絕。
3. 先跑新檔 red，再最小改產品碼；跑 `.venv/product_checks/bin/python -m pytest -q test_uruha_product_function_calling_p4.py test_uruha_product_tool_failure_truth_p4.py test_p4_admission_token_function_wrapper_contract.py test_p4_b_private_web_ledger_seam.py`，並 `python -m py_compile` 兩改檔、`git diff --check`。只在相鄰失敗有證據時再擴測；不重跑 v1/v2 actual fixture 或長生成套件。
4. 獨立只讀 code/result review，僅 scoped commit/push PR #435 exact head。若新負控或相鄰回歸失敗，保留失敗；最多兩個有根據修正批次，仍失敗轉 `REVIEW_REQUIRED`，不為追綠降低 gate。

資源上限：0 真模型請求／0 B Send／0 Safari；預期 fake suite <60 秒，不啟真 Web、daemon 或使用正式 DB。這項 PASS 最多證**已知工具繞行分支在 B intent 下送前拒絕**，不等於完整 transitive source/effect closure、B token 上界／20 秒、真人或真產品驗收。
