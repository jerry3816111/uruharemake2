# P4 來源綁定的簡單本人偏好 fallback：設計先定案

狀態：2026-10-16，**實作／新產品驗收前**。這是
`analysis/p4_relationship_question_evidence_interrupted_product_probe_result_2026-10-16.md`
的成本失敗後續；原六輪輸入、gold、結果、hash 永不改，不能重播舊輸入追分。
這是產品可用性修正，不是正式 temporal holdout、強 LLM 優勢或人類理解證據。

## Before 與可歸因變因

隔離 Safari T2 `私は昆布生姜スープが好き。` 的真 selected intent 是
`chat`，writer source admission/DB 正確，但 user wait `26.5627s`，
超過事前 `20s`。路徑先是 M29 `projection_required=true`、M33
`source_pattern_unavailable`，再是 M31 `12.8828s` 模型呼叫後因
`safe_casual_register_only=false` 拒權，M32 也未取得足夠 anchored
repair；最後的普通聊天 planner 模型呼叫 `10.3953s` 才選 `chat`。
M42 新問句稽核只 `0.0518s`，不是此次延遲主因。前批服務程序又在
Codex host 結束同秒消失，死因未定；這是另外的操作風險，不當成
語義／延遲根因。

**唯一核心變因：** 當原產品流程確實落入 LeftBrain 一般 planner
fallback 時，若完整當輪是唯一、日文、本人、肯定、來源准入的簡單
`〈我〉は〈任意物品〉が好き。` 陳述，從同一來源值建立自然的
`chat` acknowledgement rule plan；不再為這種已授權來源的句型
呼叫第二個 general planner。任何物品值皆可，不能白名單化
`昆布生姜スープ` 或寫本次題目。M31 的呼叫、拒權、source-first
guard、M32／M33、writer、問句 matcher、安全與人格流程均不變。
因此本修正**最多預期省去約 10.4 秒 planner**；對 M31 的
`12.8828s` 仍須付費，依舊數字估約 `16.2s` 僅為推算，不是
新產品結果。不得把 `completed_within_budget` 這個單一 planner
欄位當 end-to-end 通過。

## 授權與 fail-closed 邊界

- 重用目前產品已安裝的 `uruha_profile_owner_admission_p4`，包含
  postposed self-denial wrapper，做**純讀、無 writer 副作用**的
  `admit_legacy_profile_facts` 判定。完整來源須是單一子句／單一
  來源值，恰一筆 `like`、一個 admitted user decision，value 與
  source span/hash 相合；不得只因字面含 `好き` 就放行。
  表面語法上限先固定為 `私は／わたしは／僕は／ぼくは／うちは／自分は`
  其中一個前綴、1–24 字無空白或標點的物品 span、`が好き`、
  可選一個句號；整句至多 40 字，不能有額外前後文。這是有界
  grammar，不是物品名單。
- 引文、朋友／第三者、轉述、句末本人否認、混合或多子句、問句、
  否定、價值/人物歧義、明示「記住／更正」行為、保護性場景、
  非日文或超過界限長度全部保持原路。不能將 source admission
  推成使用者心理事實或提前宣稱寫入成功。
- 只在原 `LeftBrain.think` 本會選 general planner、且
  `force_general_planner=false` 的 reactive 路徑生效；原先已有
  grounded profile、M31/M32/M33 authority、低路、安全與明確
  desired-response 路徑保留優先權。回覆計畫用同一物品名、casual
  Japanese，不說「覚えた／覚えとく」，最後仍通過現有 language、
  persona、semantic/surface guards。保留原 `actual_signal` 為
  `chat`，graph 必須如實顯示 deterministic fallback、selected plan
  與最後 utterance；不為了看起來漂亮捏造獨立 M31 成功節點。
- 這是一個有界產品快路，**不是**解決所有中文／英文／日文一般聊天
  的延遲，也不是把 planner 和 verifier 融成單一模型的證明。若負
  例會錯拿記憶承諾或語義 guard，停在 `REVIEW_REQUIRED`，不加更多
  ad-hoc 特例。

## 允許檔案與驗收順序

允許新增一個 P4 additive fallback 模組、相稱的產品 entry／隔離
launcher、聚焦 tests、本卡的後續 source-only 新案例／freeze／結果，
以及 `CURRENT_TASK.md`；只准為接線作最小修改。不得改
`uruha_brain_mac.py` 的歷史 M31/M32/M33、原 writer、M42、
舊 freeze、正式 DB、原始 dirty checkout 或無關報告。

1. 先測純 eligibility／plan：至少三個不同物品的正例與朋友、引文、
   本人否認、問句、兩子句、負偏好、記憶明示、跨語與長輸入負例；
   false positive 為 0。用模擬 planner 證明正例一般 planner
   call `1→0`、負例保留原路；確認 plan 不承諾已寫記憶。
2. 再跑相鄰的 owner/postposed、question、M29–M33、M42 與 P4-H
   回歸；既有 failure 不洗白。真產品入口的 0-turn 隔離 preflight
   應通過，且不污染正式 DB。
3. 然後用**全新** developer-authored source-only 正負多輪案例，
   在送出前固定 exact input、路由/可見語義/DB gold、單輪
   `user_wait≤20s`、持久 episode、逐輪 profile row-ID 集合快照、
   graph 核對、模型 call/token/cost 可用欄位與重啟規則，
   SHA freeze 並 commit。長時 server 須有獨立的 exit/log
   控制，避免工作 session 結束就把「模型失敗」與程序故障混淆；
   這是驗收操作修復，不是模型變因。
4. 一次、0 retry 的新 Safari 產品 batch。嚴格路由與語義零錯、
   profile/episode/graph/日文逐輪一致、每輪等待 `≤20s` 才可
   稱此限定產品 gate PASS；成本若仍超，保留 FAIL 與原始 hash，
   不調門檻。raw token/價格缺值記 `unavailable`。沒有正式
   holdout／人評／強 LLM 對照不得外推。

兩個有根據的修正批次仍失敗，就保存最小反例、已排除原因和
可選取捨，標 `REVIEW_REQUIRED`；不要用更多小規則重跑已曝光題。
