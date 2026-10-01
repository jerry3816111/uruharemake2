# P4 來源約束回覆：首個修後前瞻 Safari 診斷結果

## 身分、凍結與結論

這是 developer-authored prospective product diagnostic，不是獨立 sealed holdout、
強 LLM 公平比較或人評。輸入、source-only 預期與判準先在 commit `c4ac443`
定稿，再由 `research/p4_past_source_fresh_product_probe_freeze_2026-10-01.json`
於任何產品輪次前鎖定；測試時 entry/overlay/launcher 檔案 hash 全部相符。
對 `datasets/p4_past_source_fresh_product_probe_2026-10-01.json` 的十輪沒有修改、
重送或人工 seed。隔離 JSONL 的 SHA-256：
`fa62ffc74a679f0828dc94c14813b4fc9bdbf2df0eef8b503c02198e919f30ed`。

**T10 strict FAIL。** 英文問「我以前說過自己最愛ほうじ茶嗎？若非，是誰？」後，
Safari 最後顯示「その好みを誰が言ったか、今の記録じゃ分からない。」。這句
安全地沒有捏造結衣，也沒有把朋友喜好冒充使用者，但沒有找出凍結的來源，
所以不達到產品任務。新增介面使 query 進入 M22 `factual_or_memory`、
`deterministic_rule_plan` 與日文 source-abstain node；相對舊 before 的
`general_conversation`／泛用二選一澄清，路由/拒答更可追溯，**不是來源
問答成功或對照優勢**。兩次不同案例與輸入，不可當公平 A/B。

## 真實 Safari / runtime 證據

入口 `uruha_web_ui_product_p4_past_source.py`，本機 Safari，launcher 建立的
`0700` 隔離 root：
`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-nm6gqdma`。
首 session `20261001_121750_641737fe`、PID `43382` 跑 T1–T5；其 process
和 port 7892 listener 消失後，第二 session `20261001_122343_3da313f5`、
PID `44042` 使用**同一 root/DB**跑 T6–T10。第二程序最後也已停止，port
無 listener。Safari 各輪有可見聊天、同輪圖/utterance；T10 展開
`past_statement_source_answer_p4` 節點後，狀態確為
`source_not_found_in_delivered_episodes`。沒有把單元假記憶當成 Safari。

| 全局輪 | 最終可見回覆（以完成 JSONL／Safari 核對） | 使用者等待秒 | 觀察 |
| --- | --- | ---: | --- |
| T1 | ほうじ茶が好きなんだね | 14.3248 | 沒說清這是結衣的喜好；episode 有存 |
| T2 | ノートの分類は楽になったね | 10.5429 | 簡化了原意，但仍屬日文 |
| T3 | 友達の結衣はほうじ茶って言ってただろ。 | 10.9153 | 錯把舊朋友資訊帶進無關的引用例句 |
| T4 | 触発されたね | 22.7845 | 對當輪過度簡化；超出 20 秒門檻 |
| T5 | 明日の本棚整理は後で。今は休んで | 11.6674 | 日文可讀、句尾略突兀 |
| T6 | 今日は自分用に温かい生姜湯を選んだね。 | 10.8475 | 新 session 正常回覆自己不同的飲品 |
| T7 | 先生は昨日水を飲んだね。 | 10.0786 | 老師事件未變成使用者事件 |
| T8 | ノートの角が少し折れてもまだ使えるんだね。 | 10.4590 | 保留字面 |
| T9 | 風があるなら窓閉めるのはいいね | 11.2412 | 可能性語氣偏確定，口語少助詞 |
| T10 | その好みを誰が言ったか、今の記録じゃ分からない。 | 3.0838 | 誠實棄答，但 strict source answer FAIL |

10/10 JSONL 記錄 `delivery_complete=true`、10/10 有
`last_saved_episode_id` 和 runtime graph cycle；兩 session 各五輪，沒有
retry。總等候 `115.9450s`、平均 `11.5945s`、最大 `22.7845s`，9/10 輪
符合事前 `≤20s` 成本門檻。全產品逐輪 model calls/token/金額未有完整可核
帳欄位，記 `unavailable`；受限介面自己的 `model_call_added=false` 不等於
全產品 0 call。Safari 串流中可能先出現半句，本表只記最終日誌與最後可見句。

## 最早失真與另一個離線反例

1. T1 真 episode ID
   `f40cc53b-24e4-4940-8941-e466898d5659`。T10 跨重啟
   `candidate_pool` 仍可找到同一 ID，score `0.3436`、rank `18/20`，所以
   **不是持久化遺失**。但 direct episode 只送 T4/T9 兩筆，T1 也未進
   selected working memory 或最近八輪。因此 T10 的
   `passed_to_leftbrain_trace_ids` 無 T1，受限問答只能棄答；這是本輪最早
   的 runtime 阻點。
2. 獨立離線核對 T1 實際原句／摘要又找到第二個阻點：原句
   `友達の結衣はほうじ茶が一番好きだ。結衣が言った。` 的 actor 是 `結衣`，
   但模型摘要 `友達の結衣はほうじ茶が一番好きだ` 被目前摘要正規式抽成
   actor `友達の結衣`。即使把 T1 當輪合法送達，現有核對也會回
   `([], True)`，不會授權答案。這是**事後診斷**，不是新產品 pass。
3. T10 來源 node 沒有 source ID、flow 是
   `explicit_past_source_query → no_qualifying_delivered_episode →
   visible_japanese_abstention`，final hash 與可見句一致；M22
   `factual_or_memory`、route `matched`、performed `deterministic_rule_plan`。
   這證明 fail-closed 接線在本案工作，不證明來源檢索已成功。
4. T1 `memory_runtime.profile.favorites` 曾包含
   `友達の結衣はほうじ茶`，是舊 profile 路徑將第三者敘述寫入使用者欄位的
   **同輪污染訊號**；T10 `memory_snapshot.profile_structured.favorites=[]`，
   因此本案沒有證明該錯誤跨重啟保留。仍必須在後續修正／驗收中顯式
   守住 owner boundary，不能把它藏在 T10 回答之外。

## 下一個前瞻工作邊界

不能重播這十輪宣稱修好。若繼續產品修正，需事前定義一個新的
「explicit source-query evidence delivery」介面：有界地把符合 value 的
持久 episode 明確傳給當輪左腦／provenance，完整處理多筆、矛盾與成本；
同時規範摘要關係前綴的 actor 比對，否則單修 retrieval 仍會棄答。
新的案例須另外凍結，並保留本案 0/1 strict、T3 語義誤用、T4 成本超時與
T1 同輪 profile 污染。此案不能推出人類反應方程式、同模型強 LLM 優勢、
正式 temporal holdout、人評、VRM 或 Function Calling 全面完成。
