# P4 參照探查來源准入：隔離 Safari 八輪結果

狀態：2026-10-19，**准入子門檻成立，整批產品 strict FAIL**。本批是開發者自編、實作和首輪前凍結的 fresh 產品探針；不是正式 temporal holdout、同模型因果 A/B 或真人被理解感評測。前批 deterministic plan-leak 的 strict FAIL／0 eligible 與其 raw 不改判，本批八句各送一次、0 retry，不能用後續修補重算。

## 凍結、隔離與可追溯原件

- 計畫與條件式 gold 在 `3cabf42` 先凍結；opt-in `uruha_reference_probe_evidence_p4.py`、聚焦測試、薄 Web 入口／隔離 controller 及 product SHA 在 `21527e3` 提交並推既有 PR #435，首輪前核到該 head。preimplementation SHA **2/2**、product SHA **9/9**；零模型聚焦／相鄰回歸 **193/193**、語法和 controller `--help` 通過。這些是契約／程式證據，不代替模型或 Safari 效果。
- 全新 launcher-owned 0700 root：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-ab1a56pu`。0-turn 同 PID HTTP ready、planned stop 與 vacant port 後，官方 SHA `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3` ONNX 在獨立私有副本離線封網預熱，得到 1×384 finite vector；首輪前顯式空 profile。沒有用 0-turn readiness 當產品結果。
- 真 Safari session A `20261019_060027_11f3c056`，PID 49940，A1–A4；planned stop 後同隔離 DB 新 PID 50563／session B `20261019_060426_82215eac`，B1–B4。沒有 shell HTTP 代發測試句。逐輪觀察 Safari 泡泡、下方 runtime node graph 並點看節點；raw 八行 `web_logs/conversation.jsonl` SHA-256 `892e98fb2dc29531e5b0f518cfeea3a1f935aa8b679251ad901d001e8dfa9618`。**8/8** 當輪 Safari 泡泡＝raw `assistant_reply`＝`visible_language_guard.final_reply`＝graph blackboard `utterance.payload.reply`；每輪 graph 都有 **1** 個新 `reference_probe_evidence_p4` 節點。這不表示舊 graph 其他分析欄位全面同源。
- 0-turn PID 49418、A／B PID 均已有 planned stop 收據；終局 `ps` 無這三個 PID，`lsof` 未見 7894 listener。保留新開的兩個 Safari 測試分頁，未關原有分頁；Web 服務已按隔離驗收程序停止，這兩頁不是持續在線的網站。

## 凍結八輪：真實可見結果

| 輪 | 使用者輸入 | Safari 最終回覆 | user wait | 來源准入與產品判讀 |
| --- | --- | --- | ---: | --- |
| A1 | `プラネタリウムの受付で働いてる。` | `天文館の受付ですか` | **22.9159 s** | 舊 seed `reference_probe` 被拒；最終 `chat`。普通自述被改問句，且 `プラネタリウム` 變「天文館」；超過 20 秒。 |
| A2 | `今日は入場券の案内を短くした。` | `今日は入場券の案内を短くしたんだね。` | 10.0580 s | 舊 seed 非參照；M32 既有確定提交，基本來源未錯但只複述。 |
| A3 | `撮影の予約は何時から？` | `撮影予約は午前中からできますよ。` | 10.1342 s | 舊錯誤參照 seed 被拒，最終 `chat`；沒有場次資料卻編出「上午開始」，違反未知不編。 |
| A4 | `この歌詞は何の曲？` | `断片だけ投げるなって。元ネタあるならそこまで言えよ。` | 3.4595 s | 明問曲源，`reference_probe` 合法保留且未編曲名；沒有給歌詞時仍用責備式固定口吻，不是自然的低壓承接。 |
| B1 | `投影幕の置き場、どこ？` | `投影幕は机の下に。` | 9.2670 s | 舊錯誤參照 seed 被拒，最終 `chat`；沒有儲位來源卻編出「桌下」。 |
| B2 | `夜空` | `断片だけ投げるなって。元ネタあるならそこまで言えよ。` | 2.8838 s | 凍結的短片段正控，`reference_probe` 保留、未編作品來源；責備式口吻仍不自然。 |
| B3 | `友達が『霧の中に消えた』って言った。` | `友達が『霧の中に消えた』と言ったんだね。` | 9.9039 s | 第三者引述的舊參照 seed 被拒；M32 保留「朋友說」而未升成使用者事實。 |
| B4 | `Shut up, that meme is stupid.` | `うわ、今の言い方は無理。ちょっと距離取るぞ。` | 10.2838 s | 受保護 `low_road/abuse_pushback` 未被參照准入覆寫；最終是日文。 |

新 gate 在四個前瞻假陽性 A1/A3/B1/B3 **4/4** 拒絕舊 `reference_probe` seed／selected；A4/B2 **2/2** 合法保留，B4 **1/1** 受保護路由保留。這是狹義**路由准入**成功，並非 8/8 可見回答品質成功。八輪均為日文且未見內部分析原句外洩；A1 問句化、A3/B1 無來源事實、A4/B2 責備口吻使「自然日文、行動與來源忠實」硬門檻不成立。`visible_language_guard` 接受了這些句子，不能以其 `changed=false` 當品質證書；沒有獨立日語母語人評。

A3/B1 的只讀分因更窄：M22 都以 `general_conversation/full_planner` 執行，`typed_factual_grounding.eligible=false`；M21 compact `qwen2.5:7b` 呼叫各完成三候選且沒有 fallback。無據的「午前中」「机の下」**已存在被選中的** `core_message_jp`，planner tick 1 無修訂，後段表面逐字提交；`constraints.forbid_knowledge=true`、M39 的空 source-frame／`accept` 均未攔住。所見記憶只提供對話背景而沒有這兩個值。原件不保存三候選全文，不能判斷三個都編值，或只是選擇器挑中一個；亦未對模型內部生成原因作因果證明。

## 成本、記憶、判決界線

- user wait 平均 **9.8632625 秒**，最大 A1 **22.9159 秒**，僅 **7/8** ≤20.0 秒。A1 的 M31 semantic model 完成約 **11.7246 秒**但授權被拒，後接 M21 full planner 約 **8.4437 秒**；這是 raw 可見的串行瓶頸診斷，不是已做單變因性能干預。全批 M21 full-planner model completed **3** 輪、M31 semantic model completed **4** 輪；新 gate 收據 `model_calls_added=0`。沒有可信的全管線 scoped token／費用 ledger，不能報精確總 token 或零成本；不同題的前後等待時間不是 latency 因果比較。
- 隔離 Chroma 的 `episodic_memory` 有 **8** 個不同 embedding ID；`knowledge_base`、`procedural_memory`、`user_profile`、`wisdom_semantic` 各 **0**。T0–T8 九份完整 profile 收據均 `present`／0 rows、相同內容 digest `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`。這只證本批未把推測寫成 profile 事實，不保證所有記憶情境。正式 DB、原始 dirty checkout、無關 `output/graduate_application_report/` 未動。
- 凍結規格要求 4/4 阻擋、2/2 保留、8/8 自然且來源忠實、8/8 ≤20 秒等**全部**成立；目前 A1 latency 與 frame、A3/B1 捏造、A4/B2 對話口吻已違反，整批 **strict FAIL**。不能把 4/4 的路由改善外推成「已理解人類言外意」、正式同模型強 LLM 優勢、真人被理解感或完整產品 PASS。Safari 圖像化驗收只證實逐輪資料流與這個准入節點可見，不能證實圖節點的認知假設為真。

## 下一個必要交付

A3/B1 的**普通資訊問句**斷點已只讀定位到「一般 planner 被選 core 已含無來源值，末端守門接受」，與 A1 串行超時、A4/B2 語氣問題分開。下一步須先定一個可反駁的來源／未知狀態契約，以及能辨別**候選生成**和**候選選取**責任的最小稽核；使用新的未曝光時間／地點、有來源／無來源、引述／混合負控，預先固定條件 gold、≤20 秒／日文／圖／記憶／成本 gate 與 SHA，才做單一 opt-in 修正和全新隔離 Safari。不得重送本八句、依失敗輸出改 gold、把「一律不知道」當方案或順手改 A1／參照語氣。若下一批仍失敗，依任務卡最多兩個有根據批次後 `REVIEW_REQUIRED`。正式同模型強 LLM 比較、真人、temporal holdout、長對話一般化、VRM／Function Calling 統一入口仍 pending；Goal 保持 active。
