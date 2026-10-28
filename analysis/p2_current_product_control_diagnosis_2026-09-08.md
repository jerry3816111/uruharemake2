# P2 現產品 5 sessions／9 輪控制診斷

日期：2026-09-08
證據：developer-authored、隔離本機 runtime、實際 qwen2.5:7b；不是 holdout、人評、Safari 或正式研究結果。

## 結果先行

結構契約 4/4 通過，但依原控制目的逐 session 判定只有「無上下文 `那個。` 時保守追問」可接受；
其餘 4 個 session 仍有明確語用／行動失敗。這次證明 P2 表達 commit 沒有掩蓋上游錯誤，也把下一個瓶頸
從模糊的「回答不好」縮小到 current-turn request authority、active validation、correction surface 與 source recall。
這是開發診斷，不是 1/5 的普遍品質估計。

## 逐輪歸因

| 控制 | 實際結果 | 目前最早可見錯誤層 | 判定 |
|---|---|---|---|
| `考えとく。` → `また今度にしようかな。` | 第一輪誤標 short confusion，但 surface 察覺婉拒；第二輪 model core 是 `また今度ね。`，之後 active validation 改成問「想獨處還是想被聽」 | decision／validation：有較貼題 core，卻被無關 pending hypothesis 覆蓋 | FAIL |
| `今日はただ聞いてほしい。` → `謝謝。不過現在請幫我想一個做法。` | 第二輪仍選 chat；model core 是中文 `承認你的需求`，日文 guard 退成 `ん、その話もう少し聞かせて。` | 最早是 current explicit help request 沒被 M47 grammar 認出；planner language 是下一層錯誤 | FAIL |
| `今日はただ聞いてほしい。` → `違う。今日は一人にしてほしい。` | 有承認読み違え，但又追加毫無當輪來源的「沒睡／想事情」二選一 | correction action/surface：正確新需求沒有終止舊測試情境的具體追問 | FAIL |
| 新 session 的 `今日はただ聞いてほしい。` → `「ありがとう」は誰の言葉だった？` | 第一輪把跨 session 舊 contradiction 說成「そこ読み違えた」；第二輪 planner 把來源問題選成 refusal，final 無法回答 | 跨 session feedback association＋factual/source route | FAIL |
| 無上下文 `那個。` | model core 是中文 `那个啥？`；language guard 改成 `ん、その話もう少し聞かせて。` | planner language contract 不穩，但最終保守澄清符合「未知不編」 | bounded acceptable |

## 圖與資源

- 5 sessions／9 輪；4 次實際 compact model calls、4 個 `compact_general_plan_p2` graph nodes。
- 只有 2 輪符合 completed compact direct-chat，因此有 2 個 `contextual_expression_commit_p2` nodes；另兩輪由
  active-validation／refusal surface 擁有輸出，adapter 正確不接管。
- 兩個 direct-chat selected core 都是中文，final 經既有 language guard 修成日文，故
  `final_visible_surface_matched=false`。這是正確的 trace，不是假稱 core 本身合格。
- 4 次合計 prompt 5,782、completion 314、total 6,096 tokens；模型呼叫 31.579485 秒，整組 45.554864 秒。
- persistence、graph current prediction、no-prediction pending、calibration 四項結構 checks 全過；正式 DB 未用。

## 下一個單一變因

先只處理第二個 session 的**當輪明確要求優先權**：把中／英／日自然的「幫我想／找／決定一個做法或步驟」
辨識為 current explicit help request，交給既有 M47→M46 source-bounded 路徑；前一輪的 listening 不得覆蓋當輪請求。
若沒有實際 task span，應自然詢問缺少的任務，而不是捏造方法。不可加入這句的固定回覆、不可修改模型 prompt，
也不可同批修婉拒、來源問題或 correction 尾句。

原始證據：`p2_current_product_controls_local_run1_2026-09-08.json/html`。
