# P3-C1 controlled context-flip lane plan

日期：2026-09-20

## 為什麼改走這條線

P3-B72 已證實先前的 YouTube caption-marker proxy 不足以支撐 system advantage：八列雖然 row winner 偏向
system，但 actual-label probability、top-1、Brier 與 log loss 方向衝突，第三來源四列全部掉進同一 default label。
因此不能再增加同類影片，或修改看過結果的 marker 追分。

P3-C1 改做一個獨立、可控制且可反駁的語用機制實驗。它不讀新的 Uruha 影片、字幕或未來結果，也不替代真實人物預測。
它要回答的較窄問題是：**同一句話的可觀察上下文改變時，顯式、可修正的語用狀態是否比強 direct LLM 更準確地改變
解讀，同時不會在字面情境中想太多？**

## 實驗單位與方法來源

每個 pair 只有一個 byte-identical surface utterance，另有兩個 context：

1. `literal_control`：可觀察證據支持字面解讀；
2. `pragmatic_flip`：同一句話在另一個上下文支持隱含解讀。

這對應 DRInQ 的 same-question/surface controlled context variation，以及 PaCE 的 pragmatic context-flip 與
overinterpretation control。PUB 的 implicature、presupposition、reference、deixis 只用來做 coverage 分層；PUB 的 MCQA
accuracy 不被改稱真實人物回應指標。所有題目都是文字；聲學資訊固定為 `unavailable`。

資料含 18 個 surface families、36 個 variants；train/dev/holdout 各 6 families，中文／英文／日文各 6 families。
split 單位是完整 surface family，所以同一句話的兩側不能跨 split。這批資料由開發者撰寫，holdout 在模型執行前凍結，
但不是獨立真人資料，也不是私人心理真值。target 是 `LITERAL_READING / PRAGMATIC_READING / UNCERTAIN` 的分布，保留
多重解讀空間。

## 公平對照與單一變因

兩組都使用：

- 相同 `qwen3.5:9b`、本機 Ollama、硬體與完整可觀察輸入；
- 相同 interpretation options、Uruha 公開人格表達邊界與自然日文最終回覆要求；
- temperature 0、seed 260920、top_p 1、num_ctx 8192；
- 每個 item 一次 call、completion ceiling 384；實際 prompt/completion tokens、延遲與失敗都必須記錄；
- condition order 依 pair 平衡，禁止只讓某一組永遠先跑。

`BASELINE_DIRECT` 是強 direct baseline：它取得完整 context，也可用模型原本的推理能力；不得限制成只看字面。
`SYSTEM_PRAGMATIC_STATE` 的唯一介入，是在同一次、同總 budget call 中顯式輸出可觀察的 literal、intent、stance、relationship、
implicit need/action tendency、alternative、unknowns 與 confidence，再給出相同的解讀分布及日文回覆。system 多使用的 state
token 完整計入相同 384 ceiling，不能當免費計算。

## 指標、成功與失敗

Primary：holdout mean multiclass Brier，事前最小效果量為 system 比 baseline 低至少 `0.03`。

同時必須通過兩個 guard：

1. system 的 literal-control overinterpretation rate 不得高於 baseline；
2. system 的 paired context-flip top-1 accuracy 不得低於 baseline。

另報 mean log loss、單列 top-1、context delta direction、pragmatic underreading、錯誤但信心 `>=0.70` 比率，並依語言與
phenomenon 分層。所有指標都報，即使方向互相衝突。若 primary 未達 0.03、任一 guard 退步、model batch 不完整或 schema
失敗，均保存負／mixed 結果；不得削弱 baseline、修改已曝光 holdout target 或反覆調 prompt。

## 凍結與後續 gate

P3-C1 的工作只到 contract、dataset/targets、無 target 的 prediction packet、輸出驗證、metric pass/fail fixture、測試與 hashes。
本步 model/network/Uruha source/future/human label/production write 都是 0。C1 完成不自動代表 system 較好。

後續若另行執行，順序固定為：先確認 train format，再用 dev 暴露介面問題；所有介面修正必須在 holdout 前完成並重新凍結。
holdout 一旦執行就只跑一次，結果正負均保存。自然日文只在這條線做語言 contract；felt-understanding 仍需另行盲化真人評價，
不能用本批 developer-authored distribution 代替。

## 可宣稱與不可宣稱

即使 P3-C 後續通過，也只能說：在這批受控 multilingual context-flip proxy 與固定模型／資源下，顯式語用狀態顯示出較好的
context sensitivity，且沒有增加已量測的字面過度解讀。它不能證明已解出人腦方程式、理解私人心理、預測一ノ瀬うるは未來回應、
具有人類偏好優勢或全面勝過強 LLM。
