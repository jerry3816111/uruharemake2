# P4 B 真私有產品 child：零對話資源與停損卡

狀態：**前瞻設計；尚未啟動本批 daemon／child，B 不可 Send。** 目的不是新增對話能力，而是核對已提交的 0-provider 接線能否在真私有 Ollama 和真 sandbox Web child 上，保持同一身份直到 ready/stop，並量到實際冷啟與模型核對成本。此項是 B 真輪送前的產品身份與資源 gate，不能代替 token oracle、M21 terminal、Safari 20 秒或 A 作者評分。

設計凍結後的只讀定位補正：B controller 的隔離環境目前 `URUHA_WEB_PREWARM_BRAIN=0`，沒有啟用 active-DB receipt／turn-admission journal。故 `verify-ready` 可證真 Web child PID／HTTP／私有身份在該時點一致，**不能證 Brain 已建構、SDK 在真 child 做過 `/v1/models`、B gate snapshot 為 0、或全域絕無生成**。前一批 fake child 才有 SDK 私有 URL 證據。此卡不偷偷改 product env；真 child 的 Brain/SDK 非生成驗收需另依實際缺口前瞻設計。

## 修改前證據與單一變因

- `76d04d5` 已有 controller→假 child→Web→Brain→SDK 的機械接線；11 檔 191/191。假 child 不能證明真 sandbox PID、HTTP listener、私有 daemon/runner 或冷啟耗時。四次 `_model_store` read-only 已量到 9.301121 秒、約 18.73 GB 邏輯讀；不是產品全程。
- 舊 `/tmp/uruha-p4-b-ollama.72H90N` 曾兩次啟 daemon，不能重用為本批單次測量。當前 11455/7894 無 listener，11434 共用服務 PID 1529 不碰；`/tmp` 約 116 GiB 可用。`p4_preference_fallback_detached_control.py` 已有 B opt-in `prepare/start/verify-ready/stop`，但無受控 clone、daemon/runner、descriptor 建立與私有 daemon 收尾工具。
- 唯一核心變因：把**假 private endpoint／child 換成真、全新、隔離的 endpoint／sandbox child**；產品邏輯、模型版本／manifest、B 題與 gold、A/B gate、正式 DB 均不改。這是 operational qualification，非新 M、非新 benchmark。

## 可做與不可做

允許新增一個狹窄、可測的 `p4_b_private_zero_turn_operator.py` 及其測試、結果報告、任務卡。它只能：先調用現有 controller 的全新 prepared product root、官方 ONNX cache 離線 warm；再建立全新 0700 私有模型 root，從固定本機 shared manifest＋五 blob 用 macOS `cp -c` clone，核 SHA／不同 inode／single-link／無 extra files；只啟一個絕對路徑 Ollama 0.34.4 daemon，令私有 11455 loopback 與單一動態 runner 連私有 `qwen2.5:7b`；用固定無敏感句 render-only 載入 runner，核 `0 generated completions`；觀察 PID/start generation／listener／binary/model SHA 後原子建立 0600 v1 descriptor；立刻做 B opt-in start、同 PID `verify_ready`、exact `stop`；最後只按該次捕獲 PID/start 身份終止私有 daemon/runner。輸出僅 opaque run/path、hash、時間／資源、診斷呼叫數及 PASS/FAIL，不保存固定句以外的 prompt、原始 env 或模型回覆。`cp -c`、不同 inode 及 `df` 差額只能檢查大幅實體複製風險，不能證明零物理分配或 APFS 內部 CoW 實作。

不准改 `uruha_web_ui.py`、Brain、P2、ledger、A/B 題、gold、正式研究、正式 DB 或共用 11434；不准做 completion、Safari Send、Function Calling、VRM 動作或外部部署。私有 root/失敗證據不自動刪；不以 shell wildcard 或廣域 kill 清場。若此卡審查發現需要更大範圍，先修卡，不能臨場擴權。

## 順序、接受與停損

1. Source-only freeze 與只讀審查後，先用 fake process／temp tree 做聚焦紅綠和既有 B controller/binding 相鄰回歸；`py_compile`、`git diff --check`。helper 提交並推既有 PR、核 exact head 後才實機啟動；六個 controller critical sources 必須與 HEAD byte-equal。
2. 實機入場：再核 11455/7894 無 listener、11434 原身份未改、正確 `.venv/product_checks/bin/python`、daemon/runner binary SHA、manifest＋五 blob SHA、source cache archive SHA、磁碟可用至少 20 GiB。只允許本批**一個**新 root、一個 daemon start、一個 runner、一次 controller prepared root／start；任何 one-use claim 後失敗都不重試該 root。
3. 先完成 prepared root/cache/warm，避免暖機期間私有 runner 閒置卸載；之後的私有模型 clone 與 daemon 環境固定 `OLLAMA_HOST=127.0.0.1:11455`、`OLLAMA_MODELS=<new-root>/models`、`OLLAMA_NO_CLOUD=1`、`OLLAMA_MAX_LOADED_MODELS=1`、`OLLAMA_NUM_PARALLEL=1`、`OLLAMA_MAX_QUEUE=0`；拒絕 proxy 繼承。runner port 不預填為 55132，必須從當次 child PID/argv/listener 觀察。先以 listener/PID 非 HTTP 輪詢等待 daemon，再只做 **1 個** `/api/version` setup GET；其後只准 1 個固定句 render-only 載入，加現有 probe 的 version/tags/show/render/tokenize **5 個**診斷 HTTP、0 HTTP retry。setup GET 另列；ready `GET /` 與意外 `/v1/models` 不混作 6 個診斷，若 controller／daemon 日誌不能可靠逐項計數就標 `unknown`，不得報完整 HTTP call total。helper 不**意圖**送生成；要核可觀察 0 completion，至少要有兩個 render-only 空內容/usage 0 回覆、完整的私有 daemon request log 與 child 日誌中無其他 completion，並說明其覆蓋。既有 B 零輪沒有持久 B ledger/active human-turn receipt，不能引用不存在的 0 counter；覆蓋不足只能報「helper 0 生成意圖、0 使用者送出，網路全域 0 未證」。
4. 同一 prepared runtime root `prepare`→`cache`→`warm` 後，才啟私有 daemon/runner、造 descriptor，立刻 B `start`→同 PID `verify-ready`→`stop`；`status.ready_recorded` 單獨不算 ready。成功需 HTTP 200 前後同一 final Python PID/argv/listener、同 run/receipt/private daemon+runner identity、`planned_stop=true`、7894/11455/runner listener 最終均空，11434 不變；啟動或 ready 任一失敗就是本次 FAIL，不發新的 receipt、不復用 root。
5. Receipt v2 只有 300 秒診斷壽命且不可續租；任何 expiry、source/model/PID/listener/env 漂移都 FAIL。目標停損線是從私有 daemon 啟動至全部停止 8 分鐘、child start→ready 240 秒且不得越過 receipt expiry；helper 若採同步 controller 呼叫、沒有獨立 watchdog，這些**不是已保證的硬上界**，必須實記超時並在返回後只做精確身分停機。若要把它稱為硬界，實作必須有獨立 monotonic watchdog、可中斷子行程與失敗後 exact-identity cleanup 的負測。無法證明 PID/port 清理時不掃蕩其他程序，記 `REVIEW_REQUIRED`。
6. 每段記 monotonic wall；記 operator 自身及精確 daemon/runner/child PID 的 CPU/RSS **觀察採樣最大值，不稱真 peak**、clone logical bytes、`df` byte 可用量（**ONNX warm 後且 clone 前**、clone 後、全程結束）、model-store SHA 檢查次數／估算讀量與未儀表化部分、HTTP 診斷數與可觀察的 completion 證據範圍。clone 這一段若可用量下降 **>1 GiB** 即停，因完整 4.68 GB GGUF byte-copy 本身小於舊 6 GiB 線；此差額也不是 CoW 的精確物理分配證明。可用空間 <20 GiB、觀察到其他 11455 owner／多 runner、或 11434 被動到亦立即停。20 秒 Web click→DOM 仍**未測**，冷啟 wall 不可代替。

## 判讀與下一步

- PASS 只表示**一個隔離真 zero-turn** 的 private endpoint/child 身份與 planned stop、實際冷啟成本可核，不表示日文回覆或 B 真輪可送。
- setup、timeout、receipt expiry 或身份漂移要保留原樣結果與最小原因，不重新啟動改成 PASS；成本過高須先根據真全程分段數據再做單變因效能設計。若 helper 本身不能安全收尾，停止在 0-provider 工具驗證，不啟真服務。
- 真 B Send 的獨立硬 gate 仍為：作者三項自然日文／人格／不捏造評分與外部 receipt、真 A on-only gold PASS、B transformed request 同一私有服務的 token bound/非 B usage parity、唯一 M21 及 terminal fail-closed、Safari client click→DOM 20 秒與晚到抑制。正式人評／temporal holdout/強 LLM lift 均不由此卡證明。
