# P4 legacy profile：後句本人否認對前句候選的撤銷

狀態：2026-10-02 先定案設計；**尚未實作、尚未做新 Safari**。
這是前項 selected-plan authority 限定 PASS 後的獨立產品 gate，
不能拿已曝光八輪／十一輪追分。前項來源送達 `REVIEW_REQUIRED`
是另一問題；本 owner gate 尚未進入該停止狀態。

## 真 before 與產品危害

安全 worktree 的現有 `admit_legacy_profile_facts`：
`私は紅茶が好き。` 准入 `('like','紅茶')`，合理；但
`私は紅茶が好き。これは私の好みじゃない。` 仍准入同一 like。
第二句被原准入標成另一個 rejected dislike，並未撤銷前句。
獨立唯讀診斷在新臨時 Chroma／session（0 model、0 Safari）確認
`path=legacy`、admitted=1/rejected=1、profile delta=1，真
`subject=user/fact_type=like/value=紅茶` 持久化。根因是 legacy
逐子句即加入 facts，沒有以後續的明確本人否認回溯前一候選。
這種錯誤能跨重啟被當成使用者事實；不能用「最終回答聽起來自然」
掩蓋 writer 污染。此 before 只證明 bounded 日文反例，不推論所有語種。

## 單一變因、資料流與界線

唯一核心介入是**同一輸入內、相鄰子句的來源／極性回溯裁決**：
先讓凍結的 legacy owner 准入取得候選與原 audit，再在 writer 前，
僅當下一個非空白、非引文子句以有界日文形式明確說「這／那不是
我自己的偏好」或「上述句子只是作文例文、不是我的偏好」，且
能唯一指向緊鄰的正向 user 候選，才撤銷該候選的寫入權限。
audit 將原 candidate 轉成 rejected `postposed_explicit_self_denial`、
保留原 source/value hash 與撤銷原因；**不**把否認自動提升為
`dislike`，不消除對話 episode，也不修改先前 session／DB 的記錄。
若指涉不唯一、範圍超界、缺引號平衡或非明確本人否認，保持
unknown／原有 fail-closed 行為，不用模型猜心理。後句之後的新
獨立本人正向候選應可保留，不因一個否認清空整輪所有事實。

為保留已凍結的 P4 owner／ack／plan 對照環境，使用新 additive
產品 overlay 包住 `admit_legacy_profile_facts`（在舊 owner writer
執行前），再由新 entry／隔離 launcher 安裝；不改凍結本體或
過去 raw／freeze。實作允許檔案僅新增
`uruha_profile_postposed_self_denial_p4.py`、
`uruha_web_ui_product_p4_postposed_denial.py`、
`p4_postposed_denial_safe_isolated_product_launcher.py`、
`test_p4_profile_postposed_self_denial.py`；驗收另允許新
`datasets/`、`research/`、`analysis/` 本卡檔與 `CURRENT_TASK.md`。
不碰
P4-I/H/owner/M29–M32/core brain 的原檔、正式 DB、原始 dirty
checkout、無關 `output/graduate_application_report/`。若 additive
接線無法把 source-bound veto 用於真 writer，先停下報審，不可
事後只改 bubble 或 graph。

## 成功／失敗與測試矩陣

聚焦純函式與新隔離暫存 DB，至少固定下列 source-only 對照：

1. `私は紅茶が好き。` → 仍寫一筆本人 like 紅茶。
2. `私は紅茶が好き。これは私の好みじゃない。` → 紅茶 like 0；
   被撤銷候選／hash 可追，episode 仍保留，不自造 dislike。
3. `私は炭酸水が一番好き。これは作文の例文で、私の好みじゃない。`
   → favorite 炭酸水 0。
4. `私は紅茶が好き。これは私の好みじゃない。私は海が好き。`
   → 紅茶 0、海 like 1；不得全輪清空。
5. `私は紅茶が嫌い。` → 原本明確 dislike 仍寫；
   `私は紅茶が好き。「これは私の好みじゃない」は作文の例文。`
   → 引文不得錯誤撤銷紅茶。
6. `友達の灯里は花梨茶が好き。私は海が好き。` → 只寫本人海；
   普通非 memory-act 句、P4-H selected 句與 protected route
   均不得被此 legacy 專用規則誤接管。

測試要觀察實際 owner audit／writer、隔離 Chroma profile／session
與 graph/episode，不可只測正規表示式。先聚焦，再跑舊 P4 owner、
ack、plan 與相關來源相鄰回歸；沿用已知長套件 FD soft 4096
環境限制。失敗保留最小反例，至多兩個有根據修正批次；仍不通過
即 `REVIEW_REQUIRED`，不反覆加語句特例。

通過離線後**另造**未曝光、先鎖輸入／writer delta／profile 內容／
日文表面語義／graph／重啟／成本的新多輪產品案例與 full SHA，
freeze commit 後只跑一次隔離 Safari。strict 要求禁值零誤寫、
正例不退化、來源 audit 與 DB 一致、turn episode 保留、跨重啟
一致、可見日文不得反稱已記錯誤值；單輪等待 ≤20s。若背景
consolidation 獨立寫入，另列層別與來源，不冒充 user_profile
正確即所有層安全。即使 PASS 也只支持限定的 postposed denial
修正，不代表開放域人類理解、人評或同模型比較優勢。
