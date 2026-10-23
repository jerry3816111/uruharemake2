# P4 Web 舊頁 Reset 錯位：防護與真 Safari 診斷結果

日期：2026-10-23。這是 session reset 相容性修正，不是 direct-act 同模型比較。先前 `b0–b6` 送出前 strict FAIL 原判保留：`analysis/p4_direct_reply_act_planner_handoff_pre_send_db_gate_failure_2026-10-23.md`。

## 修正與證據層級

事前單變因規格：`research/p4_stale_gradio_reset_protocol_guard_plan_2026-10-23.md`，commit `0181a5b`。`uruha_web_ui.py` 的 Reset callback 現要求新頁回傳本進程隱藏 Textbox marker；錯誤／缺失／舊欄位值回 14 個 `gr.skip()`，不呼叫 reset、不改 graph。marker 只是跨進程事件相容性值，不是登入、權限或秘密。新頁的 Reset 仍走原本的 `reset_session()`，其餘對話、模型、記憶與 P4 處置未動。

- 機制 before：零模型建構舊版 timer `fn_index=33`，新版 Reset `fn_index=33`；Gradio 6.6.0 優先按 client `fn_index` 路由，舊 timer 兩項 input 對新版 Reset 一項 input 的多餘值可被忽略。這精確解釋舊頁 2 秒輪詢為何可能錯叫 Reset，但尚無出事的 66 個 request 逐筆 client 鑑別。
- 零模型及相鄰：175/175 tests 通過、9 個既有套件警告；包括舊 list／缺值／錯 marker／非 ASCII 日文皆不重設，新 marker 正常一次 Reset、真 `Blocks.process_api` 的舊 `fn_index=33` 路徑、browser graph/reset/active DB 與 M23/M25/M29/M31/M32 等相鄰回歸。產品環境 Gradio 6.6.0 另用真 `build_demo().process_api()` 證舊 ASCII/日文 payload 0 reset、新 marker 1 reset；這仍非 Safari 證據。`research/p4_stale_gradio_reset_protocol_guard_product_freeze_2026-10-23.sha256` 8/8 OK。獨立只讀 code review 發現並在首個修正批消除非 ASCII `compare_digest` TypeError；最終 code 不以 marker 當 auth。
- 真產品／Safari：全新 0700 root `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-a62ixj_p`，官方 ONNX SHA `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3` 的獨立私有 inode/cache 驗證 OK；離線 384 維 finite embedding、0 Python socket attempts。control 產品 run `66c0a273d95b4f16` final PID `20111`，`verify-ready` 對同一 PID/7894 HTTP 200。啟動約 21 秒後、舊 Safari 頁仍開著時，live receipt 為 `memory_db/reset_generation=0/tick=0/finish=0`。此為 frozen 至少 10 秒 zero-turn 窗的 narrow PASS，不代表舊頁一定有送 request。
- 只新開一個 Safari 頁（總 tab 52→53），AX 顯示該新 root 的初始 session `20261023_172914_d607fed1`、空聊天。按該頁 Reset 一次，AX session 變 `20261023_173053_83dc565b`；同 PID receipt 變 `session_db/reset_generation=1/finish=0`，11 秒後仍為 1。之後只關該頁（53→52），exact planned stop 回報 PID 退出與 7894 vacant。兩個隔離 DB `embeddings=0`、`embeddings_queue=0`，`web_logs/` 無回合；正式 DB、原始 dirty checkout、無關報告目錄未動。

## 不能外推與新觀察

這證明此版 Reset admission 防護和**一次真 Safari 新頁 Reset**可用；沒有產生任何 b 題或模型回覆，沒有同模型品質比較、記憶效果、人類偏好或完整產品 PASS。舊分頁可能仍對同埠發出其他錯位事件；marker 只保護 Reset，不消除舊 client 流量，不是 API 身分驗證。沒有保存 Safari 原生 PNG／AX 檔，故不得聲稱 saved-native-visual PASS；上述 AX 是操作時觀察，私有 receipt/ready/stop 才是留存原件。

本次約一分鐘後，尚未手動 Reset 前，live autonomous tick 曾由 0 變 1，stdout 顯示 `passive_decay writes=0`；手動 Reset 後 tick 歸 0。zero-turn 21 秒凍結窗仍符合本項 gate，但未來任何回覆比較若要求 Send 時 tick0，**必須在 Send 前重核**，不能以早先 T0 收據代替；背景週期是與 stale Reset 不同的產品環境風險。

## 私有原件與下一步

停止後原件位於上述 0700 root：

| 原件 | SHA-256 |
|---|---|
| `active_db_receipt.json` | `73b1e847a41d7a6689da04d7931467905d5a461e8438dc127bb3b4a533ea61ea` |
| `p4_preference_fallback_detached.66c0a273d95b4f16.ready.json` | `3def8a8f9745529fd8d778ba616496d63882b6b6516e69fc1b668cb2e7f8db7b` |
| `p4_preference_fallback_detached.66c0a273d95b4f16.stop.json` | `5cc65a8964ac799f4fa800fd78ec41375abfd8a9a5fd4b4cdd3a75594d442bab` |
| `p4_preference_fallback_detached.66c0a273d95b4f16.stdout.log` | `678a7a502d18312d4906e9de8a11b18194e9c947d352d369119500fab3b48d0f` |

下一個必要交付：在**新設計卡**中處理其他舊 Gradio event-index 錯位的產品埠隔離；在任何新模型比較前，另凍結 source-disjoint 題、同模型兩臂、Send 前 live DB/reset/tick/finish 硬門檻與成本上限。既有 b 批不能換 root 補判為 PASS；舊 a0 亦不重播。背景 tick 的時窗需另做零模型／產品調度審查，不與回覆處置合成單一變因。
