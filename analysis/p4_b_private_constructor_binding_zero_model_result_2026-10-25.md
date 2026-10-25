# P4 B 私有端點 constructor 接縫：首批零生成證據

判定：**首批程式接縫與零網路契約通過；產品 child／B Send 仍 REVIEW_REQUIRED。** 這是 `research/p4_b_private_product_endpoint_binding_design_2026-10-25.md` 的第一批，不是 A/B 題真執行、Safari 產品或同模型效果。A 作者三項評分／外部 0600 receipt 和真 A on-only PASS 仍缺；A/B 真輪均 0。

## 修改前 → 修改後

- 修改前 `UruhaBrainV4_Mac` 無論由誰建構都先以共用 `localhost:11434/v1` 呼叫 `models.list()`；M31 native URL 是模組全域常數。Web 仍建立 bare `ComputeLedger`，controller 的 env 交集會丟新 key，因此獨立私有 oracle 不能證產品請求真的送到它。
- 新增 opt-in `PrivateEndpointBinding`：明示 run、canonical 0700 root、0600 SHA 綁定且短效的 controller 形狀 receipt、兩程序 PID＋啟動代次、私有 loopback port／模型檔與環境；驗同一真 ledger 上的尚未使用、沒有 token callback 的常閉 B gate。缺失／過期／漂移在連線／MemoryManager 前拒絕。`_inspect_live_identity` 只讀模型檔、程序、環境與 listener；不呼叫舊 probe 的 render-only chat 或 tokenizer。receipt 在長檢查結尾重新核 SHA／模式／存在性／內容及過期，gate 狀態與私有 root 再驗一次。
- 只有 opt-in branch 用 `httpx.Client(trust_env=False, follow_redirects=False)` 與 OpenAI `max_retries=0` 指向 exact `127.0.0.1:<private port>/v1`；`models.list()` 必須只列 `qwen2.5:7b`。M31 URL 改為 LeftBrain instance 欄位，模組常數與預設／A constructor 參數路徑不變。B M31／RightBrain 仍由既有 gate 在生成前預拒。
- **審查保留失敗：**初版曾在 constructor 身分檢查呼叫整個舊 probe，包含固定無敏感句的 render-only `/v1/chat/completions` 和 runner `/tokenize`。它沒有 completion，卻不屬此批允許的純身份接縫。獨立只讀審查發現後，改為上列檔案／程序／listener 只讀路徑；原測試對 probe 的 mock 已改成會偵測誤呼叫的負控。這不回寫前批結果。

## 驗證與成本

- 新 binding／constructor 聚焦 **35/35**；加上既有私有身份 probe、B resource gate、P2 compact 與 brain core **105/105**；M21、P3 compute、兩組 B launcher 與 persona seam 相鄰 **51/51**。共 **156/156**，用 `.venv/product_checks/bin/python`，8 個既有相依套件警告；無真 socket、真模型生成、A/B 題、Safari 或正式 DB。Python compile 與 `git diff --check` 通過。
- 真 OpenAI 2.14.0＋httpx 0.28.1 在 MockTransport 下只發私有 `GET /v1/models`；環境代理存在仍不採用，302 指向 11434 時僅一個請求且 terminal；錯模型 listing 在記憶庫前拒絕。default→私有實例一→私有實例二→default 同 process 不改全域端點。這些是無網路 transport 契約，不是真 child socket 見證。
- 對既有 `/tmp/uruha-p4-b-ollama.72H90N` clone 的**單次 read-only** `_model_store` SHA 驗證耗時 **2.507202s**；檢查 4,683,073,952-byte GGUF 加其他檔，正式 inspector 會做前後兩次，故邏輯讀取量至少約 9.37 GB。沒有啟 daemon 或 runner，也沒有量真 constructor 全程；不得把兩倍單次秒數當精確延遲或聲稱 20 秒 Web gate 通過。共用 11434 原 PID 1529 仍在，11455／55132 沒 listener，本批沒停止共用服務。
- 跨模型只讀設計審查在修訂後只放行首批；改碼審查先抓出 provider-shaped probe 與 receipt 中途撤銷缺口，修正後判**首批機械接縫 PASS**。它未獨立重跑測試，也不授權完整產品路由／B Send。這個審查與上述測試是不同證據層。

## 尚不能主張與下一步

首批沒有 controller 發證、child env 傳遞、Web 同 ledger、每次 create 前重新核身份、實際 B transformed request token 上界／provider usage parity、M21 denial 的 terminal surface、20 秒原生 Safari click→DOM watchdog 或 late-result 抑制。receipt issuer 欄是合作式契約，不是抗同帳號偽造簽章；PID／檔案哈希也非原子身分保證。現行 Web 一律仍走共用 11434，B gate 沒上界而常閉，**B 不可按 Send**。

下一必要項須另審 controller→env→Web ledger→brain→實際私有 socket 的完整產品 child 接線與真請求前身份重驗；先零 provider fake child，之後另前瞻非 B 同形狀 usage parity。Web deadline/terminal 要另立設計；A 人類核＋真 A 成功仍是獨立前置。此次未新增圖像/Safari，因尚無產品 child 可展示，不能以測試頁冒充 runtime 驗收。正式人類反應方程式、LLM 優勢、VRM/Function Calling 統一驗收均未因此增加證據。
