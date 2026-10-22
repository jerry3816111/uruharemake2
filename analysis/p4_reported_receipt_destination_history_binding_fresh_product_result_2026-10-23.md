# P4 接收地點角色：history 綁定修正後的 fresh Safari 收據

日期：2026-10-23。這是先前 r0 strict FAIL 後、事前凍結的新 h0–h3 **作者開發題**；不是重試 r0，不是正式 holdout／同模型對照／人評。事前設計見 `research/p4_reported_receipt_destination_history_binding_correction_design_2026-10-23.md`，題本見同日 `datasets/p4_reported_receipt_destination_history_binding_probe_2026-10-23.json`。零模型和程式先以 `19525af6bfc74e1505327453eb324b255be09429` 推 PR #435，產品 SHA 7/7 在真題後仍一致。先前 r0 的失敗判定不改。

## 產品邊界與原件

- 全新 0700 私有 root：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-guzeagin`。官方 ONNX archive 83,178,821 bytes，SHA-256 `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3`；私有複製 0600、不同 inode、離線封下載預熱得 384 維向量／0 下載。zero-turn run `f09cd4808677cecb` PID 33132，同 PID HTTP ready、T0 空 DB、exact planned stop；產品 run `b663d40ada24bddc` PID 33504，同 PID ready。兩次首個 ready 查詢有暫時性的「未同 PID／逾時」回應，之後只重查**原 PID**，沒有重啟或重送題。
- 原生 Safari 專用新分頁從原 52 個增加到 53 個；每題逐字送一次、0 retry，四題使用四個不同 session ID。這些 session **共用同一私有記憶 DB**，不能稱逐題記憶隔離。h1 已可見 h0 episode，h3 檢索並將 h0–h2 episode 傳進左腦；所以 4/4 不是四個獨立試驗，更不是 holdout。
- 私有 `web_logs/conversation.jsonl` **4 行、4,387,140 bytes**，SHA-256 `770b503ebb89c456cf4531f559e827b6c103f41a2356d57cef0dc08f6323843f`；原始日文和 trace 只保留在此私有 root，沒有複製入 Git。停止後 session DB `episodic_memory=4`，`user_profile=0`，其餘集合 0；memory DB 全集合 0。PID 33504 exact planned stop、7894 無 listener；只關本次 Safari 分頁，53→52。

## 四輪可見結果與來源角色

| 題 | Safari 最終日文回覆 | 新 adapter／來源角色 | 使用者等待 |
|---|---|---|---:|
| h0 正例 | `先輩は2103年2月17日に銀の懐中時計を受け取る場所を緑の温室の西通路に決めたらしいんだね。` | `accepted_verified`，接收目的地，日期附著未知；`changed=false` 但 short history 已同步、pre-episode verified | 15.6781 s |
| h1 決定地負控 | `先輩は2103年2月17日に緑の温室の西通路で銀の懐中時計を受け取る場所を決めたらしいんだね。` | `source_pattern_unavailable / abstain_unchanged`；保留「西通路で」的**決定地**，不改稱接收目的地 | 12.0318 s |
| h2 正例 | `いとこは2104年10月6日に磁器のランプを受け取る場所を琥珀色の書庫の奥窓に決めたらしいんだね。` | `accepted_verified`，接收目的地，日期附著未知；`changed=false` 但 short history 已同步、pre-episode verified | 11.5877 s |
| h3 引文負控 | `いとこは2104年10月6日に磁器のランプを受け取る場所を琥珀色の書庫の奥窓に決めたらしいと言っていたんだね。` | `source_pattern_unavailable / abstain_unchanged`；保留 `らしいと言っていた`，沒有把目的地變成無條件已確認事實 | 12.8299 s |

四輪 user bubble／最終 assistant bubble 曾在真正 Safari 顯示；raw `assistant_reply`、visible guard `final_reply`、blackboard `utterance`、各自 episode 的 User／Uruha 字串逐輪一致，profile 0。h0／h2 的 `receipt_destination_relation_p4` 是原生節點且訊號為「接收地點角色與來源一致；日期範圍未定」，負控訊號為「來源句型未確定，不改寫接收地點」；h3 原生圖有箭頭與可展開的棄權內容。raw 重建 h0／h2 的新關係節點位於 utterance 正前、主線相連（各 79 nodes、115／114 edges）；這是 raw 重建與原生 UI 觀察兩種不同證據，不能把前者冒充保存的 Safari 畫面。四輪 reload 後圖仍顯示該輪 utterance／關係節點；**聊天泡泡在 reload 後消失**，這是另外的產品限制，不宣稱聊天內容重載保留。

四輪等待均 ≤20 秒，平均 **13.031875 秒**、最大 **15.6781 秒**。adapter trace 的 `model_call_added=false` 只代表此 adapter 本身沒有加模型呼叫；**全管線 token／模型成本帳本不可得**，不可推成整輪 0 tokens。h3 雖保留轉述，`いとこは…決めたらしいと言っていた` 對誰作決定仍有輕微主語歧義；新 adapter 在不支援引文時並未驗證其開放語義忠實度。

## 判定與不能外推的部分

**窄義來源角色／guard／日文／history／episode／可見圖／延遲：h0–h3 4/4 在已觀察條件下通過。** 這顯示先前可重現的 `changed=false` 且 history stale 缺口，在全新兩個正例中沒有再擋住交付；它**不能**證明舊 r0 的唯一根因，也不能證明所有接收地點、引文或長對話語義都正確。

**完整產品／教師展示整批 strict FAIL。** 沒有保存 native Safari PNG／AX，故 saved-visual gate 為 **FAIL**；四題共用長期測試 DB 且有跨題檢索，較強的逐題記憶隔離條件不成立，不能計成四個獨立案例；full-cost gate **pending**，聊天泡泡重載不保留。這些缺口不改寫 4/4 的窄義觀察，但依凍結的嚴格判準不能將整項宣稱完整產品 PASS。舊 f2／c0／c1、r0、正式同模型強 LLM、人評、temporal holdout、VRM/Function Calling 一體化均未被本批取代或放行。長期 Goal 保持 active。

後續若要提高證據層級，先凍結新的 source-disjoint 題與**逐題獨立記憶 root**、可持久 native 視覺收據和全管線成本採集辦法，再做前瞻測試；h0–h3 不重播追分。這屬驗收方法／產品交付的設計項，不能用補寫當前報告或改弱舊 gate 取得 PASS。
