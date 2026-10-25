# P4 B synthetic fixture v2：唯一一次真沙盒預檢

判定：**窄義 PASS／`adapter_visibility_feasible`；不放行真 Ollama、Web/B Send 或 Safari。** 這是 `research/p4_b_child_local_fixture_v2_preflight_freeze_2026-10-26.md` 凍結後唯一一次新 v2 `--execute`，0 retry；v1 唯一 `fixture_invalid` 失敗原件仍原封不動。執行前新檔 fake 48/48、聚焦 284/284、相鄰 65/65、compile/diff 通過；獨立來源及執行前審查各自條件式 GO。`826f04b6efbbd6d3bcb638edf43fb4da14967251` 已推 PR #435 OPEN 且實跑緊前 `headRefOid` 精確相同；當時 Git 只剩無關 `?? output/graduate_application_report/`，未 stage 或觸碰。

## 原始結果與對照

唯一命令：`.venv/product_checks/bin/python p4_b_child_local_identity_fixture_v2_preflight.py --execute`。shell exit **0**；工具 wall **0.5196145 s**；程式自報 active **0.363141 s**、total **0.415383 s**。這不是 Web click latency、模型 latency 或 20 秒產品驗收。原始 tool stdout JSON：

```json
{"a_exit_code": -15, "active_wall_s": 0.363141, "adapter_sha256": "e523b65add5ce75a7fdcad9524266ebe497d70e5e1899dcc3925ecf4cdd89200", "b_exit_code": -15, "b_sends": 0, "cleanup_verified": true, "fixture_checks": {"a": {"app_path_sha_exact": true, "argv_tail_exact": true, "env": true, "legacy_symlink_exact": false, "listener": true, "parent": true, "raw": true}, "b": {"app_path_sha_exact": true, "argv_tail_exact": true, "env": true, "legacy_symlink_exact": false, "listener": true, "parent": true, "raw": true}}, "model_calls": 0, "negative": {"a_argv": true, "a_env": true, "a_listener": true, "a_parent": true, "a_raw": true, "b_argv": false, "b_env": false, "b_listener": false, "b_parent": false, "b_raw": false}, "negative_rejected": true, "observer_exit_code": -15, "positive": {"a_argv": true, "a_env": true, "a_listener": true, "a_parent": true, "a_raw": true, "b_argv": true, "b_env": true, "b_listener": true, "b_parent": true, "b_raw": true}, "profile_sha256": "5f759a54cfc12a5e68fb73590f585f4dee9ac9f55d50c44338f5e164684e6110", "same_observer": true, "schema": "p4_b_child_local_adapter_sandbox_preflight_v2", "source_sha256": "7d342a31b58a79c456ef35cdaa934a50b6a6c0b4b0d4373051fc9976fae10429", "status": "adapter_visibility_feasible", "total_wall_s": 0.415383, "web_sends": 0, "worker_exit_code": -15}
```

A/B 各六個 authority bit 全真，兩個 `legacy_symlink_exact=false` 不計失敗；同一 observer 的 positive 10/10 true，B 真 SIGTERM/reap 後 negative A5 true/B5 false，四個 exit 均 -15，cleanup true。因此本次證明**合成 Python listener** 在既有 sandbox 下可由新 adapter 讀到 raw/argv/env/listener/parent，且同 observer 能拒絕已終止 B。v1 沒保存逐位前提，因此「舊 venv symlink 逐字 oracle 可能導致 v1 失敗」只獲支持，不能確證它是唯一根因；不能把 v1 改判 PASS。

執行後 11 項凍結 SHA 逐項仍符合原值，包括新 script/test、adapter、舊 v1 script/test、兩份設計/前置、舊失敗報告、profile、OS App 與 venv binary。`pgrep -fl p4_b_child_local_identity_fixture_v2_preflight.py` exit 1／無輸出；這不是獨立 exact PID/port audit。`model_calls=web_sends=b_sends=0` 是 harness 程式路徑的計數，非全機網路稽核，且沒有正式 DB 或產品資料寫入的全機證明。獨立只讀結果複審確認窄義 PASS 與上述界線。

## 剩餘產品 gate

原第三次真 Ollama zero-turn `process_generation_unavailable`／`REVIEW_REQUIRED` 不因合成替身 PASS 而被洗白；第四次真 Ollama、B Send、Safari 皆未授權。真 B 還需新設計審查：完整 Web/Brain/B Send 轉移來源閉包、真 Ollama daemon/runner argv/env/listener/model SHA 等價、M21 及 token/ledger、每 create 約 18.73GB 邏輯 SHA 讀與 ≤20 秒 click→DOM 成本、fresh roots/PIDs/cleanup、A 作者真評。不能把這次 0.415 秒代入真模型成本，也不能宣稱全系統或人類反應方程式已完成。
