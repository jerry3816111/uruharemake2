# P4 compact planner taxonomy：d1 路由可識別的新診斷

事前凍結於任何 d1 模型生成前。舊 c0 的 compact `unexpected fields` 未知 subtype；d0 送出前 tick1 strict FAIL 且 M18 fast path／0 generation，兩者均保存原判、不重播。d0 字句不是目前 direct-act 的准入形態，還含會讓 M29 `not_candidate` 的 `じゃなく`；固定 `calibrate_need:v1` 追問不能拿來評估 compact parser。此次只以新的作者開發題檢查已實作的 raw-free failure-code 接線，**不改認知 code、model、prompt、validator、baseline 或 gold**。

## 唯一可歸因變因與 before

新 source-only d1 原文在 `datasets/p4_compact_planner_failure_taxonomy_d1_probe_2026-10-23.json`；與舊題逐字碰撞 0，非正式 holdout。它保留單句可觀察的工作進展與直接日文 `今は一言だけ励まして。`，避免 d0 的兩個不准入形態。對此題不把使用者情緒、私密意圖或真實偏好當事實；可見 contract 只是自然日文短句鼓勵、不得改追問睡眠／煩惱或編造背景。

新診斷只問：同一既有 `qwen2.5:7b`/temperature 0.1/OpenAI-compatible `json_object`/compact256/20s 接收到的回覆若被 strict parser 拒絕，新固定類別是否出現在私有 trace；若沒有格式失敗，只記 `non_reproduction`。產品與零模型都固定 `--direct-act-arm control`，真 trace 需 `arm=control`、`status=control_no_handoff`、`planner_prompt_injected=false`；不能誤開 treatment 而混入 certificate prompt。d1 相對 d0/c0 是**整句新輸入**，不能歸因於其中某個詞，也不能用單輪比較格式失敗率。不得因 d1 改變三候選契約、加 retry、保存 raw prompt/reply、重送 c0 或 d0。最多一個真 Safari turn、0 retry、最多 3 generations／2000 provider tokens／20s user wait；超額或帳本缺失停。

## 先零模型 go/no-go，再產品

1. 核此前 product SHA 13/13、Git status 和 d1 exact-string collision。用隔離 fake `create`／`_IsolatedContractBrain` 跑完整 `run_turn_debug`，而非只驗 regex：要求 direct certificate=`brief_encouragement`、M29 veto、M33 不接管、handoff 符合、M18 **不**接管、M21 `full_planner`、compact proxy 確實收到同一 `qwen2.5:7b`/0.1/256/json_object/20s request。測試若不通，**不啟新產品服務、不改題後假稱同一次 d1**；保留此設計失敗並重審。
2. 只在第 1 步過時，新 0700 root、空 DB、7925 空埠、官方 ONNX 私有離線預熱、same final PID ready、本機模型 digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`。Safari 只開本次新 tab、不可 Reset；縮短 brain ready→Send 時間，避免 45s idle tick。**複製 Tpre 後立刻對複本解析/assert**同 PID/session、`memory_db`、reset0/tick0/finish0、空 DB/log，再按 Send；不通即不得送，記 strict FAIL。Tpre→Send 目標 ≤10s，需另有 click 時戳才能稱精確測量；沒有就明列限制。外部 preflight 與 UI click 非原子，故 Send 後立即獨立 Tpost 還需同 PID/session/DB/reset0/tick0/finish1、episode1/profile0；任何背景 tick 或 DB 漂移即 strict FAIL，不拿 `writes=0` 放行，也不換 root 補送相同題。收據是在事件後發布、沒有自身時間戳；即使 Tpre/Tpost 均 tick0，也只證既有收據協定下的觀測，不能聲稱 click 瞬間的原子 live-state 證明。若需要更強證明，須另立同鎖取樣的測量改動，不得追認本題。
3. 真輪核 Safari 泡泡、原生 node graph、JSONL 的 route／compact audit／guard／utterance／writeback／compute receipt。若 graph 不是 `full_planner` 或 compact 未收到請求，產品診斷不成立，即使可見回覆好看也記 FAIL。若收到且格式失敗，分類碼只許 fixed enum／bounded counts，不能洩模型文字/key；若收到且有效，記未重現 c0，不反推 c0 subtype。可見日文、來源支持、成本、隔離與 saved-native-visual 各自判定，不能用零模型或 JSONL 代替 Safari PNG/AX。服務結束只 planned stop 自己 PID、只關自己新 tab；保留原件 SHA。正式人評、temporal holdout、全系統強 LLM 比較及 Goal 完成不由本題證明。
