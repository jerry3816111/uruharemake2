# P4 隔離產品高埠生命週期：前瞻單變因計畫

定案 before：2026-10-23、Git `1a0790cfd191dde8cedc3963ca808e3c49f710e7`。此項是消除舊 Safari/Gradio client 與新產品 listener 混接的測量基礎，不改模型回覆、記憶或研究題 gold；不是另開 M。舊 `b0–b6` 的送出前 strict FAIL 保留，不重新解讀；Reset marker guard 的窄義 Safari PASS 也不外推至其他 event。

## 問題與單一變因

目前 detached controller 的 `PORT=7894` 同時支配 prepared receipt、runtime metadata、child `URUHA_WEB_PORT`、lsof、HTTP ready、exact stop。Safari 有約 52 個既有舊 tab，其中多個固定連 `127.0.0.1:7894`；零模型已確認舊 timer `fn_index=33` 可撞新版 Reset 33。Reset marker 已擋此一路，但其他舊 event-index 碰撞仍可能改狀態；它不是一次模型比較可接受的背景。

唯一工程介入：只在 `p4_direct_reply_act_m29_priority_detached_control.py` 加 opt-in `--product-port`，預設原值 7894；CLI 的 prepare/start/status/verify-ready/stop 每次明傳同一已凍結高埠。wrapper 先用既有 `validate_port` 驗證，再於單次 CLI `main()` 呼叫範圍暫設底層 controller 的 `PORT`，`finally` 還原。底層現有 prepared/root/metadata/監聽 PID/HTTP/stop 檢查不改；不從 shell 繼承 `URUHA_WEB_PORT`、不自動找空埠、不改其他 wrapper、Web callback 或背景 scheduler。這是 one-shot CLI 用法，非長駐多執行緒 API。

允許檔案：上述 wrapper、新聚焦 controller 測試、必要既有相鄰 controller 測試、本 plan／結果／任務卡與產品 source SHA。不得觸碰原始 dirty checkout、正式 DB、無關報告目錄、舊 b 題或 default controller 行為。

## 先小測再真產品

零模型：對每個 lifecycle 命令核 CLI `--product-port` 被 wrapper 消耗、default 7894 不變、非法／錯埠拒絕、prepare receipt 與 start child env 精確為選埠、verify-ready/stop 只查該埠／同 final PID，`finally` 還原 global PORT；測試不啟動模型。受影響 controller/Reset guard/DB 接線回歸、source SHA 與 diff check 過。

產品診斷只用新 0700 root、官方 ONNX 私有離線預熱、明定尚未被舊 tab 連接的 `7914`（先以 lsof 核空），固定 `127.0.0.1`。prepare/start/verify-ready/stop 均明傳 `--product-port 7914`；同 PID ready 後在 10–25 秒短窗內重讀 live `memory_db/reset0/tick0/finish0`、兩 DB/profile 空；Safari 僅新建此診斷 tab，確認正確 root/session/URL、**不送訊、不按 Reset**，關閉自己新建的 tab；exact planned stop 與 7914 vacant。若任何狀態漂移則 strict FAIL，保留原件，不用「再換一個埠」補判。本項預算為 0 模型生成、0 研究題／0 retries、1 次私有 ONNX 預熱、1 個真 zero-turn run。

診斷 PASS 僅證 controller 可隔離未使用埠，不證原 66 次請求的具名來源或 b 批品質。未來新比較的每個 arm 應事先凍結不同高埠（避免上一 arm 的 Safari tab 連到下一 arm），且兩臂同基礎模型、參數、其餘 prompt/data 不變；埠差異是運輸識別而非認知處置，仍須實測 request parity。Send 前後各核 PID/session/DB/reset/tick/finish，任何背景 tick 漂移 fail-closed。若高埠仍 reset 或 idle tick 導致不可比，停止並另設計，不能改舊題、追分或悄悄關 scheduler。
