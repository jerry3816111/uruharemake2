# P4 B 零模型身份可見性探針：唯一真沙盒輪次

狀態：**受控合成程序的 child-local 可見性窄義 PASS；產品 B 仍 `REVIEW_REQUIRED`、0 B Send。** 這是先前第三次真私有 zero-turn 失敗後的架構可行性探針，不改那次 FAIL，也不以一個探針替代第四次模型、token／20 秒或 Safari 驗收。

## 事前凍結與執行

- 先依 `research/p4_b_ps_free_identity_feasibility_plan_2026-10-25.md` 做 source-only 審查；修畢假 GO 與 cleanup 反例後，另一代理僅條件式 GO 一次零模型替身。fake-only **22/22**、`py_compile`、staged `git diff --check` 通過；這些不當真沙盒證據。
- `research/p4_b_ps_free_identity_feasibility_freeze_2026-10-25.json` 固定 probe／test／plan／既有 sandbox profile SHA 及 canonical input-oracle SHA，執行前 **5/5** 一致。探針 source SHA：`e2f29f389101af35b297550b80227248cba9567539359731317c5ccc461e183c`。
- source/freeze/plan/test/task 精確提交 `98274788ec781af633de452beabfa5b239084461` 已推既有 PR #435；執行前 PR OPEN、head OID 與本機相同。只在此 gate 後執行一次 `.venv/product_checks/bin/python p4_b_ps_free_identity_feasibility_probe.py --execute`；**沒有第二輪或追綠修正**。
- 工具實記 wall `0.364877791s`、原始 process exit **0**。worker 自報 active `0.332843s`、total `0.358007s`，分層計時不可混稱為 B click→DOM。

## 原始固定欄位結果

```json
{"active_wall_s": 0.332843, "b_sends": 0, "cleanup_verified": true, "daemon_exit_code": 0, "matrix": {"daemon_argv": true, "daemon_env": true, "daemon_listener": true, "daemon_start": true, "runner_argv": true, "runner_env": true, "runner_listener": true, "runner_parent": true, "runner_start": true}, "model_calls": 0, "negative_rejected": true, "observer_exit_code": -15, "runner_exit_code": -15, "schema": "p4_b_ps_free_identity_feasibility_v1", "source_sha256": "e2f29f389101af35b297550b80227248cba9567539359731317c5ccc461e183c", "status": "feasible_observability", "total_wall_s": 0.358007, "web_sends": 0, "worker_exit_code": 0}
```

固定程式 gate 的意義：parent 在 observer 前以 raw libproc／sysctl、外部 `ps -ww/-wwE` 與 `lsof` 核兩個**本探針啟動**的 PID、env key 恰一值和唯一 listener；sandbox actual-script observer 在同一輪逐項讀九欄，全真後 daemon 對已捕獲的直屬 runner PID＋raw start 送 SIGTERM 並回收，退出碼 `-15`；同一受監督 observer PID 重讀，要求 daemon 四欄仍真、runner 五欄全假。outer supervisor 另核 matrix、負控、source SHA、退出碼與 cleanup 的一致性才准 status PASS。`observer_exit_code=-15` 是完成重讀後 cleanup 的直屬 observer 終止，非 runner 負控。程式只輸出固定布林／reason／耗時，不留完整 env、argv 或其他程序資料。

## 可主張與不可主張

可主張：先前同類 sandbox profile 已實測 `/bin/ps` EPERM；本輪**未在 sandbox 內重呼 ps**，而是在這台 macOS、這份既有 B 類型 profile、這個已凍結的受控 Python daemon/runner 上，證明 child-local libproc／sysctl／lsof 路線能看見所需九欄，並在真 runner 狀態改變後拒絕舊身份。這移除了「合成程序在沙盒內是否完全不可觀察」的不確定性，足以**開始**新的 B-only 身份契約與成本設計。

不可主張：原第三次 Ollama B zero-turn 已修好、真 Ollama daemon/runner 欄位等價、raw `tvsec/usec` 已與目前秒級 `ps lstart` receipt 同義、模型 SHA 時序、同模型 token 上限、≤20 秒 click→DOM、產品 Web/Brain 同 PID、答覆品質、或 B 放行。`model_calls/b_sends/web_sends=0` 是凍結探針的 source/protocol 計數，**不是外部網路監測**；外部 `ps/lsof` 原始字串未存檔，只有固定結果與 source gate 可追。異常 cleanup 時 supervisor 會優先緊急收尾而可能不保留已得 matrix；本次 `cleanup_verified=true` 僅是受控程序的程式驗證，未另做跨工具 PID 稽核。source review 與 22 個 fake tests 也不是獨立真人或跨機器重現。

下一個必要交付：先設計審查一份 B-only live identity 適配契約，列出 raw start↔現有 receipt、Ollama argv/env/listener/source 等價、TOCTOU、模型 SHA 與 20 秒成本；保留上述第三次失敗與 B no Send。此 probe 不授權直接產品改碼或第四次真模型 run；若設計無法給出同等安全證據，B 常閉。
