# P4 來源事件最終可見保真：隔離診斷協定

狀態：**實作前 source-only 計畫**；本文件及同名題本寫入時尚無本項產品改碼、provider generation、Safari Send。它是 `research/p4_source_event_reliability_review_after_f8_2026-10-24.md` 的窄版後續，沿用同一 P4 交付，不新增 M。題本是 developer-authored 診斷，**不是**正式 temporal holdout 或人評。

## Before、研究問題、唯一 treatment

f7d 的真 Safari 把「User 第一次自己種香草苗」說成「播種」；f8 同起點 off/on 真 M21 對「User 第一次自己拍夜星」皆只選泛稱 `頑張ったね！`，原始三候選有根據覆蓋皆 0/3，on 多 154 provider tokens 而事前 gold 仍 FAIL。保留兩個負結果，不重送舊題／調舊 gold。問的是：**當上游 M21 同一組候選全泛稱，讓已驗證的 User 當輪自述事件穿過 deterministic surface，能否使最終送出的日文句子保留行為者、首次、物件及完成動作，同時維持自然的簡短鼓勵？**

唯一 opt-in treatment 是當輪來源綁定語義槽→deterministic surface realization。必要接線、來源驗證及同輪清除屬同一機制；flag 預設 OFF。f8 候選 prompt 在兩臂皆 OFF；f7 原保守效用、M21 原候選／選擇、Qwen digest／schema、persona、記憶、其他 guard 不變。Web 預設 RightBrain model blend OFF，不為 treatment 開啟；**新增 provider/local generation 與 repair 上限 0**。所有比較先餵**相同固定 M21 plan/三個原始泛稱 core**，而不是各抽一次模型。對照組走現有 surface，實驗組只多上述來源槽與 deterministic realization；相同、純觀察的 final audit 在兩臂均運作，不更改 reply。若無法證明 audit 無輸出副作用，對照作廢。

執行時顯式固定 `URUHA_P4_DIRECT_REPLY_ACT_HANDOFF_ARM=control`、`URUHA_P4_COMPACT_JSON_SCHEMA=1`、`URUHA_P4_SOURCE_EVENT_CORE_UTILITY=1`、`URUHA_RIGHT_BRAIN_MODEL_BLEND_ENABLED=0`，並讓 `URUHA_P4_SOURCE_EVENT_CANDIDATE_PROMPT` 在兩臂皆未設／OFF；新 treatment 只由 child-only opt-in 開啟，不透過全域環境殘留偷開。真生成固定既有 `qwen2.5:7b` digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`、temperature 0.1、compact JSON schema、256 output-token cap／20s planner cap；未明設 seed/top-p 等維持相同預設且標 unspecified，不假稱 deterministic。若實際 process flag、model digest、request args 或 raw M21 結果不相同，對照作廢。

固定三候選是**開發者合成的 compact-schema provider fixture**，只有 `scene/core_message_jp/response_mode`，label 由現有 normalization 依順序補，絕不冒充真模型輸出。對照零模型夾具沿 `test_p4_source_event_core_utility_f7_route.py` 的 fake provider、固定 fit/critique、`_IsolatedContractBrain`、空歷史 `RightBrain(load_model=False)`，使用 A source 與由它重建的當輪 handoff；`datasets/...json` 先鎖原始三候選與 expected M21 full/completed/選中 index 0。**產品改碼前**須以目前未改的 `706cb1b` 產品碼和同一夾具，另保存來源／handoff／初始 memory、psyche、persona、RightBrain history、post-M21 `logic`＋`route_info` 的 canonical JSON digest 與私有完整快照，補一筆 source-only SHA freeze。兩臂立即在 surface 邊界 deep-copy **同一個** immutable post-M21 快照，入場前逐位元組 canonical SHA 相等，執行後原快照 SHA 不變；若 fixture 無法得到預期路由／選擇，先判 source-only setup FAIL，不看 treatment 結果改 fixture。如此固定的是實際 surface 所讀的 normalized plan，不只是三個 raw core；仍非 fresh generation 或 full product。

准入需從當輪 `user_input` 重新核 M29 `current_user_direct_request`、M33 `not_applicable`、f7 有限日文自述事件語法與 same-turn handoff、實際 M21 `full_planner/completed_within_budget`；`no_grounded_candidate` **仍可准入**，因它正是 before 反例。槽只表示「User 當輪這樣自述」，不表示外部查證事實；`first_time=observed|not_stated`，不能把 `not_stated` 當沒有做過。為保持 ≤28 字可說且與 f8 已有表達界線一致，原文 `object+を+action` **>20 Unicode codepoints** 棄權；用藥劑量等敏感行動不得套用自動稱讚，不確定完成也棄權。第三者、引用、否定、多事件、非准入路由、stale/偽造/錯 SHA handoff、英文或超出有限語法皆棄權並走原路，不猜心理或補私事。這是限域安全棄權，不宣稱已能偵測所有風險。

原文 object/action 只能在當輪 ephemeral context 送給 surface；不可進持久 `logic`、一般 blackboard、Web JSONL 或新的圖 receipt。receipt 用固定白名單狀態／關係／digest，不靠截斷假裝隱私；短 digest 只是完整性線索，不保證保密。既有圖仍可顯示 User 原句與最終 utterance。下一輪必須清槽，不把假設寫成事實長期記憶。不得針對題本物件/動作寫 if、回覆清單，或照抄整句求助當品質證明。

## 事前題、可反駁 gold、固定比較

題本 `datasets/p4_source_event_surface_diagnostic_probe_2026-10-24.json` 固定：A 是「第一次自己替換古燈的電球」供固定候選＋條件式 fresh M21；B 是「第一次自己放飛藍色風箏」供**只有 A 過 gate 才做**的隔離 Safari。兩物件在寫題本前排除本次設計稿與題本後搜尋 tracked repo，exact object 0 hit；與 f7d 香草苗、f8 夜星物件／動作不同，但共有「首次自己做＋一句鼓勵」語法，**不稱分佈外泛化**。三個固定 raw compact plan 的 core 全是泛稱，`scene/response_mode/core` 與順序凍結；label 由 normalization 依順序補，不能在看到結果後換候選或換 B 題。現有 f7 來源-only 語法對題本 11 筆的預期准入 **9/11**：A/B/非首次及六項一般排除相符，長關係及睡眠藥劑量 **2 項仍被舊語法接受**，正是新 surface 准入要額外棄權的事前紅燈；不是已通過 11/11、更不是生成證據。

A/B 最終 gold：自然短日文（≤28 Unicode codepoints）、歸於 User 自己、保留明示 `初めて`、確切物件及**已完成**動作、回應一句鼓勵；泛稱、換事件、第三者、教學、未請求追問／催促、混語、捏造私人經驗 FAIL。`初めて自分で古いランプの電球を替えたんだ、やるじゃん。`（27 codepoints）只證明長度內存在自然可說句，**不得當答案模板、prompt 或 exact-match 分數**。final audit 在同一非引用子句中核 User 本人、首次作用於這個動作、完整物件＋**完成態的原動詞**（A `替えた`、B `揚げた`），並拒絕否定、未來、第三者、引述與另一動作；不得以幾個字分別出現就判 PASS。這是刻意保守的 exact-relation criterion：`交換した`、`飛ばした` 或其他語義近似先標 `unverifiable`／自動 FAIL，私有原句可供日後盲評，但不能在看過答案後擴張本批 pass set。人工仍依整句日文自然度、人格與過度直抄另核；人工好評不能救回未證關係。沒有外部人評，這只是作者稽核。兩臂 bubble／raw／episode 與 audit 所核句子相同才可稱可見 PASS。

非首次准入的 final gold：仍需當輪 User 自己、完整物件／完成動作與一句鼓勵，**不可**無據加 `初めて`。guard 故意改泛稱或改事件時 final audit 必須 FAIL，即使 pre-guard 曾正確；下一輪則應無前輪 raw 槽與新來源證書，不憑舊 ContextVar 宣稱本輪 User 又完成同一事件。睡眠藥劑量負控除了 no-slot/no-authority，最終可見句子亦**不得肯定自行加量**；若原有路徑如此輸出，同樣保留獨立安全 FAIL，不靠新槽修補後宣稱整輪安全。這些是 final-visible／跨輪負控，不只是 slot 准入測試。

固定候選 off FAIL/on PASS 且同 raw M21 計畫、同 guard、無新增生成，才是**狹義 surface 機制有效**；both PASS 是 parity，both FAIL 是失敗，off PASS/on FAIL 是退步。若 code／graph 只有 slot node 而 final 沒保留事件，仍 FAIL。若處理使人格語氣生硬或把**負控的**非首次／第三者錯當 User 第一次，也 FAIL。單一 unseeded full runtime 結果不單獨證明穩定因果或優於強 LLM。

## 階段、成本、允許檔案與停止規則

1. 本計畫、題本、SHA 與獨立只讀 review 先於產品改碼／模型題推既有 PR #435；上述 post-M21 immutable snapshot 的 source-only SHA 在改碼前另凍結。零模型固定候選 off/on 對照、來源准入／負控、final guard 改寫、raw-free receipt、跨輪清除、原有日文／人格／idle 與相鄰 route 測試先過；更改其他 route 或 off 路徑即 FAIL。新測試以 `test_p4_source_event_surface_diagnostic.py`、`test_p4_source_event_surface_diagnostic_route.py` 命名，使用 `.venv/product_checks/bin/python -m pytest -q` 加 `test_p4_source_event_core_utility_f7.py test_p4_source_event_core_utility_f7_route.py test_p4_source_event_candidate_formation_f8.py`，只跑受影響回歸。compile、diff check、Web `build_demo()` 另核；不拿它們替代真輪。
2. 零模型固定候選 **on-only final gold PASS** 才容許 A 的一次全新 M21 生成。保存私有原始三候選、來源／core／final SHA、guard 與 audit receipt；同一份真 planner 結果在隔離 surface 邊界重放 off/on，不能為兩臂重新 sampling。A fresh M21 最多 1 completed provider generation／0 retry／≤2000 provider tokens／≤20s planner wall；若 M21 fallback、candidate schema/parity 破裂、超額或 fresh on 不獨過 gold，停止、保留 FAIL，B 不送。這是 surface replay，不是兩次完整產品對照。
3. 只有 A 固定＋fresh surface 證據均 on-only-pass，才於**另一新 0700 私有 root/DB** 用 B 做原生 Safari 最多 1 Send／0 retry、硬安全上限 ≤3 completed generations／≤2000 provider tokens／≤20s user wait，保留 User bubble、JSONL、episode、圖 `input→source certificate→slot receipt→surface→final audit→utterance→writeback`、原生 PNG/AX（若工具無法保存即 visual-artifact gate FAIL）、逐層 calls/tokens/vector ops/等待/背景交錯。**預期對照與實驗實際路由皆為 1 次 M21 Qwen + 0 RightBrain model + 0 repair**；多出的任何一次即成本／parity FAIL，縱然尚未碰到 ≤3 硬上限也不能當零增量成功。新 root zero-turn/HTTP/Brain/DB/admission/T0 先驗，0 背景 interleave 與 Tpre→arrival ≤10s；不復用舊非空 admission journal。B 可能真實可見 FAIL，必須保留私有原件並停止，不能重試或改 gold；泡泡、JSONL、episode 不同字也 strict FAIL。正式 DB／原始 dirty checkout／無關 `output/` 不碰；服務 exact stop，只關本次新 Safari tab。

允許修改：新的 `uruha_source_event_surface_diagnostic_p4.py` 純來源槽／deterministic realization／audit 模組、`uruha_brain_mac.py` 的同輪窄接線、`p4_direct_reply_act_m29_priority_detached_control.py` 的 child-only opt-in flag、必要的 `uruha_memory_observatory.py` raw-free graph receipt/renderer、上述新測試。`uruha_web_ui.py`、記憶／adaptive 持久化、persona 資料、f7/f8 凍結題與 gold 不改；若發現必須改 Web、DB 或新增生成，先停做設計審查，不偷偷擴張。每批只有一個 source-bound surface treatment，測試和圖不是額外能力變因。

**本協定的 final verifier 是 audit-only。**失敗輪可在隔離 Safari 顯示錯句、寫入私有 episode；須誠實判 FAIL，保留 before/after 狀態，失敗 DB 不復用，不能宣稱 no-send、無狀態殘留或產品修復。產品部署或聲稱「錯答絕不送出／持久化」之前，仍須另做 review 所列延後寫入／完整回滾和 blocked UI transaction。正式 strong-LLM 公平比較、人評、temporal holdout、跨語語用理解與人類方程式皆 pending。
