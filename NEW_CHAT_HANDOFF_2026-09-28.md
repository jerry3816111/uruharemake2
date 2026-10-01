# UruhaBrain 新聊天室完整交接｜2026-09-28

> 這是新聊天室的**入口、決策索引與操作筆記**，不是改寫過去的凍結結果，也不取代原始證據。研究結果以 Git `b543692943403224176eb4890622b82fcb7940c4` 為基準；本交接檔先於 `c22e02ded572d8df850147c76fa9ce31d2185738` 提交，後續修訂會再產生新 commit。新聊天室開始時必須重查 Git 和 `CURRENT_TASK.md`，不能把文件中的 SHA 當永久最新狀態。不要要求使用者貼舊聊天室。

## 0. 一分鐘理解專案

UruhaBrain 是在個人電腦運作的個人化認知型對話系統及可驗證的研發平台。它把「收到一句話後，人可能如何結合過去經驗、情境、關係、目的和不確定性，決定下一個行動與回覆」拆成可觀察、可介入、可被後續反應推翻的變數。研究問題是：這些中間變數能否在**未見的未來**，比資訊與資源相配的強 LLM 基線更準確預測同一個人的公開可觀察行為；產品問題是：在真實多輪對話中，這些變數能否讓回覆更接住使用者想要的幫助，並在誤解後修正。

一ノ瀬うるは只是一個以**公開資料**建立的人物參數與展示案例。系統不等於本人，也不推斷未公開童年、私生活或真實內心。「人腦方程式」在本專案是**候選計算模型**，不是生物神經方程、意識、讀心或人類等價主張。

截至此快照：本機聊天、跨 session 記憶、可展開的真實 runtime node graph、中文／英文／日文輸入後的自然日文表達、唯讀工具與使用者自備 VRM 的本機顯示已有**有界產品驗收**。M15 在公開 PUB T13 的 300 題同模型成對實驗有 +16.0 百分點的**窄正結果**。強 direct LLM 的 P3-C2 開發對照和跨來源未來預測沒有建立完整系統優勢。**最後封存可核對的正式資料狀態**為 V7 `0/18 + 0/18`、temporal rows `0/30`；近期任務沒有重新讀私有 ledger，不能把這寫成私有資料的即時查詢。依該狀態，正式 M56 比較、M58 因果修正和最終個體預測主張均未完成。

## 1. 權威順序、位置與目前 Git 狀態

1. 工作位置：`/Users/jerrychang/Desktop/uruharemake2_worktrees/persona-data-provenance`。原始 `/Users/jerrychang/Desktop/uruharemake2` 是 dirty checkout，不能在那裡清理、重設或混入修改。
2. 新聊天室第一步執行 `git status --short --branch`、`git rev-parse HEAD`，再讀 [`AGENTS.md`](AGENTS.md)、[`CURRENT_TASK.md`](CURRENT_TASK.md)、[`DEVELOPMENT_WORKFLOW.md`](DEVELOPMENT_WORKFLOW.md)、[`LONG_TERM_GOAL.md`](LONG_TERM_GOAL.md)。接著讀 [`CHAT_CONTEXT_COMPACTION_2026-08-10.md`](CHAT_CONTEXT_COMPACTION_2026-08-10.md) 第 1–4 與第 9 節，以及當前任務卡列出的直接依賴。舊交接中的「下一步」不覆蓋當前卡。
3. 2026-09-28 首次交接後核對：分支 `codex/v2-15-pragmatic-research-showcase`，HEAD／origin／PR head 為 `c22e02ded572d8df850147c76fa9ce31d2185738`，既有 PR #435 為 OPEN。只有未追蹤的 `output/graduate_application_report/`，屬使用者研究所報告成果，需保留，不能把它連同無關內容一起提交。本文件修訂後 SHA 必然改變；接手時以實際命令為準。
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

上方流程圖是**設計目標及部分已接通的模組路徑**；每一條線的真實端到端能力須看對應 frozen Safari／模型 gate。P4-AZ 仍有「審核 timeout 後沒有交付實際動作」的完整流程 FAIL，P3-C2 也沒有證成品質提升，不能因圖上有箭頭就稱任意回合的閉環成立。

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
| 50 輪、記憶與 M34–M36 | 50 輪記憶：source recall `2/2`、strict task `4/5`、false-memory `0`；最近 8 輪 baseline 為 `0/2`、`1/5`、`1`，完整 transcript baseline 為 `2/2`、`4/5`、`1`，但本系統 tokens `13,435` vs 完整 transcript `7,405`、延遲 `255.51s` vs `10.99s`。M35 同當輪 policy proxy：baseline `25%`、longitudinal `75%`，但 **7 gates FAIL**；M36 `16.67%` vs `83.33%` 亦有 7 gate FAIL | 記憶比最近 8 輪有局部 bounded 優勢，與完整 transcript strict task 打平且成本高；M35／M36 完整里程碑未過，不能宣稱一般長對話優勢或人類偏好 | [`analysis/m12_literature_grounded_evaluation_report_2026-08-17.md`](analysis/m12_literature_grounded_evaluation_report_2026-08-17.md)、[`analysis/m35_same_model_longitudinal_pragmatic_acceptance_2026-08-25.md`](analysis/m35_same_model_longitudinal_pragmatic_acceptance_2026-08-25.md) |
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
| [DRInQ, ACL 2026](https://aclanthology.org/2026.acl-long.1597/)；[PaCE, Findings ACL 2026](https://aclanthology.org/2026.findings-acl.959/) | 固定表面句／變動情境、literal／pragmatic 翻轉的候選方法。P3-C3 已完成 discovery，**可執行候選為 0**：DRInQ 缺可核授權／split、PaCE 官方 artifact 未得、PUB 已曝光且與 C1 任務不符。沒有新外部狀態，不再重複尋找或開 C1 holdout。見 [`analysis/p3_c3_external_pragmatic_benchmark_discovery_acceptance_2026-09-20.md`](analysis/p3_c3_external_pragmatic_benchmark_discovery_acceptance_2026-09-20.md)。 |

論文只提供認知假設、資料集或評分方法；是否有增益必須由**本專案事前凍結的對照**決定。PUB T13 正結果不會自動在 DRInQ、PaCE、自由聊天或時間預測上成立。

## 8. 未完成實驗與依賴順序

### 8.1 目前唯一正在做的產品單元：P4-BD

[`CURRENT_TASK.md`](CURRENT_TASK.md) 首節的唯一下一卡是 **P4-BD role-aware evidence span evaluation freeze**。P4-BC 在 `28/28` 真實模型呼叫都完成的情況下仍 FAIL；兩模型 12 組 positive role set 都對、抽到的 atoms 也在原始 source 中，但與唯一 gold span 的逐字邊界不同。`空白`／`還是空白` 可能是可接受的邊界差；`email`／`subject` 可能是角色錯。不得在看過舊輸出後改舊 gold，把 P4-BC 洗成 PASS；也不得把「任何 substring」都算對。

P4-BD 先用**完全新 raw-dialogue cases**，在模型執行前為每個 evidence role 凍結 acceptable exact span 集、可接受 containment、會改變語意或角色的 hard negatives，以及兩組可重現標註規則的一致性 proxy；若沒有獨立真人，明標 `developer-authored`。保留原 strict single-gold exact，另加 role-aware score；template、完整 slots、controls、9B／4B、prompt/schema、硬體、0 retry、`20s` gate 均不變。**本卡只能改 span 評價**，不能同時把 canonical slots 移到 deterministic compiler。先 commit freeze，再實作／測試，新的正式模型執行只准唯一一次。若 role-aware 仍失敗，保留 semantic grounding 缺口；若通過，只能說預先承認的等價邊界不再被誤罰，不能直接宣稱產品整合。

**尚未定案的數值不要由接手模型補寫**：本快照與當前卡沒有列出 P4-BD 新 role-aware 分數的完整 aggregation／逐 gate 門檻。開始新題或正式呼叫前，必須在 `CURRENT_TASK.md` 與 frozen contract 明列 role-aware positive／hard-negative／control 的分母、分子、逐模型通過線，以及它和保留的 strict exact、compile、日文、token、`20s` 如何共同判定 eligibility，經設計審查後 commit。未凍結前是 `PRE-FREEZE`，不是自行假設「全對」或調整門檻。

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

### 8.4 「過去 → 現在 → 未來」需要怎樣的真正實驗

使用者最終要的不是同一句話答得漂亮，而是可以指出「在時間 `t`，這個人**當時有過哪些可觀察經驗**，這些經驗如何成為暫定狀態，並在尚未看過的情境 `t+1` 預測其公開反應」。三個時間層要在資料與圖上真的分開：

| 時間層 | 應有資料／演算 | 可測量的結果 | 目前缺口 |
|---|---|---|---|
| 過去 `H[0:t]` | source ID、URL／授權、speaker、原始發布／錄製時間、刺激與回應邊界、cutoff 前摘要／embedding；不同說話者與未知標記分開 | 記憶來源、時間正確性、跨重啟持久性；刪除特定記憶後 `ΔP(Y)` | 正式 Uruha 的真人裁決 rows 尚 `0/30`；公開影片字幕 proxy 不是足夠真值 |
| 現在 `X[t+1]` 與 `State[t]` | 當前可見刺激、字面／言外候選、關係／目標／情緒的有來源假設、替代假設、信心、人物參數、可撤銷性 | 是否選對 observable behavior／desired-response policy；是否過度讀心；狀態有無實際改變選擇 | M54 為 contract；M35、P3-C2 仍有完整 gate FAIL |
| 未來 `Y[t+1]` | 在揭曉前輸出 normalized 行為機率與 hash commitment；只在封存後讀取未見事件、真人標註的實際反應 | Top-1／Macro-F1、Brier／NLL／ECE、paired CI、跨來源／rolling cutoff、消融與第二人轉移 | proxy 8 列方向不一致，正式 M56 真實結果不存在 |

一列合格的 temporal row 至少要有 `source_id`、人物與說話者、`observable_input_start_seconds`、`prediction_cutoff_seconds`、`observable_behavior_start_seconds`、`observable_behavior_end_seconds`、刺激內容或其受限 digest、可觀察行為類別、兩位獨立標註和裁決、cutoff 前可用歷史清單、train/dev/holdout 標記。凍結契約的嚴格時序為 `event_start ≤ input_start < prediction_cutoff < behavior_start < behavior_end ≤ event_end`；不能拿 whole-event start/end 代替 cutoff。詳見 [`analysis/m55_temporal_row_contract_acceptance_2026-09-01.md`](analysis/m55_temporal_row_contract_acceptance_2026-09-01.md)。私有 raw 內容留在授權的本機 compartment，公開圖只投影 digest、來源與必要摘要。

最低正式實驗順序：①先確認資料使用權與來源 registry；②兩位真人 V7 pilot 達可靠度；③ V9／boundary 雙人標註與人工裁決，形成 30 個 temporal rows；④ 將 prediction packet 與 outcome key 物理分離，資料切分及模型設定鎖 hash；⑤ B0–B5/Ours 用同一模型／資源條件全部先輸出行為分布；⑥ commitment 完成後獨立 scorer 才開 future；⑦報主要對照、信賴區間、資料量、成本和所有負例；⑧由 M57 找第一個真正失敗的因果階段；⑨僅在新 sealed future 上驗一個修正；⑩做 memory/state/relationship/person 的消融與 transfer。任一前置資料 gate 失敗，後面保持 `NOT_AUTHORIZED`，不能用合成列補數。

目前 M12 的文獻方法回顧已指出：M6 的合成正向 Brier 差在更嚴格審計下不能保證穩健，M8／M9 方向反轉；中央同模型優勢並未成立。這些是設計下一次實驗的**反例**，見 [`analysis/m12_literature_grounded_evaluation_report_2026-08-17.md`](analysis/m12_literature_grounded_evaluation_report_2026-08-17.md)。

### 8.5 論文級驗證與最終交付判準

使用者目前優先**研發，研究只保留必要驗證**；若以論文／研究報告呈現，研究主張仍需下表逐關成立，不能讓工程完成替代科學有效性。

| 要回答的問題 | 必要對照或資料 | 成功／失敗後的結論界線 |
|---|---|---|
| 目前系統是否真的比強 LLM 好？ | 同模型、同可用歷史與人格條件、相同硬體／資源上限；B5 與 Ours 事前主要對照，產品另看 direct／deliberate | 完整 reserve／holdout 的 paired 指標與成本通過事前門檻才可稱該範圍有優勢；負結果則簡化或定位，不換弱 baseline。P3-C2 已給出相反的 dev 訊號。 |
| 模型是否捕捉「同一個人」的可預測結構？ | 真實公開人物跨時間且跨來源的 `stimulus→response`、嚴格 cutoff、獨立標註、rolling windows | 在未見 future 能穩定勝過 B0–B5、機率校準合理，且沒有資料洩漏；否則只稱系統工程或 bounded task 能力。 |
| 記憶、關係、情緒／需要變數是否真的有用？ | 單部件移除／替換、保持其他輸入不變，報 `ΔP(Y)` 及後續 outcome | 變數的作用必須可重現且改善預測；若移除不影響輸出或只改解說文字，不能稱因果中間變數。 |
| 人物模型是否能換人？ | 第二個真實人物只替換有來源資料與 `θ`，不重寫核心推理規則 | 通過時才支持 person-independent architecture；失敗時指出哪些人物參數無法表示。 |
| 使用者會不會真的感到被理解？ | 盲式真人評分，多輪中隱含需求、過度解讀、否定後修正、跨輪一致性；同模型強對照 | 可證明的僅是評分族群／材料上的 preference；不推論私人心理真值。與時間行為預測分開報。 |

最終研究報告至少要有：可反駁假說 H1–H7（見 [`research/hypotheses.md`](research/hypotheses.md)）、資料 registry 與 train/dev/holdout manifest、模型及 prompt／硬體／資源 freeze、每列 source/cutoff/label provenance、預測在答案開封前的 commitment、原始正負結果、paired 統計與效果量、消融／介入、跨來源／第二人物、成本、安全／權利邊界及 reproduction commands。若在 M62 或至多 M75 仍未有優勢，完成的是**有界負研究結論與可用原型**，不是「證明人腦方程式」。

外部語用 benchmark 的現況也要保持：P3-C3 discovery 為可執行候選 `0`，C1 holdout 未開；沒有新增官方 artifact／授權狀態時不無限搜尋新資料集或偷看 test labels。見 [`research/p3_c3_external_pragmatic_benchmark_discovery_release_2026-09-20.json`](research/p3_c3_external_pragmatic_benchmark_discovery_release_2026-09-20.json)。

## 9. 工作規則與交接後第一步

- 使用中文；先短述本輪目標、before 證據、允許變因、成功／失敗 gate，再執行。使用者已授權持續研發，不必逐步詢問是否開始。
- 正式實驗必須先 freeze 資料／prompt／門檻／資源，再執行；一個 case 0 retry/fallback。已曝光題只能作 development。失敗永久保留；最多兩個有根據、單一變因修正批次，仍失敗則提交 `REVIEW_REQUIRED` 反例與取捨。
- 只在安全 worktree 工作，不碰原始 dirty checkout、私有正式 DB、無關變更或未授權外部部署；隔離 Web/Safari 測試 session 與 DB。最後核對 diff、相稱測試、Git commit／push／既有 PR；只提交本項範圍。
- 小測、相鄰回歸、fresh generation、完整 runtime、Safari、人評、正式 holdout 分開記錄。模型生成 timeout、再澄清、只有內部計畫卻未交付可見動作，皆依事前 gate 算 FAIL。
- 不以 benchmark-specific 規則灌答案；不降低強 baseline；不把 unknown 算成支持；不把推測心理寫成事實記憶；不拿公開人物資料冒充私人真值。M55 真人依賴不能由 Codex、LLM、synthetic 或同一人重複標註替代。
- 若使用者問進度，先回答具體資料；若問新任務，再以當前卡為準。不要因支援文件、測試數或 M 編號增加就宣稱能力進步。

**新聊天室的第一個可執行工作**：重查 Git 與 `CURRENT_TASK.md`，閱讀 P4-BC frozen failure 與 P4-BB compiler contract，寫出 P4-BD 在新題上可事前核對的 span role／containment／hard-negative annotation contract 和成功 gate，保存 freeze，再依卡片進行最小實作與一次性比較。正式真人線仍待兩位不同人，這不妨礙獨立、已授權的產品工作。

### 9.1 每一項開發的固定狀態機

接手模型不要把「看懂規格 → 寫程式 → 測試過」縮成一步。每張任務卡依下列順序進行；某一 gate 沒證據就停在該 gate，而非跳到下一步：

1. **核對當前狀態**：讀權威卡首節、`git status`、當前 HEAD、前一實驗原始報告。記錄 `before` 的最小輸入／輸出、錯誤發生在哪一個節點、這個證據是單元、fresh model、Web 還是真人。若觀察不能重現，先查入口與 fixture，不猜原因。
2. **定義一個變因**：在 `CURRENT_TASK.md` 寫清楚本輪只改什麼、允許檔案、不能動的 prompt／資料／model／guard、成功與失敗的逐項門檻、控制案例、精確命令、模型呼叫數與時間／token 上限，以及各失敗分支。不存在的 P4-BD 檔名或測試命令不能事先假寫成已驗證。
3. **設計審查**：新資料、gold／評分契約、baseline、門檻、模型、正式放行或大架構變動須留下明確審查記錄。可由不同 reviewer 審查；若只有原設計模型自己審，標為`非獨立自審`、列出反例及理由，不得降低 gate 或擴大 claim。這是規格 review，不等於人工評價資料。已定案範圍內的小實作選擇不須反覆問使用者能否開始。
4. **先凍結，再觀察正式結果**：commit 新題、來源、分割、annotation contract、固定模型／生成條件、指標／門檻與 freeze tests，記錄 SHA。formal case 在結果未知前不得變更。任何已讀過的答案或前一失敗句均降為 exposed development。
5. **實作一個受限改動**：對準前述失敗節點；重用現有 runtime／graph，保留事實記憶、身份、日文、來源與失敗關閉 guard。依文件編輯約束使用小 patch，不做無關重構、不在正式 DB 測試。
6. **由近到遠驗證**：最小反例 → 舊相鄰回歸 → 新控制／reserve → 必要的 fresh model call → 隔離完整 runtime → 真實 Safari 的可見回覆與 node graph。只要某一層未做，標 `pending`；不能用數百個局部測試抵銷一個完整流程失敗。正式模型題遵守 0 retry／fallback 和預定資源上限。
7. **判讀及保存結果**：逐項列 gate 的分子／分母、原始輸出、reason、source hash、prompt／completion tokens、延遲與實際可見動作。任一必要 gate 失敗即記完整 FAIL；局部 PASS 仍可描述，但不可改判、重跑或修改已曝光 gold。最多少量兩批有理由的單變因修正；仍失敗則 `REVIEW_REQUIRED`，記最小反例和下一個可檢驗假設。
8. **交付並接下一卡**：更新 `CURRENT_TASK.md` 的前後證據、證據層級、下一個唯一工作；只提交這張卡的檔案，推既有分支並核對 PR。舊 formal FAIL 永久保留。下一卡必須解決使用者可感受的缺口或正式研究的必要 gate，不能只為多一張圖或一個編號。

### 9.2 P4-BD 的可直接照做起手式

這是當前卡的專用流程，**不是今天已完成的 P4-BD 實驗**：

1. 先對照 P4-BC frozen 結果的 `空白／還是空白`、`收據／桌上的收據`、`email／subject`，只把它們當 development taxonomy，不放入新的正式題。
2. 在 `CURRENT_TASK.md` 寫 P4-BD 的許可清單與精確驗證命令；選全新繁中／英文／日文 raw-dialogue positives 和界外 controls。每個 positive 的 role 由原始 user source 指定可接受**逐字** span 集；另外列出允許的包含關係及絕對不可接受的 role 調換、否定詞掉落、主客體改變和憑空心理推測。
3. 以兩組可重做的規則或兩位獨立標註者標註，報告不一致處。**兩套規則仍是同一開發者設計的 proxy，不是兩位人類 coder**；沒有兩位不同真人獨立標註與裁決時只能寫 `developer-authored consistency proxy`，不能寫 inter-human reliability 或 Krippendorff α。審查 contract、所有新數值 gate 後先 commit freeze，保留既有 strict single-gold exact 作平行欄位。
4. 只改 evaluator 的 role-aware span 判定與結果欄位。使用 P4-BB／BC 現有測試作必要的相鄰回歸，新增 P4-BD 的 positive／hard-negative scorer 契約測試；**不要**改原 P4-BC 結果、canonical slots、模板、模型 prompt、schema、產品 runtime、M46／M45／M39 或 `20s` gate。
5. freeze SHA 確定後，9B 和 4B 依事前順序在新題各執行一次，0 retry。保留 JSON、template、slots、strict exact、role-aware、controls reason、downstream compile、自然日文、完整 token 與 max latency。若不能核對 freeze、硬體或模型 digest，正式執行先停在 preflight。
6. 任一模型只有事前所有必要 gate 達標才有資格進下一張卡；role-aware 通過只表示事前承認的合理邊界不再被錯罰，**不會**自動修正 9B 的 control reason／timeout 或 4B 的缺欄位，也不授權產品接線。接下來 canonical slot materializer 必須另外凍結為獨立變因。

### 9.3 結果出現後如何決定下一步

| 觀察 | 下一步，且只改一個原因 |
|---|---|
| P4-BD role-aware 仍拒絕角色正確的 span | 檢查 annotation contract 的等價範圍與雙標註一致性；不回頭重標正式輸出。若是真正 role 錯誤，保留 grounding FAIL。 |
| role-aware 通過，但 4B 仍漏 canonical `unknown_constraint_jp` | 另立新卡：只把來源無關常數交給 deterministic materializer；新題驗是否減少漏欄，不能在 P4-BD 同時改。 |
| 9B 品質通過但超過 20 秒，或模型審核仍 timeout | 以獨立成本／stage 分解驗瓶頸；不能直接把 timeout 拉長後稱同 gate 達標。 |
| 離線 spec／compiler 過，但 Safari 沒有交付動作 | 查 source→spec→plan→M46→M39→visible 的第一個斷點；真實日文、停止條件與 node graph 逐輪核對。 |
| P3 強 direct baseline 更好或成本較低 | 保留負結果；對無效部件做消融／簡化。不得故意弱化 LLM 或把開發題改名 holdout。 |
| M55 雙人 α／時間 IoU 不足 | 修 codebook 或邊界定義，另做**新** pilot；同一人重做不能成為兩位獨立 coder。 |
| M56 Ours 未優於 B5，或跨來源方向反轉 | 先看量尺與來源有效性，再由正式 M57 定位；一次只修被指認的變因，以新 sealed future 再試。負結果也可完成該假說檢驗。 |
| 消融／替換某個記憶或狀態後 `P(Y)` 沒變 | 該變數缺少可觀察因果價值；移除、重定義或降級主張，不能只保留好看的節點。 |
| 第二人物需要大量人物專用規則 | 回到 person-independent state semantics；不能把 Uruha-specific patch 冒充通用架構。 |

### 9.4 Git／PR：安全的逐步命令

以下是**每項工作完成時**的範本，`<本卡實際檔案>` 是任務卡 review 後列出的具體檔名，不能把尖括號照貼執行，也不能用 `git add .`。不同 shell 指令分次執行並檢查輸出。對 P4-BD，**freeze commit 必須早於首次正式模型呼叫，結果另 commit**。

P4-BD 具體分成兩個不可合併的提交邊界：**A. freeze** 僅包含事前新題／gold／評分契約／門檻／測試及 `CURRENT_TASK.md` 的 freeze 記錄；完成設計審查、測試與 staged diff 核對後 commit，記下 SHA，才准跑正式模型。**B. result** 保留該 SHA 不 amend、不改 gold；正式一次執行後，逐檔 stage runner／原始輸出／FAIL 或 PASS 分析／卡片進度，另 commit。可以在 A 後先推送，再執行 B；每次推送前都重新核對遠端 SHA 與 PR head。若選擇 A、B 後一起推，兩個 commit 仍須在 Git history 中保持清楚且模型呼叫的紀錄必須引用 A 的 SHA。下列命令的 commit message 僅示範 A，B 需要反映真實結果。

```bash
cd /Users/jerrychang/Desktop/uruharemake2_worktrees/persona-data-provenance
git status --short --branch
git rev-parse HEAD
git branch --show-current
git ls-files -u
git ls-remote --heads origin codex/v2-15-pragmatic-research-showcase
gh pr view 435 --repo jerry3816111/uruharemake2 --json state,headRefName,baseRefName,headRefOid,url
```

只有分支仍為 `codex/v2-15-pragmatic-research-showcase`、無衝突、PR #435 仍 OPEN 且 head 正確，才在此 checkout 工作。先記下遠端 SHA；若遠端被其他工作推進，保留本地狀態並查差異，**不要**自動 force push、pull/rebase、reset、clean 或 stash。原始 dirty checkout 不碰。`output/graduate_application_report/` 目前是**既有未追蹤使用者成果**；每次都確認它沒有進入 staged diff。

```bash
git diff --check
git diff --stat
git diff -- <本卡實際檔案>
git add -- <逐一列出本卡實際檔案> CURRENT_TASK.md
git diff --cached --name-status
git diff --cached --check
git diff --cached
git commit -m 'Freeze P4-BD role-aware evidence span evaluation'
```

上面 commit 訊息只適用 P4-BD freeze；實作與結果改用反映該結果的訊息。提交前逐檔檢查來源、資料 hash、測試命令、gate、證據種類與隱私；若 staged 內含無關檔案就**停下核對**，不要盲目 commit。正式失敗也 commit 原始結果和 FAIL 報告，不覆寫舊 SHA。

```bash
git rev-parse HEAD
git ls-remote --heads origin codex/v2-15-pragmatic-research-showcase
git push origin HEAD:codex/v2-15-pragmatic-research-showcase
git status --short --branch
git ls-remote --heads origin codex/v2-15-pragmatic-research-showcase
gh pr view 435 --repo jerry3816111/uruharemake2 --json state,headRefName,headRefOid,url
```

push 前的遠端 SHA 必須等於開始本次工作的預期 SHA；push 後遠端與 PR head OID 必須等於本地 HEAD。不可 force push，不建立無關新 PR，不因完成一項局部任務而自動合併大型 PR #435。`CHAT_CONTEXT_COMPACTION_2026-08-10.md` 第 9 節的「每個單元自行 merge」與「所有近期工作每週新增展示」是**較舊指示**；現在由 `AGENTS.md`、`DEVELOPMENT_WORKFLOW.md`、`LONG_TERM_GOAL.md` 及 `CURRENT_TASK.md` 的有限工作線、單變因與 PR 核對規則取代。

## 10. 可直接貼到新聊天室的啟動文字

> 請先完整閱讀 `/Users/jerrychang/Desktop/uruharemake2_worktrees/persona-data-provenance/NEW_CHAT_HANDOFF_2026-09-28.md`。不要要求我貼舊聊天室。依文件第 1 節核對 Git 與權威任務卡，保留 `output/graduate_application_report/` 和所有無關變更。先用中文說明你理解的研究目標、已證明的窄結果、正式未完成的 gate 與目前唯一 P4-BD 工作，並指出快照若已過期的差異；接著依 `CURRENT_TASK.md` 的最新範圍持續實作與驗證。不得把 M15、ToMBench 抽樣、synthetic、離線 compiler、Safari 個案或測試數外推成已證明人類方程式／全面優於強 LLM；正式 M55/M56 必須遵守真人資料和凍結授權門檻。

## 11. 完整查證索引

- 長期目標與工作順序：[`LONG_TERM_GOAL.md`](LONG_TERM_GOAL.md)、[`DEVELOPMENT_WORKFLOW.md`](DEVELOPMENT_WORKFLOW.md)、[`CURRENT_TASK.md`](CURRENT_TASK.md)、[`AGENTS.md`](AGENTS.md)。
- 歷史／架構／證據邊界：[`CHAT_CONTEXT_COMPACTION_2026-08-10.md`](CHAT_CONTEXT_COMPACTION_2026-08-10.md) §1–4、§9；[`research/full_completion_roadmap.md`](research/full_completion_roadmap.md)；[`research/hypotheses.md`](research/hypotheses.md)。
- 長篇成果與圖像：[`output/graduate_application_report/UruhaBrain_研究所申請_專案成果報告_2026-09-27.pdf`](output/graduate_application_report/UruhaBrain_研究所申請_專案成果報告_2026-09-27.pdf)，同目錄 DOCX 與 `figures/`；目前未追蹤，需在同一 worktree 讀。
- 當前最小反例與資料：[`analysis/p4_bc_raw_dialogue_typed_spec_failure_2026-09-27.md`](analysis/p4_bc_raw_dialogue_typed_spec_failure_2026-09-27.md)、[`analysis/p4_bc_raw_dialogue_typed_spec_evidence_2026-09-27.json`](analysis/p4_bc_raw_dialogue_typed_spec_evidence_2026-09-27.json)、[`analysis/p4_bb_typed_action_compiler_acceptance_2026-09-27.md`](analysis/p4_bb_typed_action_compiler_acceptance_2026-09-27.md)。
- 真人 gate 與正式研究狀態：[`analysis/m55_real_person_longitudinal_readiness_2026-09-01.md`](analysis/m55_real_person_longitudinal_readiness_2026-09-01.md)、[`analysis/m57_9_partial_status_2026-09-07.md`](analysis/m57_9_partial_status_2026-09-07.md)。

> 注意：使用者以前提供的 `RESEARCH_SPEC_FOR_CODEX.md` 不在此 Git checkout；若要引用它，需先核對先前使用者附件或本機 `/Users/jerrychang/Downloads/RESEARCH_SPEC_FOR_CODEX.md`，並以本文件列出的較新長期目標與當前任務卡處理衝突。

## 12. 本聊天室至今的決策脈絡：新接手者為何走到這一步

這裡保存的是**影響研發與驗證的決策摘要**，不是舊聊天室逐字轉錄；細節在上方原始報告與歷史交接。若新使用者指示與本摘要不同，先保留舊證據，再更新當前卡。

1. **像人與左／右腦原型**：使用者最初想還原「聽見 → 記憶 → 推理／情感 → 說話」；以一ノ瀬うるは作具體人物案例，需中／英／日輸入、自然日文人物回覆、長期記憶、VRM、Function Calling。早期 ToMBench、DailyDialog、Big Five 各測一部分，沒有一個總分可判定系統是不是人。
2. **拒絕只看表面回答**：使用者用「早上坐不住、腦子停不下來」指出同一句話可期待解法、陪伴、澄清或吐槽。因而加入語用假設、替代解讀、信心、下一輪預測、支持／反駁／未知與更正；一般使用者只看自然回覆，內部圖供研究核對。這不是用固定 prompt 自稱讀心。
3. **公開人物資料的界線**：Uruha 是公開可觀察行為的 reference-person／`θ` 案例，不是研究架構本體、真人身份或私人生命史。YouTube 等公開影片可以作**候選時序來源**，但須先核授權、來源、時間、說話者、刺激／反應邊界及 train/dev/holdout；不能把自動字幕任意 marker 或公開可看直接當訓練與重散布許可。
4. **一週展示與圖像化**：使用者曾要求旁觀者／老師看得懂、全圖像的 node flow、真實 Safari 外部瀏覽器；M1 Temporal Prediction Observatory 是一週版永久 checkpoint。後續必須持續前進，但不能為了新增頁面或 M 數移動 checkpoint，亦不能以模擬圖冒充真實 runtime flow。
5. **完整縱向問題**：使用者把願景收斂為「過去的記憶到當下狀態，再算未見未來行為」，允許負結果，重視同模型公平比較、強 baseline、預測先封存、之後才揭盲、消融與跨人物轉移。M54 把候選方程固定為機器可檢查契約；M55 真人人工真值是科學主張的前置依賴。
6. **長對話與對照要求**：使用者要求 50 輪及純 LLM 比較，因此不能只稱「記憶更好」。M12 顯示本系統相對最近 8 輪有 bounded recall 優勢，但與完整 transcript baseline 的 strict task 打平且成本高；P3 把完整共同歷史的 direct 和 deliberate 都當主要強對照。P3-C2 最終沒有達到事前優勢門檻。
7. **研發重於投稿包裝**：使用者後來明確把主線改為產品研發，研究只保留足以驗證的部分；每項支援工程需指出阻擋哪個交付 gate。若要寫申請／論文，必須揭露正負結果、資料不足和不能主張的部分，不能用漂亮網站或測試數代替。
8. **模型選擇不再綁型號**：過去有 GPT6 設計、GPT5 實作的任務卡模式，後改為任何模型都可按明確規格工作，但較低階模型是否能獨立完成，須用**新任務的接手實測**核對；不能因文件詳細就保證同等研發能力。系統 runtime 的 9B／4B／0.8B 資源實驗與 Codex 開發模型是兩個不同問題。
9. **近期收斂到 raw dialogue→action**：多個 P4 Safari 例子證明來源鏈可以局部接通，卻在真正交付動作時因 M45／M46 失敗或 timeout。P4-BA 用 2×2 小模型配置測後四 arm 全 FAIL；P4-BB 將正確 typed spec 編譯成動作 6/6；P4-BC 檢驗原始對話抽 spec 仍 FAIL；因此目前只做 P4-BD evidence span 評價，不把離線 compiler 偷接正式產品。
10. **研究所成果報告與新聊天室交接**：2026-09-27 產出 33 頁繁中成果報告、DOCX 與 PDF，逐頁視覺檢查；該 `output/graduate_application_report/` 仍未追蹤，需保留。2026-09-28 建立本交接文件，目的是讓新聊天室無需舊聊天逐字內容即可正確接續當前研究與開發。

## 13. 較低階模型的接手驗收卡

文件越完整，仍越不能保證未知未來的實驗成功。接手者在修改任何檔案前，應先只靠本文件與權威卡回答以下問題；若答錯就先重新讀對應原始證據，不開始正式生成。這是一個**閱讀／決策演練**，不是產品、人評或模型研發同等品質證明。

| 檢查題 | 必須回答到的要點 |
|---|---|
| 研究主問題是什麼？Uruha 是什麼？ | 截止前可觀察歷史→候選狀態→未見行為機率；Uruha 僅公開資料人物參數，不能補私人真值。 |
| 現在唯一可執行工作？第一個 commit 應含什麼？ | P4-BD；新題、annotation／role-aware 契約、hard negatives、雙標註 proxy、完整 gate 與任務卡，**先 freeze commit**，模型正式 call 在後。 |
| P4-BC 的結果和 P4-BB 的結果可否合併成產品 PASS？ | 不可。BB 是已給正確 typed spec 時的 6/6 離線 compiler；BC 28 calls 但兩模型 strict exact 0/6、完整 FAIL，未接產品。 |
| 97.5% ToMBench、M15 +16pp 各代表什麼？ | 前者 40 題混合 symbolic／LLM 的抽樣；全量 deterministic 版本分數不同。後者僅 qwen3.5:9b 的 PUB T13 指示語窄結果。 |
| 若 P4-BD role-aware span PASS，可否放寬 20s／直接改 slots／接 Safari？ | 不可；同一單元其他 gate 保持，canonical slots 和產品接線各是之後獨立實驗。 |
| 正式過去→未來實驗為何沒跑？ | 最後封存 V7 兩人各 0/18、真實 rows 0/30；M55 gate 前 M56 沒有正式生成／結果，M58 無授權；私有 ledger 最近未重讀。 |
| 若 system 對強 LLM 沒勝或成本較高？ | 保存負結果和資源，定位單一原因、做新資料消融或簡化；不弱化 baseline，不用曝光題追分。 |
| Git 要在哪裡、怎樣推？ | 只在 `persona-data-provenance`；逐檔 add、檢 staged diff、freeze/result 分開 commit、推既有 branch、核對 PR #435 head；保留未追蹤成果報告，不碰原始 dirty checkout，不強推／自動 merge。 |
| 什麼才算真正完成？ | 產品可用與研究結論各有完整 gate；正式真人、holdout、同模型公平結果、因果消融、跨來源／第二人物及人評須逐層出證據。到 M62 或至多 M75 可給可信的正或負結論，不能預定會解出真正人腦。 |

演練通過只表示**能讀懂這張交接卡**。要說「較低階模型能獨立完成同等工作」，還要讓它在**未完成的新小任務**實際跑 before、正確選擇單變因、保留資料凍結、通過受影響測試、形成可核對 diff 與結果，記錄是否需要強模型救援、耗時及成本。任何正式研究 gate、設計審查或外部真人依賴都不會因讀懂文件而消失。

2026-09-28 進行一次 `gpt-6-luna` **只讀**接手演練：只給本文件、不給舊聊天或其他 repository 檔，要求回答當前 gate、freeze、P4-BB／BC 邊界、單變因、過去／現在／未來時序、真人依賴、資料禁忌、Git 和兩次修正後的處置。9 類問題均能正確指出文件中的要點；模型另外找出三個歧義：P4-BD 數值 gate 尚未定案、雙規則不等於雙真人，以及 freeze／result commit 的分界；已在第 8.1、9.2、9.4 節補明。這是**文件理解測試**，沒有讓該模型寫程式、跑正式題或證明它能獨立完成未來任務。
