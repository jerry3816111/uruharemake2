# P4 本地時間／位置 User 來源授權：fresh Safari 產品探針

日期：2026-10-19。判定：**整批 strict FAIL**。這是依事前凍結的 11 句開發者 fresh probe 一次性執行，不是正式 temporal holdout、同模型對照或人評；不重送題句、改 gold 或以局部成功翻成產品通過。事前計畫與條件 gold 在 `research/p4_local_time_place_answer_authority_plan_2026-10-19.md`、`datasets/p4_local_time_place_answer_authority_fresh_probe_2026-10-19.json`；程式首輪前 SHA 在 `research/p4_local_time_place_answer_authority_product_freeze_2026-10-19.sha256`。前批 reference-probe strict FAIL 仍維持原判。

## 一次性執行與原件

- 產品程式：commit `5b1437afedadded478a20dbc50fa3cd5aff8f148`，既有 PR #435；首輪前 12/12 聚焦、118/118 受影響相鄰零模型測試，preimplementation SHA 2/2、product SHA 13/13。這些只屬程式證據。
- 全新 launcher-owned 0700 隔離 root：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-8yn4hr9p`。0-turn run `91be1e6c7d690bf6` PID 58653、A run `76f107ad3c4e30cf` PID 59207、同一 DB 真重啟的 B run `c2fd9328b5ae6a60` PID 59992；三者均有 same-PID HTTP ready 與 planned-stop receipt，最終原 PID 已退出、7894 無 listener。官方 SHA-256 `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3` 的 ONNX host cache 私有副本在離線禁止下載的 fresh interpreter 產生 1×384 finite embedding。T0 顯式空 profile 初始化。
- 真 Safari 新分頁，A session `20261019_064639_c16d7102`、B session `20261019_065106_ac4bac47`，共 11 句各一次、0 retry；A4 後 planned stop，同 DB 新 PID/session。只新增測試分頁，既有 Safari 分頁未關。逐輪觀察使用者可見泡泡及 node graph；每輪 raw 位於 root 的 `web_logs/conversation.jsonl`，11 行 SHA-256 `5b6543bad332c8a28abb82ad2f0d00732a7d7d1beec4bd5ab853c90b893c0b5d`。本次沒有另存 Safari 截圖，因此泡泡觀察是操作者核對，raw/graph 一致性可由 JSONL 重算。
- 原始 dirty checkout、正式長期記憶 DB 及無關 `output/graduate_application_report/` 未動；隔離 root 保留供查核，未外部部署。

## 十一輪可見結果

| ID | 問句／來源動作 | Safari 最終回覆 | User 等待秒 | 來源／路由觀察 |
| --- | --- | --- | ---: | --- |
| A1 | `舞台稽古は何時から始まる？` | `舞台稽古が何時からか、今の会話だけじゃ分からないな。` | 11.5938 | 無准入 User 來源，不編時間 |
| A2 | `展示ガイドは14時から始まる。` | `展示ガイドは14時から始まるんだね。` | 14.2247 | 保留直接 User 陳述 |
| A3 | `展示ガイドは何時から始まる？` | `展示ガイドは14時から始まるって言ってたな。` | 13.4471 | `recent_turns` 的原 User 值 `14時` |
| A4 | `友達が『予備マイクは北の棚にあるかも』って言った。` | `友達が予備マイクが北の棚にあるかもしれないと言ったんだね。` | 10.8347 | 保留第三者／推測歸屬；雙 `が` 使日文生硬 |
| B1 | `展示ガイドは何時からだった？` | `展示ガイドは14時から始まるって言ってたな。` | 9.8185 | 真重啟後 `direct_episode` 原 User 值 `14時` |
| B2 | `予備マイクの置き場、どこ？` | `予備マイクの置き場は、今の会話だけじゃ分からないな。` | 10.5138 | 不把 A4 的朋友猜測升格成確定位置 |
| B3 | `折りたたみ椅子は西の倉庫に置いた。` | `折りたたみ椅子を西の倉庫に置いたんだね。` | 10.4596 | 保留直接 User 陳述 |
| B4 | `折りたたみ椅子はどこに置いた？` | `折りたたみ椅子は西の倉庫に置いたって言ってたな。` | 11.2541 | `recent_turns` 的原 User 值 `西の倉庫` |
| B5 | `予備マイクはどこに置くのがいい？` | `予備マイクは適当な場所に。` | 11.2060 | 新 fact gate 未越權，但舊 `chat` planner 沒給可用建議 |
| B6 | `その歌詞、何の曲？` | `断片だけ投げるなって。元ネタあるならそこまで言えよ。` | 3.7975 | 真 `reference_probe` 路由保留、未編曲名；憑空責備「丟片段」 |
| B7 | `Shut up, your answer is useless.` | `はいはい、汚い方に逃げるな。言いたいことだけ言え。` | 10.9033 | `abuse_pushback`／protected low road 保留；口吻仍刺耳 |

新 gate 的五個適用問句：A1/B2 無來源 **2/2** 不編值；A3/B1/B4 直接 User 值 **3/3** 答對且留下真 trace ID。A3 `derived:recent_turn:3b6238a1be4bcc6b15b2`，B1 `stored:episode:e3ca2246-f1ed-4ce0-a400-1016dec29aae`，B4 `derived:recent_turn:3b5984a42377358b8faf`；三者最後可見句都與授權收據相符。A4 沒把朋友的「かも」寫成自己確定放置。B5/B6/B7 的**結構性不越權／原路由**均成立，但不能因此宣稱互動品質通過。

11/11 raw `assistant_reply`＝`visible_language_guard.final_reply`＝runtime graph `utterance.payload.reply`；Safari 泡泡逐輪肉眼觀察同字。11/11 user wait ≤20 秒，平均 **10.7321 秒**、最小 **3.7975**、最大 **14.2247**。新 gate 記錄增加模型呼叫 **0**；舊計算並未省掉：可觀測 M21 full-planner model-call completed **6 輪**，M31 semantic verifier completed **4 輪**（不可把兩者簡單加成整個 runtime 的總呼叫數）。完整 token ledger 未在本批 raw 提供，因此不報總 token 或費用。

## 為何仍是 strict FAIL

1. **預定逐輪記憶收據缺 T1**：當時已由 Safari 送出 A2，才發現 A1 後沒有保存 `profile-full-T1.json`／`snapshot-T1.json`。現存 T0、T2–T11 的 full-profile 均 0 rows、同 SHA `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`；T2 顯示兩個 episode，T11 顯示十一個不同 episode。但 T2 不能倒推成當時 T1 的逐輪收據，**T0–T11 每點 gate 未證實**，不得補貼標籤。
2. **B5 行動忠實度失敗**：問題是詢問應放何處，`適当な場所に` 只是空泛殘句，既無位置原則也無低壓詢問條件。新來源閘正確不介入；M21 完成舊 full-planner 後，被選 `core_message_jp` 在表面化前已是這句，M45 記 `non_help_or_protected_current_act`。斷點在原 `chat` planner／建議行為辨認，不能誤記為新來源閘失效。
3. **B6 參照回覆捏了互動前提**：使用者沒有提供歌詞片段，`断片だけ投げるな` 卻說對方丟了片段。路由正確、未編曲名，但可見回覆沒有忠實指出資訊不足，且帶責備。這句與 B7 保護路由的刺耳措辭來自既有固定 realization，不足以指控本次來源閘造成回歸。A4 雙 `が` 另是日文自然度風險；缺獨立母語／真人品質驗收，不報 11/11 自然日文 PASS。

這些是**產品層失敗與可歸因局部成功同時存在**，不證明優於強 LLM，也不外推成廣域來源判別、理解人心或 persona 品質。後續不得重播這 11 句追分。下一個工作項先只讀審查 B5 `chat`/M45 的可執行建議斷點，選單一變因並凍結新的未曝光正負控／成本／圖／Safari gate；B6 的無證據責備與 A4 語面分開處理。測試收據流程須新增逐輪完成檢查，防止 T1 類漏存，但不能改寫本批判定。若新批仍失敗，按工作規則保留失敗與 `REVIEW_REQUIRED`。正式同模型強 LLM、真人、temporal holdout、VRM／Function Calling 仍 pending；Goal active。
