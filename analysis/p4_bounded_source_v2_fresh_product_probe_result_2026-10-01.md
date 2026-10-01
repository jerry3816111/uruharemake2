# P4 v2 有界來源送達：前瞻十輪 Safari 產品結果

狀態：**可見問答成功；事前凍結的介入專屬 strict gate FAIL，`REVIEW_REQUIRED`。**
這是一次開發者自製的本機產品診斷，非 sealed holdout、同模型公平對照、
真人偏好評分或一般化能力證明。事前資料、答案與停止規則見
`research/p4_bounded_source_v2_fresh_product_probe_plan_2026-10-01.md`、
`datasets/p4_bounded_source_v2_fresh_product_probe_2026-10-01.json`；六個檔案的
hash 在首輪前依 freeze manifest 核對為 `6/6`。先前 `紗枝／桑の葉茶` 和
`結衣／ほうじ茶` 兩個 strict 負例保持原樣，沒有重跑。

## 實際產品操作與可見結果

僅在安全 worktree、隔離 `0700` temp root 和新 Safari tab 進行。第一次
server PID `53436`、session `20261001_134043_48204f2b`；T5 完成落盤後
停舊 process，`7892` port 確認關閉。沿用**同一隔離 DB**重啟，第二次
server PID `54713`、session `20261001_134639_b23d874b`，Safari 同一新
tab reload 後送 T6–T10。兩次 server 都已停止；只保留隔離 root 與原始日誌
供查核，未關／改原有 Safari tabs。對 dataset 的十筆 `input` 逐字比較為
`10/10`，每筆只送一次，0 回答重試。T3 曾有一次 paste clipboard timeout，
畫面確認輸入仍空白後只重新貼入，沒有形成重複輪次。

| 輪 | Safari 最終可見日文 | 等待秒 | 觀察 |
|---|---|---:|---|
| 1 | `凪紗、ルイボス茶` | 14.5252 | 來源片段可見，但不是自然完整句 |
| 2 | `写真の日付整理は探すのに便利だね` | 9.6236 | 依當輪照片整理回覆 |
| 3 | `忘れてないし、友達の凪紗はルイボス茶だろ。` | 10.0347 | 問題是作文引文／本人非偏好，卻插入 T1；語義偏題 |
| 4 | `古いノートを発見してページにラベルを貼ったんだね。` | 10.2776 | 英文輸入後以日文回覆 |
| 5 | `うちは明日机を整理したいので今は散歩に行くんだね。` | 10.0914 | `うちは` 錯把使用者計畫說成自己 |
| 6 | `今日は自分は温かい白湯を選んだね。` | 9.2911 | 重啟後第一輪；保留本人／朋友區別的原句未進回覆 |
| 7 | `いとこが昨日傘を買い、それが彼女の用事で私のものではないんだね。` | 9.7712 | 英文輸入後日文；保留非本人事件 |
| 8 | `机の引き出しに付箋が残っていたんだね。` | 9.5204 | 當輪簡短回覆 |
| 9 | `なるほど、窓の外は暗いね。` | 10.2512 | 遺漏使用者稍後開燈的行動 |
| 10 | `見つかった記録じゃ、凪紗がルイボス茶を一番好きって言ったとあんたが話してた。` | 3.1990 | 正確表達「使用者先前轉述朋友說」，不冒稱本人事實 |

十輪 `delivery_complete=10/10`、不同 `last_saved_episode_id=10/10`、
runtime graph `utterance.payload.reply` 與 JSONL/Safari 最終可見句 `10/10`
一致；等待總和 `96.5854s`、最大 `14.5252s`、`≤20s` 為 `10/10`。
每輪 Safari 的 runtime node graph 都顯示該輪輸入、回覆及記憶節點。
T10 目視有來源檢索、來源判定、選計畫、輸出及跨記憶線；展開節點時
可見 lookup `complete`、T1 ID 和 source `resolved_third_party_source`。
這個畫面核對加上 JSONL 是產品證據；沒有將 UI 圖像當作語義真值。

## T10 真正走過的來源鏈與 strict 判定

T1 持久 episode ID 為 `cec61e04-4e8a-4dc5-a826-21cd43e4b6f3`。
T10 的 `bounded_source_lookup` 在 `0.001798s` 完成 literal-value 查找，
`2` 筆命中為 T1 和 T3；後者是別的飲品引文輪，其 episode 文件因 T3
回覆帶到 `ルイボス茶` 而命中，並沒有被當成來源事實。來源契約最後唯一
選 T1，`selected_actor=凪紗`、`speaker_role=third_party`、
`value=ルイボス茶`、`answer_use_authorized=true`，狀態
`resolved_third_party_source`。M22 為 `factual_or_memory`、
`deterministic_rule_plan`、`matched`。graph blackboard 的順序是
`p4_bounded_source_lookup` index 25 → `past_statement_source_answer_p4`
index 26 → `selected_plan` index 27 → `utterance` index 61；最後句與
source contract 文字／SHA-256 完全相同，SHA-256 為
`3b4909dc45a803fea5a84fb6b253bb3d239b1e1465b9fd2ee32ca3bdaf62db36`。

**但事前 strict 要求 T1 經新 `bounded_source_lookup` channel 真送達。**
T1 雖列於 lookup 的 `source_memory_ids`、`passed_to_leftbrain` 和 graph，
其實際 `passed_to_leftbrain.channel` 與 source candidate 的 channel 均為
**`direct_episode`**。新 channel 送達的是 T3 episode
`01acb962-904f-4b30-955f-54036e63d299`，不是 T1。v2 設計允許
「原路徑已送同 ID 則不重複附加」，所以這不是重複資料 bug；然而本次
T1 恰由原路徑送達，即使 working-memory rank 為 `13/17`、未選入 top 5，
仍無法把可見答對歸因於新有界送達。依**原先凍結的通道條件**，
strict 為 `0/1`，不事後放寬成「有查到且答對就算通過」。最早未滿足層是
介入專屬 evidence delivery / 因果識別，不是 T10 actor parser、M22 或
日文 surface。不能據此宣稱 bounded lookup 對 T1 答案有增益。

## 另外保留的真產品缺陷與證據範圍

來源歸屬的答案正確不代表 profile 寫入正確。T1 後 runtime profile 的
`favorites` 出現 `友達の凪紗はルイボス茶`；T3 後又出現
`「私は炭酸水`，即使原句明說是作文例文、不是本人偏好。隔離
`memory_db/chroma.sqlite3` 的 `user_profile` 目前仍有兩筆
`subject=user`、`fact_type=favorite`、`memory_state=active`：
`0d6632d8-065e-4e0b-a91c-ab6749676f9c`（朋友偏好）和
`edf49681-c1b7-491a-86fb-9bacfddbad05`（引文／否定）。它們的建立時間
都在 T5 重啟前，第二 session 後仍在 DB；第二 session 的當輪 snapshot
顯示空，不足以抵消持久 DB 污染。這是獨立且重要的 owner/negation 問題，
不能被 T10 正確答案掩蓋。T3 偏題、T5 角色歸屬錯、T9 遺漏行動也保留，
因此不宣稱 `10/10` 語義或人格品質。

原始隔離日誌：
`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-g9i2xncr/web_logs/conversation.jsonl`；
SHA-256 `c81e9ab17df4432a2c6ddc99e1b0770edeeaf018cd11edc54d7b63e12b0819fe`。
v2 的離線／相鄰測試為 `151 passed`，但不是 Safari 或因果增益證據。
真產品全系統 model call/token/cost 沒有可靠完整欄位，記 `unavailable`；
lookup 的 `0 extra model calls` 只屬 overlay。沒有外部部署、正式 DB
寫入、同模型 baseline、人評、sealed/temporal holdout、VRM／工具驗收。

## 審查停點

依此工作項「最後一個有根據修正批次仍不通過則停」的規則，來源送達
**保持 `REVIEW_REQUIRED`**。下一步是設計審查而非重跑凍結十輪：
要先決定如何在全新、事前凍結的情境中區分「舊 direct path 已送達」與
「只有 bounded channel 才送達」，並讓去重仍保持單一真 ID；不得為追分
關閉舊路徑、弱化門檻或把本次正確可見答案包裝成介入因果證明。
持久 user-profile owner/引文否定污染是另一個必要產品 gate，須另立
before、單一修正變因及負反例，不混作這次 strict 結果。
