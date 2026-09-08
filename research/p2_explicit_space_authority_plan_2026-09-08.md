# P2 Explicit Space Authority：前瞻工作卡

日期：2026-09-08
狀態：實作前凍結的產品修正計畫；不是正式研究 preregistration。

## 修改前問題與因果位置

隔離產品控制為 `今日はただ聞いてほしい。` → `違う。今日は一人にしてほしい。`。第二輪的 semantic route 與
pragmatic label 都已知道這是明確修正，但 M18 的六種 response policies 沒有「尊重要求並停止互動」這個 action。
`_explicit_target_policy` 因此回傳空值，ordinary `calibrate_need` 勝出；personhood correction 又把承認誤讀與該 policy core
串接，最後輸出無來源的「沒睡／想事情」二選一，並把它保存為 pending prediction。

修改前證據：`analysis/p2_explicit_space_authority_prechange_gap_probe_2026-09-08.json`。根因不是 qwen 生成或 active
validation，目標輪為 0 model calls 且 active validation 沒有新增問題。

## 本次唯一核心變因

新增 product-only **observable explicit-space response authority**：把中／英／日明確的第一人稱／祈使式「讓我一個人、
先別理我、leave me alone、I need some space、一人にして、放っておいて」分類成 `respect_space` action。它是可直接觀察的
當輪互動要求，不是對情緒、原因或私人心理的推測。

產品 adapter 在既有 candidate decision 之後、surface 與 memory writeback 之前取得 action authority：保存舊 candidate 為
rejected proposal，改用短日文 acknowledgement-and-withdraw core，並阻止舊 `calibrate_need` 成為 pending prediction。
既有 visible Japanese/persona guard 仍執行；runtime graph 顯示 observable evidence → legacy proposal → authority → final。

## 不可改邊界

- 不改凍結 M18–M54 source、六政策正式研究結果、模型、prompt、temperature、token budget 或正式資料。
- 不把「想一個人」推成悲傷、生氣、睡眠不足、拒絕關係或長期溝通偏好。
- 不寫入事實性長期記憶，不將暫時 space request 學成一般 `listen_presence` 或 `calibrate_need` 偏好。
- 不攔 safety、identity、factual/memory、boundary 等 protected route；含風險訊號時既有安全處理優先。
- 否定式「我不想一個人」、第三人稱引述、詢問句中被引用的片語、字詞解釋與一般談論不得命中。
- 不同批修 quoted-source／cross-session feedback association。

## 預先成功條件

1. source-disjoint 中／英／日明確 space request 都產生 typed span geometry/digest，選中 `respect_space`，最終只用自然日文
   短句承認並停止追問；不得出現 sleep／thought、listen、advice 或另一個問題。
2. 帶明確 correction cue 時承認剛才讀錯；沒有 correction cue 時不虛構先前誤解。today／now／unspecified 時間範圍只依
   當輪可見詞選擇，不擴張成永久偏好。
3. negated、quoted／third-party、metalinguistic、protected 與無關輸入逐欄保留原路徑；first-turn ordinary listen/support
   不能被攔截。
4. legacy candidate 與 M27 outcome history保留在 trace，但本輪不得新增 legacy pending prediction、fact write 或 model call；
   既有 input model 不被就地改寫。
5. 圖中出現唯一且有連線的 `explicit_space_authority_p2` node，含 evidence digest、被拒絕 policy、selected action、surface
   digest、claim boundary；不複製 raw user dialogue。
6. 重跑受影響相鄰測試與同一 5-session 本機控制。目標輪改正，非目標差異逐一列出；Safari 若工具仍拒絕，維持 pending。

## 失敗與分支

- 若 surface 又被 M23/M39 改回 clarifier，修正 product adapter 的 authority ordering，不擴大 grammar。
- 若 M27 仍留下 `calibrate_need` pending，不能只修畫面；必須在 writeback 前使 legacy plan application 明確 not-applied。
- 若否定或引用句誤命中，先收窄語法和 source geometry，不加入更多 surface 模板。
- 若安全 route 被攔，視為嚴重回歸並停止；不得把 product convenience 放在安全 contract 之前。
