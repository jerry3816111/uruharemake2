# V2.14 同模型受控比較報告

日期：2026-08-11  
狀態：**frozen holdout fresh generation 完成；人類盲評未完成，因此禁止宣稱 system 優於 baseline。**

## 1. 比較問題

同一個 `qwen3.5:9b`、相同公開 Uruha 表達 contract、相同使用者輸入、temperature 0、seed 20260811、相同 output budget 與同硬體下，比較：

- Baseline：只用目前 dialogue 直接生成，沒有 structured cross-turn hypothesis/prediction/verification/calibration。
- System：同模型與同表達 contract，額外使用 V2.13 pragmatic/other/self/relationship/persona/action/learning state。

研究問題是 human pragmatic understanding；Uruha 是實驗人格，不是研究目的，也不是本人。

## 2. Freeze 與公平性

- 18 個 source-disjoint holdout cases，中文／英文／日文各 6 案，每案 3 輪，共 54 pairs、108 outputs。
- 現象包含婉拒、間接求支持、表面同意但保留、高喚起歧義、偏好撤回、關係訊號與澄清。
- 在第一個 scored output 前凍結 holdout、preregistration、V2.13 mechanism/functional sources、runner 與 human-eval source；lock 檔為 `configs/v2_14_human_pragmatic_holdout_lock.json`。
- tokenizer preflight 為兩條件補齊同一 input-token budget；54/54 pairs 的實際 `prompt_eval_count` 差為 1，低於 preregistered gate 2。
- normalizer 只移除外層引號與空白，不重寫內容；所有 transport failure 與輸出均保留。

## 3. Fresh-generation 結果

| 指標 | Baseline | System |
|---|---:|---:|
| 可見日文／人格 contract 通過 | 9/54 | 42/54 |
| 自動 semantic proxy 通過 | 6/54 | 30/54 |
| Transport errors | 0 | 0 |

System 各語言 visible contract / proxy：

- 中文：16/18、12/18
- 英文：12/18、7/18
- 日文：14/18、11/18

System proxy 依現象：ambiguous arousal 7/9、reserved agreement 7/9、indirect support 6/9、indirect refusal 5/9、clarification 2/6、preference retraction 1/6、combined relationship cases 2/6。

System 的 12 個 visible-contract failures 主要是敬體 11 次與「私」1 次；baseline 主要是敬體 45 次，另有引號、私與接客服務語氣。這只表示 frozen contract 的自動檢查差異，不表示人類偏好。

## 4. 可展示的對照

中文婉拒 turn 1：

- Baseline：「うちはその日でも大丈夫ですが、もし無理ならまた連絡してくださいね。」
- System：「行く気があるならまだしも、断りづらいだけでしょ？違うならそこだけ言ってよ。」

下一輪使用者確認真正卡住的是拒絕方式後，System 回：「やっぱ予定より断り方の方で詰まってたんだな。分かった。」內部 trace 將該 pragmatic dimension 標為 supported，保留原假設與更新紀錄。

高喚起歧義案例：System 先問「楽しみな方か不安な方か」，使用者說不是不安而是期待時，回覆「そっちだな、読み違えた」，並在 trace 將 general hypothesis 標為 contradicted、降低 confidence。

這些是具體反例展示，不足以證明所有案例或所有人都更喜歡 System。

## 5. 不能忽略的弱點

- generic active-validation 會在與當輪目標不相容時接管回覆。
- relationship／clarification 的修正常只說「読みすぎた」，沒有完整採納更正內容。
- preference retraction 的內部 withdrawn trace 正確，但可見 surface 常過度敬體、無關或沒有把撤回說清楚。
- System 仍有 12/54 visible-contract failures、24/54 proxy failures。
- proxy 是關鍵詞／契約檢查，不是「被理解感」或人類偏好的替代指標。

## 6. Claim gate

目前 raw result 明確記錄：

- `human_preference_supported = false`
- `system_better_than_baseline = false`
- 原因：尚無至少 3 位完整、獨立的 blind raters。

只有三位評分者完成 54 個盲化 pairs，且 felt-understanding preference、revision quality、overinterpretation 與 bootstrap CI 全部通過 preregistered gates，才可說：「在這個 frozen 模型、holdout、persona contract 與硬體條件下，System 優於 baseline。」即使通過也不能外推為意識、讀心、普遍人類理解或 production readiness。

## 7. 可重現 artifacts

- Raw：`analysis/v2_14_human_pragmatic_comparison_raw.json`，SHA-256 `9005d3495d90e4500409bb1304cc5b68ab62edc134e6b200ecb0fb91a7ed3c22`
- Blind packet：`analysis/v2_14_human_pragmatic_blind_packet.json`，SHA-256 `ab8059fbbd36d2404e3cfe8b110a3ecb7d1b060bd73182969f1b9934b97c1624`
- Blind key：`analysis/v2_14_human_pragmatic_blind_key.json`，SHA-256 `1ed0f93c4dede35888e5a8200df85c94466bc5c01964218c157f477d5ea630a3`
- 空白 rating templates：`analysis/v2_14_rater-01_ratings.jsonl`、`rater-02`、`rater-03`

V2.14 研究證明就緒度約 **60%**：fresh controlled generation、blind packet 與 analyzer 已完成；三位獨立人評、統計 gate 與預註冊 ablation 尚未完成。最終「可泛化的人類語用理解」理念約 **25–35%**，因為還缺更廣語境、真實語音聲學、多樣評分者與長期外部效度。
