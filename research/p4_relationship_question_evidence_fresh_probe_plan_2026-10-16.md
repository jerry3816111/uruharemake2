# P4 關係問句證據：新六輪 Safari 產品 probe 事前契約

狀態：2026-10-16 首輪前定案；**尚未在 Safari 送任何一輪**。這是
`research/p4_relationship_question_evidence_plan_2026-10-16.md` 的
developer-authored prospective product probe，並非 train/dev 未接觸
的正式 temporal holdout，也不作強 LLM 比較或真人偏好證據。
`datasets/p4_relationship_question_evidence_fresh_probe_2026-10-16.json`
含六個 exact input、預期路由及可見語義，首輪前不得改字、改 gold、
降門檻。新用詞／完整輸入於寫入資料前在 repository 搜尋無命中；
這只表示未作為舊產品輪次使用，不表示開發者未看過。

## 已有下層證據，不代替本 gate

- Before：原 `contains_any(['好き？'])` 及兩條實際規則路徑對本人
  物品陳述、物品問句、引文與混合句錯選 `ask_like_me`；
  詳見設計卡，非模型／Safari 結果。
- 新 scoped matcher 的聚焦＋M42 相鄰測試，在加入完整產品入口
  隔離整合檢查後為 `31 passed in 23.78s`；該新增檢查於 full entry
  對七句正負例核 `LeftBrain._rule_based_plan`、
  `classify_user_signal` 與 M42 trace，**未**核真 selected plan；
  受影響擴大回歸 `147 passed, 8 dependency warnings in 116.09s`
  （測試進程 FD soft 4096）。這些只是離線機制／相鄰行為。
- 新安全 launcher 在 `check` 模式的一次 0-turn 隔離啟動前檢查
  exit 0：runtime reuse、overlay/M42 雙 clone/full-turn/inline
  preflight 為 true；沒有 server、模型 call 或 Safari 操作。
  這是入口接線證據，不是可見回覆證據。
- source-only writer 預檢在六句得到候選增量
  `[0,1,0,0,1,0]`，兩個本人 like 值分別是昆布生姜スープ、
  柚子豆乳；它不代替真 DB 的逐輪 row-ID 集合差。
  首輪是空白 session 的 `ねえ、好き?`，避免把上一輪物品當作
  裸問句的合理所指；中、英明示人際問句也與物品控制交錯。

## 操作與留證

在安全 worktree 首先建立 SHA-256 manifest 並 commit freeze；
新 manifest 包含新檔、M42／rules／M40 及前一份 24-file freeze
manifest 的 hash，首輪前須核對**新 manifest 與該舊 manifest 兩層**，
才算完整覆蓋本 entry 的凍結依賴。只用
`p4_question_evidence_safe_isolated_product_launcher.py`、localhost、
新 launcher-owned 權限 `0700` 的隔離 runtime root／空白 Chroma、
一個新的 Safari tab；不碰正式 DB、原始 dirty checkout、無關
`output/graduate_application_report/`、既有 Safari tab 或外部部署。
T1–T3 逐字各送一次；停舊 PID，確認 PID 退出和 port 關閉；同一
root／DB 啟新 PID/session，再逐字送 T4–T6。總計恰兩個 session、
一次計畫重啟、0 回答重試。額度、UI、服務或模型中斷造成額外
重啟、漏輪、重送或改句時，本批程序 FAIL，不用已曝光題補跑追分。

每輪留 exact input、Safari 最終泡泡／可取得的截圖、原始
JSONL/session/PID/時間、實測 user wait、真正 selected plan、logic、
prediction、M42 trace、graph utterance、writer audit、
episodic `turn_episode` 真 ID。**在每輪前後**從 Chroma 唯讀保存
`subject=user` profile row ID 集合與完整 metadata，核對集合差；
不能再只憑 collection count 推斷 ID-attributed 寫入。最終兩筆
profile 的 value/fact_type/scope、六個 episode ID 與跨重啟狀態
另核對；背景記憶若發生，逐層列出，不當成 profile。對 raw JSONL
與 DB 留 full SHA。可視圖須逐輪核對同一輸入／選中 plan／utterance
的連線和內容，不以節點存在就稱語義正確。此 additive matcher
目前沒有獨立的 question-evidence graph node；M42 的
`changed=false` 只證明不把新變更歸功 M42，**不是**本 matcher
決策已被 graph 直接記錄。產品歸因須合用 frozen input、無模型
source-only 重算與真 selected plan；完整圖像化仍列待補能力。

成本：每輪 `user_wait_seconds ≤20` 獨立判斷，記最大、總和與
路由附加時間；模型 call/token/價格由可核帳欄位記錄，缺值寫
`unavailable`，不可稱零產品成本。測後停 server，保留隔離 root
供唯讀覆核。

## Strict route gate 與失敗分支

1. 六筆 exact input 各一次、0 retry、T3 後真 PID/session 重啟且
   同隔離 DB；六個互異並持久的 turn episode；每輪 Safari 最終
   泡泡與 graph `utterance.reply` 及 raw `assistant_reply` 逐字一致。
2. T2/T4/T5 真 selected plan **不是** `ask_like_me`，不產生無據
   的對使用者關係好感回覆；T1/T3/T6 是 `ask_like_me`，保留明示
   或裸問句的關係回覆。各輪 `actual_signal`、M42 audit、logic、
   prediction、selected plan、graph 與日文回覆要同源且不矛盾。
   M31/M32 若在之後覆蓋成錯誤 selected plan，仍判 FAIL，不以
   底層 matcher 通過抵銷。
3. 逐輪真 profile row-ID 集合差須為 `[0,1,0,0,1,0]`，且只新增
   本人 `like/昆布生姜スープ`、`like/柚子豆乳`；JSON 的
   `preference_scope:null` 對 legacy writer 表示 metadata **無此鍵**，
   不是 DB 中真的儲存 null。不得自造
   `dislike/favorite` 或把關係問句／物品問句當 user preference。
   writer audit、DB、episode、graph 不一致也 FAIL。
4. 六輪最終回覆皆為自然日文，符合 JSON 的逐輪語義 rubric，
   不捏造私有心理、過去經歷或已記住不存在的事；一般泡泡不傾倒
   內部分析。單輪等待超過 20 秒另記成本 FAIL，不能寬免語義錯誤。

任一 strict 條件未滿，保存最早失真、raw/DB/hash 與成本，明寫
**FAIL**，至多一個有根據的同卡後續修正批次；不得改舊輸入／
答案或弱化控制。即使限定 route gate PASS，2026-10-02 後句否認
產品批次 strict FAIL 不改判；整張 graph 暴露原句、朋友來源和
引文 scope、來源送達 `REVIEW_REQUIRED`、強 LLM 公平對照、
正式 holdout、人評、VRM/tool 全交付仍各自 pending。
