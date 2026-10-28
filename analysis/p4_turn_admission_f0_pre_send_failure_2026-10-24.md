# P4 admission f0：隔離 Safari 送出前嚴格失敗

狀態：**strict FAIL，0 次 f0 Send，0 次 f0 使用者輪真模型生成**。這是作者開發診斷，不是 holdout、真人偏好、同模型比較或產品回覆品質通過。事前計畫、題本與接線分別已由 `93f4963`、`12e698e` 推至既有 PR #435；本報告不改事前門檻，也不重用此題追分。

## 凍結條件與實際先後

凍結 gate 見 `research/p4_turn_admission_fresh_single_probe_plan_2026-10-24.md`，收據欄位名稱的事前更正見 `research/p4_turn_admission_fresh_single_probe_schema_amendment1_2026-10-24.md`。唯一使用者輸入 f0 是「長い小説を最後まで読み切れた。今は一言だけ励まして。」；正式 Send 前必須同 PID／session／reset0／active DB、`autonomous_tick_index=0`、`human_submission_finish_count=0`、空 user episode/profile，且 journal 第一筆是該 user arrival；背景 tick/start/end 不可混入。不能改用 tick1＋writes0 替代。

1. 新 0700 私有 root：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-phl30iyr`。port 7927 原先無 listener；本地模型 tag `qwen2.5:7b` digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`。官方 ONNX 封存私有副本 SHA-256 `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3`，封網預熱得到 384 維有限 embedding、0 network attempts。
2. 同 root 先做**無 journal、無對話**的零輪 rehearsal：run `402cf079535428bc`，PID 90796 最終 same-PID HTTP ready；首次 `verify-ready` 遇到暫時的 `product_listener_not_same_pid`，不重啟，複查同一 PID 後通過。planned stop 後 PID 離開、port vacant；五個 Chroma collection 的 embeddings 均 0。
3. opt-in 真產品啟動：run `e0402fd65f821488`，PID 91163，session `20261024_021521_f68ef1bf`，reset0，`memory_db` 在此私有 root。首次 ready check 也遇到短暫 listener 競態，複查同一 PID/HTTP 後通過。Safari 原 52 tabs，本次只新開 1 tab，載入 `127.0.0.1:7927`，確認新 session，僅在輸入框預填 f0。**沒有點 Send。**
4. 送出前獨立讀 `active_db_receipt.json`：同 PID 91163／session／DB、`brain_status=ready`、reset0、finish0，但 `autonomous_tick_index=1`。同時 journal 已存在且第一筆是 `background_start`，不是 user `arrival`。兩個硬 gate 在 Send 前即 FAIL，因此立即停止，不以任何新時序假設放行。尚未取得計畫要求的 ready/T0 與 Tpre DB regular-file tree 雙 SHA；此 gate 是 `unknown`，不能補做倒填。
5. 使用既有控制器對 exact run/PID planned stop：PID 91163 exited，7927 全 owner TCP listener vacant。Safari 先在網址列核對當前分頁為 `127.0.0.1:7927`，只關本次新分頁；標籤數回 52，原本的 7894 分頁仍在，未操作它。私有 root 保留原件，不刪除或清空 journal。

## 原件與能成立的觀察

私有 `turn_admission_journal.jsonl` 是 0600、15,455 bytes，SHA-256 `4a40530dc35f50e9178af942306a0de796839546cc63d2fd1dd1bc15c8b989bd`；14 筆、同 PID/session/reset0、全部 `contains_raw_dialogue=false`，由 7 組 background_start/end 組成，**0 個 human submission ID／arrival／terminal**。第 10、14 筆各完成一次 `passive_decay`，tick 分別 1、2；兩輪各 5 次 Chroma read（get 2/query 3）、0 add/update/upsert/delete 返回或錯誤、0 文字生成 token，`ledger_coverage_complete=true`，但 `memory_diff_nonempty=true`，表示已觀察到 in-memory 狀態變動。其餘五組 `idle_noop`。journal 的 scope 只涵蓋既有受控內存狀態及包裝的 Chroma 方法，不是所有持久 writer 的普遍無寫入證明。

停止後收據仍為同 PID/session/reset0/finish0，tick2；其 SHA-256 `0cab3c5da1722092595a4d0f725edf079d367cfd620b02015cdd7a7ec24b59ab`。停止後以 read-only SQLite 檢查五個 Chroma collection：`episodic_memory`、`knowledge_base`、`procedural_memory`、`user_profile`、`wisdom_semantic` 都是 0 embeddings，queue 0 rows，`integrity_check=ok`；`web_logs` 無檔。這只證實這個隔離 root 沒有使用者輪的落盤跡象，**不證明** ready/T0 到 Tpre 的 DB byte equality，因為未保存兩時點的 tree manifest。私有 SQLite SHA-256 `6e5a0424c32e0c6f43eeff0ba418bc8f4313269c29b8a28651e64db3d571d231`。exact stop receipt SHA-256 `586fcbb64fbcea7eb6d7863bb7f41440958e10e932fbce9e4659b0b396fb7ecc`。

## Gate 判定與因果界線

| 項目 | 判定 | 證據或限制 |
| --- | --- | --- |
| opt-in child journal 實際接線 | PASS（窄義） | 真產品 PID 91163 寫入同 root 的 0600 raw-free journal；預設未啟用的零輪 rehearsal 無 journal。 |
| Tpre tick0 與 journal 第一筆 user arrival | **FAIL** | Tpre tick1；第一筆為 background_start；稍後 tick2。 |
| 同 PID/session/reset0/DB、finish0 | PASS（Tpre） | 收據同一 root/session，尚未有 user finish。 |
| ready/T0→Tpre DB byte tree 相等 | unknown | 缺事前雙 SHA，不能事後補稱 PASS。 |
| f0 route／短自然日文／persona／句末標點／guard／bubble＝raw＝graph＝episode | 未執行 | 沒有按 Send、沒有 f0 model generation 或新輪 native graph。 |
| f0 成本／≤20 秒等待／完整 user ledger | 未執行 | 沒有 user turn；背景 ledger 的 0 生成 token 不代替它。 |
| 正式長期 DB、原始 dirty checkout | 未觸及 | 所有產品讀寫在隔離 root；工作樹外原 checkout 未碰。 |

這次失敗不是「模型答錯」，也不能說 scheduler 錯誤：現有背景循環如設計執行；問題是**預先凍結的 tick0 純淨 gate 與 Safari 準備時序不相容**，且記錄已顯示 in-memory state 變動。獨立只讀審查指出 Web 在 Brain ready 後約每 10 秒輪詢，admission mode 連尚未到 45 秒 idle 門檻的輪詢也先寫 `background_start/end (idle_noop)`；因此 journal 首筆 arrival 甚至可能比 tick0 更難達成。這是對本次 gate 可操作性的解釋，不是回溯放寬。下一步須先做獨立設計審查：要嘛設計可在首個 background tick 前可重現地完成 UI/Tpre/Send 的前瞻 protocol；要嘛以完整歸因和可反駁的非干擾判準另立**新**資料與門檻。不能回頭重送 f0、清 journal、事後把 tick1 改成合格，或把 source-only contracts 說成產品 PASS。正式 holdout、人評、同模型強 baseline、完整圖像與最終 Goal 繼續 pending。
