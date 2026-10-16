# P4 exec-context detached lifecycle：零產品可行性證據

日期：2026-10-17（Asia/Taipei）。本項只診斷前一個 launchd 0-turn
產品程序未進入 Python 程式、Python-only launchd 探針亦未印出 marker 的
程序環境問題。使用 `p4_exec_detached_lifecycle_probe.py`；未啟動產品／模型，
未開 Safari，未送任何前瞻題，正式 DB 與原始 dirty checkout 未碰。

## 凍結前的有限實測

以 `.venv/product_checks/bin/python` 呼叫 `start/status/stop`，每個
`status`／`stop` 都是與 `start` 不同的 `exec_command` 呼叫。
`/bin/sleep 30` 最終 run root 是
`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-qsofps35`，
PID `32263`，UID `501`，`lstart` `Sat Oct 17 02:05:46 2026`；
後一呼叫 `same_process_alive=true`、`identity_mismatch=false`、
port `7894` vacant。stop 先重新比對 PID／UID／lstart／完整 command／PGID，
僅向該新 session 送 TERM；結果 `signalled=true`、
`original_pid_exited=true`、`port_vacant=true`。另有前一個 90 秒
sleep roots `uruha-product-2zpyzazr`、`uruha-product-1v0zgqlm`，
同樣跨呼叫存活與精確退出。

接著以 launchd controller 相同的 `_isolated_env`（沒有探針額外
env key）、`write_sandbox_profile`、`sandbox_command`、
`/usr/bin/perl -e 'alarm(20); exec @ARGV'` 包住**同一個**
`.venv/product_checks/bin/python -c 'print("python-ready", flush=True)'`。
最終新 root `uruha-product-uxr46dnc`，PID `32063`；下一個呼叫
`stdout` 精確 `python-ready\n`、stderr 空、PID 已退出、port vacant；
stop 沒有對任何 PID 送訊號，保存 `stop.json`。先前新 root
`uruha-product-jbp0bptq` 在移除多餘 env key 後也得到同一 marker。
這與 launchd Python-only 同 profile/env 的 marker 缺失形成有限
process-context 差異證據；不能由此推出 TCC 或 OS 權限為因。

所有最終 root、manifest、兩個 log、metadata 與 stop evidence 均留在
獨立 temp root；root `0700`，metadata/stop `0600`。程式
`py_compile` 通過，合成身分 guard 四個判斷 `4/4`；停止只對同 PID、
UID、start、command、PGID 的目前程序動作，身分不合則 fail closed。
此證據只跨**這幾個 exec 呼叫**，不證明跨 Codex host 重啟或長時間穩定。

## 明確限制與下一步

- Python 探針執行很短；detached 的 exit code 在之後的呼叫不能由
  `waitpid` 可靠取得，因此記 `unavailable_after_detach`，不宣稱
  exit 0。marker 與 PID 消失證明程式執行到 `print`，不是完整服務成功。
- `/bin/sleep` 證明純程序可跨此處的獨立命令呼叫，不證明產品模型、
  HTTP listener、Safari、記憶或成本。port vacant 是當時觀察，
  不是持續保留的端口鎖。
- 下一個 product 0-turn gate 應用新 private root、先確認產品程序
  持續存在、實際 PID/UID/start/command 和 `127.0.0.1:port` listener
  歸屬、HTTP 200，再精確停止並確認 PID/port；失敗即保留，不能
  凍結／曝光尚未使用的五輪 gold 來追分。
- 這份探針目前**只具診斷用途**，沒有整合成產品 lifecycle，也沒有
  做真模型或 Safari。若要用於產品，還需處理快速啟動後命令 exec
  身分轉換、子程序退出碼持久記錄與 host 中斷的清理策略；不能把
  零產品可行性直接升級成產品 PASS。
