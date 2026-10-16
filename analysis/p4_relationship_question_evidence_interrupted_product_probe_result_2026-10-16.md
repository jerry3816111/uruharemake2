# P4 關係問句證據：2026-10-16 前瞻 Safari 產品 probe 結果

**結論：事前六輪 strict gate FAIL；僅有前兩輪的局部路由證據。**
這份結果不改 `research/p4_relationship_question_evidence_fresh_probe_plan_2026-10-16.md`
或原 gold，不把離線 31/31、相鄰 147/147 代替完整產品驗收。
六輪為開發者事前撰寫，不是正式 temporal holdout、同模型比較或人評。

## 事前條件與程序

- 新、舊兩層 source manifest 在首輪前分別核對 11/11、24/24；freeze
  commit `990b279`，當時 task/head `aa3695b`。產品由
  `p4_question_evidence_safe_isolated_product_launcher.py run` 於
  `127.0.0.1:7893` 啟動，launcher-owned `0700` 隔離 root 為
  `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-3_msivto`。
  原 PID `97499`；正式 DB 與原始 dirty checkout 未使用。
- 只在新 Safari tab 操作。T1、T2 各逐字送出一次，無回答 retry。
  T2 完成後，欲送 T3 時 Safari 出現「錯誤」且 T3 無新泡泡／JSONL
  紀錄；讀取時 PID `97499` 已不存在、`7893` 無 listener、原 exec
  session `70662` 回 `Unknown process id`。程序未做到事前規定的
  T3 後計畫重啟、第二 session、T3–T6；不額外重啟或重送已曝光輸入。
  **程序 strict FAIL。** 唯讀 macOS unified log 於 21:41:58.612 記錄
  Codex/ChatGPT host PID `87841` 因另一 Python PID `97778` 發出的
  SIGTERM 結束；21:41:58.698 記錄服務 PID `97499` client death。
  兩者時間相鄰，支持 host/session teardown 相關的假說，但沒有直接的
  `97499` signal/exit-status 或 traceback，不能斷言其確切死因、
  也不能據此替程式品質開脫。
- Safari AX 在 T1/T2 都看到最終泡泡；T1 曾以 CUA 即時顯示頁面截圖，
  但未保存持久截圖檔。兩輪 JSONL `assistant_reply`、runtime graph
  `utterance.reply` 和 Safari 可見文字相同；graph `selected_plan` 與
  logic/M42 actual signal/prediction source-plan intent 對齊。
  現有 graph 仍在 USER SIGNAL 顯示完整原句，而且新增問句 matcher
  沒有獨立 graph 節點；不能宣稱來源隱私或完整可視歸因已通過。

## 逐輪可觀察結果

| 輪 | exact input | 真 selected intent | Safari 最終日文泡泡 | profile 寫入證據 | 等待 |
| --- | --- | --- | --- | --- | ---: |
| T1 | `ねえ、好き?` | `ask_like_me` | `まあ無理ってほどじゃない。勝手に悪い方へ取るなよ。` | writer candidate 0；當輪後 profile collection 0 | 2.9856 s |
| T2 | `私は昆布生姜スープが好き。` | `chat` | `昆布生姜スープ美味しいね。` | writer candidate/admitted 1；最後 DB 有本人 `like/昆布生姜スープ` 一列 | 26.5627 s |

T1/T2 的路由與各自可見語義符合此限定案例的方向：問角色好感沒有寫成
本人偏好，本人說喜歡湯沒有被回成角色對人的告白；這不是 6/6 產品通過。
T2 `user_wait_seconds=26.5627` 超過事前每輪 `≤20` 秒門檻，
`runtime_latency_m19.target_met=false`；兩輪總等待 `29.5483` 秒、
最大 `26.5627` 秒，**成本 gate 亦 FAIL**。T2 走 `full_planner`，
`route_and_base_plan=10.4177` 秒、`cognitive_total=23.3802` 秒，
其中 planner 模型呼叫 `10.3953` 秒，後接 M31 source-first
semantic authorization 已完成的模型呼叫 `12.8828` 秒；M42 稽核
只有 `0.0518` 秒，不能把這次慢路徑歸咎新增的問句 matcher。
局部欄位同時有 `status=completed_within_budget` 與 `budget_met=false`，
不可只取前者作成本通過。模型總 token／價格沒有可核帳值，記為
`unavailable` 而非零。

唯讀 SQLite 最終核到兩個不同且持久的 `turn_episode` ID：
`127bb7cd-c7da-42ca-bdeb-6b06b82dd126`、
`89eeeb49-e898-40ae-9460-1666e63ff5af`；`user_profile` 只有
`01608600-8e17-42e9-b754-57ab5e6dec17`，metadata 是
`subject=user`、`fact_type=like`、`value=昆布生姜スープ`，
`preference_scope` 鍵缺席。T1 後查到 profile count 0，T2 最終 ID 1 筆；
但本批**沒有保存每輪前後的完整 row-ID/metadata 快照**，writer audit
又只有 count delta，不能以事後唯一一筆推成事前要求的逐輪集合差已證。

## 原始證據與後續邊界

- 原始隔離 JSONL 恰 2 行，SHA-256
  `0df86133054947032b4723a8e99dd250eae9872a6c5deb688e49921a91d09026`。
- 隔離 `memory_db/chroma.sqlite3` SHA-256
  `bdf1507936a9c24cc4845c443a3ba05ed02bd54ce375f4326183846c642df97b`。
  root 保留供唯讀覆核，服務已停止。
- 本批沒有 T3–T6、計畫重啟、跨 session 記憶、全六輪 profile、六輪
  自然日文或完整成本證據；不能對它們給分。舊 2026-10-02
  postposed-self-denial 批次 strict FAIL 仍不變。
- 此結果提示兩個獨立問題：真產品慢路徑在 T2 超預算；長時驗收的
  服務控制／逐輪 row-ID 快照不足。先分別查明，不能事後改六輪門檻，
  也不能重播六個已曝光 case 追分。問句 matcher 的完整產品結論
  保留 pending；是否開新前瞻 batch 須按工作流程設計審查並使用新資料。
