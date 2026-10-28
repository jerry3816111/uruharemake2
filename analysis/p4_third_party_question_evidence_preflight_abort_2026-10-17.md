# P4 第三者問句證據 gate：首個隔離產品啟動批次 0-turn abort

狀態：2026-10-17，**啟動／程序 strict FAIL；0 個使用者回合，沒有 Safari、生成或語義結果**。這不是 gate 回答正確或錯誤的證據。首輪前 scoped code、逐字六輪與 gold 已由 commit `19f9a03`、21/21 SHA manifest 凍結並推送 PR #435；本報告不改那些檔案或前批六輪 strict FAIL。

## 逐時事實與歸因界線

- 控制器在新隔離 root `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-j7hgxrgo` 啟動 `product`，run `f4165144f11a0c67`，final Python PID `11796`，預定唯一 loopback `127.0.0.1:7894`。`start` 回傳 `ready=false`，它不是成功訊號。
- 首次 `verify-ready` 回 `product_listener_not_same_pid`；隨後同 PID 的只讀 `ps`／`lsof` 一度看到 final Python 與唯一 loopback LISTEN，但控制器 `ready_recorded=false`。第二次 `verify-ready` 回 `product_not_final_python`；再次 status 為 `stage=exited`、PID 不在、port vacant。未自動重啟，也未送任何題。
- stdout 有 `* Running on local URL: http://127.0.0.1:7894`；stderr 的決定性錯誤是 Gradio `blocks.py:2807` 拋 `ValueError: When localhost is not accessible, a shareable link must be created...`。本機安裝碼的該分支在 `_frontend` 為真、`networking.url_ok(self.local_url)` 為假且未啟用 share 時執行；`url_ok` 以最多五次 `httpx.head` 判定。這只定位到**啟動內部 localhost HEAD 健康檢查未通過**，沒有證據足以斷言是 proxy、防火牆、Gradio root HEAD 狀態、沙箱或新 gate 的哪一個原因。嚴禁為通過而開公開 share link。
- 停止後隔離 DB snapshot `db_status=absent`、profile rows `[]`、turn episode IDs `[]`。沒有 conversation JSONL、沒有模型呼叫、沒有 Safari 泡泡或 graph 可評。

證據 root 保留；stdout SHA-256 `577869092aa845fd7427b48dc161602d4143438587c9c86eb2beb4b7f00ca9ff`，stderr `2beb3e4651ecb9736b58ffe02368d721181ec59416ff6c8dcd694f6f1d0abcfe`，`evidence/snapshot-preflight_abort.json` `5fbfc15ff0682d2e2dfb787f5508164766eeb6325a3c26e2a4e2122823185cc2`。root 與舊 Safari 分頁均未清除。

## 結論與下一步限制

原六輪產品契約明定意外停機是程序 strict FAIL，因此**此啟動批次已終止，不能把下一次啟動併回本批或稱 6/6 完成**。六個問題尚未對模型／Safari 曝光，gold／程式與 manifest 仍原封不動。可以另開清楚編號的全新隔離嘗試，沿用這份已凍結且未曝光的資料，但須將此 abort 留在總體產品穩定性分母，首輪前重新核 21/21 SHA、同 PID／loopback／HTTP 200 ready，仍不准答題 retry 或在看答案後換題。若後續再有環境故障，要分開保留，不把成功的環境抽樣視為量產可靠性。正式同模型比較、人評與 temporal holdout 仍 pending。
