# P4 B 真私有 zero-turn 首次執行：pre-Send FAIL

狀態：`fail_closed`。這是 2026-10-25 在已提交 `11d4b5373dd96f3a2fa6a8e1f7c9a3eae14243fc` 上的**第一次且唯一一次**真資源執行；沒有重送、沒有 Safari Send、沒有 B 題、沒有正式 DB 寫入。先前 fake-process 191/191 與 helper 22 個測試不能替代這次真結果。

## 原件與現場

- 0600 私有結果：`/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-p4-b-zero-568srdlo/p4_b_private_zero_turn_result.json`，SHA-256 `26db891e6f17cb44e727288399c3248b1badeeb08dedba24f9b7ab0862857291`。目錄保留，不在本項清除。
- 模型 root 為上述 `/var/.../uruha-p4-b-zero-568srdlo`；其 realpath 為 `/private/var/.../uruha-p4-b-zero-568srdlo`。prepared product root 是 `/private/var/.../uruha-product-td8ognnp`，one-use claim 已耗，不得重用。
- 真 daemon PID 74685、runner PID 74699；沒有產品 child PID、launch receipt 或 HTTP-ready。runner port 52621。執行後精確 `ps -p 74685,74699` 無列；`lsof` 的 11455、7894、52621 均無 listener，共用 11434 仍只有原 PID 1529。helper 自報 `runner_cleanup=terminated`、`daemon_cleanup=identity_drift_no_kill`、`cleanup_review_required=true`，所以**不能宣稱已按計畫精確停機**；只可說事後觀測 PID/port 已空且共用 listener 未改。

## 可歸因失敗

`_clone_private_model` 用 `Path(tempfile.mkdtemp(...))` 保存 macOS `/var` alias；現有 clone/probe 不要求 canonical root。`control.start` 已消耗 prepared one-use claim，接著 `_b_descriptor` 調用 `_exact_private_directory`，因 `path.resolve(strict=True) != path` 而拋出 `private_root_not_canonical_or_private`，包成 `p4_b_descriptor_unavailable_or_invalid`／`ControllerError`；因此產品 child 在任何 Popen 前被擋。這是 helper 與既有安全契約不一致，不是模型回答失敗。原 controller/binding 契約不應放寬。

## 成本與證據界線

| 項目 | 首次真執行觀察 |
|---|---:|
| 全程 wall | 23.8662 s |
| prepared cache/warm | 1.8735 s |
| clone＋SHA verified | 4.4261 s |
| runner loaded | 6.2841 s |
| descriptor ready | 11.0811 s |
| clone logical bytes | 4,683,088,190 B |
| warm 後 clone 前／後 free bytes | 124,368,752,640／124,366,659,584 B，差 2,093,056 B |
| helper model-store validations | 3 次，至少 14,049,264,570 B 邏輯讀 |
| operator diagnostics | 1 setup `/api/version`，另 1 render-only＋5 probe HTTP |
| user Send／intentional completion／formal DB writes | 0／0／0 |

`df` 差額不證 APFS CoW 內部物理配置。RSS 是採樣，不是峰值；因沒有 child，`resource_sampling_complete=false`、`full_cost_instrumented=false`。固定 render-only 回覆和私有 daemon 日誌可界定 helper 自身零生成意圖；`provider_network_completion_count_proven=false`、`global_provider_completion_count_proven=false`，不能稱全域零 completion。`brain_constructor_observed=false`、`sdk_models_list_observed=false`，本次沒有真 Web/Brain/SDK 路線。時間線也不是 Safari click→DOM 20 秒。

判定：此卡所要的「真 sandbox child 同 PID ready/stop」**FAIL / 未達**。保留舊 root 與失敗原件；下一步只能在前瞻單變因計畫和測試後，以全新的 private model root 與 prepared product root 做至多一次 zero-turn。B Send 維持常閉；作者 A 評分／真 A、B token 上界、M21 terminal、Safari 20 秒仍未獲授權或驗收。
