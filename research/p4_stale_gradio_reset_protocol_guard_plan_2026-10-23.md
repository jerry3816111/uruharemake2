# P4 Web 舊分頁事件錯位：Reset admission 單變因修正計畫

定案前置：2026-10-23，`226a242f1d4aed972e640f35482dd739f37e27b2`。這是產品 Web session 安全性／隔離的必要修正，不是另開研究 M，也不改 direct-act planner 的處置或 b 題 gold。先前比較送出前 strict FAIL 永久保留，詳見 `analysis/p4_direct_reply_act_planner_handoff_pre_send_db_gate_failure_2026-10-23.md`。

## Before 與可反駁原因

在新 0700 root，同 final PID ready 後但未按 Safari Send，active DB 從 `memory_db` 變 `session_db`、`reset_generation=66`、finish0/tick0。Web 唯一的 reset 呼叫鏈是 `reset_btn.click` → `reset_session_browser_bound` → `reset_session` → `RUNTIME.reset_brain_session`。獨立零模型 `build_demo()` 對映：`0942455^` 的舊 timer `fn_index=33`，目前 build 的 Reset `fn_index=33`，新版 timer=34；Gradio 6.6 `route_utils.get_fn` 優先使用 client `fn_index`。故「舊分頁 timer 被新版伺服器當成 Reset」是強機制假說，尚缺個別 request client 身分。

## 唯一工程變因

只改 Reset callback 的准入：目前頁面從當前伺服器實例得到非對話、隱藏的 reset protocol marker；點 Reset 時 marker 作為一個明確 client input 傳回，伺服器先精確驗證，否則拒絕且不呼叫 `RUNTIME.reset_brain_session()`。marker 不是身份認證或安全秘密，僅作跨版／跨進程相容性確認。應是每伺服器實例的新值，使舊頁重連不通過；不能依賴 Gradio server-side `gr.State` 的值取代 client input。正常新頁 Reset 行為、一般文字/音訊對話、既有 M29 gate、planner、記憶與 graph 不變。不在此項同時改 controller port、事件次序、模型或資料。

允許檔案：`uruha_web_ui.py`、新聚焦測試 `test_p4_stale_gradio_reset_protocol_guard.py`、受影響既有 reset/graph 測試、結果報告及 `CURRENT_TASK.md`。不碰原始 dirty checkout、正式 DB、無關輸出資料或 frozen b 題。產品 SHA 在實作後另建，不能把目前 SHA 當新 code 證據。

## 驗收與成本上限

1. 零模型：實建 Gradio 事件圖，證 Reset 只有 marker input；舊 timer payload／缺失／錯值均不得呼叫 reset，session ID、active DB、reset generation 不變；新 marker 只准一次正常 Reset，原生 graph tombstone 等既有輸出仍正確。重啟後舊 marker 應拒絕；如需直接測試以兩個不同實例 token 模擬，不能用 server-side State 假冒。聚焦及受影響回歸通過、`compileall`／`git diff --check` 通過。
2. 新隔離 zero-turn 產品診斷（不是 b0 重試）：全新 0700 root、官方 ONNX 私有離線預熱、same-PID verify-ready，固定 7894 保持不變，監看至少 10 秒（大於四個 2s 舊 timer 週期）；`reset_generation=0`、active DB `memory_db`、tick0/finish0/DB 空。舊 client 是否發送請求不由此單獨證明；如果仍 reset，立即 fail-closed，保留原件，不送研究題。
3. 正常 Reset 可用性：在**此診斷 root** 的新 Safari 頁面只點一次 Reset，receipt 必須同 PID、`reset_generation=1`、active DB `session_db`，無使用者回合；若任何舊事件又使 generation 增加則 FAIL。只關本次自建頁，不碰舊頁。exact planned stop／port vacant，保存收據與必要 log；不能把此診斷當 direct-act／full pipeline／人評 PASS。

模型生成上限 0、研究題 0、外部部署 0；官方 ONNX 可離線預熱 1 次；只做一次 fresh zero-turn 診斷（不重送失敗的 b 批）。若任一 gate 失敗，保留失敗並最多兩個有原因的工程修正批；不能藉此重判 b0–b6。診斷後若要重新做同模型比較，先前瞻凍結 source-disjoint 新題、兩臂相同環境與成本上限，並審查是否需新埠以消除其他舊事件錯位風險。
