# P4 direct-act → planner handoff：送出前 DB gate 失敗

日期：2026-10-23。此記錄保存一次已失敗的 frozen acceptance 嘗試，不修改或補跑 `b0–b6`。範圍是隔離產品／Safari 比較批次；不是模型品質評分。

## 事前契約與實際結果

- 事前 frozen plan：`research/p4_direct_reply_act_planner_handoff_plan_2026-10-23.md`；題目：`datasets/p4_direct_reply_act_planner_handoff_probe_2026-10-23.json`。Send 前必須同一 final Python PID ready、0700 root、官方 ONNX 私有離線預熱、active DB `memory_db`、`reset_generation=0`、`autonomous_tick_index=0`、`human_submission_finish_count=0`，且 T0 DB/profile 空。任何 reset／DB 漂移即 fail-closed，不能補送。
- 上一輪額度中斷留下的 `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-bvl6d631` 只見 prepared claim 和 `not_started` 收據、dead PID；沒有 controller current／ready／Web 回合。保留原件，不把它當此批成功或失敗輪次。
- 新隔離 root `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-6lp940ud` 已 prepared，官方 ONNX archive SHA-256 `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3` 私有離線預熱得 384 維 finite embedding、0 socket attempts。control product run `8de14b2d5bb67057` 同 final PID `16535` 的 HTTP ready 驗證通過。
- **Send 前 hard gate FAIL：**live `active_db_receipt.json` 在 PID `16535` 顯示 `active_db_path=.../session_db`、`reset_generation=66`、`autonomous_tick_index=0`、`human_submission_finish_count=0`、`brain_status=ready`。stdout 先初始化 `memory_db`，後重複初始化 `session_db`。兩個隔離 Chroma SQLite 的 `embeddings` 與 `embeddings_queue` 均 0；`web_logs/` 無回合檔案。未送出 b0 或任何 b 題，沒有模型回答、回覆成本或 paired product comparison。
- 控制器 `stop` 只對該 run 的 exact PID 發訊號，回報 `planned_stop=true`、原 PID exited、7894 無 TCP listener。原 root 未清除；正式 DB、原始 dirty checkout、無關 `output/graduate_application_report/` 均未動。

## 可歸因範圍

`uruha_web_ui.py` 中 `_reset_generation` 只在 `RuntimeManager.reset_brain_session()` 增加；該函式把 DB 切到 `URUHA_WEB_SESSION_DB_PATH`，Web 內的呼叫路徑是 `reset_session()` → `reset_session_browser_bound()` → `reset_btn.click`。`demo.load` 僅載入 graph，timer 僅 poll proactive。因而可確認 Reset callback 路徑被執行；目前沒有 callback request／client 審計，**不能認定誰按 Reset、哪一個 Safari 分頁、或舊分頁是否自動重送**。當時 Safari 有許多舊 `127.0.0.1:7894` 頁面，是待查可能性，不是證明。

只讀碼審查提出一個強但未實證的實際請求來源假說：66 次 reset 約每 2 秒一次，吻合舊頁的 2 秒 timer。零模型建構 `0942455^` 舊版／目前 HEAD 的真 `build_demo()` 事件圖，確定舊版 `poll_proactive_turn` timer `fn_index=33`、新版 `reset_session_browser_bound` `fn_index=33`，而新 timer 是 34。2026-10-21 `0942455` 在 Reset/Timer 前新增 `demo.load`，令事件 ID 錯位；本機 Gradio 6.6 的 `route_utils.get_fn` 對 request `fn_index` 直接取現行事件，即使舊 API 名稱不同，且多餘舊 timer input 不阻擋 reset。**事件碰撞機制已零模型證實，66 次請求實際來自哪個 client／分頁尚無網路鑑別**；不能把推論說成具名使用者操作。

本次 frozen 批次判定 **pre-send strict FAIL；0/9 arm-turns、0 可見答句、0 比較結論**。先前零模型 130/130 與 source-bound prompt delivery 的機制證據維持原範圍，不能外推為真產品成功。舊 a0 不同模型/設定比較 strict FAIL 亦不變。b0–b6 沒有模型輸出曝光，但此 acceptance 嘗試已消耗，不能更換 root 後悄悄聲稱同批 PASS。

## 可追溯私有原件

原件位於上述 0700 root；以下 SHA-256 對應停止後內容：

| 原件 | SHA-256 |
|---|---|
| `active_db_receipt.json` | `9094065ef27969d8693291774afae4241fb5456a75e3e99edeb162a8200b82eb` |
| `p4_preference_fallback_detached.8de14b2d5bb67057.ready.json` | `3bb12cd5ab593045a2069816024f1be9e6c470e53c59c100abe63440280314df` |
| `p4_preference_fallback_detached.8de14b2d5bb67057.stop.json` | `c087c2d64225f4a6b58b628cb6b150e895cb30f19f0f049c80dd62a86eabb314` |
| `p4_preference_fallback_detached.8de14b2d5bb67057.stdout.log` | `3baf9344de99cf6db899d40994c226173ba09b5afae5e5ae78a4d15932626a8b` |

## 下一個必要交付

先做**零模型、零正式 DB** 的 prospective reset attribution／隔離設計審查：僅記 reset callback 的請求來源或用未被舊分頁連接的產品埠，觀測一個完整 zero-turn ready 窗是否維持 reset0。兩者不能未經審查地混成同一變因。若確認與修好環境問題，新的 product comparison 仍需事前凍結 source-disjoint 題與相同載體、成本上限、嚴格 gate；不得重用這次失敗作 PASS，也不得重播舊 a0。真人感受、正式 temporal holdout、強 LLM 全系統比較及 VRM/Function Calling 統一驗收仍 pending；Goal active。
