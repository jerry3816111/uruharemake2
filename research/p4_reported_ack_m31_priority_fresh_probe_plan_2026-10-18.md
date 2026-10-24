# P4 第三者引述承接優先於 M31：前瞻真產品驗收

狀態：2026-10-18，首輪真 Safari 輸入前。單一產品變因是 opt-in
`uruha_reported_ack_m31_priority_p4.py` 的 source-qualified M31 defer；其餘
actor/M25/M18、M29、M32/M33、回覆人格、資料來源及正式 DB 不改。
設計審查與 before 見 `research/p4_reported_ack_m31_priority_design_2026-10-18.md`。
前批八輪 T3 與 T7 strict FAIL、其 raw/gold/程式凍結均不改、不重播。
新八句在 `datasets/p4_reported_ack_m31_priority_fresh_probe_2026-10-18.json`，
屬開發者事前自編、路由靜態核對過的產品題，不是獨立 holdout。

## 首輪前凍結

1. 聚焦 fixture 不可逐字等於新八句；需證明兩個不同第三方報告的 M31
   不呼叫模型、contract 有當輪 hash/source/action、`surface_authority=false`，
   且後續 M32/M33 不奪承接行動。混合請求、一般字面句、self-defer、
   不明歸屬、否定、保護 cue、hash/authority 汙染必須 fail closed。
2. 用真 opt-in 安裝鏈做零模型分類檢查；跑聚焦與受影響 M25/M29/M31/
   M32/M33/actor/P4-AT/source 回歸、新 controller `--help`、Python 語法、
   舊 actor 批凍結 SHA、diff check。不得以舊 T3 作新通過分母。
3. 在首次 Safari 輸入前凍結新 code、dataset、gold、計畫及 SHA manifest，
   commit/push 到既有 branch、核 PR #435 head。凍結後 0 retry、0 改題／
   改 gold／答案驅動修程式；若失敗，原件留存並標 `REVIEW_REQUIRED`。

## 隔離程序與逐輪證據

1. 只用 launcher-owned 新 0700 私有 root。先啟動 exact opt-in 入口作
   0-turn readiness：同 PID、唯一 loopback listener、HTTP 200；planned stop
   後 PID/group exited 與 port vacant。私有 ONNX 副本若需要，核官方 SHA
   後離線預熱，單列設施成本，不算生成品質。停機後由已驗證 setup helper
   建立 0-row `user_profile`，receipt 要綁 exact 新 entrypoint。
2. setup 後存 T0 的 `p4_profile_full_content_snapshot.py` 與
   `p4_preference_fallback_snapshot.py` 收據。Safari 真送 T1–T4 各一次；
   每輪立即存完整 profile digest、episode IDs、raw/graph 與當輪可見泡泡，
   記 M19 user wait、M21/M31 completion 及可信 token 欄位。T4 後同 DB
   planned stop/restart，以新 Safari session 真送 T5–T8 各一次；最後 planned
   stop。八個互異 episode、2 session、0 retry；server 出錯則停止送未曝光題，
   語義失敗仍可按已凍結順序跑完但不追分。
3. T2/T6 需可見 actor=`third_party`、M25/M18 無 direct request、M29
   candidate 的 input digest 同源、M31 status=`deferred_to_reported_ack_p4`
   與 proof、M31 model not attempted/completed、M32/M33 無新表面權限、
   selected act=`ack_reported_check_instruction_p4`、actor surface audit=
   `reported_instruction_ack_visible`、自然日文承接而非照引文下令。
   T1/T3/T4/T5/T7/T8 的新 M31 priority proof 必須缺席；混合請求與一般
   字面句保留其各自路由。所有輪 raw reply＝graph UTTERANCE＝當輪 Safari
   泡泡、無來源心理／記憶編造、日文自然、沒有對外技術分析；逐輪完整
   profile 內容 digest 與 setup 後一致。
4. 每輪等待 ≤20 秒。只報 raw 有的實際 token／call 數，缺欄位標
   unavailable，不能報成零。將 before T3 的 13.8276 秒／M31 10.8876 秒
   與新 T2/T6 延遲並列，但不同句、不同 session，**不是**受控同題加速
   因果估計；T7 的已知串行成本另卡，不因本項略過 quote 的 M31 而宣稱修好。

## 判定與界線

整批 strict PASS 需八輪／兩 session／同 DB restart／0 retry／8 episode、
所有事前路由與 final action/rubric、≤20 秒、泡泡＝graph、profile digest
不變、啟停與隔離均通過。任一失敗整批 strict FAIL，同時列出局部
source-qualified 機制的可核項。沒有操作錄影時，Safari 泡泡與 0 retry
只能報當輪目視，raw 只能獨立重算 logged reply 與 graph。

即使 strict PASS，只證明此有限日文第三方單句報告在本機 opt-in 產品路徑
中選對可見對話行動；不證明普遍語用理解、比強 LLM 好、真人被理解感、
正式 temporal holdout、完整 VRM/Function Calling，或人腦方程式成立。
