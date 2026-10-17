# P4 reported-offer source scope：全新六輪 Safari 產品驗收計畫

狀態：2026-10-17，六句／逐輪 gold **未送 Safari／模型前固定**。作者開發前瞻資料，不是獨立 holdout。上個 selected-offer 第二批的 T2/T3 strict FAIL 永久保留，這裡不重播、不改分；設計與單變因見 `research/p4_reported_offer_source_scope_design_2026-10-17.md`。

六輪逐字與 gold 見 `datasets/p4_reported_offer_source_scope_fresh_probe_2026-10-17.json`。建立當下對六句在 repo 做 exact `rg -F`，先前命中 0；新程式測試用不同輸入，不能把本 batch 用於修程式。T1/T3/T4 要把「第三者問使用者」與「使用者問 Uruha」分開；T2/T6 直接邀請不可退步；T5 保護既有第三者偏好未知路徑。任何新 node 缺席、錯標成功或泡泡仍直接接受引述，均 FAIL；只看「沒有新 audit」不構成負控制成功。

## 首輪前設施預檢與保留的失敗

第一次新 controller CLI 在送題／建 root 前因 wrapper 呼叫不存在的 `main()` 而失敗（`AttributeError`）；僅修新 controller 的轉接至底層 `main()` 並新增實際執行 `--help` 的回歸，不更動舊凍結 controller。第二次 0-turn start 建立 launcher-owned 0700 root `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-57nek51o`，run `62d994ce5575dbd5`、PID `52651`。`start` 回 `ready=false`；兩次 transient `verify-ready` 分別為 listener race／HTTP timeout，後續同 PID 核唯一 localhost listener、HTTP 200、`ready=true`，再 planned stop 核 PID exited／port vacant。這些 pre-ready transient 與初次 CLI 缺陷均保留，不作對話結果。停機前後 `memory_db`、`session_db`、`web_logs` 無檔。

本機原有 ONNX archive 83,178,821 bytes 的 SHA256 `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3` 等於安裝的 Chroma `_MODEL_SHA256`。已複製成上述新 root 內不同 inode／link count 1／0600 的私有資產；同 SHA。以該 root 的 HOME/TMPDIR 與 0-turn sandbox profile，在 `httpx.stream` 被設成任何下載立即報錯下，以 fresh Python 得 `offline_embedding_ready 1 384`，wall 約 0.91 秒。三個 DB/log 目錄仍空。這是獨立的資產／初始化成本，不是產品語義、Safari 或真人 PASS。

1. 首輪前完成新程式 focused／相鄰測試、compile、diff review；用 SHA manifest 固定新 dataset、本計畫、新 module／entry／controller／test、既有 frozen manifest 的 hash，commit/push 並核 PR #435 head。舊已凍結 8 檔不得修改。若不能凍結，真輪次不開始。
2. 建立**全新** launcher-owned 0700 隔離 root，正式／原始 dirty checkout 的 DB、session、cache、log 皆不使用。若為避免已觀察的 Chroma 首載 timeout，可在 0-turn、0 episode/profile 時從本機已存在的 SHA 符合 Chroma `_MODEL_SHA256` 的 ONNX archive **獨立複製**進此 root，離線驗證 embedding；資產容量、準備與啟動時間分開計。這不是任何對話 PASS，也不能消除前批 timeout FAIL。
3. 新 controller `p4_reported_offer_scope_detached_control.py` 啟 product，核同 PID、唯一 `127.0.0.1` listener、HTTP 200；失敗即記程序 FAIL 不送題。Safari **新分頁** T1–T3 逐字各送一次、0 retry，每輪最多等 20 秒。每輪保存泡泡、selected/core/source-scope/audit、graph utterance、profile row IDs **及 profile 全內容 hash**、episode IDs、memory write 類別、M19 等待與可得模型/token成本；一般語義失敗可繼續未曝光輪次，runtime/UI 錯誤停止本批。
4. T3 後 planned stop，核原 PID exited／port vacant；用同隔離 root/DB 重啟，核新 PID/HTTP 200，Safari 新 session 送 T4–T6 各一次。末尾 planned stop，root/raw 留存；舊 Safari 分頁不任意關閉。重啟前後 episode 需接續為 3→3→6，不能用兩個獨立資料庫冒充長期保存。
5. strict PASS 需 6/6 完成且 M19 等待 ≤20 秒、0 retry、兩 sessions／一次預定 same-DB restart、profile row-ID delta 全 0 **且 profile 全內容 hash 不變**、memory write 無第三者偏好 fact、六個不同 persisted episodes、六輪 Safari 泡泡＝graph utterance、六輪自然日文且來源與行動符合各輪事前 gold。三個純引述須 new scope certificate、selected `chat/plain_reply`、最後 graph audit `visible_report_preserved` 且泡泡不直接接受；兩個直接邀請須保留原 selected action／原 offer audit 並無新 scope node；T5 不得被新 gate 接管且不得編後輩偏好。任一缺失報 strict FAIL，保留原 raw 與被曝光題不重播追分。

此批最多能證明有限句型下的產品來源作用域與控制不退步；不證一般語用理解、人類被理解感、同模型 LLM 優勢、正式 temporal holdout 或完整 VRM/Function Calling 產品交付。若失敗，先依原始 trace 做單一因果定位，最多一個有理由的新前瞻修正批次；仍失敗列 REVIEW_REQUIRED，不降 gold 或擴大 claim。
