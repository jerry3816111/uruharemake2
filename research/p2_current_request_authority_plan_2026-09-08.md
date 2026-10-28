# P2 Current Request Authority：前瞻工作卡

日期：2026-09-08
狀態：實作前凍結的產品修正計畫；不是正式研究 preregistration。

## 已重現問題

隔離現產品控制的前輪是 `今日はただ聞いてほしい。`，下一輪改為
`謝謝。不過現在請幫我想一個做法。`。實際結果：

- M47 沒有辨識 current explicit help request，desired policy 沒有切換到 `solve_regulation`。
- compact planner 仍選 `intent=chat`，core 為中文 `承認你的需求`。
- visible-Japanese guard 將 final 修成 `ん、その話もう少し聞かせて。`，但問題沒有沿既有
  M47→M46 的缺少 task context 路徑被說清楚。

原因是現有跨語言 deterministic grammar 支援「給我方法／告訴我怎麼做」，但不支援同義、常見的
「幫我想／找／決定一個做法」。這是 current-turn 可觀察的回覆形式要求，不是心理推測。

## 本次唯一核心變因

只擴充產品入口中的 current explicit practical-help grammar：辨識中／英／日含「請對方協助思考／尋找／決定」
以及「方法／做法／下一步」的請求結構，產生與既有 M47 相同的 typed route、span geometry、digest 與 policy。
沿用 M45.1／M46 的來源 gate：當輪沒有獨立 task span 時，0 model calls 形成缺少任務的低壓澄清，不能編方法。

## 不可改邊界

- 不改 qwen2.5:7b prompt、候選、temperature、20 秒／256 tokens／0 retry。
- 不修改凍結 M47–M54 source；使用 product-only opt-in adapter。
- 不用完整測試句、謝詞或固定答案作條件；必須是跨語言句法 family，含 source-disjoint positives／negatives。
- 不把「提到方法」當成請求；否定、引述、陳述自己正在想、protected route 不得誤觸發。
- 不從前輪捏造 task；current request 只覆蓋舊 listening response form，不抹除正式回饋 ledger。
- 不同批修 active validation 婉拒、source recall、cross-session correction 或舊 fast-path suffix。
- 不把 developer-authored runtime 控制寫成 holdout、人評、正式 superiority 或完整理解證據。

## 預先成功條件

1. 重現句及至少各一個 source-disjoint 中／英／日自然同義句均形成 `practical_help_authorized`，而既有
   positive／negative／nonrequest route 逐欄不變。
2. span 可由 offsets＋digest 還原；trace 不複製 raw dialogue、0 長期記憶寫入。
3. 有獨立 task clause 時沿既有 source gate；無 task 時 `awaiting_context`、0 action model calls，final 是自然日文。
4. 前輪 listening、後輪自然 help request 的隔離 runtime，後輪 policy 必須是 `solve_regulation`；前輪 M27
   只依既有規則變成 unknown/uncertain，不得假記 supported。
5. protected、memory、correction 與不相關 chat 安裝前後不變；focused／相鄰測試通過。
6. 再跑現產品 controls 至少目標 session；圖要顯示新 route、M46 是否介入、語言 guard 與 final。

## 失敗與分支

- 若 route 正確但 final 仍不說缺少什麼，下一錯誤歸 M45/M46 surface，不用擴大 grammar。
- 若有 task span 但 M46 不使用，歸 source handoff/action planner，不在本批修。
- 若否定或普通提及被誤判，先收窄結構／否定 scope；不能用 exact test phrase blacklist。
- 若本批只改善一個作者案例，仍只算 bounded product fix；不宣稱 P2 完成。
