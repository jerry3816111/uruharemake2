# P4 新入口 0-turn 獨立程序啟動卡住：模型前負證據

2026-10-16，發生於新五輪 JSON/程式 SHA freeze 與任何新 Safari
輸入之前；不是回覆品質或模型延遲結果。新 safe launcher 的
`check` 通過（入口、source/question chain 六鍵 preflight 全 true，
0 server／0 model／0 Safari）。launchd controller 的 `/bin/sleep`
inert start/status/stop 及同一 root 新 label/PID restart 已驗證。

第一次產品 0-turn `start --mode product --python
.venv/product_checks/bin/python --port 7894`：獨立 root
`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-4ls7_rf8`，
label `org.uruhabrain.p4.preference.05a6155fbd17d28a`，
PID `7514`、PPID `1`，`launchctl` 為 running。`verify-ready`
多次回 `product_not_ready_or_not_own_listener`，當時
`lsof ... -iTCP:7894 -sTCP:LISTEN` 無 listener、stdout/stderr
皆 0 bytes。`sample 7514 1 -mayDie` 約一秒的 795 個樣本全在
Python `Py_InitializeFromConfig` → `_PyConfig_InitPathConfig` →
`getpath_readlines` → `_Py_wfopen` → `open$NOCANCEL`，physical
footprint 約 4609K，表示尚未能證實進入產品 Python 程式。
sample 在工具側寫出
`/tmp/Python_2026-10-16_221834_D4zl.sample.txt`；它是診斷輸出，
不是產品原始 log。實際卡住的檔案路徑／OS 原因仍未知，**不能**
直接歸因 TCC、沙盒或模型。

已用 controller `stop --runtime-root <上述 root>` 精確 bootout
這個 label；`original_pid_exited=true`、`port_vacant=true`，
stop JSON 保存在同一隔離 root。沒有送任何新五輪題、沒有正式
DB 寫入。為縮小原因，從 Codex `exec` context 以同一
`sandbox-exec` profile、乾淨的 `HOME/TMPDIR/PATH/LANG` 直接執行
同一 venv Python `-c 'print("python-ready")'`，立即 exit 0；
這只表明相同 profile 在另一個 process context 可啟動，仍不能
證明 launchd 卡住確因 macOS 權限。下一步是**無模型**的
launchd Python-only 探針，若仍卡住則審查可歸因的安全替代
生命週期；未找到穩定啟動前不做 Safari 新批次，也不重送舊題。

## 無產品 Python-only 對照（續作時核對）

同一 launchd GUI job／sandbox profile／隔離環境下，使用 20 秒 OS alarm
只執行 `python -c 'print("python-ready", flush=True)'`，**沒有 import
產品、啟模型或開 Web**。前一次探針誤選原始 checkout 的
`Style-Bert-VITS2/venv/bin/python`，不能拿它直接代表產品 venv；
因此另以產品**精確路徑**重測，保留兩者，不混淆：

| Python | 隔離 root | 觀察 | exact stop 後 |
|---|---|---|---|
| 本安全 worktree `.venv/product_checks/bin/python` | `.../uruha-product-87escpa6` | 20 秒無 stdout/stderr，launchd `Alarm clock: 14`，`probe_outcome=timed_out` | label 卸載、原 PID 退出、埠空閒 |
| 原始 checkout `Style-Bert-VITS2/venv/bin/python` | `.../uruha-product-iavcx5te` | 同樣 20 秒無 stdout/stderr，`timed_out` | 同上 |
| `/usr/bin/python3` | `.../uruha-product-zh44_sn5` | stdout 精確 `python-ready\n`、exit 0，`probe_outcome=passed` | 同上 |

上述 root 的 0600 stdout/stderr/stop record 均保留；2026-10-17
用 controller `status` 對三個 root 重讀，均 `loaded=false`，結果由
`stop_record` 回溯。`launchctl list` 無本卡 job、7894 無 listener。
這把故障縮小為 **特定 venv Python 在此 launchd 執行脈絡下的
入口前卡住**，不能獨立證明 TCC、哪個檔案被拒、或產品本身有錯。
`/usr/bin/python3` 成功也不表示它具備產品依賴。產品 readiness
仍未通過；五輪 JSON／gold 尚未 freeze、尚未輸入 Safari。
