# P4 Web 計算帳本長會話 retention：前瞻設計

日期：2026-10-23。證據級別：產品工程；不是正式同模型比較、真人評價或 temporal holdout。既有 cost0/cost1 真 Safari 結果及其 frozen SHA 不重寫、不重播追分。

## Before 與原因

- 原生 Web opt-in `ComputeLedger._calls` 只有 append，`checkpoint()` 以 `len(_calls)` 為索引。每輪已形成完整 receipt、並寫入私有 JSONL 後，原始 provider options 與雜湊／長度仍留 RAM。合成 1 生成＋11 Chroma 操作／輪的只讀量測：1 輪 12 calls／約 35 KB，50 輪 600 calls／約 1.80 MB Python 追蹤配置量；這不是產品 RSS，也不是正式模型成本。
- cost0/cost1 私有單行 JSONL 約 1,081,976／1,079,953 bytes，其中 receipt 約 17.6 KB，`cognition_trace` 約 853–855 KB。磁碟主因是重複 trace，**本項不改日誌編碼**；不能稱此項節省 1.08 MB／輪。另立無損歷史編碼項才可驗收磁碟收益。
- 直接 `reset()` 會重用 call index 並可能丟掉 snapshot 後晚到的呼叫；不能做。prewarm／background 也不可悄悄算入人類回合或消除歧義。

## 單一變因與界線

只改 **opt-in Web 已取得完整 item snapshot 的 ledger RAM 留存生命週期**。全域 call index 單調；`snapshot_item` 以絕對 index 取 window、回傳起訖；只有 owner-only 0700 directory／0600 regular single-link JSONL 寫入完整 receipt 成功後，才退休該 item 且 `attribution_complete=true` 的原始 call records。只移除精確 item calls，prewarm、unscoped、其他 item 和 snapshot 後晚到的 calls 保留。歧義或不安全 log 不退休，不得報 bounded success。曾退休後，過期 checkpoint 與全歷史 `snapshot()` 明確 unavailable／raise，不回傳貌似完整的部分歷史；未呼叫退休的 P3 研究 ledger 語義不變。

允許改動：`uruha_compute_ledger.py`、`uruha_web_ui.py`、`test_p4_product_turn_compute_receipt.py`、本設計及新結果、`CURRENT_TASK.md`；若需新的窄測試可新增專屬檔。不得改凍結 P3/P4 研究結果、成本原始案例、模型／提示／解碼、記憶 DB、人格／日文 guard、來源判定、圖 layout、正式資料、原始 dirty checkout。此項不增產品模型呼叫；最多一次新隔離 Safari 中性文本產品輪次／0 retry，0 下載，正式 DB 0 寫。若 Safari 無可靠操作或無原生持久視覺證據，該 gate 維持 pending／FAIL。

## 前瞻成功／失敗判準

1. 零模型 50 輪、每輪 12 calls 且私有 log 成功：global checkpoint 遞增至 600，前輪 receipt call IDs／usage／item ID 不變；Web ledger retained item calls 每輪歸零（prewarm 可保留），而非 600。量 Python 配置峰值／retained count、總耗時與私有 log bytes；不得把合成數值稱產品 RSS。
2. unscoped／other-item 出現在窗口須保留 `attribution_ambiguous`，不退休；非私有／寫入失敗不退休且 durable gate unavailable。late append 在已取 snapshot 後仍保留、下一輪不能被誤歸因；舊 checkpoint 明確失敗；研究 ledger 未使用退休時 `snapshot()` 完整且相鄰 P3 contracts 通過。失敗 provider 需留 raw-free terminal receipt，私有寫成功後才可退休。
3. 產品 Web 一次新隔離真 Safari：最後日文、圖卡 item ID＝私有 JSONL、receipt 原有 usage／來源／guard／episode 不退步。此為工程接線，不證明較強 LLM、長 session 產品 RSS 或整體產品 PASS；saved-native visual 若無文件化方式仍 FAIL。
4. 任何 ledger 缺項不得顯示「0 全成本」；retention 失敗不得假裝已界定長會話 RAM。若精確 regression 或真輪次 fail，保留反例且至多兩次有根據修正，不改舊 gold。

## 驗證順序與資源上限

先針對性 pytest（本檔新增 50 輪、歧義／late／stale／失敗／privacy 反例），再 `test_p3_complete_product_compute_accounting.py` 與產品相鄰 Web receipt／graph 回歸、compile、diff/SHA；之後才可一個新 0700 root、zero-turn 與 T0 空 DB、一次原生 Safari 實輪。實際 token、等待、JSONL bytes、留存筆數與未覆蓋的 startup／embedding token／TTS／OS RSS 記錄分開。源檔 before SHA：ledger `0a8a351d35c836e7811527d149ce5f48a3dabed21f0cd120fad705ca9ed4707a`、Web `45ac45c062bf93a8903708ac75c23f3553075cdf5b7e4c8547b4320242b2d511`、receipt test `f3fc30f8620faca4dbbcf8780a9eb2f6b41330b5bf85ebd866e90503caf7e818`。
