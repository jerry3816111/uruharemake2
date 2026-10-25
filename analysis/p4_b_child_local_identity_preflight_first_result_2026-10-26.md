# P4 B 新 observer 一次性真沙盒預檢：首輪失敗

判定：**FAIL／fixture invalid；不得說新 adapter 在 sandbox 通過或失敗。** 這是 `research/p4_b_child_local_identity_preflight_freeze_2026-10-26.md` 唯一一次 `--execute`，0 retry；原第三次真 Ollama zero-turn 的 `REVIEW_REQUIRED` 及 B no Send 不變。

## 執行前鎖與原始結果

source/fake 七檔 236/236、相鄰 67/67、compile/diff 與另一代理 source-only review 通過；產品／harness/freeze 先以 `9412508213fa1b80a7951d014d78fff60a154e4d` 推 PR #435 OPEN，執行前 remote head exact。執行後四項 SHA 仍逐字符合凍結：harness `ae2dc464...cb8c1`、harness test `66fc12e8...5acd`、adapter `e523b65a...9200`、sandbox profile `5f759a54...e6110`（完整值在凍結檔）。

唯一命令：`.venv/product_checks/bin/python p4_b_child_local_identity_sandbox_preflight.py --execute`。工具原始 shell exit **2**；工具 wall **0.239565958 s**。程式自報 active **0.052996 s**、total **0.06217 s**，不可當 Web latency。原始固定欄位 JSON 如下（從當輪工具輸出抄錄，未另存獨立 terminal transcript）：

```json
{"a_exit_code":-15,"active_wall_s":0.052996,"adapter_sha256":"e523b65add5ce75a7fdcad9524266ebe497d70e5e1899dcc3925ecf4cdd89200","b_exit_code":null,"b_sends":0,"cleanup_verified":true,"model_calls":0,"negative":{},"negative_rejected":false,"observer_exit_code":null,"positive":{},"profile_sha256":"5f759a54cfc12a5e68fb73590f585f4dee9ac9f55d50c44338f5e164684e6110","same_observer":false,"schema":"p4_b_child_local_adapter_sandbox_preflight_v1","source_sha256":"ae2dc4642b7d02aa1113d70d8e163c9817714f5566d378ed9c533640ecccb8c1","status":"fixture_invalid","total_wall_s":0.06217,"web_sends":0,"worker_exit_code":-15}
```

`fixture_invalid` 只可能出現在第一個替身 A ready 後 `_subject()` 對 raw、PPID、argv、environment exact、listener 的組合檢查；若 `observe_process` 本身拋 `ProbeError`，本程式會記為 `preflight_error`，所以這次在 sandbox 外已取得 A 的 snapshot，卻在後續聚合比較失敗。B 和 sandbox observer 尚未啟動，正／負矩陣皆空，因此**沒有取得新 adapter 在 sandbox 的觀察證據**。A 是此輪直屬子程序，回報 `-15`；worker `-15`，程式 `cleanup_verified=true`。事後唯讀 `pgrep -fl p4_b_child_local_identity_sandbox_preflight.py` exit 1／空輸出；未保存精確 PID、port 或獨立外部 cleanup transcript，不能因此稱全機審計。

## 初步原因與不能主張

一個有根據但**未被當輪原始欄位單獨證實**的原因是 harness 將 `snap.argv` 與 symlink `.venv/product_checks/bin/python` 字串逐字比較；此 symlink 在本機實際指向 `/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12`。前一個已封存 PASS 的合成探針刻意比較 `argv[0] == kernel executable`，而非逐字比較 venv symlink，顯示兩種 oracle 不等價。也可能是另外四個 `_subject` 條件；本輪固定輸出只給聚合 `fixture_invalid`，不允許事後把推測改成已證原因或改標 PASS。此首輪未觀察 sandbox，不能歸咎其 API 可見性。

後續只允許先做**只讀設計審查**：釐清 raw OS argv 與 symlink 的 canonical 語意、如何將 `_subject` 的五項 reason 分開記為無敏感布林，前瞻凍結新的 source/input/oracle、精確停損與資源；不能修改這份 v1 凍結或重跑其 `--execute` 追綠。第四次真 Ollama/B Send、Safari 20 秒、正式 A/B 仍 NO-GO；18.73GB/create 邏輯模型 SHA 成本未解。本輪不改正式 DB、不碰原始 dirty checkout或無關 output。
