# P4 B 真沙盒前置 fixture invalid：前瞻設計審查稿

狀態：**只讀原因假說與新設計候選；未改 v1 harness、未執行新程序。** v1 凍結的一次 `--execute` 已用盡，shell exit 2／`fixture_invalid`、A exit -15、B/observer 未啟動；原件在 `analysis/p4_b_child_local_identity_preflight_first_result_2026-10-26.md`。不能把這件事說成新 observer 在 sandbox 失敗或成功。

## 問題與可反駁假設

v1 `_subject()` 把五個條件用短路 `or` 合併成一個 `fixture_invalid`，無法辨識是哪個前提不符。最有根據但未證實的候選：`PYTHON` 是 venv symlink，macOS `KERN_PROCARGS2` 的 `argv[0]` 可能為 Framework App executable；v1 卻要求逐字等於 symlink 路徑。前次舊替身探針用相同 `PYTHON` 啟動，oracle 要求 `argv[0] == kernel executable`，且真輪 PASS。更重要的是既存真 child/ps 校準已記錄 OS executable `/Library/Frameworks/Python.framework/Versions/3.12/Resources/Python.app/Contents/MacOS/Python`，而 venv symlink resolve 至 `/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12`：二者不只是字串不同，檔案 SHA 也分別是 `93d04da16de15e537a76fa1278accf982dd35ff1107e06460433315512eb381f` 與 `d4f152f2a753c94e0e7935c8ebbe6b2609979e1df7898422b577d0076383d08b`。所以「兩路徑 resolve 到同一 interpreter」是錯誤假設，不得作新 oracle。若新五項 bit 中只有 argv path false，而 OS executable/argv0 精確對上**事前凍結的獨立 OS App binary anchor**，才支持此假說；任何其他 bit false 都必須另定位。

## 單一核心變因與界線

唯一候選變因是**替身程序的執行檔路徑 oracle**，不改產品 operator/controller/child observer、receipt、模型 SHA、私有端點、ledger、B 題或 sandbox profile。下一版若經審查放行，應使用新的 `v2` script/schema/source SHA、新的 sibling PIDs/worker group，並唯讀沿用已凍結的舊 sandbox profile；**不建立新 model/product root**。先在 sandbox 外將五個 fixture 判斷輸出為固定布林（不輸出 argv/env 原文）。OS `executable` 與 `argv[0]` 只接受上述**事前凍結的 Framework App binary 精確路徑及 SHA**，而非 venv symlink 或靠本輪觀察自選 expected；`argv[1:]` 仍逐字等於固定 script/role。另核發動命令的 venv symlink 及其解析目標的事前 SHA，不把兩種 executable 錯當同 inode。不能把任意相同 basename、相似命令列或遺失 argv 當同一程序；raw generation、parent、env 單值與 loopback listener、source digest 均保持。若 OS 路徑或 SHA 不符，該前提 invalid，不能改 expected 追綠。

新結果即使通過，也只表示這個*新前瞻 v2* 對自建 Python 程序的真沙盒可見性；v1 FAIL 永不改分。若 v2 的非 argv bit 失敗，應保存它為不同原因並停止，不能再縮 oracle。固定 30 秒 active＋10 秒清理、exact own-PID/PGID、不碰原第三次 roots、0 模型 clone/HTTP、0 Web/B Send、0 正式 DB。任何程式或 oracle 修改前先由獨立只讀審查判定它是新的合理診斷，不是把曝光的 v1 用例調到 PASS；來源/輸入/判準需事前 SHA 凍結、fake 負控、commit/push/PR exact head，方可**另行決定**是否准一次新實測。本文件本身不授權執行。

實作凍結時須把 `legacy_symlink_exact` 明列為**診斷 bit、不能作接受門檻**；權威 argv 判準另列 `app_path_sha_exact` 加 `argv[1:] exact`，兩者都須 true。raw、parent、env、listener 仍各自獨立 true，不能因舊 symlink bit false 而宣稱整個 argv 無證。wrong App path/hash、wrong argv tail/argc、raw usec、parent、duplicate/malformed env、非唯一 listener 都要有不送 provider 的負控。這些固定布林不包含真實 argv/env 字串。

可選更保守決策：不再做新 sandbox 程序；B 留 `REVIEW_REQUIRED`，接受目前只有舊替身 PASS、新 adapter 真沙盒未證的界線。選擇新 v2 的成本很低（零模型，約秒級），但證據仍比真 Ollama 弱；進第四次模型前仍需獨立重大設計／資源審查與至少 18.73GB/create、20 秒門檻方案。
