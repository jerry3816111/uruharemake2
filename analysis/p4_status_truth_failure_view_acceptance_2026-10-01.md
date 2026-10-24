# P4 只讀工具失敗輪的顯示真實性驗收

日期：2026-10-01（Asia/Taipei）。這是現行產品失敗路徑修正，不變更
P4-C／P4-AZ 凍結入口與原始研究結果，也不是 action transaction 的新比較。

## Before 與單一變因

在凍結 P4-C adapter 上，以隔離 fake provider 回錯工具名，core 回
`failed_closed`、日文失敗句、0 tool execution，產品卻設
`logic.surface_act=read_only_status_report`、
`debug.grounding.source=validated_read_only_tool_result`。注入 reader
exception 也重現同一矛盾（core 的 `result_exposed=false`）。這兩個
before 均 0 真實模型推理、0 外部工具。失敗節點本身正確；錯的是
產品映射到 debug／logic／認知摘要的成功標籤。

新增 `uruha_product_tool_failure_truth_p4.py` 作為現行入口後置 overlay：
只在路徑為 P4-C、摘要狀態為 `failed_closed` 時，將 surface act 設為
`read_only_status_failed_closed`，grounding 明列
`validated_tool_result=false`，再由原 trace 重畫 flow/state。reply、
核心節點、呼叫與工具執行計數、memory、成功狀態及普通聊天不改。
新 additive entry／安全 launcher 不修改 hash 鎖定的舊入口。

第一次 launcher 隔離 import probe 停在 `overlay._INSTALLED` 不存在；
定位為 probe 自身錯誤，改查安裝在 `_base._run_turn` 上的 wrapper marker。
修後 `check --python .venv/product_checks/bin/python --port 7892` 通過：
localhost、sandbox、獨立暫存 DB／session／log、overlay 安裝皆核實；
此 probe 未啟動 server、未作模型呼叫。
精確邊界：新 entry probe 與最終 server 是 sandboxed；繼承的 P4-B
最初 `probe_python()` 在 sandbox profile 建立前以隔離 env 執行，
**不是**所有 preflight import 都在 sandbox 內。此項不改歷史 launcher；
驗收主張只涵蓋現行新 entry／server 的寫入隔離與實測結果。

## 驗證

- 聚焦與相鄰 P4-C／P4-AZ freeze 回歸：`61 passed in 1.12s`，
  包括後加的診斷 probe 靜態防護契約，0 模型呼叫。
- 隔離 Safari 真實 UI：新 `127.0.0.1:7892` 分頁，fake provider
  回 `write_file` 工具名（核心必拒絕，**沒有執行該工具**）。使用者英文輸入
  `Please check the current UruhaBrain runtime status.`；最終日文為
  `今の状態確認は取れなかった。動かしたとは言わないでおく。`。
- Safari Planner Debug 可見 `surface_act=read_only_status_failed_closed`，
  `grounding.status=failed_closed`、`validated_tool_result=false`。
  node graph 可見 `function_model_decision_p4_c` 的
  `failure_category=tool_call:name`、`status=failed_closed`，以及
  `function_surface_p4_c` 的 `claimed_status_read=false`；沒有
  validated-call 或成功 tool-result 節點。
- 隔離 JSONL 恰 1 輪，SHA-256=
  `7962a83637a4a007f982e1a701ace14b3c15a48bdf6c8623181183e474d18dd8`。
  摘要的 `model_call_count=1` 是 fake provider 的**邏輯介面呼叫**；
  實際本機模型推理 0 次，status-tool execution 0，status-tool side effect 0
  （Web 在隔離 root 仍有正常 JSONL／session 寫入），
  prompt/completion token 各 0。原始隔離 JSONL 未納入 repository，
  避免把測試聊天帶入長期資料。
- Safari 驗收後，為重跑時不能誤把診斷頁的一般聊天送進真模型，
  一次性 probe 加上非 status 輸入拒絕與實際 status reader 禁止。
  這是後續安全邊界加固；上述 Safari 觀測來自加固前、但同一
  fake-provider status 路徑，不能把新 guard 冒稱為已經 Safari 實測。
- 另在**同一新入口、另一個全新隔離 root** 作一次真實本機 Ollama／Safari
  成功路徑回歸：同句輸入，`qwen3.5:9b` 模型介面 1 call、read-only tool
  1 execution、side effect 0，prompt/completion token=`310/15`；
  `tool_call_complete`，日文回覆正確說明腦尚未載入、0 turn、隔離記憶。
  Safari debug 仍是 `read_only_status_report` 與
  `validated_read_only_tool_result`；graph 具有 request→model decision→
  validated call→tool result→surface，未被 overlay 當成失敗。
  完整使用者等待 `7.5704s`，小於原 `20s` 產品目標。該隔離 JSONL
  SHA-256=`c3fea9ab6afa593378b6da1ed752fdb5252ef0f628d6a5f1dce3da9dbecb7f89`。
- 兩個診斷 Safari 分頁均已關，其他兩個既有分頁保留；localhost server
  已停，兩個隔離暫存 root 已清除。正式 memory DB 與原始 dirty
  checkout 未觸碰。

## 證據界線

這證明現行產品入口在**受控工具失敗**時，日文回覆、debug 與真實
graph 不再互相矛盾；現行入口的真實本機模型成功輪與 ordinary chat
的自動回歸亦通過。
它不是實際 Ollama outage 或 executor exception 的 Safari 輪次，
也不是 action 品質、人類理解、強 LLM 比較或真人人評證據。
