# P4 確定性回覆的內部策略外洩：前瞻單變因計畫

狀態：2026-10-19，實作與新 Safari 輪次之前凍結。本項是產品修正，不是正式 holdout、同模型比較或人評。上一批 typed-source 九輪 raw SHA `d727d22936a98ef2983064611128e676c6c423886e5907bee491a3b3eb491b5b` 與 strict FAIL 永遠不改判、不重播。

## Before 與單一變因

舊批 T4 的真實泡泡、graph UTTERANCE 與 raw 都是 `一回止まって聞き返す。そのくらいでいいだろ。`。該輪 `prediction_error_surprise → low_road/short_confusion` 的 core 是內部動作敘述；確定性 variant 把它直接接上句尾。模型候選的現有 `instruction_or_plan_leak` gate 會拒絕這句，但當輪模型候選數 0，確定性候選沒有同等檢查；最後日文 guard 只判語言而放行。這不是網站渲染故障。另一獨立失敗 T1 22.6619 秒，是 M31 11.7753 秒與 M21 8.1956 秒串行，**本項不修延遲**。

唯一變因：opt-in 最後可見邊界把**已選確定性候選**交給既有 plan-leak 判定；僅在 `low_road + short_confusion + plain_reply` 且已選句真的洩露策略時，轉成短、低壓、實際向使用者說話的日文澄清。第三者存在與否只能取用既有可觀察 source-frame，不能猜用戶心理、捏造哪個事實正確或把分析倒給使用者。原認知路由、記憶檢索、模型生成、保護性危機／辱罵回覆、人格與 source guard 不改。最終 guard 與新增 graph node 須說明前後 digest、拒絕理由和實際說話行為，raw 對話不進長期記憶。

可改：新 opt-in adapter、新薄 Web entry/controller、聚焦測試、本計畫與新資料/SHA、相稱結果報告、`CURRENT_TASK.md`。不得改凍結 core 或前批 source/gold/result、全域 scorer、正式 DB、原始 dirty checkout，亦不碰無關 `output/graduate_application_report/`。若現有檢查不適用於確定性候選，先記失敗、重新審查，不新增測試句專用禁詞。

## 新題、條件 gold 與 gate

資料：`datasets/p4_deterministic_plan_leak_fresh_probe_2026-10-19.json`，兩個新隔離 session、共八輪；所有輸入是事前固定的開發者自編新題，與舊九輪不作同題 A/B。A1–A4 先對話、突發第三者主張、澄清修正、正常請求；planned stop/restart 同隔離 DB 後，B1–B4 測普通陳述、第三者引述、未知時間及真正辱罵防衛。只有當某輪確實出現 `low_road + short_confusion + deterministic selected + existing plan-leak rejection`，才算本機制被覆蓋；至少一輪命中，否則即使文字看似順也判 coverage FAIL，不補題、不重送。命中輪必須沒有策略描述，真正做出低壓澄清行為，不能聲稱聽不到或已知道未證事實。B4 必須維持保護路由，不被新表面修正接管；A3 不能把被否定的旁白爭吵當事實；B3 不編投影時間。

每輪各一次、0 retry；8/8 raw assistant_reply＝graph UTTERANCE＝Safari 泡泡，新增 node 的前後 digest 與 `visible_language_guard.final_reply` 對上，最終自然日文且沒有中文字／英文或策略外洩；每輪 user wait ≤20.0 秒維持既有產品 strict gate，若另有慢路徑則保留 FAIL 並另卡歸因，不放寬。八個不同 turn episode、T0–T8 full-profile 0 rows／同 digest；記錄真模型呼叫、可得 token、延遲與服務 PID/port。安全負控、未知不編、記憶不污染是硬 gate；任一不過，整批 strict FAIL。最多兩個有根據修正批，仍失敗 `REVIEW_REQUIRED`。

先做零模型聚焦＋受影響 P4 surface／graph 回歸，再新 0700 root 的 0-turn readiness/planned stop、官方 SHA ONNX 私有離線預熱、空 profile，產品 SHA/diff/commit/push/PR head 核對後才開新 Safari。測試前檔案 SHA 保留，不用 outcome 改 dataset/gold。圖用既有 runtime graph，不另建永久網站。無真人證據時不得宣稱被理解感改善；本項最多只證明這類內部策略不再洩露及可見對話行為有界改善。
