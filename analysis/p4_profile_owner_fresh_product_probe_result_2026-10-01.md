# P4 本人 profile 准入：前瞻十輪 Safari 產品結果

狀態：**狹義 writer gate 在本次十輪為 10/10；完整產品 strict FAIL，保留負結果。**
這是開發者自製、事前凍結的隔離產品案例，不是 sealed／temporal holdout、
同模型強 LLM 公平比較、真人偏好評分或一般語用理解證明。介入僅是
`research/p4_profile_owner_admission_plan_2026-10-01.md` 的新本人 profile
寫入准入；前一項有界來源送達 strict `0/1`、`REVIEW_REQUIRED` 不變。

## 事前邊界與實際執行

資料／答案／門檻見 `datasets/p4_profile_owner_fresh_product_probe_2026-10-01.json`
及 `research/p4_profile_owner_fresh_product_probe_plan_2026-10-01.md`。
首輪前 freeze manifest 的十個完整 SHA-256 核對 `10/10`。產品 additive
實作的聚焦＋相鄰回歸為 `152 passed, 8 warnings`，安全 launcher 的
0-turn `check` 通過；這兩者都不是 Safari 品質證據。

只在安全 worktree、launcher-owned `0700` 系統 temp root 與新 Safari tab
執行，隔離 root 為
`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-at223w0u`。
十筆 exact input 各送一次，無回答重試；十個不同 episode ID 全部在隔離
Chroma 持久化。T1 後額度中斷令第一個 server 停止；核實 T1 已完整落盤後，
**沒有重送 T1**，以同一隔離 DB 啟第二個 session 送 T2–T5。原計畫的
T5 後停機、port 7892 確認關閉、同 DB 再啟送 T6–T10 也實行。因此實際為：

| 輪次 | Session | Server PID | 與凍結程序的關係 |
|---|---|---:|---|
| T1 | `20261001_163250_c35ee26f` | `74369` | 額度中斷後退出；額外重啟 |
| T2–T5 | `20261001_170609_afe5c431` | `78061` | 延用同一隔離 DB |
| T6–T10 | `20261001_171040_9e2cc5e5` | `78496` | T5 後預定重啟 |

凍結程序要求 T1–T5 同一 session、只在 T5→T6 重啟；**三個 session／
兩次重啟是程序偏差，產品完整性 strict 不能算通過**。多一次重啟雖提供
更多持久化觀察，不能事後用它代替原定程序。測後 server 均已停，7892
無 listener；Safari 測試 tab 留著但本機服務已停，沒有關閉原有 tabs。
沒有碰正式 DB、原始 dirty checkout 或外部部署。

## 十輪可見結果與資料寫入

`A/Δ` 是同輪 graph 的 `admitted_count / profile_collection_count_delta`；
後者只是資料庫 collection 總數差，**不是新 row ID 的逐筆證明**。
Safari 畫面逐輪觀察下方 runtime graph；原始 JSONL 的
`cognition_trace.runtime_trace.blackboard[]` 中每輪恰有一個 `label=utterance`，
其 `payload.reply` 與 `assistant_reply` 逐字 `10/10`。這是日誌／graph
結構的核對，不能僅憑它取代獨立的畫面語義判讀。

| 輪 | Safari 最終可見回覆 | A/Δ | 等待秒 | 語義／寫入觀察 |
|---|---|---:|---:|---|
| 1 | `友達の灯里は花梨茶が一番好きだと灯里が言ったんだね。` | 0/0 | 14.5788 | 朋友偏好未寫本人；原 episode 保留 |
| 2 | `千景はあずき茶、うちは刺繍` | 1/1 | 14.5872 | 只寫本人「刺繍」，但「うち」把它說得像角色本人且句子不完整 |
| 3 | `忘れてないし、刺繍だろ。` | 1/1 | 9.7271 | 只寫本人「紙版画」，回覆卻漏當輪內容、錯延續舊「刺繍」 |
| 4 | `前に紙版画が好きって言ってたし。` | 0/0 | 9.5196 | 否定「最喜歡」未轉正向或自動 dislike；回覆未接住該否定 |
| 5 | `苔庭が好きだね。` | 1/1 | 9.3900 | 省略主詞的本人喜好有寫入 |
| 6 | `豆本作りとしそ茶だね` | 1/1 | 9.7525 | 只寫本人「豆本作り」；回覆未明說「しそ茶」屬蓮実 |
| 7 | `ん、その好みは覚えとく。` | 1/1 | 9.6128 | scoped drink 正向寫入 |
| 8 | `ん、訂正の内容はそのまま覚えとく。` | 1/2 | 10.1269 | scoped correction 寫新正向與舊值明示負向，保留歷史 |
| 9 | `ん、その好みは覚えとく。` | 0/0 | 9.6798 | 第三者傳話被拒寫；**回覆卻錯誤承諾「記住那個好み」** |
| 10 | `その好みを誰が言ったか、今の記録じゃ分からない。` | 0/0 | 3.4367 | 沒有污染 profile；來源問答 strict FAIL |

十輪等待總計 `100.4114s`、平均 `10.04114s`、最大 `14.5872s`，
逐輪 `≤20s` 為 `10/10`。這是使用者等候時間，不含 server 啟動／
預檢成本。全產品模型 calls、tokens 與價格缺乏可靠完整欄位，記
`unavailable`；overlay 不增加模型呼叫不代表整個產品零呼叫或零成本。
回覆都使用日文形式，但 T2/T3/T4/T6/T9/T10 有上述語義或表達缺陷，
不可宣稱 `10/10` 自然日文、人格或「被理解感」。

## DB、圖與來源鏈核對

T5 隔離 DB 的 `user_profile` 只有「刺繍、紙版画、苔庭」三筆本人 like。
T10 DB 有七筆 `subject=user`：四筆一般 like「刺繍、紙版画、苔庭、
豆本作り」；typed drink 的「レモンバーム茶」舊 like、「橙花茶」新 like
與「レモンバーム茶」明示 dislike。六個禁止的朋友／引文／否定值
「花梨茶、あずき茶、桑の実茶、羅漢果茶、しそ茶、黒豆麦茶」均未
進入 `user_profile`。逐輪 gold 與新增 row 數及值一致，故此**限定 writer
case** 為 `10/10`；不同於舊產品案已持久化兩筆錯 owner，本案沒有新錯
owner。兩案資料不同，不可當成正式配對因果效應量。

T7 舊正向記錄的實體 metadata 仍是 `memory_state=active`，沒有被物理
改寫或刪除；T8/T10 的既有 typed resolver 以同 scope 新值把舊 ID
`6fedf656-0daa-424e-b857-17f62c3a7841` 判為 **historical**，新 ID
`0c213820-052c-48df-ba81-8f000e2acc91` 為 current active，負向舊值
另有 ID `dabdc7d9-59cb-4c4b-8008-7ff5615e18c5`。不能把「解析後歷史」
寫成「舊 row metadata 已物理轉 historical」。十筆 turn episode 均在
隔離 DB；事後另有一筆 consolidation，故資料庫 episode collection 的
總 row 數可高於十。T9 graph 的 `profile_owner_admission_p4` 顯示
`path=p4_i_selected`、`reason=selected_source_has_unresolved_preamble`、
`admitted_count=0`、`profile_collection_count_delta=0`、
`answer_use_authorized=false`；圖中 hash／owner／理由不含原始私有句。

T10 的 T1 持久 episode ID 是 `99903c3e-a551-490b-a153-ac6586e056f4`。
它在 T10 候選池 `rank=20/20`，也在 `passed_to_leftbrain`，實際 channel
是舊 `direct_episode`；**這只證明 episode 檢索與送進左腦，不證明來源
答案契約採用了它**。M22 選 `factual_or_memory`，執行
`deterministic_rule_plan`、`contract_status=matched`；但最終
`logic.intent=pragmatic_revision`，不再是 `past_statement_source_recall`。
來源 surface guard 因 `selected_source_query_route_or_intent_drift` 而
`surface_integrity_failed_closed`，`answer_use_authorized=false`、
`candidate_count=0`、`source_memory_ids=[]`，畫面答「不知道」。
本輪 `p4_bounded_source_lookup` trace 為空；不能稱新 channel 解決此案。
最早可定位的答案失敗在**來源契約候選／intent 交接**，不是 T1 沒存或
完全沒檢索。事前 T10 要求明說「使用者曾轉述灯里說她喜歡花梨茶」，
故來源問答 strict `0/1`，不能把誠實 abstain 改算通過。

## 結論與下一個必要 gate

新 writer 准入在這一組前瞻產品輸入阻止了六種非本人／引文／否定值的
profile 污染，且保留本人寫入、typed 訂正與 episode；這是有用但有界的
工程改善。**完整產品 strict FAIL**，原因有程序額外重啟、T10 來源答案
失敗，以及可見回覆錯 owner／漏當輪內容／假寫入承諾。不得重播曝光
十輪追分、改 freeze 或把狹義 writer 成績外推為整體成功。

下一個單一可歸因產品 gate 應先處理「持久 profile 准入結果 → 可見寫入
承諾」的事實一致性：T9 是最小真反例，DB 未寫卻說已記；需要另立
before、允許檔案、負正混合例與新前瞻驗收，保留自然日文、episode
及其他寫入。T10 的 source intent drift 是**獨立** `REVIEW_REQUIRED`
審查點，不能偷偷併入 writer gate；T2–T4/T6 的語義／角色品質也保留。
尚無同模型公平 baseline、正式 holdout、真人評分、VRM／Function Calling
全產品驗收，不能推論研究級優勢或完整專案完成。

原始隔離 JSONL 為
`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-at223w0u/web_logs/conversation.jsonl`，
SHA-256 `85f255dd1ec2cac06bc7ae54261f59dce943e485c5c777e6a52d94358ec7ae43`，
十行 exact input `10/10`。隔離 root 是可覆核的本機暫存位置，非永久封存或
正式資料庫；若系統清理暫存，需以此報告與已提交的 freeze／程式／測試
核對，不能聲稱原始 runtime 仍存在。
