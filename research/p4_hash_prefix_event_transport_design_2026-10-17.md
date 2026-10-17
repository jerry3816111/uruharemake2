# P4 hash-prefix 事件傳遞：第二次前瞻前的單變因設計審查

狀態：2026-10-17，只讀、同團隊非獨立審查；尚未實作或送新題。原七輪 Safari strict FAIL、首輪前 gold/plan/code/freeze、原 raw 與更早六輪 FAIL 永不重評。這份只修正**下一批要量什麼、如何把真正已發生的事件帶到可見稽核**，不宣稱先前產品其實 PASS。

## Before 與真正缺口

七輪 raw SHA `77b0a8cc138b73176a4a1f47369442b5407d10ca88511da6f41d15d7552016b8`。T1/T4/T7 final＝selected reported-offer core，舊 source audit `visible_report_preserved`、新 audit `visible_core_exact`，但 `final_related_hash_additions_removed=[0,0,0]`；T3 語義錯讀、T0 absent→T1 present 使原批 strict FAIL。資料與限制見 `analysis/p4_hash_prefix_provenance_fresh_product_probe_result_2026-10-17.md`。

只讀定位：legacy `RightBrain._finalize_surface_reply` 在符合非 structured／非 memory／非 support 條件時，依 `intent|surface_act|user_input` 字元和加八選一固定開頭（`uruha_brain_mac.py:10694-10718`）；既有 P4 wrapper 若舊 finalizer 的結果逐字為 `prefix + sanitized original` 就回傳原候選，將無原文的 SHA 事件存進 `logic_data[_hash_prefix_provenance_events_p4]`（`uruha_hash_prefix_provenance_gate_p4.py:32-53`）。但 `RightBrain.speak` 在入口先 `dict(logic_data)`，只把列舉的別種 trace 鍵寫回原邏輯（`uruha_brain_mac.py:15460-15498`）；最終 audit 從原邏輯數事件（`uruha_hash_prefix_provenance_gate_p4.py:97-123`）。既有聚焦測試直接呼叫 finalizer，沒有覆蓋這個 copy boundary；既有 full-turn fixture 甚至事前斷言 0（`test_p4_hash_prefix_provenance_gate.py:53-83,160-180`）。因此 0 是**觀察不能區分未進函式與事件遺失**，不是功能必未執行的證據。

靜態對三個 reported 句的 legacy seed 依序指向 `てか、`／`一回、`／`まあ、`，core 長度 27/24/26、`max_chars=44`，raw M21 無 compact call，P2 surface wrapper 會委派 legacy；**若**進 finalizer 前的候選逐字等於 core，均有足夠加前綴的條件。尚缺交付候選的動態 witness，不從最後句倒推出中間事件。T3 則是另一處 `先に.{0,8}(?:聞いて|確認して)` 未區分使用者自己查行程與要求助手先提問（`uruha_adaptive_person_model.py:869-893`），不能在本項順手修。

## 單一核心變因與邊界

只新增**產品 opt-in 的 per-speak 事件傳遞**，讓舊 finalizer 已產生的 bounded SHA 事件跨 `speak` 的 shallow copy 到達原 `logic_data`，並且只讓 `speak` 實際回傳候選相符的事件參與既有 final audit。可使用進入 `speak` 前新建、由 shallow copy 共用的每輪私有 list，回傳時按 `returned_candidate_sha256 == SHA(speak_reply)` 篩選；上限沿用舊 16，無原文。只讀取／移交 provenance，不再次呼叫 legacy finalizer，不改 final 字串、selected plan、來源路由、M25/M18、模型／生成參數、記憶、語言 guard 或舊 P4 audit 的 frozen code。意外既存事件、非字串 reply、例外、不同候選、跨輪 stale event 都 fail closed／不報移除。新產品入口與 controller shim 安裝在既有 hash gate 之後，不動舊凍結入口。

允許新增：事件傳遞 overlay、新 opt-in 入口/controller、聚焦測試、隔離 profile 初始化工具與其測試（測量程序，不是第二個產品決策變因）、新未曝光資料/計畫/freeze、後續結果、`CURRENT_TASK.md`。禁止更改：`uruha_brain_mac.py`、`uruha_hash_prefix_provenance_gate_p4.py`、原七輪或更早六輪資料/判準/SHA/raw、正式 DB、原始 dirty checkout、無關 `output/graduate_application_report/`。若實作需要改上述禁止檔，先回設計審查，不偷改。

## 分層驗收與失敗分支

1. 零模型 focused：原 finalizer 產生 hash-added 候選、overlay 只回原候選；完整 `speak` 跨 shallow-copy 後原邏輯確有 bounded SHA 事件，事件與實際 `speak` reply／最終 graph reply 綁定。直接邀請、未知第三者、原有連接詞、不同候選、重複呼叫、例外及跨輪污染負控制不能捏造移除；原舊 freeze manifest 保持全 OK；相鄰產品回歸不退步。若一個開發 fixture 無可達事件，先保留失敗、只讀定位，不降斷言。
2. 隔離基線程序：**新** launcher-owned 0700 root 的 0-turn server ready/stop 後，顯式在同一已驗證私有 root 以相同 venv/sandbox 建立空 `user_profile` collection；這是揭露的測試 setup DB write，單列時間與磁碟成本，不算產品效益。setup 後與新 Safari T0 的 full-profile receipt 均須 `present/present/0/同一非 null digest`，每輪、restart 與 final stop 比全部四欄；episode ID 另計。不能把讀 Chroma 說成 SQLite byte-read-only；不能回補舊七輪的 absent T0。
3. 新資料須在**任何**新 Safari 首輪之前，由固定有限 reported-offer 句法與來源 hash 桶挑出至少一個候選正控制，列明預測的 legacy 前綴、selected/source 期待、直接邀請與未知負控制；先查 repository exact 重複，做 code/gold/plan SHA、Git commit/push/PR head 凍結。選例不能依已看到的 reply 或放寬舊標準。這是開發者前瞻案例，不是獨立 holdout。
4. 真 Safari 新隔離產品測試逐句一次、0 retry、每輪 ≤20s；核 browser 泡泡、selected/source、原舊稽核、傳遞事件／新 audit、graph UTTERANCE、episodes、完整 profile digest、model calls/tokens/延遲。至少一個**實際交付**的 reported reply 要有 `final_related_hash_additions_removed>0`，並且事件提供 pre-finalize/legacy/returned SHA、最終 exact core、完整 source admission proof；否則此有限機制仍 FAIL。direct/unknown 不應冒出 reported/prefix audit。應保留至少一次 same-DB planned restart、兩個 session，最終停機；UI 截圖/操作未保存時只能稱當輪觀察，raw 等式與真 bubble 不混稱可獨立重算。
5. 這批即使通過也只可說明**有限來源前綴的產品路徑與證據傳遞**；原七輪 strict FAIL、不解 T3 語義錯誤，不能稱整體 P4 完成、自然人格人評、fresh model generation、同模型優勢或人類反應方程式成立。T3 另立單一 actor/scope 准入工作項，之後才以新未曝光整體產品批次驗收。若本第二次前瞻仍不達，保存反例轉 `REVIEW_REQUIRED`，不再用第三批改題追分。

時間／資源上限：先精確 focused＋受影響相鄰測試，0-turn preflight 及新 Safari 一批；每輪 20 秒，0 retry，無外部部署、無正式 DB；記錄 ONNX 預熱、profile setup、啟動與每輪等待分開，不重跑已足夠且未受影響的長套件。未取得 human/holdout 不偽造。
