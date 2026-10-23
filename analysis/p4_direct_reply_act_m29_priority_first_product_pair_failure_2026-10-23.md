# P4 直接回覆行動優先權：首對 Safari 真輪失敗與提前停止

日期：2026-10-23。判定：**凍結八臂驗收 strict FAIL／同模型比較不成立；已完成 a0 baseline 與 a0 system 各一次，a1–a5 未送。** 這不是正式 holdout 或人評，不用它主張系統優於／劣於強 LLM。事前設計／六題於 `6533026`、產品程式／10 SHA 於 `74b94b2` 先推既有 PR #435；真輪後 SHA 10/10 仍相符。舊 `retention0` 不重播。

## 隔離與當輪可見事實

兩臂各有不同 controller-owned 0700 私有 root，baseline `uruha-product-8rcgdq62`，system `uruha-product-050jb0ki`。各自複製官方 ONNX 83,178,821-byte archive（SHA-256 `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3`）及六個 extracted files 為私有 inode；各一次 384 維 finite embedding 預熱，socket-connect 封鎖器觀察 0 下載嘗試。各 root 先做零輪同 PID HTTP-ready、兩 DB embeddings 0、planned exact stop，再用新 PID 啟動產品，T0 兩 DB 仍 0。readiness 曾在 listener 尚未綁定或 HTTP 尚未 ready 時回暫時錯誤，只重查原 PID，沒有重新啟動。Safari 每臂只開一個新分頁（52→53）、核同一凍結原文後按 Send 一次／0 retry，觀察後只關該新分頁（53→52）。兩產品 PID `83280`／`84671` 均 exact planned stop、port 7894 vacant；原有分頁未關，正式 DB 未碰。

共同輸入：`夜、銀の栞をしまった。今日は頑張ったから、今は一言だけ労って。`。兩臂 final Safari 泡泡＝私有 JSONL `assistant_reply`＝日文 guard final＝blackboard utterance＝隔離 episode 原文。各 root 只有一行 0600 私有 JSONL：baseline 1,067,787 bytes／SHA `c7c67327783b2b7f77848afb5fa9d6f43c91a29a379899f9945cf80001b4a71a`；system 1,065,182 bytes／SHA `2c75895fcbe10ce83d3cb573284454987d6eb7b8e21596b656902f18bf4aa530`。兩組 profile 0、episode 各 1；baseline episode 在 root 的 `memory_db`，system 在 `session_db`，兩者 T0 都空，但跨輪儲存位置差異尚未解釋。Safari 原生節點展開可見 baseline M29 `projection_required=true`、M31 接管；system M29 `direct_reply_act_precedes_literal_projection_p4`、`projection_required=false`、M31/M32 未接管、full planner；私有圖及 receipt item ID 每臂一致。原生畫面曾目視，但目前沒有可持久保存的 native PNG/AX，saved-visual gate **FAIL**，不能拿 JSONL 代替。

| a0 臂 | Safari 可見日文 | 實際生成 | provider tokens | M19 user wait | 其他操作 |
|---|---|---|---:|---:|---:|
| 未啟用新 adapter | `銀の栞はしまったのか。頑張ったね` | `qwen3.5:9b`／Ollama native M31，temperature 0、num_predict 280 | 537 prompt + 166 completion = 703 | 14.8094 s | 11 Chroma（10 query／1 add） |
| 啟用新 adapter | `今日はもう粘るな。疲れてる時は休む方が先だろ。` | `qwen2.5:7b`／OpenAI-compatible full planner，temperature 0.1、另一路 output contract | 1047 prompt + 89 completion = 1136 | 10.9453 s | 11 Chroma（10 query／1 add） |

兩臂都是 1 次生成、各 12 個 scoped calls、0 unscoped／other／failed，receipt attribution complete；上述 token 不是 embedding token、OS/TTS 或全管線成本。system −3.8641 s、+433 provider tokens 是**不同模型、prompt 與參數下的觀察值**，不是新機制造成的速度／成本效果。baseline 已出現 `頑張ったね`，不能說它只會重述事件；system 的「もう粘るな／疲れてる時は休む」帶較強休息建議，是否算用戶所要的労い、是否過度推測疲勞，沒有真人主觀標註，不用自評當真值。

## 硬失敗原因與後續設計審查

凍結計畫要求 a0/a1 使用**同一 `qwen3.5:9b`、相同生成設定／硬體與資源上限**。實際 M29 veto 讓產品由 M31 native verifier 改走 `LeftBrain.think`：前者預設 `URUHA_M31_SEMANTIC_VERIFIER_MODEL=qwen3.5:9b`（`uruha_brain_mac.py:155`，請求 temperature 0／num_predict 280），後者在 `uruha_brain_mac.py:9733` 固定 `qwen2.5:7b`／temperature 0.1。這是**路由帶來的模型與生成載體共同變更**，不是純 M29 單變因對照；零模型 fake planner 測試沒有也不可能證同模型。首對一經讀回即按硬 gate 停止，a1–a5 沒送、不追分，不將本次輸出當可比結果。系統原文到 full planner 及 M29 新 gate 接線是有限的真產品機制證據；回覆品質優勢、同模型公平性、泛化、跨輪記憶與主觀被理解感均未證。

下一個必要設計審查須先決定並凍結：是把**兩個分支共同的模型、推理選項與 token cap**接成可核對的 same-model execution（不能只改 M31 模型名卻留下 0 vs 0.1），還是改為同一 full-planner carrier 的 `direct-act certificate` 有／無對照，以隔離來源綁定的回覆行動使用。兩案都要保留 baseline 強度、來源邊界、相同 T0 可用資料、API receipt 和獨立產品效果評估；新題必須 source-disjoint、事前凍結，舊 a0 不重送追分。另查 baseline/system episode 落在不同隔離 DB 路徑的原因，再做跨輪公平比較。若只靠 prompt 追加安慰句、換更弱 baseline 或降低 gate，不能稱修正。
