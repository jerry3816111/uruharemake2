# P4 隔離產品 controller：停止後 listener-vacancy 修正

2026-10-17。這是五輪前瞻 probe strict FAIL 後的**獨立生命週期支援修正**，
不是對該批 T1–T3 的追認或重測，也沒有重新啟動其 DB。

before：`analysis/p4_source_bound_preference_fresh_product_probe_result_2026-10-17.md`
所記的原始 `stop-attempt` 為 `signalled=true`、`original_pid_exited=true`，
但原 `_vacant` 用 plain `bind(127.0.0.1:7894)` 判 false，故
`planned_stop=false`；隨後 `lsof` 沒有 LISTEN，`netstat` 有同埠
TIME_WAIT。這能指出 bind 和 listener vacancy 的判準不等價，但不
足以唯一證明 OS errno／停機當下所有 socket 狀態。

單一變因：只調整 `p4_preference_fallback_detached_control.py` 的
port-vacancy 判定；全埠 `lsof -sTCP:LISTEN` 無 live listener 才算
停止後空埠，TIME_WAIT 不算仍在服務。既有 exact PID／UID／lstart／
PGID、最終命令、loopback listener 與 HTTP 200 前後同源檢查保留。
不改回答、M31/M32、記憶、gold 或正式 DB。`lsof` 回傳不明、格式
缺漏或外來 listener 一律不能當作空埠；stop 失敗仍留不可覆寫
`stop-attempt`，不能產生 planned `stop.json`。start 先查無 listener，
真正啟動若遇到其他 bind 衝突仍由既有 fail-closed cleanup 處理。

證據：新 unit 包含 bind-false／no-LISTEN 模擬、實際 macOS `lsof`
`p/f/n` 解析、外來 owner／wildcard、空白成功或錯誤輸出、已就緒
產品停止與錯誤時的 failed-attempt；聚焦
`test_p4_preference_fallback_detached_control.py` 20/20 通過。
與 launchd、隔離 launcher、snapshot 相鄰合跑 59/59 通過，
2 個 dependency deprecation warnings，約 1.96s；`git diff --check`
通過。另以全新 0700 隔離 root
`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-4ys3ud4e`
做跨 controller 呼叫的真 `/bin/sleep` 無模型兩段驗證：第一 run
`8bbfd4cb58470ee3`／PID 42083，`status` 同源 inert，`stop`
planned/signalled/PID exited/no listener；第二 run
`9bc1940b916c04bb`／PID 42160 的 `previous_run_id` 指回前段，
第二段也 planned stop，後續 status `stage=exited`、`port_vacant=true`。
這是 inert same-root 證據，**不是**產品 same-DB、Safari 或模型驗收。
沒有做新產品 same-DB 兩段真重啟或 Safari 對話驗收，該層
仍 pending。這個修正只移除 TIME_WAIT 型假不空；check-to-start
的外部同 UID 競爭不能完全消除，最終仍由 PID/listener/HTTP 同源
核對攔截，不得宣稱 production-grade lifecycle。
