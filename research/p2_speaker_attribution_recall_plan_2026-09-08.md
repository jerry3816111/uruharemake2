# P2 Speaker-Qualified Recall：前瞻工作卡

日期：2026-09-08
狀態：實作前凍結的產品修正計畫；不是正式研究 preregistration。

## 修改前問題與因果位置

產品控制先有使用者跨語言的 gratitude act：`謝謝。不過現在請幫我想一個做法。`，之後新 session 問
`「ありがとう」は誰の言葉だった？`。修改前最終只回 `ん、そこもう少しだけ聞かせて。`。

實際 runtime graph 證明舊 episode 已進入 selected working memory，episode 也保有 `User:`／`Uruha:` 欄位；缺口是
`semantic_route_m22` 仍選 `general_conversation`，沒有把 quoted phrase、跨語言 speech-act 等價與 speaker provenance 組成
可回答 contract。詳細證據：`analysis/p2_speaker_attribution_recall_prechange_gap_probe_2026-09-08.json`。

前一項曾觀察到的新 session 假 correction 已隨 explicit-space 錯誤 pending 被撤回而消失，不另加機制。

## 本次唯一核心變因

新增 product-only **speaker-qualified quoted recall**：

1. 只辨識中／英／日明確的「引號內這句是誰說的」問題，抽取 quote geometry／digest，不把一般提及或翻譯問題當來源查詢。
2. 只檢查既有 retrieval 已選入的 recent／working-memory evidence；不掃未取回的私有資料，也不讓 LLM 猜來源。
3. 保留 storage schema 中的 `user`／`uruha` speaker role；一般 quote 用 normalized exact match。第一個跨語言 semantic atom 僅為
   bounded `gratitude`，公開支持範圍，不宣稱開放域翻譯或語意理解。
4. 只有證據指向唯一 role 才直接回答；兩邊都說過就顯示 ambiguous 並短問場景，沒有證據就明說目前記憶無法確認。
5. 把 typed source contract 接到 factual/memory route、selected plan、Japanese surface 與 runtime graph；舊 working-memory provenance
   保留，0 新增 model call、0 fact write、0 raw dialogue 複製。

## 不可改邊界

- 不改 frozen M18–M54 source、正式結果、模型、prompt、temperature、token budget 或 retrieval ranking。
- 不因同義、情緒或上下文相似就猜 speaker；不把 speaker attribution 寫成使用者心理或長期偏好。
- 不讀未被目前 retrieval 選入的 episode；證據缺失時 fail closed。
- 不攔 safety／boundary；不修一般 memory QA、quoted meaning、人物事實或 open-domain coreference。
- 不把單一 gratitude atom 說成完整跨語言理解；其他 atom 必須另有資料與測試才可擴張。

## 預先成功條件

1. exact quote 可分別辨識 user 與 Uruha；中／英／日 source-query grammar 有 source-disjoint 測試。
2. `ありがとう` 對已取回 `謝謝` 的 bounded gratitude atom，唯一 speaker 為 user 時，以自然日文直接回答且不重複外語原句。
3. 同一 phrase 兩個角色都說過時不得選一邊；沒有 matching selected evidence 時不得用 unselected memory 或模型補答案。
4. 非來源問題、翻譯／詞義問題、沒有 quote、第三人稱一般敘述與 safety route 保留原流程。
5. trace 只含 quote／utterance digest、speaker role、match type、trace／memory ID；不複製 raw dialogue。graph node 唯一、有連線、
   位於 retrieved evidence 與 selected plan 之間，最後 surface 與 contract 相符。
6. focused、affected adjacent、同一 5-session／9-turn 本機 qwen 控制都通過相稱檢查；目標輪修正，其他差異逐一解釋。
7. Safari 若外部工具狀態未變，維持 pending，不把離線 HTML 冒充 Safari 驗收。

## 失敗與分支

- 若 gratitude episode 沒被 retrieval 選入，本次不得偷偷掃全庫；先保留 fail-closed，另立 retrieval recall 改進項。
- 若下游 M18/M39 改寫來源答案，修 authority ordering，不能靠把答案塞進一般人格 prompt。
- 若兩角色候選未形成 ambiguous，先修 role-preserving evidence join，不用 recency 猜唯一 speaker。
- 若產品實測只有固定控制通過，結論維持 bounded mechanism，不外推 open-domain memory superiority。
