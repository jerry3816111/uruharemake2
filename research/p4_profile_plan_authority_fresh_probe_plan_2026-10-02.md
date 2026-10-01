# P4 選中 plan 來源權限：第二批全新八輪 Safari 驗收

狀態：**事前撰寫、尚未凍結 hash／commit，0 model、0 Safari 輪次。**
本批是開發者自製 prospective product probe，不是獨立 holdout、真人偏好
評價、同模型強 LLM 比較或正式 temporal data。舊十一輪
`analysis/p4_profile_write_ack_fresh_product_probe_result_2026-10-02.md`
的 strict FAIL、raw 和 freeze 都不改判、不重播。

## 問題、單一變因與資料新鮮度

前批 T1 表面拒寫與 profile 零新增是真的，但 M32 真 `selected_plan`
仍把朋友值當本人偏好；T2/T9/T10 也有 plan authority 名實不符。
本批只驗證 `research/p4_profile_plan_authority_repair_2026-10-02.md`
定案的同一修正：**已辨識明示 profile 記憶行為時，P4 owner／writer
同源的 plan 在選中之前壓過 M29 泛用字面投影**。不是在 writer 之後
單改泡泡或重繪 graph。P4-H/I/owner 與 M29/M31/M32 凍結本體、
正式 DB／既有失敗、source lookup、背景 wisdom 和 owner 句末否認
均不在本批修改範圍。

完整 source-only 輸入及逐輪 gold 在
`datasets/p4_profile_plan_authority_fresh_probe_2026-10-02.json`。
作者在寫入兩檔前，以 `rg` 對安全 worktree（排除無關
`output/graduate_application_report/`）查找
`璃帆|蕎麦蜜茶|柚香麦茶|金柑玄米茶|Norah|wild thyme tea|若晞|桂花酸梅湯|杏仁酥|lo-fi piano|lavender tisane|cardamom milk`，
exit `1`、0 hit；原候選「白桃烏龍茶」因在舊測試／研究文件
已有 hit，事前改成「金柑玄米茶」。這只證明這些 actor／value
未在當時 repository 出現，**不證明語法或機制未被開發者接觸**。
gold 依空白隔離 DB、逐句顯式來源及前輪應持久的資料事前標定，
沒有讀模型答案來調整。

## 固定八輪、來源與期望

順序不可變：T1 日文璃帆傳話（fresh-session M29 風險）拒寫，
T2 日文本人飲物 write，T3 日文同 scope 訂正，T4 英文 Norah
引述拒寫，**T4 後真 PID/session 重啟**，T5 中文本人點心 write，
T6 中文若晞對使用者的間接轉述拒寫，T7 英文本人音樂 write，
T8 英文本人兩個飲物候選拒寫並澄清。T6 是「朋友報稱使用者喜歡」
而非「朋友自己喜歡」；即使值的主體被說成使用者，來源仍不是本人
自述，因此不得提升為 `subject=user` 的已確認偏好。T8 是兩個
本人候選，不能誤稱第三人稱。中／英／日輸入最終均須為自然日文，
一般泡泡不露內部分析。

空白起始 profile 的逐輪新增 row 數固定為
`[0,1,2,0,1,0,1,0]`，結束共五筆；T3 產生新的金柑玄米茶
`like/drink` 與柚香麦茶 `dislike/drink`，原 T2 的正向柚香麦茶
由 resolver 視為 historical，不要求物理改寫 metadata。
T1/T4/T6/T8 保留對話 episode 但不得新增 user profile row；
五個第三者／歧義候選值亦不得夾在任何 user profile value 裡。
逐輪 `expected_selected_plan.intent/core_message_jp`、writer outcome、
日文 final exact、owner reason 已鎖在 JSON，不能看輸出後改成寬鬆
rubric。對拒寫／正寫皆同樣核對真正的 blackboard `selected_plan`
（恰一個）、`logic.intent/core_message_jp`、prediction／後續 surface
的來源立場，而非只讀 P4-H 宣告 `plan_authority=true`。

## 執行先後與可稽核證據

先完成 additive overlay 聚焦與受影響相鄰測試、launcher 0-turn
安全檢查、獨立唯讀審查。由主工作者將程式、測試、兩份本批資料
與門檻納入 full SHA-256 manifest，**freeze commit 在首輪 Safari
之前**；首輪前重算 hash。不能因這份草案已寫就稱已 freeze。
只用安全 worktree、launcher-owned 權限 `0700` 的新系統 temp root、
本機產品入口及一個新 Safari tab；不碰使用者其他 tab、正式
Chroma／個資或原始 dirty checkout。先驗空白 profile。T1–T4
每句 exact 一次、留 episode／graph 後停舊 server，驗證 port 關閉；
沿用同一 root／DB 用新 PID/session 起服務，再送 T5–T8 exact
各一次。必須恰兩個 session、一個預定重啟、0 回答 retry；若中斷
或偏離程序，保留原樣 FAIL，不重跑已曝光輸入追分。

每輪記錄 Safari 實際泡泡、送達時間／等待、input/reply JSONL、
session/PID、持久 episode ID、P4 owner/P4-I writer、M29 候選
pre-veto／post-veto、P4-H audit、真 `selected_plan`、logic、
prediction、utterance、truth node 與 graph 畫面。查隔離 DB 的
`subject`、value、scope、時間／resolver state 及 profile count
前後差；不能只依 log 或 graph 宣稱已寫。保存原始 log full SHA，
測後停 server 並保留隔離 root 供覆核。單輪等待 `≤20s` 是獨立
成本目標；超時記成本 FAIL，不把它事後拿來寬免來源／plan gate。
overlay 預期不新增 model call；產品實際 call/token/價格如無完整
ledger 標 `unavailable`，不可稱零成本。

## 不可改判的 strict gate

1. 八個輸入逐字各一次；T4→T5 真 PID/session 重啟但同一隔離 DB，
   恰兩個 session、八個互異且持久的 turn episode、逐輪 Safari
   final 與同輪 graph utterance 一致。
2. T1 的 M29 原候選需有 `pre_veto_projection_required=true`，其
   post-veto 是 `superseded_by_profile_memory_act_p4` 且不持有
   projection／surface authority；否則即使選中 plan 正確，也只能
   算「未測到本批介入的因果風險」，不可報修正成功。T1–T8 的
   真 `selected_plan` 恰一個，intent/core 與 JSON 精確相符；
   同輪 logic、prediction 的來源立場與選中方案不得相反。
3. 每輪 writer delta/value/scope 與 gold **8/8**；T3 resolver 舊值
   historical，其餘四輪拒寫沒有畸形 legacy fallback；profile
   最終五筆。保留 episode 不能冒充 profile 寫入；寫入成功的
   plan／final 才可保留原日文承諾。
4. 每輪 graph 的 profile truth node 恰一個，`status=matched`、
   `checks.selected_plan_authority=matched`，preflight、writer、
   episode、selected_plan、utterance、Safari 泡泡互相對應；
   不可只在 truth node 寫 `matched` 而實際選了 M32 錯 plan。
5. 八輪泡泡自然日文、對應來源角色，不將 T1/T4/T6 的轉述
   誤作本人確認，也不將 T8 的兩個本人值判作他人；未寫入不得
   假承諾。任一輪嚴重角色／語意錯、外語可見輸出或分析外露即
   產品 strict FAIL。

這是第二個有根據修正批次；任一 strict 條件失敗，保留 raw/hash，
依 `CURRENT_TASK.md` 轉 `REVIEW_REQUIRED`，不在本案例追改規則
或重播。通過也只支持有限的「來源約束 profile act 在真產品中
取得選中 plan 權限」，不證明普遍語用理解、相對強 LLM 的優勢、
真人被理解感、VRM/tool 完整性或人類反應方程式已求解。
