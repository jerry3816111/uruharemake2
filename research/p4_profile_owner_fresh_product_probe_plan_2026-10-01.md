# P4 本人 profile 准入：前瞻十輪 Safari 產品驗收

狀態：事前設計與 source-only gold；開發者自製產品案例，不是正式 sealed
holdout、真人被理解感評分或強 LLM 公平比較。唯一核心介入是
`research/p4_profile_owner_admission_plan_2026-10-01.md` 已定案的
**新 `subject=user` profile 寫入來源／owner／引文／極性准入**。
舊 `凪紗／ルイボス茶` 案已曝光且來源送達 strict `0/1`、`REVIEW_REQUIRED`，
不得重跑，也不得藉本案改其結論。

## 新資料與事前答案

十筆 exact input、逐輪新 profile gold 在
`datasets/p4_profile_owner_fresh_product_probe_2026-10-01.json`。
建檔前 `rg` 對本案所有人物／偏好／活動 exact 字串在 repo 中為 0-hit；
這只是新開發資料，不是未參與設計的 holdout。T1 是使用者**轉述**朋友
灯里自己說最愛花梨茶；既不是使用者偏好，也不是系統直接證實朋友
真的這樣說。T2／T6 的朋友與本人順序相反；T3 是引文否認後有另一句
本人喜好；T4「不是最喜歡」不可變成正向 favorite 或推定 dislike；
T5 是日文省略主詞的本人偏好；T7／T8 保留既有 scoped typed write
與 correction。凍結前的獨立反例審查另發現 P4-I 可誤收朋友傳話，故
T9 用新值「黒豆麦茶」作為第三者傳話 selected-path 負例（加入前
repo exact 0-hit）；T10 問 T1 來源，要求真 episode ID 送達，僅要求
**實際通道**而不要求 `bounded_source_lookup`：該通道的獨立因果 gate
仍未通過，不得混在這項中改判。

## 凍結、執行與成本

先完成產品程式、聚焦＋相鄰回歸與 launcher `check`。再提交本計畫、
dataset、產品入口、overlay、launcher、測試及 freeze manifest；首輪前以
manifest 核對**完整 SHA-256**。後續不改輸入、答案、門檻或程式，也不
回答重試。只在安全 worktree 使用 launcher-owned `0700` 系統 temp root，
`p4_profile_owner_safe_isolated_product_launcher.py run --python
.venv/product_checks/bin/python --port 7892 --preserve-runtime` 開本機服務，
Safari 新 tab exact 送 T1–T5。停止舊 process 並驗證 port 關閉，再以
`--runtime-root <原隔離 root> --reuse-runtime --preserve-runtime` 重新啟動
同一隔離 DB，記新 PID/session，送 T6–T10。不得碰原始 dirty checkout、
正式私有 DB、既有 Safari tab、外部部署或付費 API。

每輪記 Safari 最終可見句、等待秒、session/PID、JSONL 原樣 input／reply、
持久 episode ID、同輪 graph `profile_owner_admission_p4`、memory writeback
及 `utterance`。每輪 `≤20s` 是獨立成本目標。若全系統 model calls、
tokens 或價格無可靠完整欄位，記 `unavailable`；不能把 gate 額外零
model call 說成全產品零成本。保存隔離 JSONL hash 與持久 DB 唯讀查詢，
測後停止 server，保留隔離 root 可覆核。

## 不可事後放寬的判準

**Writer strict**：十輪 profile 新增與 dataset 的逐輪 source-only gold
完全一致。T1/T4/T9/T10 零；T2/T3/T6 只保留本人 exact 值；T5 保留
省略主詞；T7/T8 的 `drink` positive、歷史與 explicit negative 按既有
typed 契約保留，不能改走 legacy 重複寫。十輪 episode 各有不同的
持久 ID，profile 拒寫不能刪 episode。T5 與 T10 用持久 `user_profile`
metadata／resolved state 查核；**重啟後空 session snapshot 不代表
持久污記憶已消失**。朋友、引文和 T4 否定值不得有 active
`subject=user` profile；歷史 T7 positive 不應仍為 current active。
圖上 admission 的 hash／owner／reason／count 與當輪一致，不含私人原句；
`profile_collection_count_delta` 只稱資料庫總數差，不冒充新 row ID 的證據。

**產品完整性 strict**：Safari 10/10 exact inputs 各一次、10/10 完整
final＋graph、graph utterance 與最終可見句一致；T5→T6 是舊 process 真退出、
新 PID/session、同隔離 DB。T10 的 T1 ID 必須出現在當輪實際 delivered
source trace；來源 actor=灯里、value=花梨茶，日文可見句明確是使用者先前
轉述她說，不把偏好歸使用者或說成世界真相；route、plan、graph、reply
同一來源。只回「不知道」為 partial、strict FAIL；即使答對也不能推翻
獨立 `bounded_source_lookup` 因果 strict `0/1`。

逐輪另列日文自然度／語義／人格瑕疵與 latency，不用 writer 正確掩蓋。
任何 strict 失敗保留原樣、定位最早失真；至多兩個有根據修正批次，
已曝光題不重跑追分，必要時 `REVIEW_REQUIRED`。本案即使通過，僅支持
這個限定產品 gate；不證明普遍語用理解、真人偏好優勢、同模型公平
對照、正式 temporal holdout、VRM 或 Function Calling 已驗收。
