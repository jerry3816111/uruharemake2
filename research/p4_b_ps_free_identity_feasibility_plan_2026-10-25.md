# P4 B 沙盒內身份可見性：前瞻零模型 stop/go 探針

狀態：**另一代理只讀設計審查僅條件式 GO 一次零模型探針的實作與 source-only freeze；不授權產品改碼、第四次真 zero-turn、B Send 或 Safari Send。** 此審查不是獨立真人／跨機器驗證。來源負例與選項比較見 `analysis/p4_b_private_zero_turn_third_real_review_required_2026-10-25.md`、`analysis/p4_b_private_identity_design_review_2026-10-25.md`。這是兩個修正批次失敗後的架構可行性審查，不把一個新編號當產品能力進展。

## 單一問題與不變條件

問題：在與 B child 相同類型的真 macOS sandbox 中，是否能**不呼叫被拒的 `/bin/ps`**，對受控外部 daemon-like／runner-like 程序逐項取得現有 `_inspect_live_identity` 所需的 PID generation、exact argv、daemon parent→runner、指定 `OLLAMA_MODELS`／`OLLAMA_NO_CLOUD` 環境值及 loopback listener owner？先前受控 `/bin/sleep` 僅是未封存原始命令／結果的探索，環境欄位連外部 `ps -wwE` 都不可見，故不能把那次空值當正式 no-go 或正式 API 通過。

唯一變因為**觀察 API／可見性**；不改 binding、controller、Web、Brain、ledger、sandbox policy、receipt、模型或 M21 gate。先用單一受控、無模型的 Python daemon-like 程序（固定已知的非秘密 env、固定 argv、127.0.0.1 動態 listener）及其一個 runner-like child；兩個 env sentinel 的**key 名及完整 `KEY=VALUE` 賦值**不得出現在被觀察程序的 Python `-c` 程式碼、argv 或路徑。單字元值 `OLLAMA_NO_CLOUD=1` 的 `1` 可能自然出現在 Python 版本／路徑，不能以單字元 substring 當污染。observer 必須跳過 `argc` 個 argv 後**只解析環境區**，不能在整個 procargs buffer 搜尋字串而假陽性。父方以原有 `/bin/ps`／`lsof` 作獨立對照，並在 observer 前用同 OS API 取得兩程序 raw PID start `tvsec/usec`；sandbox 實際 script 只回各欄是否可見／匹配與固定錯誤碼，絕不輸出／存檔完整 argv、環境、代理或其他使用者程序資料。不得讀共用 11434 的 env／argv；兩程序由本探針產生、精確 PID/啟動代次收尾，不廣域 kill，不碰正式 DB。

## 成功、失敗與成本

- 先證 surrogate 有效：外部 `/bin/ps -wwE` 必須對 daemon 與 runner **各自**看到兩個固定 env key，且每 key 恰一筆、值相符；否則結果 `invalid_surrogate`，不能據此宣稱 sandbox 無權。外部 `lsof` 必須確認兩個 listener 真為各自 PID 所有。
- 同一真 sandbox actual-script 的 child-local 候選須在**同一輪**核對兩程序 raw start（與父方獨立讀得的 raw start 精確一致；另評估如何對應現有秒級 `ps lstart` receipt，不可鬆散轉換冒稱等價）、exact executable/argv、runner parent、指定 env 的恰一值、兩個 loopback listener owner；缺任一就是 `no_go_missing_identity_field`，不得以初始 receipt 或自我 `sys.argv` 補位。先只核小型可觀察資料，不讀模型檔；模型 SHA 時序及 20 秒成本另保留硬 gate。
- **必要真狀態變化負控：**正測後父方向 daemon 傳已捕獲的 runner PID＋raw start；daemon 以其未回收的直屬 `Popen` child 核代次、送 SIGTERM 並 `wait`，僅 `-SIGTERM` 退出碼才確認；daemon 在 listener 仍開時回收 runner，**同一 sandbox observer／同一受監督 PID 重新讀取**，要求 daemon 四欄仍真、runner start／argv／env／parent／listener 五欄全拒；只改 verifier 的期望值不足以證明 observer 非 stale。若仍接受則 `no_go_stale_observer`。不測其他使用者程序、不接 provider。
- 上限為兩個受控的**合成** daemon-like／runner-like 程序、一個 sandbox observer、0 模型 clone／0 真 Ollama daemon／runner、0 provider HTTP、0 Web/Safari、0 B 題。另有不接模型的外層 supervisor worker 與父方 monotonic watchdog：worker 在獨立且唯一的 process group 內啟動上述三個子程序；父方要求 30 秒內收到 `cleanup_started`，否則只終止**自己未回收 worker 所領導的專用 process group**，不按程序名稱或觸碰共用服務。worker 每個 blocking call 使用剩餘時間，並用自身 alarm 作次級保護。正常 cleanup 另給最多 5 秒；若協定／清理失敗，父方對專用 group 最多再用 5 秒緊急收尾，故**總 wall 可超過 30 秒，最壞約 40 秒**，必須分開實記，不可宣稱端到端 30 秒硬界。若 group／exact PID 無法核對或清理，記 `cleanup_review_required`、不做第二組追綠。原三組 one-use roots 只可唯讀參照 profile，絕不重用 claim。

只允許一個狹窄 probe 程式／測試、本結果／任務卡；**不允許改任何產品來源**。在第一次 surrogate start 之前，先固定 probe source SHA、env/argv/listener 建構、每欄的對照 oracle、30 秒硬 timeout、精確清理及 0 retry，經只讀設計／source review 後提交並推 PR exact head；source review 必須特別核兩個 listener 的唯一 owner、socket FD 不跨子程序繼承、sandbox observer 回報 PID 與受監督 `Popen.pid` 相同、正測後 exact runner 終止與**同一 observer**重讀的 phase handshake。凡外部自身 oracle 無法成立，包括 exec path／argv0 不相等時，歸 `invalid_surrogate`，不得冒充 sandbox 拒絕或重跑；此嚴格相等有本機既有 actual-script 預檢先驗，不宣稱 macOS 通則。`invalid_surrogate` 也是終止結果，不得看到輸出後改 surrogate 重跑追綠。執行後保留原始退出碼、固定欄位矩陣、耗時與精確 cleanup。若通過，也只能授權新的 B-only identity 架構規格與成本設計，**仍不可直接進行第四次模型 run**；若失敗，停止 child-local 選項，broker 需另一份重大設計／成本決定，否則 B 常閉。
