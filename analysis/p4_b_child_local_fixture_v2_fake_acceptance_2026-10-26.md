# P4 B synthetic fixture oracle v2：source/fake 驗收

判定：**只通過 source／fake-only 契約；真沙盒尚未執行，產品 B 仍 `REVIEW_REQUIRED`。** v1 唯一實跑 shell exit 2／`fixture_invalid`、A -15、B/observer 未啟動與空矩陣保留，不回寫、不重跑，也不能事後斷言其唯一原因是 argv symlink。

## 單一修正與 before／after

本次只新增 standalone v2 harness 與假測；產品 observer、v1 harness／結果、sandbox profile、模型／Web／Safari 均未改。v1 把 A 的 raw、PPID、argv、env、listener 合成一個 reason，無法從失敗得知哪項；v2 把它拆成 `raw,parent,env,listener,app_path_sha_exact,argv_tail_exact` 六個權威布林，另有不影響 PASS 的 `legacy_symlink_exact` 診斷位。v2 先驗本機 Python.app 與 venv 兩個**不同** binary 的路徑／SHA、兩層 symlink／owner／inode、原 sandbox profile SHA；worker 啟 A 前再驗一次。A 失敗仍保留逐位結果及監聽埠 cleanup 核對，不會偷啟 B 或 observer。其餘同 observer 10 欄正測、B SIGTERM/reap 後 A5 true/B5 false 的負控、30+10 秒與 0 retry 不變。

新檔本身 48/48 fake-only；凍結八檔聚焦命令 284/284；相鄰 constructor/Web ledger/resource gate/controller 四檔 65/65（9 個既有第三方警告）；兩個新 Python 檔 `py_compile`、`git diff --check` 通過。獨立只讀審查抓到 App/venv terminal 路徑使用會跟隨 symlink 的 `stat()` 缺口；已改 `lstat()` 並加入兩個 symlink 負控後複審 GO **僅 scoped source/fake commit**。本次測試沒有啟動 listener、sandbox、Ollama 或 Web，沒有 B Send。相鄰 65 與上一輪 67 是不同命令／收集範圍，不合併或冒稱退步。

Source/fake commit `c1bf851fe8cc86cc8dae74c5cc6aa1cf21a92f0d` 已推既有 PR #435。實跑須另按 `research/p4_b_child_local_fixture_v2_preflight_freeze_2026-10-26.md` 完整 SHA 凍結、獨立執行前 GO、PR exact head 核對，且只可一次。即使未來 v2 真沙盒 PASS，也只證合成 Python listener 可由同 sandbox 觀察；不證真 Ollama flags/model SHA、Web ready、B token upper bound、Safari ≤20 秒、人評或正式比較。若六權威位全真且 legacy 位為假，只能**支持** v1 argv 假說，無法確證舊輪唯一根因。
