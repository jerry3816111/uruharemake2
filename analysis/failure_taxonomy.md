# UruhaBrain 失敗分類學 (Failure Taxonomy) v1.2

這份 taxonomy 的目的不是評分「像不像某個角色」，而是把「不像人類思考與對話」拆成可標註、可回歸、可修復的錯誤類型。  
機器可讀版本在 `/Users/jerrychang/Desktop/uruharemake2/analysis/failure_taxonomy_schema.json`。

## 核心原則

- 先標「中間思考哪裡錯」，再標「表面句子哪裡醜」。
- 不知道梗不是必然失敗；不知道後仍然用像人的方式接住，才是正確目標。
- 簡短回覆也不是必然失敗；如果它承接到 focus 且符合當下關係/情緒，仍可判定通過。
- 每個 `mixed/fail` 標註至少選一個 failure type，避免回歸資料失去可修方向。

## Failure Types

### [MISREAD_INTENT] 意圖讀錯

系統沒有抓到使用者這句話真正要做的事，例如提問、嘲諷、挑釁、接梗或關係確認。

- 常見訊號：只抓到單字，沒有抓到整句社交動作。
- trace proxy：`focus_anchor_miss`, `obligation_miss`
- 例子：使用者在嘲諷「哭哭啼啼」，系統卻把它當成真的需要安慰。

### [MISSED_VIBE] 情緒位向錯誤

抓錯情緒與互動氛圍，導致安慰、吐槽、冷淡或拒絕用錯地方。

- 常見訊號：辱罵被當成求助、玩笑被當成危機、疲憊被當成挑釁。
- trace proxy：`vibe_manual_review`, `obligation_miss`

### [MISSED_JOKE_OR_CULTURE] 梗 / 文化脈絡漏接

沒有抓到歌詞、網路梗、諧音、反諷、語言文化脈絡。重點不是必須知道所有梗，而是不知道時要像人類一樣疑惑、追問或吐槽。

- 常見訊號：把歌詞當一般句子、把亂講話當認真命題、把諧音梗當字面問題。
- trace proxy：`focus_anchor_miss`, `vibe_manual_review`

### [LOW_DENSITY] 資訊空洞 / 句終結者

有回話，但有效詞彙太少，沒有承接核心，也沒有提供可接續內容。

- 常見訊號：一句可套用到任何情境的短句。
- trace proxy：`focus_anchor_miss`, `obligation_miss`

### [GENERIC_REPLY] 泛用模板回覆

回覆不是短而已，而是可以套用到太多問題上。

- 常見訊號：「それはしんどいよな」「そうなんだ」類型在不同行情境反覆出現。
- trace proxy：`robotic_manual_review`, `focus_anchor_miss`

### [REPEATED_REPLY] 重複句型 / 模式塌陷

同一句或同一語義模板在多輪、多場景反覆出現。

- 常見訊號：使用者換了話題，系統仍回同一種句子。
- trace proxy：`robotic_manual_review`

### [TOO_ROBOTIC_LOGIC] 過度理性 / 機器人感

回答過於工整、客服化、百科化，像在完成任務，不像真人聊天。

- 常見訊號：缺乏偏性、口語停頓、社交距離感與當下反應。
- trace proxy：`robotic_manual_review`

### [WRONG_BOUNDARY] 邊界反應錯誤

該拒絕、吐槽、澄清或冷處理時選錯策略。

- 常見訊號：性騷擾時順從、辱罵時安慰、普通問題時過度拒絕。
- trace proxy：`obligation_miss`, `vibe_manual_review`

### [GHOST_MEMORY] 幽靈記憶 / 因果斷裂

系統檢索到了相關記憶，但最後回覆完全沒有體現記憶對 plan 或語氣的影響。

- 常見訊號：明明記得使用者前面說過某事，這輪卻像第一次聽到。
- trace proxy：`memory_misuse`, `memory_available_but_silent`

### [WRONG_MEMORY_USE] 記憶使用錯誤

使用了不該說出口、不相關、過期或錯置的記憶。

- 常見訊號：把別的情境記憶套到現在、過度提及隱私、用舊記憶壓過當下語境。
- trace proxy：`memory_misuse`

### [RIGHTBRAIN_SURFACE_ERROR] 右腦表面化錯誤

左腦 plan 可能正確，但右腦輸出出現日文不自然、英文洩漏、語氣錯位或句子破碎。

- 常見訊號：英文洩漏、奇怪日文、語氣與 plan 不一致、動作標籤外漏。
- trace proxy：`robotic_manual_review`

## 標註規則

- `pass`：不需要 failure type。
- `mixed`：至少一個 failure type，表示有可修正缺口。
- `fail`：至少一個 failure type，且 `severity` 通常為 `medium` 或 `high`。
- 如果同時有「左腦讀錯」與「右腦講爛」，同時標 `MISREAD_INTENT` 與 `RIGHTBRAIN_SURFACE_ERROR`。
- 如果只是短，但短得有針對性、符合情緒與關係，不標 `LOW_DENSITY`。

## 與 trace 的對齊

| Failure code | 主要 trace proxy | 修正方向 |
| :--- | :--- | :--- |
| `MISREAD_INTENT` | `focus_anchor_miss`, `obligation_miss` | 強化 focus / reply obligation |
| `MISSED_VIBE` | `vibe_manual_review`, `obligation_miss` | 強化情緒位向與互動策略 |
| `MISSED_JOKE_OR_CULTURE` | `focus_anchor_miss`, `vibe_manual_review` | 強化梗/歌詞/亂講話的接法 |
| `LOW_DENSITY` | `focus_anchor_miss`, `obligation_miss` | 增加 content units 與可接續內容 |
| `GENERIC_REPLY` | `robotic_manual_review`, `focus_anchor_miss` | 增加 specificity 與 focus anchor |
| `REPEATED_REPLY` | `robotic_manual_review` | 增加 anti-collapse sampling 與 repetition memory |
| `TOO_ROBOTIC_LOGIC` | `robotic_manual_review` | 增加口語與偏性 |
| `WRONG_BOUNDARY` | `obligation_miss`, `vibe_manual_review` | 調整 high/low road 與邊界策略 |
| `GHOST_MEMORY` | `memory_misuse`, `memory_available_but_silent` | 強化 memory gravity |
| `WRONG_MEMORY_USE` | `memory_misuse` | 強化 speakability / privacy / recency gate |
| `RIGHTBRAIN_SURFACE_ERROR` | `robotic_manual_review` | 修右腦表面化與語言檢查 |
