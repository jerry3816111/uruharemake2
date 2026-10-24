# P4-AX compound feedback/request split: offline PASS

P4-AX 在事前凍結資料與 gate 後完成一個 bounded、additive 的語用分解：當下一輪同一句話同時明示「上一輪先確認需要是對的」與「這一輪改要一個具體方法」時，把兩者保存為兩個可驗證變數，而不是讓後半句覆蓋前半句。

## 為什麼需要這一層

P4-AW 的正式 Safari T2 有 exact previous-action receipt，也成功辨識本輪 `solve_regulation`，但 P4-AT 將整句判成 current request only，previous outcome 變成 unknown。P4-AU 因而正確拒絕 prior-source handoff。這表示「知道使用者現在要方法」不等於「知道使用者也明確肯定了上一輪澄清」。

P4-AX 只補這個斷點。它要求：

- 既有 M44 pending receipt 與 P1 identity 完全一致；
- performed action 是上一輪的 `calibrate_need`，時間嚴格早於當輪；
- 來源是 direct user，不是第三人報告、引用／測試句或假設句；
- 同一個 bounded clause 同時有 clarification/checking action、第一人稱 response-need object 與正面評價；
- 既有 current-request routing 已獨立選到 `solve_regulation`。

它不自己建立 current request、不放寬 P4-AU、不改 candidate ranking，也不跳過 M46/M45。

## 第一次實作失敗與唯一修正

第一次結果為 development=`0/1`、fresh positive=`9/9`、controls blocked=`10/12`、predecessor=`6/6`。三個問題被完整保留：offline harness 未傳入真實產品已有的 M25 base-request trace；舊 direct-source guard 沒覆蓋該日文第三人稱報告形態；中文假設標記後使用錯誤的 word-boundary 判斷。

唯一 informed correction 只讓 harness faithful 地傳入 released M25 trace，並修正這兩個 bounded source guards。沒有改資料、gate、正例 grammar、舊 P4-AT 結果、request routing、P4-AU、M46/M45、prompt、model、memory 或 visible reply。

## 固定結果

- exposed development=`1/1`；
- 全新中／英／日三類複合正例=`9/9`；
- third-party／quoted-meta／generic-confirmation／hypothetical controls=`12/12` 維持 unknown；
- 舊 P4-AT question-based support=`6/6` core fields 原樣保持；
- 所有 16 個被支持案例都有 exact receipt identity，current request 仍是 `solve_regulation`；
- false support、P4-AT predecessor mutation、P4-AU bypass、candidate rerank、visible change、model call、factual-memory write、raw-dialogue trace、private truth、完整 fresh 字串 patch 全為 0。

focused=`13 passed`；P4-AT～AX affected=`74 passed`。port `7888` sandbox product preflight=`ready`，0 model／Safari／VRM-tool operation。

## 能與不能主張

這支持一個窄的工程論點：有限的中英日可觀察語法可以讓 exact previous-action feedback 與 current response request 在同一輪並存，並在 false-link controls 上 fail closed。

它不證明 open-domain 語用理解、真人偏好、建議有用、被理解感、人類方程式、自然分布泛化或優於 matched strong LLM；也沒有修掉 P4-AW 正式 T2 的獨立 model timeout。下一步必須是全新的 Safari pair，不能重跑已曝光題目。
