# P4 偏好快路產品 probe：背景程序生命週期事前修訂

狀態：2026-10-17；新五輪資料／gold **未 freeze、未送模型或 Safari**。
這是 `p4_source_bound_preference_fresh_probe_plan_2026-10-16.md` 的
操作層修訂，不改五輪 exact input、語義／DB／20 秒門檻或唯一核心
fallback 變因。原計畫要求 GUI launchd job；這項要求在任何新輸入前
因 0-turn readiness 實測失敗而修訂，不能事後稱原規格已通過。

## Before 與選擇原因

launchd `/bin/sleep` 可獨立存活，但產品 venv 的完整產品程序尚未
產生 listener：PID 7514 的 795/795 個短樣本停在 Python 入口前
`open$NOCANCEL`，stdout/stderr 空。隔離 Python-only 20 秒探針中，
**精確產品** `.venv/product_checks/bin/python -c print(...)` 無 marker、
以 alarm 14 結束；舊 Style-Bert venv 同樣；`/usr/bin/python3`
有 marker 並 exit 0。沒有證據指出具體檔案或 TCC 根因。三個 job
都已 exact stop，7894 空閒；詳見
`analysis/p4_preference_fallback_launchd_product_preflight_stall_2026-10-16.md`。

另以相同沙盒 profile／curated env 從 Codex exec context 建立新
session：`/bin/sleep` 在不同命令呼叫仍在，精確產品 Python-only
輸出 marker，PID 消失；兩者都有私有 root、身分核對與停止證據。
這只證明本次跨 exec-call 可行，不證明產品、跨 Codex host 或
production 可靠性。詳見
`analysis/p4_exec_context_detached_zero_product_probe_2026-10-17.md`。

## 單一操作修訂與不變 gate

本批只允許改用 **exec-context detached、無自動重啟** 的本機產品
controller。它必須繼承同一現有 safe launcher 的隔離 preflight 與
write sandbox；0700 launcher-owned 新 root、0600 per-run metadata／
stdout／stderr／stop 證據，僅 localhost，絕不使用正式 DB。開始前
確認 port vacant；新 session 記唯一 run ID、PID、UID、開始時間、
完整 command、PGID 與 root。啟動成功不等於 ready；在首輪前
必須核對**同一**子程序/身份在 HTTP 200 前後擁有 127.0.0.1:7894
LISTEN。身份或 port 歸屬不明即 fail closed，不送 Safari。
若沙盒 wrapper 以 `exec` 正常轉成最終產品 Python，PID 可不變而
command 會變；controller 必須事前限定允許的 wrapper→Python
轉換，記錄兩邊身份，並在 ready 後重新綁定最終 command／開始時間
與 root，停止時只驗最終已記錄身份，不能把任意 command 變化視為
正常或沿用 wrapper 的 command 猜測身份。
0-turn readiness 觀察最多 120 秒；逾時要先保存 status/log，精確
stop 並標記啟動 gate 失敗，不得無限等待或直接送 Safari 試運氣。

真產品 0-turn ready 後先 exact stop，核原 PID 消失、listener 空閒，
再以全新 root 起五輪驗收；不能將 preflight root 改作正式五輪。
五輪中的 T3 後仍在**同一隔離 root/DB**，確認舊 PID/port 退出，
用新 run ID/PID/session 重啟，保留兩段 log/metadata，不覆寫。
每輪輸入前再核 ready／身份；非預期服務死亡、身份不符、額外
重啟或無法退出均依原計畫 strict FAIL，0 retry、不重送、保留原始
結果。detached child 在 parent 消失後的 exit code 若不可得記
`unavailable`，不得猜為 0。controller 停止只向核對過的精確
同 UID/PID/start/command/PGID 發 TERM，身分變了就拒停，絕不
使用廣泛程序名稱清理。不得解除 macOS 權限、防護或關閉既有服務。

產品五輪的原語義、日文、graph、逐輪 row-ID、episode、等待 `≤20s`、
token/延遲記錄和 0 retry 全部不變。改啟動環境會影響性能比較，
因此舊 T2 `26.5627s` 與本批秒數仍不可直接視為同條件因果差；
只比較已核對的 call-path，保留 runtime 成本的實際測量。

這份設計審查與實作屬同一產品 gate 的必要操作修復，**不是新 M、
不是額外模型能力**。controller 的 inert 測試、真產品 0-turn
ready/stop 都必須在五輪 JSON/code/plan hash freeze 前完成；若
做不到，產品層維持 pending 並交付負面紀錄，不能放寬 gate。
