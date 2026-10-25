# P4 B：真產品 child 的私有 Ollama 端點綁定（前瞻設計）

狀態：**設計草案；獨立放行審查未完成；尚未實作；B no Send。** 承接已提交的非 B 零生成身份預檢（`e949db8`）。前批只證私有 model store／daemon／runner 可在固定無敏感句上 render+tokenize；凍結計畫的 daemon 啟動數有歧義、耗時未保存，不能當 B 放行。這批改動的唯一核心變因是：B opt-in 產品 child 的實際 Ollama 目標由共用 11434 轉為一個已核身份、run-bound 的私有 loopback endpoint。A 題、B 題、gold、P2 request transformer、人格、正式 DB、預算閾值與一般產品預設路徑不變。

## Before、反例與源碼邊界

`uruha_web_ui.RuntimeManager` 在 import 時建 `ComputeLedger()`（沒有 B gate），`get_brain()` 建 `UruhaBrainV4_Mac`；後者於 `models.list()` 前用固定 `OLLAMA_URL=http://localhost:11434/v1` 建 OpenAI client，M31 native URL 亦由同一常數導出。故即使獨立私有 oracle 很準，產品真請求仍可能去共享服務。`p4_preference_fallback_detached_control.py` 會將 launcher env 與 `_isolated_env` key 交集；只在 launcher 加 URL 會被靜默丟掉。M21 在 `uruha_brain_mac.py` 的 `except Exception` 可吞 `P4BResourceGateError` 並轉 fallback；Web 在 final audit 前串流角色片段。這些都使 B 仍嚴禁 Send，不因 endpoint 接線而放行。

前置 SHA-256：`uruha_brain_mac.py` `c255fa631f100574dfc17108f10bf892c56c8ef54d590f6826cb61ddd6797fcd`；`uruha_web_ui.py` `10bfea36200b2af51926501a5aac80bd08ddade27111335a28b8381afc6f2ec3`；`uruha_compute_ledger.py` `b3210b92f7af7a50ca948a63dd5129d2d0d92bf1fc861f8808c0bba05ce278b9`；`p4_direct_reply_act_m29_priority_detached_control.py` `c9d460e1767e4dfd7f56b7d68bad975d29ebe87b255c14ca75d3a02fedff0c52`；`p4_preference_fallback_detached_control.py` `a50c28867201afd164f031e0293c26708f7f2f34ba330455d4cc8b3adc13feca`。舊 source SHA 測試若因必要產品變更而失敗，要列為歷史凍結的真差異；不可改舊 SHA 追綠。

## 單一變因的設計與權限

1. 新 child-only endpoint binding 物件僅接受明示的 `127.0.0.1:<private port>/v1`，拒絕共享 11434、hostname/外網、redirect、缺 run ID、缺 private root、缺 daemon/runner PID 或 digest。沿前批 probe 的 manifest＋五 blob、Ollama 0.34.4、兩 binary、model path、父子 PID 與 loopback listener 核驗；子程序的私有 `OLLAMA_MODELS`／`OLLAMA_NO_CLOUD` 需以 process environment 或可信 controller 啟動收據交叉核對，不能僅憑使用者傳入 URL。runner 可能在閒置後卸載，故開機 preflight 不能作為 Send 時的持久憑證；在真正 M21 create 送前須再次核 PID／port／model／template 與 receipt 時效，runner 消失或換代即拒絕。這仍是合作式身份而非同帳號惡意程序的原子保證。
2. 改 `UruhaBrainV4_Mac` 的 opt-in constructor seam：只有帶合法 binding 且 B gate 已安裝才將 OpenAI `base_url` 與 native URL 指向同一私有 endpoint；核驗發生在 `models.list()` 之前。預設無參數、預設 11434、`max_retries=0` 及 A runner 逐位元組行為不變。**controller** 須在 Popen／Web import／DB 建立之前驗缺 binding/gate 並拒絕；child constructor 再核一次，不能把 constructor 單獨當成 DB 前保證。任何失效不得降回共用端點。
3. 明確的 B child controller flag 將私有服務身份、run ID、root、端點傳給產品 child；須處理上述 env 交集，核對實際 child env／target client 的 base URL，並確認 Web 的 `ComputeLedger` 是帶 gate 的**同一個** ledger。絕不讓 inherited 任意 `URUHA_*OLLAMA*` env 自動啟用；一般 launcher default/off/on 和 A 路徑不變。至此仍保留 gate 的 prompt bound 為缺席，因 B 真 transformed request 尚未量測；不得用 callback fixture 放行。

第一個實作批次的允許檔：新 `uruha_p4_b_private_endpoint_binding.py`、`uruha_brain_mac.py` 的 constructor／native URL 窄接線、新聚焦測試與本設計之後的結果檔。child controller／`uruha_web_ui.py` 接線前須先做同批獨立設計 review，逐個確認原 B 規格第 1／2 點允許哪些產品檔；若要改 Web 事件、spinner、stream 或 deadline，必須另立 Web 前瞻設計，不能借 endpoint 改動偷渡。完成 constructor seam **不等於產品 child 已綁定**。

## 驗收、成本與失敗去向

- 先以零網路 fake OpenAI 的紅／綠測試證：預設 base URL 不變；合法私有 binding 才能到私有 `models.list()`；共享、外部、alias、redirect、PID/port/model/binary 漂移或無 gate 在任何 `models.list` 前拒絕；native/local／第二 M21 在 gate 下仍拒絕。再跑 P2、B resource gate、persona/runtime constructor、受影響的歷史 SHA 測試，明確分開源碼凍結失配與功能退步。相鄰測試未過不稱通過。
- 產品 child 接線後仍先跑 0-provider fake child：核 controller→env→Web ledger→brain→OpenAI target；未真送 A/B，不用正式 DB，不改原題／gold。再用**新非 B 句**和獨立私有 root 測相同 shape 的 render/tokenize 與真 provider usage 差分，事前凍結最多 1 真 completion／256 output tokens、耗時／實際 usage／HTTP 呼叫數；若失配保留反例，不能藉改 B 題或閾值修分。只有真 request 送前 token bound、M21 terminal fail-closed、Web deadline/late-result 及 A 真人＋A on-only PASS 都過，才可能考慮唯一 B Safari Send。
- 任一身份核查未知、使用共用 11434、env 被丟、子程序替換、counter 缺席、gate 被吞或 Web partial 提前顯示，當前 B 授權一律 false。資源上限此設計批：0 B/A 真請求、0 Safari、0 正式 DB；first implementation 0 provider，非 B parity 必須另凍結其精確呼叫上限。最多兩個有據修正批次；失敗記 `REVIEW_REQUIRED`，不改弱既有 baseline／gold。

本設計目前是待獨立審查的 draft，不因寫下它就授權修改產品路由，也未推定私有路由成功。若審查無法取得，先保存草案和 before 證據，仍可做與 A/B 不相依的必要只讀診斷；不以同模型自審冒充獨立放行。P4/長期 Goal 仍 active。
