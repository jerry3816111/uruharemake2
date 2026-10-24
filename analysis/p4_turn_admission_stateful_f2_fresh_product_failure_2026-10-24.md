# P4 stateful f2：第一次隔離真 Safari，嚴格 FAIL

**結果：f2 產品輪次 strict FAIL；一次 Send、零重試。** 事前題本／判準在 `research/p4_turn_admission_stateful_f2_plan_2026-10-24.md`，source-only freeze commit `b8f9552`；零模型 route gate `5e8d780` 只證 Brain 內部路由，沒有替代本次 Web 驗收。f0 pre-Send FAIL 與 f1 原始 route FAIL 均不重判、不重送。

## 實際前送與執行

- 新 controller-owned 私有 root：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-gpqixkpx`，mode 0700；port 7929 起初空閒。官方 ONNX archive 83,178,821 bytes／SHA-256 `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3`，私有 0600 inode 49296648，與主機 inode 4160298 不同；Chroma 預熱為 1×384 finite、觀察到的下載入口 0 呼叫。這不是 OS 全面封網證明。本機 `qwen2.5:7b` tag digest 符合凍結值 `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`。
- zero-turn run `3bc74b4c1f237535`／PID 99627，同 PID HTTP ready，`memory_db` embeddings/queue 0/0、無 Web 對話檔，exact planned stop、原 PID 退出、7929 vacant。正式 run `5e4167d102aa018a`／PID 99951 用 control＋repair-cue＋journal 三個 opt-in；首次 verify-ready 暫遇 listener race，僅在同 PID 重查後 HTTP 200，未重啟。Safari 只新開一個分頁，原生 URL `127.0.0.1:7929`、session `20261024_025945_760d511d`。
- T0 regular-file DB tree 只有 `memory_db/chroma.sqlite3` 176,128 bytes／SHA-256 `91e5f950ad831065a9a55bac80676b2cf19eabe6bd33f28c2de614d7f33f575b`。Tpre 同一檔、同尺寸與 SHA，embeddings/queue 仍 0/0；無 symlink／取樣漂移；PID 99951、同 session／active `memory_db`／reset0／finish0／brain ready，當時 autonomous tick=3，明確是 **stateful pre-state，不是 pristine tick0**。journal 到 Tpre 為止 20 events＝10 組序號連續且完整的背景 start/end，ledger coverage complete、0 wrapped mutation returned/error、0 unknown worker；`passive_decay` 曾改 in-memory fingerprint，沒有改 DB tree。Tpre 結束 monotonic ns `1782020839115250`。T0/Tpre 逐檔讀取結果留在本次 Codex 工具輸出及本報告，**當時沒有另寫不可變的私有 snapshot 檔**；後設報告不是同等的獨立落盤證據，此保存 gate 另列缺證。
- Safari 預填原句後只按 Send 一次；click wall time `1792782095793` ms，距 Tpre 取樣結束約 4.20 秒。journal `arrival` sequence21 monotonic ns `1782025204354708`，距 Tpre 4.365 秒；Tpre→arrival 沒有背景 event。相同 opaque submission id `5bf9475fe39b177e92d946b10fb4e41e` 的 sequence22 為 `admission_snapshot ready`、tick3/DB 綁定一致；sequence23 **`terminal error`**，沒有 `cognition_start/end` 或 `delivered`。下一個背景 start 是 sequence24，已在 terminal 後。完整 journal 共 31 events＝14 組背景 pair＋3 個 human admission/error events，背景 mutation returned/error 仍 0。

## 失敗原因與未通過的 gate

Safari 原生畫面顯示使用者 f2 原句，但助手泡泡停在 `...`、Stage=`thinking`，並顯示錯誤；沒有可見日文、當輪 node graph 或 episode。正式 run stderr 的精確例外：

```text
TypeError: install_product_function_calling_p4.<locals>.wrapped() got an unexpected keyword argument 'admission_token'
```

`uruha_web_ui.py` 的 browser-bound submit 依 admission journal 新契約傳入 `admission_token`；外層 `uruha_product_tool_failure_truth_p4.py` 會透傳 `**kwargs`，但舊 `uruha_product_function_calling_p4.py` 的產品 wrapper 只列舊參數，因此在 `_run_turn` 進入真 cognition 前就拋錯。這是真實 Web wrapper 組合缺口；f2 假 LeftBrain 的 `run_turn_debug` 預檢沒有覆蓋這一層。無 user-turn provider generation、無可評日文品質，故不是「真模型回答錯」的證據。隔離 `web_logs`、`session_db` 停止後無檔；`memory_db` embeddings/queue 0/0。原件保留在上述 0700 root，journal 31 events／32,889 bytes／SHA-256 `4c6821712c8ec328726940b10f8a9ec543197a55198ddc30e59149a70e8c8bc1`，正式 stderr SHA-256 `2a4dca53f7e196419558286a516092e3c85993899b96905b434aaaba1dbdc6c3`。

正式 PID 99951 exact planned stop、原 PID 退出、7929 vacant；只關本次 Safari 新分頁，tab count 53→52，未關舊分頁。**f2 不重送、不改 gold**。下一項先前瞻凍結單一 wrapper-contract 變因及正負控，在零模型 Web 層讓新 admission token 經非 Function Calling route 傳到原 Web `_run_turn`，保持 Function Calling selected route/安全契約；另立新的 source-disjoint f3 才可做真產品。Web delivery 額外 Chroma 成本仍 unknown；正式同模型比較、人評、temporal holdout、VRM+Function Calling 統一驗收及完整 Goal 均 pending。
