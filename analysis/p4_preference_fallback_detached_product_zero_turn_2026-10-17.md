# P4 偏好快路產品 0-turn：隔離生命週期結果

2026-10-17，在新私有 root
`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-sjja92fg`
以明示 `.venv/product_checks/bin/python` 啟動
`p4_preference_fallback_detached_control.py start --mode product`。
此項只驗產品啟停，**沒有送模型對話、五輪題或 Safari 輸入**。

- 啟動結果 `ok=true`、run ID `8593716f2c12f285`、PID/PGID
  `35257`、UID `501`、`lstart=Sat Oct 17 02:18:49 2026`；
  start 回報 `ready=false`，沒有把 spawn 當可用。
- 跨另一個命令呼叫的 `status` 為同源存活、`stage=final_python`；
  當時 port 尚 vacant，故仍未放行。
- 隨後 `verify-ready` 核對相同 PID/UID/lstart/PGID、校準後最終
  Framework Python + 精確產品 entrypoint，前後全埠 `lsof` 僅有
  `(35257,127.0.0.1:7894)`，中間 localhost HTTP GET 回 `200`。
  `ready.json` 私有保存同一最終身份。
- `stop` 於仍 alive/ready 時送同組 TERM，結果
  `planned_stop=true`、`signalled=true`、`original_pid_exited=true`、
  `port_vacant=true`；後續 `status` 顯示 `stage=exited`。
  stdout 僅顯示本機 URL 與 `share=True` 提示，未開公開分享。

事前安全回歸：
`.venv/product_checks/bin/python -m pytest -q
test_p4_preference_fallback_detached_control.py` 為 `14 passed`，
涵蓋意外死亡不可作 planned reuse、全埠 listener 排他、隔離樹
symlink/hardlink 防護、start-error 身份不明不盲目 signal、失敗證據等。
獨立只讀安全再審准許這個**受控本機 0-turn**，不代表 production
安全；同 UID TOCTOU 與脫離程序群組的後代不可能由此完全排除。

這個 PASS 僅解除新五輪送題前的生命周期阻擋；
`≤20s` 每輪成本、真 selected plan、日文回覆、記憶 row-ID、graph
及重啟後持久性仍未驗。detached 後 exit code 不可得，保留
`unavailable_after_detach`。原先 launchd venv 0-turn 失敗與
舊六輪 strict FAIL 均不改寫。
