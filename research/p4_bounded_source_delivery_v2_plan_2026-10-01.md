# P4 下一批次設計：明確來源問句的有界證據送達

狀態：**實作前設計，未改程式或跑修後案例**。本設計由已凍結的
`p4_past_source_fresh_product_probe` 負結果出發；該案 T10 0/1 strict、
T1 rank 18/20 未送進左腦，且摘要關係前綴造成 actor 錯配。舊案與
`p4_current_relation_recall_probe` 均不得重跑追分；新測試需另凍結。

## 單一介入與不變邊界

介入是 explicit source-query 的**證據送達／歸屬核對交易**：從已選的
單一 value 有界取得過去 `turn_episode`，真實附上 `memory_id`、trace、
來源 channel 到本輪 `memory_data.memory_provenance.passed_to_leftbrain`，
使左腦和 graph 都能看見；摘要的 `友達の<姓名>` 只是關係前綴，不應
把它當作姓名本體。若改後成功，仍只能把**整個交易**視為可歸因差異，
不能分別宣稱檢索或前綴正規化各有獨立因果效果。

不可改基礎模型、prompt、generation cap、已凍結資料/結果、B1/B2、
舊 before entry/launcher、正式私有 DB、原始 dirty checkout、其他產品
路由。安全/拒絕優先、日文 guard、公開人格與不從私密推測寫事實記憶不變。
候選只能作「使用者先前報告某人說過」的陳述來源，不證明本人真實偏好。

## 有界查詢與 fail closed

1. 只在 `classify_past_statement_query_p4` 精確選中時、在原本
   `query_all_layers` 完成後，對同一隔離／產品既有 `episode_col` 做一次
   Chroma `get(where={"source":"turn_episode"},
   where_document={"$contains": value}, limit=9,
   include=["documents","metadatas"])`。沒有模糊向量擴大、沒有掃
   profile/wisdom／網路／別的使用者 DB；查詢 value 來自當輪 observable
   問句，不能以摘要自行製造。9 是 sentinel：0–8 筆才完整處理，9 筆
   一律 `overflow` 棄答，不能只選前八筆假裝唯一。這只涵蓋原樣 literal
   value 的同 collection 命中，不是 NFKC／語義等價字形、全庫或真人偏好
   的唯一性；正向授權還須原句 value 與問句 value 原樣相同，顯示句只說
   「找到的記錄」。若其他已送達 episode 正規化後相同、但不在本次 lookup
   ID 集合，視為檢索不完整而棄答。例外、ID/document/metadata 長度不齊、
   缺失／重複 ID、metadata `source` 不符、單文件超過 2048 字或總文件超過
   16384 字一律 `lookup_unavailable` 棄答，不能截斷或沿用部分候選。
2. 將 0–8 筆**全部**以真 `stored:episode:<id>`、channel
   `bounded_source_lookup` 附入本輪 `passed_to_leftbrain`；若已由原路徑
   送達同 ID 則不重複附加，**lookup 回傳內部**重複 ID 則視為失敗；
   同步 `passed_to_leftbrain_trace_ids`。這是新的已送達來源，不改寫
   working-memory rank 或原本 direct query 結果。記錄 lookup 狀態、
   matched count、source IDs、elapsed；sidecar 不再複製原始對話。
   `where_document` 可能匹配到 assistant 回覆或舊問句；最後仍必須逐筆
   解析 User 原句＋Summary 同一 actor/value。含值的損壞/偽造 delimiter
   文件必須作 unresolved 阻擋答案，不得像舊 parser 靜默丟掉；完整的同句
   過去來源問句本身不是肯定證據，不能因重複詢問製造歧義；問句混雜聲稱
   仍是 unresolved。9 筆 sentinel 在任何解析、去重或排除問句之前判定。
3. 摘要核對只允許朋友第三者原句配同名 `友達の<actor>`，不對 user 原句
   剝 `友達の`，不以任意子字串／翻譯猜名字。正向、否定與第二人物摘要
   共用這個核對；其他關係、不同 actor、多個 actor、
   不確定/否定、複合值、匿名/代詞、引文、欄位注入仍棄答。查詢失敗、
   overflow 或證據非唯一時 surface 必須是中立日文，node 顯示原因。

此路徑可能增加一次本機 Chroma exact-substring 查詢和最多八筆序列化。
需記 `lookup_elapsed_seconds`、end-to-end 秒與輸入 token/模型 call 有無完整
核帳；`get` 內部搜尋成本未知，不能事先稱 O(1) 或免費。開發 gate 以
0–8/9 邊界、exception、duplicate、assistant-only match、previous-question
nonassertion、two actors、conflicting correction、NFKC 等價但 literal 不同值、
metadata/文件損壞、unsafe query、cross-session
persisted IDs、graph/visible final 一致性為固定反例。

## 前瞻驗收

允許修改檔案：現有 additive P4 來源 overlay、該 overlay 的聚焦測試、
本設計／結果／任務卡、新前瞻案例及必要的新 additive 入口／launcher。
舊凍結 before entry、資料與結果零 diff。

先完成離線 fake collection contract 和相鄰 route/surface/provenance 回歸；
再用**新人物、新 value、新十輪**先 commit/source+rubric+hash 才開真本機
Safari。T5 後真 PID/session 重啟，T1 脫離最近八輪。strict：T10 T1
episode ID 經新 channel 真正送達，摘要 actor 前綴對齊，唯一 actor/value
回答以自然日文指出是使用者先前轉述；graph 的來源 ID、route、final
與可見句完全一致。非 T10 逐輪語義/日文、profile owner、episode
write、latency `≤20s` 分開報。正式 same-model baseline、人評、VRM
與工具仍 pending。失敗原樣保留；這是同一 P4 工作項僅剩的一個有根據
修正批次，不能再拿本案或新案換規則追分。
