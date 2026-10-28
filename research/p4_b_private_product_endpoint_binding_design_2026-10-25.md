# P4 B：真產品 child 的私有 Ollama 端點綁定（前瞻設計）

狀態：**跨代理只讀審查指出首批契約缺口，已前瞻修訂；待修訂版放行；尚未實作；B no Send。** 承接已提交的非 B 零生成身份預檢（`e949db8`）。前批只證私有 model store／daemon／runner 可在固定無敏感句上 render+tokenize；凍結計畫的 daemon 啟動數有歧義、耗時未保存，不能當 B 放行。這批改動的唯一核心變因是：B opt-in 產品 child 的實際 Ollama 目標由共用 11434 轉為一個已核身份、run-bound 的私有 loopback endpoint。A 題、B 題、gold、P2 request transformer、人格、正式 DB、預算閾值與一般產品預設路徑不變。

## Before、反例與源碼邊界

`uruha_web_ui.RuntimeManager` 在 import 時建 `ComputeLedger()`（沒有 B gate），`get_brain()` 建 `UruhaBrainV4_Mac`；後者於 `models.list()` 前用固定 `OLLAMA_URL=http://localhost:11434/v1` 建 OpenAI client，M31 native URL 亦由同一常數導出。故即使獨立私有 oracle 很準，產品真請求仍可能去共享服務。`p4_preference_fallback_detached_control.py` 會將 launcher env 與 `_isolated_env` key 交集；只在 launcher 加 URL 會被靜默丟掉。M21 在 `uruha_brain_mac.py` 的 `except Exception` 可吞 `P4BResourceGateError` 並轉 fallback；Web 在 final audit 前串流角色片段。這些都使 B 仍嚴禁 Send，不因 endpoint 接線而放行。

前置 SHA-256：`uruha_brain_mac.py` `c255fa631f100574dfc17108f10bf892c56c8ef54d590f6826cb61ddd6797fcd`；`uruha_web_ui.py` `10bfea36200b2af51926501a5aac80bd08ddade27111335a28b8381afc6f2ec3`；`uruha_compute_ledger.py` `b3210b92f7af7a50ca948a63dd5129d2d0d92bf1fc861f8808c0bba05ce278b9`；`p4_direct_reply_act_m29_priority_detached_control.py` `c9d460e1767e4dfd7f56b7d68bad975d29ebe87b255c14ca75d3a02fedff0c52`；`p4_preference_fallback_detached_control.py` `a50c28867201afd164f031e0293c26708f7f2f34ba330455d4cc8b3adc13feca`。舊 source SHA 測試若因必要產品變更而失敗，要列為歷史凍結的真差異；不可改舊 SHA 追綠。

## 單一變因的設計與權限

1. 新 child-only endpoint binding 物件僅接受明示的 `127.0.0.1:<private port>/v1`，拒絕共享 11434、hostname/外網、redirect、缺 run ID、缺 private root、缺 daemon/runner PID 或 digest。沿前批 probe 的 manifest＋五 blob、Ollama 0.34.4、兩 binary、model path、父子 PID 與 loopback listener 核驗；子程序的私有 `OLLAMA_MODELS`／`OLLAMA_NO_CLOUD` 需以 process environment 或可信 controller 啟動收據交叉核對，不能僅憑使用者傳入 URL。runner 可能在閒置後卸載，故開機 preflight 不能作為 Send 時的持久憑證；在真正 M21 create 送前須再次核 PID／port／model／template 與 receipt 時效，runner 消失或換代即拒絕。這仍是合作式身份而非同帳號惡意程序的原子保證。
2. 改 `UruhaBrainV4_Mac` 的 opt-in constructor seam：只有帶合法 binding 且 B gate 已安裝才將 OpenAI `base_url` 與 native URL 指向同一私有 endpoint；核驗發生在 `models.list()` 之前。預設無參數、預設 11434、`max_retries=0` 及 A runner 逐位元組行為不變。**controller** 須在 Popen／Web import／DB 建立之前驗缺 binding/gate 並拒絕；child constructor 再核一次，不能把 constructor 單獨當成 DB 前保證。任何失效不得降回共用端點。
3. 明確的 B child controller flag 將私有服務身份、run ID、root、端點傳給產品 child；須處理上述 env 交集，核對實際 child env／target client 的 base URL，並確認 Web 的 `ComputeLedger` 是帶 gate 的**同一個** ledger。絕不讓 inherited 任意 `URUHA_*OLLAMA*` env 自動啟用；一般 launcher default/off/on 和 A 路徑不變。至此仍保留 gate 的 prompt bound 為缺席，因 B 真 transformed request 尚未量測；不得用 callback fixture 放行。

第一個實作批次的允許檔：新 `uruha_p4_b_private_endpoint_binding.py`、`uruha_brain_mac.py` 的 constructor／`LeftBrain` instance-local native URL 窄接線、新聚焦測試與本設計之後的結果檔。child controller／`uruha_web_ui.py` 接線前須另做設計 review，逐個確認原 B 規格第 1／2 點允許哪些產品檔；若要改 Web 事件、spinner、stream 或 deadline，必須另立 Web 前瞻設計，不能借 endpoint 改動偷渡。完成 constructor seam **不等於產品 child 已綁定**。

### 2026-10-25 首批審查修訂：可執行的私有接縫條件

- 只有明確 B opt-in 且帶 immutable run-bound binding 才進私有分支；缺 binding 的 B 意圖不可靜默走一般 11434。binding 至少綁 run ID、canonical 0700 root／models、0600 controller-issued launch receipt 的版本／SHA／短期限、daemon 與 runner PID **及 process-start generation**、兩個 loopback port、daemon 啟動 environment 的 canonical `OLLAMA_MODELS=<private root>/models` 與 `OLLAMA_NO_CLOUD=1`、binary／manifest／五 blobs／GGUF／system／template hashes。live inspector 須核 listener owner、runner-parent、兩程序 generation 與 daemon environment；任一未知／例外 fail closed。舊固定句 probe 可重用模型／模板的 read-only 身份檢查，但它只查 PPID/argv、不查 env/PID reuse，也不能單獨充當持久 binding；constructor 當下與未來每次真 create 送前重驗是兩個不同 gate。這是合作式同帳號證據，不聲稱抵抗惡意程序或消除 TOCTOU。
- 私有 constructor 在建立任何連網 client、`models.list()` 或 MemoryManager 前，須驗證 binding、同一 `ComputeLedger` 上真正的 `P4BResourceGate`、gate 尚未 terminal／使用，以及 receipt/live 身份。首批 gate 不可由任意 callback 假裝已取得 B token 上界：只有常閉 gate 可用；constructor 可成功但真生成仍拒絕。B 意圖／binding／gate 不匹配即拒絕，不 fallback 至一般路徑；一般與 A 的無參數 constructor 原行為逐欄不變。`LeftBrain` 僅加可選 instance native URL，唯一 M31 request 使用它；module global 不變，native 與 RightBrain 在 B gate 下仍於生成前拒絕。
- B-only OpenAI HTTP client 必須顯式 `trust_env=False`、無 proxy/custom mounts、`follow_redirects=False`、SDK `max_retries=0`，只接受 exact `http://127.0.0.1:<private daemon port>/v1` authority；userinfo、query、fragment、hostname／alias、IPv6、外網、11434 與非預期 path 都拒絕。3xx 不得跟隨成第二個 request。一般與 A 不換 transport。`base_url` 字串／零生成 probe 都不足以證明最後送達的 socket；後續 child 須以零 provider fake socket/target 見證，真 Send 前再核實際 child env。
- 首批必有 no-socket sentinel 與真 SDK＋假 HTTP transport 兩層測試：所有 invalid binding/gate 在 `models.list()`／MemoryManager／HTTP 前拒絕；有效 fixture 只觸及私有 `/v1/models`、redirect 不跟隨、proxy env 不採、0 retry；default→private A→private B→default 同 process 不串線。另覆蓋錯 run/root/env/receipt、PID generation／port owner／model／template／binary 漂移及 inspector 例外；同一 ledger 傳入 OpenAI wrapper、LeftBrain、RightBrain，native/local 仍 0 calls。測試可注入 inspector，但 production 不能把 callback 當 controller receipt。不能以 mock 通過宣稱真 socket、Web 或 B token 上界已驗收。
- 第一批 constructor identity inspector 不呼叫舊 `probe()` 的 render-only `/v1/chat/completions` 或 runner `/tokenize`；兩者雖不完成生成，仍是 provider-shaped 診斷，不屬這次常閉接縫。首批只讀 private model files、process generation/env/argv/binary、listener owner 與 receipt；若在檢查中 receipt 過期、gate 被其他執行緒使用或文件狀態漂移，結尾再次拒絕。此修訂源自實作後只讀審查發現的缺口，尚未放行 child/Web 或 B Send。

## 驗收、成本與失敗去向

- 先以零網路 fake OpenAI 的紅／綠測試證：預設 base URL 不變；合法私有 binding 才能到私有 `models.list()`；共享、外部、alias、redirect、PID/port/model/binary 漂移或無 gate 在任何 `models.list` 前拒絕；native/local／第二 M21 在 gate 下仍拒絕。再跑 P2、B resource gate、persona/runtime constructor、受影響的歷史 SHA 測試，明確分開源碼凍結失配與功能退步。相鄰測試未過不稱通過。
- 產品 child 接線後仍先跑 0-provider fake child：核 controller→env→Web ledger→brain→OpenAI target；未真送 A/B，不用正式 DB，不改原題／gold。再用**新非 B 句**和獨立私有 root 測相同 shape 的 render/tokenize 與真 provider usage 差分，事前凍結最多 1 真 completion／256 output tokens、耗時／實際 usage／HTTP 呼叫數；若失配保留反例，不能藉改 B 題或閾值修分。只有真 request 送前 token bound、M21 terminal fail-closed、Web deadline/late-result 及 A 真人＋A on-only PASS 都過，才可能考慮唯一 B Safari Send。
- 任一身份核查未知、使用共用 11434、env 被丟、子程序替換、counter 缺席、gate 被吞或 Web partial 提前顯示，當前 B 授權一律 false。資源上限此設計批：0 B/A 真請求、0 Safari、0 正式 DB；first implementation 0 provider，非 B parity 必須另凍結其精確呼叫上限。最多兩個有據修正批次；失敗記 `REVIEW_REQUIRED`，不改弱既有 baseline／gold。

本設計目前是待獨立審查的 draft，不因寫下它就授權修改產品路由，也未推定私有路由成功。若審查無法取得，先保存草案和 before 證據，仍可做與 A/B 不相依的必要只讀診斷；不以同模型自審冒充獨立放行。P4/長期 Goal 仍 active。
