# P4 B 雙 argv 修正：前瞻修訂 1（child-local OS argv observer）

狀態：**另一代理只讀設計審查已條件式放行改碼與零服務探針；未放行第三次全量 run**。此審查不是獨立真人／跨機器驗證。原凍結卡 `research/p4_b_private_zero_turn_dual_argv_correction_2026-10-25.md` 保留不改。修訂原因與負結果見 `analysis/p4_b_dual_argv_sandbox_observer_probe_2026-10-25.md`：同類真沙盒拒絕 child 啟動 `/bin/ps`，使原自查必定在 Web 前失敗。這不是模型／題目／門檻的結果，不更改舊實驗。

## 唯一變因與安全界線

只將 B-only child 的 OS identity observer 從**另啟 `/bin/ps` 的 flat command**換成**在同程序以 macOS `sysctl(KERN_PROCARGS2, self PID)` 讀取 kernel procargs**。本機 SDK 定義 `CTL_KERN=1`、`KERN_PROCARGS2=49`；後者包在 `__APPLE_API_UNSTABLE`，因此只能宣稱這台 pinned macOS 的實驗性身份觀察，不能當作跨版本耐久的正式安全介面。同一真沙盒的 `-c` 探針已讀得 exec path/argc/argv，但 actual-script 尚未驗。實作讀 native signed 32-bit `argc` 並要求恰為 2；讀非空、NUL 結尾的 exec path，跳過 NUL padding，只解析前 `argc` 個非空、NUL 結尾 argv 並立即停止；buffer 後續可能含環境變數，絕不可列印、保存、傳回或摘要它。限制配置與回傳 buffer 長度、嚴格 UTF-8／NUL／argc／exec path 等於 argv[0] 檢查；sysctl unavailable、errno、解析不完整、非 macOS 或不精確匹配均 fail closed，沒有 libproc、`ps` 或 `sys.executable` 的 OR fallback。

receipt v3、controller 校準的外部 OS `/bin/ps` exact final command、同 PID/ready/stop、300 秒效期、source／env／endpoint／私有模型身份不變。child 先要求 procargs 的 `exec path` **及** `argv == [expected_os_executable, fixed absolute entrypoint]`，再獨立要求 `sys.executable`＋`sys.argv == [fixed entrypoint]` 的 in-process digest。兩個 Python 路徑可能不同，必須分欄；兩個身份層和 controller 外部命令檢查是 AND。Kernel procargs 是當前 OS process 的觀察，不是加密的啟動證明；controller 外部只觀察 flat `ps`，兩者可互相核對但不可宣稱跨平台或防惡意同 uid 程序。

允許檔仍是原卡七個產品／測試檔，加本修訂、探針／結果報告與 `CURRENT_TASK.md`；不改 operator、Web、Brain、ledger、題／gold、正式 DB、產品 port 或預算。這是第二個有根據修正批次內的 observer 修訂，**不是**第三個追分批次。`libproc.proc_pidpath` 已在真沙盒讀得執行檔，但只含 path、沒有完整 argv，故不作自動後備；若 sysctl actual-script 失敗，不暗降到 path-only 檢查。

## 放行順序與可反駁判準

1. 已由另一代理只讀審查本修訂與已觀察 `-c` 原件；結論是**只對改碼＋真 actual-script 零服務探針 GO**，對第三次完整 run NO-GO，並要求 native signed 32-bit argc、恰兩個 argv、exec path 等於 argv[0]、只解析 argv 不碰 env、所有錯誤 fail closed。這不是跨模型或真人獨立性證據。
2. 審查 GO 後才以最小改動替換 child observer；新零服務 actual-script 探針必須使用**產品同一 parser/observer**、既有真 profile 類型與 venv Python，核 `argc=2`、exec path/OS argv 完全匹配、與不同的 `sys.executable` digest 皆成立。探針不 claim 舊 root、不啟 daemon、不發 HTTP。單純 `-c` 成功不足。
3. 聚焦紅綠與相鄰測試要含真實不同的 Framework/venv 路徑；分別篡改 OS exec path、OS argv[0]、entrypoint、額外 flag/arg、argc、buffer 長度/NUL/UTF-8、sysctl 不可用、in-process path/argv、receipt 新欄與舊 v2、boot 後撤銷／precreate 漂移，任一不能到 provider。測試不只 mock observer 成功；至少一個 test 走真沙盒 actual-script 程序。controller fake 仍核外部 exact command，且附加 arg 會拒。跑四個聚焦檔與現有 zero-provider chain、`py_compile`、`git diff --check`。
4. 只在 actual-script 真探針及相鄰回歸通過、獨立只讀改碼審查、精確 commit/push/PR #435 head 核對後，才依原資源卡用**全新** one-use roots 做第三次且最後一次真 zero-turn。任一預檢 FAIL，不消耗 4.68 GB clone／約 240 秒觀察等待；第三次仍 FAIL 即 `REVIEW_REQUIRED`，不重啟追分。
5. 即使真 zero-turn PASS，仍只證私有身份與 ready/stop/cost；A 作者核准／真 A、B token oracle／terminal／Safari 20 秒、真正 Brain/SDK child 呼叫、人評、正式 holdout 都獨立 pending。**沒有 B Send 授權**。
