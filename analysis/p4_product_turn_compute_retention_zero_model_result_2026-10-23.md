# P4 Web 計算帳本 retention：零模型結果

日期：2026-10-23。工程契約證據，尚不是新真模型／Safari 產品驗收，也不是完整 production 資源上界。

## 改變與 before／after

事前凍結見 `research/p4_product_turn_compute_retention_plan_2026-10-23.md` 與同名前置 SHA。原來 opt-in Web 每輪的 `ComputeLedger._calls` 永久 append；合成 1 generation＋11 Chroma 操作／輪的唯讀診斷在 50 輪留下 600 calls、約 1.80 MB Python tracing 配置量（不是產品 RSS）。新機制保持絕對單調 call index，先形成 raw-free item receipt，私有 JSONL 寫入後經 owner-only 最新完整行讀回、核 item/reply/receipt 相符，才移除該輪精確 IDs。50 輪相同合成操作的聚焦測試：累計 checkpoint `600`，每輪收據仍各 `12 calls / 16 provider tokens`，私有 JSONL 仍留完整第一輪證據，而 ledger 於每次記錄後留存 scoped calls `0`（原為第 50 輪 `600`）。這是**正常、私有、歸因完整的人類輪次**的 RAM 留存改善；未量真產品 RSS。

失敗及界線沒有隱藏：非私有 log、實際跨執行緒 unscoped 混入、損壞的 JSONL 尾端均不退休；完整 `snapshot()` 在已退休 ledger 上明確 raise，過期 checkpoint 明確 reject，零 call 不推進退休水位。兩個完成輪次可反序寫 log 仍各刪自己的 IDs，snapshot 後晚到 unscoped call 留存。JSONL 寫失敗不退休；JSONL 成功而後 TXT 寫失敗仍只退休已私有驗證的輪次。terminal provider exception 先寫 `compute_failures.jsonl`，成功後退休、失敗則保留；錯誤不被改成成功回覆。可變 snapshot 的歧義旗標即使被翻改，retire API 也重新核完整窗口。

## 驗證與成本

- 聚焦加受影響相鄰：`111 passed`，命令為 `.venv/product_checks/bin/python -m pytest -q test_p4_product_turn_compute_receipt.py test_p3_complete_product_compute_accounting.py test_p4_browser_bound_graph_hydration.py test_p4_web_final_graph_evidence_delivery.py test_progressive_runtime_graph_m24.py test_human_priority_scheduler_m19.py test_uruha_product_function_calling_p4.py test_uruha_product_tool_failure_truth_p4.py test_p4_reported_receipt_destination_compute_detached_control.py`；約 `7.20 s`，0 模型、0 下載。`py_compile`、`git diff --check` 通過。新 product SHA 9 檔將在真輪次前核對。
- 合成 50 輪包含 600 個帳本操作，但**不產生模型推論**；`16` 是 fake provider usage／輪，不是真 token 成本。Web private row 回讀增加每輪一次最大 16 MB 的尾行驗證，真產品的額外延遲／RSS 尚待實測。
- 沒有改模型、提示、解碼、來源／語言 guard、記憶資料、圖 layout 或正式資料。成本圖仍顯示原收據；零模型只證 item ID／收據／圖接線，原生 Safari 尚 pending。

## 不成立的較大宣稱

背景/prewarm、非私有、歧義及失敗寫入分支會保留 calls；沒有 hard cap，不能稱整個長會話 RAM 有界。兩筆舊真輪次的約 1.08 MB／row 主要來自 `cognition_trace`，receipt 只有約 17.6 KB；本項不減少那些 JSONL bytes。saved-native Safari 視覺、全管線 token/OS/TTS、強 LLM 公平比較、真人與 temporal holdout、VRM/Function Calling 統一驗收均不由本項通過。下一步只做事前凍結的單次全新隔離 Safari 產品輪次，保留 strict gate 結果。
