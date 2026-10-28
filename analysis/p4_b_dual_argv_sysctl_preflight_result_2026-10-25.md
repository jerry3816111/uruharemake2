# P4 B 雙 argv 身份修正：真沙盒預檢結果

判定：**改碼與零服務 preflight PASS；第三次真私有 zero-turn、B Send、Safari 均未驗收。** 此結果承接原 v2 在第二次真執行的 `private_child_argv_drift` 負例與先前 `/bin/ps` sandbox EPERM 負例；舊結果不改分。前瞻修訂先於改碼提交 `bf14424`，見 `research/p4_b_private_zero_turn_dual_argv_amendment1_sysctl_2026-10-25.md`。

## 改了哪個機制

在 B-only 0600 receipt v3 將父方校準的 OS Framework Python 最終命令和 child `sys.executable` venv Python 分成兩個獨立欄。controller 仍在沙盒外用 `ps` 比對同一 PID 的 exact final command／ready／stop；child 在 Web import 前、再次驗證及 provider create 前用**同程序** `sysctl(KERN_PROCARGS2,self PID)` 讀 kernel exec path＋恰兩個 argv，要求與 receipt OS vector 完全一致，再獨立要求 venv `sys.executable`＋唯一固定 entrypoint digest 一致。三層是 AND，任何缺證或額外參數拒絕，不退回只驗其中一層。B 校準改為單行同時輸出 `sys.executable`，避免第二條 pipe line 可無界等待；一般產品／A 校準不變。

`KERN_PROCARGS2` 在本機 SDK 屬 `__APPLE_API_UNSTABLE`。此機制只對目前 pinned macOS 的合作式 child 身份可觀察性提供證據；receipt 不是簽章，也不是抗惡意同帳號程序或跨 OS 的保證。procargs buffer 可能含環境變數：程式只解析 argc、exec path、兩個 argv，不輸出／保存／摘要其餘 bytes。

## 分層證據

- 舊 child-local `/bin/ps` 的同 sandbox actual-script 探針退出 1；新產品**同一 observer**在同 profile actual-script 退出 0，OS argv digest `242d970bbfbfc1a4bffa47bec2d413f4680c27950be0721c82e1028b6546e05f`、in-process digest `027bef8e92b0fd4861d7c65fc5e5bef4a39ae99f21dd2ffed4a1de2f6517cee3`，兩路徑不同。額外 Python `-B` 參數探針退出 1；並非單純 `-c` 成功。探針重用舊 profile**唯讀**，不 claim 舊 root、不啟 daemon、不送 HTTP／模型題。
- 同 sandbox 的 B-only controller calibration 實測取得 Framework OS executable 與 venv `sys.executable`，兩者不同；沒有新 root 或模型服務。
- 聚焦／相鄰 11 個 B controller、binding、child、fake chain、Web ledger、constructor、resource gate、launcher、operator、isolated identity 測試 **235/235 通過、9 個依賴 warning**，wall 20.17 秒。畸形 procargs、sysctl 失敗／長度、額外 OS arg、in-process 漂移、receipt v2／v3 欄位、boot 後撤銷與 provider 前重驗均為零服務負控；`py_compile`、`git diff --check` 通過。另一代理只讀改碼審查另跑四個聚焦檔 **126/126** 與相同正負真沙盒探針；這不是獨立真人或跨機器驗證。
- 無真 Web HTTP ready／same-PID stop、真 Brain/SDK、B transformed-request token 上界、M21 terminal、Safari click→DOM 20 秒、日文回覆、作者評分、正式 DB 寫入或人評。**0 B Send，第三次全量 zero-turn 仍 pending。** 235 tests／毫秒級探針不證完整產品 PASS。

下一步只在 scoped commit/push、PR #435 exact head 與 critical source bytes、私有 port／共用服務身份、模型與磁碟前檢後，才依原資源／停損卡用第三組全新 one-use roots 執行**一次**真 zero-turn。任一 gate 失敗保留原結果；第三次真 run 失敗即 `REVIEW_REQUIRED`，不再逐項追綠，不放行 B Send。
