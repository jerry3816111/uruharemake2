# P4 reported-ack：M31 保護路由准入（A）

狀態：2026-10-18，實作與新 Safari 生成前定案。同團隊、非獨立設計審查；
前兩批 `REVIEW_REQUIRED`、題目、gold、raw 與 SHA 原封不動。本項只改
「已有完整第三者來源證明時，M31 可否 deferred」的准入，不修 selected→
visible 的日文表面失真（B），也不修 unknown 對象／延遲（C）。

## before、可反駁機制與單一變因

已曝 raw `ab52412deaf05e1e5fa9dce08e4d94beb9b4b88ccfbbe5c86061500d044c553d`
中，T6 的 `actual_signal.seed_plan` 為 protected，route=`low_road`、
M22=`safety_sensitive`，舊 `uruha_reported_ack_m31_priority_p4.py` 因只見
M25/P4-AT/M29 來源證明仍使 M31 `deferred_to_reported_ack_p4`。T2 是
`chat/casual`、`high_road`、`general_conversation`，但最終回覆仍因後段
guard fallback 失去承接；A 不得將 T2/T6 重計新 pass。

新 opt-in 在 orchestrator 主要 M31 呼叫點顯式提供同輪 seed、route、M22
與 factual grounding context；只將選定的路由標籤／digest 寫入稽核，不保存
整份 context 或原文。只有 context 完整且一致、
seed=`chat/casual`、route=`high_road/deliberative` 且無 protected intent／
hijack、M22 是沒有其他候選或衝突證據的
`general_conversation/existing_guarded_router`、無 grounded profile，並且
舊 M25/P4-AT/M29 當輪 digest/source/action certificate 也通過時，才准許
舊 deferred contract。缺欄、來源 digest 不合、protected、factual/memory、
correction、低路或證據矛盾，一律調用原始 M31，不做新模型捷徑。
另一個無 context 的後期 semantic repair M31 呼叫亦須回原始 M31，不能
偷用舊優先序 wrapper。保留 M31 原 contract status，在其內附 raw-free
准入稽核，供既有 blackboard／runtime node graph 展開。不得用 ambient
state、寫事實性 profile，或從路由推斷第三者私人心理。

允許改：`uruha_brain_mac.py` 的主要 M31 呼叫點一個可選 hook、全新
`uruha_reported_ack_route_admission_p4.py`、新 opt-in web 入口與 controller、
聚焦測試、本計畫／新資料／結果／`CURRENT_TASK.md`。舊 priority overlay、
前批 dataset/gold/SHA、正式 DB、預設入口、原始 dirty checkout 不改。

## 分層判準和資源

1. 零模型：一般 source-qualified report 可 defer，原 M31 0 call；低路、
   protected seed、M22 protected/factual、矛盾／缺失 context、篡改 digest
   或混合直接請求均不 defer，原 M31 恰 1 call 且參數不變。預設非 opt-in
   主呼叫與後期無 context 呼叫保持原始行為。至少覆蓋 M25/M29/M31/M32/
   M33/actor/P4-AT 相鄰回歸、語法和 controller help。精確命令：
   `PYTHONDONTWRITEBYTECODE=1 .venv/product_checks/bin/python -m pytest -q -p no:cacheprovider test_p4_reported_ack_route_admission.py test_p4_reported_ack_m31_priority.py test_p4_temporal_actor_scope.py test_p4_at_executed_action_outcome_closure.py test_semantic_authorization_m31.py test_semantic_commit_repair_m32.py test_source_semantic_atoms_m33.py test_generalized_literal_topic_projection_m29.py test_p4_reported_offer_source_scope.py`。
2. 首輪真生成前凍結全新 `datasets/p4_reported_ack_route_admission_fresh_probe_2026-10-18.json`
   的順序、逐輪條件式 gold、code、計畫與 SHA，commit/push 並核 PR #435。
   開發 fixture 不得逐字使用新八題；凍結後 0 retry、0 題目／gold／程式
   追改。這是開發者自編產品題，不是正式 holdout。
3. 隔離 localhost 0700 root；exact opt-in 入口先 0-turn readiness/planned
   stop，再離線私有 ONNX 預熱與 0-row profile setup。真 Safari 兩 session、
   T4 後同 DB planned restart，各題一次；8 distinct episodes、profile
   full-content digest 逐輪不變。每輪核 source proof、seed／route／M22、M31
   准入與 model call、selected/final、raw reply＝graph UTTERANCE＝目視泡泡，
   日文 guard、無私人／記憶捏造。若未實際遇到某路由，該 runtime 路由
   保留未覆蓋，不能拿 unit 代替。
4. A 的嚴格子門檻：至少一個真正 high-road 完整報告准入、至少一個有
   certificate 的 protected/low-road 報告拒絕，其餘 8/8 符合凍結條件式
   判準；每輪使用者等待 ≤20 秒、0 新 profile 事實、圖／泡泡一致、隔離
   啟停正確。記完成的 M21/M31 呼叫、真實可用 token 與延遲；缺 token
   欄標 unavailable。最多一個新八輪首發批與有根據的單一修正批，仍失敗
   則 `REVIEW_REQUIRED`，不以已曝光句追分。
5. A 即使通過，reported-ack 最終可見品質仍可能 FAIL；不得聲稱 P4
   產品、同模型 LLM 優勢、人評、temporal holdout、VRM／Function Calling
   或完整人類反應方程式已通過。下一項 B 必須另立前瞻表面忠實度卡。

回退：卸除新 opt-in 入口／不安裝 hook 時，預設入口語義不變；A 新入口
任何缺少 context 的呼叫 fail closed 回原 M31。舊批不改，結果正負都保存。

## 首輪前靜態檢查（非生成、非產品驗收）

設計時曾發現最早自編的「先に日程を確認して」與「まず資料をチェックして」
不能得到既有 actor/action certificate，故在任何 model/Safari 輸入前改為
完整語法內的新句；沒有看輸出後追改。2026-10-18 真 opt-in classifier
鏈的 8 題靜態 certificate 與事前欄位一致：T1/T2/T5/T7 `true`，其餘
`false`。無模型的 seed 預覽：T1/T5 預設 `chat/casual`，T2/T7 的
`言ってた` 被既有過廣 false-premise cue 判 `hallucination_safe/boundary`。
這只證明控制題設計有機會觸及兩側；runtime 的 route、M22、M31 與
visible 都仍須真 Safari 核對，過廣 cue 本身不在 A 放寬。
