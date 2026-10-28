# P4 f7c 真產品入場：Brain prewarm fail-closed（2026-10-24）

結論：**pre-Send strict FAIL；0 Safari Send、0 f7c fresh generation、0 可見回覆**。f7c 的事前題與 gold 沒有修改，也沒有把頁面 HTTP 200 誤當 Brain ready。這是隔離啟動協定失敗，不能判斷 f7 來源事件效用或日文品質。

## 凍結條件與已發生的操作

- 產品碼仍是已提交的 f7 opt-in utility；f7c source-only freeze 是 `b4238a1`。事前計畫指定 7936、正確 `.venv/product_checks/bin/python`、同一隔離 root 先零輪再正式啟動、正式最多 1 Send／0 retry。
- 啟動前 source SHA 3/3、f7 product SHA 10/10、`qwen2.5:7b` digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`、Python product import/callable、7936 vacant 均核過。新 controller-owned 0700 root 為私有 `uruha-product-t_zr7es7`；官方 ONNX 私有獨立副本 SHA `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3`，離線 warm 回傳 1×384 finite、0 下載。
- 零輪 run `1e69c79c31394488` / PID 71081 同 PID HTTP ready，Brain 載入並指向 root 下 `memory_db`；exact planned stop 後 PID exited、7936 vacant。此零輪在固定 `turn_admission_journal.jsonl` 留 `background_start`/`background_end` 兩行（sequence 1/2、同 PID/session `20261024_120657_56f265ad`、`idle_noop`、0 call/token/write、0 error）。
- 正式 run `d6976217729e29e1` / PID 71367 **重用同 root**，同 PID HTTP 200，但 stdout 為 `Brain prewarm failed: RuntimeError`；active receipt 是 `brain_status=not_started`、`active_db_status=unavailable`、`active_db_path=null`、reset0、finish0。T0 的 Brain/DB 入場 gate 未成立，故**沒有開 Safari、沒有預填或按 Send**。PID 71367 exact planned stop，PID exited、7936 vacant。

## 原因與已核的保護

`uruha_web_ui.py` 的 `RuntimeManager.__init__` 在新 process 看到非空 admission journal 就設 `_admission_audit_invalid=True`（約 802–806 行）；`get_brain()` 在建立 DB 以前執行 `_admission_preflight_before_db_effect()`（約 853、924–927 行），因此拒絕重用前一 process 的證據鏈。stdout 只印例外**類型**，沒有完整訊息；由舊 PID 的非空 journal、正式 start 的固定 journal path、receipt `not_started` 及這條控制流程，定位為 `turn_admission_db_preflight_unavailable`。這是有意 fail-closed，不應刪、清空或覆寫舊 journal 來追跑本題。獨立只讀複核同意此歸因。

焦點契約重跑：`.venv/product_checks/bin/python -m pytest -q test_p4_turn_admission_attribution.py::test_nonempty_journal_from_prior_process_cannot_be_reused test_p4_prepared_first_start_isolation.py` → **24 passed、9 既有 warnings**。這只證明保護與 prepared-root 契約，不是 Safari/模型能力證據。

## 私有原件與下一步

私有原件位於 root `uruha-product-t_zr7es7`，未複製 raw 對話到 repo。可核 SHA-256：`turn_admission_journal.jsonl` `57d8da8db91c3746b09ad491fafce1015fb9bc3f07743e19b9eecd37a72d8358`；正式 `active_db_receipt.json` `4865701aee610b6d607990c64af0ad846d983cd07bccfeb013998e99ba6119a2`；正式 `.ready.json` `1cb1c2cb9e29c7c473f7a71f2c86fd6acd23aff88f8bd0c0a9794219943bb63b`；正式 `.stdout.log` `fcd6e6bb76b0773c685ce7a8dca41883954edd3d9434e315fb32f6216db38b16`；正式 `.stop.json` `975561293705657a741585f57ef5aa58463398132a4b566882b5fcbb77cfdd37`。

下一個前瞻入場協定應將零輪與正式輪放在**兩個各自 prepare/cache/warm 的全新 0700 root**，都保留 admission journal；不再跨 process 重用非空 journal。現有 controller 支援，不需削弱 runtime guard。新 source-disjoint 題、gold、雙 root、port、成本/圖/可見門檻須在任何產品啟動前重新凍結。零輪 root 完成無使用者輸入的啟動／停止；正式 root **只啟動一次**，在同一正式 PID 核 HTTP、Brain、admission、T0 後直接走 Safari gate，不先停止再重用。任一 gate 失敗即停；所謂無輸入不等於零啟動成本。f7c 題不重送；正式 same-model 比較、人評、temporal holdout、完整 P4 仍 pending。
