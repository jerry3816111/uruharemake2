# P4 混合請求過去地點來源授權：fresh Safari 結果

2026-10-20。**整批 strict FAIL；新來源 gate 在四個目標混合輪次 0/4 取得表面權限。** 本批是實作前凍結的同團隊前瞻探針，不是獨立 holdout、正式同模型比較或人評。前批 A1–A7、所有舊 FAIL／`REVIEW_REQUIRED` 不改判、不重送。

## 前提與原件

- 計畫與 11 個零模型契約、七輪 W1–W7 在 `0e0fd0c` 先凍結；opt-in gate、測試、薄 Web 入口與 product SHA 在 `d61167f` 推既有 PR #435。聚焦 9/9、受影響相鄰 148/148；preimplementation SHA 2/2、首輪前 product SHA 10/10。這些只證程式契約與來源檔固定。
- 新 launcher-owned 0700 root：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-95lby3fk`。0-turn run `4e9615b59f48c3d7`／PID 93023 同 PID localhost HTTP ready 後 planned stop；未送訊息。官方 Chroma ONNX archive 83,178,821 bytes、SHA256 `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3` 複製為不同 inode、link count 1 的 0600 私有資產，封下載離線預熱得 1×384 embedding。六個解壓檔權限調為 0600 後，空 profile 專用程序只在此 root 預建 0-row `user_profile`；T0 episode 0、profile 0，digest `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`。預建 2.2911 秒是 setup，非產品輪次成本。
- 產品 run `8fd276d3efa5282b`／PID 94723 同 PID ready；只新增一個 Safari 分頁，session `20261020_162122_3b388563`。W1–W7 依凍結順序各送一次、0 retry；每輪在下一輪前目視 Safari 泡泡／runtime node graph，保存 `evidence/snapshot-T0,W1…W7.json` 與同標籤 `profile-full`。本次 Safari 畫面曾目視並由工具輸出截圖，但**沒有持久化獨立 screenshot 檔**，不得把 JSONL 稱作截圖。服務 planned stop 後 PID 退出、7894 vacant；只關本次新分頁，原 52 個分頁保留。
- 原始七行 `web_logs/conversation.jsonl` SHA256：`1c50246f25b048b582f2fc644df84a763b3923c612f5b045909a603af6fef9df`。七個不同 direct turn episode；T0–W7 full profile 均 0 rows／同 digest。正式 DB 未作 before/after hash，故只能說本次產品使用隔離路徑且未觀察到正式 profile 污染，不能宣稱形式化證明正式 DB 全域未變。

## 逐輪可見輸出與條件 gold

| 輪 | Safari 可見最終句 | 判斷 |
|---|---|---|
| W1 直接 User 種子 | `うちは2026年10月9日の集合場所を翡翠色のアーチ下に決めたんだね。` | **FAIL**：把 User 的「私は決めた」歸給角色 `うち`；原始 User 句仍保存於隔離 episode。 |
| W2 同日有來源混合 | `集合場所は検討中で、うちが選んだ場所も思い出してんだね。` | **FAIL**：沒有回想 User 的 `翡翠色のアーチ下`，也沒交付朋友向柔和改寫；再一次主語歸屬錯。 |
| W3 相對日未知混合 | `集合先は保留で、一昨日私が選んだ場所も教えてんだね。` | **FAIL**：未斷言虛構地點，但也沒自然說明不能確認、沒完成改寫；把請求照搬成敘述。 |
| W4 第三人引述種子 | `友達が2026年10月8日の集合場所を緑のテント前に決めたと言ったんだね。` | 有界 attribution 守住：仍是朋友所說，未直接升為 User 選擇；不抵銷其他失敗。 |
| W5 第三人不可升為本人 | `集合場所は再確認中で、2026年10月8日に私が選んだ場所も思い出してんだね。` | **FAIL**：沒有把朋友的 `緑のテント前` 當 User 地點，但也沒明示未知或完成改寫。 |
| W6 同日第二筆直接 User 種子 | `うちは2026年10月9日の集合場所を琥珀色の時計台前に決めたんだね。` | **FAIL**：再次把 User 選擇歸給角色；第二筆原 User 句仍在隔離 episode。 |
| W7 同日衝突混合 | `集合先は仮。場所も教えて` | **FAIL**：未任選兩個地點，但只是殘缺指令，不是自然日文的未知回覆，也沒交付柔和改寫。 |

七輪 Safari 泡泡＝raw `assistant_reply`＝`logic.visible_language_guard.final_reply`＝blackboard `utterance.payload.reply` **7/7**；episode 保存的 `Uruha:` 亦與這七句逐一相同。這是交付一致性，不證正確性。W1/W6 的錯誤角色歸屬也被持久化為 assistant 回覆；未證成 profile 事實（profile 為 0 rows）。

## 因果與圖的證據界線

W2/W3/W5/W7 的 `current_turn_source_role_p4.act=mixed_request` **4/4**，但 `mixed_past_place_source_authority_p4` 在 logic、raw runtime trace 與圖的 blackboard **0/4**。不是 gate 已審過並批准舊答，而是它在目前接線下**沒有取得表面權限**：四輪 M31 `surface_authority=true`，其中前三輪 M32 也 `true`；新 wrapper 的 `_has_competing_authority` 依凍結設計優先保留既有權限並返回原流程。source-role lineage 同時只證相同文字 digest，四輪均為 `same_text_but_event_and_parent_lineage_unproven`、`authority_transfer_permitted=false`。不能為了讓 probe 過關就忽略 M31/M32 權限；需要獨立設計其同輪來源與 act 仲裁。W2 已有 W1 原 User episode 與 recent context，不等於已證 gate 真獲取、認可該來源；該輪 gate 根本沒有執行到交付。

Web 圖在 W7 目視可見 USER SIGNAL、RECENT／SHORT TERM／EPISODIC、source-role、決策與 UTTERANCE 節點和投影線；**沒有新 mixed gate 節點**。原始 runtime blackboard 只有節點、序與 digest，沒有可驗的原生 event/parent edge，因此不能把瀏覽器投影線稱作這批已證明的因果連線。這也未過使用者要求的「旁觀者一眼看懂」產品展示標準。

## 成本、嚴格判決與下一步

七輪完成等待 proxy 依序 16.1332、11.0584、10.4066、12.4399、11.8779、11.5696、10.6282 秒，**7/7 ≤20 秒**，合計 84.1138、平均 12.0163、最大 16.1332 秒。上游 M31 七輪各一個完成呼叫，`elapsed_seconds` 合計 60.1935 秒；新 gate 因未獲權限，實際增加模型呼叫 **0**。可靠全管線 token ledger／金額成本 unavailable，不是零成本；等待時間是 runtime proxy，不是 Safari 獨立秒錶。此批沒有公平 baseline。

凍結的正例來源回答 W2 **0/1**，四個 mixed-act 完整回答 **0/4**，新 gate 覆蓋 **0/4**；未知／衝突未出虛構具體地點，但 W3/W5/W7 也沒有交付合格未知回覆。加上 W1/W6 的角色歸屬錯、W7 自然度失敗，**整批 strict FAIL**。程式契約 148/148、七輪一致與延遲 gate 不能覆蓋產品失敗；不能主張比強 LLM 好、長期記憶可靠、人類語用理解成立或完整方程式。

下一個必要項先做 **0-call 權限設計審查**：讀 M31/M32 原始同輪事件與 source-role／混合 act 的交接位置，設計不靠相同 text digest、模型自報信心或舊答文字的 typed event/parent 證書；若能證明只有混合請求的過去事實子任務需要重定向，先以來源不重疊的新題凍結單一權限變因、保護負控、來源／可見／episode／graph／≤20 秒與成本 gate，再實作。W1/W6 的主語歸屬、自然改寫品質及 W7 表面殘句需獨立處理，不能順手合修或重送 W1–W7 追分。若兩個有根據修正批次仍失敗，保留 `REVIEW_REQUIRED`；正式同模型、真人、temporal holdout、VRM／Function Calling 統一驗收仍 pending，Goal active。
