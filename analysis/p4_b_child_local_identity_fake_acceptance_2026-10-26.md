# P4 B child-local 身分適配：source/fake 層結果

狀態：**source/fake PASS；真沙盒、真 Ollama、B Send／Safari 未因此通過。** 原第三次真私有 zero-turn 在 Web import 前被 sandbox `/bin/ps` EPERM 擋住，0 ready、0 B Send、總 262.7400 秒，結果仍為 `REVIEW_REQUIRED`。上次舊合成 observer 探針僅證 API 對替身可見，不證產品 adapter。

本批唯一核心變因是 B-only sandbox child live identity 觀察路徑：移除它對 `ps` 的依賴，改用 raw PID/PPID/微秒代次、KERN_PROCARGS2 argv/env 與唯一 loopback listener；operator 首次見證→descriptor v2→controller 外部再見證→receipt v4→child 每次 create 前後核對。原 `ps lstart` 留在 sandbox 外供稽核，模型 store 雙掃、binary/model SHA、同 ledger/M21 常閉 gate 不減。`analysis/p4_b_child_local_identity_source_closure_2026-10-26.md` 列 16 個本窄路徑 repo 來源及尚未納入的 B Send 入口。

假程序負控包含：同秒 usec 換代、PPID/argv/executable/env duplicate/壞 UTF-8、listener 非唯一或非 loopback、runner flag/model、receipt 舊版或竄改、source SHA 漂移、operator cache↔warm 改檔、模型 store/binary 漂移、未知 PID 不得 cleanup 訊號、沙盒 harness 結果自我造假。child＋controller fake chain 仍只做 private GET `/models` 1 次、完成請求 POST 0 次、B Send 未授權。

最終驗證（均無真 Ollama／Safari）：凍結七檔聚焦 `236 passed`；相鄰 constructor/Web ledger/resource-gate/controller `67 passed`（9 個既有第三方警告）；六個 Python 檔 `py_compile`、`git diff --check` 通過。新的 harness 自身 fake-only 測試 15/15 包含於 236；它**尚未**執行 `--execute`。模型呼叫、B 題、正式 DB 寫入皆為本輪 0（程式路徑與測試範圍，不是全機網路核帳）。

新來源保護不是 code signing：同 UID 換檔/換代與 signal 間仍有非原子競態；真 Ollama argv/env、真 sandbox adapter 可見性、每 create 約 18.73 GB 邏輯模型 SHA 讀和 Safari ≤20 秒均未由 fake tests 證明。一次性非模型真沙盒輸入與 oracle 另凍結於 `research/p4_b_child_local_identity_preflight_freeze_2026-10-26.md`，需先 commit/push/PR exact head 再執行；第四次真 Ollama 與 B Send 仍需新的重大設計與資源審查。
