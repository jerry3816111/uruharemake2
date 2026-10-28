# P4 profile 記憶行為的選中 plan 來源權限：第二個修正批次

狀態：2026-10-02 設計先定案，**尚未做新實作／新 Safari**。這是
`research/p4_profile_write_ack_truth_plan_2026-10-01.md` 的同卡第二個
有根據修正批次，不改第一次 freeze／raw／負結果；本批仍失敗即
`REVIEW_REQUIRED`，不可重播兩個曝光的產品案例追分。

## 真 before 與單一變因

第一次全新十一輪 Safari raw SHA
`73e5270525174444ce2a80b8ac458095f5440e7206e2c4cea3a6c1fc6d760352`
之 T1，owner 拒絕朋友傳話、profile delta `0`、final 日文拒寫，
但 graph `selected_plan` 和 `logic.intent` 是 M32 的
`deterministic_semantic_commit_m32`，core
`今は枇杷葉茶が好きであるんだね。`，錯把朋友值指向本人。
T2/T9/T10 本人正例 final/writer 正確，P4-H audit 宣稱
`plan_authority=true`，實際 `selected_plan` 仍由 M32 搶走。
原 truth node 的 `non_commitment_plan` 只排除明示寫入 intent，
所以沒有抓到這個 source-role／plan authority 分歧。

根因定位：M29 對 fresh／上一輪未連結的自足字面句提出 projection，
M31 canonical 在 T1 遺失朋友 actor，M32 的 plan 候選先於 P4-H
來源受限 rule plan 選中；表面 guard 之後才救回 final。
這個批次的**唯一核心變因**是「已辨識的明示 profile 記憶行為，
以 P4 owner／writer 同源的 plan 權限優先於泛用字面投影」。
不改 M29/M31/M32、P4-H/I/owner 的凍結本體，也不改大模型／資料／
評分門檻或既有 profile schema。

## 最小資料流與允許檔案

以新 additive overlay 包住 M29 candidate 入口：先讓舊 M29 產生候選；
只有候選真的 `projection_required=true` 且同一輸入的 P4-H 明示
memory act `selected=true`，才將泛用投影標記為
`superseded_by_profile_memory_act_p4` 並撤掉其 projection／surface
authority，保留原候選 status/reason/input digest 供 graph 追溯。
這發生在 M31/M32 建候選、plan 排序、prediction 與 selected-plan
graph 之前；後續走現有 P4-H plan／P4 owner preflight，朋友或不唯一
來源選 noncommit，本人選原 write/correction。protected low-road
仍較高權限，未選中普通聊天原樣。若 M33 或其他候選還能搶走，
後述 post-check 必須報 mismatch，不能事後把錯 plan 改名。

新 overlay 另在既有 profile truth node 的寫後 materialize 階段加入
`selected_plan_authority` 實際檢查：非 protected 的 selected act，
`logic.intent/core_message_jp`、**真正的** `selected_plan` blackboard
payload（恰一個）必須和同輪 preflight 的拒寫句或既有 P4-H
write/correction plan 一致；不一致使 truth node `mismatch` 並阻止
成功 UI 交付。這是驗收儀表而非回答路徑修復；不得只為了過關修改
graph 或放寬過去結果。既有 writer／episode／surface readback 繼續有效。

只允許新 overlay、相應 additive 產品 entry／安全 launcher、聚焦測試、
新 source-only dataset/plan/freeze/result 與 `CURRENT_TASK.md`；
不動前批 `759b88e` 凍結的檔案、過去 raw/result、正式 DB、
原始 dirty checkout、無關 `output/graduate_application_report/`。

## 成功／失敗、成本與產品驗收

- 最小負例：新朋友傳話在 fresh M29 projection 條件下，真
  `selected_plan` 不得誤歸本人，應為 profile noncommit；writer `0`、
  final 日文拒寫。新增故意錯 plan 反例，truth 必須 mismatch 而非
  `matched`。引文、報述、多本人候選與 stateful scope 歧義不得退化。
- 最小正例：P4-H selected 本人 write／correction 遇 M29 候選時，
  真 `selected_plan` 的 intent/core 與原記憶行為一致，writer
  真落盤、final 保留原日文承諾；不是只靠最後 guard 成功。
- 未選中一般句、protected route 不觸發新 M29 veto；保留舊
  P4 source、owner、language guard、graph、episode、VRM/tool 邊界。
  合約與受影響相鄰測試需通過；若 default 測試 FD 256 再耗盡，
  如實記錄並用測試進程上限 4096 交叉驗證，不把資源錯當功能成功。
- 測試通過後另寫**全新** actor/value 的混合 source-only 多輪資料，
  事前鎖 input、selected plan intent/core、profile delta、final、
  graph、兩 session 和成本；full SHA／commit 後一次隔離 Safari，
  各句 exact 一次、0 回答 retry、重啟同 root，檢查真 DB 與可見 UI。
  單輪等待 `≤20s`；overlay 不加模型呼叫，full token/價格若無
  可靠 ledger 記 unavailable。即使過關仍只是開發者自製有限產品
  案例，不是正式 holdout／人評／強 LLM 優勢。

本批 strict 只要一輪 selected plan、writer、final、graph、episode、
程序或可見日文不符即 FAIL，保留 raw/hash，不重跑曝光資料追分。
來源問答 intent drift、句末否認 owner 漏洞及 T11 後背景 wisdom
副作用是獨立 gate，不在本批同時修。
