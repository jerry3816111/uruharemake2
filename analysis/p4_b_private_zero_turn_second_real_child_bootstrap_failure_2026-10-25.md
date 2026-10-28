# P4 B 真私有 zero-turn 第二次：child bootstrap FAIL

狀態：`fail_closed`，不是 ready/stop PASS。第一次 `/var` alias 失敗和修正分別保留於 `analysis/p4_b_private_zero_turn_first_real_presend_failure_2026-10-25.md`、commit `05871ea`。第二次只在該修正提交並推 PR #435 後用**全新** model／prepared roots、單 daemon／runner、單 controller start；沒有重用第一次的一次性 root，沒有 Safari Send／B 題／正式 DB 寫入。

## 原件和直接原因

- 私有 result：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-p4-b-zero-hppmycyt/p4_b_private_zero_turn_result.json`，SHA-256 `c10e66c3e8c6ff7b09b4b2fdc6931a501cd1ef4a4bfccb4ff0b00e1337f2f47e`。prepared product root：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-19qgrglu`，one-use claim 已耗，兩個 root 均保留。
- child PID 2126 的 0600 stderr SHA-256 `d92314586cef79cb366f1bfc00f91df4fcf4db93c06e5b90d2907b61667c2043`；只在 bootstrap `_child_context`、Web import 前拋 `PrivateEndpointBindingError: private_child_argv_drift`。stdout 0 bytes，無 ready receipt。
- controller 的 0600 receipt 用 calibration 觀察的 macOS `ps` Framework App executable 算 `expected_final_argv_sha256=242d970b...b6546e05f`。同一 `.venv/product_checks/bin/python` 的 `sys.executable` 是 venv launcher，經 `_final_argv_digest` 為 `027bef8e...de2f6517cee3`；兩者解析後也不是同一執行檔。child 卻用 `sys.executable` 對比父方 **ps** digest，所以此環境必然拒絕。fake child 的 calibration 路徑與 `sys.executable` 相同，漏了此平台差異。不可藉此放寬 OS final-command identity 或略過 bootstrap 驗證。
- helper 輪詢至 child 240 秒 ready 觀察線，才回較粗的 `child_not_same_pid_ready`；總 wall 263.2617 秒。stop-attempt SHA-256 `e32732df5b41079c4e3cea14162776694e0ea3c230a3108b4db8746a7846106d` 記 `unexpected_process_absent_before_stop`、`planned_stop=false`、`signalled=false`、原 PID 已退出／7894 空。receipt 300 秒效期尚未到；這不是 expiry 或 HTTP 問題。

## 成本和清理界線

| 項目 | 第二次真執行觀察 |
|---|---:|
| 全程 wall | 263.2617 s（child ready 觀察線約 240 s，含 11.5251 s `control.start`，其後輪詢約 228.5 s；非硬 watchdog） |
| prepared warm／clone verified／runner loaded／child start | 1.9295／4.4696／6.3110／11.5251 s |
| private clone logical bytes | 4,683,088,190 B |
| warm 後 clone 的 `df` 可用量下降 | 4,096 B；不證 CoW 內部物理分配 |
| helper model-store validations／邏輯讀下界 | 3 次／14,049,264,570 B；controller/Web 未儀表化 |
| operator diagnostics | 1 setup version GET；另 1 render-only＋5 probe HTTP，0 intentional completion |
| sample RSS | runner 最大約 4,965,600 KiB、child 單次 24,912 KiB；非真峰值 |

postrun 精確 PID 1696／1761／1774／2126 均不存在；11455／49373／7894 無 listener，共用 11434 仍為原 PID 1529。helper 回 `runner_cleanup=terminated`、`daemon_cleanup=identity_drift_no_kill`、`cleanup_review_required=true`；因此不能稱私有 daemon 已按計畫 exact stop。`resource_sampling_complete=true` 只表示四種 PID 都有採樣，不表示 full pipeline cost 完整；`full_cost_instrumented=false`。`provider_network_completion_count_proven=false`、`global_provider_completion_count_proven=false`；沒有 Brain/SDK 真 child 路線，也沒有 B usage counter 證據。

判定：canonical-root 的單一前瞻修正確實把阻擋點從 child 前推進到真 child bootstrap，但原卡「同 PID HTTP ready／planned stop」仍 **FAIL**。兩次真 root 均不可重用；至多再設計一個有根據的單變因 argv 身份修正，先雙路徑差異與竄改負控，再以新 root 驗收。若仍失敗，按開發流程保留 `REVIEW_REQUIRED`，不得追改原實驗或放行 B Send。A 作者核准／真 A、B token oracle／terminal／Safari 20 秒仍 pending。
