# P2 Repeated Refusal Arbitration：前瞻工作卡

日期：2026-09-08
狀態：實作前凍結的產品修正計畫；不是正式研究 preregistration。

## 修改前問題與因果位置

隔離本機兩輪：

1. `考えとく。`
2. `また今度にしようかな。`

第二輪 qwen2.5:7b compact planner 已完成並選出低干預 direct core `また今度ね。`。但後續有兩層依序覆蓋：

- pragmatic attunement 再次把同一 `indirect_refusal` 暫定推測反射成「其實不是想去，而是不好拒絕」。
- active validation 因同一 provisional implicit need 連續影響兩輪，使用只按 `kind` 選模板的 generic question，改問
  「想被放著還是想被聽」，與候選 value「希望對方接受拒絕，不必逼迫明說」不一致。

因此 final 為 `いや、今は放っといてほしいのか、少し聞いてほしいのかだけ教えて。`。這不是模型不會回答，
而是低信心推測層在沒有新支持／反駁時，連續覆蓋了較低干預的當輪回覆。

修改前 raw：`analysis/p2_active_validation_prechange_gap_probe_2026-09-08.json`。既有 5-session 圖：
`analysis/p2_current_request_authority_local_run1_2026-09-08.html`。

## 本次唯一核心變因

加入 product-only **response arbitration**：當且僅當下列證據同時成立，讓已完成的 compact direct plan 優先於
重複的拒絕推測反射與新建的主動確認：

1. 當輪與上一輪 pragmatic label 均為 `indirect_refusal`；
2. 上一輪驗證結果仍為 `uncertain`，不是 supported／contradicted；
3. 當輪 typed action tendency 為 `decline_or_delay`，且有 current text evidence；
4. 當輪 compact planner 真正 completed，原計畫是 casual direct answer；
5. 沒有 safety、identity、memory、boundary、correction 或既有 pending validation contract。

這代表「在沒有新增可驗證證據時，尊重重複的退讓／延後訊號，選擇較低互動成本的回覆」，不把
`indirect_refusal` 當成使用者私人心理真值。

## 不可改邊界

- 不寫死測試句或答案，不新增固定 visible reply；final 必須來自當輪既有 compact model core。
- 不禁止所有 active validation；`possible_indirect_support_request` 等真正需要確認的類型維持既有行為。
- first exposure 的 bounded pragmatic reflection 保留；supported／contradicted outcome 仍由既有修正流程處理。
- 不改 qwen2.5:7b prompt、candidate、temperature、20 秒／256 tokens／0 retry。
- 不改凍結 M47–M54、正式資料、holdout、M27 outcome 判定或長期事實記憶。
- 不同批修 solitude correction、quoted-source、cross-session recall 或其他 controls。

## 預先成功條件

1. 中／英／日 source-disjoint 的 repeated indirect-refusal 結構，在上述五項證據齊全時保留各自 base compact core；
   不是比對特定句子。
2. 第一次 indirect refusal、repeated support bid、supported／contradicted、non-compact、protected 與已有 pending
   validation 均不被本 arbitration 誤攔。
3. longitudinal layers、verification history、typed calibration 照常更新；只撤銷本輪新建的 intrusive pending question，
   不把推測寫成事實。
4. trace node 顯示 base compact → repeated inference proposal → validation proposal → selected low-interference plan，
   並保留各 core／question 的 digest；0 raw user dialogue 複製、0 新增模型呼叫、0 fact write。
5. 隔離本機同一兩輪 final 不再出現不相關 listen/alone 二選一，且使用當輪實際模型產生的自然日文 core；
   既有 P1/P2 guards 與相鄰測試不退化。
6. 重跑現產品 controls；非目標 fresh-generation 差異只保存觀察，不歸因。Safari 若工具仍拒絕，維持 pending。

## 失敗與分支

- 若 arbitration 成立但 final 仍不是 base core，下一錯誤在 surface ownership，不擴大 eligibility。
- 若 repeated support bid 被抑制，視為嚴重回歸，必須收窄，不可刪除原 active-validation 測試。
- 若 base compact core 本身不貼題或非日文，既有 visible guard 必須處理；本項不能以錯誤 core 為由創作固定答案。
- 若實際控制只因 stochastic generation 改善，不能算本項通過；trace 必須證明 arbitration 真正決定 final。
