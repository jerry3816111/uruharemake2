# P4 B 私有產品 child 接線：零 provider 驗收

結論：**限定的機械接線 PASS；真 B Send 仍 REVIEW_REQUIRED。** 本批單一核心變因是把顯式 opt-in 的隔離產品 child 的 Ollama 目標綁至同一 run 的私有端點，而不是預設共用 `11434`。不改 A/B 題、gold、P2 request transformer、人格、正式 DB、M21 fallback、Web stream 或一般產品預設。事前設計及門檻見 `research/p4_b_private_product_child_binding_plan_2026-10-25.md`；上一批 constructor 接縫見 `analysis/p4_b_private_constructor_binding_zero_model_result_2026-10-25.md`。

## 可核對的前後差異

| 邊界 | 修改前 | 本批零 provider 證據 |
|---|---|---|
| Controller | 沒有 B opt-in；產品 preflight 會匯入 Web，launcher env 交集丟棄新鍵 | B 必須顯式 opt-in、新 prepared root、0600 descriptor；先驗 HEAD 六個關鍵來源、私有模型／程序／listener，簽一次性 receipt v2；B 靜態 preflight 不匯入 Web。default／inert 沿原路 |
| Child 啟動 | Web 在匯入時先建 log、bare ledger／RuntimeManager | 固定 entry 在任何 Web 匯入前執行 B bootstrap；壞／部分／大小寫不符意圖拒絕，boot 後 env 消失／漂移也在 Web 副作用前拒絕 |
| 真實 SDK 目標 | `UruhaBrainV4_Mac` 預設共用 `11434` | 新獨立假 child 經 entry→Web 同一 ledger/gate→Brain opt-in→真 OpenAI SDK + HTTPX MockTransport，只見 `GET http://127.0.0.1:11455/v1/models` 一次；0 completion POST；缺真 prompt bound 時 M21 request 被送前拒絕 |
| 每次 create | inner proxy 只看 B resource gate | B 模式於 gate 前及 gate 後各重核同一 receipt、來源、env、私有 daemon／runner／模型與 gate object；換 gate、bare ledger、receipt 撤銷／過期、身份漂移均不能走 fake provider |

收據 v2 只核定 B＋隔離**白名單 env keys 的 digest**、run/root、模型／程序、固定 entry＋bootstrap＋binding＋Web＋ledger 來源 SHA 與最終 Python argv SHA；不是全環境 hash、密碼學簽章或 OS 強隔離。Controller 用 committed HEAD byte check 防未提交關鍵來源；child 再與 receipt 比對。ready 證據另綁實際 child PID／final command／listener 與當時 private identity，`status.ready_recorded` 僅表示曾通過，不是目前 daemon 一直有效。每次真 create 前才重核現時身份。

## 測試、成本、未做的事

- 使用 `.venv/product_checks/bin/python -m pytest -q` 跑 11 個 B binding／bootstrap／controller／Web／constructor／resource-gate 與原 product lifecycle／compute receipt 相鄰檔：**191 passed，9 個既有依賴 warning**。`py_compile` 與 `git diff --check` 通過。獨立唯讀審查對本批零 provider 機械接線判 PASS，沒有獨立跑真產品。新同一假 child 試驗另有 controller final env／receipt→子行程→固定 entry→同 ledger→真 SDK 假傳輸，**2/2**；它用 fake Popen/identity，不能冒充真 sandbox PID／ready。
- 對既有私有模型 clone 連續四次 read-only `_model_store`，實測 **9.301121 秒 wall、43,925,504 bytes max RSS**。GGUF 為 **4,683,073,952 bytes**，四次至少約 **18.73 GB 邏輯讀取**；這是在快取、無 daemon／Web／模型生成下的檔案身分成本，不是 click→DOM 或完整 child 延遲。現行 gate 前後雙重重核各兩次 `_model_store`，因此 20 秒產品目標有實質風險；後續須另審能維持安全邊界的低成本檢查，而不能把此成本藏起來。
- **0 真 provider completion、0 A/B 題、0 原生 Safari Send、0 正式 DB 寫入。** 本輪沒有真私有 daemon/runner 的 controller→sandbox child ready，沒有 transformed request 真 token 上界／non-B parity，沒有 M21 例外可見 terminal 或 late-result 20 秒驗收。A 作者三項真人評分＋外部 receipt 與 A on-only PASS 仍缺。故此結果只授權下一個必要的獨立驗證，絕不授權 B Send 或聲稱比 LLM 更懂使用者。

## 下一個必要 gate

在新的隔離 private root／未曝光 B 題外，先量真 controller→sandbox child 同 PID ready/stop、私有端點模型列舉與 B 送前身份重核的全程耗時／CPU／RSS；若 300 秒診斷租期或 20 秒 Web 上界受成本影響，保留失敗並另立單變因設計。B 要真正送出前，仍需 A 作者資料與 A on-only PASS、真 transformed request token oracle、M21 terminal fail-closed、非 B 原生 Safari queue/deadline 演練，全部按凍結卡分層驗收。
