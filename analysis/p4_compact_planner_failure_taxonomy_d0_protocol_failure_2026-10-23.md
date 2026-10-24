# P4 compact planner 失敗分類：d0 真 Safari 診斷未通過送出前 gate

日期：2026-10-23。這是 `research/p4_compact_planner_failure_taxonomy_plan_2026-10-23.md` 的一次作者開發題診斷，不是 formal holdout、同模型 certificate 比較或品質改善證明。既有 c0 control 的 `unexpected fields` 原始 JSON 未保存，仍不能分辨缺欄、多欄或兩者；c 批 strict FAIL 不變，不重送舊題。

## 事前改動與契約證據

`df50fa0` 先提交單一變因設計、source-only d0 題及 preimplementation SHA；`e61495b` 再提交 raw-free 固定分類碼與 bounded 欄位計數、聚焦測試及 product SHA。此改動只診斷 compact planner 的拒絕原因；原三候選嚴格驗證、模型／prompt／carrier／256 token、20 秒、無重試或自動修補皆維持。改動前聚焦 11/11；改動後聚焦 14/14、受影響合併 83/83，compile、`git diff --check`、13/13 product SHA 通過。這些只是 zero-model／程式契約，不代表 Safari 曾觸發新診斷。

## d0 的實際時間線與硬判定

全新 launcher-owned 0700 私有 root `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-s_6vrisa`、7924、run `ae226e30d62e4c30`、PID `51965`、Safari session `20261023_214043_e75e1e19`。ready 時同 final PID，官方 ONNX 私有離線預熱有限 384 維；Web 在新 Safari tab 顯示空對話／圖。沒有操作 Reset。正式 DB、原始 dirty checkout 與無關 output 未使用。

21:41:48 CST 保存的獨立 Tpre receipt 是同 PID/session、`memory_db`、reset0、finish0，**但 `autonomous_tick_index=1`；凍結要求 tick0**。依現場操作順序，我先複製收據、後按 Safari Send；沒有獨立可落盤的 Send-click 時戳，不能只憑 receipt 和 JSONL 完成時間證明精確間隔。我在 Send 前沒有先讀取並斷言已複製的收據，仍把 d0 按送出一次。這是執行程序錯誤；無論間隔多短，預送 gate 已 strict FAIL。不能把那一輪追認為合格診斷，也不重送相同 d0。21:43:17 CST 才另存的 late-post 為同 PID/session、`memory_db`、reset0、tick3、finish1；它不是及時取得的 tick0 Tpost，不能替代缺失的合格 Tpost。

已送出的 off-gate 輪可見 User：「朝の作業で図面を一枚整理できた。今は長い話じゃなく、ひと言だけねぎらってほしい。」Safari 泡泡／私有 JSONL `assistant_reply`：「寝てないのか、考え事で止まんないのか、まずそこだけどっち？」；自然日文，但沒有交付明示的簡短労い，還提出來源未支持的睡眠／煩惱二選一。這是可見品質失敗，不推論背景 tick 造成此句。

本輪 trace 是 `high_road_m18_fast_path`，M21 `completed_without_general_model`、`model_call_attempted=false`；M25 明示期待 `detected=false`，M29 `not_candidate`，handoff `not_admitted`。沒有 compact planner 節點、候選或 failure code。turn-scoped compute receipt 為 0 generation／0 provider tokens、11 vector operations，user wait 2.8422 秒；「0」不涵蓋 startup/background。故 d0 **既未重現也未檢驗** compact format 失敗類別，更不能據此說新分類器在產品通過或不通過。圖的關鍵路由與最後 utterance 曾在原生 Safari AX 現場核對，但無可重核 native PNG/AX 檔，saved-visual gate 仍未達。

私有原件 SHA-256：Tpre `c7c0e6680886dfd861ef4b81a4d0f86573616ae49150b5248b72ee7661c91a06`；late-post `f80f94cbb7581e36196682574f0df9089c79301b970a3d905c2c8080996937bb`；一行 JSONL `000900cf931c45ec128d2c85d0968c962f28aa4db9a0646d1ff2364b7f272c95`；ready `13f4f7e57ee2418942c49c0f7e287b30ba13ed53dee63ce9be108a6eb61c4858`。僅此新 Safari 分頁 53→52 已關；controller 對 exact PID planned stop 回傳 `original_pid_exited=true`、`port_vacant=true`，額外 `lsof` 查 7924 無 listener。隔離 DB 的一筆 episodic add 只在此私有 root，不是正式長期記憶。

## 下一步，不能混作既有結果

先把「複製 Tpre → **立即解析/assert** PID/session/`memory_db`/reset0/tick0/finish0 → 才准 UI Send」設為不可跳過的測試程序；檢查等待或頁面操作期間的背景 tick 邊界。再用零模型路由前檢、事前凍結的 **新 source-disjoint** probe 確認真會到 full/compact planner，否則新的格式診斷題沒有識別力。兩項需分別設計審查／驗收；不可修改 d0 或 c 題後重播、降低 gate、將 83/83 契約測試包裝為真產品成功。若無法得到合格 pre/post 與實際 planner call，保持 `REVIEW_REQUIRED`，不做 certificate 結論。正式人評、temporal holdout、強 LLM 全系統比較、VRM/Function Calling 統一驗收及整體 Goal 仍 pending。
