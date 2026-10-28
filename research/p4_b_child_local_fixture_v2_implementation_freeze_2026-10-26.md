# P4 B fixture oracle v2：改碼前凍結候選

狀態：**獨立只讀改碼前審查 GO，僅限 v2 新檔與 fake-only 測試；actual `--execute` NO-GO。** 審查者核對 Python.app、venv 兩層 symlink／target、profile SHA 及 v1 原始 `fixture_invalid` 結果；要求 standalone、不改 v1、逐 bit 保存失敗及前瞻完整 SHA 凍結。設計基準 `research/p4_b_child_local_fixture_oracle_review_2026-10-26.md` 已在第一版錯誤 venv=Python.app 假設被否決後修正。v1 的 `fixture_invalid`／shell exit 2 及其 source/input/oracle 永遠不改、不重跑。這是已曝光 fixture 的工程診斷，非正式 holdout／真 Ollama 證據。

## 單一變因、before 和輸入

唯一變因：**synthetic fixture 的 OS executable/argv0 接受 oracle**。v1 用 `snap.argv[0] == venv symlink`，但既有同機 OS 校準指出實際 executable 可能是另一個 Framework Python.app binary；v1 的聚合 reason 又不能判定是哪一欄。v2 應保存同一新 B-only adapter、raw、PPID、env、listener、兩個 sibling listener、同 sandbox profile、同 30+10 秒與同負控；產品 operator/controller/receipt/child observer 絕不改。

v2 的 OS anchor 前瞻固定為 `/Library/Frameworks/Python.framework/Versions/3.12/Resources/Python.app/Contents/MacOS/Python`，SHA-256 `93d04da16de15e537a76fa1278accf982dd35ff1107e06460433315512eb381f`、唯讀 stat uid 0／inode 889937／regular single link；發動命令 `.venv/product_checks/bin/python` 必須是 uid 501、`readlink` 恰 `python3.12` 的 symlink（目前 inode 37200054），其下一跳 `.venv/product_checks/bin/python3.12` 必須是 uid 501、`readlink` 恰 `/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12` 的 symlink（目前 inode 37200053）。解析目標是 root-owned regular single-link binary，SHA-256 `d4f152f2a753c94e0e7935c8ebbe6b2609979e1df7898422b577d0076383d08b`、inode 889709。OS App 與 venv target **不是同一檔**。若任何事前路徑、symlink target/owner、實體檔 SHA、profile SHA 不符，記 invalid 並不啟程序；inode 只作本機診斷，跨重啟若 inode 變而 bytes/owner/target 同，須獨立審查後才能重凍結，不能執行時動態接受。不從新觀察結果反選 expected。Profile 沿用 v1 SHA `5f759a54cfc12a5e68fb73590f585f4dee9ac9f55d50c44338f5e164684e6110`，只讀，不建立 model/product root。

## 允許改動與 oracle

只允許**新** `p4_b_child_local_identity_fixture_v2_preflight.py`、`test_p4_b_child_local_identity_fixture_v2_preflight.py`、source/input/oracle SHA 凍結文件、結果、任務卡。不得編輯 v1 harness/test/result、產品、既有 profile、資料、token/baseline，亦不得新建 M 或網站。新 script 必須是可獨立審核的 standalone one-use 程式；可參照 v1 非 oracle 的程序監督/清理邏輯，但**不得 import v1 後 monkeypatch 其全域函式／常數**或暗改 v1。必要的機械複製需在 diff review 中只說明安全保持與明確 oracle 差異，不當成新能力進展。

把 A/B sandbox 外 fixture 檢查輸出為固定、無敏感字串的布林：`raw`、`parent`、`env`、`listener`、`app_path_sha_exact`、`argv_tail_exact`，另有 `legacy_symlink_exact` **僅診斷、不計 PASS**。權威 argv 要求 observed executable 與 argv0 都是上述凍結 Python.app exact path 且該檔 SHA 不變、`argv[1:]` 完全等於新 script 與 `--listen-a|b`、argc 恰 3。所有非 diagnostic bit 必須 true 才可進 sandbox observer。observer 在同 PID 下正測兩 listener 的 raw/argv/env/listener/parent 10/10 true，B 真 SIGTERM/reap 後 A 五欄仍 true、B 五欄全 false；0 模型／Web/B Send、cleanup true、退出碼與完整耗時照 v1 嚴格核。fixed result 只留 bit、reason、hash、時序及 exit，不留 argv/env 原文。

worker 內部結果 schema 固定 `p4_b_child_local_adapter_sandbox_preflight_v2`，保留 v1 的 `positive`／`negative`、same observer、cleanup、三種 0 send/call counter、SHA、active/total 和 A/B/observer exit，另加 `fixture_checks`（只允許 `a`/`b` 已啟角色，每個有 `raw,parent,env,listener,app_path_sha_exact,argv_tail_exact,legacy_symlink_exact` 七個布林）。supervisor 對原欄與新欄**同時**驗型、同一 frozen SHA、10/10／A5+B5、30+10s；外部結果再加 `worker_exit_code`。`legacy_symlink_exact=false` 不會單獨使新結果 FAIL；其餘六個 authority bit 每個都須 true 才能進 observer。fixture 失敗仍固定 exit 2 並保留可得的 per-bit 布林，不能以 `fixture_invalid` 聚合抹掉原因或輸出原字串。

fake-only 負控至少涵蓋 wrong App path/hash、venv target/hash、argv tail／argc、raw usec/PPID、env 缺失/重複/壞 UTF-8、listener 非唯一／非 loopback、fixture partial bit、同 observer negative、source/profile drift、worker PID/PGID 換代與已回收後 no kill。聚焦命令固定 `.venv/product_checks/bin/python -m pytest -q test_p4_b_private_zero_turn_operator.py test_p4_b_private_controller_seam.py test_p4_b_private_endpoint_binding.py test_p4_b_private_child_bootstrap.py test_p4_b_private_child_chain_zero_provider.py test_p4_b_child_local_identity.py test_p4_b_child_local_identity_sandbox_preflight.py test_p4_b_child_local_identity_fixture_v2_preflight.py`；再跑 constructor/Web ledger/resource-gate/controller 四檔相鄰回歸、compile、diff check；獨立 source-only review；最後固定新 script/test/adapter/舊 v1/profile/OS anchors 的完整 SHA、commit/push PR #435 exact head。**只有所有前置通過且另行明確 GO 一次 v2 實跑，才准一個新 actual-script 輪次，0 retry。** 任一 FAIL 原樣保留，不放寬 oracle、不重跑 v1 或 v2 追綠。

即使 v2 真 sandbox PASS，仍非真 Ollama argv/env/model SHA／Web ready／B token upper bound／Safari ≤20 秒。第四次真 Ollama、B Send 與正式比較仍需新的重大設計和資源審查；18.73GB/create 邏輯讀與 A 作者真評均未解。

若 v2 未來真實 sandbox 的全部 authority bit 通過且 `legacy_symlink_exact=false`，僅**支持**「v1 的 argv symlink 比對可能造成聚合失敗」，不追認歷史唯一原因；v1 另外四種 bit 當時未記錄，無法補證。
