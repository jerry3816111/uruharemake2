# P4 後句本人否認：凍結 Safari 產品批次的中斷與負結果

**事前 strict gate：FAIL，不能宣稱八輪完成。** 凍結八輪中只有 T1–T6
經由 Safari 各送一次；T7、T8 未送。前四輪後按計畫真停舊 PID、關 port，
並用同一隔離 DB 的新 PID/session 執行 T5、T6；其後 Codex 回合中斷使
第二個服務程序終止。恢復時唯讀檢查確認 raw 恰六行、7892 無 listener，
沒有用第三次啟動補送已曝光資料。事前 plan 明訂額外重啟或漏輪為程序
FAIL、不在本批重跑追分。即使六個觀察到的 writer 結果正確，也不抵銷
可見回覆、未完成輪數或程序失敗。

## 凍結、環境與已做的驗證

- 事前設計 `research/p4_profile_postposed_self_denial_plan_2026-10-02.md`；
  八輪資料與 strict gold 在
  `datasets/p4_profile_postposed_self_denial_fresh_probe_2026-10-02.json`、
  `research/p4_profile_postposed_self_denial_fresh_probe_plan_2026-10-02.md`。
  `research/p4_profile_postposed_self_denial_fresh_probe_freeze_2026-10-02.sha256`
  的 24/24 hash 首輪前 OK；freeze commit `bfd137b` 已推既有 branch。
  本案是 developer-authored prospective probe，不是正式 holdout 或人評。
- 最後 protected-route 測試加入後，聚焦＋受影響相鄰回歸
  `221 passed, 8 dependency warnings in 98.65s`（測試進程 FD soft 4096）。
  新安全 launcher 0-turn check exit 0；localhost、獨立 `0700` root、
  overlay/pre-writer hook 與重用 runtime 的隔離設定均核對。獨立純函式
  審查在產品前核對八輪 gold，8/8 一致；這些都不是 Safari 證據。
- 本案隔離 root 保留於
  `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-4qb6ifi7`；
  raw `web_logs/conversation.jsonl` 恰六行，SHA-256
  `31923687010fff11e684ec63791c981107be92e493cc920b86ea13d3dd151a9d`。
  同 root 的 `memory_db/chroma.sqlite3` 唯讀覆核時 SHA-256 為
  `e323988c1b2bb7aaf1a139cf49cffeb01ad0c8f012c82eb99d1b28ae9e383564`；
  這是中斷後的最終狀態，不是逐輪 DB 快照。
  真 session 為 `20261002_053918_449139c7`（T1–T4）及
  `20261002_054309_69140c0d`（T5–T6）。T1–T6 無回答重試；T4 後
  舊 PID `63714` 已退出且 port 關閉，新 PID `64320` 使用同 root；
  中斷後它亦退出。Safari 泡泡與 node graph 曾逐輪觀察；沒有另存
  截圖 artifact，不把 raw JSONL 冒稱 screenshot。

## 真產品觀察：writer 局部有效，回覆並未接住當輪意思

| 輪 | 凍結來源語義；准入數／raw profile count delta | Safari 最終日文／最早可見問題 |
|---|---|---|
| T1 | 本人正向後立即否認；`0 / 0`，veto 1 | `一回、まあ無理ってほどじゃない。勝手に悪い方へ取るなよ。`；plan 錯選 `ask_like_me`，把物品偏好導成關係好感。 |
| T2 | 撤銷黒豆柚子飴，保留甘栗せんべい；`1 / 1`，veto 1 | `普通に、別に嫌いではないし。そこまで身構えるなって。`；未辨認撤銷與新偏好。 |
| T3 | 作文例句月桃水被否認；`0 / 0`，veto 1 | `甘栗せんべいって言ってただろ。`；錯誤 plan 下由上一輪正確記憶牽引表面，未處理本輪例句。 |
| T4 | 朋友真緒轉述相反意見，不撤銷本人桜葉ソーダ；`1 / 1`，無 veto 決策 | `うちは桜葉ソーダが好きではない、と友達の真緒が言ったんだね。`；M32 選中表面把本人／角色視角混在一起。 |
| T5 | 後句是疑問，不是確定否認；`1 / 1`，無 veto 決策 | `まあ、全くじゃないとは言わない。そこ聞いて安心したいだけだろ。`；再錯選 `ask_like_me`，捏入未證實的安心需求。 |
| T6 | 否認是引文例句，保留本人焙じ梅茶；`1 / 1`，無 veto 決策 | `焙じ梅茶が好きなこと、作文の例文`；M31 選中內容把本人喜好當成例句，且句子不自然／未完成。 |

六輪 raw 的 `profile_owner_admission_p4`、同名 graph node 與 writer
結果一致；raw 回報的 collection-count delta 為
`[0,1,0,1,1,1]`，事後 DB 四筆不同 ID 的值與時間順序支持此觀察。
然而 raw 自標 `collection_count_delta_not_id_attributed`，且當輪前後
沒有另存 row ID 集合快照，故**事前規定的逐輪 ID 差驗證未達**。
最終 DB 四筆
`subject=user/fact_type=like` 值是甘栗せんべい、桜葉ソーダ、
すだち麦茶、焙じ梅茶；被否認的三個值、`dislike` row 均未出現。
六個互異 `source=turn_episode` 已持久。這只支持**六個已執行輪次**
的限定 writer 接線，不是原八輪 gate PASS，也不表示所有記憶層安全。
raw blackboard `utterance.reply` 與 `assistant_reply` 6/6 逐字相同，
真 `selected_plan` 也解釋了錯誤表面，故失真不只是渲染層。

可見失真的最早根因之一可由既有純規則重現：
`uruha_leftbrain_rules.contains_any` 與
`uruha_brain_mac.LeftBrain._contains_any` 把關係問句關鍵字 `好き？`
壓縮成 `好き`，於是含 `私は…が好き。` 的陳述也可能匹配
`ask_like_me`。T1/T2 的 M31/M32 來源語義接管遭拒後回落到這個錯
plan；T3 另被上一輪正確 profile 記憶拉偏。T4/T6 的來源指涉／引文
scope 是不同問題，不能假稱只改問句 matcher 就會修好全部六輪。

## 成本、圖像與 claim 邊界

六輪 `runtime_latency_m19.user_wait_seconds` 分別為
`11.9655, 12.2923, 12.4786, 12.7904, 3.0901, 12.7223`，
合計 `65.3392s`、最大 `12.7904s`，觀察到的 6/6 低於 20 秒；
T7/T8 無數據。M31 `model_call_completed` 在五輪為 true、T5 無此
完成紀錄；完整產品 call/token/價格 ledger 仍不可用，不能說零模型
成本。圖像化 UI 的 node graph 逐輪顯示 owner/writeback、selected
plan、utterance；owner audit node 只含 hash/類別/count，未含原句。
既有 `personhood_perceive_other_v2_13.payload.user_signal` 及其
`known.value`／`human_pragmatic_understanding.literal_content.value`
可顯示輸入原文；本卡
owner audit node 雖沒有原句，事前文字寫的是「graph 不得洩出原句」，
並未限定為單一 audit node。照字面解讀，整張 graph 的這項隱私條件
也未達成；它是既有跨層呈現邊界，不能以 owner node 的 hash 化
宣稱整張 graph 安全，也不改變本批已成立的 strict FAIL。

本批不能證明 T7 英文 typed path、T8 中文正例的真產品非干擾，也
不能證明一般語用理解、真人被理解感、同模型強 LLM 優勢、正式
temporal holdout、VRM/tool 完整交付或人類反應方程式。下一步應先
定案新的**未曝光**、單一變因問句敏感的關係 intent 匹配修正與
正負控制，再做新產品確認；T4/T6 另保留為來源 scope 反例，不能
與問句 matcher 混修。舊八輪 selected-plan PASS、十一輪 FAIL 及
來源送達 `REVIEW_REQUIRED` 均不改判。
