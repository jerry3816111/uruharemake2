# P4 profile 記憶承諾：十一輪 Safari 前瞻產品結果

**結論：可見回覆／實際 profile 寫入的狹義子門檻通過；完整 planner→graph→surface strict gate 仍 FAIL。**
T1 朋友傳話的最終日文正確拒絕把朋友喜好當本人偏好寫入，DB 也沒有該值；
但真實 `selected_plan`／`logic.intent` 被 M32 改為
`deterministic_semantic_commit_m32`，其 `core_message_jp` 為
`今は枇杷葉茶が好きであるんだね。`。這句將朋友偏好指向對話者，
沒有選中事前設計要求的來源受限 noncommit plan；最終 surface 是被後段
guard 救回。新 truth node 仍顯示 `matched`，因它只排除兩個顯式
memory-write intent，未檢查此選中 plan 的角色歸屬。不能把該 node
的 11/11 當成整個圖或整體產品通過。此負例原樣保留，**不重跑同一案追分**。

## 事前鎖定與程序

- 開發者自製、非 sealed holdout 的十一輪輸入／判準見
  `datasets/p4_profile_write_ack_fresh_probe_2026-10-01.json` 與
  `research/p4_profile_write_ack_fresh_probe_plan_2026-10-01.md`；
  freeze commit `759b88e`，`research/p4_profile_write_ack_fresh_probe_freeze_2026-10-02.sha256`
  首輪前 `shasum -a 256 -c` 全部 OK，修後不改資料或程式。
- 安全 launcher 的 0-turn `check` 通過（sandbox、overlay 安裝、0 model/Safari calls）；
  fresh temp root `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-7vqr9lc3`
  初始五個 Chroma collection 均 0 rows。只在同一個新 Safari 分頁用
  `127.0.0.1:7892` 逐筆送 exact input；T1–T4 各一次後停止 PID `24764`，
  `lsof` 證實 port 關閉、該 PID 不在，再用同一 root 新 PID `25355`
  啟動並 reload 該分頁，T5–T11 各一次；沒有回答重試或第二份資料。
  Session ID 分別 `20261002_000231_761f5174`（4 輪）與
  `20261002_000719_338a35b8`（7 輪）。末輪後 server 已停、temp root 保留覆核。
- 隔離 raw JSONL：`.../uruha-product-7vqr9lc3/web_logs/conversation.jsonl`，
  SHA-256 `73e5270525174444ce2a80b8ac458095f5440e7206e2c4cea3a6c1fc6d760352`。
  它有 11 行；與 freeze dataset 逐行 `diff` 無差異。Safari 每輪實際泡泡與
  下方 node graph 均觀察，不能只用 JSONL 代替 UI。

## 實際前後差異與逐輪結果

前項 2026-10-01 的已曝光真產品 T9：owner 准入 `0`、profile delta `0`，
卻顯示 `ん、その好みは覚えとく。`，是此次 before。此次新案的三個朋友／引文
輪 T1/T4/T6 最終都顯示 `ん、その話は聞いた。お前の好みとしては覚えない。`，
沒有該三值的本人 profile；這是**限定來源句型的可見修正**，不代表舊案重測通過。

| 輪 | source-only 預期新增 profile | 實際新增 | Safari 最終／觀察 |
|---|---:|---:|---|
| T1 朋友傳話 | 0 | 0 | 日文拒寫；但 selected plan 錯歸本人（本案 strict FAIL） |
| T2 本人飲品 | 1 | 1 | `ん、その好みは覚えとく。` |
| T3 訂正飲品 | 2 | 2 | `ん、訂正の内容はそのまま覚えとく。` |
| T4 英文朋友引述 | 0 | 0 | 日文拒寫 |
| T5 中文本人點心（重啟後） | 1 | 1 | 日文既有 write 承諾 |
| T6 中文朋友報述 | 0 | 0 | 日文拒寫 |
| T7 英文本人音樂 | 1 | 1 | 日文既有 write 承諾 |
| T8 英文兩個本人候選 | 0 | 0 | `ん、好みが複数あるな。今のはどれか教えて。` |
| T9 同值飲品 | 1 | 1 | 日文既有 write 承諾 |
| T10 同值食物 | 1 | 1 | 日文既有 write 承諾 |
| T11 無 scope 訂正 | 0 | 0 | `ん、前の好みが複数の種類に残ってる。どの種類を直すか教えて。` |

實際 row delta 與事前 gold 都是 `[0,1,2,0,1,0,1,0,1,1,0]`。
六個成功輪的固定日文回覆 6/6 exact；五個拒寫／澄清輪的可見
source-only 語義 5/5，無假 `覚えとく`。T8 未明說兩種茶、T11 未明說
`飲み物／食べ物`，語氣略制式；這是品質限制，不把它加成其他通過。

隔離 Chroma `user_profile` 共七筆、全部 `subject=user`：
`山桃茶/drink/like`、`桂皮茶/drink/like`、`山桃茶/drink/dislike`、
`黑芝麻糕/點心/like`、`ambient jazz/music/like`、
`ルバーブ/drink/like`、`ルバーブ/食べ物/like`。
T3 resolver 將舊山桃茶視為 historical；T9 後桂皮茶的 drink 正向列
為 historical；T11 前後同值ルバーブ在 drink、食べ物均 active。
六個禁入值都未成為 profile value 或 value 子字串。T11 的純文字
owner 預檢准入 `1`，但 typed writer 真實結果是
`ambiguous_extraction/old_value_has_multiple_active_scopes`、
`typed_write_not_completed`、delta `0`；同輸入／同 episode hash 的
legacy fallback suppression 為 `true`，沒有錯寫 `黒糖生姜`。

十一輪各有一個不同的持久 turn episode ID。最後 SQLite collection
`episodic_memory` 為 12 rows，多的一筆是本機背景 `EpisodicSummary`
（非額外使用者輸入），另有 `procedural_memory=1`、`wisdom_semantic=1`；
背景 wisdom 在 T11 未解 scope 訂正後仍寫了
`Userはルバーブが好き寄り`。它未改 profile，卻顯示本項尚未約束
跨層背景整理對未解訂正的處理；需要另設跨層記憶 gate，不可宣稱
「所有記憶層都沒有副作用」。故不能寫成「整個 DB 僅 11 筆」，
也不能說背景完全不寫。正式私有 DB
不在 launcher 可寫區；此次只保留隔離 root。

每輪 graph 有且只有一個新 truth node、`status=matched`，11/11
`utterance` 與 Safari/JSONL reply 一致，11/11 visible guard、session
turn 與持久 episode reply check 為 matched；五個拒寫輪沒有 P4-H
成功節點。然而 T1 的 `selected_plan` 角色錯歸已足以否定完整
plan/graph source-consistency。T2/T9/T10 的本人值也由 M32 選為
`deterministic_semantic_commit_m32` 而非 P4-H 記憶 act plan；final 和
writer 正確，但 plan authority 仍不是設計的單一來源鏈。

User wait 總和 `76.9982s`，最大 `13.2459s`，11/11 `≤20s`；
全產品 token／model calls／價格沒有可信的完整 ledger，標 `unavailable`，
不能把 overlay 0 額外 model calls 當產品零成本。

## 測試層級、限制與下一個必要修正

聚焦＋六組相鄰回歸在同一測試進程提高 soft FD limit 至 4096 後
`178 passed, 8 dependency warnings in 72.21s`；安全 launcher 0-turn
check 通過。macOS 預設 soft FD 256 的合併長套件曾因 Chroma client
檔案描述符耗盡而失敗，單檔及提高 limit 後通過；不抹去此環境限制。
無 Safari 人評、formal temporal holdout、同模型強 LLM 對照、VRM/tool
整體或完整人類反應方程式的授權。前項 source intent drift 與既有 owner
句末否認誤准入仍是獨立審查點；core 先寫 episode 後寫 profile 非原子，
DB 寫入失敗不能由此次修正事後修補已存 episode。

下一個最小、可歸因的同卡修正：在其他 M32/M33 規劃候選完成後、
`selected_plan` 與 prediction/action trace 固定之前，以同一已存
preflight source decision 重新裁決**選中**的 memory-act plan；
保留被 veto 的原候選與理由供追溯，不只事後覆寫 graph label。
新增 T1 型朋友來源的「selected plan 不誤歸本人」回歸與本人正例、
protected、非目標反例；先凍結**另造**未曝光的 source-only 產品資料，
再做一次隔離 Safari。不得修改本次 freeze、原始 raw 或結果，也不得
把此次 surface 11/11 改稱全面 PASS。
