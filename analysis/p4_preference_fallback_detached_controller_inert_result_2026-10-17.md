# P4 偏好快路 detached controller：模型前限定驗證

2026-10-17。依事前
`research/p4_preference_fallback_lifecycle_amendment_2026-10-17.md`
新增 `p4_preference_fallback_detached_control.py`。此檔只提供本機
one-shot `start/status/verify-ready/stop`；本報告尚未執行產品入口、
模型、Safari 或新五輪題，不能稱產品 gate PASS。

## 實際無模型證據

`.venv/product_checks/bin/python -m pytest -q
test_p4_preference_fallback_detached_control.py`：`14 passed`。
涵蓋 wrapper／venv pre-main／Framework final Python 的有界命令轉換、
未知 command／新 lstart 拒絕、listener owner／loopback scope 拒絕、
HTTP 200 前後同身份、身分不合停止無 signal、零產品校準、mock 產品
start metadata，以及真 `/bin/sleep` 跨呼叫同 root 新 run。
後續安全審查增加並通過：未預期 PID 消失只寫 `stop-attempt` 失敗
證據，不產生 planned `stop.json` 且拒同 root 重啟；產品未 ready
的清理同理。same-root 只接受事前 ready 的**同 final identity**、
確實送 TERM 後 PID/port 退出的 planned stop；inert 以原身份替代
ready。查整個 7894 埠的 lsof listener 集合，拒其他 PID 或 wildcard，
不再只查預期 PID。重用 root 在任何 `build_runtime_layout`/preflight
前對 memory/session/web_logs 子樹用 `lstat` 拒 symlink、外人 UID、
hardlink／特殊檔，測試內層 symlink 指向外部 sentinel 時確實 fail
closed、外部檔不變。每段 metadata 存實際隔離 DB/session/log/root
路徑與 host/port，讀回時核對。

另以真 inert 啟動刻意造成 pointer 失敗：cleanup 只向當次已驗證的
UID/PID/PGID/command 新 session 發 TERM，檢整組 member 空、PID
消失、port vacant，並保留 0600 `start-failure.json`；未知 identity
的 mock 反例未發訊號且留 `cleanup_verified=false`。這仍不是 host
故障恢復或真產品可靠性證據。
`py_compile` 與 `git diff --check` 通過。

真 inert run root
`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-v4wcxijb`：
第一 run `4a507986838c9955`／PID `32799`，另一次
`exec_command` 的 status `same_origin_alive=true`、`stage=inert`；
`verify-ready` 被拒為 `http_readiness_product_only`；stop 有
`original_pid_exited=true`、`port_vacant=true`。同 root 第二 run
`f2565c4e7ea117b4`／PID `32858`，`previous_run_id` 正確且前段
metadata/log/stop 不覆寫；第二段亦 exact stop、PID 消失、port vacant。
root 0700，per-run metadata/profile/stdout/stderr/stop 0600。

以同隔離 profile/env、精確產品 venv 做**零模型校準**，在 marker
`python-calibrated` 已輸出後才觀察 `ps`：此 host 的最終 argv0 是
`/Library/Frameworks/Python.framework/Versions/3.12/Resources/Python.app/Contents/MacOS/Python`，
並非 venv symlink。controller 因此只允許 sandbox wrapper、同一
venv Python pre-main、校準後的 final Python + 精確產品 entrypoint，
且 PID／UID／lstart／PGID 持續一致；ready 後以 final identity 綁定。
另以臨時 `/usr/bin/python3 -m http.server 7894 --bind 127.0.0.1`
驗證真 `lsof` parser：初版 PID `33576`、全埠排他版 PID `34946`
的 loopback listener 都被正確歸屬；終止後 PID 退出、port vacant。
沒有使用 Safari。

## 接續 gate 與限制

真正產品 0-turn 尚未執行。下一步應從**新** root 用明示產品 venv
`start --mode product --python .venv/product_checks/bin/python`，在首輪
之前反覆只讀 `status`／`verify-ready`，要求相同最終 Python PID
在 HTTP 200 前後獨占 `127.0.0.1:7894` listener；然後 exact stop、
舊 PID 消失、port vacant。失敗不得送五輪／凍結新 gold。

繼承的 safe launcher preflight 第一層仍有 unsandboxed import，後續
probe 與真正 child 才在 write sandbox；metadata 標
`legacy_base_import_unsandboxed_later_probes_sandboxed`，不能宣稱整條
preflight 完全 sandboxed。detached 後 exit code 無法可靠 `waitpid`，
保留 `unavailable_after_detach`。目前跨 `exec_command` 的 inert 證據
不能保證跨 Codex host、長期 production 或真產品 0-turn 穩定。
