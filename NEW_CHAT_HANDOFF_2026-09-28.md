# UruhaBrain 新聊天室完整交接｜2026-09-28

> 這是新聊天室的**入口與決策索引**，不是改寫過去的凍結結果，也不取代原始證據。請先讀本文件，再依第 1 節讀當前權威檔與直接依賴。文件中的「目前」以 Git `b543692943403224176eb4890622b82fcb7940c4` 為準；新聊天室開始時必須重查 Git 和 `CURRENT_TASK.md`。不要要求使用者貼舊聊天室。

## 0. 一分鐘理解專案

UruhaBrain 是在個人電腦運作的個人化認知型對話系統及可驗證的研發平台。它把「收到一句話後，人可能如何結合過去經驗、情境、關係、目的和不確定性，決定下一個行動與回覆」拆成可觀察、可介入、可被後續反應推翻的變數。研究問題是：這些中間變數能否在**未見的未來**，比資訊與資源相配的強 LLM 基線更準確預測同一個人的公開可觀察行為；產品問題是：在真實多輪對話中，這些變數能否讓回覆更接住使用者想要的幫助，並在誤解後修正。

一ノ瀬うるは只是一個以**公開資料**建立的人物參數與展示案例。系統不等於本人，也不推斷未公開童年、私生活或真實內心。「人腦方程式」在本專案是**候選計算模型**，不是生物神經方程、意識、讀心或人類等價主張。

截至此快照：本機聊天、跨 session 記憶、可展開的真實 runtime node graph、中文／英文／日文輸入後的自然日文表達、唯讀工具與使用者自備 VRM 的本機顯示已有**有界產品驗收**。M15 在公開 PUB T13 的 300 題同模型成對實驗有 +16.0 百分點的**窄正結果**。強 direct LLM 的 P3-C2 開發對照和跨來源未來預測沒有建立完整系統優勢。**最後封存可核對的正式資料狀態**為 V7 `0/18 + 0/18`、temporal rows `0/30`；近期任務沒有重新讀私有 ledger，不能把這寫成私有資料的即時查詢。依該狀態，正式 M56 比較、M58 因果修正和最終個體預測主張均未完成。

## 1. 權威順序、位置與目前 Git 狀態

1. 工作位置：`/Users/jerrychang/Desktop/uruharemake2_worktrees/persona-data-provenance`。原始 `/Users/jerrychang/Desktop/uruharemake2` 是 dirty checkout，不能在那裡清理、重設或混入修改。
2. 新聊天室第一步執行 `git status --short --branch`、`git rev-parse HEAD`，再讀 [`AGENTS.md`](AGENTS.md)、[`CURRENT_TASK.md`](CURRENT_TASK.md)、[`DEVELOPMENT_WORKFLOW.md`](DEVELOPMENT_WORKFLOW.md)、[`LONG_TERM_GOAL.md`](LONG_TERM_GOAL.md)。接著讀 [`CHAT_CONTEXT_COMPACTION_2026-08-10.md`](CHAT_CONTEXT_COMPACTION_2026-08-10.md) 第 1–4 與第 9 節，以及當前任務卡列出的直接依賴。舊交接中的「下一步」不覆蓋當前卡。
3. 2026-09-28 核對：分支 `codex/v2-15-pragmatic-research-showcase`，HEAD `b543692943403224176eb4890622b82fcb7940c4`，與 origin 同步；既有 PR #435。唯一既有未追蹤項為 `output/graduate_application_report/`，屬使用者研究所報告成果，需保留，不能把它連同無關內容一起提交。
4. [`GPT5_HANDOFF.md`](GPT5_HANDOFF.md) 是 P3-A 歷史交接。2026-09-13 使用者已解除「開發必須 GPT6、執行必須 GPT5」的型號限制；現在以資料凍結、可重現結果、證據邊界與收斂判斷品質。不同模型若要宣稱同等效果，仍要另做實驗。
5. `LONG_TERM_GOAL.md` 是 repository 的長期執行規格；它不代表 Codex app 裡未完成 Goal 的文字或 usage limit 已被修改。只有整個目標達成才可將 Goal 設為 complete。

## 2. 目標是如何收斂的

最初願望是「做出像人一樣從聽到、記得、思考到說話的系統」，以左腦／右腦作工程分工：左側處理語意、社會推理、記憶與行動選擇，右側把選定內容以人物風格表達。這些是**程式架構名稱與設計隱喻**，不能宣稱對應真正的腦半球。

使用者後來指出，一句「我從早上就坐不住，腦子停不下來」可能是在求立即可做的事、求陪伴、暗示沒睡、或等待熟人吐槽。回答字面內容不等於知道對方希望得到什麼。因此系統加入暫定意圖、需求、關係與回覆策略，並要求後續對話能支持、反駁或保留未知。

「像不像人」沒有單一可驗證門檻，故正式研究縮成**可觀察的個體縱向行為預測**：在每個 cutoff 以前只能看以前的來源，先封存預測，再揭開後續公開行為計分。產品開發仍是目前優先交付；研究保留為檢查部件是否真的帶來價值的必要驗證。這兩條線不能互相冒充。

候選方程在 [`research/m54_human_response_equation_v1_plan_2026-09-01.md`](research/m54_human_response_equation_v1_plan_2026-09-01.md) 定義為：

```text
P(Y[t+1] | X[t+1], H[0:t], M[t], S[t], R[t], N[t], C[t], θ[person], U[t])
State[t+1] = G(State[t], Prediction[t], ObservableOutcome[t+1], Error[t+1])
```

`X` 是當前刺激，`H` 是 cutoff 前歷史，`M` 是具來源的記憶，`S` 是暫定狀態，`R` 是關係，`N` 是需求／目標，`C` 是情境，`θ` 是人物參數，`U` 是不確定性；`Y` 首先是**可觀察行為的機率分布**，其次才是互動策略與最終語句。每個變數必須能指出觀察來源、未知範圍、更新方法與可移除的介入。`observed`、`self_reported`、`inferred` 不可混用；缺可靠聲學資料時標 `unavailable`，文字不能冒充實際語音語氣。情緒或關係只是可撤銷的模型假設，不得寫成事實性長期記憶。

使用者要求的完整交付還包含：跨 session／重啟保留與更正；中／英／日輸入皆得到自然日文可見回覆；一般聊天不傾倒內部分析、不因閒置單獨催促；真實 node graph、VRM、Function Calling 的本機統一入口；同模型公平比較；正式時間 holdout、消融、第二人物轉移與人類被理解感評價。M1「一週展示版」是**已封存的 checkpoint**，不可移動完成線以美化進度。

里程碑的大方向：M1–M5 建立時間觀測站、記憶與狀態骨架；M6–M12 在合成行為預測、跨窗口、第二虛構人物及日文實現上確認局部機制與反例；M13–M15 用公開 PUB 語用題建立第一個確認性窄正結果；M16–M29 把逐輪預測、修正、持久化、日文表面和 Safari 圖接回產品；M30–M36 用新保留集及同模型比較發現語義忠實度、surface、長期策略仍有失敗；M37–M53 收窄來源授權、回饋連結和實際可交付動作；M54 起定義候選方程與嚴格真人時間預測。每個 M 的精確 PASS／FAIL 與依賴見 [`research/full_completion_roadmap.md`](research/full_completion_roadmap.md)；不能用編號連續增加推定能力連續上升。

## 3. 真實系統從輸入到輸出

```text
文字／語音輸入
 → 語者與來源資格、字面與語用訊號
 → 短期／episodic／knowledge／wisdom／procedural／profile 記憶檢索
 → 已知／推測／未知的使用者狀態與關係假設
 → 候選行為、下一輪預測與不確定性
 → 有來源的策略／動作選擇
 → 日文表達與來源、身份、語意、語言、安全檢查
 → 使用者可見回覆、工具或本機 VRM 顯示
 → 真正下一輪回饋 → 支持／反駁／未知、校準、撤銷、持久化
```

核心位於 [`uruha_brain_mac.py`](uruha_brain_mac.py)：`MemoryManager` 使用 Chroma 的多類記憶；`LeftBrain` 管路由、推論與選擇；`RightBrain` 管日文表達；`UruhaBrainV4_Mac` 的 `ingest → cognitive_tick → emit` 形成逐輪資料流。[`uruha_runtime.py`](uruha_runtime.py) 管 runtime state／blackboard／event，[`uruha_compute_ledger.py`](uruha_compute_ledger.py) 記呼叫與成本，[`public_persona_contract_v3.py`](public_persona_contract_v3.py) 管公開人物證據邊界。

Web 基底在 [`uruha_web_ui.py`](uruha_web_ui.py) 與 [`uruha_web_ui_product.py`](uruha_web_ui_product.py)。目前 P4 產品新增層一路疊加到 [`uruha_web_ui_product_p4_az.py`](uruha_web_ui_product_p4_az.py)；**不能把最初的 `uruha_web_ui_product.py` 誤認成最新完整入口**。應以當前任務卡與現行 launcher 再核對啟動方式。P4-BB／P4-BC 是離線的 typed-action 實驗，**尚未接入產品 runtime**。

使用者平常只看自然日文結果；研究／除錯畫面可展開本輪真正經過的輸入、來源、記憶、假設、候選、決策、utterance、回寫與後果節點。圖上有節點只證明事件被記錄；要主張某段記憶**造成**回答差異，還需在等條件下移除／替換該記憶並觀察 `ΔP(Y)`。

目前 P4 的有界產品能力：P1 讓 prediction ID 跨重啟不覆寫舊回饋；P2 有緊湊策略與部分更正／求助／婉拒／speaker-qualified recall；P4-B 本機隔離啟動、P4-C 一個唯讀 `get_runtime_status` 工具、P4-D 使用者自備 VRM 的 browser-only 中性模型顯示、P4-E/F 跨 process 記憶回溯與偏好更正均有真實 Safari 有界驗收。VRM 目前只是本機呈現，不具有已驗證的認知動作控制；Function Calling 目前不是一般可寫入的工具代理。後續 P4 真實多輪曾反覆在來源接線、候選審核 timeout、最後實際動作交付失敗；不能把早期產品通過概括成 open-world 可靠。

一個可見的**有界正例**：當上游已提供「簡報仍空白」及已授權的 `structure_scaffold` typed spec，P4-BB 會在不呼叫模型的情況下編譯出「まずメモに見出しを三つだけ書いて、そこで止めよ。」這個帶立即動作與停止條件的日文計畫。但 P4-BC 顯示，從原始對話抽取可靠 typed spec 仍失敗。**真實 Safari 負例**則是：在多輪裡雖然正確連回前一輪來源、辨認使用者要一個實際步驟，M46 的模型審核仍曾 timeout，最後只得到澄清而沒有交付步驟。這正是目前要修的「內部理解／計畫」到「使用者真正得到幫助」的斷點，見 [`analysis/p4_az_real_previous_turn_ellipsis_to_action_delivery_failure_2026-09-26.md`](analysis/p4_az_real_previous_turn_ellipsis_to_action_delivery_failure_2026-09-26.md)。

## 4. 實驗設計與證據階梯

正式研究比較的條件為 `B0` 行為先驗、`B1` 事件＋最小身份的 LLM、`B2` 加靜態人格、`B3` 普通 RAG、`B4` 全歷史摘要、`B5` 等資訊預算的強結構化 LLM、`Ours` 有明確記憶／狀態／轉移／機率決策的系統。P3 產品對照另比較 `full_history_direct`、`full_history_deliberate`、`product_system`；不同實驗不可混為同一條件。規格見 [`research/p3_product_comparison_spec_v1.md`](research/p3_product_comparison_spec_v1.md)。

要固定基礎模型、可見歷史與人物條件、硬體、temperature／seed、context／completion ceiling，公開實際 prompt／completion tokens、延遲與失敗率。先凍結資料、cutoff、主要指標、最小重要效果與錯誤分類；預測 hash 封存後才揭開 future。時間 `t` 後的影片、字幕、摘要、embedding、標註與答案都不能進入 `t` 的預測。來源可讀不等於允許訓練或重散布。

主要指標依問題分開：行為 Top-1／Top-k／Macro-F1；機率 Brier／NLL／ECE；語用成對正確率與過度解讀；記憶來源與時間正確性；消融／介入後 `ΔP(Y)`；獨立真人的盲式偏好與「被理解感」。證據層依序是資料時間有效 → deterministic 機制 → fresh prediction → 同模型增益與成本 → 消融因果性 → rolling／跨來源／第二人物 → 完整 runtime／Safari／人評。下一層不能由上一層測試數量推定。

## 5. 已做實驗與 benchmark：數字、能說什麼、不能說什麼

| 實驗／版本 | 實際結果 | 合理結論與限制 | 原始證據 |
|---|---|---|---|
| DailyDialog controller proxy | 60 題：act accuracy `0.300`／macro-F1 `0.125`；emotion accuracy `0.6167`／macro-F1 `0.1801` | 早期對話行為選擇仍弱；是 planner proxy，不是最終日文回覆 | [`reports/formal_brain_benchmarks_report.md`](reports/formal_brain_benchmarks_report.md) |
| DailyDialog utterance interpreter v4 | 不同的官方 test 200 題：act `0.965`／macro-F1 `0.9651`；emotion accuracy `1.0`、全標籤 macro-F1 `0.7143` | 評的是輸入句 act／emotion 分類器，**不能取代上列 planner 或最終聊天** | [`reports/formal_dailydialog_holdout_report.md`](reports/formal_dailydialog_holdout_report.md) |
| ToMBench 40 題樣本 | `39/40 = 97.5%`；19 題 LLM MCQ、21 題 symbolic selection | 僅該抽樣、system-level 選答；非完整 ToMBench、純 LLM 或「像人 97.5%」 | [`reports/formal_brain_benchmarks_report.json`](reports/formal_brain_benchmarks_report.json) |
| ToMBench 全 2,860 題不同開發版本 | 6/8 affect-appraisal 版本 `1106/2860 = 38.67%`；6/9 後續 faux-pas 版本 `1999/2860 = 69.90%`，仍 `605` 未解析 | 開發期不同版本、不同方法與專用規則；**不可與 40 題 97.5% 合成提升曲線，也不是獨立 future holdout** | [`reports/tombench_affective_appraisal_before_after_20260608.md`](reports/tombench_affective_appraisal_before_after_20260608.md)、[`reports/tombench_fauxpas_before_after_20260609.md`](reports/tombench_fauxpas_before_after_20260609.md) |
| MPI-style Big Five | 中／英／日 30 題 parsed `30/30`，CV `0.2446`、stability `0.7554` | 自陳答題跨語穩定度；非真人相似度、人格效度或 Big Five 正式受試結果 | [`reports/formal_brain_benchmarks_report.json`](reports/formal_brain_benchmarks_report.json) |
| M6／M8／M9 早期縱向 predictor | M6 合成 8 筆：Ours Top-1 `87.5%`、Brier `0.151`，B5 `75%`／`0.347`；M8 新合成 16 筆反轉為 Ours `62.5%`／`0.741`、B5 `81.25%`／`0.428`；M9 第二虛構人物 16 筆 Ours `43.75%`／`1.050`，B4/B5 各 `75%` | M6 有局部機制訊號，但後兩組未重現；全部是合成資料，不能推成真實個體未來預測 | [`analysis/m6_behavior_predictor_acceptance_2026-08-15.md`](analysis/m6_behavior_predictor_acceptance_2026-08-15.md)、[`analysis/m8_rolling_scaling_acceptance_2026-08-15.md`](analysis/m8_rolling_scaling_acceptance_2026-08-15.md)、[`analysis/m9_second_person_transfer_acceptance_2026-08-15.md`](analysis/m9_second_person_transfer_acceptance_2026-08-15.md) |
| M10 日文實現 | 16 合成案例／144 calls；上游忠實 `14/16`、最終 outcome `9/16`，direct outcome `10/16`，自然日文 surface `7/16` | 決策正確與最後說對是兩個 gate；此版本未優於 direct，無人評 | [`analysis/m10_behavior_authoritative_language_acceptance_2026-08-15.md`](analysis/m10_behavior_authoritative_language_acceptance_2026-08-15.md) |
| PUB M13→M15 | M13 64 題 Ours `70.3%` vs generic `75.0%`，schema `15/64`；M14 disjoint 64 題 `64.1%` vs `54.7%`，差未顯著；M15 新 300 題 T13：`68.7%` vs `52.7%`，成對 `+16.0pp`、95% CI `[+7,+25]pp`、McNemar `p=0.00079446`，勝／平／負 `123/102/75` | M15 是 `qwen3.5:9b`、一種指示語任務、固定 protocol 的確認性窄正結果；多 `13,830` tokens（`+9.0%`）和 `109.2s`（`+4.8%`）。CI 下界為 +7pp，**不能稱母體提升至少 15pp**；不證明全語用或人類理解 | [`analysis/m13_pub_pragmatics_report_2026-08-17.md`](analysis/m13_pub_pragmatics_report_2026-08-17.md)、[`analysis/m15_deixis_confirmation_report_2026-08-17.md`](analysis/m15_deixis_confirmation_report_2026-08-17.md) |
| 50 輪、記憶與 M34–M36 | 50 輪 trace 與跨 process speaker-qualified recall 可展示；M35 同當輪輸入的 policy proxy：baseline `25%`、longitudinal `75%`，但 **7 gates FAIL**；M36 `16.67%` vs `83.33%` 亦有 7 個機制／修正／表面 gate 失敗 | 已確認歷史可在凍結案例改變策略；不可宣稱自然長對話、人類偏好或完整里程碑通過 | [`analysis/m35_same_model_longitudinal_pragmatic_acceptance_2026-08-25.md`](analysis/m35_same_model_longitudinal_pragmatic_acceptance_2026-08-25.md)、[`research/full_completion_roadmap.md`](research/full_completion_roadmap.md) |
| P3-C2 強 direct baseline 對照 | 12 個 developer-authored dev rows，兩組 Top-1 都 `12/12`；Brier baseline `0.133050`、system `0.120717`，改善 `0.012333 < 0.03` 事前 SESOI；system completion tokens `3.112×`、model latency `2.314×`，整批 `32/32` calls 完成 | 正式**開發線 FAIL**、C1 holdout 未開；強 direct baseline 已接住這批題，system 未有足夠品質或成本優勢 | [`analysis/p3_c2_controlled_context_flip_acceptance_2026-09-20.md`](analysis/p3_c2_controlled_context_flip_acceptance_2026-09-20.md) |
| P3-B 公開影片前瞻 proxy | 來源 1 四窗：Brier baseline `1.17095`、system `1.01340`，Top-1 雙方 `1/4`；來源 3 四窗：baseline `0.81845`、system `0.95215`，Top-1 `2/4` vs `1/4`；跨來源八列 row wins `2/6`（baseline/system），但 actual-label probability `0.31875/0.2625` 與 Top-1 `3/8` vs `2/8` 偏 baseline | 先預測、封存、後揭盲流程跑通；跨來源方向反轉、caption-marker label diversity 不足，proxy **不能支撐 system 優勢**。NLL 偏 system 受 baseline 單一 zero-prob row 放大 | [`analysis/p3_b72_cross_source_proxy_validity_audit_acceptance_2026-09-20.md`](analysis/p3_b72_cross_source_proxy_validity_audit_acceptance_2026-09-20.md) |
| P4-BA→BC 原始對話到行動 | BA 2×2 小模型／審核模型 20 calls，`0/4` arm eligible，最快組也未過品質；BB 有正確 typed spec 時，六種低風險 action plan `6/6` exact／自然日文，12 controls `12/12` blocked，0 model call，max compile `0.00090479s`；BC 從新 raw dialogue 抽 typed spec，28 calls 全完成，但 9B evidence single-gold exact `0/6`、control reason `7/8`、max `21.71181s`，4B positive normalized／compile `5/6` | BA 否定「只換小模型就保品質又快」；BB 只證明**給定正確 typed spec**的下游 compiler；BC 是正式 FAIL，原始對話來源與 span 仍未過，三者都未接產品 | [`analysis/p4_ba_stage_model_allocation_failure_2026-09-26.md`](analysis/p4_ba_stage_model_allocation_failure_2026-09-26.md)、[`analysis/p4_bb_typed_action_compiler_acceptance_2026-09-27.md`](analysis/p4_bb_typed_action_compiler_acceptance_2026-09-27.md)、[`analysis/p4_bc_raw_dialogue_typed_spec_failure_2026-09-27.md`](analysis/p4_bc_raw_dialogue_typed_spec_failure_2026-09-27.md) |

上述不同測試的樣本、任務、模型與資料暴露程度不同，不能合成一個「系統準確率」。尤其 ToMBench 的抽樣與全量版本、DailyDialog 的 planner 與 interpreter、M15 的公開指示語與 P3 的多輪預測，都回答不同問題。

## 6. 可以證明什麼、目前仍不能證明什麼

目前可主張：① M15 的明確語用分解在該同模型、該公開 T13 protocol 下提升 exact reference resolution；② 產品在已驗收的本機隔離案例能保存、回溯並用來源限定記憶，展示真實資料流；③ typed spec 正確時，六種低風險行動能由 deterministic compiler 安全形成日文計畫；④ 時間先後封存與揭盲程序及同模型比較 infrastructure 可執行；⑤ 強 baseline、跨來源與 fresh Safari 的失敗已被定位和保存。

目前**不能**主張：已得出人類或一ノ瀬うるは的真實思考方程式；知道私人內心；整體更像人；全面優於強 LLM；open-world 長對話穩定被理解；正式個體未來行為預測成功；第二真人 transfer 成立；VRM 已有認知動作智慧。P4-BB、M54、M56 infrastructure 的 deterministic PASS 都不等於 fresh model generation、完整產品、人評或正式 temporal holdout PASS。

2026-09-27 的 33 頁申請用報告在 [`output/graduate_application_report/UruhaBrain_研究所申請_專案成果報告_2026-09-27.pdf`](output/graduate_application_report/UruhaBrain_研究所申請_專案成果報告_2026-09-27.pdf) 與同名 DOCX。該報告有完整圖表與 12 gate 路線，但**目前未追蹤於 Git**，新聊天室要在同一工作機和 worktree 找；其中 ToMBench 主表只列 40 題抽樣、產品入口列基底檔，需以上方更完整的版本說明和當前卡為準。報告的「工程展示約 73%／科學主張 readiness 約 26%」是加權**主觀進度 rubric**，不是 benchmark 成績或可由實驗量出的客觀完成百分比。

## 7. 已使用或規劃採用的文獻：各自提供什麼

| 來源 | 本專案的用途與邊界 |
|---|---|
| [ACT-R cognitive architecture](https://act-r.psy.cmu.edu/)；[Cowan 2008 工作／長期記憶](https://pubmed.ncbi.nlm.nih.gov/18394484/) | 提供拆分認知階段與記憶類別的理論參考；不是 UruhaBrain 部件已符合人腦的證據。 |
| [Scherer & Moors 2019 情緒評估](https://doi.org/10.1146/annurev-psych-122216-011854)；[Levelt 1999 語言產生](https://pubmed.ncbi.nlm.nih.gov/10354575/) | 參考事件評估、行動傾向，以及先規劃訊息再形成表面語句；推測狀態仍須驗證。 |
| [ToMBench, ACL 2024](https://aclanthology.org/2024.acl-long.847/)；[PUB, Findings ACL 2024](https://aclanthology.org/2024.findings-acl.719/)；[LoCoMo, ACL 2024](https://aclanthology.org/2024.acl-long.747/) | 分別測社會推理、語用四類 14 任務／約 28k 題、長期對話記憶；任何單一 benchmark 都不判斷「是不是人」。 |
| [Gneiting & Raftery 2007](https://doi.org/10.1198/016214506000001437)；[Guo et al. 2017](https://proceedings.mlr.press/v70/guo17a.html) | Proper scoring／Brier、NLL、機率校準與 ECE 的評價方法。 |
| [Peyrard et al. 2021](https://aclanthology.org/2021.acl-long.179/)；[Berg-Kirkpatrick et al. 2012](https://aclanthology.org/D12-1091/)；[Liu et al. 2016](https://aclanthology.org/D16-1230/) | 成對 instance-level 比較、統計不確定性，以及對話自動分數不能替代真人品質的警示。 |
| [DRInQ, ACL 2026](https://aclanthology.org/2026.acl-long.1597/)；[PaCE, Findings ACL 2026](https://aclanthology.org/2026.findings-acl.959/) | 可作固定表面句／變動情境、literal／pragmatic 翻轉的未來外部測試候選；尚未形成可執行正式比較，需先查 artifact、授權、欄位及 split。 |

論文只提供認知假設、資料集或評分方法；是否有增益必須由**本專案事前凍結的對照**決定。PUB T13 正結果不會自動在 DRInQ、PaCE、自由聊天或時間預測上成立。

## 8. 未完成實驗與依賴順序

### 8.1 目前唯一正在做的產品單元：P4-BD

[`CURRENT_TASK.md`](CURRENT_TASK.md) 首節的唯一下一卡是 **P4-BD role-aware evidence span evaluation freeze**。P4-BC 在 `28/28` 真實模型呼叫都完成的情況下仍 FAIL；兩模型 12 組 positive role set 都對、抽到的 atoms 也在原始 source 中，但與唯一 gold span 的逐字邊界不同。`空白`／`還是空白` 可能是可接受的邊界差；`email`／`subject` 可能是角色錯。不得在看過舊輸出後改舊 gold，把 P4-BC 洗成 PASS；也不得把「任何 substring」都算對。

P4-BD 先用**完全新 raw-dialogue cases**，在模型執行前為每個 evidence role 凍結 acceptable exact span 集、可接受 containment、會改變語意或角色的 hard negatives，以及兩組可重現標註規則的一致性 proxy；若沒有獨立真人，明標 `developer-authored`。保留原 strict single-gold exact，另加 role-aware score；template、完整 slots、controls、9B／4B、prompt/schema、硬體、0 retry、`20s` gate 均不變。**本卡只能改 span 評價**，不能同時把 canonical slots 移到 deterministic compiler。先 commit freeze，再實作／測試，新的正式模型執行只准唯一一次。若 role-aware 仍失敗，保留 semantic grounding 缺口；若通過，只能說預先承認的等價邊界不再被誤罰，不能直接宣稱產品整合。

直接依賴：[`analysis/p4_bc_raw_dialogue_typed_spec_failure_2026-09-27.md`](analysis/p4_bc_raw_dialogue_typed_spec_failure_2026-09-27.md)、[`configs/p4_bc_raw_dialogue_typed_spec_prompt_v1.txt`](configs/p4_bc_raw_dialogue_typed_spec_prompt_v1.txt)、[`configs/p4_bc_raw_dialogue_typed_spec_v1.json`](configs/p4_bc_raw_dialogue_typed_spec_v1.json)、[`datasets/p4_bc_raw_dialogue_typed_spec_v1.json`](datasets/p4_bc_raw_dialogue_typed_spec_v1.json)、[`run_p4_bc_raw_dialogue_typed_spec.py`](run_p4_bc_raw_dialogue_typed_spec.py)、[`uruha_typed_action_compiler_p4.py`](uruha_typed_action_compiler_p4.py)。截至快照尚無 P4-BD 檔案，仍在設計／凍結前。

P4-BD 之後的**條件式**產品路線是：若 span gate 值得保留，另立單一變因把來源無關的 canonical slots 交給 deterministic materializer；再以全新 raw-dialogue holdout 測 `dialogue → typed spec → compiler`，最後以隔離 Safari 真實輪次驗 `input → source → spec → plan → M46/M39 → visible Japanese action`，並記錄 token／延遲與 0 正式記憶污染。任何一關失敗應保留負結果，不能直接接產品。

### 8.2 正式個體未來預測研究線

1. **M54 已完成契約**：九個變數、證據狀態、可介入與更新介面可機器檢查；沒有真人預測效度。見 [`research/m54_human_response_equation_v1_plan_2026-09-01.md`](research/m54_human_response_equation_v1_plan_2026-09-01.md)。
2. **M55 的不可替代依賴**：兩位**不同真人**各完成 18 題 V7 codebook pilot，四欄 Krippendorff α 需達事前 `0.667`，時間邊界 mean IoU 至少 `0.5`；最後封存稽核為 `0/18 + 0/18`。通過後才可讓兩人獨立處理公開來源 V9、邊界與顯式裁決，建立至少 30 個真正有 cutoff、刺激、speaker、可觀察 response 的 temporal rows；最後封存稽核為 `0/30`。近期工作未重讀私有 ledger，接手時不能稱這是即時資料。工具工程 ready 不等於真人資料 ready。見 [`analysis/m55_real_person_longitudinal_readiness_2026-09-01.md`](analysis/m55_real_person_longitudinal_readiness_2026-09-01.md)。
3. **M56 正式公平比較**：已有 B0–B5/Ours 授權視圖、prediction commitment、no-retry、crash-safe、single-writer、獨立 scorer 與資源審計等工程；最後封存稽核的正式模型呼叫／outcome／result 為 `0`。M55 合格後重驗 hashes 與授權，固定 30×7 prediction slots、實際 token／延遲，再在 outcome 開封前提交全組預測；B5 vs Ours 是主要 contrast。正負都保存。不能用 synthetic rehearsal 假稱正式結果。
4. **M57→M58**：M57 依 M56 真正錯誤，做不看答案的單部件替換／oracle 定位；目前只在 synthetic fixture 有工程驗證，無正式 localization。M57.9 的 backend 局部測試曾通過，但最後同次 Safari／disk／freeze 驗收是 **partial**，不能稱 M57.9 完成。M58 只能由正式結果事前選定**單一**要修的變因，再用新 holdout 驗，不准從舊答案追分。
5. **M59–M62／至多 M75**：完成記憶、狀態、關係、人物參數的消融與反事實介入；desired-response 前瞻驗證與真人盲評；rolling cutoff、資料量曲線、第二人物不改核心的 transfer、第二模型重現及完整成本／安全。若結果不支持，也須明確停下、刪除無效部件或給出受限負結論。M75 是硬停止點，不是保證成功的里程碑。

額外的人類「被理解感」實驗與 temporal behavior truth 不同：建議事前固定 rubric，至少 3 位獨立 rater、50 組以上同模型成對多輪對話，盲式比較接住隱含需求、過度解讀、被否定後修正與跨輪一致性；不得拿自動文字分數、模型自評、合成標籤或同一人重填當獨立人評。

### 8.3 時間與資源估計（規劃值，不是已花費）

2026-09-27 申請報告估計：由一人兼開發／資料／實驗，做出可支持核心研究主張約 `4–8` 個月；加入第二人物、較多公開資料與正式人評約 `8–12` 個月。最低量級約兩位各 18 題 pilot、30 個真實時序列、3 個公開來源、約 300–600 次本機模型呼叫、120–250 人工小時；穩健版本約 5–8 個來源／100+ episodes、1,000+ calls、300–600 人工小時。這些是**條件式估算**，真正風險是來源權利、真人真值與跨來源重現，不是再多寫幾個 M。

## 9. 工作規則與交接後第一步

- 使用中文；先短述本輪目標、before 證據、允許變因、成功／失敗 gate，再執行。使用者已授權持續研發，不必逐步詢問是否開始。
- 正式實驗必須先 freeze 資料／prompt／門檻／資源，再執行；一個 case 0 retry/fallback。已曝光題只能作 development。失敗永久保留；最多兩個有根據、單一變因修正批次，仍失敗則提交 `REVIEW_REQUIRED` 反例與取捨。
- 只在安全 worktree 工作，不碰原始 dirty checkout、私有正式 DB、無關變更或未授權外部部署；隔離 Web/Safari 測試 session 與 DB。最後核對 diff、相稱測試、Git commit／push／既有 PR；只提交本項範圍。
- 小測、相鄰回歸、fresh generation、完整 runtime、Safari、人評、正式 holdout 分開記錄。模型生成 timeout、再澄清、只有內部計畫卻未交付可見動作，皆依事前 gate 算 FAIL。
- 不以 benchmark-specific 規則灌答案；不降低強 baseline；不把 unknown 算成支持；不把推測心理寫成事實記憶；不拿公開人物資料冒充私人真值。M55 真人依賴不能由 Codex、LLM、synthetic 或同一人重複標註替代。
- 若使用者問進度，先回答具體資料；若問新任務，再以當前卡為準。不要因支援文件、測試數或 M 編號增加就宣稱能力進步。

**新聊天室的第一個可執行工作**：重查 Git 與 `CURRENT_TASK.md`，閱讀 P4-BC frozen failure 與 P4-BB compiler contract，寫出 P4-BD 在新題上可事前核對的 span role／containment／hard-negative annotation contract 和成功 gate，保存 freeze，再依卡片進行最小實作與一次性比較。正式真人線仍待兩位不同人，這不妨礙獨立、已授權的產品工作。

## 10. 可直接貼到新聊天室的啟動文字

> 請先完整閱讀 `/Users/jerrychang/Desktop/uruharemake2_worktrees/persona-data-provenance/NEW_CHAT_HANDOFF_2026-09-28.md`。不要要求我貼舊聊天室。依文件第 1 節核對 Git 與權威任務卡，保留 `output/graduate_application_report/` 和所有無關變更。先用中文說明你理解的研究目標、已證明的窄結果、正式未完成的 gate 與目前唯一 P4-BD 工作，並指出快照若已過期的差異；接著依 `CURRENT_TASK.md` 的最新範圍持續實作與驗證。不得把 M15、ToMBench 抽樣、synthetic、離線 compiler、Safari 個案或測試數外推成已證明人類方程式／全面優於強 LLM；正式 M55/M56 必須遵守真人資料和凍結授權門檻。

## 11. 完整查證索引

- 長期目標與工作順序：[`LONG_TERM_GOAL.md`](LONG_TERM_GOAL.md)、[`DEVELOPMENT_WORKFLOW.md`](DEVELOPMENT_WORKFLOW.md)、[`CURRENT_TASK.md`](CURRENT_TASK.md)、[`AGENTS.md`](AGENTS.md)。
- 歷史／架構／證據邊界：[`CHAT_CONTEXT_COMPACTION_2026-08-10.md`](CHAT_CONTEXT_COMPACTION_2026-08-10.md) §1–4、§9；[`research/full_completion_roadmap.md`](research/full_completion_roadmap.md)；[`research/hypotheses.md`](research/hypotheses.md)。
- 長篇成果與圖像：[`output/graduate_application_report/UruhaBrain_研究所申請_專案成果報告_2026-09-27.pdf`](output/graduate_application_report/UruhaBrain_研究所申請_專案成果報告_2026-09-27.pdf)，同目錄 DOCX 與 `figures/`；目前未追蹤，需在同一 worktree 讀。
- 當前最小反例與資料：[`analysis/p4_bc_raw_dialogue_typed_spec_failure_2026-09-27.md`](analysis/p4_bc_raw_dialogue_typed_spec_failure_2026-09-27.md)、[`analysis/p4_bc_raw_dialogue_typed_spec_evidence_2026-09-27.json`](analysis/p4_bc_raw_dialogue_typed_spec_evidence_2026-09-27.json)、[`analysis/p4_bb_typed_action_compiler_acceptance_2026-09-27.md`](analysis/p4_bb_typed_action_compiler_acceptance_2026-09-27.md)。
- 真人 gate 與正式研究狀態：[`analysis/m55_real_person_longitudinal_readiness_2026-09-01.md`](analysis/m55_real_person_longitudinal_readiness_2026-09-01.md)、[`analysis/m57_9_partial_status_2026-09-07.md`](analysis/m57_9_partial_status_2026-09-07.md)。

> 注意：使用者以前提供的 `RESEARCH_SPEC_FOR_CODEX.md` 不在此 Git checkout；若要引用它，需先核對先前使用者附件或本機 `/Users/jerrychang/Downloads/RESEARCH_SPEC_FOR_CODEX.md`，並以本文件列出的較新長期目標與當前任務卡處理衝突。
