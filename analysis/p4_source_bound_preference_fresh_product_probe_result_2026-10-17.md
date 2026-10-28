# P4 來源綁定本人偏好快路：五輪前瞻 Safari 產品 probe 的中止結果

日期：2026-10-17（Asia/Taipei）。**整批 strict FAIL；T1–T3 各一次，T4/T5 未送。**
這是事前凍結的 developer-authored 產品驗收，不是正式 temporal holdout、
同模型強 LLM 對照、人評或全系統完成證據。輸入、gold、20 秒等待門檻與
0 retry 保持 `datasets/p4_source_bound_preference_fresh_probe_2026-10-16.json`
及 `research/p4_source_bound_preference_fresh_probe_plan_2026-10-16.md` 原樣。
首輪前本層 SHA manifest 27/27、上層 11/11 核對通過；凍結 commit
`b03d3dd`。本次結果不回寫 gold 或覆蓋舊負結果。

## 實際產品路徑與結果

隔離 root：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-bt560czz`。
獨立 product process run `a96f71422d682c67`、PID 36294、Safari
`http://127.0.0.1:7894/`、session `20261017_022334_57384990`；
首輪前、接續 T3 前由 controller 驗同一 final Python PID、唯一 localhost
listener 與 HTTP 200。原始 `web_logs/conversation.jsonl` 恰三筆，
SHA-256 `42e31d6879f0a4875b0b505b5773c4d0553ec21a25bee563fb24b9905b6475d1`。
資料庫位於該 root 的 `memory_db/`，未連正式 DB；停止後
`chroma.sqlite3` SHA-256
`627b63f446ff914dcdc7167c88f7cb9317d0ff56e5603a6dbf2f4ef660b8073d`。
Safari 訊息泡泡、實際 node graph 的 selected／M21／utterance，與 raw
三輪逐一核對；三輪圖上 `utterance.reply` 均逐字等於泡泡和 raw 回覆。

| 輪 | 凍結要求與實際 selected | Safari 真回覆 | user wait | 結論 |
|---|---|---|---:|---|
| T1 | `chat`／`source_bound_preference_fallback_p4`，實際一致；圖上 fallback `selected_source_admitted_rule_fallback`，M21 deterministic、general planner model call=false | `普通に、黒豆きなこ餅が好きなんだ。いいじゃん。そのくらいでいいだろ。` | 26.6754s | writer／路由局部符合；**超過 20s，成本 FAIL** |
| T2 | 禁止 fallback／`ask_like_me`，實際 M31 `semantically_authorized_literal_topic_m31` | `小豆柚子羊羹、好きだね` | 9.4792s | 沒寫朋友偏好，但回覆省略「友達」，不能清楚保住第三人稱歸屬，**表面語義 FAIL** |
| T3 | 預期 `chat`／fallback，實際 M32 `deterministic_semantic_commit_m32`；圖上沒有 fallback node | `うちは青じそ梅せんべいが好きだね。` | 14.7039s | **selected 路由 FAIL**；「うちは」在此角色語境可讀成角色自身喜好，不能把本人來源表達判 PASS |

T1 的 `runtime_latency_m19`：ingest 13.3930s、cognition 11.2448s、
surface/writeback 0.7849s。隔離 Chroma stderr 確有 79.3MB ONNX
模型下載（進度約 11s），但缺逐 span 歸因；不能把 26.6754s 全部
歸咎下載或把熱路徑數字改當冷路徑 PASS。T2 M31 約 7.0s cognition；
T3 M31 `model_call_completed=true`、11.6307s 後 M32 接管，
M21 general planner model call=false 不等於全輪沒有模型呼叫。
完整 token／價格 ledger 不在 raw 可用欄位，記為 unavailable，不能報零。

## 逐輪持久記憶，而非 collection count 推測

`evidence/snapshot-before-t{1,2,3}.json`／
`evidence/snapshot-after-t{1,2,3}.json` 六個 0600、不可覆寫快照留在
同一隔離 root。`user_profile_rows[].id` 前後集合差為 `[1,0,1]`：

- T1 新 ID `e93fc85e-d3fa-463e-b852-31fd28b3cf30`，`subject=user`、
  `fact_type=like`、值 `黒豆きなこ餅`。
- T2 無新增本人 profile；朋友的 `小豆柚子羊羹` 未出現在該集合。
- T3 新 ID `79d5f27f-6b3d-4e99-8eb7-a888d460b198`，`subject=user`、
  `fact_type=like`、值 `青じそ梅せんべい`。

三輪各新增一個不同 `turn_episode` ID：
`b70241d2-8dec-455d-9e40-4c2cff511975`、
`b79afab8-ad4b-4a87-8929-efee6ea39bb0`、
`5c05f6d8-bc8c-4d14-800a-8912d05183c5`。
上述 profile 兩筆 metadata 均無 `preference_scope` 鍵。
原始快照 SHA 依序：before/after T1
`68da2b6638f10fed17afe9b5bfa6ce0e01c57bcdf88a704139e5a272a2619a7e`／
`92f86fec03424973cf146396abe592e04eeed476bbd287f123081cc31348fb03`；
T2 `92f86fec03424973cf146396abe592e04eeed476bbd287f123081cc31348fb03`／
`92467e67e9d2d6c09fbba0ba39dba94aad1854327b20b1bc45510d1316290268`；
T3 `92467e67e9d2d6c09fbba0ba39dba94aad1854327b20b1bc45510d1316290268`／
`6d63b4a0a4c997cf346c18f91941a02bd1b4d9ebefd5186cdc32be7fc528393b`。
這是 snapshot API 的 row-ID 查詢，不聲稱對 Chroma 進程外 DB bytes
具 OS 級唯讀保證。

## T3 後生命週期與不重送邊界

照事前計畫對同一 PID 呼叫 `stop` 一次。controller 的原始
`p4_preference_fallback_detached.a96f71422d682c67.stop-attempt-9e7ffdb0.json`
（SHA-256 `390567cdef434c1a8e508276d554c12f84328a169355945a6bbdca86f36c254b`）
記 `signalled=true`、`original_pid_exited=true`、`port_vacant=false`、
`planned_stop=false`、`process_or_port_not_clean_after_term`；沒有成功的
`stop.json`。之後 `lsof` 無 7894 LISTEN，`netstat` 看到舊 PID 的
127.0.0.1:7894 `TIME_WAIT`，而 controller 的 `_vacant` 是直接 bind
且未設 `SO_REUSEADDR`。這支持「可能把 TIME_WAIT 當不空」的診斷，
但沒有當下 errno／完整 owner 快照，不宣稱唯一因果根因。
controller 的同 root reuse 明確要求既有 `planned_stop=true` 與
`port_vacant=true`；本批沒有，故**不補寫成功紀錄、不重啟同 DB、不送
T4/T5**。三輪已曝光，不重播追分。計畫的兩個 session 與重啟後
持久性因此未驗，程序也 strict FAIL。Safari 專用頁可能因服務停止
顯示無法連線；其他分頁未關閉，隔離證據 root 保留。

## 定位與下一步邊界

T2 profile owner admission 正確拒絕第三人稱（0 row），但 M31
canonical 的 `subject_jp=友達` 沒進授權的 visible reply；其 anchor
checks 只核物品和 `好き`，M32 也未修復，M39 對這種省主語仍接受。
T3 source admission 也正確（+1 row），但 M31 成功授權、M32 先於
rule fallback 選中；因此本次快路不是對本人偏好穩定優先，不能用
T1 的一例 PASS 證明變因有效。T3 後人格表面又把 `私は` 實現為
`うちは`，現有 M39/frame shadow 沒報 role violation。

下一步需分開處理，不能一批混修：先以當前最核心的 **T3 selected-plan
競權**作新的單變因設計審查，保留 T2 主語／T3 表面角色、T1 冷啟成本
為獨立失敗；未來再啟同 DB 產品 probe 前，另外修正 controller 對
listener 與 TIME_WAIT 的安全判定並用無模型生命週期測試核對。
所有新產品驗收都須是未送過的 source-only case、事前新 freeze、0 retry。
本批對長期目標的貢獻是定位「記憶 writer 正確但 selected／可見表面
仍不可靠」這一真產品瓶頸；不證明全面理解、優於強 LLM、VRM／工具
整合、正式 M55/M56 或人類方程式成立。
