# P4-B 共用工具端點送出前阻擋：source／fake 結果

狀態：**局部 source/fake PASS；真 Ollama、B Send、Web／Safari NO-GO。** 事前凍結 `research/p4_b_tool_route_presend_guard_freeze_2026-10-26.md` 已先以 `951774e6f12aaa8ffa3992069c7d66ad6651ceb5` 推 PR #435 且 exact head 核對；獨立只讀改碼前審查只給此 scope GO。原靜態可達共用 11434 反例見 `analysis/p4_b_entry_effect_source_inventory_2026-10-26.md`，不是實際 HTTP 發送紀錄。

唯一產品變因：`uruha_product_function_calling_p4.py` 的 explicit status 工具 route 在原 admission gate 之後、活動／provider factory／tool core 之前，對任何大小寫不拘 `URUHA_P4_B_` 環境鍵 fail-closed。錯值／缺欄也阻擋；B 普通聊天仍交給原 Web；非 B status 工具與原 admission 遮斷不改。這不是將工具改接私有 provider。

先加 test、未改產品碼時，目標 9 例 **8 failed／1 passed**：8 個 B explicit 變體均進入 `core.run_function_call_turn`，是有方向的 red before。最小改碼後：

```text
.venv/product_checks/bin/python -m pytest -q \
  test_uruha_product_function_calling_p4.py \
  test_uruha_product_tool_failure_truth_p4.py \
  test_p4_admission_token_function_wrapper_contract.py \
  test_p4_b_private_web_ledger_seam.py
39 passed, 9 existing third-party warnings, 9.52s, exit 0
```

8 個 B explicit 組合（full/partial/值 0/lowercase × 顯式／工廠 provider）都在 factory、core、status reader、activity 與原 Web 前固定拋錯；測試 monkeypatch `urlopen` 若碰到即 fail，provider invocation=0。B ordinary 帶 token/claim 仍原樣轉送；非 B explicit 日文 reply 與既有一次假 provider、Web admission 相鄰契約均通過。兩個修改檔 `py_compile`、`git diff --check` 通過；獨立只讀 diff/code/result review 為 **GO 僅 scoped commit**，無 live execution。

界線：fake 0 HTTP 不代表全機網路封鎖。這只把**已知 B explicit-status 繞行**改成拒絕，使用者若觸發會看到 terminal error，不能稱成功日文工具回覆。若上游所有 B marker 消失，此局部 guard 無法識別；其他 dynamic tool route、32 個 entry source、Brain/overlay/import effects 的完整 source binding、真 daemon/model 身份、token 上界／20 秒、人評均未完成。原 v1 fixture FAIL、v2 fixture 合成 PASS、第三次真零輪 `REVIEW_REQUIRED` 判定不變；本次 0 真模型、0 B Send、0 Safari、正式 DB 未碰。
