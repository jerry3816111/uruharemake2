# P4 exact-input surface A：單次真 M21 的零 provider 執行前核驗

狀態：**執行器／安全前置契約就緒，真 A 尚未執行，B Safari 不放行**。本項沿用
`research/p4_source_event_surface_diagnostic_plan_2026-10-24.md` 與
`research/p4_source_event_surface_exact_input_capability_amendment_2026-10-24.md` 的凍結 A/B 題、gold、唯一
treatment 與停止規則，不是新 M、正式 holdout、真人偏好證據或 Web 全管線驗收。

## Before 與本次新增的可操作界線

`83b93c5`／`0d68b20` 以前只證明固定 fake-M21 路徑：A 和紙封筒來源在同一起點的
default＝off、on 結構保真；0 真 Qwen、0 Safari、0 真人自然度／人格核。獨立只讀審查在本次
runner WIP 中找到三個真執行前阻斷：一次性標記可由更換 private parent 繞過；controller 先回報成功
才寫 child flag 證據且失敗不清理；兩臂由認知前 seed 重放而遺失 post-M21 runtime 狀態。
這些不是模型品質失敗，也不得把修好工程 gate 寫成「理解能力提升」。

本次只補 A 執行及其必要安全接線：`p4_source_event_surface_exact_input_fresh_a.py` 預設沒有執行模式，
`--preflight-only` 以 fake 三候選驗來源、模型 digest、off/default/on、同一 post-M21 `logic+route_info`
和相同認知後 surface 可讀狀態／event SHA，真 provider 0。`--execute` 另需兩個 live prepared/current／
HTTP ready 的不同 controller root、各自 run-bound child flag 證據、私有 0700 證據 parent 與一份
**使用者提供的作者自然度／人格評分**的外部 0600 檔。缺其中一項不進真 M21；runner 不把合成
assertion 冒充真人。兩臂事先各 claim 一次 permit；全機固定私有 0700 目錄的 O_EXCL A marker
跨 evidence parent 阻止第二次嘗試。呼叫前寫原始 request 私有收據；最多一個 no-retry M21
completion，隨後對同一 raw tick、同一 post-cognition surface 狀態及同一 event 各深拷貝重放，
重放另封死 LeftBrain／OpenAI 呼叫。off 必須由**獨立 final-visible 關係稽核**與產品 audit 都是 FAIL，
on 兩者都 matched；兩臂 episode／history／utterance 對齊。合格的資料收集仍回傳退出碼 3
（作者對真回覆的自然度未核），絕不自動授權 B。

controller 啟動時的 allowlisted child flags 綁 run ID／PID／port 存私有 0600 receipt；只有 receipt
成功才公開 start 成功。寫入失敗時對同一新 root 呼叫既有身份核對的 exact stop、回報結果而不宣稱
清理必然成功。permit 的 issue／claim／同輪 validate 也逐次核該 receipt；缺失／錯 arm／錯 PID
拒於 cognition 前。這不是抵禦同 UID 惡意改檔的安全模型。

## 目前可重現觀察

- 兩次 `--preflight-only` 的 request SHA 均為
  `df9d2be6a6c2f8c1fc56cd495ac72df23aa2d400e0dc01868c6d76076d48b9af`，
  Qwen `qwen2.5:7b` digest 查詢符合凍結值；每次 **1 fake M21／0 真 provider**，
  default＝off、off final relation `mismatch`、on `matched`，三臂同一份 raw 與認知後狀態。
  deterministic surface 例句為 `和紙の封筒を初めて自分で折ったんだ。やるじゃん。`，其自然度、
  人格與是否過度直抄**尚無人類評分**。兩次 preflight 的初始／event／raw SHA 因時鐘不同而
  不相同；不宣稱跨次位元決定性。
- 受影響合併測試：**277 passed／1 skipped／2 xfailed**（159.84 秒），含 capability、Web
  拒絕、controller、f7/f8、M29、personhood、graph 及新 A 假執行；2 xfail 是舊有未解
  安全反例，1 skip 是歷史產品碼快照，不計 PASS。`py_compile`、`git diff --check` 通過。
- 假執行覆蓋一次 provider call、兩臂 0 追加 call、跨 parent 的第二次嘗試拒絕、超 token／
  超 wall／不完整 finish 不重試且保留私有 terminal receipt、request drift 前置拒絕、錯
  child attestation 不發 permit。這些都是合成契約，不是實際 token、延遲或品質數據。
- 本批 **0 真 A M21／0 Web Send／0 原生 Safari／0 正式 DB**。沒有新圖像化頁面或 PNG/AX
  驗收；現有 graph 只在零模型 route 核過，不能代替 B 的原生畫面。

## 尚未放行與誠實成本界線

本 runner 是隔離 Python 進程內的 *surface replay*：認知後狀態在三臂相同，但它不是兩個產品
Web child 的完整執行、真 Browser graph 時序、持久 DB 或一般使用者輸入安全。runner 拒絕繼承
`URUHA_*` import-time 環境，並核實實際 M21 request byte digest 與 fake preflight 相同；它仍
不能證明所有非白名單設定與已啟動 Web child 完全相同。`max_tokens=256` 是 completion cap，
`≤2000 provider total tokens` 由 response usage **事後**判 FAIL，並非可在呼叫前保證的
實耗硬上限；若 prompt 意外超支，已耗成本仍必須保留。真 A 前需依這個界線審視是否接受此
一次性資源風險，不能將事後 gate 寫成預付硬保證。

固定句的人類作者自然度／人格核尚未取得，無外部 0600 評分檔、無兩個真 ready root，故沒有
執行 `--execute` 或消耗 A 一次性 slot。真 A 若任何模型路由、相同 request、成本、off/on
visible gold 失敗，保留 FAIL，B 不送；即使 A 成功，還要核真回覆自然度才准 B 的一次原生
Safari。正式強 LLM 公平對照、獨立人評、temporal holdout、一般安全、no-send transaction、
VRM／Function Calling 一體產品與完整人類反應方程式均未由本項證明。
