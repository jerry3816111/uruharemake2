# P4 關係問句：裸「好き？」的當輪問句證據

狀態：2026-10-16 設計先定案；尚未實作或進行新的產品驗收。這是
2026-10-02 後句本人否認產品批次 strict FAIL 後的一個**獨立路由修正**，
不回頭改該批 frozen 程式、八輪 gold 或結果。也不以本卡修復 T4 的
朋友來源、T6 的引文 scope、逐輪 profile row-ID 證據或全 graph 原句曝光。

## Before 與可反駁的問題

先前 Safari T1/T2/T5 對本人「喜歡某物」的陳述選到 `ask_like_me`，
給出「うちは你／使用者的好感」方向的回覆，和當輪來源語義不符；
T3 也有同類路由，另受舊 profile 記憶牽引。純規則 before 在相同
開發 worktree 可重現：`uruha_leftbrain_rules.contains_any` 與
`LeftBrain._contains_any` 對 `['好き？']` 都將
`私は紅茶が好き。`、`好き？`、`紅茶、好き？`、
`「好き？」は作文の例文。` 判成 true。對同四句，直接呼叫
`get_rule_based_plan` 與 `LeftBrain._rule_based_plan`（空 recent／
memory、現有開發依賴）所得 intent 也全部是 `ask_like_me`；
在一次性 Python 行程暫時將 extracted helper 置為空後，inline
`_rule_based_plan` 對同四句仍全部是 `ask_like_me`，確認不是只
重複測到 extracted 早退；
這是純規則 before，不冒充完整模型或 Safari。原因是 compact 比對同時
抹掉 cue 和輸入的 `？/ ?`，使 `好き？` 退化為 `好き`。
這是可觀察的 route attribution bug，不聲稱判得出真實私心。

## 單一核心變因與接線界線

只將關係路由 inventory 中的**裸 `好き？/好き?` cue** 改為須有
當輪、非引文、指向互動對象的問句證據；不改全域標點 compact
規則或其他安全／記憶 cue。無明示對象時，本卡高精度限定為
`好き？` 或精確呼語 `ねえ、好き？` 的同一問句；「某物、好き？」、陳述、引文、
混合多子句或目標不明的擴展句一律不由這個裸 cue 授權
`ask_like_me`。明示 `うちのこと好き`、`喜歡我/喜欢我`、
`like me` 的既有關係 cue 維持原路由，不用本卡重定義它們。
不確定時讓一般理解路徑處理，不因單一 `好き` 猜成關係確認。

同一判準必須同時覆蓋 `uruha_leftbrain_rules` 的 extracted rule
與 `LeftBrain._rule_based_plan` 的 inline fallback；只修其中一條
仍會錯路由。`get_rule_based_plan` 會先取 priority `scoped_input`，
混合句可能只把尾端 `好き？` 傳進 detector；因此判準必須保留
**完整當輪來源**，不能只看已裁切片段。既有 M42 於 import 時
各自 clone baseline/guarded rule；新接線必須對兩份 clone 採同一
裸問句判準，保留 M42 自身的 safety gate，不能只 patch module
global 而把本卡差異誤歸因 M42。安裝 preflight 應斷言 extracted、
inline 兩路由都受控，混合句仍有 full-turn evidence，M42 audit
不錯標本卡修正。沿用 additive 產品入口，在現有
`uruha_web_ui_product_p4_postposed_denial.py` 安裝完成後再安裝
本 scoped matcher；不修改已凍結的 M29–M32、P4-H/I/owner、
postposed writer、核心 brain 或舊 entry。可新增的實作檔為
`uruha_relationship_question_evidence_p4.py`、
`uruha_web_ui_product_p4_question_evidence.py`、
`p4_question_evidence_safe_isolated_product_launcher.py`、
`test_p4_relationship_question_evidence.py`；本卡的 fresh data、
freeze、結果另放 `datasets/`、`research/`、`analysis/`，並更新
`CURRENT_TASK.md`。若無法在 source-bound 當輪路徑同時控制兩處，
停下報 `REVIEW_REQUIRED`，不可只改最終泡泡或 graph 偽裝修復。

## 正負控制、驗收與成本

聚焦測試先驗兩條 rule path 和 current-turn actual signal：

1. `好き？`、`ねえ、好き？` → 裸問句授權；明示
   `うちのこと好き？`、`你喜歡我嗎？`、`Do you like me?`
   維持既有關係路由。
2. `私は紅茶が好き。`、`紅茶、好き？`、
   `「好き？」は作文の例文。`、`私は紅茶が好き。好き？`
   → 裸 cue 不授權 `ask_like_me`。後二者不能從引文／混合
   子句取走關係決策權。
3. 既有 `ask_miss_me`、annoying、protected route、P4-I selected、
   profile owner／write／episode、M31/M32 source 授權與 node graph
   的對應相鄰測試不得退化。舊已曝光 T1–T6 可作回歸，不計新分數。

先跑聚焦，再跑受影響的相鄰回歸；既有 FD soft 4096 是長套件環境
需求。新實作不應增加模型呼叫或新的持久 user fact；記錄局部路由
時間與真產品等待，不能在缺 ledger 時聲稱全產品零 token 成本。
離線通過後，**另造未曝光**的正負混合多輪資料與 source-only gold，
在首輪前鎖 exact input、路由／selected-plan 方向、可見日文語義、
writer/episode 非干擾、graph、跨重啟與 `≤20s` 成本條件，產生完整
SHA manifest、commit freeze；再於新 `0700` 隔離 root 和 Safari
各送一次、0 retry。任何已曝光或中斷案例不得重播追分。

strict route gate：負例不得選 `ask_like_me` 或給出無根據的關係
好感回覆，正例不能丟失原本的關係路由；真 selected plan、logic、
prediction、graph utterance、可見日文與當輪 evidence 不矛盾；
writer/profile/episode 非干擾，逐輪真 DB 與 row-ID 集合差須保存。
凡一條失敗就保留 FAIL、最早失真與成本，最多兩個有根據的修正
批次；仍失敗即 `REVIEW_REQUIRED`。即使這個 route gate PASS，
2026-10-02 全產品 FAIL、graph 原句邊界、T4/T6 source scope、
正式 holdout、人評及同模型 LLM 比較仍各自 pending。

只在安全 worktree、localhost、新隔離 DB 工作；不碰原始 dirty
checkout、正式私有資料、外部部署或無關
`output/graduate_application_report/`。此卡不新增網站或研究 M 編號。
