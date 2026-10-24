# P4 明示引述改寫：fresh Safari 產品探針結果

日期：2026-10-20。**整批 strict FAIL**。這是開發者事前寫定、實作前凍結的八輪產品探針，不是正式 holdout、人評或同模型強 LLM 比較。前批 repair-cue 六輪的失敗不改判、不重播。本批資料與判準見 `research/p4_explicit_rewrite_action_plan_2026-10-20.md`、`datasets/p4_explicit_rewrite_action_fresh_probe_2026-10-20.json`；preimplementation SHA 2/2、首輪前 product SHA 6/6，結束後重核仍全符。程式／受影響零模型測試 135/135 與本批產品結果屬不同證據層，不能互代。

## 隔離與原件

- 全新 launcher-owned 0700 root：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-qcphly1z`。0-turn 首個 PID 34434 same-PID ready、planned stop；官方 SHA 的 Chroma ONNX 檔在私有 root 離線預熱；T0 episode 0、profile 0。產品 PID 35013、run `928af172a1b6c190`、Safari session `20261020_085958_00abfc97`。八句在同一新 Safari 分頁各送一次，0 retry、無題目或 gold 事後修改。產品 PID 已 planned stop、7894 無 listener。
- 原始 `web_logs/conversation.jsonl` 八行 SHA-256：`1c45c0bfeead0799849eb77017149e37488f8103f54e1ed7f72d8872d87642ad`。T0–T8 的 `evidence/snapshot-T*.json` 與 `profile-full-T*.json` 每輪後、下輪前存；episode 0→8、八個不同 ID，profile row 全程 0，完整 profile digest 全程 `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`。正式 DB 未作此測試的目標或輸入。
- Safari 目視核每輪 user 泡泡、bot 泡泡及當輪 node graph；T1–T3 的新 `explicit_rewrite_action_p4` 節點可展開，T4–T8 不出現該節點但有 `UTTERANCE`。raw 最後回覆與 graph `UTTERANCE` **8/8** 相等；raw 與最後 `visible_language_guard.final_reply` **7/8** 相等，T3 在 guard 後被 P4-W 改寫。獨立 Safari stopwatch 未量，以下等待數字是 runtime proxy。

## 逐輪可見結果與因果斷點

| 輪 | 凍結輸入摘要 | Safari 最後回覆 | 新 action / 判斷 | user wait proxy |
|---|---|---|---|---:|
| T1 | 柔化「かしこまりました」 | `ん、そこもう少しだけ聞かせて。` | eligible；一次模型候選因 `formal_register` 拒絕，原路徑又被 M39 變成泛問；**沒有交付改寫** | 18.8992s |
| T2 | 英文要求柔和改寫 “I understand” | `分かったよ、うん` | eligible；候選同因 `formal_register` 拒絕，原路徑恰好給出可讀的口語答句；**不能算 typed action 已交付** | 16.5594s |
| T3 | 中文要求委婉改寫「我現在去不了」 | `「うちは今行けない」っていう記載なんだね。` | 局部形狀檢查漏過候選 `「私は今行けません」がいいかな。` 中的敬體 `ません`；`RightBrain.speak` 已未保住完整候選，其後 P4-W `quote_embedding_restore` 又將引述當成被陳述文字。最後 `downstream_surface_mismatch`、guard≠final；即使下游保留，也不能證明符合凍結語氣 gold | 10.5366s |
| T4 | 問「言い換えて」詞義 | `言い換えるとは、別の言葉で言うこと` | 新路徑未啟動；詞義回答符合負控 | 18.6271s |
| T5 | `了解、助かったよ。` | `分かったよ、ありがとう` | 新路徑未啟動；普通對話負控 | 17.1123s |
| T6 | 朋友說過「かしこまりました」 | `ん、そこもう少しだけ聞かせて。` | 新路徑未啟動，沒有把轉述當改寫指令；一般對話品質仍普通 | 10.8873s |
| T7 | 紙上登入密碼放哪裡 | `なくすのは困るよな。人目につく所に置きっぱなしにせず、他人に見られない形で管理しとけ。` | 新路徑未啟動；未肯定具體擺放地點 | 11.3535s |
| T8 | 問「あなたの名前は一ノ瀬うるは？」 | `は？そういうのうちに求めないで。` | 新路徑未啟動，**身份負控失敗**：selected/core 原為 `うるはだよ`，可見輸出轉成拒絕且 M39 接受；這是另一路徑的 selected→surface 失真，不能歸功或歸咎新改寫 action | 11.1942s |

新路徑在三個正例 **3/3 辨識、3/3 各一次新增模型呼叫，但 0/3 經證明完成「候選→最終可見改寫行動」**；T2 的字面答句或許能被讀成口語改寫，但其 receipt 明確記錄候選被拒與原路徑回覆，不能用巧合填新 action 的交付門檻。負控 T4–T8 **0/5 誤啟動**；T8 自身身份品質失敗。八輪皆為日文且 runtime wait proxy **8/8 ≤20s**；平均 14.3962s、最大 18.8992s。新 action 總共 **3 次完成呼叫、359 prompt + 36 completion tokens、實測新增 call latency 合計 4.539817s**；這不是完整 runtime token 成本，也不是 baseline-matched comparison。

## 可主張與下一步

可主張的只有：明示引述的當輪範圍檢查與正負控分流在此八句可觀察，新增候選的失敗有記錄，T3 的下游覆寫可由圖／digest 查出，記憶隔離與本機可見等同性依上列範圍成立。**不能主張改寫功能成功、較強 LLM 更好、身份穩定、產品正式可交付或已證明人類理解。** 這批不是固定題的修分素材；不可重送本八句或變更 gold。

下一個必要設計審查先分開三個斷點：候選生成／敬體檢查不足（T1–T3，T3 漏過 `ません`）、已選 typed action 在 speech／P4-W 被當轉述（T3）、既有身份 core 在 speech／self-monitor 與 M39 接受之間失真（T8，精確首次斷點尚待核）。選一個對產品最重要、單一可歸因的修正，先定新的未曝光正負控、來源／可見行動／安全／身份／圖／≤20s／成本門檻，再至多一個有根據的修正批次；仍失敗則 `REVIEW_REQUIRED`。正式同模型 baseline、temporal holdout、人評、VRM／Function Calling 統一驗收依舊 pending。
