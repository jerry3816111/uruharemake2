# P4 B 第三次真私有 zero-turn：REVIEW_REQUIRED

**結論：第三次且最後一次預註冊真 zero-turn 仍 `fail_closed`。** 不以第四組 root 重跑追綠；B 不可 Send。前兩次負結果和兩個修正批次分別見 `analysis/p4_b_private_zero_turn_first_real_presend_failure_2026-10-25.md`、`analysis/p4_b_private_zero_turn_second_real_child_bootstrap_failure_2026-10-25.md`。本次在雙 argv／真沙盒 actual-script 預檢通過、程式提交 `1dd215a` 並推 PR #435 exact head 後，才消耗第三組全新 one-use roots。無 Safari Send、B 題、正式 DB 寫入或外部部署。

## 最小反例與歸因

- 私有 result：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-p4-b-zero-fyuq6pek/p4_b_private_zero_turn_result.json`，SHA-256 `6818ce113f52a30f4c6662ed526fb84589b26fd224598e2aa293623bd62fd21a`。prepared root：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-xremdzdp`。兩者 one-use 均耗盡、保留原件。
- child PID 13537 的 stderr SHA-256 `43b979e2a2d1ce772e33f881202883c9d7b1bd4b6183ac3ec069c98b51b964ae`。stack 已越過第一次 `_child_context` 的 OS＋in-process argv 核對，進到 `bootstrap_private_child → validate_private_endpoint_binding → _inspect_live_identity → _process_start`，於 Web import 前呼叫 `/bin/ps -p <daemon PID> -o lstart=`，sandbox 回 `PermissionError: [Errno 1] Operation not permitted`，包成 `process_generation_unavailable`。這表示新雙 argv 修正把第二次的 `private_child_argv_drift` 阻擋點移過，但**未讓產品 ready**；不是日文回覆或模型答題失敗。
- 問題不是一個孤立的 `/bin/ps` 呼叫：同一 `_inspect_live_identity` 還會用 `/bin/ps -wwE` 觀察 daemon 環境，並由 `p4_b_isolated_ollama_identity_probe._process/_listener` 間接用 `/bin/ps`、`/usr/sbin/lsof`。這些是現有「每次 provider create 前驗私有身份」的硬 gate。同沙盒零服務只讀診斷顯示 `/bin/echo` 可啟、`/bin/ps` 被拒、`/usr/sbin/lsof -p self` 可啟；**不能把 ps 的 EPERM 外推為所有 subprocess 均被拒，也不能把 lsof self 成功外推到 daemon/runner 身份驗證。** 不能只 mock 第一個 `_process_start` 或跳過 live check 冒充完成。
- 同一只讀診斷中，in-process `KERN_PROCARGS2` 對同 uid 的既有外部 PID 只完成 buffer size query，`libproc` BSD info 只回固定長度；尚未解析外部程序 argv、env、啟動代次或 listener。它們是下一輪設計候選，不是本次產品證據。
- helper 因等待 child ready 觀察線約 240 秒，最終只報較粗的 `child_not_same_pid_ready`；總 wall `262.7400 s`。stdout 0 bytes，無 HTTP ready receipt；`planned_stop=false`。0600 stop-attempt SHA-256 `e44d3a1e6ec67eef5ad3b164a1a53847f48bcbea468e039dca1d3eec49215e15` 記 child 已意外退出、沒有發停機訊號。

## 三次狀態、成本與收尾

| 真實執行 | 失敗階段 | wall | child HTTP ready／planned stop |
|---|---|---:|---|
| 第一次 | helper `/var` 非 canonical root，child 前拒絕 | 23.8662 s | 無／無 |
| 第二次 | child 將 OS Framework 與 venv `sys.executable` 當成同一 digest | 263.2617 s | 無／無 |
| 第三次 | 雙 argv 已過，後續 live-identity subprocess 在 sandbox EPERM | 262.7400 s | 無／無 |

第三次 clone 邏輯量 `4,683,088,190 B`；helper 3 次 model-store SHA 的邏輯讀取下界 `14,049,264,570 B`，controller／Web 額外檢查未儀表化；warm／clone verified／runner loaded／child start 分段 `1.6080／4.0884／5.5874／11.5636 s`。clone 前後 `df` 差只有 8,192 B，不證 APFS 物理零配置；冷啟與 240 秒等待也不是 Safari click→DOM latency。child brief、無 child RSS sample，`resource_sampling_complete=false`、`full_cost_instrumented=false`。helper 0 有意生成、0 Safari Send、0 B 題／正式 DB；`provider_network_completion_count_proven=false` 與 `global_provider_completion_count_proven=false`，不可宣稱全域零 completion。

事後精確 PID 13110／13164／13177／13537 均不存在，私有 11455／runner 56707／產品 7894 無 listener；共用 11434 仍為原 PID 1529／原 generation。helper 記 `runner_cleanup=terminated`、`daemon_cleanup=identity_drift_no_kill`、`cleanup_review_required=true`，所以只能說事後觀察已空，**不能說按計畫精確清理通過**。舊 root、stderr、stop-attempt 與新原件不刪。

## 設計審查必決的下一步（尚非實作授權）

兩個有根據修正批次已用完。不得補一條例外或降低 receipt／live identity gate；先比較以下單一核心設計與代價，選定一個後重新凍結 before、成功／失敗、零服務真沙盒探針與安全門檻，才談新實作：

1. **不依賴被拒 `/bin/ps` 的 child-local 身份觀察。** 研究 macOS in-process API 能否同時核 daemon/runner PID generation、argv／環境；listener owner 可另用經真沙盒驗證的窄義觀察，但不能由 `lsof -p self` 推論已可核外部 listener。任何要素無可靠來源就 NO-GO。可能牽涉不穩定 OS API、權限、FD/socket 解碼與每次 create 的檢查成本；不能只拿 `proc_pidpath` 當完整身份。
2. **sandbox 外的受控 attestation broker。** parent 依原 `/bin/ps`／`lsof` 實際檢查，給 child 具 run／PID generation／nonce／短效與單次使用語意的身份結果；child 在每次 create 前要求新鮮結果、缺 broker 時 fail closed。需審查 IPC、重放與時序窗口、同一正式 ledger/gate、20 秒產品延遲及 broker 故障，不可直接把初始 receipt 當永久證據。
3. **保留目前安全常閉並停止此 B 子路線。** 若前兩案成本／可靠性不足，就記 B no-go，不以多加沙盒規則或放寬強 baseline 換 PASS；仍可在另已定案且獨立的產品範圍繼續，但 B 真比較、Safari 與完成聲稱保持 pending。

目前只能主張：B-only 雙 argv 在真沙盒的首次 `_child_context` 越過了上次失敗，並證明下一個硬阻擋是 live-identity 的子程序依賴；**不能主張**私有 Web 已 ready、A/B 可比較、日文／記憶／VRM／Function Calling 已在此路線驗收、優於 LLM，或更接近完成候選人類反應方程式。下一步為設計審查，不是第四次模型冷啟。
