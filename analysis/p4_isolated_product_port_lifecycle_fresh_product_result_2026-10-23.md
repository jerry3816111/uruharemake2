# P4 產品高埠隔離：一次零對話真產品／Safari 診斷

日期：2026-10-23。這是 `research/p4_isolated_product_port_lifecycle_plan_2026-10-23.md` 事前凍結的**運輸／測量基礎**，不是回覆品質實驗。先前 b0–b6 送出前 strict FAIL（0/9）與 a0 非同模型 strict FAIL 均不改判，也不重送舊題。

## 單一改動與零模型證據

僅 `p4_direct_reply_act_m29_priority_detached_control.py` 加 opt-in `--product-port`；預設 7894 不變。既有 `validate_port` 拒絕非法值，prepare/start/status/verify-ready/stop 都在一次 CLI 呼叫期間使用同一選定埠，`finally` 還原底層全域 `PORT`。底層同 PID、prepared receipt、HTTP ready、stop 檢查與產品認知路徑未改，亦不從呼叫者環境自選埠。

新增 5 個隔離、零模型契約，涵蓋五個 CLI 動作與預設／選埠、私有 prepared receipt、錯埠 start 預檢拒絕、錯埠 status/ready/stop 不觸及 listener／訊號，以及異常時狀態還原。獨立只讀複核指出錯埠 metadata 負例後才補測。聚焦及相鄰 controller/direct-act/Reset/active-DB 合併 **90/90 passed**，9 個既有警告；compile、diff check 與 `research/p4_isolated_product_port_lifecycle_product_freeze_2026-10-23.sha256` **11/11 OK**。這僅證新 wrapper 契約，不等於真產品或同模型品質。

## 唯一一次真產品診斷

- 起點先用 lsof 證 `127.0.0.1:7914` 無 listener。新 launcher-owned 0700 root：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-_83y__ti`。官方 ONNX 私有獨立 inode archive SHA-256 `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3`；本 root 離線預熱 384 維 finite，Python socket attempts 0，controller 完整 cache 驗證通過。未使用正式 DB。
- `prepare/start/verify-ready/stop` 均明傳 7914。Run `080ff1cdaebd5d8b`，最終 PID `25213`。第一次 ready 查核遇 listener 尚未穩定而回 `product_listener_not_same_pid`；**同一進程**稍後重新觀察並通過，HTTP 200、before/after listener 同 PID 25213、URL `http://127.0.0.1:7914/`，沒有重啟或重送比較題。ready 原件時間 17:53:10。
- 約 16 秒後的 live `active_db_receipt.json` 觀察到同 PID、`memory_db`、`reset_generation=0`、`autonomous_tick_index=0`、`human_submission_finish_count=0`；當時記憶 DB `embeddings=0`、`embeddings_queue=0`，session DB 與 web_logs 無檔。這符合事前 10–25 秒零輪窗。**此短窗收據只有當時工具觀察；檔案後續由背景 tick 覆寫，不以最終 SHA 冒充 T0 快照。**
- 真 Safari 僅新開 `127.0.0.1:7914/` 一頁（52→53），AX 確認該 root、session `20261023_175256_4716fdc3`、空 chat 與等待輸入的圖；不按 Reset、不送訊。只關自建頁（53→52），其他舊 7894 tabs 未改。無原生 PNG／AX 落盤，saved-native-visual gate 仍未達。
- 稍後 live receipt 的 tick 由 0→1→2，`reset_generation=0`、finish0、同 session／同 `memory_db` 保持；stdout 兩次 `passive_decay writes=0`。背景 tick 是**獨立於 stale tab/reset 的比較風險**，不能把短窗 tick0 當任何未來 Send 時的 tick0。整次 0 使用者輪／0 比較題／0 重試；未見 provider generation，但未設獨立 provider-call 帳本，故不把模型呼叫數標成已直接量測的零。exact planned stop 對同 PID 成功、PID exited、7914 vacant；停後記憶 DB 0/0、session DB 與 web_logs 仍空。

停止後此私有 root 原件 SHA-256：`active_db_receipt.json` `d33baca7033df79e906222122b881315c1c5f115754b3bd13a62992925deb2dd`（**最終 tick2**）；ready `4d8f290f9a63a6a63c682b6fa36aae8cbeeaae3bd7f0ac7cc03d0515b36aaa0b`；stop `5c5f24bfd10590401bad91572dd67a74d4c2afac4fa55fc90d2c163bf87c7796`；stdout `3bfab2476a1757278e67a08e9cb47bac720900bd0a7858d90a904ea898e9b4c1`；stderr `88b8712e9f56e5ab37383a0c810b3dc85e372ea4374a1d12edb40e48d6d077c6`。

## 判定與下一步

只判 **選埠 lifecycle／短窗零輪／Safari 入口窄義 PASS**。它降低舊 7894 分頁撞新 listener 的風險，不能定位舊 66 次 Reset 的具名來源，也沒有任何 b 題回覆、同模型優勢、自然日文、人評或完整產品圖像驗收。下一個必要設計審查是讓比較 arm 的 Send 前後 live tick／DB／reset／finish 真可歸因：若背景 tick 跨 Send，須 fail-closed 或先以前瞻單變因控制，不得對舊 b 題改判。之後另凍結 source-disjoint 題與每臂高埠、同模型同設定對照，再做真 Safari 回覆和圖驗收。正式 temporal holdout／強 LLM 總效果／真人感受及 VRM／Function Calling 統一交付仍 pending。
