# P4 B 新 observer 一次性零模型真沙盒預檢凍結

狀態：**source/input/oracle frozen candidate；尚未執行 `--execute`。** 真實執行必須先經獨立 source-only 審查 GO，七檔 fake-only 與相鄰回歸通過，精確 commit/push 並核 PR #435 remote head。這份只允許一次 actual-script 零模型預檢、0 retry；不授權第四次真 Ollama、B Send 或 Safari。凍結背景及停損見 `research/p4_b_child_local_identity_implementation_freeze_2026-10-26.md`。

## 不可事後改的輸入及來源

- 執行命令：`.venv/product_checks/bin/python p4_b_child_local_identity_sandbox_preflight.py --execute`，只在安全 worktree。
- 新 harness SHA-256 `ae2dc4642b7d02aa1113d70d8e163c9817714f5566d378ed9c533640ecccb8c1`；fake test SHA `66fc12e82418105ea2e76a7edcfa3894139dc7fb91d7e7fbfca9fef6cabf5acd`；實際被測 adapter SHA `e523b65add5ce75a7fdcad9524266ebe497d70e5e1899dcc3925ecf4cdd89200`。
- 真 profile 路徑：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-xremdzdp/p4_preference_fallback_detached.6a0185bb8bc10e98.sandbox.sb`；SHA-256 `5f759a54cfc12a5e68fb73590f585f4dee9ac9f55d50c44338f5e164684e6110`。若檔案不存在／SHA 不合，記 invalid，不換 profile 追綠。
- 兩個不同於上次 probe 的受控 Python sibling listener：直屬 worker 的 A/B 程序，各在 loopback 隨機私有 port，只帶 `URUHA_B_IDENTITY_SYNTHETIC_ROLE=a|b`；相同 sandbox observer PID 依序量正測，B 直接 SIGTERM/reap 後量負測。不是 Ollama daemon→runner，也不 clone 模型、啟 Web 或送 B 題。
- 30 秒 active＋單一 10 秒清理；worker 及 observer 只處理本次新 PIDs/PGID，先核 raw generation；任何 identity 不確定、cleanup 不可核，均 no-go 並留原件，不以較弱 oracle 重跑。

## 固定判準與結果欄

正測 `a_raw/b_raw`、`a_argv/b_argv`、`a_env/b_env`、`a_listener/b_listener`、`a_parent/b_parent` **10/10 必須 true**。負測同 observer PID 下 A 五欄維持 true、B 五欄全部 false，`negative_rejected=true`、`same_observer=true`、`cleanup_verified=true`、B exit `-SIGTERM`、observer exit 0 或受監督 SIGTERM、shell exit 0、三種送出/模型計數 0，才稱 `adapter_visibility_feasible`。必須保存 raw JSON、原始 shell exit、active/total wall、source/profile SHA、正負矩陣與 exact cleanup 結果；不保存完整 argv/env 或聊天內容。

任何欄缺失、程序代次變更、來源/profile 漂移、超時、非預期退出或 cleanup 不可證，均保留 FAIL/invalid，**不再試第二次**。即使 PASS，也只說明新 adapter 在同 sandbox 對自建 Python listener 可見；不證真 Ollama flags/model SHA、operator→controller→receipt→產品 child 真輪、20 秒 click→DOM 或正式比較。第三次真 zero-turn 原失敗與 B `REVIEW_REQUIRED` 均不改。
