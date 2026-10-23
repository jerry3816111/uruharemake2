# P4 直接回覆行動：同載體 planner handoff 前瞻消融

日期：2026-10-23。狀態：**設計／題本凍結在本項程式與模型輸出之前**。作者自寫開發題，不是正式 holdout、盲式人評或「使用者真的被理解」標註。舊 `a0` 首對因模型／參數不同而 strict FAIL，永不重播追分；`a1–a5` 不移作新題。本卡經獨立只讀設計審查，不能改弱控制組或在看模型答案後改 gold。

## 問題、可識別效應與邊界

舊 opt-in M29 gate 在真產品把直接請求保留為來源綁定證書，並確實讓路由到 full planner，但證書只在 M29 trace，`LeftBrain.think` 仍只讀原文。因而「有沒有把可觀察的直接回覆行動送到選句階段」尚未測到。首對 baseline 已說 `頑張ったね`；新工作不得把它描述成完全不會労い。另一觀察是 baseline `memory_db`、system `session_db`，靜態路徑為 Web Reset Session 會切換 DB，私有紀錄可證 reset 初始化時序不同，但缺 callback 審計，不指認操作者；本項先把 reset／active DB 對齊。

**唯一操縱：**兩臂都安裝相同 M29 direct-act admission gate、同一 full planner、相同原始輸入、同一公開人格、空的同型隔離 DB、相同 guard／graph／選句／writeback。控制臂從原文規劃，不把已准入的 direct-act certificate 交給 planner；處置臂只把同一張證書的 `requested_act`、當輪 source/cue digest 和「不推測未給的心理、不要只重述事件」界線作為內部 planner 約束。不得塞固定日文答句或新增私人狀態真值。若 source digest、角色、M29 准入、實際 full-planner 路由任一不合，處置失效閉鎖。這估計的是**同載體的 certificate handoff 效果**，不是舊 default M31→新系統的 total effect，更不是完整 UruhaBrain 對純強 LLM 的優勢。

本項只允許在 `uruha_brain_mac.py` 的 M29→當輪 transient planner context 與 LeftBrain full-planner prompt／plan trace 兩個 opt-in seam、現有 P4 direct-act controller 的受控 child-env、新聚焦測試、前瞻資料／SHA／報告／`CURRENT_TASK.md` 改動。M31/M32、M25 政策、guard、資料庫記憶語義、安全路由和已凍結舊題不改。相同 M29 gate 仍應讓正例進 full planner；若不能，先零模型停下。非正例的處置旗標不可覆蓋 M33/low-road／安全權限；內部 trace 不能假裝可見答句或真人偏好。

## 事前題本與硬 gate

全新 `datasets/p4_direct_reply_act_planner_handoff_probe_2026-10-23.json` 的 `b0/b1` 是明示短労い／鼓勵，各跑 control 和 treatment 一次；`b2–b6` 純敘事、第三者引述、否定、衝突雙要求、敏感請求只跑 treatment，總上限九個 fresh arm-turns。逐字對舊 P4 direct-act 題與本項題不得碰撞；比對只能用事前 frozen contract。正例：兩臂同 full planner、相同模型 `qwen2.5:7b`、temperature `0.1`、產品 compact-plan `max_tokens=256`、同一 API/transport／模型 digest、同一 20s planner timeout；top-p、seed、context 未顯式指定時，兩臂均保持同一 Ollama 預設並在 receipt 標 `unspecified`，不能假稱固定 seed。除處置的內部約束段落外，精確 planner request 的角色、原文、人格、記憶、規則及 output schema 須相同；模型可能非決定性，兩個配對只是 bounded developer cases，不用單次差異估計普遍效應。新段落增長的 prompt token 是介入成本，要實量報告。

零模型先 capture 兩臂真正送到 compact proxy 之後的 planner request，證明 model/temperature/max_tokens/response_format/timeout 與未操縱段落相同，處置只多 source-bound act 約束；capture trace 證 certificate 被 plan 使用而不只寫在圖上。受影響舊 M23/M25/M29/M31/M32、P4 接線、日文、安全、記憶、graph 回歸須過。fresh product 每臂新 0700 root、官方 ONNX 私有離線預熱、同 PID zero-turn ready、T0 空 DB／profile 0；Safari 兩臂一致**不按 Reset**，在 send 前核 active DB 是 `memory_db`／runtime autonomous tick 0，若任何 reset 或狀態漂移則 fail-closed，不補送。正式 UI 原文各一次、0 retry，核 native graph/泡泡、private raw、guard、utterance、episode 同字同 ID、日文/persona/source/safety，兩臂真 route/trace 與 DB path。若保存不了 native PNG/AX，`saved-visual=FAIL`，不能以 JSONL 假代。

正例須短自然日文執行明示 act，而非僅事件 echo；未給出的疲勞、成績、私密動機不得斷言。負控不得取得 direct-act handoff，安全題須維持保護路由。任一來源／模型設定／資料／route／writeback／安全／預設 20s user wait hard gate 失敗，整批 strict FAIL；不事後刪題改門檻。最多九 arm-turns、每臂最多三次模型生成、全批最多 20,000 provider tokens，逐臂列 provider/向量 calls、latency、token、JSONL bytes；超上限即停。無真人主觀真值時，「比較好聽／被理解」只能標待人評。

即使 B↔C 的狹義消融成立，仍需另做 A=default M31、B=同 planner 無 handoff、C=同 planner 有 handoff 的 prospective total-effect 設計；A↔C 必須逐項對齊模型權重 digest、temperature、top-p、seed、context、`think`、輸出 cap、API/transport 及硬體才可稱同設定。其路由 prompt/schema 的不同是總效果的一部分，不得冒充單獨 certificate 效果。正式強 LLM/temporal holdout／真人被理解感／跨輪個體預測仍 pending。
