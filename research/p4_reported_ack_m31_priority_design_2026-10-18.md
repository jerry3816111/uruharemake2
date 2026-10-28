# P4 第三者引述承接 vs M31 字面回覆：單變因設計審查

狀態：2026-10-18，同團隊、非獨立的**首輪新題前**設計。此文件不是實作、
新 Safari PASS 或正式 holdout。原 actor/scope 八輪與此前七輪的題目、gold、
程式凍結 SHA、raw 及 strict FAIL 均不改、不重播追分。

## Before 與因果位置

最近一次前瞻批次 raw SHA-256
`5402089aeec6902ce62d99908bdd8fa250086bd9f8db2857746804abac38f0cb`。
事前 T3 對第三者引述要求「不把引文當命令，並自然承接先輩說過的話」。
真 Safari 最終為 `先輩が先に確認してと言った`；`actor=third_party`、
`action=reported_check_instruction`、M25/M18 均 null，actor node 在 M25 前，
可見 utterance 與 raw 相符。這證明**上游來源辨識已改善，但最終行動失敗**。
最終 `selected_plan.surface_act=semantically_authorized_literal_topic_m31`，
不是 actor 層選的 `ack_reported_check_instruction_p4`；actor audit 如實報
`reported_instruction_ack_missing`。M31 `plan_applied=true`、10.8876 秒，
且其 own surface self-check 中 faithful/subject/predicate 為 false。

程式順序可核：`uruha_brain_mac.py` 先建 M29 literal candidate，再產生 M25
與 M18 決策；稍後 `apply_decision_to_plan`（現 opt-in actor wrapper 可選
reported-ack）→ `apply_literal_topic_projection_m29` →
`apply_semantic_authorization_m31`。後者在 `surface_authority=true` 時重寫
`intent/core_message_jp/response_mode/surface_act`，不考慮有來源的當輪
reported speech act；其後 M32/M33 與 final M31 surface commit 又可取得權限。
這個覆蓋是實際 T3 根因，不是再刪 M25 正則或只換最後一句可修復。

另有獨立 T7 失敗：不明歸屬句沒有誤觸 `calibrate_need`，卻因 M21 planner
9.5932 秒與 M31 semantic 10.7653 秒串行，M19 等待 23.4192 秒，超出
預先 20 秒。**本項不以 unknown 句為捷徑、不修改其路由或性能閾值**；
產品總 gate 仍須另外解決它。

## 唯一變因與保護理由

唯一產品變因是：在 M31 取得字面回覆表面權限**以前**，若同一當輪來源
已被既有 actor/scope typed gate 證明為「只是在報告第三者叫人先確認」且
符合 source-qualified reported-ack 的**准入條件**，則讓該**對話行動**先於 M31 的字面
重述；M31 模型不必為這個被承接的非任務引述額外執行。這是 speech-act
authority 的優先序，不是宣稱第三者引述的內容為事實、私人意圖或穩定偏好。
可見句只作低壓承接與開放澄清，不能假定引文是對 Uruha 的命令、也不
假定引文受詞是使用者。其他一般字面敘述仍由 M31 原路處理。

首選在新 opt-in overlay 包住現有 `LeftBrain.authorize_literal_topic_m31`
的入口；只對**整句單一引述報告**、既有 M25/P4-AT classifier 與 actor
scope 同時承認 `source_kind=third_party_report`／
`actor=third_party`／`action=reported_check_instruction`、
`assistant_request_authorized=false`、`additional_clause_observed=false`、
`selected_policy=null`、非保護情境，且 M29 candidate 的 `input_digest`
等於當輪來源雜湊時，回傳有明確 source/action proof、
`surface_authority=false` 的 M31 deferred contract。不新增 model call；
M32 的輸入也因而不會從被抑制的 M31 surface 生成另一個強制 commit。
此入口執行時尚未產生最終 selected plan，因此 certificate 只證明准入，
**不能**宣稱承接行動已被選中。之後仍讓既有 actor wrapper 選擇承接行動，並在 graph 最終核對
actor → M25/M18 → M31 defer → selected plan → utterance。

入口**不得**按單一題目全文、先輩一詞或回覆字串白名單放行；需對
有限但可替換的人物稱謂、引號內簡短「先確認」說法與報告動詞作
完整作用域解析，且無第二句、列舉、分號、另外請求、否定、受詞
衝突或未知來源。對解析不完整、M25/P4-AT 意見不一致、hash 不一致、
M29 已有其他優先 proof、memory factual/protected 路由，不改原行為。
不得全域停用 M31，也不得用本 overlay 改公開 persona、記憶寫入、
基礎模型、生成參數或其餘既有凍結入口。

選此早期交接點而非最終覆寫字串：後者會留下 M31/M32 語意權限與
selected action 不一致，可能使 pending/outcome 及 graph 假報成功；
也白花 M31 約 11 秒。新 contract 必須保留 defer 的來源、理由、
原 M29 digest 與 `model_call_completed=false`，final actor audit 不得
只因 `surface_authority=false` 就報成功，必須核 selected act 和真句。

## 前瞻驗收與失敗分支

1. 先於任何新 Safari 題，建與新前瞻句**不逐字相同**的零模型 fixture：
   第三者單句引述正例至少兩種說話者／報告動詞；引文後的直接助手
   回覆形式請求、獨立新任務、普通非引述第三者事實、使用者自行
   延後回覆、未知 `確認して`、否定、保護情境與 digest/contract
   汙染為負控制。對正例核 M31 不呼叫、M32/M33 無新表面權限、
   P4-AT/M18 不誤升級、selected ack 與 final 日文同義；負例原路不變。
2. 跑聚焦與受影響 M25／M29／M31／M32／M33／actor/P4-AT／source
   回歸，舊 freeze SHA 不變，compile/diff check。不得用已曝光 T3
   作新 pass 計分。若不能建立 source-qualified single-report proof，
   **停止實作**，回設計審查，不把任意 quote 當可跳過 M31 的許可。
3. 另立未曝光中／英／日新題與逐輪 gold（新引述正例、直接助手
   控制、self-defer、literal-topic 正例、unknown、混合子句），以及
   成功／失敗、≤20 秒、profile/episode/graph、成本與重啟程序。
   首輪前 SHA manifest、diff review、commit、push、核 PR #435 head；
   後只在新 0700 root 真 Safari 一次性輸入，0 retry，至少兩 session
   同 DB planned restart，逐輪存完整 profile digest 和 episode IDs。
4. **strict PASS** 需所有新輪自然日文、同一 bubble＝graph utterance、
   actor/M25/M18/M31/selected/final 同輪一致、負例不被新 overlay
   侵入、無來源事實性寫入、每輪 ≤20 秒、可稽核啟停與隔離。任何
   一輪或程序門檻失敗整批 FAIL，保存原件與原因；本項是該問題的
   第二個有理由前瞻修正批次，若仍失敗，標 `REVIEW_REQUIRED`，
   不再以換句/加小規則追分。T7 性能問題另卡，不能用通過窄報告
   句就稱整個 P4 達標。

即使 strict PASS，最多證明有限 source-qualified speech-act priority
在 opt-in 本機產品路徑有效；不證明一般 LLM 做不到語用理解、真人
被理解感、正式 temporal holdout、全域多語解析、Uruha 私人心理或
生物人腦方程式。
