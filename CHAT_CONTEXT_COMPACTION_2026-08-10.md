# UruhaBrain 新任務交接檔（2026-08-10；2026-09-06 M57.8 participant-confirmed ledger completion）

> **2026-09-07 最新工作順序：** 使用者批准產品效果優先、研究保留驗證，並要求較弱模型也能依明確流程接手。
> 讀完本交接後，以 `DEVELOPMENT_WORKFLOW.md` 與 `CURRENT_TASK.md` 執行當前工作；歷史「下一步」不直接執行。
> M57.9 保留收尾，Safari 最終驗收尚未完成；新增有限 P1–P4 產品線，正式 M55–M62/M75 的證據門檻完全保留。
> P1 先修已重現的跨重啟 prediction ID 碰撞：舊 supported 回饋被同句 turn 1 的 pending 覆蓋。

> 這是新任務的歷史與證據入口。不要要求使用者貼舊聊天室，也不要把整段舊聊天重新載入 Context。
> 先讀本檔，再用本檔列出的檔案、Git 與測試輸出確認最新狀態。

> **2026-09-01 最高優先目標覆蓋：** M1–M53 全部結果、失敗與產品能力保留，但不再把
> 增加局部對話規則當作核心研究完成度。從 M54 起，把現有記憶、狀態、關係、需求、人物
> 參數、不確定性、預測、結果驗證與誤差更新整理成可觀察、可干預、可否證的候選人類反應
> 方程式；以一ノ瀬うるは公開可觀察行為作第一人物案例，依 strict temporal holdout 驗證
> 未見未來預測，而不是宣稱私人心理或生物人腦真值。最樂觀完成線 M62，允許保留失敗並以
> 全新 sealed data 重試至 M75；M75 是本輪硬停止點，無論正負都必須形成完整結論。詳細順序
> 見 `research/full_completion_roadmap.md` 的 2026-09-01 override 與
> `research/m54_human_response_equation_v1_plan_2026-09-01.md`。本覆蓋優先於所有舊「下一步」。

> 最新續接（2026-08-30）：先讀第 7.66 節及 M52 acceptance。
> M52 已用 deterministic shared-substring object、casual clause ending、explicit existing stop 對齊
> M51候選；Safari契約3/3且交付2/3。但日文白紙report被自行補成環境／經濟／社會，M46
> same-model no-invented proxy誤放行；bounded author source alignment只有1/3。英文仍surface fail。
> M52 contract PASS、source-aligned pipeline FAIL；313項選定測試不能抵銷真實false accept。
> 下一個單一變因是 M53 source-neutral scaffold authorization；不得加入task白名單或改M46為全通過。
> 舊章節的「下一步 M31…M52 尚未實作」是歷史記錄，以7.66為準。

## 0. 新任務開始時必做

1. 工作目錄使用：
   `/Users/jerrychang/Desktop/uruharemake2_worktrees/persona-data-provenance`
2. 先執行 `git status --short --branch`，不得碰 unrelated dirty files。
3. 用 `git status --short --branch` 確認目前分支；2026-08-12 的安全分支是：
   `codex/v2-15-pragmatic-research-showcase`
4. 讀取本檔與當前里程碑報告，不要先讀 45 萬字的 evolution log。
5. 先保留既有研究與產品結果，再依 2026-09-01 最高優先覆蓋從 M54 持續執行，不等待逐 M 確認。

原始工作樹 `/Users/jerrychang/Desktop/uruharemake2` 有大量歷史 dirty files，不能清除、還原或混入目前研究修改。真正的連續研究工作在上述獨立 worktree。

## 0.1 2026-08-24 目標覆蓋：開發研發優先

使用者已明確將專案從「完整研究／論文導向」改為 **實際系統開發與研發導向**。本節優先於後文所有尚未完成的研究排程；M1–M15 已形成的凍結結果仍保留，但不再支配後續工程順序。

新的長期交付目標是：

> 把現有語用分析、記憶、狀態、預測、誤差與人格模組，整合成一個在真實多輪對話中持續運作的個人化認知系統。它必須能形成對當前使用者所需回覆的可檢查預測，從後續反應判斷猜對、猜錯或未知，修改具名變數與策略可靠度，並讓下一輪回覆真正使用修正後的模型。

新的執行原則：

1. **功能先於論文包裝**：優先完成 runtime 整合、跨輪學習、持久化、可視化、安全邊界與可用性。
2. **研究只留必要驗證**：保留隔離回歸、對照、失敗案例、成本與證據邊界；不再為了論文格式額外建構 preregistration、投稿用統計或大量展示包裝。
3. **實驗模組必須接回產品**：只存在於 lab／replay／dashboard 而不影響實際對話的機制，不算完成研發。
4. **不可挪用推測為事實記憶**：人類狀態只能作為有來源、信心、時間與可撤銷性的運作模型；必須與事實性長期記憶分開。
5. **對外保持誠實**：不宣稱意識、讀心、真人等價或已解出生物人腦方程式；只宣稱實際驗證過的功能。

**M16–M29 已於 2026-08-25 完成 bounded 產品驗收**：M29 把 M28 的 bounded weather rebase 擴成 fail-closed generalized literal-topic projection；自包含的新話題只有在 exact source span、subject/predicate、Japanese surface、visible anchors 與 casual register 全部通過時才可接管 final reply。隔離 Safari 中中文 `明天要考試。`、英文 `My train leaves at seven tomorrow.`、日文 `来週から新しい授業が始まる。` 都得到保留 literal content 的自然日文，且每輪 M27 都維持 `resolved_unknown_excluded`、final pending 為 null、raw dialogue 未持久化。M29-specific 8/8、focused compatibility 237/237 通過；較寬歷史組合 242/244，兩個失敗是保留的 V2.15 frozen-source/UI-order locks。證據見第 7.43 節與 `analysis/m29_generalized_literal_topic_projection_acceptance_2026-08-25.md`。

M30 已以凍結 18-case construction holdout 證明 M29 **尚不可靠**：15 個 valid cases 僅 4 faithful authority（26.67%）、5 false authority、6 false reject；3 個 incomplete 全部正確 abstain，median 5.1547s、p95 7.7157s。凍結門檻未改，原始失敗結果與 hash 保留；Safari 現在把 `4/15 / 5 / 6 / 3/3` error taxonomy 直接顯示在 live runtime graph 上方。證據見第 7.44 節與 `analysis/m30_cross_lingual_literal_fidelity_acceptance_2026-08-25.md`。

目前下一個產品里程碑為 **M31 Semantic Authorization and Reserve Confirmation**：修正 M30 發現的候選 negation 誤擋、noncanonical polarity、語義錯誤接管與 realization-only anchor mismatch，但不得拿同一 18 題 remediation 後成績冒充 holdout；必須保留 M30 original result，另用 sealed reserve 做 confirmation。

## 1. 歷史研究框架（現僅保留為驗證與證據邊界）

正式研究主體是 **Interpretable Longitudinal Human Digital Twin**：只使用預測時間點以前的可觀察縱向歷史，建立具有來源、時間、不確定性與可干預性的計算狀態，預測同一個人在未見未來情境中的行為機率分布，並以實際可觀察的後續行為驗證或否定模型。

中央研究問題：

> 能否把個體的長期可觀察行為資料轉換成可解釋、可參數化、可更新與可干預的計算模型，並在嚴格 temporal holdout 下，比強 LLM／RAG 基線更準確地重建已知行為及預測未見未來行為？

操作性形式：

```text
H_0:t, X_t+1 -> S_hat_t+1 -> P(Y_t+1 | H_0:t, X_t+1, S_hat_t+1)
```

- `H_0:t`：截止時間以前可用的公開可觀察歷史；不得含任何未來資料或事後摘要。
- `X_t+1`：新的事件、情境或對話刺激。
- `S_hat_t+1`：由記憶、暫定情緒、人格傾向、關係、偏好／價值、目標、習慣、情境與不確定性組成的可檢查模型狀態。
- `P(Y_t+1)`：可能行為的校準機率分布；主要預測層依序是行為類別、立場／方向、最後才是自然語言實現。
- `Y_t+1`：時間切割後實際可觀察到的發言、反應、選擇或行動。

LLM 負責語意理解、事件／意圖／立場抽取、相似度與自然語言實現；明確演算法負責 provenance、記憶強度與衰減、狀態轉移、關係／偏好更新、機率正規化、校準、消融、反事實干預與重現性。最終語句不得先生成再反過來虛構狀態或解釋。

先前的 desired-response／felt-understanding loop 保留為互動情境中的子問題：它可提供語用事件特徵、關係狀態與應用層人評，但不再是整個研究唯一的主要因變量。VRM、語音、即時聊天、Function Calling 與 Uruha 日文表面皆屬展示／應用層，不得取代 temporal future-prediction 證據。

研究只提出可反駁的計算假設；不宣稱是真實生物腦方程式、真人意識、讀心、完整私人個體或任意未來的完美預測。某個名為 emotion 的狀態只是一個帶不確定性的模型變數，必須靠 predictive lift、校準、消融、干預、穩定性與泛化取得可信度。

## 2. 個體重現的研究邊界

一ノ瀬うるは是第一個真實縱向 case study 與 person-specific 參數 `theta_Uruha`，不是架構本身。選她是為了讓一般「人類」問題收斂成有公開資料、時間軸、來源、ground truth 與 holdout 的具體個體；主要研究物是她在公開情境中可觀察的行為分布與時間變化，不是只模仿口吻。

正式結構是：

```text
person-independent architecture
+ public longitudinal observations
+ person-specific parameters
= public-observable behavioral digital twin
```

只能稱為「公開可觀察行為模型」：

- 不宣稱系統就是本人。
- 不推測私人記憶、真實內心或完整人格。
- Uruha 公開人格相似度、日文語氣與被理解感是次要表達／人評指標，不是未來行為預測成立的理由。
- 未公開童年、私生活、私人狀態與不可觀察經驗保持空白；不得用角色合理化捏造。
- 資料必須有來源、用途與 provenance；訓練、開發、獨立測試與最終保留資料必須分離。
- 每一筆記錄必須區分 `observed`、`self_reported`、`inferred`；隱藏動機和私密情緒若沒有明說，必須保持未知。
- 中文、英文或日文可作為互動展示輸入；Uruha 實例最終可見語言仍必須為自然日文。
- 架構最終必須以第二人物資料測試 transfer；若換人就必須重寫核心邏輯，不能稱為通用架構。

## 3. 如何證明完整架構值得做

所有主要結論必須來自 strict temporal holdout：對時間 `t` 的預測只能使用 `t` 以前的 evidence、embedding index、summary、prompt example 與參數選擇；任何時間洩漏都使該結果失效。

最低基線階梯：

1. `B0`：資料集行為 prior／random baseline。
2. `B1`：base LLM，只給事件與最小人物識別。
3. `B2`：相同 LLM 加靜態 persona prompt。
4. `B3`：相同 LLM 加普通 RAG。
5. `B4`：完整歷史摘要加 LLM。
6. `B5`：相同資訊預算的強 structured-prompt LLM。
7. `Ours`：structured memory、explicit state、temporal transition、probabilistic decision 與 LLM realization。

主要評量不是 exact sentence match，而是行為 top-1／top-k、Macro／weighted F1、Brier Score、NLL、ECE、MRR／NDCG、source correctness、irrelevant-memory intrusion、temporal leakage、persona／relationship consistency 與資源成本。自然語言相似度和 felt-understanding 只作次要人評。

解釋必須直接來自真正參與計算的 memory IDs 與 state features。對聲稱重要的記憶、情緒、關係、偏好、目標、習慣及 temporal dynamics 逐一移除或替換，量測 `Delta P(Y)`；若移除後預測不變，該解釋或部件沒有因果證據。

完整架構只有在 unseen future、rolling cutoffs、消融、干預、資料量曲線與最終 transfer 中取得一致證據，才能主張捕捉到有預測價值的個體結構。若強 LLM／RAG 相同或更好，必須如實記錄並簡化無效部件。

## 4. 證據層級

任何結果都要標明它只證明哪一層；下層通過不能自動授權上層：

1. `data / temporal validity`：來源、時間、標註與 cutoff 是否完整，future leakage 是否為零。
2. `deterministic state mechanism`：狀態是否能形成、衰減、保留、撤回、重播與接受指定 intervention。
3. `fresh temporal behavior prediction`：在未見 future events 上，行為分布是否正確且校準。
4. `same-model hybrid lift`：相同模型、資訊／token 預算與硬體下，Ours 是否優於 B0–B5。
5. `ablation / intervention faithfulness`：被解釋為重要的 state 或 memory 是否對 `P(Y)` 有可重現因果影響。
6. `rolling / data-scaling / transfer generalization`：結果是否跨 cutoff、資料量與人物成立。
7. `human realization / full runtime`：自然語言、人類偏好、聊天、語音、VRM、Function Calling、安全與成本是否可接受。

下層通過不能自動授權上層。Replay、已知回答或 deterministic retention 不能宣稱 fresh generation，更不能宣稱 production ready。

記憶證據也必須分開：

1. 被檢索到。
2. 被傳給決策模組。
3. 移除、替換或反事實干預後，能證明它造成回答差異。

只有第 3 項是記憶參與決策的因果證據。

### 4.1 一週定律（longitudinal prediction 版本；已於 M1 封存）

「一週定律」不是排程名稱，而是每週研究交付規格：

1. 每週選一個足以代表 longitudinal behavior prediction 核心問題的單一、可反駁研究單元。
2. 一週內做出可實際操作、能讓完全不了解專案的人看懂且感到研究差異明顯的成果。
3. 必須完整圖像化：cutoff 前歷史、被鎖住的未來、evidence、狀態、候選行為機率、實際未來、誤差、介入後機率變化與狀態更新；不能只放文字 log。
4. 必須同畫面呈現 B0–B5／Ours 的資料可見性、機率分布、真正差異、成功案例、保留失敗與證據邊界。
5. 必須有 frozen dataset／cutoff／taxonomy／config、leakage tests、可重現 command、實際 Web／Safari 驗收、資源量與「能主張／不能主張」。
6. 若外行人看完仍不知道研究在算什麼，或只有漂亮 UI 沒有可驗證實驗，該週不算完成。
7. 每週成果可以狹窄或是負結果，但必須真實、可展示、可累積並直接推進 temporal prediction；不得用合成 fixture、固定 replay、漂亮 UI 或聊天自然度冒充正式 future-behavior evidence。

### 4.2 一週版完成標記與後續模式（2026-08-15 使用者指示）

```text
ONE-WEEK SHOWCASE CHECKPOINT
START: V2.11–V2.22 retained subsystems
END:   M1 Temporal Prediction Observatory
STATUS: CLOSED / ARCHIVED / DO NOT MOVE THIS BOUNDARY
```

M1 的 audit、temporal schema、B0–B3、probability metrics、failure retention、完整圖像網站與 Safari 驗收，是「一週牛逼版做到這裡」的固定標記。後續不得為了讓一週版看起來更大而回寫、重算或移動此完成線。

從此主要執行模式改為 **full-completion mode**：依 master specification 的依賴順序持續完成 B4／B5、memory model、HumanState、transition、Ours predictor、正式 Uruha temporal data、ablation、intervention、rolling cutoff、scaling、transfer 與 full runtime。每個階段仍需 frozen artifacts、測試與誠實 evidence boundary，但不再受一週內必須收斂成展示成果的範圍限制。

## 5. 近期已合併的工作

所有以下 PR 都已合併到 `origin/main`：

| PR | 內容 | 結論 |
|---|---|---|
| #420 | V2.8 final reserve construction preregistration | 凍結 4 個 fresh + 2 個 final reserve conversation |
| #421 | V2.8 result | 失敗；只建出 5/8 cases，exact-string oracle 不足 |
| #422 | V2.9 evidence-ID preregistration | 改用 LoCoMo 官方 evidence dialogue IDs，projection 不變 |
| #423 | V2.9 development result | 115 cases；evidence recall 0.532787 -> 0.688525 |
| #424 | V2.10 final reserve preregistration | 凍結最後兩個未曝光 conversation |
| #425 | V2.10 final reserve result | 57 cases；evidence recall 0.649123 -> 0.824561 |

連結：

- https://github.com/jerry3816111/uruharemake2/pull/420
- https://github.com/jerry3816111/uruharemake2/pull/421
- https://github.com/jerry3816111/uruharemake2/pull/422
- https://github.com/jerry3816111/uruharemake2/pull/423
- https://github.com/jerry3816111/uruharemake2/pull/424
- https://github.com/jerry3816111/uruharemake2/pull/425

V2.10 的 paired transitions：

- both: 35
- isolated only: 2
- adjacency only: 12
- neither: 8
- adjacency 相對 isolated 的 evidence recall 增益：`+0.175439`
- mean character ratio：`0.170979 -> 0.273276`

這只證明 adjacency projection 在 final reserve 上保留更多官方 evidence turns。它尚未證明模型會使用這些內容，也未證明答案品質、完整聊天品質、人物相似度或可上線性。

## 6. 目前未提交工作：V2.11

目前分支：`codex/source-projection-v2-11-model-qa-contract`

目前已存在但尚未提交：

- `.gitignore`：忽略 V2.11 本機 raw checkpoint。
- `configs/source_preserving_memory_projection_v2_11_model_qa_preregistration.json`
- `locomo_official_qa_f1.py`
- `run_source_preserving_memory_projection_v2_11_model_qa.py`
- `test_source_preserving_memory_projection_v2_11_model_qa.py`

2026-08-10 已執行：

```text
python3 -m unittest -v test_source_preserving_memory_projection_v2_11_model_qa.py
Ran 5 tests in 3.376s
OK
```

目前檔案 SHA-256：

```text
ad2151fb5612f00bdac706434094a59b4cb8949cfcbe3c7d78d13127350cc92c  configs/source_preserving_memory_projection_v2_11_model_qa_preregistration.json
645a63ee6bd93384c2b0a9086bdbbc02dbab84fb52bf6316b5bc30d6f00038b5  locomo_official_qa_f1.py
72a825684222915c40e1526348ab503c117ddc38fea9532e49e40fb15a7a737a  run_source_preserving_memory_projection_v2_11_model_qa.py
c2d1e86b86671e58d2760ce6892bafbbde08b5b6f16727b7dab01b43a396f658  test_source_preserving_memory_projection_v2_11_model_qa.py
```

V2.11 唯一自變變因：`source_projection_representation`

- control：isolated source turn
- intervention：adjacency source span
- 同一組 57 個 final-reserve questions
- 每題兩個條件，共 114 次 fresh local-model calls
- 問題、模型、prompt、temperature、seed、token budget、scorer 與硬體固定
- gold answer、evidence IDs、condition label 不得出現在 model prompt

預定模型：本機 Ollama `qwen3.5:9b`，temperature 0、think false、seed 20260805、num_ctx 8192、num_predict 64。

正式主要指標使用 LoCoMo 官方 category-2 token F1。主要 gates 在 preregistration 中，重點包括：

- 114 calls、每條件 57 rows、0 transport errors。
- adjacency mean F1 >= 0.45。
- adjacency - isolated mean F1 >= +0.03。
- paired bootstrap 95% CI lower > 0。
- 12 個 adjacency-only evidence-gain cases 的 F1 delta >= +0.10。
- mean output tokens <= 32。
- 0 production memory writes、0 VRM actions。

V2.11 即使成功，也只允許另立一個 full-pipeline memory-intervention preregistration；不得直接修改 runtime、shadow enable 或 production。

## 7. 歷史一週里程碑與完整專案續作

下一個一週定律里程碑正式命名為 `V2.16 Uruha Reference-Person Desired-Response Equation`。單一核心變因是：在同一個 Uruha 公開人格表達條件與直接生成 baseline 上，加入「可干預的人類狀態＋θ_Uruha reference-person 評估 → 期望回覆策略」推算器；本週不擴張 VRM、聲學辨識或其他周邊功能。

1. 凍結一組「完全相同輸入、不同個人狀態」的反事實案例。主展示句固定為「我從早上就一直坐不住，腦子停不下來」，至少包含缺眠／身體狀況、真心求解法、只想被聽、一起興奮、吐槽邀請五種互斥或競爭情境。
2. 建立可追溯狀態資料結構：memory atoms、affect/physiology、desired-response need、relationship/humor boundary、context、feedback history、unknown 與 provenance。
3. 產生至少五種候選回覆策略：solve、listen、care、share-arousal、playful-tease；分別預測使用者接受、否定或反感的可能性。
4. 將候選策略同時通過兩個可分離評分：`desired-response fit`（使用者此刻想要）與 `θ_Uruha behavioral fit`（這個 reference-person 是否會這樣理解與表達）；人格不是生成後才套上的口吻。
5. 以明確 expected-utility／posterior 規則選擇策略；高不確定時允許自然的多需求兼容回答或低壓確認，但不能把「問問題」自動算成功。
6. 下一輪使用者反應必須更新造成錯誤的具體變數，例如 humor invitation、advice acceptance 或 sleep-debt hypothesis，而不只更新一個總 confidence。
7. 建立同模型、同人格、同 token 預算 baseline，預先凍結 desired-response gold／acceptable alternatives；加入 target-user blind choice 與至少可重現的 proxy harness。
8. Web 第一頁改成完整圖像化 equation lab：相同 `A` 分流到不同狀態向量、候選回答、雙重效用、選中回答與 feedback update；一般人不用看原始 JSON 就能理解。
9. Safari 實際跑完至少一個命中、一個猜錯後定位變數並修正、一個吐槽與解法競爭案例；隔離 session，0 production memory writes。
10. 報告分開：方程式機制、fresh desired-response prediction、same-model output、Uruha reference-person 行為契合與人類被理解感。沒有盲評不得宣稱已解出人腦、已複製真人或全面優於 LLM。

### 7.1 2026-08-12 V2.16 實際完成狀態

- 已凍結同一輸入的六種競爭情境與六種 gold desired-response policy。
- 已實作十個具名狀態原子、六個候選效用、可替換 `θ_Uruha` reference-person 評估、單一變數介入與 feedback 後具名原子校正。
- deterministic tests 可令六個情境選出六種不同 policy；unknown case 不擅自診斷或吐槽。
- 已完成本機 `qwen3.5:9b` fresh same-model paired generation：12 scored outputs、6/6 token gates；narrow proxy baseline 1/6、system 5/6，system visible-Japanese contract 6/6。
- 預註冊總 gate 沒有全通過：listen-only 的禁止字錨把「方法は出さずに」誤判為違規。此負結果保留，不得調參重跑，不得宣稱人類偏好勝利。
- Web 第一頁已改成 V2.16 `Equation Lab`；Safari 已實測同句異境、unknown 校準、feedback 後 `calibrate_need → playful_tease`、baseline/system 與證據邊界。
- 正式報告：`analysis/v2_16_one_week_reference_person_equation_acceptance_2026-08-12.md`。

### 7.2 原排程研究單元：Target-User Desired-Response Ground Truth

V2.17 不再增加新 UI 或手工規則。唯一變因是把作者設計的 development gold 替換成「目標使用者在看到回答前預先標註的期望回覆」。先凍結 30–50 組未參與 V2.16 開發的同句異境／自然多輪 cases，收集 target-user top-1、acceptable alternatives、反感策略與信心，再用同一模型、同一 Uruha 表達、相同 token 預算比較 direct baseline 與 V2.16 equation system。至少三位獨立盲評只看對話與匿名回答，評 desired-response match、felt understanding、overinterpretation 與 Uruha public-behavior fit。沒有這一層，不得把 5/6 proxy 稱為真的理解優勢。

V2.11–V2.15 是歷史證據與必要器官，必須保留，但從此不能把「有語用假設／會修正」本身當成人類意義上的理解成功。

此原排程未取消，但 2026-08-14 依使用者最新要求先插入長對話記憶研究；為避免名稱與既有產物衝突，原排程不得再沿用 `V2.17` 編號，恢復時應另立新里程碑與 preregistration。

### 7.3 2026-08-14 V2.17 Long-Dialogue Memory Trace 實際完成狀態

- 已在隔離 DB 實跑 25 輪：T1 記憶種子、T2–T16 十五輪干擾、T17 延遲回溯、T18 明確修正、T19–T23 五輪干擾、T24 修正後回溯、T25 舊值撤銷確認。
- T17、T18、T24、T25 走完整 runtime；其餘 seed／distractor 為凍結 transcript 經 production `save_episode` 寫入，不得稱為 25 輪 fresh generation。
- 四個 checkpoint 皆為自然日文，且 graph 可追到來源輪次／profile → passed-to-decision row → memory anchor → visible reply。
- T17 回溯草莓牛奶；T18 把目前偏好更新為 ginger ale 並撤回草莓牛奶；T24 再回溯 ginger ale；T25 明確不把草莓牛奶當成目前偏好。
- 決策 anchor 的 mechanism ablation 通過：移除精確目標會改變 anchor，移除無關記憶仍保留 anchor；這不是重新生成回答的 full-model ablation。
- 正式 DB aggregate hash 前後同為 `c56a8201731a004c8c031d01908e8c6ebd7c7b3aafdd295dc6d898873d859da6`，0 production memory writes。
- 第一次正式執行確實暴露「修正輪仍重複舊偏好」與「否定提問被 guard 拉回舊值」；之後另有 scorer 與 UI trace 對齊問題。所有失敗 attempt 均保留，不得只報最終成功。
- Web 第一頁已改成 `Long Memory Lab`，Safari 實際點選 T17、T18、T25 驗收；不得關閉使用者既有 Safari 分頁。
- 正式報告：`analysis/v2_17_long_dialogue_memory_acceptance_2026-08-14.md`。

### 7.4 下一個單一研究單元

凍結一組 100+ 輪、跨程序重啟、多種記憶類型的隔離 holdout，加入相似記憶干擾、false-memory controls 與完整生成級 memory ablation。在此之前只能稱本次 25 輪單一偏好案例為 bounded pass，不能宣稱通用長期記憶已完成。完成後再回到 target-user desired-response ground-truth／same-model blind comparison，驗證記憶能力是否真的改善使用者想要的回答。

### 7.5 2026-08-14 V2.18 50-Turn Memory Comparison 實際完成狀態

- 已在看到輸出前凍結 50 輪 scaling case、三條件與 scorer：`uruha_memory`、同一 `qwen2.5:7b` 最近 8 輪 direct LLM、同模型完整 transcript direct LLM。
- 加入第三個完整 transcript 診斷組的原因，是避免把「控制組沒有看到來源」包裝成外部記憶的推理優勢。
- T1 coffee；T25 延遲回溯；T26 撤回 coffee 並改為 chamomile tea；T48 再回溯；T49 撤銷確認；T50 朋友 melon soda 的關係誤綁控制。共 5 個三條件 fresh checkpoints；其餘為 frozen replay through `save_episode`。
- 第一次正式結果保留且 `uruha_preregistered_gate_pass=false`：Uruha 主要 source-grounded recall 1/2、recent 0/2、full 1/2 exact proxy；不得重跑追分或宣稱全面勝出。
- Uruha profile/state transport 成功：T26 後 `dislikes=[coffee]`、`favorites=[chamomile tea]`；T48 正確 profile row 與 `favorite_drink → カモミールティー` anchor 已進決策，但 final reply 洩漏「日本語だけで…」修復指令。這是 surface failure，不是 retrieval failure。
- T26 另暴露 stale active-validation 蓋過明確偏好更新；T50 暴露 `最喜歡` 疑問句被誤解析為 `current_preference_update`，雖然 assertion-scope 阻止 profile 寫入。
- Uruha T49 正確撤回 coffee；三條件皆無舊值正面復活或 melon-soda false assertion。Uruha visible-Japanese 5/5，recent 3/5，full 2/5。
- 五個 checkpoints 資源：Uruha 13,672 total tokens／268.79s；recent 2,526／14.33s；full 7,374／10.76s。Uruha 為 full 的 1.85x tokens、24.97x latency；這是非 token-parity full-system cost，不可只歸因於記憶。
- 盲評 packet 已產生但評分空白；`human_preference_supported=false`。本案例是 V2.17 family 的 scaling case，不是 independent semantic holdout。
- Web 第一頁新增 `50-Turn A/B`，以 50-node timeline、三條件平行答案、來源／anchor／surface chain、契約與成本分軸顯示；正式 gate failure 必須置頂。
- Web 顯示層將 `凍結 auto proxy` 與生成後 `REVIEW PASS / PARTIAL / FAIL` 分離；例如 T50 的 Uruha 為 auto proxy pass、但人工工程複核 fail（安全 non-answer 不算回答成功）。這是展示層標註，不修改 locked case／scorer／第一次正式 raw。
- Safari 已重新載入並核對 T48、T50；證據為 `analysis/v2_18_safari_50_turn_comparison_t48.jpeg` 與 `analysis/v2_18_safari_50_turn_comparison_t50.jpeg`，驗收時 7 個既有分頁均保留。
- 正式報告：`analysis/v2_18_fifty_turn_memory_comparison_acceptance_2026-08-14.md`。

### 7.6 下一個單一研究單元：V2.18 remediation 後的新 frozen case

保留第一次負結果，不修改既有 frozen case／scorer。先修正三個具體 failure stage：明確 preference update 優先於 stale active validation；有 memory anchor 時 final repair 不得輸出內部語言指令；favorite 疑問句不得成為 current assertion。修正後另立新值、新 transcript 與新 lock，只能稱 development remediation；之後用未參與修復的新記憶類型與 50+ 輪 holdout 驗證泛化，並完成盲評。

### 7.7 2026-08-14 V2.19–V2.21 remediation 實際完成狀態

- V2.18 的第一次負結果與 frozen artifacts 均保留；修正另立新資料、preregistration 與 lock，沒有重寫舊分數。
- Runtime 已修正三個 stage：明確 direct report 優先於 stale provisional clarification；有 concrete memory anchor 時 visible-language repair 不得洩漏內部指令；favorite claim 疑問句不再被當成 current assertion，且 false claim 會走 grounded denial。
- V2.19 使用新值（barley tea → hojicha；false-control lemonade）重跑同一 50-turn family。Uruha 主要 source-grounded recall 2/2、strict task 3/5、visible Japanese 5/5，但 T50 仍誤把 lemonade 當正向偏好；正式 gate 失敗。
- V2.20 attempt 1 在 summary 階段因 preregistration key mismatch 中止；只保留 failure report，沒有 raw result，不能算 pass 或 fail，也不能引用未落盤輸出。
- V2.21 只重跑已修復的 Uruha arm，V2.19 的 recent/full baselines 保持 frozen。T50 已能否定 lemonade，strict task 提升為 4/5，仍因未指出它只屬於 friend 的來源而 gate 失敗。

### 7.8 2026-08-14 V2.22 stable relational-source replay 實際完成狀態

- V2.22 嘗試讓 relation claim 優先尋找穩定來源事件；但 production runtime 的 `recent_turns` 只包含前 8 輪，T41 friend event 在 T50 已離開視窗，retrieval 也沒有穩定選到它。
- Uruha T50 最終回答為 `レモネードが本命って記録はない。そこは勝手に足さない。`：已正確否定錯誤主張、沒有再寫入或正向聲稱 false memory，但仍沒有追溯到 `朋友喜歡 lemonade` 的關係來源。
- 正式結果仍為 `uruha_preregistered_gate_pass=false`：Uruha main recall 2/2、strict task 4/5、visible Japanese 5/5；recent-window baseline 0/2、1/5、3/5；full-transcript baseline 2/2、4/5、4/5。
- Uruha 與 full transcript 在 strict task 和 main recall 上打平，因此不得宣稱全面優於 full-context LLM。相對 recent-window baseline 的優勢只能主張為跨窗 persistence，不是更高智慧，因為資料可見性不同。
- 五個 checkpoint 的資源：Uruha 13,435 tokens／255.5081s；recent 2,526／12.5258s；full 7,405／10.9935s。Uruha 為 full 的 1.81x tokens、23.24x latency；為 recent 的 5.32x tokens、20.40x latency。
- 三個原始錯誤中，T26 update precedence 與 T48 instruction-leak repair 已 end-to-end 通過；T50 assertion polarity 通過、relation-source attribution 未通過，因此本次只能稱 `2 個修好 + 1 個部分修好`。
- 正式 DB aggregate hash 前後相同，0 production memory writes；scoped 88 tests 通過，V2.22 lock validation 與 `git diff --check` 通過。這不是全 repository suite 或 production-readiness 證據。
- Web 第一頁新增 `50-Turn Repair` 圖像頁：以 repair cards、50-node timeline、三條件 lanes、T41→T50 trace、版本進展與成本比較呈現；gate failure 必須置頂，不得用 UI 隱藏。
- Safari 已實際重新載入並切換 T26、T48、T50 驗收；證據為 `analysis/v2_22_safari_memory_repair_t26.jpeg`、`analysis/v2_22_safari_memory_repair_t48.jpeg`、`analysis/v2_22_safari_memory_repair_t50.jpeg`。驗收後 7 個既有分頁全數保留。
- 正式報告：`analysis/v2_22_memory_remediation_comparison_acceptance_2026-08-14.md`；正式 raw：`analysis/v2_22_stable_relational_source_replay_raw.json`。

### 7.9 下一個單一研究單元：structured relation-event memory holdout

停止在同一飲料案例追加規則或重跑追分。下一個 frozen 單元應改用未參與修復的新關係型記憶與 50+ 輪獨立 holdout，把 `subject／relation／object／source_turn／scope／polarity／validity` 存成結構化 relation event，並以生成級移除／替換 intervention 驗證該事件是否造成回答差異。同模型 full transcript 與 bounded recent context 仍必須保留；只有通過新語義 holdout、關係來源 attribution、false-memory control 與盲評後，才可主張此修復泛化。

### 7.10 2026-08-15 master research migration 與一週里程碑

`RESEARCH_SPEC_FOR_CODEX.md` 已把專案主體重新定義為 `Interpretable Longitudinal Human Digital Twin`。V2.11–V2.22 必須凍結為可重用的 memory／state／trace／realization 子系統與歷史證據，不再繼續以聊天修補或同題飲料規則作為主要研究進度。

當前一週里程碑命名為 **M1 Temporal Prediction Observatory**：

1. 先完成 Phase 0 research definition 與 Phase 1 `reports/RESEARCH_MIGRATION_AUDIT.md`，不可直接重寫 runtime。
2. 建立 versioned historical manifest、event／behavior-label schema、strict cutoff、prediction-time validator 與 future-leakage tests。
3. 先完成 B0 prior、B1 base LLM、B2 persona prompt、B3 RAG；同一模型與資源條件必須記錄。B4／B5 與 Ours 可預留介面，但不得用空殼算完成。
4. 所有模型先輸出 behavior probability distribution，再做自然語言 realization；主要指標為 Top-k／F1／Brier／NLL／ECE，exact reply 只作次要觀察。
5. Web 首頁展示 cutoff 前歷史、被鎖住的 future、baseline 機率、實際未來、誤差、provenance、leakage gate、成本與能／不能主張；Safari 必須真實驗收。
6. 現有 public-persona framework 已凍結 3 個 Uruha calibration sources、30 個 sampling slots 與 4 個 sealed holdout sources，但正式 target behavior events、獨立真人編碼與 reliability 均為 0。V7 尚需兩位真人完成 18-slot codebook pilot；在此 gate 通過以前，不得啟動正式 Uruha target coding、模型執行或 unseal holdout。
7. 因此一週內可完整交付 audit、temporal benchmark infrastructure、B0–B3 runner、metrics、leakage proof 與 synthetic／development fixture demonstration；若真人 ground truth gate 尚未完成，必須把 Uruha formal-result lane 明確顯示為 `DATA GATE BLOCKED`，不得把 fixture 包裝成真人 future-prediction 結果。

完整 master specification 不是一週項目。M1 只完成可信 temporal evaluation 地基與可操作展示；explicit state model、learned transition、Ours predictor、正式 Uruha temporal result、rolling cutoffs、全 ablation/intervention、data scaling 與 second-person transfer 均屬後續里程碑。

### 7.11 2026-08-15 M1 Temporal Prediction Observatory 實際完成狀態

- Phase 0 research definitions 與 Phase 1 migration audit 已完成；主目標正式改為 strict temporal holdout 下的可校準未來行為預測。
- 新增乾淨 `longitudinal_human_model` research core：temporal validator、B0–B3、probability metrics、hash/registry 與 atomic result runner；沒有把新 benchmark 塞回 17k-line runtime。
- 合成 fixture 共 12 個歷史事件、12 個 cutoff 後未來事件；144 個 history references 全數在 cutoff 前，0 leakage。此資料完全虛構，`formal_target_claim=false`。
- V1 第一次凍結生成只有 29/48 valid rows，19 筆因模型回傳 top-level probability map 而被 strict parser 拒絕；正式標為 `invalid_incomplete_run` 並保留。
- V1.1 另立 preregistration 與 lock，只增加「接受等價 top-level exact label map」；資料、prompt、模型、seed、retrieval、metrics 與 no-retry 不變。結果 48/48、0 failure；因樣本已在 V1 暴露，明確標為 nonfresh engineering rerun。
- 合成 V1.1：B0／B1／B2／B3 Top-1 分別為 16.7%／50.0%／83.3%／83.3%；Brier 為 0.833／0.546／0.353／0.312；NLL 為 1.792／1.108／0.770／0.667；ECE 為 0.000／0.118／0.270／0.329。B3 ranking/proper score 較好但 calibration 與成本較差，不能只報 accuracy。
- 36 次本機 `qwen3.5:9b` 呼叫共 20,966 tokens、240.1 秒模型 latency；B3 10,889 tokens，為 B1 的 2.39x。
- Web 第一頁已改為 `Temporal Twin · NEW`：完整節點圖顯示歷史、cutoff、當前事件、B0–B3 機率、解封未來、B3 實際檢索、metrics、成本、V1 failure 與 roadmap。
- Safari 外部瀏覽器已開啟 `http://127.0.0.1:7860`，並實際由 S07 切換 S09，確認 graph 更新。新證據：`analysis/m1_safari_temporal_twin_s07_2026-08-15.png`、`analysis/m1_safari_temporal_twin_metrics_2026-08-15.png`。
- 17 個 M1 unit/contract/Web tests 通過；Gradio build smoke 通過。TTS server 未啟動，不影響 read-only M1 lab。
- Uruha formal lane 維持 `DATA_GATE_BLOCKED`：target behavior events 與 independent coders 仍為 0。M1 工程／展示 rubric 100% 完成，但 full project engineering 約 40–45%、central scientific evidence 約 10–15%；不得平均成系統成熟度或宣稱真人預測成功。
- 正式報告：`analysis/m1_temporal_prediction_observatory_acceptance_2026-08-15.md`。下一個必要單元不是再加 UI，而是兩位真人完成 frozen V7 18-slot reliability pilot；通過後才可啟動 V9 target coding。

### 7.12 2026-08-15 完整完成模式啟動

- 使用者已指示把 M1 固定為一週版完成標記，後續目標改為完整完成 master specification，不再用一週範圍限制架構工作。
- 人類標註 gate 與可由 Codex 獨立完成的工程採雙軌：Uruha 正式結果等待兩位真人 V7 reliability；同時工程不得空等，先完成 B4 full-history-summary 與 B5 history-conditioned structured-prompt 強基線。
- B4／B5 是 Ours 前的必要比較地板。若未先完成，就不能判斷 explicit state／transition 是否提供超越強 LLM history conditioning 的價值。
- B4／B5 在既有合成 fixture 上只能提供 engineering evidence；已曝光 M1 samples 不得稱 fresh holdout。正式科學比較仍等待未曝光真人 temporal dataset。
- 完整完成路線與 gate 記錄於 `research/full_completion_roadmap.md`；後續每完成一個階段都需更新該檔與本節，不得以單一總百分比掩蓋 data、mechanism、prediction、causal、generalization 與 runtime 的不同成熟度。

### 7.13 2026-08-15 M2 Strong Temporal Baselines 實際完成狀態

- B4 full-history-summary 與 B5 structured full-history 已在同一個 `qwen3.5:9b`、同一事件與同一六類機率契約下完成；B4 的 summary 不接收 current test event 或 future outcome，B5 沒有 explicit state/transition 演算法。
- 第一次凍結模型執行為 24/24 prediction rows、1 個共用 B4 summary、25 calls、0 failure；M2 共 27,083 tokens、257.7 秒 model latency。
- 合成 fixture 的 Top-1：B0 16.7%、B1 50.0%、B2 83.3%、B3 83.3%、B4 58.3%、B5 75.0%。B5 雖非 accuracy 最佳，但 Brier 0.2912、NLL 0.6368 為六組最佳；後續 Ours 必須同時面對 accuracy 與 proper-score 地板。
- 此為已曝光 M1 samples 的 nonfresh synthetic engineering evidence；不得宣稱 B5 泛化、預測 Uruha、或系統已比一般 LLM 更懂真人。
- Web 已升級為 `Temporal Twin · M2`，Safari 實際核對 S11、B0–B5 六條機率 lane、summary、metrics、成本、M1 archived marker 與 data gate。驗收時未關閉任何使用者既有 Safari 分頁。
- 證據：`analysis/m2_strong_temporal_baselines_synthetic_first_generation_raw.json`、`analysis/m2_strong_temporal_baselines_acceptance_2026-08-15.md`、`analysis/m2_safari_b0_b5_s11_2026-08-15.png`、`analysis/m2_safari_b0_b5_metrics_2026-08-15.png`。
- 下一個依賴順序是 M3 structured temporal memory：provenance、validity/cutoff、decay、importance、semantic/relationship/emotional relevance、confidence、可追蹤 retrieval 與 memory-only ablation。不得在 exposed outcomes 上偷調權重。

### 7.14 2026-08-15 M3 Structured Temporal Memory 實際完成狀態

- 已新增 person-independent `longitudinal_human_model/memory.py`：每筆記憶包含 subject、observable event、event/available/source 時間、來源、extractor、dataset、confidence、importance、emotional salience、relationship tags、frequency、validity 與 supersession。
- 檢索前先執行 subject／cutoff／availability／source／validity gate；future、expired、not-yet-valid 與 other-subject memory 不能靠高分混入。
- activation 分成 7 個可檢查成分：semantic relevance、recency、frequency、importance、emotional salience、relationship relevance、confidence；參數可設定，每個 contribution 與 provenance 都進 trace。
- 凍結合成機制實驗含 14 records、6 queries、完整條件＋7 個 single-component ablations。完整 Recall@2 100%；future selected 0、expired selected 0。移除 semantic 後 Recall@2 83.3%，移除 emotional salience 後 66.7%；其餘移除仍改變排名或分數。
- 這些數字是作者設計 synthetic fixture 與 equal-weight probe 的機制效果，不是人類參數估計，也尚未證明 behavior prediction 比 B0–B5 好。semantic 現為 lexical proxy，不得稱真正語意理解。
- Web 第一頁已改為 `Memory Core · M3`，Safari 實際由 Q6 切到 Q4，selected memories 從 M11/M12 更新為 M07/M08；future／expired gate 保持。既有 Safari 分頁未關閉。
- 證據：`analysis/m3_structured_memory_synthetic_first_result.json`、`analysis/m3_structured_memory_acceptance_2026-08-15.md`、`analysis/m3_safari_structured_memory_q06_top_2026-08-15.png`、`analysis/m3_safari_structured_memory_ablation_2026-08-15.png`。40 個 M1–M3 scoped tests 通過，M3 lock 0 mismatch。
- 下一個依賴順序是 M4：建立可序列化、可 replay、帶 timestamp/source/uncertainty 的 person-independent `HumanState` snapshot；M4 只定義狀態表示與 snapshot contract，不先偷做 T1 transition 或 Ours predictor。

### 7.15 2026-08-15 M4 Timestamped HumanState 實際完成狀態

- 已新增 person-independent `longitudinal_human_model/state.py`，固定 M/E/P/R/V/G/H/K/U 九個可檢查部分；每個 estimate 必須標 observed／inferred／unknown、confidence、evidence IDs、updated time 與 evidence-boundary note。
- unknown 強制為 null value、0 confidence、0 evidence；observed／inferred 必須引用存在的 evidence。memory evidence 不得晚於 cutoff，current-event evidence 不得晚於 snapshot timestamp。
- 2 個凍結 synthetic snapshots 皆產生 deterministic SHA，serialize → reload 完全一致；4 個 M3 memory activations、6 unknown paths、6 low-confidence paths、future evidence 0、broken reference 0。
- M4 明確 `state_transition_enabled=false`、`behavior_predictor_enabled=false`；這些 confidence 與 psychological labels 是作者設計 model variables，不是私人心理 ground truth，也尚未證明 predictive lift。
- Web 第一頁已改為 `HumanState · M4`，完整顯示 event → memory → nine-part state → snapshot、evidence catalog、unknown space、SHA/replay gate 與 `NO TRANSITION / NO PREDICTOR`。Safari 實際由 Q6 切到 Q4，goal/evidence 由 technical state 改為 privacy state；8 個既有 tabs 全保留。
- 證據：`analysis/m4_human_state_synthetic_first_result.json`、`analysis/m4_human_state_acceptance_2026-08-15.md`、`analysis/m4_safari_human_state_q06_top_2026-08-15.png`、`analysis/m4_safari_human_state_evidence_2026-08-15.png`。52 個 M1–M4 scoped tests 通過，M4 lock 0 mismatch。
- 完整專案目前粗略 30–35%；engineering architecture 約 55–60%，central scientific evidence 約 10–15%。此三軸不得合併包裝成系統成熟度。
- 下一個依賴順序是 M5：在 frozen M4 snapshot contract 上實作與比較 T0 static、T1 configurable weighted、T2 learned、T3 hybrid feature-extractor＋learned transition；沒有比較完成前不得跳到 Ours claim。

### 7.16 2026-08-15 M5 State Transition 實際完成狀態

- 已依 master spec 建立共同介面：`next_state = transition(previous_state, current_event, retrieved_memories, person_parameters)`；每個 trace 都含 before／after／delta／feature source／實際 contribution。
- 四個家族均已實作：T0 static、T1 hand-designed weighted、T2 ridge-linear learned、T3 constrained `qwen3.5:9b` observable-event feature extractor＋同型 learned transition。T3 prompt 看不到 next state、outcome、behavior label、私人心理或身份。
- 第一次模型呼叫前已凍結 40 個互不重複 event texts：24 train、8 dev、8 holdout；不重試、不做逐列 fallback。實際 40/40 calls 成功，8,614 tokens、178.76 秒累計本機推論。
- holdout RMSE：T0 0.1264、T1 0.0420、T2 0.0042、T3 0.0576；方向命中分別 14.6%、77.1%、100%、70.8%。T2 在 disclosed linear synthetic oracle 上最佳。
- T3 不是最佳家族，且不得包裝成成功勝出：其 holdout event-feature MAE 0.2294，repetition 0.3675、support 0.2950、technical failure 0.2625 是最大瓶頸。這個負面差異已保存在 raw、result lock、報告與 UI。
- 所有 engineering gates 通過；每條 trace 都明確 `behavior_prediction_performed=false`、`language_generation_performed=false`。raw 的兩個同名 gate keys 為 `true` 是「absence requirement 通過」，不是執行了 behavior／language；報告已註明。
- M5 專屬 12 tests 通過；M1–M5 scoped regression 49 tests 通過；M2／M3／M4／M5 frozen lock validations 全部 0 mismatch。
- Web 第一頁新增 `State Transition · M5`：可切換 8 個 holdout，完整節點圖顯示同一輸入分流到 T0–T3、六維 before／gold／prediction、T3 gold-vs-Qwen feature 與成本／主張邊界。
- Safari 已實際重載並切換 technical failure、privacy boundary，核對數字與下半部 perception bottleneck；8 個既有 tabs 全保留。證據：`analysis/m5_safari_technical_failure_2026-08-15.png`、`analysis/m5_safari_privacy_boundary_2026-08-15.png`、`analysis/m5_safari_privacy_boundary_lower_2026-08-15.png`。
- 正式 raw：`analysis/m5_state_transition_synthetic_first_generation_raw.json`，SHA-256 `61abb11677eedcd9c3824a9a14767b346396bc5b7770d3841a7fdbf5933f1a0c`；報告：`analysis/m5_state_transition_acceptance_2026-08-15.md`。
- 完整專案目前粗略 35–40%；engineering architecture 約 65–70%，central scientific evidence 仍約 10–15%。M5 只證明 synthetic transition instrument，不證明 model variables 是真人內心，也尚未證明 behavior prediction lift。
- 下一個依賴順序是 M6：在任何語言生成前，把 transitioned HumanState＋event＋memory 轉成 behavior logits、probabilities、calibration 與 selection，並在 frozen temporal fixture 上和 B0–B5 比較；不通過就保留負結果，不得回頭偷調 M5 holdout。

### 7.17 2026-08-15 M6 Calibrated Behavior Predictor 實際完成狀態

- 已實作 master spec 的行為層順序：`transitioned state + event + memories + person parameters → behavior logits → softmax probabilities → temperature calibration → behavior selection`；所有條件都停在 behavior，`language_realization_performed=false`。
- 使用 frozen M5 的 24 train、8 dev、8 holdout；M6 materialized temporal dataset 有 32 筆 cutoff 前 history、8 筆 future、256 history references、0 future leakage。六個 behavior labels 是作者設計 observable synthetic outcomes，不是 Uruha 或真人資料。
- B0–B5 在相同 8 future events、相同 32 history 與同一 `qwen3.5:9b` fresh 執行；共 41 calls（含 1 次 B4 summary）、45,512 tokens、426.77 秒。
- Ours 沿用 frozen M5 T3 Qwen features 與 transition，M6 增量 0 LLM calls；inclusive 成本保留 M5 的 40 calls、8,614 tokens、178.76 秒，再加 4.55 秒 CPU classifier/calibration。
- holdout：Ours Top-1 87.5%、Top-3 100%、Macro-F1 0.800、Brier 0.1509、NLL 0.1939、ECE 0.1042；最佳 B0–B5 Top-1 87.5%、Brier 0.3469、NLL 0.6949。預註冊窄版 synthetic lift 三條件全通過：Top-1 不低於最佳 baseline，Brier 與 NLL 嚴格較低。
- 這不是全面勝利：B2／B4 Macro-F1 0.911 高於 Ours；`quiet_success::holdout` 的正確 label 是 `acknowledge_then_continue`，Ours 卻以 0.775 高信心選 `direct_rejection`，而 B2／B3／B4／B5 都選對。此錯誤已凍結，不得回頭調參。
- calibration 在 8 筆 dev 選到 temperature 0.5，dev NLL 0.0323→0.00135；它會 sharpen confidence，可能過度擬合，不能稱一般校準已證明。
- explanation 直接顯示實際 linear logit contributions 與 evidence，不用第二個 LLM 事後編理由。
- M1–M6 scoped 65 tests 通過，M6 lock 0 mismatch，`git diff --check` 通過。正式 raw SHA-256：`b042011646c16b7fd565f39ed8acab621cbd16fb2a9e910a0e776e5829ea20b4`；報告：`analysis/m6_behavior_predictor_acceptance_2026-08-15.md`。
- Web 第一頁新增 `Behavior Predictor · M6`：7 條件 metrics、state→logits→probability→calibration→selection、每列前三機率、direct contribution、temperature grid、成本與 failure boundary。
- Safari 已實際核對 technical failure 正確案例與 quiet success 保留錯誤，上下半頁一致；8 個既有 tabs 全保留。證據：`analysis/m6_safari_behavior_success_2026-08-15.png`、`analysis/m6_safari_quiet_success_failure_2026-08-15.png`、`analysis/m6_safari_quiet_success_failure_lower_2026-08-15.png`。
- 完整專案目前粗略 40–45%；engineering architecture 約 75–80%，central scientific evidence 仍約 10–15%，因為這是 nonfresh synthetic hypothesis，不是正式真人 longitudinal evidence。
- 下一個依賴順序是 M7：對實際存在的 state／event／memory／person components 做 frozen ablation 與 `Delta P(Y)` intervention；如果 preference／habit 等 master-spec component 在 M6 中沒有獨立表示，必須標記 `not_identifiable`，不能捏造一個 ablation 分數。quiet-success 失敗是首要診斷案例。

### 7.18 2026-08-15 M7／M7.1 Ablation & Intervention 實際完成狀態

- M7 先精確 replay frozen M6 Ours 的 8 筆 holdout 機率，再做 component removal 與 probability-level intervention；沒有重調 M6、沒有語言生成、沒有新模型呼叫。
- 第一次 M7 誠實暴露結構缺口：master-spec 的 preference 與 habit 在 M6 中沒有獨立表示，因此 8 個元件可評估、2 個標記 `not_identifiable`；這個第一次結果已鎖定保留。
- M7 第一次消融顯示 memory、personality、explicit state、semantic interpretation 的移除會惡化結果；relationship 與 temporal dynamics 的移除反而改善。尤其以 T0 previous state 取代 T3 temporal update 時 Top-1 +12.5 pp、Brier -0.102、NLL -0.100，證明目前 T3 不是只要存在就有益。
- 80 個具名 intervention 與 40 個 explanation top-feature intervention 已完成；40/40 都實際改變 selected-label probability，解釋直接對應模型項而非第二個 LLM 事後編理由。
- `quiet_success::holdout` 的錯誤完整保留：原正確 label 機率 0.225、錯選 `direct_rejection` 0.775；設定 preregistered `event.support=1.0` 後，正確機率升到 0.99995 並翻轉選擇。這只證明數值路徑可干預，不代表 support=1 是真人內心真值。
- M7.1 另立 post-exposure remediation：加入 5 個 explicit preference alignment 與 6 個只用 24 筆 train labels 拟合的 behavior-centroid habit similarity；17 個 frozen base features 擴為 28，10/10 master components 均可獨立消融。
- M7.1 的 10/10 ablations 都改變至少一個機率指標，但正負效果並存：habit removal NLL +0.417；semantic +1.698；explicit state +0.956；temporal -0.220；relationship -0.116；preference -0.014；goal 只有 +0.0009。可識別性不等於必要性或心理有效性。
- M7.1 full Top-1 87.5%、Brier 0.248、NLL 0.675 是已看過同一 synthetic holdout 的 diagnostic，不得替換或提升 frozen M6 predictive claim。
- M7/M7.1 scoped 20 tests 通過；結果與 experiment lock 皆固定。正式結果：`analysis/m7_ablation_intervention_diagnostic_first_result.json` 與 `analysis/m7_1_component_coverage_remediation_result.json`；報告：`analysis/m7_1_component_coverage_acceptance_2026-08-15.md`。
- Web 第一頁新增 `Ablation Lab · M7`：完整顯示 frozen prediction→remove/set variable→recompute→compare、10 個 ΔNLL 雙向條、quiet-success intervention、coverage repair、正負證據與主張邊界。
- Safari 實際重載、切換 temporal→habit、核對 quiet-success 22.5%→99.995%；首次驗收抓到未展開模板並修正後重驗。8 個既有 tabs 全保留。證據：`analysis/m7_safari_ablation_overview_2026-08-15.jpeg`、`analysis/m7_safari_habit_ablation_2026-08-15.jpeg`、`analysis/m7_safari_intervention_boundary_2026-08-15.jpeg`。
- 完整專案目前粗略 45–50%；engineering architecture 約 85–90%，central scientific evidence 仍約 10–15%。M7 完成的是 synthetic causal-diagnostic instrument，不是 human-state causal validity。
- 下一個依賴順序是 M8：rolling cutoffs、multiple seeds、history-volume scaling 與全新 semantic holdout；主要目的不是追更高分，而是檢查 M6 lift、T3 temporal 負效果、relationship／preference 噪音與 calibration 是否穩定重現。

### 7.19 2026-08-15 M8／M8.1 Rolling Cutoff & Scaling 實際完成狀態

- 新增一條完全虛構、未參與 M5/M6 開發的 24-event multilingual timeline：8 筆初始歷史，E1–E4 每個 cutoff 封印 4 筆 future；下一個 cutoff 才能看到上一批 outcome。可見歷史嚴格為 8→12→16→20，16 個測試句、0 future leakage。
- 第一次 M8 真模型執行在 H08 停止：`qwen3.5:9b` 輸出 `support=-0.5`，strict [0,1] parser 依 no-retry 規則保留 7/108 completed calls 並中止。原始失敗 SHA `48ccb4da581f43f7bc603d5e88a42b3c8baf667c219af8e89f8dc2279fbd1d01`，不得覆寫。
- M8.1 另立單一 parser amendment：prompt、data、model、seed、cutoffs、hypotheses 與 no-retry 全部不變，只把 finite numeric out-of-bound value 裁到 [0,1] 並保存 raw。實際只有 H08 support -0.5→0、E3-02 support -0.3→0 兩次 normalization；16 個 rolling test prompts 在 amendment 前尚未呼叫。
- M8.1 engineering gate 完成：24 feature calls + 84 B1–B5 calls = 108/108；B0–B5 共 96 prediction rows，Ours 16 rows；8 history volumes、5 bootstrap seeds、4 rolling cutoffs、0 language realization。
- 8 條 preregistered diagnostic hypotheses 只通過 1 條；科學 gate 明確失敗。新 semantic holdout 上 B5 Top-1 81.25%、Brier 0.428、NLL 0.879；Ours 62.5%、0.741、2.916。Ours 不勝 B5，且和 B1 同為 62.5% 但 proper score 與 ECE 更差。
- rolling Ours 極不穩定：E1/E2/E3/E4 Top-1 = 75%／50%／100%／25%，NLL = 0.931／3.547／0.035／7.148。不能用 aggregate 62.5% 掩蓋 E4 collapse。
- 歷史量不單調：D0 NLL 2.683，D2 最佳 2.055，D5／D6 Top-1 最高 68.75%，D7 all-history 反而 NLL 2.916；`more history improves` 主要假設失敗，只通過狹義 final increment 不大於 first increment 的 diminishing-return inequality。
- 五 seeds 的 Top-1 50.0–68.75%、NLL 2.142–2.944，顯示 sampled history 會 materially change result。
- M7 三個負方向全部在新資料反轉：temporal removal ΔNLL -0.220→+0.852、relationship -0.116→+0.259、preference -0.014→+0.327。不得宣稱它們是穩定的壞元件；效果依 context/dataset 改變。
- 資源：74,820 tokens、864.80 秒 local-model latency、81.66 秒 numeric fitting；0 production memory writes。結果 SHA `afcc425ef550444204d219c300a256d4f59d4a5eeccbe580ab15c3766d899726`。
- M8 scoped 15 tests 通過，`git diff --check` 通過。報告：`analysis/m8_rolling_scaling_acceptance_2026-08-15.md`。
- Web 第一頁新增 `Robustness · M8`：B0–B5/Ours、rolling cards、D0–D7 NLL bars、5 seeds、逐 cutoff B1/B5/Ours cases、M7 sign reversal 與 resource/claim boundary 同頁顯示。
- Safari 實際重載 E4、切換 E1、核對下半部 sign reversal/boundary；8 個既有 tabs 全保留。證據：`analysis/m8_safari_robustness_e4_2026-08-15.jpeg`、`analysis/m8_safari_robustness_e1_2026-08-15.jpeg`、`analysis/m8_safari_sign_reversal_boundary_2026-08-15.jpeg`。
- 完整專案目前粗略 55–60%；engineering architecture 約 90–95%，central scientific evidence 約 15–20%，但 formal Uruha evidence 仍為 0，DATA GATE 仍 blocked。
- 下一個依賴順序是 M9 second-person transfer：核心 schema、transition、memory、predictor 與 runner 不得為第二人改寫；只能替換 person data、history、person parameters 與 fit artifacts。必須分開 zero-shot、data/parameter adaptation 與 B0–B5，保留負結果。

### 7.20 2026-08-15 M9／M9.1 Second-person Transfer 實際完成狀態

- 第二個人使用全新虛構研究協調者 `Synthetic Mira`；領域、事件文字、person parameters 與 history 都不同於 `Synthetic Ren`，但 behavior taxonomy、schema、memory、state、transition、predictor 與 rolling core 不改。
- 比較三個 target condition：Ren history + Ren parameters 的 `REN_ZERO_SHOT`、Ren history + Mira parameters 的 `MIRA_PARAMETER_SWAP`、Mira history + Mira parameters 的 `MIRA_FULL_ADAPTATION`，並保留 B0–B5 floor。
- M9 第一次真模型執行在第 46 個 call 停止：B4 產生等價 key `behavior_prediction_summary`，strict parser 依 no-retry 規則保留失敗。raw failure SHA `aeb69e7bf6b0776597e00f40463ad691d0189953d82dc361922c0ad9a55a285b`，不得覆寫。
- M9.1 另立單一 summary-alias amendment：只接受已記錄的 `behavior_prediction_summary` alias 並保留 raw；資料、模型、prompt、seed、hypotheses 與 core 均不改。完整結果 108/108 calls，實際 3 次 alias normalization，0 feature boundary clip、0 language realization、0 production memory writes。
- 工程 transfer gate 全通過：8 個 SHA-bound core files 均與 Ren pipeline 相同，person-specific core branch count = 0。Mira fixture SHA `b5af35207fb1157737bc67a07bbcde48d2af91ea3d7c8ded7954fd5ecef71e11`，M9.1 result SHA `e3c35e1236d7c99d3707fbac75fc6469dc46585f432ff0918a942ead028f8aba`。
- 七條 predictive-transfer hypotheses 只有一條通過。Top-1：Ren zero-shot 50.00%、Mira parameter swap 56.25%、Mira full adaptation 43.75%；B4/B5 都是 75.00%。Full adaptation 的 Brier 1.0498、NLL 2.9452，明顯沒有勝過 strong baselines。
- rolling full adaptation 不穩定：E1/E2/E3/E4 Top-1 = 0%／25%／100%／50%，NLL = 5.515／2.729／0.058／3.479。Top-3 100% 只表示答案仍在候選集合，不代表機率分布正確；ECE 0.5088 仍高。
- 資源：76,757 tokens、888.76 秒 local-model latency、23.55 秒 numeric work；正式報告：`analysis/m9_second_person_transfer_acceptance_2026-08-15.md`。
- M9 scoped 13 tests 與 Python compile 通過。Web 第一頁新增 `Transfer · M9`：零樣本→參數替換→完整適配、B4/B5 floor、四個 rolling windows、逐 case prediction、8 個 unchanged-core hashes、parser/cost/claim boundary 同頁顯示。
- Safari 實際重載、從 E1 切到 E3 並核對 cases 與核心邊界；既有 8 個 tabs 全保留、沒有關閉。證據：`analysis/m9_safari_transfer_e1_2026-08-15.jpeg`、`analysis/m9_safari_transfer_e3_2026-08-15.jpeg`、`analysis/m9_safari_transfer_core_boundary_2026-08-15.jpeg`。
- 完整專案目前粗略 65–70%；behavior-research engineering architecture 約 95–100%，central scientific evidence 仍約 15–20%，formal Uruha evidence 仍為 0，DATA GATE 仍 blocked。
- 下一個依賴順序是 M10：先讓 frozen behavior distribution 成為 language realization 的上游 authority，再做 persona consistency／自然日文／人類盲評與成本、安全驗收。依 master spec，voice／VRM 不能在 prediction research 尚不穩定時搶先成為主張或遮蔽負結果。

### 7.21 2026-08-15 M10／M10.1 Behavior-authoritative Language 實際完成狀態

- 先凍結 `research/m10_behavior_authoritative_language_plan.md`：把 language realization 拆成「是否忠實實現上游 behavior」與「上游 behavior 是否符合 observed future」，避免用流暢日文掩蓋 prediction error。
- 16 個 Synthetic Mira cases 全納入；每案比較 `L0_DIRECT`、`L1_PREDICTED_BEHAVIOR`、`L2_ORACLE_BEHAVIOR`。三條件同一 `qwen3.5:9b`、event/state、development-only Uruha surface brief、temperature 0、seed、output budget 與硬體。Oracle 明確 future-leaking，只作上限、禁止 runtime。
- M10 第一次真模型 run 在 5 calls 後停於 `M-E1-01::L1` classifier parse：模型給了完整六類分布但 key 為 `classification`。原始失敗 SHA `ecddec64124d0f614f708d04f14ff6eb6cdadcda033882e6d684514b478ed2b4` 已鎖定、無 retry。
- M10.1 另立單一 alias amendment，只接受 exact six-label `classification`→`probabilities`，raw 保留、錯誤 label set 仍 fail closed；data、prompts、model、conditions、metrics、hypotheses 不改。完整 144/144 calls，6 次 alias normalization。
- 每案三條件先各做一次 token preflight；16/16 scored prompt token range 都為 0。資源：124,226 prompt tokens、5,790 completion tokens、815.79 秒模型時間、0 production memory writes、0 tool/physical actions。
- Frozen metrics：Direct outcome 10/16 = 62.5%；Predicted authority 14/16 = 87.5%，但 outcome 9/16 = 56.25%；Oracle authority/outcome 16/16 = 100%。六／九 hypotheses 通過；Predicted 沒勝 Direct，總科學 gate 失敗。
- L1 具體分解：7 案 predictor 正確且 realization 忠實；7 案 predictor 錯而 realization 忠實，形成「忠實地說錯」；另 2 案 realization 繞過錯誤 authority，碰巧修正 outcome，不能當成架構保證。
- Surface gate 失敗：Direct/Predicted/Oracle 完整 contract pass = 75.0%／43.75%／25.0%。主要為 polite-register drift（4／8／12 次），各有一個 quote-wrapper failure；沒有私人 Uruha 事實或讀心宣稱。
- Same-model classifier 只是 proxy。16-item A/B/C blind packet 與 key 已分離，但目前 M10 獨立真人評分者為 0，因此 human preference、felt understanding、Uruha fidelity 都不成立。
- 正式 result SHA `631fb2096d65a70fa91c9dd7fc75a3a95f6519bee07d382af502de1df279ce3c`；報告 `analysis/m10_behavior_authoritative_language_acceptance_2026-08-15.md`；M10 scoped 13 tests 與 Python compile 通過。
- Web 第一頁新增 `Behavior→Language · M10`：16 案可切換的 event→distribution→utterance→decoded act→observed outcome node chain，三條件日文並排、7/7/2 error matrix、outcome/surface bars、成本與 claim boundary。
- Safari 實際重載並核對 M-E1-01 faithful-wrong 與 M-E2-03 lucky-bypass，8 個既有 tabs 全保留。證據：`analysis/m10_safari_faithful_wrong_e1_01_2026-08-15.jpeg`、`analysis/m10_safari_lucky_bypass_e2_03_2026-08-15.jpeg`、`analysis/m10_safari_error_matrix_boundary_2026-08-15.jpeg`。
- 完整專案目前粗略 70–75%；behavior-research engineering architecture 約 95–100%，central scientific evidence 仍約 15–20%，formal Uruha evidence 仍為 0。
- M10 仍 active。下一個必要工程 gate 是 source-disjoint、behavior-preserving casual-register realization：要降低敬體／label-paraphrase，但不得降低 authority alignment；之後才進獨立人類 blind ratings。Voice／VRM 仍為下游示範，不是 predictive validity 證據。

### 7.22 2026-08-15 M10.2 Behavior-preserving Register Repair 實際完成狀態

- M10.2 是看到 M10.1 敬體失敗後才設計的 remediation，不是 untouched global holdout。它另外建立 18 個 source-disjoint 中／英／日事件（各 6 案；六種 observable behavior 各 3 案），與 M9／M10 event overlap 為 0；每案共享同一個 one-pass 初稿，再只做 casual-register repair，避免把「重生一個答案」誤當表面修正。
- 同一 `qwen3.5:9b` 在 72/72 calls、0 retries 下完成：S0 one-pass surface 13/18 = 72.22%、authority 18/18 = 100%；S1 repair surface 18/18 = 100%、authority 17/18 = 94.44%。12/18 句實際改變，五個 polite-register failure 全修正，0 個 surface pass→fail。
- 七條 preregistered hypotheses 通過五條，整體 gate 仍失敗：修正後 authority 未保持至少等於 S0，而且出現一個 aligned→misaligned proxy regression。唯一案例為 `R-JA-06`：`同じミスが三回も起きたから、ちょっと待ってて確認し直そう。` 修成 `同じミス三回もやらかすなら、ちょっと待ってて確認し直そう。`；固定 same-model classifier 將後者從 `pause_and_reassess` 判成 `defer_commitment`。這可能是實際 drift，也可能是 classifier limitation，禁止事後改 classifier 消除它，必須交由 blind human raters。
- 資源：72 calls、25,612 prompt tokens、4,261 completion tokens、374.93 秒 model latency、0 production writes。正式結果 SHA `a3adfdefc98068b6b75232264bfae2f053e0d9e412d8d383309f4bb18caaa92e`；result lock SHA `7a9712fe9f60593df62fd0e3751bef9dc0c5bd9d9b0f7a8bbeb9319015ca22b7`；報告 `analysis/m10_2_behavior_preserving_register_acceptance_2026-08-15.md`。
- 18 組 blind A/B packet 與答案 key 已分離，但獨立評分者仍為 0；automated surface compliance 改善不等於真人自然度偏好、行為保持或 Uruha fidelity 證據。
- Web 第一頁新增 `Register Repair · M10.2`：逐案例顯示 same-intent before→repair→decoded behavior、18 案矩陣、surface gain、authority cost、資源與人評邊界。Safari 已核對 `R-EN-04` 修正成功、`R-JA-06` 唯一 proxy regression 與下方 gain/cost boundary；8 個既有 tabs 全保留。證據：`analysis/m10_2_safari_surface_repair_en04_2026-08-15.jpeg`、`analysis/m10_2_safari_authority_regression_ja06_2026-08-15.jpeg`、`analysis/m10_2_safari_gain_cost_boundary_2026-08-15.jpeg`。
- 完整專案粗略仍為 70–75%；language engineering 多一個可檢驗修正器，但 central scientific evidence 仍約 15–20%，formal Uruha evidence 仍為 0。M10 仍 active；下一個不可跳過的 gate 是收集可追溯的獨立 blind ratings。Codex 可先完成 rating instrument、匿名化、資料驗證與分析器，但不得自行捏造人類評分。

### 7.23 2026-08-15 M10.3 Blind Human-rating Instrument 實際完成狀態

- 在任何 M10.2 真人評分之前，已凍結 `research/m10_3_blind_human_rating_plan.md`、preregistration 與 artifact lock。研究問題只問：S1 casual-register repair 是否在這 18 組 remediation pairs 上改善真人自然度評分，同時保留語意、authorized behavior 與 non-overclaiming。
- 固定四個 1–5 paired dimensions：`semantic_preservation`、`behavior_fit`、`natural_casual_japanese`（primary）、`non_overclaiming`，再加 A／B／tie／both_bad preference。至少三位完整獨立真人；平均 pairwise quadratic-weighted kappa ≥0.40；自然度 delta ≥+0.50 且 item-cluster bootstrap CI lower >0；其餘三維 delta 各 ≥−0.15；changed decisive pairs 的 S1 preference >0.60。門檻已先鎖，失敗不能事後改。
- 新增 `m10_3_register_human_eval.py`：驗證完整性、distinct pseudonymous raters、attestations、packet SHA、paired scores 與 duplicate；只分析完整 raters，輸出 S1−S0 deltas、bootstrap CI、agreement、preference 與強制 `R-JA-06` case report。少於三人、partial、raw identity、未聲明 key unseen 或 malformed data 一律 fail closed。
- 新增 `uruha_register_rating_lab.py` 與 Web `Blind Rating · M10.3` tab：collection surface 只載 blind packet、不載 hidden key；評分者匿名代號只保存 SHA-256 pseudonym；資料原子寫入隔離 `analysis/m10_3_register_ratings/`，另留 audit stream，不寫 production memory、chat logs 或 persona facts。
- M10.3 tests 9/9（含 instrument-lock test）已通過；compile、diff check 與 lock validation 也通過。零評分 analyzer 明確輸出 `complete_rater_count=0`、`claim_authorized=false`，沒有用 synthetic scores 冒充真人。
- Safari 已載入 A/B 評分頁，顯示 `0/3` pending boundary；空白表單被拒絕且 rating directory 仍無檔；8 個既有 tabs 全保留。證據：`analysis/m10_3_safari_blind_rating_entry_2026-08-15.jpeg`。報告：`analysis/m10_3_register_human_eval_instrument_acceptance_2026-08-15.md`。
- M10.3 完成的是可重現的人評入口，不是人評結果。M10 仍 active 且 human gate blocked；目前 0 raters，不得宣稱真人自然度偏好、behavior preservation、felt understanding 或 Uruha fidelity。依 master spec，prediction stability 尚未建立，所以 voice／VRM 不得升級為核心研究主張。

### 7.24 2026-08-15 M11 Research Evidence Closure 實際完成狀態

- M11 不是新科學實驗；它完成 master spec 要求的 final claim table 與老師可直接理解的總圖。`configs/m11_research_evidence_map.json` 綁定 master spec 與 M1–M10.3／Uruha data gate 共 13 個 SHA source，任何 frozen source 漂移都 fail closed。
- Web 第一頁改為 `Research Closure · M11`：以 `sealed history → structured memory → estimated state → transition → behavior probability → Japanese realization → future/human judgment` 顯示研究方程；12 個 M0–M10.3 stage 可切換，且每個 stage 分開顯示 decisive metric、evidence 與 allowed claim。
- 總圖明確保留 M8 `B5 81.25% > Ours 62.5%`、M9 `full adaptation 43.75% < B4/B5 75%`、M10.1 predicted outcome 56.25% < direct 62.5%、M10.2 authority 100%→94.44%、M10.3 0/3 raters 與 formal Uruha 0%。
- 四條成熟度軸不混用：engineering 95–100%、central science 15–20%、formal Uruha evidence 0%、dependency-weighted internal estimate 70–75%。最後一項明標為 planning estimate，不是 model-quality score。
- claim matrix 分成「目前有證據支持／目前不能宣稱／完成研究還缺」，並把兩個真人 gate 與核心 science rerun 串起來：V7 雙人 18-slot reliability → formal temporal data rerun → M10.3 三人 blind rating。Voice／VRM 不得跳過 prediction stability。
- M11 renderer 3/3 tests、13 source hashes、compile、diff check 通過；M9–M11 最終 scoped regression 49/49 通過，包含 M10.3/M11 locks。Safari 已重載、切換 M8→M9、核對下方 claim/gates，8 tabs 保留。證據：`analysis/m11_safari_research_equation_spine_2026-08-15.jpeg`、`analysis/m11_safari_negative_transfer_m9_2026-08-15.jpeg`、`analysis/m11_safari_claims_and_human_gates_2026-08-15.jpeg`；報告：`analysis/m11_research_evidence_closure_acceptance_2026-08-15.md`。
- M11 關閉「展示與 claim 治理」工程缺口，但不增加科學證據。接下來不能由 Codex 假造的硬 gate 是：兩位獨立 V7 coders 與三位獨立 M10.3 raters；正式資料完成後，還必須重跑並面對 M8/M9 是否仍失敗。

### 7.25 2026-08-16 Human Test Platforms 啟動狀態

- 主 Observatory `http://127.0.0.1:7860` 正常；Safari 已開到 `Blind Rating · M10.3`。三位不同真人各用不同匿名代號完成同一份 18-pair packet，評分前不得看 hidden key。目前 rating files = 0、complete raters = 0/3。
- V7 雙人 codebook pilot 已啟動兩個隔離 local servers：port 7866 綁定 coder `coder-01`／private ledger `pilot-v7-coder-01.json`；port 7867 綁定 `coder-02`／`pilot-v7-coder-02.json`。兩份 ledger 都在 gitignored `analysis/local_public_persona_contrast_coding_v5/`，目前各 0/18。
- Safari 已開 coder-01 的 V7 頁，顯示 frozen search start、官方 YouTube link、中文 codebook manual、event boundary、分類欄位與兩個 no-quote/no-skipping attestations。coder-02 服務已啟動但不替第二人開答或填答；同一真人不得完成兩份 ledger。
- V7 每位 coder 的 18 格最大 frozen search window 合計 6,793 秒（約 113 分鐘原始影片上限），另加分類時間；M10.3 每位 rater 為 18 組 A/B。所有平台可關閉 browser tab，已保存資料仍留在本機；server 重啟後 session token 會改變，需從新啟動輸出取得 URL。
- 完成人類工作後才能執行 V7 reliability 與 M10.3 hidden-key analyzer。Codex 不得替人填、複製第一人的答案給第二人、或用 synthetic ratings 滿足門檻。

### 7.26 2026-08-17 M12 論文方法對齊評測實際完成狀態

- 已建立回溯性、SHA-bound 的 `M12 Literature-Grounded Evidence Audit`。它不是新 preregistration，也沒有重跑模型；只對 M6、M8.1、M9.1 已凍結的逐事件機率重新做成對統計。
- 評價方法直接對齊 published methods：Gneiting／Raftery 的 proper scoring rules（Brier、NLL）、Guo 等人的 calibration／ECE、Peyrard 等人的 instance-level paired evaluation、Berg-Kirkpatrick 等人的 bootstrap significance、LoCoMo 的長記憶任務分解，以及 Liu 等人對自動 dialogue metrics 的限制。
- primary baseline 固定為 master spec 的 `B5_STRUCTURED_HISTORY`，禁止從測試集事後挑較弱 baseline。每條證據軌報告 20,000 次 paired bootstrap 95% CI、exact sign-flip p、Top-1 exact McNemar、逐案 win/tie/loss；ECE 因 n=8／16 只作描述。
- M6（n=8）方向有利 Ours，但 Brier Δ `-0.1960` CI `[-0.5414,+0.2500]`、NLL Δ `-0.5009` CI `[-1.0360,+0.1357]`，均不確定。M8（n=16）方向有利 B5；M9（n=16）Brier Δ `+0.5744`、p=`0.0455`，NLL Δ `+1.9897`、p=`0.0230`，成對 proper-score 統計支持 B5。
- replication 結論為 Ours 1/3、B5 2/3、formal real-person tracks 0；`central_same_model_superiority_supported=false`。此負結論已鎖定，不得覆寫追分。
- M7 的 80 次 named intervention 與 40/40 direct explanation interventions 仍證明機率計算可干預，但 preference／relationship／temporal 的移除方向在 M8 重現為 0/3；只能主張 computational faithfulness，不能主張心理變數已被真人驗證。
- V2.22 50-turn memory 依 LoCoMo-style task decomposition 重述：Uruha `4/5`、recent-8 `1/5`、full transcript `4/5`；只支持 bounded persistence over recent context，不勝 full transcript，且是 `1.81x` tokens、`23.24x` latency。
- 正式產物：`configs/m12_literature_grounded_evaluation_protocol.json`、`configs/m12_literature_grounded_evaluation_result_lock.json`、`analysis/m12_literature_grounded_evaluation_result.json`、中文報告與 standalone graphical dashboard。M12 scoped tests 6/6 通過。
- M12 完成的是目前 frozen evidence 的可信統計總評，不新增 formal Uruha ground truth、人類自然度或 felt-understanding 證據；中央科學成熟度不因「多一份報告」而上調。

### 7.27 2026-08-17 M13 PUB Published Pragmatics Benchmark 實際完成狀態

- 在 Uruha V7 雙人 temporal coding 尚無人類真值時，另接 ACL 2024 PUB 公開 MIT 語用基準，測試較窄、可由既有答案自動驗證的 implicature／sarcasm／presupposition／deixis；這不取代 formal Uruha 軌。
- 先凍結 4 tasks × 16 = 64 個 hash-ranked cases，排除 schema audit 時已看過的 IDs 0／1；所有條件使用相同 `qwen3.5:9b`、相同題目與選項排列。Primary 固定為 Ours versus 強 `B1_GENERIC_DELIBERATION`，Direct 只作 secondary。
- 第一次三呼叫 contract probe 發現 B1 被 220 token 截斷、Ours 把 index 寫成 array；立即停止，另立 M13.1 amendment，只把 num_predict 220→320、限制 reasoning 欄位長度並澄清純整數。三次 probe 永久排除正式分數，題目、模型、baseline、metrics 與 gates 不改。
- 正式 192/192 calls、0 retries、answer parse 100%。Direct `45.31%`、Generic `75.00%`、Ours `70.31%`。Ours−Generic `−4.69pp`，paired bootstrap CI `[-12.5,+1.6]pp`、McNemar `p=.375`，win/tie/loss `1/59/4`；正式 superiority gate 失敗。Ours−Direct `+25.0pp`、CI `[+10.9,+39.1]pp`、`p=.0025`，只證明 reasoning 條件勝 immediate answer，不證明專屬語用架構勝強 LLM。
- Task 層：T2 93.75% vs Generic 100%、T6 75% vs 81.25%、T12 31.25% vs 31.25%、T13 81.25% vs 87.5%。Presupposition 對三條件都很弱，是基礎能力缺口，不可由相對分數掩蓋。
- Posthoc implementation-fidelity audit 嚴格檢查完整 keys/types：Ours 只有 `15/64 = 23.44%` 完整 schema，多數漏 `pragmatic_target`；因此這次是「實際 prompt 行為」的負結果，不是完整 cognitive loop 的乾淨因果測試。answer parse 不能冒充認知步驟已執行。
- 資源：正式 192 calls；Direct／Generic／Ours prompt tokens 14,058／16,810／19,562，completion 514／6,723／5,544，latency 114.2／462.0／411.8 秒；production memory writes 0。
- 正式產物：protocol、M13.1 amendment、answer-free case manifest、raw/result、中文報告、standalone interactive dashboard、result lock；M13 scoped tests 8/8 通過（完成時）。下一個有效單變因是 JSON-schema 強制完整欄位後，用未使用 PUB IDs 建立 source-disjoint replication；不得重用這 64 題追分。

### 7.28 2026-08-17 M14 Schema-enforced PUB Replication 實際完成狀態

- M14 只改一個 M13 failure mechanism：Ollama `format` 從 generic JSON 改為 condition-specific JSON Schema，所有 expected keys required、types／uncertainty enum 固定、禁止 additional properties；prompt、`qwen3.5:9b`、decoding、tasks、n、baseline、metrics、gates 均保留。
- Formal sample 使用相同 hash ranking 的每 task 第 17–32 名，共 64 個新 cases，與 M13 overlap `0`；三次 schema probe 使用已看過且永久排除的 task 2 ID 0，3/3 完整 schema 後才准 formal run。
- 正式 192/192 calls、0 retries、Direct／Generic／Ours answer parse 與 full schema 全為 100%。因此 M13 的 implementation-fidelity confound 已修掉。
- Direct `62.50%`、Generic `54.69%`、Ours `64.06%`。Primary Ours−Generic `+9.375pp`，paired bootstrap CI `[-6.25,+25.0]pp`、McNemar `p=.3269`、win/tie/loss `16/38/10`；方向有利 Ours 但不確定，正式 gate 失敗。Ours−Direct 僅 `+1.56pp`、CI `[-12.5,+15.6]pp`、`p=1.0`。
- Task heterogeneity 很大：T13 deixis `+37.5pp`、T2 indirect `+12.5pp`、T12 `0`、T6 sarcasm `−12.5pp`（Ours−Generic）。不可用總平均掩蓋反諷退步。
- 跨 split 效應方向未重現：M13 Ours−Generic `−4.69pp`、M14 `+9.375pp`；又因 M13 Ours schema 只有 23.44%，禁止把兩者直接 pool。M14 只授權「schema enforcement 建立 implementation fidelity」，不授權 pragmatic superiority。
- 資源：formal 192 calls；Direct／Generic／Ours prompt tokens 14,836／17,588／20,340，completion 514／6,656／6,242，latency 117.2／462.6／456.2 秒；production memory writes 0。
- 正式產物：M14 preregistration、answer-free disjoint manifest、excluded probe、raw/result、中文報告、interactive graphical dashboard、result lock。下一個有效步驟不是追加樣本追 p-value；必須先做 prospective power plan，並把 T13 benefit／T6 harm 拆成新 ID 上可反駁的 mechanism hypotheses。
- Safari 真實驗收先發現 dashboard JavaScript newline escaping 讓動態 cards/matrix 空白；修正後 `node --check` 通過，Safari 重載可見三條件 cards、accuracy bars、四 task、M13→M14 方向反轉、64-case matrix，並成功切換到 Ours 查看完整 schema。11 個 tabs 均保留，沒有關閉既有頁面；新開的 M14 static-file tab 可安全關閉且不依賴 server。證據：`analysis/m14_safari_overview_2026-08-17.jpeg`、`analysis/m14_safari_case_trace_2026-08-17.jpeg`。
- 最終 scoped regression 為 M12+M13+M14 `19/19` tests；Python compile、M14 dashboard `node --check`、`git diff --check` 全通過。原始 dirty checkout 未觸碰；安全 worktree 的既有大批未提交研究 stack 全保留，沒有 commit／PR／外部部署。

### 7.29 2026-08-17 M15 Prospective Deixis Confirmation 實際完成狀態

- M15 把 M14 的 T13 `+37.5pp` 小樣本訊號明確當成 development hypothesis，不當成證明；正式問題只問：strict full-schema 的 explicit pragmatic decomposition 是否在全新 PUB T13 deictic-reference cases 上，勝過同模型、同題、同解碼、同樣 strict schema 的強 `B1_GENERIC_DELIBERATION`。
- 在任何 formal generation 前已凍結 SESOI `+15pp`、two-sided exact McNemar `alpha=.05`、90% power、M14 T13 planning discordance `10/16=.625`、固定 `n=300`、零 retry／零 optional stopping。精確 unconditional power 為 `0.90072385`；n=299 未達 90%，n=300 才通過。
- answer-free manifest 使用相同 hash ranking 的 T13 第 33–332 名，共 300 個新 IDs；和 M13／M14 formal samples overlap `0`。probe 只用已看過且永久排除的 T13 ID 0，兩條件 2/2 full schema 後才進 formal run。
- 正式 `600/600` local-model calls 完成，0 retries；Generic／Ours answer parse 與 full schema 都是 100%，production memory writes `0`。唯一 raw SHA-256 為 `0f740971332eef70e602a898aa9cfda3810eff0bef3537d2e2dac0f6905a2d99`；相同 raw 連續 analysis 兩次的 result／report／dashboard SHA 完全一致。
- Confirmatory result：Generic `52.67%`，Ours `68.67%`，paired delta `+16.0pp`，item-paired bootstrap 95% CI `[+7.0,+25.0]pp`，exact two-sided McNemar `p=.00079446`，Ours-win／tie／Generic-win `123/102/75`。answer parse、full schema、point estimate SESOI、CI > 0、McNemar 五個事前 gates 全通過，decision 鎖定為 `pass_focused_deixis_advantage`。
- 必須精確解讀：觀察到的 sample effect `+16pp` 跨過 SESOI 且 CI 排除 0，但 CI lower 只有 `+7pp`，所以 M15 證明正向 focused advantage，不證明 population effect 至少必然為 `+15pp`。M14 `+37.5pp` 到 M15 `+16pp` 方向重現但 magnitude attenuation `−21.5pp`；M14 是 hypothesis-selection data，禁止和 M15 pool。
- Posthoc exploratory question families 全為正方向：action attribution `+30.0pp`（n=40）、entity state/location `+20.5pp`（n=112）、epistemic certainty `+8.6pp`（n=93）、person location `+9.1pp`（n=55）；後兩者 family CI 含 0，不能升格為 confirmatory subclaims。context-length 四分位 delta 也全正，但只有第三四分位單獨 CI 排除 0。
- 成本同時保留：Generic total tokens `153,888`、Ours `167,718`，Ours `+13,830 / +9.0%`；aggregate latency `2286.3s` vs `2395.4s`，Ours `+109.2s / +4.8%`。不得把 accuracy improvement 說成免費。
- 授權主張只限：在 frozen qwen3.5:9b、單一 deterministic option permutation、300 個 disjoint public PUB T13 cases 上，explicit pragmatic decomposition 對 exact deictic-reference resolution 有 `+16pp` 的 same-model paired advantage。不得外推為 general pragmatics、unseen-model／pretraining-uncontaminated generalization、長期人類理解、felt-understanding、Uruha fidelity、意識或人腦方程式。
- 正式產物：`configs/m15_deixis_confirmation_preregistration.json`、answer-free manifest、`configs/m15_deixis_confirmation_result_lock.json`、raw/result、`analysis/m15_deixis_confirmation_report_2026-08-17.md`、standalone interactive `analysis/m15_deixis_confirmation_dashboard_2026-08-17.html`、runner 與 tests。
- Dashboard 完整顯示同一輸入分流到 Generic 與 Pragmatic nodes、accuracy／CI／p／五 gates／成本／探索性題型，並可從 198 個 discordant cases 切換；每案直接並排 Generic reasoning 與 Ours 的 literal／target／evidence／alternative schema，完整輸入可收合。
- Safari 外部瀏覽器已真實驗收首頁與 `OURS_WIN · PUB-T13-112`：下拉與並排 trace 實際更新，JavaScript 可執行。Safari 原 11 個 tabs 全保留，只新增最右側 M15 static-file tab；可安全關閉且不依賴 server。證據：`analysis/m15_safari_overview_2026-08-17.jpeg`、`analysis/m15_safari_case_trace_2026-08-17.jpeg`。
- 最終 M12–M15 scoped regression `24/24` tests；Python compile、Dashboard `node --check`、deterministic reanalysis hash check、`git diff --check` 全通過。原始 dirty checkout 未碰、既有 safe-worktree changes 全保留，沒有 commit／PR／merge／外部部署。
- 這是一個完整但 bounded 的「可看出優勢」研究單元，不是完整專案。下一個有效測試是另一個 frozen option permutation 加至少一個 disjoint base model replication；human felt-understanding 與 longitudinal correction 必須另用 fresh multi-turn holdout／blind human evaluation，不能拿 M15 multiple-choice pass 代替。

### 7.30 2026-08-24 M16 Adaptive Person Model Runtime 實際完成狀態

- 開發目標已由論文導向改為產品研發導向；M1–M15 保留為歷史驗證，不再支配工程 backlog。M16 的問題是把既有「理解／期望回覆」研究接進真實對話，而不是再做一個 lab 分數。
- 新增 `uruha_adaptive_person_model.py`：把當輪證據表示為具名 state atoms，對六個 response policies 評分，保存上一輪 prediction，依下一輪 support／contradict／uncertain 更新策略可靠度與可撤銷 atoms；只保存 digest 與結構化參數，不保存原始文字。
- `uruha_brain_mac.py` 與 `uruha_runtime.py` 已在每個真實 turn 載入模型、觀察回饋、建立狀態、選策略、把策略接入 speech plan、保存更新並輸出 trace。危機／安全、事實回憶與既有 boundary plan 不被 adaptive policy 覆蓋。
- 新增 final surface commitment guard：若 graph 已選策略但模型表面沒有執行，最後可見日文會補上該策略核心；因此「trace 看似成功但嘴巴沒做」不再算完成。
- Safari 隔離實測：第一次 `我坐不住，腦子停不下來。` 回覆 `てか、寝てないのか、考え事で止まんないのか、まずそこだけどっち？`；使用者說 `不是要方法，是等你吐槽。` 後，系統明確修正並吐槽；控制式重啟後相同首句直接回 `てか、朝から脳内だけ二十四時間営業かよ。止まる気ゼロじゃん。`。
- graph 實際顯示 feedback contradiction、三個 learned atoms、候選與 selected policy、persistence revision、surface commitment；product-first comparison card 說明 direct generation 與 adaptive runtime 的差別。
- 實測額外抓到並修正一個否定判斷錯誤：`不是要吐槽，是真的想要方法` 現在不會被當成邀請玩笑，且有專屬 regression。
- 最終 scoped regression `141/141` 通過；Python compile、`git diff --check` 通過。adaptive JSON 對四段測試原文掃描為 0 命中，正式 DB 未被這次 Safari 隔離 session 污染。
- 完成邊界：M16 100% 完成，但整體產品尚未完成。策略集合仍窄、learned preference 尚未 context-scoped、本機首輪約 65–85 秒、未有廣泛真人盲評；不得宣稱讀心、人類等價或普遍優於所有 LLM。
- 正式報告：`analysis/m16_adaptive_person_model_runtime_acceptance_2026-08-24.md`。下一個單一開發里程碑是 M17 context-scoped adaptation + latency budget。

### 7.31 2026-08-24 M17 Context-Scoped Adaptation + Latency Budget 實際完成狀態

- M17 把 M16 global learned atoms 升級為 `domain:interaction_kind:relationship_band` categorical scopes；每個 scope 有獨立 atoms、policy reliability、revision age、confidence decay 與 TTL。legacy M16 global atoms 只保留診斷，不會被 M17 無條件套用。
- 下一輪不再一律視為上一輪 feedback：回答 `calibrate_need`、明確提到上一輪想要／不要的接法、或直接確認／否定時才 linked；單純換話題會是 `uncertain + linked=false + atom_changes=[]`，不污染上一 scope。
- 新增 guarded planner fast path：只有 M17 active、margin 足夠、非 safety／boundary／factual recall 時，才跳過之後會被 adaptive policy 覆蓋的一般 LLM planner；hypothesis、pragmatics、longitudinal model、persona appraisal、self-monitor、visible Japanese guard 仍保留。
- 明確要求或 exact-scope 已驗證的 response policy 必須真的到達 visible surface；修正了「graph 選 playful_tease，但嘴巴仍問 generic clarification」的 trace／surface 分裂。
- Safari 圖表修復 `plan` unknown-lane `KeyError: reason`、compact candidate string `AttributeError`；新／未知 runtime stage 會落到有效 lane，完整與 compact trace 都能 render。
- 真實 Safari 也抓到 `finish it` compact 成 `finishit` 後誤中 `shit` 的英文 routing bug；已改成單一 Latin keyword 不跨真實 word boundary compact matching，實際辱罵 guard 仍保留。
- 隔離四輪結果：初始 ambiguous arousal→`calibrate_need`；明確否定→linked contradiction + `playful_tease`；新 report deadline→task scope、learned 0、`solve_regulation`、feedback linked=false；回到相同 arousal→learned 3 + `playful_tease`。四輪 visible replies 全為自然日文且 graph 的 selected／surface 一致。
- warm user wait 為 1.1033／1.1467／1.1766／1.2135 秒，cognition 為 0.0139／0.0131／0.0147／0.0161 秒；早期約 65–85 秒的重複 planner 等待已從 M17 decisive path 消除。cold brain initialization 仍約 45 秒，但由 background prewarm 承擔，不能宣稱冷啟成本消失。
- 停止並重啟完整 Web process 後，相同 arousal 首句仍載入 learned 3、選 `playful_tease`、visible true；wait 1.1814 秒、cognition 0.0202 秒。adaptive JSON 未包含五段 Safari 原文，revision=1；正式 DB 未用，所有資料在 `/tmp/uruha-m17-final.TVE9Lt`。
- 最終 focused regression `150/150`；Python compile、`git diff --check` 通過。Safari 只使用既有 local tab，其他 15 tabs 未關。證據：`analysis/m17_safari_context_isolation_2026-08-24.png`、`analysis/m17_safari_comparison_graph_2026-08-24.png`、`analysis/m17_safari_scope_graph_2026-08-24.png`。
- 完成邊界：M17 100% 完成，但整體產品尚未完成。七個 domain、exact-only hierarchy、marker-based feedback linkage、六個固定 policies 與約 45 秒 cold init 都仍是限制；不得宣稱讀心、人類等價、完整人腦方程式或普遍勝過 LLM。
- 正式報告：`analysis/m17_context_scoped_adaptation_latency_acceptance_2026-08-24.md`。下一個單一開發里程碑是 M18 hierarchical context + adaptive policy coverage。

### 7.32 2026-08-24 M18 Hierarchical Context + Adaptive Policy Coverage 實際完成狀態

- M18 把 exact-only scope 擴成 `exact 1.00 / domain 0.62 / relationship 0.36` 三層 hierarchy；每個 used/rejected atom 或 dimension 都保留來源 scope、match level、有效信心、age 與 gate reason。
- negative-transfer gates 使 current explicit request、physical/sleep evidence、情緒／傾聽需求與 relationship boundary 優先於歷史互動風格。relationship fallback 只能轉移 directness/humor/distance，不能轉移 solution/listening 等內容需要。
- 回覆策略加入 care、directness、humor、listening、actionability、distance 六維 composition；每個 semantic anchor 有 3–4 個 casual Japanese variants，選擇可重現但不再每輪同一句，final Japanese/commitment guard 仍保留。
- 回饋歸因能把 `Exactly, that's right.` 的上一輪支持與同一句後半的新話題分開；新話題的 explicit atoms 不會錯寫回上一 scope。
- Safari 真實案例：relationship transfer 顯示 `used 3 / blocked 3` 且選 `share_arousal`；domain reuse 顯示 `used 9`、選 `playful_tease` 與新日文變體；明確求解顯示 `blocked 3`、actionability 0.96；頭痛＋整夜未睡顯示 physical scope、`blocked 4`、care 0.92、humor 0.02。
- 三個 decisive backend trace 的 user wait 是 1.1630／1.1645／1.2412 秒，cognition 0.0205／0.0165／0.0133 秒；guarded fast path 均實際省下一次 general planner call。
- adaptive store 跨兩次完整 Web process restart 保留；最終 schema M18/version 3/two scopes，所有 Safari 測試片段在 adaptive JSON 都為 0 命中，正式 DB 未污染。
- M18-specific 11/11 與 focused compatibility 100/100 通過；compile、diff check 通過。另有 57 個歷史測試中的 6 個既有 fixed-string/hash lock failure，已分開記錄，沒有為 M18 改寫歷史 lock。
- Safari 只操作既有本機 UruhaBrain tab，其他 15 tabs 未關閉或修改。證據：`analysis/m18_safari_hierarchical_transfer_2026-08-24.jpeg`、`analysis/m18_safari_domain_reuse_latency_2026-08-24.jpeg`、`analysis/m18_safari_negative_transfer_dimensions_2026-08-24.jpeg`、`analysis/m18_safari_graph_comparison_card_2026-08-24.jpeg`、`analysis/m18_safari_runtime_node_graph_2026-08-24.jpeg`。
- 完成邊界：M18 是 bounded product milestone，不是讀心或完整人腦方程式。七個 manual domains、marker-based evidence、有限 semantic anchors/variant bank、廣泛真人驗收仍未完成。
- 真實 Safari 額外暴露 M19 問題：brain trace 約 1.2 秒，但 autonomous poll 與人類 submit 共用 queue 時，頁面層可顯示 43.7 秒。下一個里程碑是 M19 human-priority cognitive scheduling，不得用只報 cognition time 隱藏此缺口。

### 7.33 2026-08-24 M19 Human-Priority Cognitive Scheduling 實際完成狀態

- Web submit 先經 queue-free human admission marker，再進獨立的 human concurrency lane；human waiter 必定在 `finally` 清除。proactive poll queue-free，真人 turn 仍序列化，避免同一 session brain 被並行改寫。
- background cycle 在 human waiting、brain 未 ready、brain lock busy 或 recheck 發現 human 時直接 skip；brain lock 使用 non-blocking acquire，背景工作不會排到真人前面。Web background consolidation 明確 `allow_model_maintenance=False`，CLI/default 行為不變。
- M19 end-to-end trace 分開 `frontend_queue_wait_seconds`、`runtime_lock_wait_seconds`、`cold_brain_initialization_seconds`、`brain_work_seconds`、`surface_stream_seconds`、`handler_total_seconds` 與 final delivery；graph 第一節點是 scheduler admission，最後節點是 final timing。
- 1 秒 autonomous stress session 的前四個 warm turns：queue 0.0132–0.0177 秒、brain lock 全為 0、brain 1.1451–1.2816 秒、surface 2.2107–3.8951 秒、end-to-end 3.5267–5.3607 秒；中文／英文輸入的 visible replies 全為日文。
- 第 49 次 background tick 後，真人訊息 `Now answer ... Say you are here.` 得到 `うん、ここにいるよ。`。queue 0.0933 秒、brain lock 0 秒，scheduler 記錄 `human_waiters=1`、`background_status=skipped`；但非 fast-path brain work 57.4038 秒、end-to-end 59.8518 秒，20 秒總延遲 gate 未通過。這是排程 pass、總延遲 fail，兩者不可混稱。
- M19 scoped contracts 6 個；focused compatibility `106 passed in 4.92s`，compile 與 diff check 通過。另有一個固定 2026-07-18 日期的歷史 24-hour-window consolidation test 因當前日期自然失效，未為 M19 改寫舊 fixture。
- 真實多輪另暴露兩個 M20 缺陷：明確糾正 `只想一起等結果` 後仍三次重複舊 clarifier；partial reply 每段重傳完整 cognition/graph payload，使 surface latency 逐輪增加並讓 Safari 暫時留在空白 `streaming_reply`。
- 正式報告：`analysis/m19_human_priority_cognitive_scheduling_acceptance_2026-08-24.md`。下一個里程碑是 M20 correction-aware surface commit。

### 7.34 2026-08-24 M20 Correction-Aware Surface Commit 實際完成狀態

- 明確 correction 可成為當輪 authority；上一輪 `calibrate_need` 被標記 contradicted 並撤銷，repair policy 改為 `share_arousal`，舊 clarifier surface 被加入 `must_avoid`，最終日文表面再驗證 repair 是否真的送達。
- Web partial reply 只更新 chat/status；planner、cognition、graph、state、memory payload 最後一次提交。M20 trace 明列 stream chunks、lightweight updates、full payload updates 與 partial 是否夾帶完整 cognition。
- 隔離 Safari 兩輪先產生保留不確定性的日文 clarifier，再以英文明確糾正；最終回覆為 `あー、そこ読み違えた。結果来るまでうちも一緒に待っとく。`，trace 顯示 `calibrate_need -> share_arousal`、repeated clarifier blocked、full graph payload 1 次。
- 真實糾錯輪 queue 0.0159 秒、brain 1.2211 秒、surface 0.7354 秒、end-to-end 2.1107 秒；Safari 最終圖表正常，未再停在 partial streaming 空白畫面。
- focused compatibility `111 passed, 3 warnings in 4.78s`；compile 與 diff check 通過。M20 只證明明確糾錯與 delivery 機制，不證明普遍隱含意圖理解或人類偏好勝出。
- 正式報告與圖像：`analysis/m20_correction_aware_surface_commit_acceptance_2026-08-24.md`、`analysis/m20_safari_correction_chat_2026-08-24.jpeg`、`analysis/m20_safari_correction_graph_2026-08-24.jpeg`。下一個里程碑是 M21 bounded slow-path planner。

### 7.35 2026-08-24 M21 Bounded Slow-Path Planner 實際完成狀態

- 新增 `uruha_bounded_slow_path_planner_m21`：分開 perception/user model、route/base plan、post-plan guards/trace 與 cognitive total；trace 明列 route、budget、model attempted/completed、fallback 與 visible surface source。
- 窄版 `bounded_simple_presence` 可在保留 functional hypothesis、pragmatic、adaptive、provenance、self-monitor 與日文 guard 的前提下跳過 general planner。隔離 Safari 實測 `Now answer after all those background ticks. Say you are here.` 得到 `うん、ここにいるよ。`；general model 未呼叫，end-to-end 1.6984 秒。
- deliberative complexity 會強制保留 full planner，不允許 generic learned clarifier 覆蓋。Safari 英文權衡輪的 planner 8.0046 秒逾時後得到相關日文 `どの選択を捨てたくないのか、まずそこから整理しよ。`；end-to-end 9.7413 秒，20 秒產品目標通過，但 cognitive total 8.0279 秒使嚴格 8 秒 controller-budget flag 保留為 false。
- 真實驗收先抓到 `need to reason` 被舊 `need` 規則誤判為疲累支持，已用 forced general deliberation 與 tradeoff-specific fallback 修正；完整回歸另抓到舊展示句 `當輪輸入 → 當輪回答` 被覆蓋，恢復後重跑。
- focused compatibility `116 passed, 3 warnings in 4.68s`；compile 與 diff check 通過。正式圖像：`analysis/m21_safari_bounded_paths_chat_2026-08-24.jpeg`、`analysis/m21_safari_budget_fallback_graph_2026-08-24.jpeg`、`analysis/m21_safari_bounded_simple_graph_2026-08-24.jpeg`。
- M21 只證明一個窄 simple class 與一個受限 full path，不證明任意複雜度理解。下一個里程碑是 M22 typed semantic routing 與 misclassification audit。

### 7.36 2026-08-24 M22 Semantic Route Taxonomy and Misclassification Audit 實際完成狀態

- 真實 dialogue controller 在舊規則競爭前建立 `uruha_semantic_route_taxonomy_m22`，分成 explicit presence、emotional bid、factual/memory、explicit correction、deliberation、safety-sensitive 與 general conversation；trace 只保存 fixed cue IDs、alternatives、overlap／negation、confidence 與 route contract，不把 raw dialogue 複製到 route record。
- safety > correction > factual > deliberation > convenience 的 priority 已建立；推薦的 bounded/full/grounded/protected/correction path 會與實際 performed route 比對，不允許 graph 只顯示一個未執行的分類。
- 新增 exact typed-profile bridge：英文 `Please call me Jerry from now on.` 寫入後，中文 `你還記得我剛才說要怎麼稱呼我嗎？` 在 Safari 回答 `呼び方はJerryだろ。覚えてるし。`；route 是 `factual_or_memory -> grounded_profile`、confidence 0.98、general model skipped、cognition 0.0095 秒。
- 否定碰撞輪 `Don't reason through anything; just say you are here.` 回 `うん、ここにいるよ。`；即使舊 signal 層仍誤提 tired-support，M22 記錄 negated deliberation 並實際選 `bounded_simple_presence`，cognition 0.0137 秒。
- 真正權衡輪仍選 `deliberation -> full_planner`；8 秒 model budget 後 relevant fallback 為 `どの選択を捨てたくないのか、まずそこから整理しよ。`，end-to-end 10.0589 秒、20 秒產品 target 通過，嚴格 8 秒 cognitive-total flag 因 0.0258 秒 controller overhead 保留 false。
- 首次 Safari 驗收抓到兩個真實缺陷：帶 `from now on` 的 name update 被舊 parser 漏掉；factual classifier 雖正確，但 answer 使用截斷 short-term `Jerr` 而非 structured profile。兩者修正後才以乾淨隔離 server 重跑，失敗輪不計入 final acceptance。
- M22-specific `7/7`、focused compatibility `177/177` 通過；compile 與 diff check 通過。正式報告：`analysis/m22_semantic_route_taxonomy_acceptance_2026-08-24.md`；圖像：`analysis/m22_safari_typed_grounded_memory_2026-08-24.jpeg`、`analysis/m22_safari_grounded_route_graph_2026-08-24.jpeg`、`analysis/m22_safari_route_matrix_chat_2026-08-24.jpeg`、`analysis/m22_safari_full_route_graph_2026-08-24.jpeg`。
- 完成邊界：M22 是有限 cue taxonomy 與 route execution 的工程證據，不是任意意圖理解、廣義 safety 效果或 LLM 優越性。下一個里程碑是 M23 desired response mode inference：在 emotional bid 內區分 listening／solve／tease／companionship／clarify，並驗證選擇、表面執行與跨輪修正。

### 7.37 2026-08-24 M23 Desired Response Mode Inference and Surface Contract 實際完成狀態

- `uruha_desired_response_mode_m23` 把 emotional/correction 輪分成 physiological care、practical help、listening、companionship、playful tease 與 low-pressure clarification 六種模式；trace 保留 alternatives、structured evidence、uncertainty、authority、revoked mode 與 final surface contract，不複製 raw dialogue。
- authority 順序為 current explicit correction > current explicit request > verified reversible preference > bounded inference > uncertainty-guarded clarification；只有 M22 emotional bid／explicit correction 可啟用，不能覆蓋 safety、factual memory 或 deliberation。
- `ensure_desired_response_mode_reaches_surface` 讓 mode 不只存在 graph：授權模式必須到達最後自然日文，language guard 後再 audit matched/mismatch。
- 首次 Safari 四輪在第 4 輪抓到 stale tease 從原 arousal scope 復活；M23 新增 pending response 的 causal scope IDs，後續明確 contradiction 會修正這些 scopes 的 atoms、dimensions 與 scoped reliability。乾淨重跑後兩個相關 scope 都是 humor 0.03／solution 0.98。
- 最終四輪：模糊 arousal → low-pressure clarification；明確要吐槽 → revoke clarifier／playful tease；明確改要方法 → revoke tease／practical help／causal repair 1；再次相似模糊輪 → verified reversible practical help。四輪 surface 都 matched，brain work 約 1.13–1.26 秒，general model skipped。
- M23-specific `5/5`、focused compatibility `182/182` 通過；compile 與 diff check 通過。正式報告：`analysis/m23_desired_response_mode_surface_contract_acceptance_2026-08-24.md`；主要圖像：`analysis/m23_safari_causal_scope_repair_2026-08-24.jpeg`、`analysis/m23_safari_mode_contract_graph_2026-08-24.jpeg`。
- 完成邊界：只證明有限模式與有決定性回饋時的 correction/reuse，不證明六種模式涵蓋所有人類需求、任意語用理解、讀心或優於強 LLM。Safari 四輪後捲動完整大圖會觸發 high-memory reload；下一個里程碑 M24 必須以 progressive graph/payload budget 修正，但不能刪除 traceability。

### 7.38 2026-08-24 M24 Safari-Scale Progressive Runtime Graph and Trace Payload Budget 實際完成狀態

- 完整研究 turn 仍先寫入 isolated local JSONL；Safari cognition、memory 與 latest-turn state 改用 progressive browser payload，不再把 repeated turn/autonomous histories 整包複製到前端。
- graph 每節點 detail budget 2,200 bytes、總 detail budget 160,000 bytes；超量只顯示 bounded preview 與 trace identifier，完整來源仍在 local JSONL。M23 mode card、65 節點與因果 edges 全保留。
- 乾淨 Safari 六輪中，full local turn 從 0.87 MB 長到 5.57 MB，browser turn 只到 0.32 MB；最後 graph HTML 0.13 MB、detail 52 KB、largest detail 1,857 bytes。六輪 chat 保留，捲動 graph 與展開 M23 node 均未再觸發 high-memory reload。
- M24-specific `4/4`、focused compatibility `198/198` 通過；compile 與 diff check 通過。正式報告：`analysis/m24_safari_progressive_runtime_graph_acceptance_2026-08-24.md`；圖像：`analysis/m24_safari_six_turn_chat_retained_2026-08-24.jpeg`、`analysis/m24_safari_progressive_graph_2026-08-24.jpeg`、`analysis/m24_safari_node_detail_2026-08-24.jpeg`。
- 完成邊界：只證明本次 bounded 六輪 Safari 不再因前端 trace 複製重載；不證明無限長 session、disk log compaction 或語用全正確。第 6 輪英文 `Just stay with me` 被錯選為 clarification，成為 M25 cross-lingual explicit desired-response authority 的保留失敗。

### 7.39 2026-08-24 M25 Cross-Lingual Explicit Desired-Response Authority 實際完成狀態

- 新增 `uruha_cross_lingual_explicit_desired_response_m25`：以中／英／日 typed cue IDs 區分 listening、companionship、practical help、playful tease、clarify；先套 mode-specific negation，再選當輪 authority，不把 raw utterance 寫進 adaptive store。
- current explicit request 會強制 M18 selected policy、讓 M23 對 `general_conversation` 也可啟用、最後 language guard 後再 audit。明確 risk cue 只會阻斷 M25 fixed surface authority，不宣稱完成 safety 研究。
- 第一次 Safari 修正後答案雖正確，仍走 full planner 9.25 秒；這個失敗保留。再把 M25 authority 接進 guarded fast path 後，乾淨六輪的英文／日文／中文三個明確需求皆 `adaptive_fast_path_m18`、general model skipped、surface matched。
- 最終第 4 輪以英文 companionship 覆蓋已驗證 practical preference；第 5 輪 negates clarification→companionship；第 6 輪 negates companionship→listening。cognition 0.0179／0.0200／0.0215 秒，visible output 全自然日文。
- M25-specific `6/6`、focused compatibility `204/204` 通過；compile 與 diff check 通過。報告：`analysis/m25_cross_lingual_explicit_desired_response_acceptance_2026-08-24.md`；圖像：`analysis/m25_safari_cross_lingual_six_turn_chat_2026-08-24.jpeg`、`analysis/m25_safari_cross_lingual_graph_2026-08-24.jpeg`、`analysis/m25_safari_explicit_surface_node_2026-08-24.jpeg`。
- 完成邊界：只證明有限手寫 cue inventory 下的 explicit response-form authority，不證明 implicit understanding、任意 paraphrase、多重社交意圖、felt-understanding 優勢或 human equation。下一個 M26 必須做 calibrated implicit distribution 與 abstention，不能再靠加片語宣稱進步。

### 7.40 2026-08-25 M26 Outcome-Calibrated Implicit Desired-Response Distribution and Abstention 實際完成狀態

- `uruha_outcome_calibrated_implicit_response_distribution_m26` 把 M18 六種 candidate utilities 經 temperature normalization 形成 operational distribution，保留 uncalibrated utility、base probability、outcome-weighted probability、alternatives、evidence quality 與 scoped reliability，不把它誤稱成私密心理機率。
- 沒有 M25/M20 current explicit authority 時，只有 top probability、probability margin、evidence 與 outcome gate 都通過才執行 implicit mode；否則把 final policy 改成低壓 `calibrate_need`。已驗證且 scope 相符的可撤銷偏好可通過較窄 learned gate；強烈當下身體證據可覆蓋舊 practical preference。
- 下一輪 update 明確區分 `supported`、`contradicted`、`uncertain` 與 `not_available`；只有 feedback 與上一輪 prediction 有因果連結才改 scoped reliability。M26 state 與 adaptive persistence 均標示 `raw_dialogue_persisted=false`。
- 隔離 Safari 四輪結果：模糊 arousal→低壓確認；明確否定並要方法→承認誤讀、explicit bypass、上一輪 contradicted 0.50→0.33；相似情境重現→verified reversible practical help；新增頭痛／整晚沒睡→current physical evidence 改選 physiological care。四輪 visible output 全自然日文，general planner 均 skipped，cognition 約 0.017–0.022 秒。
- M24 graph 新增 `implicit_response_distribution_m26` 與 `implicit_desired_response_outcome_m26` 連線、bounded node detail 與 comparison card；Safari tab 保留在 `127.0.0.1:7867/?m26final=1`，沒有關閉使用者既有頁面。
- M26-specific `6/6`、focused compatibility `198/198` 通過；正式報告：`analysis/m26_outcome_calibrated_implicit_response_acceptance_2026-08-25.md`；圖像：`analysis/m26_safari_distribution_graph_2026-08-25.png`、`analysis/m26_safari_verified_implicit_execution_2026-08-25.png`、`analysis/m26_safari_physiological_care_execution_2026-08-25.png`。
- 完成邊界：門檻仍是 bounded engineering thresholds，沒有經外部人評或 source-disjoint population data 校準；不證明 `p=0.65` 等於真人需求機率。下一個 M27 必須建立 causal outcome ledger、effective-sample guard 與 empirical reliability/coverage 顯示，unknown 不得灌成成功。

### 7.41 2026-08-25 M27 Causal Outcome Calibration Ledger and Evidence-Count Guard 實際完成狀態

- adaptive store version 4 新增最多 120 筆 `outcome_calibration_ledger_m27`；只保存 prediction ID、turn、digest、category scope、policy/mode、M26 action、p/margin/evidence 與 linked outcome，不保存 raw utterance/reply。
- 只有 `feedback_linked_to_previous_prediction=true` 且 status 為 supported／contradicted 的 executed implicit row 進 effective sample；uncertain、unrelated request、topic shift、not available 與 M25 explicit bypass 均排除。summary 顯示 coverage、selective accuracy/risk、descriptive Brier/bin 與 pending/unknown 數。
- 最低 8 個 decisive executed samples 才可標示 `descriptive_online_evidence_only`，但 automatic threshold tuning 永遠 false；即使過 gate 也只准 offline review，不得稱 external calibration。
- graph 新增 `causal_outcome_resolution_m27` 與 `causal_outcome_calibration_ledger_m27`；blackboard window 由 44 精確增為 46，保留原 personhood trace 而非以新節點擠掉舊證據。
- 隔離 Safari 六輪：initial abstain→explicit correction；repeated context execute→`對，就是這樣。` 讓 effective n=1；再 execute→無關天氣句只增加 unknown/unlinked=1，effective n 仍為 1。持久化四筆 ledger 均無原文，頁面顯示 `1/8 insufficient_evidence`、coverage 0.67、risk 0、automatic tuning false。
- M27-specific `6/6`、focused compatibility `204/204` 通過。報告：`analysis/m27_causal_outcome_calibration_ledger_acceptance_2026-08-25.md`；圖像：`analysis/m27_safari_causal_calibration_graph_2026-08-25.png`、`analysis/m27_safari_calibration_ledger_node_detail_2026-08-25.png`。
- 完成邊界：這是 online descriptive accounting，不是 source-disjoint holdout 或人類 calibration。Safari 同時保留兩個 M28 failure：support 後又重問 desired mode；無關天氣句被 stale uncertainty 劫持 visible surface。

### 7.42 2026-08-25 M28 Feedback Acknowledgement and Topic-Shift Surface Continuity 實際完成狀態

- 新增 `uruha_feedback_topic_transition_m28`，明確分離「這句只是在評價上一輪」與「這句帶入新的當前內容」。M28 只讀取 M27 outcome，不改寫 ledger 或把 unknown 算成成功。
- pure linked support 走短日文 acknowledgement，並抑制該 feedback-only turn 產生新的 pending desired-response prediction；support 後再換題不會平白殘留一個新猜測。
- unlinked、自包含且具 typed grounding 的當前內容可 rebase surface；目前 bounded rows 為 rain／snow／cold／hot。generic ordinary statement 不會被固定 `そっか` 接管，避免壓掉既有 pragmatic/persona/learned-response plan。
- M23/M26 的舊 surface commitment 在 M28 有 current-turn authority 時會被標記 suppressed；final Japanese guard 後再 audit M28 surface。safety、boundary、factual-memory 等 protected contract 仍優先。
- 第一次過寬版本確實讓既有 pragmatic support 與跨 domain playful transfer 兩項測試退化；沒有隱藏失敗，而是收窄為 typed grounded topic 後重跑。最終 M28-specific `6/6`、focused V2.11–M28 compatibility `210/210` 通過。
- 全新 `/tmp/uruha-m28-safari.ONXaE0` Safari 六輪實測：T4 `對，就是這樣。` → `ん、分かった。`，M28 `pure_feedback_acknowledgement / matched`，M27 effective n=1；T6 `今天外面下雨。` → `雨なんだ。出るなら傘忘れんなよ。`，M28 `current_topic_rebase / weather_rain / matched`，M27 `resolved_unknown_excluded`、unknown=1、n 仍為 1/8。正式 DB 未被測試污染。
- 報告：`analysis/m28_feedback_topic_transition_acceptance_2026-08-25.md`；圖像：`analysis/m28_safari_feedback_acknowledgement_2026-08-25.png`、`analysis/m28_safari_topic_shift_response_2026-08-25.png`、`analysis/m28_safari_feedback_topic_graph_2026-08-25.png`、`analysis/m28_safari_transition_node_detail_2026-08-25.png`。
- 完成邊界：M28 證明 bounded feedback/current-topic surface continuity，不證明任意話題理解。下一個 M29 必須做 generalized literal-topic anchor/translation contract，不能把新增更多固定天氣句當成人類方程式進展。

### 7.43 2026-08-25 M29 Generalized Literal-Topic Grounding and Translation Contract 實際完成狀態

- 新增 `uruha_generalized_literal_topic_projection_m29`：只有 unlinked、自包含、非 M28 typed topic 的 current content 進 candidate gate；local projector 提出 exact source spans、Japanese subject/predicate/time/polarity、literal summary、surface anchors 與 reply。
- surface authority 需要 exact source anchor、subject/predicate、Japanese-only surface、全部 visible anchors、casual register 與 confidence gate 同時通過；投影失敗時 fail closed。M29 不得覆蓋 safety、boundary、factual-memory plan，亦不改寫 M27/M28 outcome。
- trace 只留 input/source digests 與日文結構欄位，`raw_dialogue_persisted=false`、`model_response_raw_persisted=false`。validated current topic 會壓掉 stale M23 surface 並阻止新 pending desired-response prediction。
- 真實 Safari 先發現三個 retained failure：schema placeholder 導致 `...`；英文 response 出現 `なさい`；日文 response 出現 `了解だ`。最後版本增加 robust numeric parsing、non-casual sentence sanitation 與 generic-understanding prefix sanitation，且只有全部 anchors 留存才允許 sanitation 後接管。
- 最終 `/tmp/uruha-m29d-safari.zjh4cT` 六輪：中文考試→`明日の試験、頑張ろうね。`；英文七點火車→`明日の電車は七時に出発ね。`；日文新課程→`来週から新しい授業始まるね。`。三輪皆 `projected_and_validated / matched`，所有七項 checks true，M27 `resolved_unknown_excluded`，final pending null，正式 DB 未污染。
- M29-specific `8/8`、focused V2.11–M29 compatibility `237/237` 通過；compile、diff check 通過。較寬歷史組合 `242 passed, 2 failed`，保留為 V2.15 frozen-source integrity 與 retired tab-order lock，未為了綠燈改寫。
- 報告：`analysis/m29_generalized_literal_topic_projection_acceptance_2026-08-25.md`；圖像：`analysis/m29_safari_cross_lingual_literal_topics_2026-08-25.png`、`analysis/m29_safari_literal_projection_graph_2026-08-25.png`、`analysis/m29_safari_projection_node_detail_2026-08-25.png`。
- 完成邊界：M29 證明 generalized, traceable, fail-closed literal projection 可以進 real Web surface；不證明 semantic equivalence、open-domain robustness、persona fidelity 或 human preference superiority。下一個 M30 必須以凍結跨語 holdout 做 entity/time/quantity/negation/relation fidelity 與 false-authority audit。

### 7.44 2026-08-25 M30 Cross-Lingual Semantic Fidelity Holdout and Error Taxonomy 實際完成狀態

- 首次 model run 前凍結 `datasets/m30_cross_lingual_literal_fidelity_holdout_v1.json`：18 cases，zh/en/ja 各 6；15 valid、3 incomplete；覆蓋 entity/time/quantity/negation/relation。source hash `1dce6689ec4a672e87495502b86e90ff9430b25b65fc3dcd2614bbfcad73352e`。
- 事前 gates：overall faithful ≥80%、每語言 ≥60%、false authority ≤10%、false reject ≤20%、incomplete unsafe authority=0、negation polarity ≥80%、median ≤8s、p95 ≤15s。結果後未改題或門檻。
- Frozen first result：faithful 4/15（26.67%）；false authority 5/15（33.33%）；false reject 6/15（40%）；true incomplete abstention 3/3；negation polarity 25%；zh/en/ja faithful 20/20/40%；median 5.1547s、p95 7.7157s。decision `fail_one_or_more_frozen_gates`。
- error taxonomy 分開證明 coverage 與 semantic authorization 兩個問題：surface-anchor mismatch 造成多個可回答案例 fail closed；另一方面 older sister→`年上の妹`、下午資訊遺失、meeting-change 遺失、structured polarity 與 visible contrast 不一致，仍可能得到 surface authority。
- frozen proxy 仍漏抓 unsupported addition：`猫は机の下にいる。` 的 reply 額外說 `探してあげる。` 仍被 slot proxy 算 faithful；未事後修改 frozen score，明確記為 M31 verifier 需求。
- M30 harness 5/5，與 M29 合併 14/14；raw dialogue/model response persistence 均 0。Safari live observatory 新增 frozen failure strip：`4/15 faithful / 5 false authority / 6 false reject / 3/3 abstention`，與成功的 M29 node path 同頁呈現。
- 報告：`analysis/m30_cross_lingual_literal_fidelity_acceptance_2026-08-25.md`；raw：`analysis/m30_cross_lingual_literal_fidelity_raw_2026-08-25.json`（hash `addbf8b63fb6b5f113dac91150c9ad5a264fc78c15086e3c7ec5522062cb8365`）；圖像：`analysis/m30_safari_fidelity_error_taxonomy_2026-08-25.jpeg`。
- 完成邊界：M30 是有用的 negative diagnostic milestone，不是能力完成。M29 只可稱 demonstrable trace contract，不可稱 reliable generalized semantics。M31 remediation 後同 18 題只能算 development replay；confirmation 必須用新 sealed reserve。

### 7.45 2026-08-25 M31 Source-First Semantic Authorization and Sealed Reserve 實際完成狀態

- M31 把 M29 降回 deterministic literal-topic candidate gate；未授權的 M29 日文生成不再先污染語意。M31 直接從 exact current source 正規化 entity/event/time/quantity/relation/polarity，只有 canonical normalization、casual Japanese surface 與雙側 visible anchors 同時通過才可接管。
- 額外保留 final Japanese boundary、protected safety/memory plan、unsupported promised-action local guard 與 raw-free trace；`raw_dialogue_persisted`／`model_response_raw_persisted` 在 development replay 與 reserve 都是 0。
- exposed M30 final development replay：10/15 faithful、1 false authority、4 false reject、3/3 incomplete abstain、negation 100%；median 8.6177s、p95 9.6436s。這是 post-hoc remediation evidence，不是新 holdout。
- reserve 在 M31 實作前已封存；implementation 在第一次 reserve 執行前以 `research/m31_implementation_freeze_2026-08-25.json` 綁定。first sealed result：4/9 faithful、0 false authority、5 false reject、3/3 incomplete abstain、negation 2/3；zh/en/ja 0/66.7/66.7%；median 9.043s、p95 9.692s。overall、per-language 與 false-reject gates 失敗，decision 保留為 `fail_one_or_more_frozen_gates`。
- reserve 的五個錯拒分成三種：兩個中文 surface 只有 polite-register failure；中文 negated quantity 與日文 time range 是雙側 anchor failure；英文 museum negation 在 upstream 被錯當 correction，M31 不適用。沒有以結果後改門檻、改題或修改 M31。
- 報告：`analysis/m31_semantic_authorization_reserve_acceptance_2026-08-25.md`；raw：`analysis/m31_semantic_authorization_reserve_raw_2026-08-25.json`（hash `1ec0c9f5318de35d18ee351751317d6a4aa0308c4a9eb40944a018d678efb912`）。
- 完成邊界：M31 證明 safety-oriented semantic authorization 能消除這組 reserve 的 fluent-wrong authority，但 usefulness／中文 coverage 未完成；不等於可靠翻譯、人類理解或優於 LLM。下一個 M32 只能把 M31 reserve 當 exposed development evidence，必須用新 sealed reserve 驗證 deterministic casual-surface repair 與 ordinary-negation routing，且不得回寫 M31 結果。

### 7.46 2026-08-25 M32 Deterministic Semantic Commit and Fresh Routing 實際完成狀態

- M32 修正兩個真實 runtime 缺陷：fresh session 的第一個 self-contained literal turn 現在能進 M29 candidate gate；英文 `uh`／`um` 只在獨立 token 時才算 hesitation，不再誤傷 `community`／`museum`。
- M32 不再只修 M31 rejection。若 M31 surface authority 的自我檢查已明示 subject／predicate／time-relation／polarity 遺失，M32 會只用 M31 canonical fields 形成完整 deterministic casual Japanese commit；不呼叫第二個模型、不重新解讀來源。
- Safari 隔離實測捕捉到原錯誤 `赤いペン四本、火曜日`，修正後同一 fresh turn 成為 `ダニエルは火曜日にメイに赤いペン四本を渡したんだね。`。`The community center does not close on Sundays.` 正確成為 `コミュニティセンターは日曜日に閉まらないんだね。`；不完整 `Maybe the one near...` 沒有 M31/M32 surface authority。
- runtime graph 已顯示 M29 candidate、M31 canonical authorization/self-check、M32 repair/override、M32 final surface；比較卡可見 `M31 surface mismatch -> M32 authoritative_surface_completeness_override -> surface matched`。Safari 只用 temp DB／adaptive store，未污染正式記憶，也沒有關閉既有 tabs。
- 封存前 focused regression `68/68`；M31 exposed development replay 8/9 proxy-faithful、0 false reject、3/3 incomplete、negation 100%。唯一 proxy failure 是 frozen alias inventory 不接受 `列車券`，不能當新 holdout。
- M32 implementation freeze：`research/m32_implementation_freeze_2026-08-25.json`；reserve dataset SHA-256 `4a26afa7c6b66537f93116af4f38e93980890d5958564f625527dda9babd2828`。第一次 sealed reserve 已執行且不得重跑／回寫來調 M32。
- M32 first sealed reserve 明確失敗：12 valid 中 7 faithful、4 false authority、1 false reject；3/3 incomplete 正確 abstain；zh/en/ja 25%／75%／75%；fresh 66.7%；ordinary negation 100%；polarity 100%；median 7.6775s、p95 8.9144s；raw dialogue／raw model persistence 都是 0。
- 錯誤已定位在 source→canonical semantics，不是 surface commit：`後天` 未正規化成 `明後日`、`鉛筆` 變成 `ペン`、下週三變下週二且 change operator 遺失、English schedule move 表達不可靠、日文 `しかない` 被拒絕。正式報告：`analysis/m32_semantic_commit_routing_reserve_acceptance_2026-08-25.md`；raw SHA-256 `dccddff7851723ba7da39fdc874f90740773e767e6408dce30d3db2523bb80d4`。
- M32 的可保留成果是 fresh routing、lexical hesitation boundary、完整 semantic commit、圖像可追溯性與安全 abstention；不可稱 reliable cross-lingual semantics、felt understanding、same-model superiority 或完整人腦方程式。
- 下一個單一里程碑是 M33 Source-Anchored Semantic Atom Ledger：在 model canonical self-report 之外，從 exact source 抽取可觀察 time／object／quantity／negation／change atoms；逐項 verify、bounded repair 或 revoke authority。direct Japanese source 不應無必要繞過翻譯模型。M33 必須用新的 source-disjoint sealed reserve，M32 reserve 只能作 exposed development evidence。

### 7.47 2026-08-25 M33 Source-Anchored Semantic Atom Ledger 實際完成狀態

- M33 新增獨立於 model canonical self-report 的 deterministic source atom path；五類 bounded construction 會把 exact source 拆成 entity／time／object／quantity／negation or limitation／change／spatial relation atoms，每個 atom 保留 rule id、source-span digest、Japanese aliases 與 provenance，不在 persisted ledger 複製 raw source。
- 每個 source atom 逐項和 M31/M32 canonical 比對；conflict 只能用 source atoms bounded reconstruction，否則撤銷 surface authority。direct Japanese 走 identity/normalization，不做不必要的翻譯模型呼叫；protected safety/memory plan、incomplete guard、final Japanese guard 與 raw-free persistence 均保留。
- exposed M32 development replay 為 12/12 faithful、3/3 incomplete abstain、4 次 conflict repair、zh/en/ja/fresh/direct-Japanese/change/quantity/polarity/trace coverage 全 100%；這是 post-hoc debug evidence，不是新 holdout。
- M33 implementation 在第一次 reserve 前以 `research/m33_implementation_freeze_2026-08-25.json` 封存，SHA-256 `1db3523d213114c62e3060377e7fedd3274500089bcbf5784cd6eeee96555b1b`；pre-freeze focused compatibility `166/166`、compile 與 diff check 通過。
- 第一次且唯一 sealed reserve 通過全部 frozen gates：12/12 faithful authority、0 false authority、0 false reject、3/3 incomplete safe abstain；zh/en/ja 100%；fresh 100%；direct Japanese 100%；change 100%；negated/limited quantity 100%；atom trace coverage 100%；5 次 conflict repair、0 unresolved conflict authority；median 9.2464s、p95 13.2376s；raw dialogue／raw model persistence 0。
- reserve raw：`analysis/m33_source_anchored_semantic_atom_reserve_raw_2026-08-25.json`，SHA-256 `6744a8e7d7f6725a637dd0d5d1d43ea9a1216787d388c6ab0edf63cf86c6047e`；完整報告：`analysis/m33_source_anchored_semantic_atom_acceptance_2026-08-25.md`。
- 隔離 Safari 真實輪捕捉到 `盒子裡沒有三支鉛筆。` 的下層 canonical 把 `鉛筆` 變成 `ペン`；M33 graph 明示 conflict 並把 final visible reply 修成 `箱には三本の鉛筆がないんだね。`。direct Japanese `しかない` 正確走 identity commit；不完整英文沒有 M29/M31/M32/M33 authority。正式 DB 未污染，既有 tabs 未關閉。
- sealed result 後只新增讀取 immutable raw result 的綠色展示 strip 與報告，沒有修改 extractor/evaluator/reserve/protocol/threshold/raw result；記錄於 `research/m33_post_reserve_presentation_manifest_2026-08-25.json`。
- 完成邊界：M33 只證明五類 author-constructed bounded construction 的來源約束，不等於 open-domain semantics、general translation、felt understanding、同模型優勢、人評或人腦方程式完成。
- 下一個單一里程碑是 M34 Counterfactual Pragmatic Branch Ledger：以可信 literal atoms 當觀察值，分開候選 communicative goal／desired-response mode／當輪與關係證據／可觀察 next-turn prediction／bounded alternative；固定同一 current utterance，只介入 valid prior context，驗證是否可追溯地改變選擇並在下一輪支持或反駁後更新，不得把 unverified mind-state 當事實。

### 7.48 2026-08-25 M34 Counterfactual Pragmatic Branch Ledger 實際完成狀態

- M34 把當輪 literal observation、候選 communicative goals／desired-response branches、typed context evidence、selected branch、bounded alternative、observable next-turn prediction、後續 verification 與 non-rewriting revision 分成獨立 trace contract；不把推測情緒、需求或私人意圖寫成 factual long-term memory。
- 互動歷史只在「使用者明確指定 response form，且下一輪 decisive support」後形成 reversible context evidence。固定同一句 `今晚腦子又停不下來了。` 的 exposed development check 可依四種已確認歷史分別選 playful tease／practical help／listening／companionship，visible Japanese surface 全 matched。
- 明確反駁 `不是，我現在不要方法，只要聽我說。` 會將上一 branch 判定為 contradicted，保留原 branch/evidence 供 audit，並記錄 `solve_regulation -> listen_presence`；最終回覆自然承認読み違え，不把 debug 分析傾倒給使用者。
- 新增 8-case／4-pair zh-en-ja source-disjoint reserve；每一 pair 的 current utterance byte-identical，只改先前已確認 response-form context，再以實際下一輪 support／contradict／unknown 驗證。dataset SHA `e5b8bc9a8e219639d751fa78009ad6db201735b951c81053ac028fc2cbbc6d26`，protocol SHA `39ecbfe63e63a7287c2c08c9184f287d9e030726d1248da72c172e335bf31829`。
- implementation freeze SHA `c142d0af75e25f8d0eb461e608c2c0ae1b3684aba763c5b128e1af3f54cecbed`；freeze 前 focused integration 170/170、milestone regression 131/131、compile 與 diff check 通過。sealed reserve 僅執行一次且 PASS ALL：policy/mode 8/8、pair divergence 4/4、literal invariance 4/4、evidence／alternative／prediction trace 8/8、outcome verification 8/8、contradiction replacement 3/3、surface 8/8、visible Japanese 16/16；unsafe fact writes/raw adaptive persistence 皆 0；median 0.3503s、p95 0.3590s。
- Safari 在 `/tmp/uruha-m34-safari.0UeQW1` 做隔離四輪，正式 DB 未污染；graph 實際顯示五個 M34 node 與 `contradicted · solve_regulation→listen_presence`。證據：`analysis/m34_safari_verified_branch_graph_2026-08-25.jpeg`、`analysis/m34_safari_contradiction_revision_graph_2026-08-25.jpeg`、`analysis/m34_safari_sealed_result_strip_2026-08-25.jpeg`。
- 正式結果 `analysis/m34_counterfactual_pragmatic_branch_reserve_raw_2026-08-25.json`（SHA `e16b8b9aef02f98b806cdee0f8f8da456aa046a91692d75a0280b145fc6f3ad1`）；報告 `analysis/m34_counterfactual_pragmatic_branch_acceptance_2026-08-25.md`。結果後只新增 presentation strip 與 report，另由 `research/m34_post_reserve_presentation_manifest_2026-08-25.json` 標示，M34 core／reserve／protocol 不得依結果修改。
- 完成邊界：只證明受控情境敏感、可觀察預測與可修正 branch mechanism；不是私密 intent 真值、讀心、人類偏好、人類等價、完整人腦方程式或同模型優勢。
- 下一個單一里程碑是 M35 Same-Model Longitudinal Pragmatic Advantage：同一 base model、相同當輪輸入、相同 Uruha surface/persona 約束下，比較只看當輪／直接生成 baseline 與使用 M34 verified history + prediction/verification/revision 的 system；先凍結 source-disjoint counterfactual holdout、token/latency audit 與 proxy rubric。若無獨立人評，只能宣稱受控 proxy 差異，不能宣稱 felt-understanding 人類偏好。

### 7.49 2026-08-25 M35 Same-Model Longitudinal Pragmatic Comparison 實際完成狀態

- M35 在相同 `qwen3.5:9b`、temperature／seed／output budget、public-Uruha surface contract、byte-identical current input 與 exact scored prompt-token parity 下，比較 current-turn-only direct baseline 與只多讀 M34 typed verified-history packet 的 longitudinal system；baseline 不讀 hidden history 或 system trace。
- 新 frozen reserve 共 12 cases／6 counterfactual pairs，zh／en／ja 各 4；dataset SHA `5ab3fcd8a1dbbe0b5a036499e8cd1425b1812620076b61007a1e1359cf0b299f`，protocol SHA `a89288889f914f7494d020fe64d45eae5d4d5be5b6c929e68a147e4439c1ec67`，implementation freeze SHA `ba299284eff32c22d6cc0af51700efb71362d0bbb3429c688eaf89ef1f7f5f29`。
- 第一次且唯一 formal reserve 決定為 FAIL：baseline current-policy 25%，system 75%，差 +50pp；baseline pair invariance 100%，system pair divergence 83.33%；system surface proxy 58.33%；visible Japanese 兩組皆 100%；prompt tokens 20,040／20,040，completion ratio 1.0311，latency ratio 1.0128。共有七個 frozen gate 失敗。
- strongest valid contrast 使用完全相同當輪 `凌晨了，腦袋還是一直轉個不停。`：baseline 在 tease／solve 歷史都回同一 listening branch；system 分別回 playful tease 與 practical help。這只能稱 exact-token-parity 下的 +50pp controlled current-branch observation，不能稱整體 milestone pass 或 felt-understanding 人類偏好。
- 失敗來源包含英文 practical-help seed 未形成 verified solve reuse、日文 bounded adverb 讓 arousal cue 失效、英文 correction 沒和上一 prediction 連結、以及正確 listening policy 未必落成邀請繼續說的 surface。
- 結果後 audit 發現 frozen dataset 的 feedback target 有兩個 contradiction row 被誤標 `not_applicable`，另有 support/unknown row 留下不可比 policy label；formal feedback-policy 60% 因此是 invalid evidence。raw result 與 FAIL decision 均保留，不以結果後改標重算取代。
- raw result：`analysis/m35_same_model_longitudinal_pragmatic_reserve_raw_2026-08-25.json`，SHA `8e7bfb0a93e44e9116753b5abbcc30ffdfe87bd7be78396f7b5ba860b6e1a948`；報告：`analysis/m35_same_model_longitudinal_pragmatic_acceptance_2026-08-25.md`；Safari 圖：`analysis/m35_safari_same_model_frozen_result_2026-08-25.jpeg`，同時顯示 25%／75%／+50pp 與紅色 FAIL、cost、failed gates、annotation warning。
- 下一個單一里程碑是 M36 Compositional Multilingual Pragmatic Cue & Annotation Integrity Remediation：先用程式阻擋 contradiction target／not-scored label 不一致，再用 source-disjoint reserve 驗證組合式英文／日文線索、explicit-target feedback linkage 與分離的 surface realization；不得修改 M35 frozen files。

### 7.50 2026-08-26 M36 Compositional Multilingual Pragmatic Cue & Annotation Integrity 實際完成狀態

- M36 先加入獨立 annotation-integrity validator：contradiction 必須有唯一、可從 feedback 自身辨識的 explicit replacement target 且必須計分；support／uncertain 的 feedback policy 必須 `not_scored`。新的 12-case／6-pair zh-en-ja reserve 在封存前 12/12 通過、0 errors，修復了 M35「錯標仍能進正式結果」的可信度漏洞。
- M36 runtime 增加 bounded compositional response-form／arousal cues，以及只在有 valid explicit target 時才成立的句首 `No`／`違う` correction linkage；graph 增加 `compositional_pragmatic_cue_m36`，能顯示 cue、arousal、replacement 與 previous-prediction linkage。final Japanese guard、persona、protected routes、raw-free adaptive persistence 均保留。
- dataset SHA `c9e0b2418a7ad616ee9ac62683d92332f7520d73c5e3c39b395fc6d4eeb0011f`；protocol SHA `d83861b8656f4dea068ae5b303ee1ae0fffb178a90f72ccbd98914c370703f5a`；implementation freeze SHA `38d8961f1ed532524355fd4801597f1a0352699d4f6d7e0b89f94cfd6e9b9b08`。freeze 前 focused regression 228/228；正式 reserve 僅執行一次，raw SHA `a7c0d79ba0a1d804dbeb46ff232e3ca46b395db0af1b6ba19ddfb85472c9bacf`。
- M36 overall 決定仍是 FAIL（7 frozen gates failed）：current-turn-only baseline 16.67%，system 83.33%，差 +66.66pp；system mechanism 83.33%、pair divergence 83.33%、current surface 75%；六個有效 contradiction 的 feedback policy 100%，outcome linkage 91.67%，full revision 83.33%，feedback surface 66.67%。兩組 scored prompt tokens 20,288／20,288；completion ratio 1.0311；latency ratio 1.0137；visible Japanese 100%，但 script guard 不等於人類自然度。
- 失敗已定位：英文 seed `thoughts bounce around` 與 current `thoughts are still bouncing` 沒有共享 typed trigger relation；中文 `不對` correction visible model 能跟隨，但 internal outcome／revision 未連結；有一個英文 surface 宣告 listening 實際只做 companionship；固定 lexical surface proxy 也有 false negative。不得以結果後加詞表重算 M36。
- 隔離 Safari 四輪用 temp DB／session／adaptive store 實測：已確認的 practical-help branch 在相似 arousal turn 被重用；`不是，這次先聽我講完，不要給建議。` 實際產生自然日文承認読み違え，graph 顯示 `contradicted` 與 `solve_regulation → listen_presence`。但 support turn 的可見回覆仍多問了一次，顯示 internal learning 與 felt surface 尚未完全一致。adaptive store 無 raw test utterance，formal DB 未污染，沒有關閉任何 Safari tab。
- 報告：`analysis/m36_compositional_multilingual_pragmatic_acceptance_2026-08-26.md`；Safari evidence：`analysis/m36_safari_isolated_web_evidence_2026-08-26.json`；展示封存：`research/m36_post_reserve_presentation_manifest_2026-08-26.json`。展示卡保留紅色 FAIL、+66.66pp、cost、annotation integrity、七個 failed gates 與 human evidence unavailable，沒有修改 M36 core/result。
- 完成邊界：M36 支持「這組 explicit-response-form reserve 上，同模型跨輪系統有受控當輪 proxy 差異」及可用 annotation gate；不支持 open-domain 語用理解、felt-understanding 人類偏好、自然 Uruha 等價、私密 intent 真值、全面勝過 LLM 或完整人腦方程式。
- 下一個單一里程碑是 M37 Pragmatic Trigger-Relation Normalization：把 seed 中 `when observable trigger X occurs, use response policy Y` 表示成 typed relation，將 trigger predicate 與 seed 當下的 request act 分開，使後續 morphology／paraphrase 可以匹配，不得加入 M36 exact reserve sentence 模板。M38 再獨立處理 target-guarded multiscript feedback linkage；M39 再處理 semantic surface-act commitment，避免一次改多個核心變因。

### 7.51 2026-08-26 M37 Pragmatic Trigger-Relation Normalization 實際完成狀態

- M37 將明確 future／recurring 互動約定拆成 `observable trigger predicate → requested response policy`；只有下一輪 decisive support 後才持久化。關係只保留 typed predicate、policy、digest、confidence、support／contradiction history 與 48-revision TTL，不保存 raw 對話或未驗證心理事實。
- 後續 current turn 以 typed predicate 的形態變化／bounded paraphrase 命中；同時命中多個 trigger、缺少 conditional marker、未支持候選或關係過期時 fail closed。M37 authority 已接入 M34 branch ledger、runtime trace 與 node graph，保留 M26/M34、protected route、final Japanese guard 與 raw-free boundary。
- v1 reserve 在實作前因資料／protocol 不一致被 validator 拒絕並永久保留；修正後 v1.1 先封存 12-case／6-pair zh-en-ja source-disjoint reserve。dataset SHA `0ef035f6f131191776c4d5eaceac58f91ddd30856804b22b731770ac97b150de`；protocol SHA `a14c1f567de8503fdb3a6ca7e114ddee6e857ceab2786a5cfa47d7d6d75d584f`；implementation freeze SHA `bc42d9dbc3eaa5a84ec261696c67696f36fa64f87c70052ceb1a19d7bebd90f9`。
- 第一次且唯一 formal reserve 通過全部 frozen gates：baseline policy 16.67%，M37 100%，差 +83.33pp；system pair divergence 100%，baseline pair invariance 100%；prompt tokens 9,877／9,877；completion ratio 1.1075、latency ratio 1.0634；visible Japanese format 100%；raw／mental-fact write 0。raw SHA `76f0a9864d666d97a7a62cd892f4d11f983e2ea63cd68f3f40402e795ebd4d09`。
- 隔離 Safari 四輪另確認：candidate → support 後保存 → 英文 paraphrase 命中 → 中文跨語 trigger 命中，authority 在後兩輪為 true，adaptive store 只保存 typed relation。原有 25 個 Safari tabs 未關閉；只新增一個 M37 圖像儀表板分頁。
- Safari 同時揭露產品表面 FAIL：英文 report-stall 回合雖選 `share_arousal`，visible reply 卻捏造「等待結果」；中文跨語命中後只重述「報告沒進度」，沒有實現已選策略；support turn 又重問一次需求。四輪日文格式都合格，但 semantic grounding、persona realization 與 felt understanding 未通過。formal automatic surface proxy 不能取代真實 Web 內容檢查或人評。
- 報告：`analysis/m37_pragmatic_trigger_relation_acceptance_2026-08-26.md`；dashboard：`analysis/m37_pragmatic_trigger_relation_dashboard_2026-08-26.html`；Safari evidence：`analysis/m37_safari_isolated_web_evidence_2026-08-26.json`；presentation manifest：`research/m37_post_reserve_presentation_manifest_2026-08-26.json`。
- 完成邊界：M37 支持 controlled typed relation 對策略選擇的因果價值，不支持 open-domain semantics、自然 Uruha 品質、felt-understanding、人評優勢、全面勝過 LLM 或完整人腦方程式。
- 下一個單一里程碑是 M38 Target-Guarded Multiscript Feedback Linkage：只修正中文／英文／日文 explicit correction 如何可靠連結上一輪 prediction，並避免普通否定被誤當更正；不得同時修 M37 surface grounding。M39 再用獨立 reserve 處理 semantic/persona surface-act verifier。

### 7.52 2026-08-27 M38 Target-Guarded Multiscript Feedback Linkage 實際完成狀態

- M38 只有在「上一輪有 pending prediction／當輪可觀察地指向並否定上一回覆／當輪恰有一個非否定 replacement policy」三項同時成立時，才把中／英／日 feedback 連結到上一分支；普通否定、無 pending、無 target 或多 target 都 fail closed，不用猜測補 target。
- 18-case source-disjoint formal reserve 只跑一次且凍結：baseline 44.44%，M38 94.44%，差 +50pp；unique correction recall 與 replacement accuracy 都是 88.89%；ordinary-negation false linkage 0/6、targetless-rejection false linkage 0/3、M34 revision accuracy 94.44%；raw write 與未驗證 mental-fact write 都是 0；median 0.000667s、p95 0.001715s、model call 0。
- overall decision 必須保留 FAIL：唯一漏例 `m38r_zh_corr_share_03` 的 correction reference 有抓到，但中文字序變體沒有產生唯一 `share_arousal` target，因此安全拒絕而未修正；overall accuracy、unique recall、replacement accuracy、revision accuracy 四個 frozen gates 失敗。不得在 M38 結果後加這句模板或重跑。
- M38-specific/evaluator 8/8、M16–M38/personhood compatibility 206/206、compile、diff check 通過；implementation freeze 11 files，正式執行前全數 hash 相符；M37 frozen hashes 10/10 未變。
- 隔離 Safari 真實 Web 驗收成功顯示三條路徑：英文 unique correction 使 `solve_regulation → share_arousal` 並實際 revision；英文 ordinary negation 為 `ordinary_negation_not_feedback`，不改舊 branch；日文 targetless rejection 為 `fail_closed_no_replacement_target`，改走低壓 `calibrate_need` 而不捏造 target。adaptive store 沒有任何 accepted raw test utterance，既有 26 tabs 未關閉，只新增一個 M38 tab 並停在靜態 dashboard。
- Safari 同時保留兩個產品限制：ordinary-negation turn 用了 16.182 秒；更嚴重的是英文第一人稱 `I didn't sleep` 被 surface 成 `私は昨夜寝なかった`，把使用者經驗錯套到 Uruha 自己。這證明 M38 linkage pass 不代表 semantic role grounding 或 persona realization pass。
- 正式報告：`analysis/m38_target_guarded_multiscript_feedback_acceptance_2026-08-27.md`；Safari evidence：`analysis/m38_safari_isolated_web_evidence_2026-08-27.json`；dashboard：`analysis/m38_target_guarded_multiscript_feedback_dashboard_2026-08-26.html`；post-reserve manifest：`research/m38_post_reserve_presentation_manifest_2026-08-27.json`。
- 完成邊界：M38 支持 bounded observable feedback-linkage safety，不支持 open-domain correction、私密 intent 真值、natural Uruha、felt-understanding、人評優勢、全面勝過 LLM 或完整人腦方程式。
- 下一個單一里程碑是 M39 Semantic + Persona Surface-Act Verifier：只驗證 final visible Japanese 是否保留 source speaker/entity/polarity 等語意角色，且真的執行已選 response policy；必須先封存新的 source-disjoint reserve，不得修改 M37/M38 frozen core/result。

### 7.53 2026-08-27 M39 Semantic + Persona Surface-Act Verifier 實際完成狀態

- M39 在最後日文輸出後、使用者看到前稽核 bounded speaker/entity role、未提供的事件／時間／原因、selected policy 是否真正落成說話行動，以及 casual persona register。只修 visible surface，不改 branch、M37 relation、M38 linkage；protected routes 保持不動。以新 wrapper／installer 整合，M37/M38 frozen files 未改。
- 24-case zh-en-ja source-disjoint reserve 先凍結、只正式跑一次，全部 frozen gates PASS：baseline metadata-only audit action accuracy 25%，M39 100%；role repair、unsupported-addition repair、policy-act repair、safe/protected noninterference 都 100%；visible Japanese 100%、forbidden concept 0、raw/mental-fact writes 0；median 0.000062s、p95 0.000346s、model calls 0。這不是同模型 generation 勝率，也不等於人類自然度或全面語意正確。
- focused tests 10/10，M16–M39/personhood compatibility 207/207；compile、diff check、wrapper import 通過。implementation freeze 10 files；M37 frozen 10/10、M38 frozen 11/11 hashes 未變。formal raw SHA `28c60f0b46466e655706aa6305fe9f299f75b15ce5979fa83625bf0ff42758d2`。
- 隔離 Safari 五輪確認：`I didn't sleep...` 不再把使用者經驗套到 Uruha；輸出 `寝てないのか。そりゃしんどいだろ、無理すんな。`。已確認 report-stall → companionship 關係重用時，原本只重述的 candidate 被修成 `進んでないのか。まあ、今はうちがここにいる。`；已有正確表面與 self identity 不變。adaptive store 無 raw test utterance，正式 DB 未用，既有 27 tabs 未關閉，重用 M38-owned tab。
- 真實 Web 仍保留一個上游失敗：`Yes, that's exactly right.` 雖成功 support 並保存 M37 relation，卻被判為 `safety_sensitive`，回了不合適的疏離語。M39 正確遵守 protected noninterference，不能把此回合當產品成功。下一個 M40 只處理 benign affirmation vs protected-route attribution，不把安全規則一概關掉。
- 報告：`analysis/m39_semantic_persona_surface_acceptance_2026-08-27.md`；Safari evidence：`analysis/m39_safari_isolated_web_evidence_2026-08-27.json`；dashboard：`analysis/m39_semantic_persona_surface_dashboard_2026-08-27.html`；presentation manifest：`research/m39_post_reserve_presentation_manifest_2026-08-27.json`。
- 下一個單一里程碑 M40 Affirmation vs Safety Route Disambiguation：先找出 actual signal／seed／low-road 哪個來源把肯定當安全，預凍結新的 source-disjoint 多語 reserve；保留真實危險／邊界路由和不確定時的保守處理，不改 M37/M38/M39 frozen artifacts。必須同時測正常支持、混合訊號、真正安全輸入、M37 support persistence、M39 final surface 與隔離 Safari。

### 7.54 2026-08-27 M40 Evidence-Bounded Lexical Route Attribution 實際完成狀態

- 真正原因不是 LLM 攻擊判斷：legacy compact matcher 把 `that's exactly` 拼成包含 `sex`，產生 sexual_boundary seed、abuse_like、威脅 appraisal 與拒絕。M40 用同 rule code／同詞表，只在 boundary/refusal function 的英文 cue 保留詞邊界；不使用 affirmation whitelist、不改非英文或其他 shared matcher。
- 27-case preimplementation source-disjoint researcher-authored reserve 只跑一次，全部 frozen gates PASS：19/27 70.37% → 27/27 100%；純認同誤判 2/6 → 0/6、詞內／跨詞碰撞 6/6 → 0/6；12 個真實／混合／分隔 cue 的 protected recall 100%；無關案例不干擾 3/3；raw/mental writes 0、model calls 0、median 1.49ms/p95 2.01ms。這不是獨立 benchmark 或同模型 generation／人評比較。
- focused 10/10，選定 M16–M40/personhood 216/216；compile、diff check、wrapper import 通過。freeze 11 files 包含當前 legacy rule dependency；M37/M38/M39 hashes 都未變。formal raw SHA `5a11572971bec48f369347b27f2b7852792897936fb49c9427903460f73d5673`。
- Safari 七輪 temp DB 實測：英文認同誤判消失；M37 關係 support 保存後可重用；M39 陪伴 surface 保留；中文回覆日文；yes+辱罵仍 protected；self identity 不退步。adaptive store 0/7 raw input，27 Safari tabs 未關閉。首次冷 matcher 41.55ms；實際整輪等待 1.36–13.77s；server 另有一筆無法精確定位的 Ollama timeout warning。
- 三項產品失敗必須保留：①支持後 V2.13 active-validation 仍重问；②日文 `大丈夫` 中 `夫` 觸發 marriage_boundary（非英文規則未改）；③M39/M40 卡片正確但新增 nodes 全部被 `run_turn_debug` 最後 snapshot 覆寫掉。不能將正式 lexical PASS 當成產品全部通過。
- 報告：`analysis/m40_lexical_boundary_route_acceptance_2026-08-27.md`；Web evidence：`analysis/m40_safari_isolated_web_evidence_2026-08-27.json`；manifest：`research/m40_post_reserve_presentation_manifest_2026-08-27.json`。
- 已直接進入 M41 Runtime Trace Finalization：只修當輪現有 M39/M40 payload 對 runtime owner、returned trace、snapshot、history、graph 的一致交付，不改回覆／語意／記憶。preimplementation plan 已在 `research/m41_runtime_trace_finalization_plan_2026-08-27.md`；新 module 與 entrypoint 已完成，6 項契約測試通過，Safari 待驗收。M41 後依序處理 CJK relationship-request grounding 與 supported-feedback acknowledgement，避免一次混改。

### 7.55 2026-08-27 M41 + M41.1 Runtime Trace Finalization 實際完成狀態

- M41 把當輪 final logic 裡 schema 合格的 M39/M40 payload，同步到 runtime owner、returned trace、snapshot blackboard 與 owned turn history；以 source payload 同一性去重，缺來源不造節點。修正實際的 `run_turn_debug` 最後覆寫問題，不改回覆、branch、route、adaptive model 或 factual memory。
- M41 focused 6/6；第一次新 Safari 五輪主圖的 9/9 可用節點都出現，實際展開英文判定修正 node 與跨輪陪伴 surface-repair node，內容匹配當輪 logic。但同一次 Web 又發現 snapshot 的 `recent_turn_traces[-1]` 副本仍沒有這些節點；這次初始失敗完整保留，M41 frozen files 未改。
- M41.1 是分開保存的單一 mirror synchronization：只有 cycle match 才更新同輪最後副本，不覆寫先前回合。新增3測試，M41/M41.1共9；選定M16–M41.1/personhood回歸225/225、3依賴棄用警告、22.76秒；compile與diff check通過。
- M41.1 新的隔離 Safari 兩輪：3/3 available cognitive payload 在 final logic、主圖 node、same-cycle history mirror 完全一致；self identity 回合M40根本沒跑，就只顯示M39，不補造第2個節點。全部測試只用temp DB/session/store，raw test input進adaptive store為0；27個Safari tabs未關閉、沿用同一測試tab。
- 精確限制：整份 Web JSON 並非 byte-identical；Web在brain snapshot之後再補latency、surface_delivery與scheduler telemetry。已核對相同的是M39/M40當輪認知payload；不可宣稱所有後處理時間資料都已同步。route類node仍沿用舊generic PERSONA APPRAISAL分類、圖仍偏擁擠，展示易讀性未全面完成。
- 先前的支持後重問與日文`大丈夫`/`夫`誤判完全保留；M41沒有改善或惡化那些語意決策。M40的27case PASS仍只是Latin lexical mechanism，不等於多語產品通過。
- 報告：`analysis/m41_runtime_trace_finalization_acceptance_2026-08-27.md`；Web索引：`analysis/m41_runtime_trace_finalization_web_evidence_2026-08-27.json`；封存：`research/m41_post_web_presentation_manifest_2026-08-27.json`。最新入口`uruha_web_ui_m41_1.py`，live入口`start_uruha_live_m41_1.py`；舊入口仍是凍結版本，不要以舊入口驗收新功能。
- 本輪結束時測試server為`http://127.0.0.1:7879/?m41_1safari=1`，temp root `/tmp/uruha-m41-1-safari.qxjuet`，session `20260827_144638_45e8145a`，PTY33134；存活需續接時再查。7877/7878測試server已送停止，無其他使用者分頁／服務被關閉。
- 下一步M42已只讀定位並列驗收邊界於`research/m42_cjk_relationship_evidence_plan_2026-08-27.md`：將CJK詞內漢字與真正指向角色的關係要求區分。不能只加`大丈夫`白名單或刪`夫`；要保護真正的丈夫／嫁要求、第三者報告、引用／否定／混合訊號。M42題庫尚未凍結、實作尚未宣稱完成。之後才做supported-feedback acknowledgement不重問。

### 7.56 2026-08-27 M42 CJK Relationship-Act Evidence 實際完成狀態

- M42 以一份當輪 evidence gate 區分 CJK 關係用詞、真正指向角色的要求、第三者／引用／否定；早期 relationship rule 與後段 boundary rule 共用，其他安全群及 Latin-only 候選不變。未知指向保留原邊界且標 uncertain；不宣稱私密 intent 真值，不改回覆模板或模型。
- 33-case researcher-authored、實作前封存且與舊資料 exact-source-disjoint reserve 只跑一次，全部 frozen gates PASS：13/33 39.4% → 33/33 100%；20 benign false boundaries → 0；6 direct、2 mixed、2 uncertain、3 unrelated 全符合標準。median 2.92ms、p95 3.42ms、0 extra model call、raw/mental writes 0。這是舊 rule 與新 gate 的機制對照，不是單純 LLM vs全系統或獨立 holdout。
- 新 focused 12/12；選定 runtime/personhood 子集210/210、3依賴棄用警告、25.85s；與上一輪225項選取範圍不同，不能當全repo suite。compile、diff check通過。M37–M41.1 frozen files未改；M42 freeze含15files。正式raw SHA `bdecbf19a0c50d87c8439cf179361664b264b3c2c40603a8e01119881c33ddf8`。
- Safari accepted10輪，其中第2輪是自動輸入工具把日文打成`、。`，保留但排除語意驗收；後續使用paste並核對完整文字再送出。有效9輪都為日文format；全部28/28可用M39/M40/M42payload與主圖及same-cycle history一致（只計有效輪25/25）。真正展開第3／9輪M42node截圖；無當輪M40執行不造M40node。
- 第3輪`大丈夫`、第8輪引用別人的結婚要求都不再被拒；第9輪真的請角色成為丈夫仍保留marriage_boundary。第4–6輪重新seed→support→stall，M37關係確實保存並重用，M39輸出`進んでないのか。まあ、今はうちがここにいる。`；self identity仍日文自稱うるは。
- 產品品質必須保留FAIL：認同後仍問不相干的arousal或更多說明；conditional seed可能被表面改成現在已卡住；`我的丈夫今天幫我買了早餐`被更早meal-check規則誤當問角色吃飯、回自己餓了；真正關係拒絕用了來源沒有的dirty/attack意象。M39 bounded accept不是全語意通過；M42沒有修這些下游錯誤。graph仍擁擠且沿用generic PERSONA APPRAISAL分類。
- 實際有效回合2.0452–14.5056s；server另有2筆無turn id的Ollama timeout warning，不強行歸因。temp root`/tmp/uruha-m42-safari.pqqcs9`，session`20260827_150256_5c1f547b`，adaptive store0完整raw輸入，1筆verified typed relation。正式DB未用，27個Safari tabs未關閉／新增。
- 報告：`analysis/m42_cjk_relationship_evidence_acceptance_2026-08-27.md`；精簡Web證據：`analysis/m42_safari_isolated_web_evidence_2026-08-27.json`；presentation manifest：`research/m42_post_web_presentation_manifest_2026-08-27.json`。新入口`uruha_web_ui_m42.py`及`start_uruha_live_m42.py`，原入口保持凍結。
- 本輪測試server`http://127.0.0.1:7880/?m42safari=1`，PTY38814；存活續接時再查。7879的M41.1測試server已停止，其他使用者服務／分頁未關。關閉Safari tab不會刪成果。
- 下一個單一里程碑M43計畫已列於`research/m43_supported_feedback_closure_plan_2026-08-27.md`，尚未實作／凍結reserve。原因已定位：M27/M37有linked supported，M28 exact-token pure-feedback gate卻失配，未授權acknowledgement；V2.13 unknown/pending或泛用fallback再接手。M43需處理已確認act的結束，保留支持+新請求、普通肯定與真正未決資訊；不得只補這個exact sentence或清光不確定性。meal-check角色錯置與protected-surface錯置另作下一步。

### 7.57 2026-08-27 M43 Supported Feedback Closure 實際完成狀態

- 新 M43 module/installer 以整句組合解析區分純支持與新內容；必須已有 M27 decisive linked support 才授權短日文承接。保留原回饋真值、歷史關係、其他未確認事項及保護／事實路徑；不提升心理事實。M39 改驗證當輪承接而非重做先前策略，舊 frozen source 未改。
- 實作前 24-case reserve／protocol 封存，20-file implementation freeze 後唯一正式執行 PASS：判斷 24/24 vs 原 M28 15/24；9/9 純支持、0/15 誤收束，pending 精確處理與上游不變全部通過；p95 0.136ms、0 新模型呼叫。這是作者編寫的 bounded typed-feedback 契約，不是 independent holdout／LLM 或人評優勢。
- 13 新 focused 加原 210 選定回歸共 223/223、29.61 秒、3 依賴警告；另 1 presentation-only CSS test。真正 runtime 契約仍是 fake generation。精確已綁定 pending 收束僅有契約證據，Web 沒有產生合格 pending，不可偷換成 Web 全流程通過。
- 主 Safari 10 輪有效輸入逐次 paste 核對：en／zh／ja 有有效前一輪紀錄的 3 次確認全部自然承接；其中中文確認使 M37 report→share_arousal 關係保存，第 5 輪成功重用。4 次純確認總計 3 成功、1 失敗，不能省略失敗分母。10/10 日文可見，角色 self identity 保留。
- 保留 FAIL：第 1 輪 presentation gets stuck 未被 M37 認為 trigger；第 5 輪 M37 真正陪伴卻被 M32 suppresses_new_pending_prediction 清掉後續紀錄，第 6 輪「その通り、ありがとう。」又泛問；第 9 輪確認+新實用要求雖未被 M43 吞掉，但原 planner 沒給下一步。這些不能算整體理解通過。
- 同句日文在第 8 輪（有 prediction）成功承接，在第 6 輪（無 prediction）失敗。49/49 可用 M39/M40/M42/M43/binding payload 在 logic／主圖／same-cycle history 相同。實際 user wait 2.014–19.6267 秒，短確認仍約 10 秒；沒有宣稱 0.136ms 是整輪延遲。
- 10 輪主驗收 temp `/tmp/uruha-m43-safari.xZvLgA`、session `20260827_153741_1ec7bad2`；所有 log/DB/store 隔離，0 完整原句進 adaptive store。兩個正式 Chroma SQLite 檔 SHA 前後相同。27 個 Safari tabs 未增減，M42 7880／初版 M43 7881 服務已停止，檔案未刪。
- 初版圖卡的暗字／窄版問題有真實失敗截圖；以獨立 `uruha_m43_readable_memory_observatory.py` + `uruha_web_ui_m43_readable.py` 做純 CSS 修正，不改 M43 freeze/result。最新隔離站 `http://127.0.0.1:7882/?m43readable=1`，temp `/tmp/uruha-m43-readable.AWVJxc`，PTY67266（首次 CSS QA 的 PTY26165 已停止），存活續接時再查。大圖整體仍擁擠，不宣稱 outsiders UX 全面完成。
- 報告 `analysis/m43_supported_feedback_closure_acceptance_2026-08-27.md`；主 Web `analysis/m43_safari_isolated_web_evidence_2026-08-27.json`；呈現 Web `analysis/m43_readability_web_evidence_2026-08-27.json`；封存 `research/m43_implementation_freeze_2026-08-27.json` 與 post-web manifest。
- 下一個 M44 已只讀定位及列規格於 `research/m44_executed_action_feedback_plan_2026-08-27.md`，尚未實作／封存新 reserve。單一變因：最後真正執行且通過表面檢查的已驗證回覆策略，要有下一輪可驗證 receipt；不能把任何純字面回覆都登記為心理策略，也不能覆蓋 unrelated pending 或重設已決 outcome。先看新 plan、git 狀態、freeze integrity 後直接續做，不用再次確認。

### 7.58 2026-08-27 M44 Executed Action Receipt 實際完成狀態

- 延續 M43，不等待額外確認，已實作獨立 M44 post-emission receipt。只有當輪有效 M37 verified relation、decision/branch/policy/input 一致、M39 最後表面通過、且 pending 因 literal 層缺失時補上下一輪紀錄；不改先前 plan，不重寫 resolved ledger、不覆蓋其他 pending、不提高關係信心／TTL，不把紀錄建立當使用者支持。
- 新 store 欄位 `executed_action_receipts_m44` 有 typed whitelist、32 筆上限及正常 save/load；僅下一個 user turn 有效，過期不硬算支持。原 M27/M38 決定後果；receipt/outcome 都有 runtime node、final snapshot、owner 與 same-cycle history 同步。
- 24-case 作者自編 typed contract 先封存，implementation freeze 後唯一正式 run PASS：判斷 24/24 vs 原 M43 狀態 19/24，5/5 合格補紀錄，0/19 誤登記，後續 outcome 5/5；新增模型呼叫 0、心理事實 0、raw 0、implicit calibration inflation 0。不是 independent holdout／LLM 或人評比較。
- 233/233 選定測試，34.14s，3 依賴警告；9 個新 M44 + 原 223 + 1 CSS。runtime 合約明確使用 fake generation、真 M39 checker 與 missing-pending fault injection，不能當 Web 新生成證據。正常磁碟 roundtrip 僅契約測試。
- 真實 Safari 新隔離 session 跑 9 有效輪，逐次 paste 核對、觀察回覆和下圖。turn3/5/7 確實補出缺失紀錄，turn4/6/8 分別為 supported/contradicted/uncertain。原 M43 會泛問的 `その通り、ありがとう。`，turn4 現在回 `ん、伝わってたならよかった。`。這是已知序列的新執行回歸，不是未見 holdout。
- 保留 FAIL：turn6 已認錯、M34 改選 solve_regulation，但只回 `あー、そこ読み違えた。今すぐできる一個だけ一緒に決めよ。`，沒給步驟。M39 的 `一個/決めよ` regex 誤把提議當交付。turn8 `明日に授業があるんだね。` 字面對但措辭較不自然；不能將 9/9 日文寫成自然度滿分。
- 56/56 可用 M39–M44/binding payload 在 logic／runtime／same-cycle mirror 相等；9/9 圖 node 唯一連線且 budget 通過。三份結果沒有回寫成全成功；share_arousal scope reliability 0.6667→0.5，未知只增 uncertain 不提高 mean；implicit 有效樣本仍 0。user wait 2.0183–14.2507s，短確認仍 10.1783s。core check 不含磁碟保存。
- 圖卡已在 Safari 目視核對；節點第3輪展開過，右側詳細預覽仍有裁切、整張圖仍密集，非完整 outsider UX。觀察到2個無 turn ID 的 Ollama timeout 警告，9輪皆完成，不假稱零警告。一次 Find 貼上逾時未送出聊天，已恢復，沒有無效對話輪。
- 新入口 `uruha_web_ui_m44.py`，`http://127.0.0.1:7883/?m44safari=1`，temp `/tmp/uruha-m44-safari.JZBsIK`，session `20260827_224641_b6aae58e`，PID4142／PTY80022；續接先查存活。舊 M43 7882 PID3339 已停止，檔案全保留。27 Safari tabs 未增減。兩個正式 Chroma SQLite 前後 SHA 相同，此程序只開隔離 DB。無 commit/PR/merge/deploy，無原始 dirty checkout 修改。
- 報告 `analysis/m44_executed_action_receipt_acceptance_2026-08-27.md`、Web精簡證據 `analysis/m44_isolated_safari_evidence_2026-08-27.json`、唯一正式結果 `analysis/m44_executed_action_receipt_reserve_raw_2026-08-27.json`、M44 implementation/post-web manifests。M37–M44 frozen core/eval/tests/results 不改不重跑。舊 M44 plan 也已被 M43 post-web manifest 鎖住，不更新它。
- 下一個必要工程 **M45 Actionable Help Delivery**：`research/m45_actionable_help_delivery_plan_2026-08-27.md`，只讀定位／規格完成，尚未實作。單一變因是 practical-help 真的交付具體、來源一致的可執行步驟；缺必要脈絡可短問，但不得算已完成。不要用固定報告範例硬編答案，也不要把 M44 成功包裝成理解能力或人腦方程式完成。

### 7.59 2026-08-29 M45–M45.2：交付部件部分完成，實用性仍FAIL

- 按§0.1研發優先繼續，沒有等使用者再確認。已完整读交接、檢查git，仍在安全worktree與原分支；未碰原始dirty checkout、未部署／commit／PR／merge。舊M37–M44 frozen核心、測試、結果不改；M45之後同樣分版保留首次結果。
- M45新增 `uruha_actionable_help_delivery_m45.py` 及opt-in入口／圖卡：最後solve回覆需有task source、object、verb、可觀察completion；本機qwen3.5:9b最多2呼叫、共用18秒（原12秒在開發逾時，修訂另檔保留）。語意審核只是同模型proxy，不是人評。新增typed未交付紀錄，下一輪不能把未交付方法當成功；不改resolved歷史、不寫心理事實。
- M45預列24項typed契約結果24/24，原M39keyword檢查6/24；這是檢查器對照，語意位元為fixture輸入，不是LLM能力比較或holdout。原實作238/238選定測試。開發probe01–12包含多次失敗，均保留，不回填成事前已知。
- **M45首次Safari11輪FAIL**：純「給我一步」被補出資料／會議情境並誤判delivered；第6輪未有原M44完全相同前置receipt，僅當輪要求被當task source；第8輪有內容仍拒答。第7輪人稱錯誤，第9輪「不要給我方法」被M25選solve，第10輪日文手順未辨識，第11輪日文問名字未正確回答。這些未修，不能宣稱人格／路由全過。M45圖payload 11/11同步、unique connected；utterance精確字串10/11，第9輪全形/半形空白差異。
- M45.1 `uruha_task_evidence_authorization_m45_1.py`：用既有M25/M36與correction classifier按標點排除回覆形式／糾正子句，保留独立內容的原始offset/digest；不是task白名單，task只嵌在request子句時會保守拒绝。**新Safari8輪：缺任務零模型呼叫、確認後solve可靠度仍0.5、無atom_changes；8/8 trace核對。三個有任務案例仍0/3交付，FAIL保留。** 正常傾聽及英文Who are you可維持既有角色回覆，不能抵銷原日文身分失敗。
- M45.2 `uruha_action_extraction_contract_m45_2.py`：review schema的source ID/原文引用只能選合法來源；允許实际出現在回覆中的單漢字object。未放寬任何語意審核位元。單元測試曾抓shared `_TEXT` alias造成enum污染，修正後 **256/256選定測試（37檔，40.87s，3個既有依賴警告）**。不是全歷史suite。
- **M45.2新Safari5輪：三個有任務案例只有1/3自評delivered，0/3可確認有效推進目標。** 書架案例僅回「本棚の一番手前にある本を、隣の本と入れ替えてみる。」任意交換不等於整理，不能算有用；另2個被casual-Japanese proxy拒絕。來源格式3/3及5/5×6項trace核對通過。不把可執行动作等同help成功。新增6呼叫，2415 prompt+629 completion tokens；整輪2.0603–21.4135s，短確認仍慢。
- 三次共24個實際Web輪次，是相依修復驗收，不是24個獨立holdout。精簡報告 `analysis/m45_actionable_help_delivery_acceptance_2026-08-29.md`；各版`*_isolated_safari_first_result_*`、`*_safari_observations_*`、`*_safari_raw_*.jsonl.gz`保存完整來源與實際Safari觀察。圖卡及真正節點已目視/展開，但全圖仍擁擠、節點預覽受220-byte限制；不能稱完整outsider UX。
- 最後入口 `uruha_web_ui_m45_2.py`，`http://127.0.0.1:7886/?m45_2safari=1`，temp `/tmp/uruha-m45-2-safari.0bfQdA`，PID36126／PTY82348；續接先查存活。舊本任務7883/7884/7885已停止、檔案保留；只沿用一個Safari分頁、未加新分頁。兩個正式Chroma DB前後SHA256相同，見報告。
- 下一個必要工程參見 `research/m46_goal_progress_delivery_plan_2026-08-29.md`，**只有定位／計畫，尚未實作**。目標是讓建議在生成前已有任務目標與可觀察進展條件，避免任意動作被判有幫助；先保存隔離拒絕候選作診斷，不把語氣審核false改true，不加固定報告／書架答案。上游否定／身分／澄清／速度另列，不混作一次修改。M45整體尚未達成功條件，不宣告Goal完成。

### 7.60 2026-08-29 M46：目標進展機制已接入，完整跨語言管線仍 FAIL

- M46 是新 opt-in overlay，不改 M45–M45.2 凍結檔。實用建議在可見句之前先形成 exact
  user source、task goal、observable progress criterion、typed progress mechanism、action、
  expected state change、unknown constraint；第二個同模型呼叫在看不到 planner mechanism
  自我標籤下重新分類，內容與日文表面分開。這是可反駁工程假設，不是讀心或人類效用真值。
- 三種非進展類型 `same_task_smaller_unit`、`random_rearrangement`、`unknown` 不可交付；動作
  還須有逐字 object、內部動詞、停止 cue。拒絕草稿只在隔離 diagnostic trace，adaptive
  long-term record 不存 raw candidate。M46 node 唯一、相連，圖卡顯示六段 goal→effect 流程。
- 開發真模型暴露動詞形態漏判、第一段換名、plan/surface 不同詞、18/26秒逾時、機制分類歧義、
  表面停止線與來源綁定；共同上限最後 34 秒。不能把加 timeout 稱效能改善。最終選定回歸
  **268/268（38檔，42.23秒，3個既有依賴警告）**，不是全歷史 suite。
- 正式隔離 Safari 8輪：缺任務0呼叫且不捏造；下一輪未交付不計成功；英文空白報告交付
  `とりあえず「はじめに」という見出し行一つ書いてみよ`，圖上 goal／criterion／effect
  與內容／日文通過可見；日文書架未被上游選 help；中文信件／收據到 M46 但候選缺 object
  與停止線而拒絕；日文不要方法正確；中文不要方法仍被上游誤選 solve。8/8可見日文，
  但具體任務只1個交付，不能宣稱跨語言成功或人類偏好。
- 正式8輪 M46 共4次完成呼叫、3323 prompt＋744 completion tokens、42.27065秒；成功輪
  M46自身25.39852秒。首次 exact trace 只有7/8，因全形／半形空格；修正後單輪1/1與
  post-fix三輪3/3全部 trace/history/node/digest/utterance/origin一致，首次失敗保留。
- M45.2 的任意換書舊反例未覆寫；post-fix Safari 書架候選 `棚の本を左から右へ並べよう`
  因缺停止點被拒，沒有冒算 progress。這是相依對照，不是 unseen holdout。
- 正式 DB SHA256 未變。第一次 Web 因漏設 log env 追加的9筆已依唯一 session 精確移除，
  壓縮 raw/text backup 可恢復；CJK模擬輸入變標點的工具錯誤不計正式產品結果。run2/run3
  memory/model/log 全在 `/tmp/uruha-m46-safari.OFth4S/`。
- 完整報告 `analysis/m46_goal_progress_delivery_acceptance_2026-08-29.md`；正式八輪與 post-fix
  audit、原始 gzip、三張 Safari 圖均在 `analysis/m46_*`。目前實驗頁
  `http://127.0.0.1:7887/?m46safari_run3=1`，PID48757，Safari停在成功圖卡；27分頁前後不變。
- **M46 mechanism integrated，但 full-pipeline gate FAIL。** 未解：日文 practical-help 路由、
  中文否定範圍、中文自然 action、澄清銜接、25秒級延遲、長對話／人評。下一步只做
  `research/m47_crosslingual_help_routing_plan_2026-08-29.md` 的單一變因，不用 M46 掩蓋路由錯誤。
- 未 commit／PR／merge／部署；原始 dirty checkout 不碰。長期 Goal 未完成。

### 7.61 2026-08-29 M47：跨語言 help route 通過，實際步驟交付仍 FAIL

- M47 是新 opt-in overlay，只改 current-turn desired-response scope，不改 M46 的 goal、進展
  機制、同模型 review、34秒預算或交付門檻。中文／英文／日文正向一步請求授權
  `solve_regulation`；明確不要方法則 negate solve；普通提到「方法」不再產生 solve request。
- 舊錯誤已保留：修正前日文 `手順を一つだけ教えて` 為 `selected=null`；中文
  `不要給我方法` 反而選 solve；普通「看過這個方法」底層 solution atom=0.98。第一版 M47
  仍把否定句內的 `給我方法` 當正向，之後才以 span containment 移除假正向；後續不重疊的
  replacement request 仍可授權。
- source evidence 只保留 current-input 的 exact offset／length／digest，不把原句複製到
  adaptive long-term model；`long_term_memory_write=false`。M47 node 唯一、相連，圖卡顯示
  語言 → 回覆形式範圍 → task位置 → 實際策略 → M46應／實際介入 → route verdict。
- M47+M25/M36 17/17；M16–M46選定38檔加M47 **275/275（42.81秒，3既有依賴警告）**。
  第一次擴大命令因 zsh 變數未拆分而0 tests，未冒算通過；不是全歷史 suite。
- 正式隔離 Safari session `20260829_215140_740eebe1` 六輪：日文／中文／英文要一步全部
  authorize→solve 並進 M46；日文／中文不要方法全部 forbid 且避開 M46；中文只提到方法
  沒有誤觸 solve。route 6/6、可見日文6/6、正向介入3/3、非正向避開3/3。
- **完整管線仍 FAIL**：三個正向案例實際 action delivery 0/3（日文 reviewer timeout；中文
  與英文 plan rejected）。中文 no-method 雖不再 solve，表面仍問「方法還是傾聽」，所以
  禁止方法表面遵守只有1/2；普通方法名詞也仍引出多餘 response-mode 澄清。不得把 route
  pass 寫成 useful help 或 felt-understanding pass。
- 原 checkout／安全 worktree 正式 Chroma DB SHA256 仍為 `9bd050...895f`／`eb3483...cf4`。
  本輪 memory/model/log 位於 `/tmp/uruha-m47-safari.IlCkB8/`；Safari 沿用一個既有分頁由
  7887 導向 `http://127.0.0.1:7888/?m47safari=1`，沒有新增或關閉其他分頁。
- 完整報告 `analysis/m47_crosslingual_help_routing_acceptance_2026-08-29.md`；逐輪 audit、
  observations、raw gzip、六輪 chat 與 route card 均在 `analysis/m47_*`。沒有 commit／PR／
  merge／部署；原始 dirty checkout 不碰，長期 Goal 未完成。
- 下一個單一變因 **M48 Cross-Lingual Action Realization**：固定 M47 route 與 M46 usefulness
  gate，只改善中／日／英 task source 到自然日文 action plan 的 object／verb／visible stop
  保留與穩定性。中文 no-method 澄清連續性另列，不得混入 M48。

### 7.62 2026-08-29 M48：表面動作可對齊，source-qualified task 仍遺失

- M48 opt-in overlay 只允許由既有 `action_object_jp/action_verb_jp/action_step_jp/completion_jp`
  修 visible instruction 的 object／stop／casual-Japanese mismatch；不改 goal、criterion、
  progress mechanism 或其他 semantic fields，reviewer 也看不到 M48 私有 trace。
- nonprogress、task relabel、invalid internal fields、missing object binding 全部 fail closed；M48
  成功 repair 後仍需原 M46 content/surface review。runtime node/card 顯示 internal fields、
  pre-gap、repair、stop 與 remaining authority；long-term write false。
- 開發保留 unmatched-parenthesis collection error、三個未過M45.1的錯誤test source ID，以及首個
  Safari `action_verb_jp=分けよ` 無法 bounded inflect。支援已實現短命令後 focused 28/28；
  M16–M47選定39檔＋M48 **284/284（41.94秒，3既有依賴警告）**，非全歷史suite。
- 正式隔離 Safari session `20260829_221224_2ffcdcb6` 七輪：trace7/7、日文7/7；M48 repair 1、
  repair contract1/1、not-needed1、fail-closed/block4；6個help中M46交付2。8 completed calls、
  6678 prompt＋1863 completion、M46/M48 path累計99.70422秒，延遲仍FAIL。
- 真 repair 輪將缺 visible stop 的既有 action 對齊成
  `見出しと導入文を書いてみよ。それができたら、そこで止めよ。`，M46 proxy交付；但 source
  要求「見出しを三つ」，plan卻改成「見出し＋導入文」。bounded author source alignment僅
  1/2 delivered，該輪是 same-model reviewer false accept，不算 useful-help 成功或人評。
- 原因定位：M47 task_spans 已找到 embedded `見出しを三つ作るために`／`色ごとに分ける`，
  但 M45.1/M46 排除含 response-form 的整句，planner只看到獨立「レポートが白紙」等內容。
  下一步不是再放寬surface，而是安全交接 M47 已分離的不重疊 task evidence。
- 報告 `analysis/m48_crosslingual_action_realization_acceptance_2026-08-29.md`；正式七輪／首次
  failure raw、audit、observations、actual turn6 HTML與Safari三卡圖均在 `analysis/m48_*`。
  正式DB hash未變；同一Safari tab目前顯示 frozen real turn6 trace replay，live 7889仍在。
- 下一個單一變因 **M49 Route-Qualified Task Handoff**，計畫見
  `research/m49_route_qualified_task_handoff_plan_2026-08-29.md`。不改 M46 reviewer/M48 surface、
  不加 task白名單、不混 no-method 澄清。未 commit/PR/merge/deploy，長期Goal未完成。

### 7.63 2026-08-29 M49：exact task span 交接完成，planner 選擇仍不穩

- M49 只將 M47 找到、與 response-form evidence 不重疊的 current-user task span，以原始
  offset／digest 交給 M46；不翻譯、不推論、不寫 long-term person model。正式 Safari 六輪
  exact span handoff 2/2、route trace 6/6、自然日文6/6；新增 span 真被選為 goal 1/2。
- 四個有任務案例只2/4交付；日文分色 span 已到但 planner 不選，英文單一來源仍 plan reject。
  純 request 與 no-method 2/2安全。6次完成模型呼叫、5362 prompt＋1487 completion tokens、
  路徑累計85.46056秒。M49 contract PASS，但 practical-help pipeline FAIL。
- selected regression 首次289/290：`You misunderstood; give me a method.` 的 meta-correction
  被誤當 task prefix。增加既有 M45.1 correction classifier 的 isolated-span gate 後，聚焦47/47、
  選定回歸291/291；新 Safari regression added_count0、模型呼叫0、awaiting_context。
- 報告 `analysis/m49_route_qualified_task_handoff_acceptance_2026-08-29.md`；formal/postfix raw、
  audit、frozen turn2 HTML與 Safari 圖均在 `analysis/m49_*`。沒有 commit／部署，長期Goal未完成。
- 下一步 M50 將同一輪相容的 exact fragments 組成唯一 planner source；不修改 M46/M48。

### 7.64 2026-08-30 M50：完整 source bundle 完成，planner 候選品質成為主瓶頸

- M50 將同一 current-user turn 中通過 M45.1/M49、offset 不重疊且無 observable correction 的
  exact fragments，按原順序組成唯一 `current_task_bundle_m50`。component ID／offset／digest
  可回原文；trace不存raw、long-term write false。只證明結構共現，不冒稱語意相容。
- 開發保留兩種失敗：首個 Web wrapper 呼叫不存在的 chained main；首次合併測試因 M50 全域
  install 污染 M49 契約而2 fail。分別修成既有 build_demo 啟動與 test-local patch 後，聚焦54/54；
  M16–M50選定回歸 **298/298（43.03秒，3既有依賴警告）**，不是全歷史suite。
- 正式 Safari session `20260830_155659_16416b2e` 五輪：trace5/5、自然日文5/5、exact bundle
  ledger2/2、兩個多片段案例都只剩1個planner source；純request/no-method 2/2安全。
- 有任務三輪0/3交付：report只提「先寫一個」而被判same_task_smaller_unit；color只重述分紙且
  漏stop；英文heading action relabel。這是M46正確拒絕，不是M50把拒絕冒算成成功。3次完成
  模型呼叫、2623 prompt＋697 completion tokens、路徑43.46428秒。pipeline仍FAIL。
- 報告 `analysis/m50_current_task_source_bundle_acceptance_2026-08-30.md`；audit、observations、
  formal raw、frozen turn2 HTML與Safari圖在`analysis/m50_*`。目前Safari顯示frozen M50 turn2；
  live 7891仍是隔離temp。未commit／PR／merge／部署，正式DB未使用，長期Goal未完成。
- 下一個單一變因 **M51 State-Changing Candidate Generation**：計畫見
  `research/m51_state_changing_candidate_generation_plan_2026-08-30.md`。只改善來源綁定的候選
  多樣性與狀態改變，不放寬M46 rejection gate、不加task白名單、不混人評／長對話／延遲。

### 7.65 2026-08-30 M51：兩個狀態改變候選已接入，欄位與口語實現成為瓶頸

- M51 在原 M46 plan call 的位置，以同一 `qwen3.5:9b` 呼叫產生 exactly two source-bound
  candidates；依既有 `structural_plan_violations` 去重與選擇，再交原 M46 counterfactual review。
  沒有增加 M46 plan+review 的模型呼叫數，也沒有讓候選存在直接等於可交付。
- candidate schema 緊湊為 mechanism/object/verb/effect/stop/instruction。所有生成操作欄位須為
  日文；trace只保留fingerprint、mechanism、violations與數量，raw candidate不持久化、long-term
  write false。缺任務與明確不要方法路徑0 candidate、0新增模型呼叫。
- 開發失敗完整保留：首輪candidate JSON超出輸出額度；explicit color rule機制曾被錯標；複合
  verb曾違反單一動詞契約；日文report content過但surface不過；英文report object過長且未逐字
  出現在instruction。另一次回歸清單去重寫錯，重複收集到505 pass時中止；不能算正式證據。
- 有效選定回歸為 **305/305（42.35秒，3個既有依賴警告）**。正式Safari session
  `20260830_162123_4a627afe` 五輪：trace5/5、日文5/5；三正例two distinct candidates 3/3，
  至少一個結構valid 2/3，最終交付1/3；missing-task/no-method安全2/2。
- 真成功輪將依顏色分紙轉成可觀察分組並交付；文字仍有重複、偏正式。日文report scaffold的
  content review通過但casual surface fail；英文report兩候選皆因object/instruction literal binding
  失敗。5完成模型呼叫、3801 prompt＋1553 completion tokens、M46路徑80.55061秒。
- 報告`analysis/m51_state_changing_candidates_acceptance_2026-08-30.md`；audit、observations、
  formal raw、frozen turn1/2 HTML與Safari圖在`analysis/m51_*`。M51 contract PASS，practical-help
  pipeline仍FAIL；不是人評、felt-understanding或人腦方程式證據。
- 下一個單一變因 **M52 Candidate Realization Contract**：只把已生成操作轉成instruction逐字含有
  的短object、單一可見動詞與自然casual Japanese；task goal、effect、stop與source不得改，修後
  仍由同一M46 review決定。未commit／PR／merge／部署，正式DB未使用，長期Goal未完成。

### 7.66 2026-08-30 M52：候選實現契約通過，來源外 scaffold 被 same-model reviewer 誤放行

- M52 只在 M51 candidate 進 M46 前做 deterministic realization：object只能縮成原object與
  instruction共同已有、位於可見受詞位置的日文子字串；規格句尾轉成casual command。第一個真
  Web又發現舊regex把句中「三個」誤算stop，故只使用候選既有stop field把停止條件真正說出。
- source ID/span、goal、unknown、mechanism、effect、stop byte-for-byte不變；不新增模型呼叫，
  找不到共同物件fail closed。trace只存digest/改動類型，raw candidate與long-term write皆false。
- 初始整合測試2 fail是fixture未複製M50重寫後source ID；只修fixture。首版Web完成candidate但
  34秒內review timeout，保留不冒算。最終聚焦36/36；選定回歸 **313/313（43.53秒，3警告）**。
- 正式Safari session `20260830_164209_4f6310e9` 五輪：trace5/5、日文5/5、三正例realization
  contract3/3、交付2/3、安全2/2。6完成模型呼叫、4731 prompt＋1855 completion，M46路徑
  95.84866秒。
- 日文color來源對齊且交付。日文白紙report卻自行補`環境／経済／社会`；來源沒有題目，這是
  明確false accept，儘管M46把no_invented_facts判true。英文object契約修好但長規格句仍被
  casual-Japanese proxy拒絕。bounded author source alignment僅1/3，pipeline FAIL。
- 報告`analysis/m52_candidate_realization_acceptance_2026-08-30.md`；audit、observations、formal
  raw、frozen false-accept HTML與Safari圖在`analysis/m52_*`。不是human preference、open-domain
  usefulness或理解證據。
- 下一個單一變因 **M53 Source-Neutral Scaffold Authorization**：無exact source支持的具體topic／
  category label不能交付；可保留空槽位或結構占位。不得固定寫report答案、不得取代M46整體review。
  英文長句自然化另列。未commit／PR／merge／部署，正式DB未使用，長期Goal未完成。

### 7.67 2026-08-30 M53：來源外具體標籤已阻擋，完整實用建議管線仍未通過

- M53 在 M52/M46 前加入 source-neutral scaffold authorization：來源未明列的具體題目、分類或
  scaffold label 不得靠 reviewer 猜測後交付；有來源明列時才授權，空白任務則維持安全拒絕。
- 聚焦測試 **33/33**；選定相容回歸 **319/319**。正式隔離 Safari 五輪中，空白報告的自創標籤
  被 `unsupported_concrete_scaffold_label_m53` 阻擋；來源明列標籤的案例通過 M53，但 M46 review
  timeout，沒有冒算交付；顏色分組案例可交付；missing-task 與 no-method 皆安全。
- 五輪共4個完成模型呼叫、2900 prompt＋1253 completion tokens；M46路徑時間合計約88.17153秒。
  這證明 bounded source authorization，而不是完整 practical-help、自然度、人評或人腦方程式。
- M53 原始Web證據在 `analysis/m53_safari_formal_five_turn_raw_2026-08-30.jsonl.gz`；正式DB未使用。

### 7.68 2026-09-01 M54：候選人類反應方程式 V1 契約與runtime圖像接入完成

- 使用者已把主線改為可觀察、可干預、可否證的候選人類反應方程式；M1–M53保留為既有器官與
  失敗史，不再以局部回覆修補充當最終目標。M54–M62為樂觀完成線，可誠實重試至M75硬停止。
- M54凍結九個變數 `X/H/M/S/R/N/C/theta/U`、primary observable behavior、secondary desired
  response policy、downstream utterance、outcome/update、provenance、intervention與claim boundary。
  read-only adapter不改回覆／決策、不加模型呼叫、不寫長期記憶；未知變數必須保持未知。
- JSON與compile通過；聚焦 **10/10**；M1–M53選定相容回歸＋M54 **329/329**（46.43秒，3個既有
  警告）。這不是全歷史suite。
- 隔離Safari session `20260901_050820_8ba6d32e`：輸入「方法はいらない。ただ聞いてほしい。」
  得到自然日文「うん。今は方法出さないから、そのまま話して。そのくらいでいいだろ。」；
  M47阻擋方法生成，M54來源覆蓋由1/9升至7/9，`S/C`保持unknown，primary真人行為分布明確顯示
  尚未形成，secondary policy已正規化，圖上有唯一M54 node。測試DB與log都在`/tmp`。
- 驗收報告：`analysis/m54_human_response_equation_v1_acceptance_2026-09-01.md`。M54只證明方程式
  契約可測、可接runtime，不證明真實人物預測、人類等價或LLM優勢。
- 下一個單一里程碑是 **M55 Timestamped Real-Person Longitudinal Pilot**：先做有時間截止、來源與
  獨立編碼規則的小型真實人物資料pilot；不能用未來資料回填變數，也不能在sealed future上調式。
- Desktop Goal API不能改寫仍未完成的paused objective；舊Goal未被假標完成。專案交接與roadmap已
  將M54–M75設為最高優先；若要讓桌面Goal排程顯示新文字，仍需使用者在UI replace/resume。

### 7.69 2026-09-01 M55 readiness：前內容與時間隔離已通過，真人資料pilot被可靠度gate阻擋

- 新增 `audit_m55_real_person_longitudinal_readiness.py`，把M54 Equation V1接到既有V7 codebook
  reliability與V9 Uruha target-calibration資料線；它只讀hash／count／gate，不讀或上傳私人標註內容。
- pre-content gates全通過：M54契約有效、V7/V9凍結binding有效、3個官方Uruha來源有publication date、
  30個內容無關target slots平衡、final sealed future在frame中為0。
- 真正M55仍 **BLOCKED**：兩份V7 private ledger目前0/18與0/18、reliability lock不存在；因此V9仍是
  target event 0/30、independent review 0/30、human coder 0，M56明確不授權。Codex不得假造第二真人
  或用synthetic/model labels補過此gate。
- 聚焦 **8/8**；含M54與V7/V9凍結result tests的相容組 **34/34**。圖像renderer顯示
  `M54 → V7 → V9 → M55 → M56`，並驗證不洩漏token、URL或私人paraphrase。報告
  `analysis/m55_real_person_longitudinal_readiness_2026-09-01.md`。
- 兩個本機隔離V7服務已啟動在ports 7901/7902；Safari現開coder-01的0/18頁。session token不寫進Git，
  重啟會改。coder-02必須由不同真人在同一台Mac獨立完成；任一人都不能看另一份ledger。
- 只有兩份18-slot ledger完成且既有analyzer達成mean temporal IoU≥0.5、所有primary nominal
  Krippendorff alpha≥0.667後，才可啟動V9兩人30-slot Uruha calibration；否則保留舊ledger、修codebook、
  用新preregistered pilot重試。這是第9節允許停下的真人主觀判斷硬gate，不是程式等待確認。

### 7.70 2026-09-01 M55 temporal-row contract：預測切點已可檢查，真人pilot仍未完成

- 只讀稽核發現V9只有整段event start/end，不能證明context在目標行為開始前停止；若把event start
  偷當prediction cutoff會洩漏答案。新增獨立M55 temporal-row contract，要求input start、cutoff、
  behavior start、behavior end四個界線，且不改V7/V9凍結schema、slot、ledger或結果。
- 新契約綁定M54 Equation V1、event schema、V6 codebook、V9 frame/source/result lock共6個SHA；九個
  Equation變數各有observed／pre-cutoff derived／unavailable狀態，`S/N`不從公開行為硬猜。
- fail-closed compiler只接受明確傳入的private record pack；禁止raw/verbatim/model/private-state欄位、
  時間重疊、假真人review與current outcome回填。2-row synthetic工程fixture為0 leakage、1個合法歷史
  reference，且model execution/formal claim固定false。
- readiness新增`30/30 cutoff→future rows` gate；目前contract PASS、V9 alone不可編譯、真人rows 0/30、
  V7仍0/18與0/18、V9 target 0/30，故M55真人pilot仍BLOCKED、M56仍NOT AUTHORIZED。
- 聚焦＋相容組 **46/46**，compile與diff check通過。Safari在既有空白tab實測read-only圖像頁，顯示
  `可觀察輸入X → locked cutoff → 未見行為Y`、九變數missingness與誠實的0-row/M56禁止狀態；沒有
  新增或關閉分頁、沒有讀取私人ledger內容。
- 驗收：`analysis/m55_temporal_row_contract_acceptance_2026-09-01.md`。下一個可獨立工程單元是private
  two-coder boundary-extension collection instrument；只可用synthetic fixture測工具，V7可靠度通過前
  不得消耗Uruha target內容或把它稱為真人結果。

### 7.71 2026-09-01 M55 two-coder boundary tool：工程工具通過，真人證據仍為0

- 新增獨立、gitignored、atomic-write 的 M55 boundary ledger；每位 coder 只載入自己的 V9 entry
  與自己的 boundary ledger，另一人的資料在收集時不可見。每筆以 V9 entry digest 綁定，不修改
  frozen V7/V9 schema、slot、ledger、codebook、threshold 或 result。
- contract 綁定7個 frozen dependency、要求17個欄位；四個時間必須符合
  `event start <= input start < cutoff < behavior start < behavior end <= event end`。pre-cutoff input
  必須重新改寫，不得複製 whole-event context；raw/verbatim/model/private-state key與假attestation拒絕。
- 真實 init／serve 仍需 genuine V7 reliability lock；synthetic ledger 不可啟動真人server，real與
  synthetic ledger不可混比，非finite時間拒絕。server每次GET重新驗證來源；V9 entry若在啟動後
  改變，HTTP 409 fail closed，不讓coder在stale source上繼續。
- 兩份完整、不同真人、相同data kind的ledger才可比較。輸出只有slot digest、input/behavior IoU、
  cutoff差與文字digest是否相同；不顯示paraphrase，不自動平均，不挑文字，不產生formal record pack。
  每列都保留為explicit human adjudication required。
- 聚焦32/32、M54/V7/V9/M55相容67/67、compile與diff check通過。contract hash
  `52426afc62060eaf46c84eec9834c3f7ef78841f63c027b0c70043fd91a41e2e`；implementation freeze已建立。
- Safari實際核對`http://127.0.0.1:7904/dashboard`：兩條私人lane、X/cutoff/Y、IoU、分歧、禁止自動
  合併與V7→V9→M55→裁決→30 rows同頁清楚可見。27 tabs不增不減，沒有填真人表單。
- readiness仍是V7 0/18與0/18、V9 0/30、real temporal rows 0/30、M55 incomplete、M56 forbidden；
  synthetic graph與tests不是human evidence。報告：
  `analysis/m55_boundary_extension_tool_acceptance_2026-09-01.md`。
- 下一個不能由Codex假造的依賴仍是兩位不同真人完成V7。V7通過後才可初始化兩人的V9＋boundary
  工具；30 slots完成後必須先做明確真人裁決與M55 temporal compile，再另凍結M56 protocol。

### 7.72 2026-09-01 M55 explicit adjudication：裁決與record assembly工具通過，真人列仍為0

- 新增獨立private adjudication ledger；初始化永遠是0筆，即使Coder A/B完全一致也不能auto-pass。
  每個paired selected slot都必須由人明確accept A、accept B或manual resolution，並保留兩份V9 entry
  與兩份boundary entry digest。caller輸入順序不影響canonical A/B身份。
- accept A/B只完整複製被選者的event、X/cutoff/Y、paraphrase、public behavior/context/relation，
  不混另一人的欄位。manual resolution需重填22欄record所需內容、理由、信心與三個attestation；
  automatic average／text merge請求、bad chronology、unsupported labels、raw/verbatim/private keys都拒絕。
- 兩份V9與boundary ledger必須完整、有效、不同coder、相同data kind；real V9還必須完整30 slots，
  real init／serve持續需genuine V7 lock。server每次GET/save/export重新驗證四個ledger hash；source改變
  立即HTTP 409。synthetic export固定0 human coder與`synthetic_engineering_only`，不可冒充真人。
- 完整synthetic裁決可輸出並通過既有22-field M55 temporal record validator，但tool/export仍回報
  M55 false、M56 false、model calls 0、sealed future false、production write 0。
- 聚焦9/9、M54/V7/V9/M55相容69/69、compile與diff check通過；contract hash
  `9cb11cca6d75f85f488fbbbcd86054d0ecbe744f1cf5a9754c5c03112b1d3682`，implementation freeze已建立。
- Safari沿用既有M55 tab並維持28 tabs：outsider graph顯示M54→V7→V9→X/cutoff/Y→裁決→M55→M56；
  private synthetic頁顯示兩條完整lane、三種決定、manual欄位與evidence boundary。沒有填寫或送出表單。
- 正式狀態不變：V7 0/18＋0/18、V9 0/30、real temporal rows 0/30、M55 incomplete、M56 forbidden，
  blocker仍是`complete_two_independent_v7_18_slot_ledgers`。報告：
  `analysis/m55_boundary_adjudication_tool_acceptance_2026-09-01.md`。
- 目前所有不消耗target content的M55資料工具鏈已齊。下一個不可由Codex替代的依賴是兩位不同真人
  完成V7；通過後才按V9→boundary→adjudication→temporal compile順序使用，不可跳步。

### 7.73 2026-09-01 M56 blinded fair-comparison preflight：規則已先凍結，正式執行仍禁止

- 在任何真人M55 outcome或M56 generation存在前，先凍結七組條件：B0 prior、B1 current X、B2
  static persona、B3 RAG、B4 full-history summary、B5 structured full history、Ours explicit state
  transition。固定primary contrast為B5 vs Ours；結果出來後不得換較弱baseline。
- B1–B5/Ours綁定相同`qwen3.5:9b` artifact、hardware、decoding與每筆input 8192/output 384預算；
  B0是明列的deterministic exception。B4 summary與Ours upstream成本都需計入；若B5/Ours actual
  prompt tokens差超過5%，必做exact-token sensitivity。
- generation只收cutoff前prediction packet；private outcome key完全分離。七組prediction需先SHA
  commit，之後獨立scorer才可看outcome。condition order按sample hash與seed 560901輪替。
- success需Brier與NLL paired bootstrap 20,000次的95% CI上界都低於0，且Ours top-1不得比B5低超過
  5pp；所有gate都要通過，ECE僅描述。失敗保留，M57才診斷，M58才可單一變因＋新sealed data重試。
- fail-closed validator以synthetic fixture攻擊outcome leak、packet/order/hash、model/hardware/options、
  token、retry/fallback與sample drift；final focused 17/17，選定M1/M2/M6/M54/V7/V9/M55/M56相容
  116/116，compile與diff check通過。contract hash
  `aba95b4c0879cf9b8d70362606e6bf80055f9f34fa3475a8270a6007aa78abec`，implementation freeze已建立。
- Safari沿用既有local tab並維持28 tabs；圖像頁可見七組輸入、answer isolation、same-model/token規則、
  Brier/NLL gate、V7 0/18＋0/18、V9 0/30、real rows 0/30與M56禁止；無水平溢出、無表單送出。
- 正式狀態仍是M55 incomplete、M56 execution blocked、model calls 0、target outcome access 0、formal
  result false；blocker仍為`complete_two_independent_v7_18_slot_ledgers`。報告：
  `analysis/m56_fair_comparison_preflight_acceptance_2026-09-01.md`。這只證明protocol已可被公平執行，
  不證明Equation V1、Uruha預測或任何LLM優勢。

### 7.74 2026-09-01 M56 capability-separated execution capsule：執行／計分工程通過，正式實驗仍禁止

- preflight packet雖無future outcome，仍含完整安全歷史；若把整包交給所有條件，B1/B2可偷看到
  history。新增執行艙把每個sample-condition實體化成獨立view；model request一次只輸出一個view，
  不把七組capsule交給模型。
- B0只看label與pre-cutoff count並驗證Laplace prior；B1/B2無history；B3固定top-4；B4 raw history
  只進獨立summary task，prediction只看已封存summary，所有summary cost另計；B5與Ours使用byte-identical
  source object/hash，B5不得看equation artifact，Ours必須有pre-outcome fit/state/transition三個hash。
- submission嚴格要求sample順序＋每題凍結condition rotation、七組完整且唯一、exact labels、sum-to-one、
  frozen argmax、authorized evidence、同model/hardware/options、0 retry/fallback與完整token/latency/memory。
  全部有效後才建立SHA-256 receipt；任何事後改動都使separate scorer拒絕。
- scorer重驗packet/capsule/receipt/split/outcome key後才join；proper score只用primary observed label，
  acceptable alternatives只影響rank。bootstrap 20,000；<=20 pair用exact sign-flip，正式30 pair用預先固定
  deterministic Monte Carlo 20,000。B5/Ours token差>5%時exact-token sensitivity未過不得formal pass。
- synthetic反作弊final focused **28/28**；選定M1/M2/M54/V7/V9/M55/M56相容 **161/161**；compile與
  diff check通過。contract hash `b30a9ff4a99c68bc28b3c67ad8d68bff13c911d410b7578553c0c7d1e470d84a`；
  implementation freeze已建立。
- Safari沿用既有M56 tab並維持28 tabs，圖像頁顯示七組權限、safe packet→generation compartment→
  SHA commitment→separate scorer、四種作弊阻擋與目前0/18＋0/18／0 real rows；無水平溢出、未提交表單。
- 正式狀態不變：formal model calls 0、target outcome access 0、formal result false；M55仍被兩位不同真人
  V7 gate阻擋。報告`analysis/m56_blinded_execution_capsule_acceptance_2026-09-01.md`。未來真人gate通過後
  還需產生真正pre-outcome Equation V1 fit/state/transition artifact才可執行Ours，不能用fixture hash冒充。

### 7.75 2026-09-02 M56.1 pre-outcome Equation artifacts：真實內容綁定通過，正式實驗仍禁止

- 不修改M54–M56任何凍結檔，新增獨立overlay，把B5/Ours byte-identical source object轉成真正
  content-addressed fit、九變數state與跨cutoff transition；原M56 fixture的`aaaa/bbbb/cccc`只能作
  舊shape測試，不能再通過新的bound submission validator。
- fit只使用`available_at <= cutoff`的已完成observable history，產生13類Laplace prior與sparse
  observable transition counts；第一cutoff history n=0，第二cutoff才使用第一筆已完成history n=1。
  same-target history若倒退、晚於cutoff、含current outcome或改內容後hash不符都fail closed。
- state按M54固定順序materialize九變數；X/H/M/C/theta/U有pre-cutoff typed/digest來源，無可靠證據的
  `S/R/N`保持`unavailable_not_inferred + null + no evidence`，private-state fabrication為0。artifact
  不保存current event或history summary raw text。
- transition只記newly available history、behavior-count delta、fit n變化與各variable status/value-digest
  變化；不聲稱心理轉移、不做behavior prediction或language generation。artifact materialization為
  0 model calls、0 target outcome access、0 production memory writes。
- 只有Ours可取得完整artifact payload；B5或其他條件出現artifact hash即拒絕。Ours submission必須引用
  exact三個content hash與request hash；wrapper receipt同時綁frozen M56 receipt與bundle hash，wrapper
  scorer在讀answer前重驗bundle。synthetic separate scoring仍固定非正式。
- final focused **14/14**；M54–M56 direct **110/110**；選定M1/M2/M54/V7/V9/M55/M56相容
  **170/170**；compile與diff check通過。contract hash
  `32eac97730eddabc8eb11fea23223de37a0db28b739d6d3d6999e9f420c8495f`；2-cutoff bundle hash
  `1bd2353b2ef77ec8c4908ca6d8dae857dac36618474e8d113126d4c36406bf7d`；implementation freeze已建立。
- Safari沿用既有M56 tab導向`http://127.0.0.1:7909/dashboard`且維持28 tabs；頁面顯示
  `same source→Fit→State→Transition→Ours→SHA`、0→1 history、三個unknown、五種拒絕路徑與真人gate，
  無水平溢出、未送出表單。報告`analysis/m56_pre_outcome_equation_artifacts_acceptance_2026-09-02.md`。
- 正式狀態不變：V7 0/18＋0/18、V9 0/30、real rows 0/30、formal calls 0、formal result absent。
  現overlay刻意只允許synthetic packet。真人gate通過並完成30列後，還需另凍結real-data execution
  authorization、重驗所有dependency hashes、計入actual CPU與Ours prompt tokens，才可執行正式M56。

### 7.76 2026-09-02 M56.2 formal real-data activation envelope：正式入口已封閉式建立，目前仍拒絕執行

- 不修改M54–M56.1凍結檔，新增單一live-gated activation boundary。公開audit沒有caller-supplied
  `readiness`參數，只讀標準V7 ledgers／reliability lock、V9 result與private M55 compilation；一個
  外觀正確的30-row packet不能取代真人證據鏈。
- 真人gate未過時，只能建立`pending_activation`的未來執行形狀：30列prediction packet、獨立
  outcome key、30×7=210個condition-separated tasks、30 fit＋30 state＋30 transition=90個Equation
  artifacts，以及綁定本機`qwen3.5:9b`、Ollama、CPU／RAM、decoding與resource規則的run manifest。
- 未來正式資料必須寫入gitignored `analysis/local_m56_formal_execution_v1/<run-id>/`，並隔離為
  generation／commitments／scoring／telemetry四個目錄。outcome key只能在scoring；generation不得
  讀target outcome。30分鐘、single-use receipt只能原子式換成一次no-retry generation lease，不能
  提前授權scoring、scientific claim、production memory write或deployment。
- synthetic rehearsal使用不同schema且明列`formal_authorization=false`。測試中刻意偽造的real-shaped
  30-row packet只證明mechanics可建，仍無法取得live receipt；expired／consumed receipt、outcome-key
  injection、artifact/dependency/model drift、write-before-gate與excess authority全部fail closed。
- final focused **13/13**；M54–M56.2 direct **123/123**；選定M1/M2/V7/V9/M54–M56.2相容
  **188/188**；compile與diff check通過。第一次以缺少pytest的Python 3.14執行所得7個import errors是
  invocation environment錯誤，未計為程式結果；改用repo既有Python 3.12 pytest後得到上述結果。
- contract hash `0a449537e9db629c579bd7f7240f9c06dc4895289a94a276dee6978207bd77ab`；
  dependency-set hash `ca074573da1f72145cd18f69d2fdea4161b80884cb8bc939f2206bc36cc4f078`；
  local model manifest SHA `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`；
  current audit hash `5c31289d6cb20e8ebf2cc74fc79871157add6d8fb4fcb696e048d95542504913`。
- Safari沿用既有M56.1 tab導向`http://127.0.0.1:7910/dashboard`，未新增／關閉tab；頁面顯示
  `DENIED NOW`、V7 0/18＋0/18、V9 0/30、real rows 0/30、四個private compartments、model/hardware
  binding、0 formal calls與無formal result。頁面read-only，可安全關閉，不持有private資料或狀態。
- 正式狀態不變：receipt不存在、formal calls 0、target outcome access 0、formal result absent。
  M56.2只完成未來真人資料到正式執行之間、不能靠公開API注入readiness繞過的fail-closed工程入口；
  它不是能抵抗同機攻擊者重寫程式與全部檔案的cryptographic trust boundary，也不新增真人證據或模型分數。下一個
  不可由Codex替代的依賴仍是兩位不同真人完成V7；在此之前可繼續做不消耗holdout、不假造真人的必要
  工程，但不得把M56.2宣稱為Equation V1、Uruha預測優勢、人類方程式、full-pipeline或production證據。

### 7.77 2026-09-02 M56.3 lease-gated formal generation runner：真實執行／commitment路徑通過，現在仍拒絕呼叫模型

- 不修改M54–M56.2凍結檔，新增M56.2 lease之後的單一正式狀態機：validate consumed lease→freeze
  schedule→B4 summaries→30×7 predictions→actual resource ledger→complete submission→SHA commitment→
  separate-scorer release。公開formal entry point只有`run_id`，沒有provider/readiness/outcome/retry注入。
- M56.2 activation controller仍負責在scoring隔離側重驗真人chain與consume receipt；M56.3 generation
  runner只開generation／commitments／telemetry，不列舉、hash或載入scoring outcome key。B0 deterministic
  0 call；B1–B5/Ours各sample恰好一次call；每個distinct nonempty B4 history另一次summary call。
- 固定local Ollama `qwen3.5:9b`、同manifest/hardware/options、一次transport、0 retry/fallback。每call
  記actual prompt/completion tokens、latency、process CPU、process/Ollama memory、Ollama duration fields、
  model identity、prompt hash與raw-response hash；不保存raw response或reasoning trace。Equation artifacts
  先deterministically rematerialize並記CPU；drift或budget/parse/schema/model/resource錯誤terminal fail。
- 只有210列完整、順序/labels/argmax/evidence/resource/artifact全部通過才能atomic寫submission與SHA
  commitment；之後才建立separate scorer可讀scoring的release。release仍不授權result claim、production、
  deployment、retry，generation仍0 target access。post-commit mutation與scoring-before-commit均fail closed。
- test-only forged 30-row in-memory packet可建立210-task schedule與完整mock submission/commit/release，
  但live audit仍DENIED；mock tokens/latency/memory不是actual formal resource evidence。no-call synthetic
  rehearsal另用不同schema，0 humans／0 lease／0 formal authority。
- final focused **14/14**；M54–M56.3 direct **137/137**；選定M1/M2/V7/V9/M54–M56.3相容
  **202/202**；compile與implementation freeze通過。runner contract hash
  `43eceb6055d1ba12a394caf2e37f01bd0cbe35026bf6aab9186bdbd985720b6e`；live audit hash
  `402fc96fb3d09cbd7b53291ee67d40c62cbfa2264d5a65dca489f7aae98bccf9`；rehearsal hash
  `33f3b1896afee47b96b7243a0f944b441bfd8e0c471d6b6eed915224bd7a7306`。
- Safari沿用同一tab導向`http://127.0.0.1:7911/dashboard`，仍29 tabs，未新增／關閉tab或送出表單；
  圖示六步、generation/scoring硬邊界、V7 0/18＋0/18、V9/real rows 0/30、formal calls/result 0。
  頁面read-only可安全關閉。
- authoritative state不變：lease absent、formal calls 0、commitment absent、scoring release absent、result
  absent。M56.3證明未來authorized generation的runner mechanics，不是actual model resource/performance
  evidence；hash仍是frozen application-level drift control，不是抵抗同機改檔者的digital signature。
  下一個不可替代依賴仍是兩位不同真人完成V7。

### 7.78 2026-09-02 M56.4 separate formal scorer：答案前資源gate與不可變結果路徑通過，現在仍拒絕計分

- 不修改M54–M56.3凍結檔，新增post-commit單一狀態機：revalidate prediction release→check resource
  comparability before outcome→commit scoring access receipt→open withheld outcome→score all seven→frozen
  B5/Ours contrast→private score report→result SHA commitment。公開入口只有`execute_formal_scoring(run_id)`，
  不接受prediction/outcome/metric/threshold/sensitivity/result/readiness/provider注入。
- 在開`scoring/`前重驗M56.2 request／consumed receipt／lease、M56.3 schedule／210-row submission／prediction
  commitment／release、Equation artifacts、runtime binding與逐call ledger。B5/Ours actual prompt-token差若
  超過5%，在答案讀取前停止；不能用caller boolean補過，必須另建prospective exact-token sensitivity freeze。
- private scorer只讀標準outcome key與split report，驗activation hashes、sample/label order、confidence、
  cutoff<observed<source、0 leakage與generation access=false。固定報七組，primary仍是B5_STRUCTURED_HISTORY
  vs OURS_HYBRID；Brier/NLL bootstrap、sign flip、Top-1 noninferiority、McNemar與ECE規則不變，scorer 0 call。
- private report排除source text、raw model response、reasoning與private mental state，只保存aggregate metrics、
  preregistered paired deltas、opaque sample ids、resource totals、hash與bounded pass/fail。score report後再做
  result commitment；中斷可只finalize相同report，mutation或想改decision均拒絕，負結果必須保留。
- test-only forged 30-row real-shaped資料可在temporary directory走210 predictions、180 mock call rows、七組
  metrics與result commitment，且primary metrics與既有frozen scorer完全相同；但它不是真人資料、actual
  model resources或正式結果。no-call rehearsal另用不同schema，0 humans／calls／outcome／formal authority。
- final focused **17/17**；M54–M56.4 direct **154/154**；選定M1/M2/V7/V9/M54–M56.4相容
  **219/219**；compile、JSON、diff與implementation freeze通過。scorer contract hash
  `3c374130102335515114e3a560f3103e06dbc392f46740d6617c7a49b3bebd6a`；live audit hash
  `67c23e06c53718dc4f86e0664d8c25bd26a095738e8e47f89e584211e4243d3d`；rehearsal hash
  `2eeba5c58cf2baa9c13b5c84251f0d196d232b10b08dfd7acb841888104a586f`。
- Safari沿用M56.3 tab導向`http://127.0.0.1:7912/dashboard`，前後均30 tabs，未新增／關閉tab或送表單；
  圖示六步、outcome前5% resource gate、generation/scoring硬邊界、V7 0/18＋0/18、V9/real rows 0/30、
  score access/calls/result 0。server已停止；read-only tab可安全關閉。
- authoritative state仍是prediction release absent、formal scoring denied、target outcome access 0、score
  report/result commitment absent。hash是application-level drift control而非防同機改檔者的digital signature；
  下一個不可替代依賴仍是兩位不同真人完成V7。

### 7.79 2026-09-02–03 M56.5 crash-safe no-retry continuation：中斷可續跑工程通過，正式實驗仍禁止

- 不修改M54–M56.4任何凍結檔，新增M56.3 generation runner的單一恢復overlay。M56.5 mode commitment
  必須在schedule前落盤；Equation bundle重新materialize後checkpoint；每個model step先原子寫invocation
  intent、只做一次transport，再把validated result與actual call telemetry合成一個immutable checkpoint。
- 重新啟動時，完整且重建一致的checkpoint直接沿用，該task不再呼叫模型；checkpoint＋matching intent
  視為crash-window中的完成狀態，清除intent後繼續。只有intent沒有checkpoint表示不確定模型是否已回覆，
  必須terminal，不能retry、fallback或人工補值。transport failure、failure record、source/prompt/resource
  drift、mutated／unexpected／out-of-order checkpoint全部fail closed。
- 公開入口只有`execute_resumable_formal_generation(run_id)`，沒有provider／prediction／outcome／resume／
  retry override。最後仍產生原M56.3 submission、call ledger、prediction commitment與scoring release，並由
  M56.4 prescore重驗；generation不列舉或讀取private scoring outcome。
- forged 30-row fault fixture的中斷續跑與不中斷各自都恰好180 calls；summary artifacts、210 predictions與
  call ledger完全一致。已完成task不重呼；intent-only restart為0呼叫並terminal；checkpoint＋intent crash
  window沿用；transport失敗只嘗試一次。fixture有1個shared empty summary＋210 predictions＝211 steps；
  正式summary數由凍結distinct histories決定，不宣稱固定211或212。
- final focused **15/15**；M54–M56.5 direct **169/169＋4 subtests**；選定M1/M2/V7/V9/M54–M56.5
  **234/234＋4 subtests**；compile、JSON、freeze hash與diff check通過。contract hash
  `4961034f87fb0eb8f812fed88d7722d1e042f0668f102fba88398e377fc9780e`；live audit hash
  `5f8a9ec165d82a99f0d0b5af3f2af09b79b6f6043b9daa7086e2bffc9f41ef3c`；no-call rehearsal hash
  `a35bd451848b579b22ee1df7dd37f2a8d76cadbc6eafa34eca5fbfb2152ff161`。
- Safari沿用既有tab導向`http://127.0.0.1:7913/dashboard`，前後均30 tabs；真實目視先抓到錯寫
  `212 fixed steps`並改為固定summary順序＋210 predictions及data-dependent summary count後重驗。頁面read-only、
  無form／水平溢出；server已停止，tab可安全關閉。證據為兩張`analysis/m56_5_safari_*.jpeg`。
- authoritative state仍是V7 0/18＋0/18、V9／real rows 0/30、formal calls 0、outcome access 0、commitment／
  release／result absent。M56.5只證明普通程序中斷下不浪費已完成call且不暗中重呼；SHA是application-level
  drift control，不是抵抗同機攻擊者的digital signature，也不新增真人、actual model resource/performance、
  Equation V1、人類方程式、full-pipeline或production證據。下一個不可替代依賴仍是兩位不同真人完成V7。

### 7.80 2026-09-03 M56.6 single-writer formal generation：重複啟動已封閉，正式實驗仍禁止

- 不修改M54–M56.5任何凍結檔，新增M56.5之外的單一並行overlay。原M56.5的exclusive intent可阻止
  乾淨的雙重呼叫，卻不能阻止第二個本機程序把第一個健康run寫成terminal failure；M56.6先取得同一
  private run-id的nonblocking OS advisory exclusive lock，才進完全不變的M56.5 delegate。
- 公開入口只有`execute_single_writer_formal_generation(run_id)`。在建立lock前先重驗標準permitted run；
  lock固定在private telemetry，拒絕symlink、非regular file、wrong owner、multiple hard links、group/world
  permission與descriptor/path identity drift。沒有provider／prediction／outcome／readiness／retry注入。
- 兩執行緒真競爭為1個delegate、1個delegate前rejection、0額外transport、0 contender terminal failure；
  delegate exception保留原語意且釋放lock。獨立子程序在持鎖後`os._exit(19)`，作業系統釋放ownership，
  原lock file可重用。不同run-id互不阻擋；stale lock text不是authority。
- forged full M56.5 path仍恰好180 mock calls、outcome access 0、scoring release complete、failure absent。
  final focused **15/15**；M54–M56.6 direct **184/184**；選定M1/M2/V7/V9/M54–M56.6 **249/249**；
  compile、JSON、freeze hash與diff check通過。contract hash
  `5a3e1ea8a0923bd4ddc77816391c7c9e77ba46eae1b982ac2100dcacc8f7dd59`；live audit hash
  `cb0115a0355e99bb7f6764dbaeeec75b379da3fd8f06d3ffb12183a832512a80`；rehearsal hash
  `50c0191b4c64add022a1256f10c9c3b01b16edfac1ef18bd8d76ea71f900e512`。
- Safari沿用M56.5 tab導向`http://127.0.0.1:7914/dashboard`，前後均32 tabs，未新增／關閉tab；修改前
  競爭缺陷、single-writer lock、唯一owner／contender、process-death release、stale-file boundary與
  工程fixture均可讀，無form／水平溢出。server已停止，tab可安全關閉；兩張JPEG證據在`analysis/m56_6_*`。
- authoritative state不變：V7 0/18＋0/18、V9／real rows 0/30、formal calls 0、outcome access 0、
  commitment／release／result absent。M56.6只是同一台Mac上合作式duplicate-launch可靠度，不是distributed
  lock或malicious-host security，也不新增真人、actual performance、Equation V1、人類方程式、full-pipeline
  或production證據。下一個不可替代依賴仍是兩位不同真人完成V7。

### 7.81 2026-09-03 M56.7 Mac full-sync generation commit：檔名落盤邊界通過，正式實驗仍禁止

- M56.5只對JSON檔案本身`fsync`，M56.6只處理重複啟動；新檔名所在directory沒有同步。Mac突然斷電時，
  模型可能已成功回覆但checkpoint目錄項遺失，重開後只剩intent而使唯一授權terminal。M56.7只改此
  stable-storage completion boundary，不改prompt、資料、模型、順序、token、checkpoint內容、retry或score。
- 新入口`execute_full_sync_formal_generation(run_id)`先持有不變的M56.6 lock；沒有M56.7 mode卻已有M56.5
  狀態的run不能事後冒充。context-local dispatcher只在新入口內把M56.5所有JSON寫入改成payload完成→
  file `fsync`→file `F_FULLFSYNC`→directory `fsync`→directory `F_FULLFSYNC`，checkpoint barrier完成後才
  允許原M56.5清intent；前後另有immutable mode與durable release。舊入口不自動取得M56.7證據。
- 真實目前Mac上的file/directory `fsync`與`F_FULLFSYNC`四項probe通過；操作順序、unsupported barrier、
  舊狀態拒絕、checkpoint+intent中斷續接均通過。forged 30-row完整路徑仍為180 mock calls、211 step
  checkpoints、0殘留intent、400 durable artifact commits，M56.4 prescore相容且outcome access 0。
- 三次同形fixture：M56.6中位1.124688s，M56.7中位3.717044s，增加2.592356s／8192 allocated bytes／2 files；
  這是快速deterministic filesystem fixture，不是正式模型延遲或production throughput。
- 第一次focused為12/14：一個test在temp-root context前算路徑，於gitignored private root建立單一假mode；
  該精確假run已刪除並驗證不存在。另一test mock整個platform而先觸發upstream hardware drift；只改test
  fault scope後通過，沒有放寬正式gate。final focused 15/15；M54–M56.7 direct 199/199；選定
  M1/M2/V7/V9/M54–M56.7 264/264；compile、JSON、freeze hash與diff check通過。
- Safari重用既有M56.6 tab導向`http://127.0.0.1:7915/dashboard`，前後33 tabs，沒有新增／關閉；流程、
  三種restart state、成本與紅色證據邊界均可讀、無form／水平溢出。server已停止，tab可安全關閉；圖在
  `analysis/m56_7_safari_full_sync_flow_2026-09-03.jpeg`與`analysis/m56_7_safari_restart_boundary_2026-09-03.jpeg`。
- authoritative state仍是V7 0/18＋0/18、V9／real rows 0/30、formal calls 0、outcome access 0、formal
  commitment／release／result absent。沒有實際拔電，不能保證故障硬體；M56.7也尚未讓凍結的M56.4 scorer
  強制要求durable release，更沒有新增真人、actual performance、Equation V1、人類方程式、full-pipeline或
  production證據。下一個不可替代科學依賴仍是兩位不同真人完成V7。

### 7.82 2026-09-03 M56.8 durable-release-gated scoring：耐久生成與正式評分授權已串接，正式實驗仍禁止

- 只讀稽核證實凍結的M56.4完整隔離測試不建立任何M56.7 mode／durable release，仍可開test outcome並
  建立M56.4 result；因此舊scorer不能單獨證明預測經過後來新增的Mac full-sync generation邊界。
- 不修改M54–M56.7凍結檔，新增唯一目前授權入口
  `execute_durable_release_gated_formal_scoring(run_id)`；只接受run-id，先重驗不變的M56.4 prescore、exact
  M56.7 mode與durable release，再以file＋directory `fsync/F_FULLFSYNC`提交M56.8 gate，之後才delegate
  未改動的M56.4 outcome join／metrics／result。
- 缺少或竄改M56.7 mode／release均在outcome loader前拒絕；若沒有較早M56.8 gate卻已出現M56.4 access
  receipt、score report或result commitment，該run不能事後補證明。既有gate內容改變也fail closed；相同
  restart只能沿用同一gate與同一result。
- forged完整路徑實際先走M56.7 generation，再走M56.8：180 mock generation calls、0 scorer calls；測試
  在outcome loader被呼叫時已觀察到gate `artifact_commit_complete`。七組metrics、B5/Ours主比較與decision
  和原M56.4相同。
- 三次相同deterministic score fixture：M56.4中位0.597449s，M56.8中位0.747182s，增加0.149733s；三次
  score semantics全相同。這不是formal model latency或production throughput。
- final focused **10/10**；M54–M56.8 direct **209/209**；選定M1/M2/V7/V9/M54–M56.8 **274/274**；
  compile、JSON、freeze hash與diff check通過。contract hash
  `ee60d7c4179d347418d24467f7a3b0656cafab14f127cde4b8853f8280cd3316`。
- Safari重用既有M56.7 tab導向`http://127.0.0.1:7916/dashboard`，前後33 tabs，沒有新增／關閉；五步
  授權鏈、前後差異、不能事後補證明與same-host限制皆可讀、無form／水平溢出。server已停止，tab可安全
  關閉；證據為兩張`analysis/m56_8_safari_*.jpeg`。
- authoritative state不變：V7 0/18＋0/18、V9／real rows 0/30、formal calls/outcome/result皆0或不存在。
  M56.8是合作式application/research authority，不是OS sandbox；有同機程式／檔案權限者仍可直接呼叫
  歷史M56.4，該讀取不會被物理阻止，只是不具M56.8授權。沒有新增真人、actual performance、Equation V1、
  人類方程式、full-pipeline或production證據。下一個不可替代科學依賴仍是兩位不同真人完成V7。

### 7.83 2026-09-03 M56.9 single-writer formal scoring：重疊答案讀取已封閉，正式實驗仍禁止

- 只讀稽核與暫存30-row forged fixture證實：有效M56.8 gate/access receipt存在時，兩個同時M56.8呼叫
  會讓`load_outcome_inputs`執行2次；1個成功、另1個直到建立`formal_score_commitment.json`才因
  `FileExistsError`失敗。也就是失敗者已先開過答案，與single-logical-join語意不符。沒有讀正式資料。
- 不修改M54–M56.8任何凍結檔，新增
  `execute_single_writer_durable_release_gated_formal_scoring(run_id)`。它先只讀驗證標準M56.8 run，再於
  private telemetry取得同run的nonblocking OS advisory lock，持有期間delegate完全不變的M56.8；同時
  競爭者在M56.8與outcome前拒絕，不等待、不重試、不寫第二份score/result。
- lock拒絕symlink、非regular file、wrong owner、multiple hard links、group/world permission與fd/path
  identity drift。delegate exception及子程序`os._exit(19)`會釋放OS ownership；stale lock text不是
  authority，不同run互不阻擋。
- 完整並行fixture修改後為2 callers→1 M56.8 delegate→1 private outcome load＋1 pre-delegate rejection；
  唯一owner仍產生未改的七組M56.4 report/result，scorer model call 0。focused 15/15；M54–M56.9 direct
  224/224；選定M1/M2/V7/V9/M54–M56.9 289/289；compile、JSON、freeze hash與diff check通過。
- 三次deterministic score fixture：M56.8中位0.724372s，M56.9中位0.855941s，增加0.131569s，0新增模型
  呼叫。這不是正式model latency或production throughput。
- 保留且測得明確限制：兩個**依序**呼叫在lock釋放後仍會讓凍結M56.8重新讀答案2次；M56.9只處理
  overlapping concurrency，不是跨重啟exactly-once、distributed lock、OS sandbox或malicious-host安全。
- Safari重用M56.8 tab導向`http://127.0.0.1:7917/dashboard`，前後33 tabs，未新增／關閉；2→1圖、
  四步owner流程、依序重開限制及證據邊界可讀，無form／水平溢出。server已停止，tab可安全關閉；圖在
  `analysis/m56_9_safari_concurrency_flow_2026-09-03.jpeg`與
  `analysis/m56_9_safari_sequential_boundary_2026-09-03.jpeg`。
- authoritative state仍是V7 0/18＋0/18、V9／real rows 0/30、formal calls/outcome/result 0或不存在。
  沒有新增真人、actual performance、Equation V1、人類方程式、full-pipeline或production證據。下一個
  可獨立工程單元是crash-safe exactly-once scoring continuation；不可替代科學依賴仍是兩位不同真人V7。

### 7.84 2026-09-03 M56.10 crash-safe at-most-once outcome join：跨重啟重讀已封閉，模糊狀態刻意terminal

- 隔離30-row forged fixture先證實M56.9缺口：第一次在private outcome loader後、score report前中斷，
  留下access receipt但無report/result；第二次依序呼叫會再次打開答案並完成，總loader calls為2。沒有讀
  正式答案；證據在`analysis/m56_10_prechange_crash_window_reproduction_2026-09-03.json`。
- 檔案讀取與新checkpoint寫入無法形成單一原子交易，因此M56.10沒有假稱所有crash point都能exactly-once
  完成。凍結的可證明規則是：完整run總讀取1次；已有有效full-sync score checkpoint的重啟額外讀0次；
  完成後依序再呼叫額外讀0次；只有durable intent而沒有checkpoint時，歷史讀取是0或1不可判定，故永久
  terminal、不得重試或補造結果。這犧牲狹窄crash window的availability以保住at-most-once。
- 新公開入口`execute_crash_safe_outcome_join_formal_scoring(run_id)`只收run-id，外圍沿用M56.9同run lock，
  內部依序full-sync M56.10 mode→不變M56.8 gate→不變M56.4 prescore/access receipt→join intent→唯一outcome
  load→不變M56.4 score建構→private score checkpoint→不變canonical report/result commitment。M56.4七組
  metrics、threshold、B5-vs-Ours primary contrast與result內容未改。
- 完整fixture、checkpoint後中斷續跑、intent-only失敗、completed replay、同時contender、mutated/missing/
  retroactive state均有測試。修改後完整與checkpoint-restart總loader calls均為1；intent-only首次fixture
  讀1次後，後續呼叫0次且terminal；scorer model calls 0。focused 16/16；M54–M56.10 direct 240/240；
  選定M1/M2/M6/V7/V9/M54–M56.10為305/305；compile、JSON、freeze hash與diff check通過。
- 七組交錯paired fixture的M56.9／M56.10中位為0.855593／0.770818s，paired差-0.080518s；另一次初始
  3-run也為負。此短fixture不能推論M56.10更快，真正可歸因成本是full-sync JSON commits由1增為8（+7）。
  五次completed checkpoint replay中位0.278417s、0額外outcome load、0 model call。不是正式模型延遲。
- Safari重用M56.9 tab導向`http://127.0.0.1:7918/dashboard`，前後33 tabs，沒有新增／關閉；上半部2→1、
  下半部未開始／checkpoint／intent-only三條路徑、availability tradeoff與證據邊界皆可讀，無form／可見
  水平溢出。兩張PNG在`analysis/m56_10_safari_*.png`；server已停止，唯讀tab可安全關閉。
- authoritative state仍為V7 0/18＋0/18、V9／real rows 0/30、formal model calls／real outcome access／
  result皆0或不存在。舊M56.8/M56.9 API與直接檔案存取仍可由同機程式物理呼叫；M56.10是合作式sanctioned
  path，不是distributed transaction、OS sandbox或malicious-host security，也沒有實際拔電測試。沒有新增
  真人、actual performance、Equation V1、人類方程式、full-pipeline或production證據。
- 原先列為下一步的private scoring artifact containment未被跳過，而是順延成M56.12；M56.11先補一個
  更直接的證據缺口：M56.10只有普通Python exception，尚未讓程序真的消失並由新程序接手。

### 7.85 2026-09-03 M56.11 process-death scoring crash matrix：四個真程序中斷狀態通過

- 修改前缺口：M56.10例外測試可執行cleanup，不能代表程序突然死亡。隔離30-row forged probe先用
  `os._exit(71/72)`實證intent-only會0重讀terminal、checkpoint會0重讀完成，再凍結四phase合約；沒有
  正式答案、真人或模型呼叫。
- 單一變因只把failure injection從same-process exception提升為四個獨立child process abrupt death；
  M56.10 runtime、M56.9 lock、M56.8 authority及M56.4 scoring semantics全部不改。新無參數工程入口
  `run_process_death_crash_matrix()`只建立temp forged run，child-only monkeypatch呼叫`os._exit`，formal
  runtime沒有新增fault hook；輸出只有state/count/hash，沒有outcome label、source或raw model response。
- 四個凍結位置實測：lock後/state前exit70由新程序讀1次完成；outcome後/checkpoint前exit71總讀1次、
  新程序0重讀並terminal不完成；checkpoint後/report前exit72總讀1次、新程序0重讀完成；report後/result
  前exit73總讀1次、新程序0重讀且report hash不變完成。4/4 exit code符合、4 child皆reaped、retry/
  fallback/scorer model call為0、real private root/outcome access為0。
- focused 9/9；M54–M56.11 direct 249/249；選定M1/M2/M6/V7/V9/M54–M56.11為314/314；compile、JSON、
  contract/schema、dependency與freeze hash通過。matrix hash為
  `d7346f14b492144746f5db75f929a488fb2634aeda46285f4c7db95234f51c33`。
- 三次完整matrix為5.115022／5.129000／5.164917s，中位5.129000s；每次4 child launch、4個互相獨立
  forged outcome load、0 scorer call。這是validation harness cost，不是production scoring overhead。
- Safari重用M56.10 tab導向`http://127.0.0.1:7919/dashboard`，前後33 tabs、沒有新增／關閉；頁面直接
  驗證並載入封存matrix而非手寫結果，四phase、每條總讀1、exit71不完成、4 child回收及限制皆可讀，
  無form／可見水平溢出。兩張PNG在
  `analysis/m56_11_safari_process_death_*.png`；server已停止，唯讀tab可安全關閉。
- authoritative state仍是V7 0/18＋0/18、V9／real rows 0/30、formal call/outcome/result 0或不存在。
  這不是拔電、kernel/filesystem corruption、multi-host或malicious-host測試；不新增Equation V1、完整
  人類反應方程式、full-pipeline、runtime/production或真人證據，intent-only仍刻意犧牲availability。
- 下一個必要單一變因是M56.12 Outcome-Derived Artifact Containment and Public Projection Audit：證明private
  checkpoint/report/outcome-derived material不會流入public renderer、log或telemetry，只能呈現bounded
  aggregate state且不洩漏per-sample label、raw source或hidden outcome。不可替代科學依賴仍是兩位不同
  真人完成V7。

### 7.86 2026-09-03 M56.12 outcome-artifact public projection：run-specific安全出口已建立

- 修改前沒有發現production公開外洩，但也沒有run-specific安全投影；隔離forged 30-row run若naive序列化
  checkpoint＋report，初始default JSON為57,024 bytes，controlled canonical為52,458 bytes，包含60次
  sample ID、60個pair occurrences、14個condition-metric blocks、3次outcome-key hash與2個decision。這是
  artifact sensitivity／缺安全出口證據，不是歷史外洩證明。
- 單一變因只新增private outcome-derived artifact→public state-only allowlist；M56.10 checkpoint、report、
  metrics、decision與scoring semantics完全不改。四個sanctioned function都只收`run_id`，內部完整驗證
  private state，再讓dashboard/log/telemetry共用同一schema；呼叫者不能注入artifact、metric、decision、
  result或readiness。
- 七個phase全部驗證：未開始、mode、intent incomplete且答案是否開過未知、terminal ambiguous、checkpoint、
  report、result committed。公開面只含phase、六個existence bool、result artifact是否存在、retry/fallback 0、
  redaction policy與public projection hash；不含raw run id、private hash、sample/pair、label、metric或decision。
- controlled canonical 52,458→1,225 bytes（-97.66%）；sample ID 60→0、pair 60→0、metrics 14→0、
  outcome-key hash 3→0、decision 2→0、全surface private canary hits 0。projection/log/telemetry byte-identical；
  private或public artifact mutation皆fail closed。
- 聚焦9/9；M54–M56.12 direct 258/258；選定M1/M2/M6/V7/V9/M54–M56.12為323/323；compile、JSON、
  contract/dependency/freeze/rehearsal/audit hashes通過。0 formal model call、0 real outcome access。
- 七次forged completed-run：naive無驗證序列化中位0.000484s，完整validated projection中位0.143658s，
  三個獨立surface refresh中位0.433071s。這是containment validation overhead，不是production throughput。
- Safari重用M56.11 tab導向`http://127.0.0.1:7920/dashboard`，前後33 tabs、沒有新增／關閉；前後bytes、
  全敏感項歸零、3/3 surfaces、data membrane與限制可讀，無form／可見水平溢出。兩張PNG在
  `analysis/m56_12_safari_public_projection_*.png`；server已停止，唯讀tab可安全關閉。
- authoritative science仍V7 0/18＋0/18、V9／real rows 0/30、formal call/outcome/result 0或不存在。
  M56.12只保護遵守新API的合作式consumer；不能阻止same-host direct file/old API，也未證明每個未來consumer
  都遵守，更沒有Equation V1、完整人類反應方程式、full-pipeline或production證據。
- 下一個必要單一變因是M56.13 Unidirectional Public Snapshot Boundary：private exporter只把validated
  M56.12 projection耐久輸出到separate public compartment；dashboard/log/telemetry在private-root access
  明確禁用時仍能讀同一狀態。不可替代科學依賴仍是兩位不同真人完成V7。

### 7.87 2026-09-04 M56.13 unidirectional public snapshot：公開consumer已移除private讀取能力

- 修改前M56.12沒有發現輸出洩漏，但三個public consumer各自呼叫private-state loader；loader被禁用時
  dashboard/log/telemetry為0/3可用、共呼叫loader 3次，consumer module有4個private M56 imports。
- M56.13只改public consumer capability：private exporter以run-id完整驗證一次，產生random 128-bit
  snapshot id，使用Mac full-sync exclusive write把唯一allowlisted projection寫到separate public root；
  standalone reader只收snapshot-id，不import任何M56 Python module，也不依賴private-root env。
- 實際forged 30-row rehearsal在export後把private root chmod 000，再啟動projection/log/telemetry/HTML四個
  fresh child process：4/4 exit 0、stderr空、全部reaped；private validation 1、public M56 imports 0、private
  canary hits 0、projection/log/telemetry byte-identical。snapshot為1,954 bytes、0600、single-link、random id。
- malformed/traversal id、tampered hash/content、forbidden field、symlink、hard link、group/world permission及
  public root嵌入private run root均fail closed。第一次rehearsal用mock包裝public函式而改變signature，被
  M56.12 contract正確拒絕；未放寬contract，改為只監測內部private loader後通過。
- 七次forged rehearsal中位：validated export 0.145821s、四child 0.151264s、整體1.307229s，範圍
  1.300077–1.314878s；這是本機fixture成本，不是formal model latency或production throughput。
- focused 10/10；M54–M56.13 direct 268/268；選定M1/M2/M6/V7/V9/M54–M56.13為333/333；compile、JSON、
  freeze/dependency hash與diff check通過。0 formal model call、0 real target-outcome access。
- Safari重用M56.12 tab導向`http://127.0.0.1:7921/dashboard`，前後33 tabs、沒有新增／關閉；圖上可讀
  private exporter→immutable snapshot→public reader、修改前0/3、修改後4/4、1 validation、0 imports、
  0 canary及DENIED boundary，無form／可見水平溢出。兩張PNG在`analysis/m56_13_safari_*.png`；server已
  停止，唯讀tab可安全關閉。
- 同OS user的其他程式仍可能直接讀private files；hash不是writer signature；crash可能留下safe orphan，
  沒有latest/revocation lifecycle。這不新增真人、Equation V1、model performance、full-pipeline或production
  證據；authoritative science仍V7 0/18＋0/18、V9/real rows 0/30、formal calls/outcome/result 0或不存在。
- **M56.13是M56最後一點，不建立M56.14。** 下一個主里程碑為M57 outcome-blind component error
  localization：perception/retrieval/state/decision/realization的oracle substitution protocol與harness可先準備，
  但正式M57結論必須等待authorized M56 result，不得以synthetic fixture冒充。

### 7.88 2026-09-04 M57 outcome-blind component error localization：工程readiness完成，正式診斷仍禁止

- 修改前M56 forged report有7個condition metrics與30組B5/Ours paired records，但M57要求的10個
  localization keys為0/10、component interventions 0、provenance records 0；這只證明診斷表示缺口，
  不證明任何真實元件有錯。
- M57只新增component-substitution diagnostic，不改模型、樣本、結果、generation rules或formal authority。
  五個stage是perception、retrieval、observable-only state proxy、decision diagnostic ceiling、realization；
  private mental truth一律不作oracle。每個plan必須在outcome前commit，只換一個stage並記錄downstream
  recomputation；decision排除判因，缺human realization ratings時保持unavailable。
- frozen rule以Brier/NLL/Top-1及20,000 paired bootstrap（seed 570904）判recoverable effect；兩個proper
  score的95% CI lower都必須>0且Top-1不退步。leading stage還要Brier/NLL同一唯一leader且至少領先0.05；
  tie、mixed metrics與interaction必須abstain，永不宣稱unique biological/psychological cause。
- 兩個作者構造30-row mechanical fixture通過：clear case中retrieval Brier recovery 1.108、perception 0.402、
  state 0，得到leading=retrieval；tie case中perception/retrieval各1.108，得到leading=null與
  ambiguous_interacting_or_unresolved。兩者都是0 model call、0 real outcome access、0 formal result，
  不是Uruha診斷或Equation V1證據。
- mutation涵蓋missing sample、probability sum、changed-component drift、plan drift、future leak、retry、
  outcome-before-commit與caller-minted formal authority並全部fail closed。focused 13/13；final selected
  M1/M2/M6/V7/V9/M54–M57為349/349（其中direct M54–M57為281/281）；compile、JSON、dependency/freeze
  hashes與diff check通過。
- 七次clear＋tie fixture pair中位1.602724s，範圍1.593786–1.612762s；這是本機synthetic analyzer成本，
  不是formal model latency或production throughput。
- Safari第一次顯示發現五stage長字串溢出section；未放寬研究規則，改成可縮放換行卡、中文名稱與Brier
  recovery bars後重驗通過。沿用既有tab，前後33 tabs、沒有新增／關閉；aggregate→component、clear
  retrieval、tie abstention、FORMAL DENIED與V7 0/18＋0/18皆可讀。server已停止，唯讀tab可安全關閉。
- M57 **工程readiness完成，但正式M57科學結果未完成**。authoritative science仍V7 0/18＋0/18、V9與
  real temporal rows 0/30、formal M56 result 0。下一個不可替代步驟是兩位不同真人完成V7，再完成V9、
  boundary/adjudication、M55 real rows與authorized M56；只有之後才能執行已凍結M57。沒有formal M57
  結果不得建立結果導向M58或捏造一個leading stage。目前也刻意沒有formal artifact bridge；pure analyzer
  即使收到caller自填`formal_authorization=true`也拒絕real bundle，未來bridge必須從validated M56 artifacts
  導出authority與resource hashes，不能信任caller boolean。

### 7.89 2026-09-04 M57.1 pre-outcome diagnostic commitment：答案前封存順序已補齊，正式M57仍禁止

- 修改前正式入口雖安全拒絕，但M57 durable artifacts為0、pre-outcome commit/validate API都不存在；未來若
  M56結果出現才建立stage plan，無法證明outcome-blind。保留probe為0 real outcome access、0 formal result。
- 單一變因只新增M57診斷模式在M56 outcome state前的full-sync commitment；M57五stage、統計規則、M56
  prediction/scoring、模型、資料、資源與0 retry全部不改。公開commit/validate API都只收`run_id`，沒有plan、
  resource、outcome、readiness或authorization注入。
- first commit與M56.10共用同run nonblocking scoring lock；先重驗M56.7 durable release與M56.8 prescore，並要求
  M56.8 gate、M56.10 mode/intent/checkpoint/failure、M56.4 access/report/result共8個outcome-state artifact全無。
  commitment綁5個stage plan與17個M56 data/runtime/hardware/model/Equation/schedule/submission/prediction/
  ledger/release/expected-outcome hashes；事後第一次補做拒絕，既有完全相同commitment可在result後重驗。
- temporary forged 30-row完整順序為commit→不變M56.10一次fixture outcome load→M56 result link重驗→相同hash
  replay；M57.1 model calls 0、real target outcome reads 0、formal M57 result 0、M58 authority false。partial或
  mismatched result、commit/upstream mutation、path escape、dependency drift與lock race均fail closed。
- focused M57+M57.1 **26/26**；selected M1/M2/M6/V7/V9/M54–M57.1 **385/385**（111.37s）；compile、JSON、
  freeze hash與diff check通過。首次用system Python跑unittest為281 tests＋7個pytest import errors，保留為環境
  invocation failure，後用既有pytest重跑綠燈，沒有安裝或放寬依賴。
- 七次forged fixture first commit中位0.287402s（0.283163–0.315814），post-result validation中位0.146691s
  （0.144262–0.148582）；commitment固定6,102 bytes，7/7完整M56.10 result-chain links valid。不是formal
  latency/throughput。review時發現只驗M56.4 report/result不足，已補M56.8 gate＋M56.10 mode/intent/checkpoint
  完整鏈；legacy M56.4 direct result現在明確不算valid link。
- Safari在`http://127.0.0.1:7923/dashboard`顯示三步時間順序、修改前0 commitment、5 stages/17 bindings、
  FORMAL DENIED、V7 0/18＋0/18、real rows 0/30與M58 denied；無可見overflow，server已停止。display-name
  targeting先意外走過本機test-tab history，改用`com.apple.Safari`才成功；tab 33→34、未關閉任何tab，新增
  M57.1唯讀測試tab可安全關閉。
- M57.1只建立cooperative same-Mac順序與artifact binding，不是digital signature，也沒有建立具體兩位coder
  evidence manifest或30-row component predictions。因此下一個answer-free必要單元是M57.2 component-substitution
  prediction capsule：在答案前綁具體provenance並封存available stage outputs；不得合成真人證據或啟動M58。
  正式科學依賴仍是V7兩位真人、V9 review、30 real rows及authorized M56。

### 7.90 2026-09-04 M57.2 component prediction capsule：具體逐題替換預測已能在答案前封存

- 修改前M57.1有5個generic stage plans，但concrete evidence-manifest、component schedule與30-row
  prediction capsule bindings都是0；只能證明「想過怎麼查」，不能證明逐題替換內容與輸出在答案前存在。
- 單一變因只新增source-bound pre-outcome component evidence與predictions；M56的30 samples、原始Ours
  distributions、模型／硬體／decoding／token budget／scoring／0 retry及M57統計全部不改。公開execute／
  validate API都只收`run_id`，不收evidence、provider、outcome、readiness、authorization或resource注入。
- 每個sample固定五stage evidence：perception／retrieval各要求兩位不同coder＋不同adjudicator；retrieval
  只能選cutoff前history ID；state只能含六個observable/derived proxy variable，三個private state禁止；
  decision在outcome前固定unavailable；realization缺獨立盲式人評固定unavailable。每個contribution、
  adjudication、row及manifest皆content-addressed。
- 同M56 scoring lock內先重驗M57.1與M56 durable chain、確認8個outcome-state artifacts全無，然後先
  full-sync 150-step schedule，再以同Ours model/options/budgets對30×3 available stages做downstream
  recomputation；逐call要求actual tokens、latency、CPU、process/Ollama memory、durations與model identity，
  最後full-sync ledger、capsule與commitment。capsule保留原Ours distribution但沒有observed label。
- 暫存author-constructed 30-row evidence＋mock provider完成90/90 predictions，0 real model call、0 target
  outcome access；同份forged evidence送公開formal入口會在schedule與call前拒絕。decision／realization都
  沒有被補造。五個artifact合計826,603 bytes。
- fail-closed涵蓋path/missing M57.1、dependency/source/hash/order drift、post-cutoff history、同coder、重複
  contribution、coder兼adjudicator、private-state fabrication、forbidden outcome key、decision提前可用、
  model identity、token budget、probability mass、transport failure、same-run retry、shared-lock outcome race、
  prompt/resource/ledger/capsule mutation。
- review發現公開validator會把forged capsule回報structurally valid，雖executor仍拒絕但未來bridge可能只看
  `valid`誤用；現已改成public validator對forged必為invalid，只有明名internal validator可驗engineering
  fixture。安全修改後舊freeze hash test如預期先fail，更新freeze後重驗通過。
- focused M57.2 **17/17**；adjacent M54–M57.2 **312 tests collected**且包含於下列綠燈；selected
  M1/M2/M6/V7/V9/M54–M57.2 **403/403**（126.29s）；compile、JSON、freeze hash與diff check通過。
  七次fixture中位0.374307s（0.371192–0.401570），只是Python/hash/full-sync/mock plumbing成本；formal最多
  90次local model calls，尚無真實token／latency／energy measurement。
- Safari在`http://127.0.0.1:7924/dashboard`顯示四步答案前資料流、五stage可用性、5 generic plans→90
  engineering predictions、成本與FORMAL DENIED boundary；V7 0/18＋0/18、real rows 0/30、M58 denied皆
  可讀，無form或可見overflow。34→34 tabs、沒有新增／關閉；server已停止，唯讀M57.2 tab可安全關閉。
  初次快捷鍵拼法、缺paste format與scroll element index被Computer Use API拒絕，修正呼叫後通過，沒有
  隱藏成系統失敗。
- M57.2只證明cooperative pre-outcome concrete-prediction mechanics；distinct IDs/hash不是三位真人的
  cryptographic identity proof，未來formal collection仍須綁獨立稽核的人類ledger。這不是independent-human evidence、
  Uruha真實錯誤定位、Equation V1、LLM優勢或人類反應方程式證據。下一個必要單元是M57.3 sanctioned
  outcome-to-analyzer bridge：可先以forged full chain驗證mechanics，但formal execution必須同時要求既有
  M57.1、完整M57.2、valid M56.10 result，不能接受caller labels；沒有formal M57 result仍不得啟動M58。

### 7.91 2026-09-04 M57.3 sanctioned outcome-to-analyzer bridge：答案只能由受控結果鏈接回凍結分析器

- 修改前M57.2有30 rows與90個答案前perception／retrieval／state predictions，但observed labels與
  decision ceilings皆為0；capsule schema不能直接進入凍結M57 analyzer。用保留的forged M56 aggregate
  paired deltas反推label時30/30皆ambiguous，因此不能由總分猜答案，也不能讓caller傳入label或bundle。
- 單一變因只新增從完整M57.2 capsule與M56.10 result chain到未改M57 analyzer的sanctioned bridge；M56
  predictions／score／model／samples／resources／thresholds與M57統計全部不改。公開execute／validate API
  只收`run_id`，author-constructed evidence會在建立M57.3 mode、intent或讀答案前被拒絕。
- bridge先重驗exact M57.1 mode、完整M57.2 evidence／schedule／capsule／ledger／commitment與完整M56.8／
  M56.10 gate／intent／checkpoint／report／result chain。之後在同一per-run scoring lock下依序full-sync
  mode、no-retry intent、一次獨立命名的M57 diagnostic private-outcome load、private joined checkpoint、
  aggregate-only result與SHA-bound commitment。intent存在但checkpoint缺失時刻意terminal，不能猜測重讀。
- 一次完整研究run因此有兩個不同用途的答案讀取：M56 score **1**、M57 diagnostic **1**；有效checkpoint
  replay額外讀取**0**。joined checkpoint加入30 observed labels與30 post-outcome decision one-hot ceilings，
  保留原90 pre-outcome predictions不變；realization缺獨立盲式人評仍unavailable。aggregate result不輸出逐題label。
- 機械projection產生120 available stage rows後交給未改`analyze_component_substitution_bundle`；projection本身
  沒有formal authority。M57.3只有完整real upstream chain才可能formal；M58還額外要求唯一且eligible的
  `leading_recoverable_stage`，不能因bridge有效或結果ambiguous就啟動。
- 暫存author-constructed full chain完成M57.1→M57.2→M56.10→M57.3：30 labels、90 preserved
  predictions、30 decision ceilings、120 available stage rows、0 realization ratings；M56/M57 fixture loads各1，
  replay額外0；0 real model call、0 real target-outcome access、formal result false、M58 false。刻意無資訊的
  mock distribution沒有eligible recoverable effect，只是mechanics結果，不解讀為Uruha認知元件發現。
- focused M57.3 **14/14**；adjacent M56.10＋M57–M57.3 **74/74**（94.30s）；selected
  M1/M2/M6/V7/V9/M54–M57.3 **398/398**（185.00s）。compile、JSON、saved rehearsal、freeze hash與
  Git whitespace checks通過。初次測試因系統Python 3.14沒有pytest而未collect；切回既有Python 3.12後，
  兩個focused失敗均確認為無效mutation fixture與過晚error-message expectation，未放寬任何實作規則。
- 七次fixture中join＋20,000-bootstrap analyzer中位**2.100255s**（2.081292–2.125582），整個fixture wall
  中位**6.343483s**，五個M57.3 durable artifacts **214,530 bytes**。這只量Python validation／hash／
  full-sync／numeric bootstrap，不是未來90個真模型calls、人工標註、energy或production throughput。
- Safari沿用既有tab在`http://127.0.0.1:7925/dashboard`顯示六步flow、1＋1答案用途、replay 0、
  30/90/30/120/0 counts、private checkpoint與aggregate-only boundary；FORMAL M57 DENIED、V7 0/18＋0/18、
  real rows 0/30、formal result 0、M58 denied皆可讀。34→34 tabs，沒有新增／關閉；server已停止，唯讀
  M57.3 tab可安全關閉。Computer Use第一次取得Safari狀態遇到舊binding/API物件問題，改用模組實際匯出後通過，
  沒有隱藏成產品錯誤。
- M57.3只封閉「答案如何合法進分析器」的可反駁性缺口；hash是同使用者合作式integrity control，不是抵抗
  惡意程序的signature。它仍沒有兩位真人component evidence、真Uruha localization、Equation V1有效性、
  UruhaBrain優勢或完整人類反應方程式證據。下一個必要單元是M57.4 independently attributable
  component-evidence collection/quarantine：綁distinct coders／adjudicator、source viewing、timestamp、
  disagreement、adjudication與pre-outcome export；可以synthetic rehearsal驗工程，但不得冒充真人或解鎖formal。

### 7.92 2026-09-04 M57.4 independently attributable component-evidence collection：可稽核收集路徑完成，真人證據仍為0

- 修改前M57.2只有完成物schema與直接fixture constructor，沒有讓兩位coder與不同adjudicator實際看來源、
  各自保存、封存、保留分歧並在答案前export的操作路徑。V7的18-slot persona coder回答不同問題，不能代替
  30-row component evidence。
- 單一變因只新增三角色pre-outcome collection/quarantine；M56 samples/predictions/model/outcome/score/resource、
  M57 stages/statistics、M57.2 manifest semantics與M57.3 bridge皆未改。public API為initialize、source view、
  entry save、ledger seal與manifest export；synthetic initializer明名internal且永遠不能formal。
- 每一action重驗M57.1與outcome absent。兩位coder只看permitted source與自己的private ledger，先有server
  timestamped source-view receipt才可save；revision append-only，30/30才可seal。兩份coder seal都valid後
  adjudicator才看到雙方contribution；perception/retrieval disagreement由系統計算，另建立source-bound
  observable state proxy。30筆adjudication及第三seal後才能輸出exact M57.2 manifest。
- complete synthetic rehearsal完成3 roles、90 source views、60 coder entries、30 adjudicator entries、60＋60
  perception/retrieval contributions、30 state proxies、60 adjudications與3 seals；保留6個perception、8個retrieval
  disagreements。internal engineering validator接受，public formal validator拒絕；0 real model call、0 real
  outcome access、M57.2 prediction未啟動、M58 false。
- 初次rehearsal因兩個synthetic coder的說明文字每題不同而誤報30/30分歧；這是fixture錯誤，freeze前修成只
  保留刻意semantic差異6/8。Safari填表時AX index更新造成欄位第一次錯置，未送出；重讀後逐欄修正，只送出
  一次。另一次shell查錯ledger欄位而先看到0，實際`entries`/`source_views`確認1 revision／2 views／0 answer／0 model。
- focused M57.4 **11/11**（70.81s）；adjacent M56.10＋M57–M57.4 **85/85**（165.40s）；selected
  M1/M2/M6/V7/V9/M54–M57.4 **409/409**（252.66s）。compile、JSON、screenshot format/hash、freeze hash、
  stopped services與Git whitespace checks通過。
- 七次full synthetic collection中位**54.224564s**（54.176508–54.772366），每run九個durable artifacts
  **685,646 bytes**。這只量Python validation/token checks/hash/atomic full-sync，不是human labor、model latency、
  energy、formal throughput或production security。
- Safari dashboard顯示兩個private coder→dual seal→adjudicator→M57.2 manifest與60/30/90/6/8/0 counts，
  FORMAL M57 DENIED、V7 0/18＋0/18、real rows 0/30、M58 denied皆可讀；functional synthetic collector實際
  保存一筆正確coder revision並跳下一題。35→35 tabs、未新增／關閉；M57.4 test tab可安全關閉，servers已停止。
- M57.4只讓未來component evidence在application-level可歸因、可重播、可拒絕答案後寫入；pseudonym、token與
  self-attestation不是三位physical humans的cryptographic proof，也沒有產生真人label、private mental truth、
  正式localization、Equation V1、LLM優勢或human equation證據。live real component rows仍0/30。
- 下一個必要單元M57.5只做separate participant-capability issuance與token-surface hardening：不能修改M57.4
  frozen evidence semantics；要避免coordinator API把三個bearer tokens回傳給同一caller，避免token出現在argv／
  URL／browser history，以分開one-time permission-restricted envelopes與secure local cookie session驗證role
  capability不能互相導出／消耗。仍不能取代external identity oversight，也不得讀outcome、建立formal result或啟動M58。

### 7.93 2026-09-05 M57.5 separate participant capabilities：角色token已移出caller／argv／URL／HTML／cookie

- 修改前M57.4 mode只存token hash，但initializer會把三個raw role tokens一次回傳同一caller；direct collector
  另把token放進`--token`、query string、hidden form與redirect URL。這不否定M57.4 mechanics，但不適合交給
  三個不同study roles。
- 單一變因只新增M57.5 wrapper；M57.4 frozen source/view/ledger/seal/adjudication/manifest semantics完全不改。
  wrapper先full-sync no-retry intent，再呼叫原initializer，將三個capabilities分別寫入0700 role dirs／0600
  envelopes；central commitment與public receipt只有pseudonym/token hash/envelope hash/path，raw token 0。
- collector CLI只收run/role/envelope path/port。claim重驗outcome absent、role/path/hash，寫exclusive receipt，
  scrub envelope後只在server process memory保留M57.4 token；second claim與claim後restart刻意fail closed。
  browser改用獨立host-only `HttpOnly; SameSite=Strict` cookie與CSRF；role token不進URL、HTML/form或cookie。
  loopback plain HTTP未假稱TLS或`Secure` cookie flag。
- synthetic rehearsal完成3 envelopes、1 claim、303 cookie handshake與1個原M57.4 coder POST；public receipt與
  測試的URL／redirect／HTML／cookie／CSRF中raw role token occurrences皆0，ledger 1 revision／1 source view，
  target outcome/model calls 0，formal false，M58 false。沒有用假真人呼叫public real initializer。
- 第一次rehearsal因macOS `/var`→`/private/var` canonical path差異在artifact accounting失敗，沒有保存；兩側
  resolve後重跑通過。review另發現rehearsal duplicate了一份claimed server，freeze前刪除，saved result與tests
  改走同一production server constructor，沒有放寬規則。
- focused M57.5 **11/11**（20.71s）；adjacent M56.10＋M57–M57.5 **96/96**（188.60s）；selected
  M1/M2/M6/V7/V9/M54–M57.5 **420/420**（273.55s）。compile、JSON、frozen dependencies、saved rehearsal、
  JPEG hash/dimensions、servers stopped、freeze hash與Git whitespace checks通過。
- 七次issuance→claim→cookie→POST中位**4.601486s**（4.586087–4.638623），六個M57.5 durable artifacts
  **5,587 bytes**/run。這不是人工完成90 entries、model/outcome/energy/TLS/production成本。
- Safari圖頁與functional synthetic collector皆通過：token-free URL顯示sample ID，正確表單送出後跳第2題；
  disk確認1 revision／2 source views、spent envelope與claim都無raw token、outcome/model 0。35→35 tabs，未新增／
  關閉；servers已停止，M57.5 test tab可安全關閉。第一次state capture在303途中混合舊dashboard tree，重讀後
  才以實際collector頁驗收，未冒充第一次畫面成功。
- M57.5只提升真人收集的operability/provenance。0700/0600與separate paths在同一macOS user下不是adversarial
  identity proof；claim後server若crash目前無法restart，因raw token已scrub。live V7仍0/18＋0/18、real temporal
  rows 0/30、real component rows 0/30、formal M56/M57 0、M58 denied。
- 下一個必要單元M57.6是crash-recoverable participant-owned active capability。先證明post-claim restart fail，
  只讀確認可用authenticated-encryption primitive，再prospective freeze；participant recovery secret只能從
  interactive non-argv channel進入、不落盤，active capability只能加密保存，restart需同一secret，browser仍0 token。
  若無合適audited primitive就保留terminal failure，不能自創crypto或降回plaintext；仍不得代替human identity
  oversight、讀outcome或啟動M58。

### 7.94 2026-09-05 M57.6 crash-recoverable participant capability：claim後新process可用同一secret恢復

- 修改前已用隔離實測重現：M57.5第一次collector start成功，但claim與envelope scrub後第二次start以
  `M57.5 role capability was already claimed; restart is unsupported`終止，post-claim restart成功數為**0**。
  一次普通process crash因此可能中斷尚未完成的30-row真人收集，雖然既有ledger本身仍有效。
- 單一變因只新增participant-secret-bound encrypted recovery；M57.4 evidence semantics與M57.5 issuance、claim、
  token-surface、browser-session契約未改。public CLI仍只收run/role/envelope path/port；first activation從真TTY
  隱藏輸入同一secret兩次，restart輸入一次，secret不接受argv、environment或browser channel。
- 既有Codex desktop Python 3.12.14提供精確`cryptography==50.0.1`；普通project Python 3.12.10與default Python
  不提供authenticated encryption。因此未安裝package或自創crypto，只凍結既有backend；backend缺失或漂移
  會terminal refuse，這不構成一般portable runtime claim。
- M57.6先full-sync random Scrypt/AES-GCM參數與0600 encrypted vault，再執行原M57.5 claim/scrub。Scrypt使用
  `N=32768,r=8,p=1`導出AES-256-GCM key；AAD綁run、role、pseudonym、M57.5 commitment/contract、token hash、
  initial envelope hash與crypto參數。activation另綁vault與claim；wrong secret、ciphertext tamper、role/path mismatch、
  crypto drift與outcome race都fail closed且不洩漏哪一項驗證失敗。
- 三個interruption state都已回歸：vault已落盤但claim前、claim與spent envelope已落盤但activation前、claim receipt
  已落盤但envelope scrub前。只允許exact hash-committed spent record復原；不重發或弱化capability。
- 修改後clean new process以同一secret恢復成功數為**1**，vault SHA與activation hash不變；restart collector完成
  1筆exact M57.4 coder revision並前進下一題。durable/browser surfaces raw token **0**、raw secret **0**，outcome/model/
  real participant/formal evidence/M58 authority全為**0**。
- focused M57.6 **14/14**（44.621s）；adjacent M56.10＋M57–M57.6 **110/110**（225.008s）；selected
  M1/M2/M6/V7/V9/M54–M57.6 **434/434**（300.78s）。compile、JSON、freeze hashes、saved rehearsal、JPEG hashes/
  dimensions、server stopped與Git whitespace皆通過；未安裝dependency。
- 七次encrypt→claim→restart→decrypt→cookie/CSRF→POST皆通過，中位**7.119880s**（7.035195–7.267910）；
  三個M57.6 durable artifacts **3,649 bytes**，連同M57.5 claim/spent envelope共五個受影響artifacts **4,956 bytes**。
  此成本不含真人90 entries、model/outcome、energy、TLS或production throughput。
- Safari實際啟動first process（2 hidden prompts）、停止、再以相同command啟動new process（1 hidden prompt），
  成功送出1筆synthetic coder form；圖頁顯示`TTY secret → Scrypt → AES-GCM vault → M57.5 claim → process restart
  → M57.4 ledger`、0→1、formal denied。AX index第一次把欄位填反而未submit，fresh screenshot修正後只submit一次。
  Safari tab count 33→35，沒有明確new-tab action且原因未證明，沒有關閉任何tab；servers已停止，test tab可安全關閉。
- M57.6只改善未來真人收集的crash operability/provenance，不證明secret entropy、Python memory zeroization、同帳號
  adversarial security、TLS、三位真人身份、predictive validity或Equation V1。M57.5 handler因沒有claimed-token constructor，
  M57.6暫時鏡像其HTTP handler，存在parity maintenance risk。live V7仍0/18＋0/18、real temporal/component rows
  仍0/30、formal M56/M57 0，M58 denied。
- 下一個必要單元M57.7只處理auditable participant runtime launcher：先證明普通project runtime無法承載凍結crypto、
  目前依賴hidden Codex runtime；再prospective freeze一個project-owned locked runtime launcher，在接收secret前驗證
  exact interpreter與crypto artifact，collection時不得download/install，secret/token仍不得進argv/log/browser。fresh launch與
  restart必須使用相同attested runtime、runtime drift fail closed、M57.4–M57.6 hashes與formal denial不變。若無法在不做
  broad packaging的前提下重現，保留Codex-runtime limitation，不假稱portable。

### 7.95 2026-09-05 M57.7 auditable participant runtime launcher：不再依賴hidden Codex interpreter

- 修改前repo沒有dependency lock、Python-version檔、participant launcher或project-owned runtime；default Python
  3.14.2與普通project Python 3.12.10都沒有`cryptography`，只有非project-owned Codex Python 3.12.14含
  `cryptography==50.0.1`。project-owned ready runtime為**0**，repository使用者無法獨立啟動M57.6。
- 單一變因只新增`project_owned_attested_participant_runtime_launcher`，M57.4 evidence、M57.5 capability/session、
  M57.6 Scrypt/AES-GCM、角色、source visibility、ledger、prediction、outcome、scoring與formal authorization皆未改。
- `prepare`和collection完全分離：prepare不收run/role/token/secret，可在收集前下載並以`--require-hashes`安裝
  cryptography 50.0.1、cffi 2.1.1、pycparser 3.0三個精確wheel到staging runtime；child audit通過後才atomic publish，
  existing/partial runtime不會自動repair或overwrite。runtime目錄0700、attestation 0600。
- attestation綁M57.7 contract/requirements、base/runtime Python、macOS arm64 platform、三個packages、兩個critical
  compiled binaries、M57.6 frozen files與smoke test。read-only audit遇missing、path escape、symlink、attestation/
  interpreter/package/binary/upstream drift都fail closed。
- `launch`只收run、role、M57.5 envelope path與port；完整audit成功後才以project runtime執行unchanged M57.6
  `--serve-recoverable`，再由M57.6真TTY收hidden secret。argv secret/token **0**，collection-time download/install/
  repair **0**，Codex interpreter dependency在collection為**false**，project-owned ready runtime改為**1**。
- focused M57.7 **18/18**；adjacent M56.10＋M57–M57.7 **128/128**（225.69s）；selected
  M1/M2/M6/V7/V9/M54–M57.7 **452/452**（309.38s）。第一次selected command用了兩個已不存在的M56檔名，
  collection前exit 4、0 tests；修正為repo實際檔名後通過，錯誤被保留而未隱藏。
- explicit project-runtime prepare為**3.349842s**；三wheel **4,243,044 bytes**；runtime **26,073,907 bytes**；
  七次audit中位**0.291446s**（0.290234–0.293445），collection install calls **0**。成本不含真人、model/outcome、
  energy、offline mirror、cross-platform、sign/notarize、TLS或production throughput。
- Safari沿用同一existing test tab，36→36、open 0、close 0。default Python呼叫launcher，project-runtime audit在
  hidden prompt前通過；first process停止後以同一public command與secret啟動clean second process，reload後送出1筆
  isolated synthetic coder form，exact M57.4 revision由sample 01前進02。dashboard顯示
  `PREPARE → HASH LOCK → ATTEST → AUDIT → HIDDEN PROMPT → COLLECT`、install 0、real 0/30、formal denied；
  services已停止，tab可安全關閉但未關。
- 開發失敗均保留：`-I`隱藏repo module；過窄PATH漏Homebrew Ollama與`/usr/sbin`；移除HOME令Ollama panic；
  Safari AX indices shift與一次stale Start Page；最後改為`-E -s`、固定工具PATH並保留既有HOME，只submit一次且disk
  exact。這些是implementation findings，不是正式資料。
- M57.7只證明tested macOS 15 arm64 host上的exact-hash local runtime可在不依賴Codex interpreter下承載M57.6。
  不證明offline/cross-platform、wheel provenance或supply-chain audit、code signing、same-account adversarial security、
  TLS、真人身份、label validity、Equation V1、LLM advantage、human-response equation或production。live V7仍
  0/18＋0/18、real temporal/component 0/30、model/outcome/formal M56/M57 0，M58 false。
- 下一個必要單元M57.8只處理participant-confirmed ledger completion/seal。M57.4已有完整ledger seal primitive，
  但M57.5/M57.6 browser只有`POST /save`與「保存這一題」，30/30後participant無token-free UI確認並seal自己的
  ledger。下一步先prospective freeze一個CSRF-protected explicit confirmation；只有30 unique/30且outcome absent才
  呼叫unchanged M57.4 seal，incomplete、mutated、wrong-role與nonidentical replay fail closed，不得順便改evidence語義。

### 7.96 2026-09-06 M57.8 participant-confirmed ledger completion：30/30後由本人明確封存

- 修改前M57.4已有exact complete-ledger seal，但M57.5/M57.6 browser只有`POST /save`；participant完成30/30後
  看不到完整度摘要與exact draft hash，也不能在不交回raw token的情況下自行seal。token-free participant seal
  path由**0→1**。
- 單一變因只新增`participant_confirmed_token_free_complete_ledger_seal`；M57.4 evidence fields/validation/seal schema、
  M57.5 capability/session、M57.6 recovery/crypto、M57.7 runtime、prediction/outcome/scoring/formal authority皆未改。
- 頁面顯示unique完成數、missing、source views、revisions與exact draft ledger hash；29/30沒有seal form，保存第30筆
  後仍保持open且automatic seal **0**。只有另一個CSRF-protected checkbox＋confirm POST能開始封存。
- seal在既有single-writer lock內重驗outcome absent、run/role/token、30份entry/source view、revision與displayed hash；
  先full-sync寫0600 intent，再產生unchanged M57.4 sealed ledger/seal，最後寫0600 M57.8 receipt。identical interrupted/
  completed replay只重驗或補完相同artifact；incomplete、stale、tampered、wrong-role、outcome-present與nonidentical
  replay fail closed。封存後browser read-only且save/confirm forms均消失。
- focused M57.8 **11/11**（217.24s）；adjacent M56.10＋M57–M57.8 **139/139**（454.05s）；selected
  M1/M2/M6/V7/V9/M54–M57.8 **463/463**（543.64s）。後兩套並行執行，時間只作run evidence，不是效能比較。
  compile、JSON、contract/rehearsal、freeze hashes與JPEG hash/format均通過。
- Safari用project launcher完成isolated synthetic 30/30→explicit confirm→seal。顯示draft
  `bbc8b0e8...9d8df9`、M57.4 seal `30454411...8f346e`、M57.8 receipt `2d52fab7...eb2798`；final acceptance
  38→38、0 open/close，services stopped。dashboard圖示
  `SAVE → 30/30 → HASH PREVIEW → CONFIRM → INTENT → SEAL`、automatic 0、receipt 0→1、token/secret 0、real 0/30。
- 失敗保留：completion panel原本在form下方、title殘留M57.5、一次stale Safari AX index建立Open Codex tab但modal已
  cancel且未關tab、dashboard曾在confirm後量seal count而fail closed；全部修正後重新驗收。整個debug session 37→38，
  不是final acceptance新增tab。剩餘test tab可安全關閉但沒有關。
- 三次synthetic completion transaction為0.293659–0.306211s，中位**0.295989s**；fixture setup＋30 entries
  18.724178–18.861495s；intent＋receipt每次1,800 bytes。這不是human time或production throughput。
- 維護限制：M57.8為了在already-held non-reentrant lock內保持stale-hash atomicity，重建exact frozen M57.4 seal schema，
  沒有呼叫public M57.4 seal function；當前由hash/contract/parity tests綁定，未來M57.4 schema變動需顯式同步。
- authoritative science完全不變：V7 0/18＋0/18、real temporal/component 0/30、real completion receipt 0、
  model/outcome/formal M56/M57皆0，M58 false。M57.8只證明synthetic participant completion mechanics，不證明
  真人身份、label validity、predictive value、Equation V1、LLM advantage、human-response equation或production。
- 下一個必要單元M57.9只處理`adjudicator_confirmed_token_free_preoutcome_manifest_export`。adjudicator現在可在browser
  seal 30/30，但exact M57.2 manifest export仍只能用internal M57.4 API＋raw capability。先做prechange gap與prospective
  freeze，再增加post-seal separate CSRF confirmation、durable intent/receipt、unchanged export與outcome-absence revalidation；
  不得藉synthetic export建立formal evidence或啟動M58。

### 7.97 2026-09-07 產品開發路線與 P1；M57.9 保留 partial

最新排程是 `DEVELOPMENT_WORKFLOW.md`、當前動作是 `CURRENT_TASK.md`，不得繼續舊的下一步而無限新增小數 M。
P1 修復 turn counter 重啟造成相同 prediction ID 覆寫舊回饋：7/7 focused、39/39 adjacent；隔離 mock／本機
runtime 各 2 sessions／6 輪，8 項 identity／保存／graph assertions 全過。入口 `uruha_web_ui_product.py`。
見 `analysis/p1_prediction_identity_acceptance_2026-09-07.md`；歷史 frozen 模組未改。

P1 本機兩次 qwen2.5:7b general-planner 呼叫均逾時，0 completed fresh generation；確認／致謝的兩輪仍多餘追問。
因此只算事件可靠性通過，不算完整對話品質、Safari 或弱模型等效。下一步 P2 第一批，依
`research/p2_grounded_validation_plan_2026-09-07.md` 限制未知占位欄位被誤當可澄清的具體假設。

後續 P2 第一批 gate 已實作：10/10 focused、51/51 adjacent，本機相同六輪移除兩次無根據二選一，M27 ledger
逐欄不變。但模型逾時後的通用追問與新控制中的語意錯誤仍在，**P2 對話品質 FAIL**；詳見
`analysis/p2_grounded_validation_acceptance_2026-09-07.md`。啟動診斷 19.547616 秒完成一個 token；不得算聊天通過。
當前接續：本機 planner readiness／生成預算的最小診斷，再依負結果定第二批；不添加測試句專用答案。
使用者追加高效率要求：不重跑未變动長套件、不新增支援編號，優先修影響實際對話的問題。

P2 第二批已完成 bounded compact general planner：同模型／原 Memory 與 Hard rules，三個有效精簡候選、
256 output tokens、產品預設 20 秒／0 retries。原研究入口未改，這不是同預算公平研究比較。
最後相鄰 62/62；本機六輪兩次一般生成 2/2，6.730137／8.623820 秒；M27 與 P1 原始六輪逐欄相同。
最新圖接線兩輪驗證一個模型呼叫對應一個 compact node；仍非 Safari。詳見
`analysis/p2_compact_planner_acceptance_2026-09-07.md`。
P2 整體 partial：自然度與廣泛控制未過。兩批後下一步重評表達層的無來源 hash prefix／重複 suffix，
先做 model core→最終文字對照，不新增專用測試答案或研究編號。

M57.9 backend focused 10/10，507.37 秒；source／既有 synthetic artifact 保存為 WIP，未完成 final freeze／
相鄰檢查／最終同 run Safari。兩張舊 Safari 圖不是同 run 前後，見 `analysis/m57_9_partial_status_2026-09-07.md`。
Computer Use 已拒絕當時 Safari 網址並結束 session，禁止改用別的 UI 技術繞過。Web 層 pending 不阻止獨立產品研發。
正式人類與 M58 gates 未改；保存的 audit 是前階段 snapshot，不能冒充本日新讀私人 ledger。

## 8. 關鍵檔案，按順序讀取

最新先讀：

1. `analysis/m57_8_participant_confirmed_ledger_completion_acceptance_2026-09-06.md`
2. `research/m57_8_participant_confirmed_ledger_completion_plan_2026-09-05.md`
3. `configs/m57_8_participant_confirmed_ledger_completion_v1.json`
4. `research/m57_8_participant_confirmed_ledger_completion_implementation_freeze_2026-09-06.json`
5. `m57_8_participant_confirmed_ledger_completion.py`
6. `test_m57_8_participant_confirmed_ledger_completion.py`
7. `analysis/m57_8_prechange_participant_ledger_completion_gap_probe_2026-09-05.json`
8. `analysis/m57_8_participant_confirmed_ledger_completion_rehearsal_2026-09-05.json`
9. `analysis/m57_8_participant_confirmed_ledger_completion_live_audit_2026-09-05.json`
10. `analysis/m57_8_participant_confirmed_ledger_completion_fixture_cost_2026-09-05.json`
11. `analysis/m57_8_safari_participant_completion_acceptance_2026-09-06.json`
12. `analysis/m57_8_safari_participant_ready_to_seal_2026-09-06.jpg`、
    `analysis/m57_8_safari_participant_sealed_2026-09-06.jpg`與
    `analysis/m57_8_safari_participant_completion_flow_2026-09-06.jpg`

再追M57.7時讀：

1. `analysis/m57_7_auditable_participant_runtime_launcher_acceptance_2026-09-05.md`
2. `research/m57_7_auditable_participant_runtime_launcher_plan_2026-09-05.md`
3. `configs/m57_7_auditable_participant_runtime_launcher_v1.json`
4. `configs/m57_7_participant_runtime_requirements.txt`
5. `research/m57_7_auditable_participant_runtime_launcher_implementation_freeze_2026-09-05.json`
6. `m57_7_auditable_participant_runtime_launcher.py`
7. `test_m57_7_auditable_participant_runtime_launcher.py`
8. `analysis/m57_7_prechange_participant_runtime_gap_probe_2026-09-05.json`
9. `analysis/m57_7_auditable_participant_runtime_launcher_rehearsal_2026-09-05.json`
10. `analysis/m57_7_auditable_participant_runtime_launcher_live_audit_2026-09-05.json`
11. `analysis/m57_7_auditable_participant_runtime_launcher_fixture_cost_2026-09-05.json`
12. `analysis/m57_7_safari_attested_runtime_acceptance_2026-09-05.json`
13. `analysis/m57_7_safari_attested_runtime_flow_2026-09-05.jpg` 與
    `analysis/m57_7_safari_recovered_collector_2026-09-05.jpg`

再追M57.6時讀：

1. `analysis/m57_6_crash_recoverable_participant_capability_acceptance_2026-09-05.md`
2. `research/m57_6_crash_recoverable_participant_capability_plan_2026-09-05.md`
3. `configs/m57_6_crash_recoverable_participant_capability_v1.json`
4. `research/m57_6_crash_recoverable_participant_capability_implementation_freeze_2026-09-05.json`
5. `m57_6_crash_recoverable_participant_capability.py`
6. `test_m57_6_crash_recoverable_participant_capability.py`
7. `analysis/m57_6_prechange_post_claim_restart_gap_probe_2026-09-05.json`
8. `analysis/m57_6_crash_recoverable_participant_capability_rehearsal_2026-09-05.json`
9. `analysis/m57_6_crash_recoverable_participant_capability_fixture_cost_2026-09-05.json`
10. `analysis/m57_6_crash_recoverable_participant_capability_live_audit_2026-09-05.json`
11. `analysis/m57_6_safari_crash_recovery_acceptance_2026-09-05.json`
12. `analysis/m57_6_safari_crash_recovery_flow_2026-09-05.jpg` 與
    `analysis/m57_6_safari_recovered_collector_2026-09-05.jpg`

再追M57.5時讀：

1. `analysis/m57_5_participant_capability_issuance_acceptance_2026-09-05.md`
2. `research/m57_5_participant_capability_issuance_plan_2026-09-04.md`
3. `configs/m57_5_participant_capability_issuance_v1.json`
4. `research/m57_5_participant_capability_issuance_implementation_freeze_2026-09-04.json`
5. `m57_5_participant_capability_issuance.py`
6. `test_m57_5_participant_capability_issuance.py`
7. `analysis/m57_5_prechange_participant_capability_gap_probe_2026-09-04.json`
8. `analysis/m57_5_participant_capability_issuance_rehearsal_2026-09-04.json`
9. `analysis/m57_5_participant_capability_issuance_fixture_cost_2026-09-04.json`
10. `analysis/m57_5_participant_capability_issuance_live_audit_2026-09-04.json`
11. `analysis/m57_5_safari_participant_capability_acceptance_2026-09-04.json`
12. `analysis/m57_5_safari_capability_flow_2026-09-04.jpg` 與
    `analysis/m57_5_safari_secure_collector_2026-09-04.jpg`

再追M57.4與上游時讀：

1. `analysis/m57_4_component_evidence_collection_acceptance_2026-09-04.md`
2. `research/m57_4_component_evidence_collection_plan_2026-09-04.md`
3. `configs/m57_4_component_evidence_collection_v1.json`
4. `research/m57_4_component_evidence_collection_implementation_freeze_2026-09-04.json`
5. `m57_4_component_evidence_collection.py`
6. `test_m57_4_component_evidence_collection.py`
7. `analysis/m57_4_prechange_component_evidence_collection_gap_probe_2026-09-04.json`
8. `analysis/m57_4_component_evidence_collection_rehearsal_2026-09-04.json`
9. `analysis/m57_4_component_evidence_collection_fixture_cost_2026-09-04.json`
10. `analysis/m57_4_component_evidence_collection_live_audit_2026-09-04.json`
11. `analysis/m57_4_safari_component_evidence_collection_acceptance_2026-09-04.json`
12. `analysis/m57_4_safari_component_evidence_flow_2026-09-04.png` 與
    `analysis/m57_4_safari_component_evidence_boundary_2026-09-04.png`
13. `research/m57_3_sanctioned_outcome_analyzer_bridge_plan_2026-09-04.md`
14. `configs/m57_3_sanctioned_outcome_analyzer_bridge_v1.json`
15. `research/m57_3_sanctioned_outcome_analyzer_bridge_implementation_freeze_2026-09-04.json`
16. `m57_3_sanctioned_outcome_analyzer_bridge.py`
17. `test_m57_3_sanctioned_outcome_analyzer_bridge.py`
18. `analysis/m57_3_prechange_outcome_analyzer_bridge_gap_probe_2026-09-04.json`
19. `analysis/m57_3_sanctioned_outcome_analyzer_bridge_rehearsal_2026-09-04.json`
20. `analysis/m57_3_sanctioned_outcome_analyzer_bridge_fixture_cost_2026-09-04.json`
21. `analysis/m57_3_sanctioned_outcome_analyzer_bridge_live_audit_2026-09-04.json`
22. `analysis/m57_3_safari_outcome_analyzer_bridge_acceptance_2026-09-04.json`
23. `analysis/m57_3_safari_outcome_bridge_flow_2026-09-04.png` 與
    `analysis/m57_3_safari_outcome_bridge_boundary_2026-09-04.png`

再追M57.2與上游時讀：

1. `analysis/m57_2_component_prediction_capsule_acceptance_2026-09-04.md`
2. `research/m57_2_component_prediction_capsule_plan_2026-09-04.md`
3. `configs/m57_2_component_prediction_capsule_v1.json`
4. `research/m57_2_component_prediction_capsule_implementation_freeze_2026-09-04.json`
5. `m57_2_component_prediction_capsule.py`
6. `test_m57_2_component_prediction_capsule.py`
7. `analysis/m57_2_prechange_component_prediction_capsule_gap_probe_2026-09-04.json`
8. `analysis/m57_2_component_prediction_capsule_rehearsal_2026-09-04.json`
9. `analysis/m57_2_component_prediction_capsule_fixture_cost_2026-09-04.json`
10. `analysis/m57_2_safari_component_prediction_acceptance_2026-09-04.json`
11. `analysis/m57_1_preoutcome_diagnostic_commitment_acceptance_2026-09-04.md`
12. `research/m57_1_preoutcome_diagnostic_commitment_plan_2026-09-04.md`
13. `configs/m57_1_preoutcome_diagnostic_commitment_v1.json`
14. `research/m57_1_preoutcome_diagnostic_commitment_implementation_freeze_2026-09-04.json`
15. `m57_1_preoutcome_diagnostic_commitment.py`
16. `test_m57_1_preoutcome_diagnostic_commitment.py`
17. `analysis/m57_1_prechange_preoutcome_commitment_gap_probe_2026-09-04.json`
18. `analysis/m57_1_preoutcome_diagnostic_commitment_rehearsal_2026-09-04.json`
19. `analysis/m57_1_preoutcome_diagnostic_commitment_fixture_cost_2026-09-04.json`
20. `analysis/m57_1_safari_preoutcome_diagnostic_acceptance_2026-09-04.json`
21. `analysis/m57_component_error_localization_acceptance_2026-09-04.md`
22. `research/m57_component_error_localization_plan_2026-09-04.md`
23. `configs/m57_component_error_localization_v1.json`
24. `research/m57_component_error_localization_implementation_freeze_2026-09-04.json`
25. `m57_component_error_localization.py`
26. `test_m57_component_error_localization.py`
27. `analysis/m57_component_error_localization_rehearsal_result_2026-09-04.json`
28. `analysis/m57_component_error_localization_live_audit_2026-09-04.json`
29. `analysis/m57_component_error_localization_fixture_cost_2026-09-04.json`
30. `analysis/m57_safari_component_localization_acceptance_2026-09-04.json`
31. `analysis/m56_13_unidirectional_public_snapshot_acceptance_2026-09-04.md`
32. `research/m56_13_unidirectional_public_snapshot_plan_2026-09-03.md`
33. `configs/m56_13_unidirectional_public_snapshot_v1.json`
34. `research/m56_13_unidirectional_public_snapshot_implementation_freeze_2026-09-04.json`
35. `m56_13_unidirectional_public_snapshot.py`
36. `m56_13_public_snapshot_reader.py`
37. `test_m56_13_unidirectional_public_snapshot.py`
38. `analysis/m56_13_unidirectional_public_snapshot_result_2026-09-04.json`
39. `analysis/m56_13_unidirectional_public_snapshot_fixture_cost_2026-09-04.json`

需要追上游理由時，再依下列既有順序讀取：

只先讀以下檔案，避免無目的掃描整個 repository：

1. `CHAT_CONTEXT_COMPACTION_2026-08-10.md`
2. `analysis/m56_6_single_writer_formal_generation_acceptance_2026-09-03.md`
3. `research/m56_6_single_writer_formal_generation_plan_2026-09-03.md`
4. `configs/m56_6_single_writer_formal_generation_v1.json`
5. `research/m56_6_single_writer_formal_generation_implementation_freeze_2026-09-03.json`
6. `m56_6_single_writer_formal_generation.py`
7. `analysis/m56_5_crash_safe_no_retry_continuation_acceptance_2026-09-02.md`
8. `research/m56_5_crash_safe_no_retry_continuation_plan_2026-09-02.md`
9. `configs/m56_5_crash_safe_no_retry_continuation_v1.json`
10. `research/m56_5_crash_safe_no_retry_continuation_implementation_freeze_2026-09-02.json`
11. `m56_5_crash_safe_no_retry_continuation.py`
12. `analysis/m56_4_separate_formal_scorer_acceptance_2026-09-02.md`
13. `research/m56_4_separate_formal_scorer_plan_2026-09-02.md`
14. `configs/m56_4_separate_formal_scorer_v1.json`
15. `research/m56_4_separate_formal_scorer_implementation_freeze_2026-09-02.json`
16. `m56_4_separate_formal_scorer.py`
17. `analysis/m56_3_lease_gated_generation_runner_acceptance_2026-09-02.md`
18. `research/m56_3_lease_gated_generation_runner_plan_2026-09-02.md`
19. `configs/m56_3_lease_gated_generation_runner_v1.json`
20. `research/m56_3_lease_gated_generation_runner_implementation_freeze_2026-09-02.json`
21. `m56_3_lease_gated_generation_runner.py`
22. `analysis/m56_2_real_data_activation_envelope_acceptance_2026-09-02.md`
23. `research/m56_2_real_data_activation_envelope_plan_2026-09-02.md`
24. `configs/m56_2_real_data_activation_envelope_v1.json`
25. `research/m56_2_real_data_activation_envelope_implementation_freeze_2026-09-02.json`
26. `m56_2_real_data_activation_envelope.py`
27. `analysis/m56_pre_outcome_equation_artifacts_acceptance_2026-09-02.md`
28. `research/m56_pre_outcome_equation_artifacts_plan_2026-09-01.md`
29. `configs/m56_pre_outcome_equation_artifacts_v1.json`
30. `research/m56_pre_outcome_equation_artifacts_implementation_freeze_2026-09-02.json`
31. `m56_pre_outcome_equation_artifacts.py`
32. `analysis/m54_human_response_equation_v1_acceptance_2026-09-01.md`
33. `analysis/m55_real_person_longitudinal_readiness_2026-09-01.md`
34. `analysis/m55_temporal_row_contract_acceptance_2026-09-01.md`
35. `analysis/m55_boundary_extension_tool_acceptance_2026-09-01.md`
36. `analysis/m55_boundary_adjudication_tool_acceptance_2026-09-01.md`
37. `analysis/m56_blinded_execution_capsule_acceptance_2026-09-01.md`
38. `analysis/m56_fair_comparison_preflight_acceptance_2026-09-01.md`
39. `research/m56_blinded_execution_capsule_plan_2026-09-01.md`
40. `research/m56_fair_comparison_preflight_plan_2026-09-01.md`
41. `research/m55_boundary_adjudication_tool_plan_2026-09-01.md`
42. `research/m55_boundary_extension_tool_plan_2026-09-01.md`
43. `research/m55_temporal_row_contract_plan_2026-09-01.md`
44. `research/m54_human_response_equation_v1_plan_2026-09-01.md`
45. `research/full_completion_roadmap.md`
46. `configs/m56_blinded_execution_capsule_v1.json`
47. `configs/m56_fair_comparison_preflight_v1.json`
48. `configs/m55_boundary_adjudication_tool_v1.json`
49. `configs/m55_boundary_extension_tool_v1.json`
50. `configs/m55_temporal_row_contract_v1.json`
51. `configs/m54_human_response_equation_v1.json`
52. `m56_blinded_execution_capsule.py`
53. `m56_fair_comparison_preflight.py`
54. `m55_boundary_adjudication_tool.py`
55. `m55_boundary_extension_tool.py`
56. `m55_temporal_row_contract.py`
57. `audit_m55_real_person_longitudinal_readiness.py`
58. `NEXT_THREAD_PROMPT_2026-08-10.md`

只有需要更早設計理由時才讀：

- `CHAT_CONTEXT_COMPACTION_2026-05-01.md`
- `URUHABRAIN_EVOLUTION_LOG.md`

## 9. 使用者工作方式

2026-09-07 排程更新：依 `DEVELOPMENT_WORKFLOW.md` 與 `CURRENT_TASK.md` 區分產品效果、支援工程與正式研究。
以下研究資料與單一變因規則繼續有效；低風險支援項不必各自新建 M 或 dashboard。工具受限的驗收層保持 pending。

- 使用中文，先簡短說明計畫，再開始實作。
- 嚴肅研究使用高推理強度；以證據而非直覺決策。
- 不要求使用者貼舊聊天室。
- 每輪只改一個可歸因的核心變因。
- 所有近期規劃遵守第 4.1 節「一週定律」；每週成果必須同時是核心研究、可操作實驗與外行可理解的完整圖像展示。
- 先小規模、後完整測試；同時檢查能力、行為退步、延遲與資源。
- 測驗題目、答案、題型規則或解題小抄不得寫入 Prompt、記憶、訓練資料或判斷程式。
- 除非確實需要人類主觀判斷、登入或外部硬體，否則自行完成。
- 可獨立驗證的研發單元必須有 `codex/` branch、PR、測試、diff review 與自行 merge。
- 原始 dirty worktree 的 unrelated files 絕對不能動。

## 10. 每輪回報格式

只回報高訊號內容：

- 解決了什麼問題。
- 修改了哪個系統部件。
- 修改前後的實際數據。
- 是否符合預先成功條件。
- 對長期目標的實際貢獻。
- PR、測試及合併狀態。
- 下一個最值得處理的問題。

不要把 narrow mechanism pass 寫成整體系統成熟，也不要用報告篇幅取代實際工程與實驗。
