# P4 後句本人否認：全新八輪 source-only 產品驗收草案

狀態：**開發者自製 prospective product probe；尚未 freeze／commit，0 本案模型、0 Safari 結果。**
此檔與 `datasets/p4_profile_postposed_self_denial_fresh_probe_2026-10-02.json`
只鎖事前輸入、來源語義 gold 與驗收規則，不是正式 holdout、真人評價或
同模型強 LLM 對照。新增 additive 程式與聚焦測試已先出現；最後一組
聚焦＋受影響相鄰回歸 `221 passed, 8 dependency warnings in 98.65s`
（FD soft 4096），獨立唯讀的原 owner／新 overlay 純函式 gold
八輪一致；這不是 Safari 或模型品質證據。新 launcher 0-turn check
exit 0、隔離 runtime、overlay／pre-writer hook 已核對；freeze 仍須在
任何本案 Safari／模型回合之前完成，不可把本草案當成
通過證據。

## 單一變因與資料新鮮度

依 `research/p4_profile_postposed_self_denial_plan_2026-10-02.md`，本案
只驗證 legacy profile writer **之前**的相鄰子句回溯：明確、肯定式的
後句本人否認，撤銷緊鄰的正向本人候選；保留原候選與否認來源 hash
於 audit，不產生 `dislike`，不清空後面獨立正例，也不修改先前已存的
row 或 episode。P4-I selected typed writer、舊 owner／ack／plan 本體、
來源送達及背景整理不是本次修改目標。舊八輪與十一輪的 PASS／FAIL
及 source `REVIEW_REQUIRED` 不改判、不重播追分。

建檔前在安全 worktree 執行
`rg -n --hidden --glob '!.git/**' --glob '!output/graduate_application_report/**' '蜜柑山椒茶|黒豆柚子飴|甘栗せんべい|月桃水|桜葉ソーダ|すだち麦茶|焙じ梅茶|roasted barley latte|芋圓豆花|真緒' .`，
exit `1`、0 hit。這只說明選用 actor／value 在當時的搜尋範圍內未出現；
句型受已知 before、設計卡與聚焦測試啟發，**不能冒充獨立、未開發
接觸的 holdout**。gold 由凍結前原句中的來源、指涉、語氣及既有
writer 契約標定，不讀本案模型回覆調整。

## 固定八輪與 source-only gold

空白 profile 起始。T1 本人句末否認 `蜜柑山椒茶`，零寫入；T2 同輪
否認 `黒豆柚子飴` 後另述 `甘栗せんべい`，只留後者；T3 指明作文
例文並否認 `月桃水` favorite，零寫入；T4 `真緒` 轉述相反意見，
不得用朋友的話撤銷本人先述 `桜葉ソーダ`。**T4 完成後真關閉舊
PID／port，以同一隔離 DB 的新 PID/session 重啟。**T5 後句是問號，
不是確定否認，保留 `すだち麦茶`；T6 否認字樣在引號內、且是作文
例文，保留 `焙じ梅茶`；T7 英文明示目前飲物偏好並要求記住，走
既有 P4-I selected typed write，保存 `roasted barley latte/drink`；
T8 中文直接本人喜好且無記憶行為請求，走 legacy，保存 `芋圓豆花`。
中／英／日輸入的可見答覆都應是自然日文。

逐輪新增 user-profile row 數固定為 `[0,1,0,1,1,1,1,1]`，最終
**恰六筆**，內容與 `preference_scope` 見 JSON：五筆 legacy row 的
scope metadata 欄位應不存在，T7 typed row 的 scope 應是 `drink`。
三個被撤銷值不可作為任何 `subject=user` profile value，連包含它們
的較長 value 亦不行；否認句不得另造 dislike。T1/T2/T3 的 audit
各有一個 `postposed_explicit_self_denial` veto，T4/T5/T6/T8 的
veto 數為零，T7 `path=p4_i_selected` 且不應有 postposed-veto 欄。
T1/T3 writer 不啟動，T2/T4/T5/T6/T8 legacy writer 回傳，T7
typed writer 完成。所有八輪仍各存一個不同的 `turn_episode`。

## 證據取得與成本界線

先由主工作者確認聚焦＋受影響相鄰回歸、隔離 launcher 0-turn check
及獨立唯讀審查；再將程式、測試、本 JSON、此 plan 與必要入口納入
**完整 SHA-256 manifest 與 freeze commit**，首輪前重算核對。本檔
尚未執行 freeze，不得事後改輸入、gold、門檻或程式來追分。只用安全
worktree、新 launcher-owned `0700` 系統 temp root、空白隔離
Chroma、單一新 Safari tab；不碰原始 dirty checkout、正式 DB、
既有 tab、`output/graduate_application_report/` 或外部部署。

以 `p4_postposed_denial_safe_isolated_product_launcher.py` 啟動產品
入口，T1–T4 逐字各送一次，保存 Safari 泡泡、原始 JSONL 與 graph；
停舊 server、確認 PID 結束及 port 已關，再沿用原 runtime root／DB
啟動新 PID/session，T5–T8 逐字各送一次。總計恰兩個 session、一次
預定重啟，**0 回答重試**。若額度、服務或 UI 中斷導致額外重啟、
漏輪、重送或改句，保留原樣程序 FAIL，不對已曝光題重跑追分。

逐輪留原始 input/reply JSONL、Safari 最終泡泡、時間／等待秒、
session/PID、`turn_episode` 真 ID、graph 的 `memory_updates`、
`profile_owner_admission_p4` 與 `utterance`，及 T7 真
`selected_plan`、logic、prediction、P4-H/I write truth。從 Chroma
唯讀查當輪前後 row **ID 集合差**與 metadata（`subject`、
`fact_type`、`value`、`preference_scope`、state），核對最終六筆；
不能只依 audit count、graph 或 raw 日誌聲稱實際寫入。對 veto
候選，以凍結原句與原 owner 決策重新計算 source/value SHA，核對
post-veto row 保留同一來源／值 hash、`owner=unknown`、
`admitted=false`、否認來源 hash 和原因。graph 不得洩出原句；
episode 可以含原句，但不可拿 episode 當 profile row。

逐輪 user wait `≤20s` 是獨立成本目標；記錄實測最慢、總等待及
可核對的 model call/token/價格。如全產品 ledger 不完整，標
`unavailable`，不能把此 gate 預期零**新增** model call 說成產品
零呼叫或零成本。原始 JSONL 與隔離 DB 證據保留 full SHA；測後停
server，隔離 root 留供覆核。背景 consolidation 如另寫 episode
summary、procedural、wisdom，逐層列來源與時間，不把 profile-only
正確冒充所有記憶層安全。

## 事前 strict gate

1. 八筆 exact input 各一次、0 retry；T4→T5 真 PID/session 重啟，
   同一隔離 DB；八個互異且持久的 turn episode。每輪 Safari final
   與同輪 graph `utterance` 完全相同。
2. 每輪 owner path、veto 數、candidate reason／owner、source/value
   hash、writer status／delta 與 JSON 相符；T1/T2/T3 只撤銷其緊鄰
   正向候選，不把否認提升為 dislike；T4 朋友歸屬、T5 疑問、T6
   引文皆不誤 veto。T7 走 P4-I selected 且不經 legacy veto；T8
   中文 legacy 正例不退化。
3. Chroma 實際 row ID 差、metadata 與逐輪 gold **8/8**，最終
   恰六筆，三個禁值及其子字串污染為零；重啟後持久狀態相同。
   若 graph、raw 與 DB 不一致，以真 DB 決定 writer 是否正確，
   另列 graph／log 不一致為產品 FAIL。
4. T7 真 `selected_plan` 的 intent/core 與現有 P4-H 契約相符，
   P4-I typed writer、logic／prediction、truth node、graph、可見
   日文同源；只有這一輪有可由既有 `AUTHORITATIVE_SURFACES["write"]`
   推得的逐字 final。其餘七輪**不鎖 exact final**，逐一按 JSON
   語義 rubric 判定自然日文、正確來源角色、否認／疑問／引文分界、
   不虛稱錯值已記住，且一般泡泡不露內部分析。正確 DB 不能抵銷
   嚴重可見語義或 selected-plan 不一致。
5. 每輪等待 `≤20s`；超時單獨記成本 FAIL，不用它寬免 writer、
   graph、日文或重啟 gate。缺 model/token/價格 ledger 就明列缺值，
   不猜測、不宣稱相對人類或強 LLM 的效益。

任何 strict 條件失敗，保存 frozen source、raw/hash、DB 與最早失真
位置；依設計卡至多兩個有根據修正批次，不能在本案重播或放寬判準。
即使 PASS，也只支持有界日文後句本人否認及所列非干擾控制在此
隔離產品路徑中的結果，不代表開放域理解、人評、正式 temporal
holdout、同模型比較優勢或 P4 全部完成。
