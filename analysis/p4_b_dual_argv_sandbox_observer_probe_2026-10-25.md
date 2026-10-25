# P4 B 雙 argv 修正：真沙盒零服務觀察

狀態：原凍結方案的 child-local `/bin/ps` observer **FAIL**；第三次完整 zero-turn 尚未啟動，B 仍禁止 Send。這是預檢負結果，不覆蓋兩次真私有 zero-turn 的原始失敗。

使用第二次真執行留下的 sandbox profile（唯讀；SHA-256 `5f759a54cfc12a5e68fb73590f585f4dee9ac9f55d50c44338f5e164684e6110`）、本 worktree 的 `.venv/product_checks/bin/python`，以 `PYTHONDONTWRITEBYTECODE=1 /usr/bin/sandbox-exec -f <profile> <python> test_p4_b_private_child_bootstrap.py` 跑實際 script，退出碼 1，輸出 `{"ok": false, "reason": "ps_or_digest_unavailable"}`。同沙盒的直接診斷確認 child 呼叫 `/bin/ps` 遇 `PermissionError: [Errno 1] Operation not permitted`。現有 WIP 的 fake/契約 99/99 綠不抵銷此實機負例；此版不能提交成產品放行或做 4.68 GB clone 的第三次全量 run。

同一沙盒內、**不啟服務、不請求 provider** 的 `-c` 探索顯示，`libc.sysctl` 以 `(CTL_KERN=1, KERN_PROCARGS2=49, self PID)` 兩次呼叫取得大小及內容，均 `rc=0`：當次 buffer 3,508 bytes，`argc=3`，exec path 為 macOS Framework Python；buffer 的 argv 前段為 Framework Python、`-c`、程式碼。常數與本機 macOS SDK `sys/sysctl.h` 第 184、261 行一致。這**只證**該 `-c` 程序可讀自己的 OS argv，尚未證產品 actual-script 身份比對、ready、stop、模型請求或 Safari。

後續只能依 `research/p4_b_private_zero_turn_dual_argv_amendment1_sysctl_2026-10-25.md` 的前瞻修訂、獨立設計審查、同沙盒 actual-script 零服務探針進行；探針失敗則保留 FAIL／`REVIEW_REQUIRED`，不試第三次完整 run。這批沒有真生成、B 題、正式 DB 或 Safari 操作；全程成本主要是毫秒級零服務探針，不得與第二次 263.2617 秒冷啟成本混算。
