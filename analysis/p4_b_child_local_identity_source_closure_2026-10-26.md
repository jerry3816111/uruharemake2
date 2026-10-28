# P4 B 零輪身分鏈來源盤點（改碼後、真沙盒前）

本表只涵蓋 B 私有 zero-turn 的 operator→controller→pre-Web child 身分、隔離與資源准入路徑；不是整個 Web／Brain／B Send 的 transitive source closure。來源凍結是同一使用者下的 cooperative SHA 與 Git HEAD 核對，不是程式簽章或原子 OS 保證。前置只讀盤點見 `analysis/p4_b_source_closure_inventory_2026-10-26.md`；原真 Ollama 第三次失敗仍為 `REVIEW_REQUIRED`。

`B_COMMITTED_SOURCES` 目前列 16 個檔，controller 每次在 B static preflight、receipt 前與 child Popen 前檢查 live bytes = Git HEAD；`private_child_source_digests()` 把同 16 檔的 SHA 寫入 0600 receipt v4，child 在 Web import 前及每次 create 前重核。下表逐函式標出 *此窄路徑* 的用途；這不代表被列檔案的所有 import、任何未列出的 Web overlay 或 B Send 生成路徑均已封閉。

| 來源檔 | 這條零輪路徑的實際函式／作用 | controller HEAD／child receipt |
|---|---|---|
| `p4_b_private_zero_turn_operator.py` | `run_once`、`_capture_raw_identity`、`_write_descriptor`、`_stop_exact`：首次見證、v2 descriptor、限縮清理 | bound／bound；operator 自身於 daemon 前與 descriptor 前另核 HEAD SHA |
| `p4_stateful_private_evidence.py` | operator 子程序的 `prepare_cache`／`warm_cache`：私有 ONNX root 準備 | bound／bound；operator 在 cache 前、cache↔warm 間與兩次動作後再核相同 HEAD SHA |
| `uruha_compact_planner_p2.py` | `_REQUIRED_JSON_SCHEMA_FORMAT` 供 probe `_fixed_request` 的零完成 render-only 請求 | bound／bound；其生成用途仍屬 B Send 未驗 |
| `p4_b_isolated_ollama_identity_probe.py` | `_model_store`、`_process_identity`、`_fixed_request`、`probe`；外部模型／程序證據、child 私有模型雙掃 | bound／bound；child 不呼叫其中的 `ps` 身分函式 |
| `p4_preference_fallback_detached_control.py` | `_b_descriptor`、`_b_controller_witness`、`_b_static_preflight`、`start`、`verify_ready` | bound／bound；controller 是自身 HEAD snapshot 的項目 |
| `p4_b_safe_isolated_product_launcher.py` | root 建立、Python 解析、既有 prepared layout | bound／bound |
| `p4_b_safe_isolated_product_launcher_v2.py` | `write_sandbox_profile`／`sandbox_command` | bound／bound |
| `p4_exec_detached_lifecycle_probe.py` | controller 使用的 PID／代次與啟停觀察 | bound／bound |
| `p4_preference_fallback_launchd_control.py` | `_isolated_env` 的私有 child 環境建立 | bound／bound |
| `uruha_p4_b_child_local_identity.py` | `raw_generation`、`observe_process`、`owns_loopback_listener`、`argv_digest`，child 不執行 `/bin/ps` | bound／bound |
| `uruha_p4_b_private_endpoint_binding.py` | `issue_private_child_receipt`、`_inspect_live_identity`、`validate_private_endpoint_binding`；receipt v4、兩端 raw＋模型檔掃描 | bound／bound |
| `uruha_p4_b_private_child_bootstrap.py` | `_child_context`、`bootstrap_private_child`、`revalidate_private_child_before_create` | bound／bound |
| `uruha_p4_b_resource_gate.py` | `P4BResourceGate`，M21 生成嘗試預設常閉 | bound／bound |
| `uruha_compute_ledger.py` | 同一 ledger 的 provider create 前後 gate 與重驗接線 | bound／bound |
| `uruha_web_ui_product_p4_preference_fallback.py` | 固定產品 entry 在 Web import 前先 bootstrap | bound／bound |
| `uruha_web_ui.py` | 私有 boot state 與 ledger 傳入 Web Runtime | bound／bound |

這 16 個 *已列名、會決定本窄路徑* 的 repo 來源目前無 `missing`。`p4_b_isolated_ollama_identity_probe.py` 的 `ps` helper 只在 sandbox 外 operator/controller 使用；child 的 binding 只匯入其 model-store/file SHA helper，pre-Web 與 pre-create B live 身分路徑改用新 observer。舊 `ps lstart` 秒級欄仍由外部 operator/controller 保留作稽核，不能替代 raw 微秒代次。

未關閉的邊界：Web entry 的 overlays、`uruha_brain_mac.py`／RightBrain／native endpoint、compact planner 的生成用途及它們的 transitive imports 尚未逐入口 source-close；這些是 B Send 的必要後續工作。整個 Web import 是否有非預期 provider 副作用、真 Ollama argv/env 相容、真 sandbox 可見性、真成本、Safari 20 秒和正式比較也尚未由此表證明。若找到新的會決定零輪身份／隔離／M21 准入的 repo 函式，這份 16 檔表立即不再完整，必須先補前瞻盤點，不可宣稱產品放行。
