# P4 f7：當輪來源事件候選效用的零模型結果

狀態：**有限契約／隔離假模型路由 PASS；真模型、Safari、可見品質 pending**。f6 真產品語義 FAIL 不改判、不重送。f7 事前來源題、gold 與單一變因設計已在 `3acfa25` 推既有 PR #435；本報告不是正式 holdout 或強 LLM 對照。

## 變因與可操作差異

只在 control arm、M29 當輪 direct act／M33 not-applicable、實際 completed 的 full compact 三候選選擇邊界，讓已存在、具可觀察「受詞＋完成動作」字面關係的核心先於舊 Bayes score 泛稱核心；同一類內沿用舊分數。沒有新候選、沒有答案模板、沒有改 prompt/schema/model/fallback/final guard/記憶。來源檢查只認單句日文 `自分で{object}を{action}` 的有限構式，不能證明同義改寫或跨語翻譯；沒有可驗證候選就 `no_grounded_candidate` 且保持舊選擇。所有證書和三個原始候選的索引、core hash／固定原因碼可追，新增 audit 不含原文。

同一組假模型 JSON Schema 三候選與相同 prompt hash：關閉 f7 選泛稱 `おめでとう、いいじゃん！`，開啟 f7 選原有 `庭のベンチを塗り直したんだ、いいじゃん！`，均 1 次 fake model call、compact completed/3、M21 full/no fallback；開啟時記 `old_index=0 → new_index=1`、final core hash 等於 winner、`selection_changed`，圖上有唯一 source-event audit 節點。這是**共享候選集的零模型 selection counterfactual**，不是可見真模型改善。另注入下游 plan 覆寫後，雖中途選中 grounded 候選，最終 audit 和圖都降為 `not_exercised`，不能冒稱操弄保留到輸出；泡泡是否真的承接事件仍要另判。

## 反例、回歸及證據界線

獨立審查抓到初版把哥哥／母親的事件、轉述和問句誤判為 User 事件，以及下游覆寫仍記 `selection_changed`；第二次複核再抓到現在式關係子句 `…磨く兄だ／でした`。兩個有根據的修正批次後，加入反例並保守棄權：上述來源、候選 `…磨いたの、母だよね`／`…磨いたって、母が言ってた`／`…磨いた？` 等不能取得效用；遇到無法可靠辨析的續句也不加分。首版聚焦 48/48 不足以發現這些錯誤，因此不沿用首版結論；有限構式仍不能視為一般日文語義理解。

修正後 f7 純函式、controller、完整隔離 RightBrain＋假 LeftBrain route **60/60 passed**；非 full deterministic route、compact 失敗、三候選全泛稱的隔離陰性路由 **3/3 passed**；與 M29/M33、compact、可見日文、Web 圖、personhood 相鄰合併回歸 **220/220 passed**（9 個既有依賴棄用警告）。`py_compile` 與 `git diff --check` 通過。以上均為 **0 真 provider／0 Safari Send／0 正式 DB 寫入**；pytest 時間不能替代真 token、延遲、背景或 Web 成本。歷史 frozen SHA lock 不因新產品碼更新，也不拿它宣稱現版 V86 可重現。

下一 gate：在全新 7934／0700 私有 root、官方 ONNX 離線 warm、同 PID zero-turn 和 T0/Tpre admission 後，以原生 Safari 對事前新題只送一次；核 M29/compact/M21、原候選覆蓋及最終 hash、真泡泡與 raw/guard/graph/episode 同字、自然日文事件及簡短鼓勵、≤20 秒、≤3 generations／2000 tokens、無正式 DB 污染。三候選全泛稱、後續 surface 丟事件、時序或視覺證據缺失均嚴格 FAIL，不重送追分。
