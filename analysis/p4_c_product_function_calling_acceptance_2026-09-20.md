# P4-C read-only Function Calling 產品驗收

日期：2026-09-20  
結論：`product_read_only_function_calling_and_chat_regression_pass`

## 真正新增的產品能力

UruhaBrain 的同一本機 Safari 入口現在有第一個真的 Function Calling 路徑，而不再只有 research policy：使用者明確詢問目前
runtime 狀態時，模型只能選擇唯一 allowlisted 工具 `get_runtime_status({})`。工具只讀四個有界狀態：brain 是否已載入、目前 turn
數、記憶是否在隔離環境、以及目前允許的工具能力。它不能讀取對話或記憶內容、不能回傳檔案路徑或 secret、不能初始化 brain，
也不能寫檔、執行 shell、連外或控制 VRM。

這是未來 action transport 的最小真實骨架；它不是把 research policy 改名成 Function Calling，也不是宣稱一般工具使用已完成。

## Safari 真實狀態工具輪

在重啟後、brain 尚未因聊天載入的全新 session，實際輸入：

> Please check the current UruhaBrain runtime status.

Safari 顯示的最終日文：

> うん、脳はまだ待機中。記録は0ターン、記憶は隔離環境。今使えるのは読み取り専用の状態確認だけ。

結果與當時 UI 狀態一致：`brain_loaded=false`、`turn_count=0`、`memory_isolation=isolated`、
`tool_capability=get_runtime_status_only`。本輪只有 1 次本機模型呼叫、1 次工具執行、0 retry、0 side effect；status reader 沒有為了回答
而啟動 brain。端到端耗時 `6.2512s`，低於現有 `20s` 產品目標。

runtime node graph 同輪實際顯示：

1. `function_request_p4_c`
2. `function_model_decision_p4_c`
3. `function_validated_call_p4_c`
4. `function_tool_result_p4_c`
5. `function_surface_p4_c`

後面再接既有的 surface delivery 與 latency，共 7 nodes。圖不是事後報表；它就是該輪產品 trace，能看到「請求→模型決定→驗證→
工具結果→日文表達」。

## 普通聊天沒有被工具路徑攔走

同一 session 下一輪實際輸入：

> I feel tired today. Please just listen; I do not want advice.

Safari 顯示：

> うん。今は方法出さないから、そのまま話して。

這輪沒有任何 P4-C function node、沒有工具執行，也沒有 P4-C 新增的模型呼叫；仍走原本 69-node cognitive path，選擇
`listen_presence` 並排除 `solve_regulation`。端到端 `2.697s`。因此此次單一變因沒有把普通聊天全部誤路由成 status tool。

## 安全、閒置與瀏覽器事實

- P4-C 在 P4-B 的 private isolated runtime root 追加 2 筆紀錄；production memory access=`0`。
- 兩輪後觀察到 4 次 background latent-rehearsal cycle，conversation rows 維持 `3→3`，可見閒置催促=`0`。
- 真實模型呼叫合計 2 次：core gate 1 次、Safari product status 1 次；retry=`0`、付費 API=`0`、外部網路=`0`。
- Uruha 頁面沿用既有 `http://127.0.0.1:7860/` 分頁，沒有關閉任何使用者頁面。
- UI automation 的一次 stale click 意外新增了 1 個無關「Open ChatGPT Desktop」分頁；它不是系統所需頁面，這裡沒有擅自關閉，
  使用者可以自行關掉。

## 證據邊界與下一步

P4-C 證明的是「一個 read-only status tool 真正進入產品、圖上可追蹤、普通聊天未退化」；不是一般 Function Calling、VRM 動作、
voice、開放世界品質或研究優勢。下一步 P4-D 先盤點本機是否已有可合法重用的 VRM asset、renderer 與 dependency；若沒有，
先凍結 user-supplied asset 邊界與離線 renderer contract，不能下載來路不明角色模型或直接把未通過 holdout 的 action policy 接到實體動作。
