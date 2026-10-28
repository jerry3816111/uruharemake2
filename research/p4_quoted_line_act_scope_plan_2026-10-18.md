# P4 引述台詞的當輪 act-scope：首輪前計畫

狀態：2026-10-18，**只讀設計審查完成；新題／判準在實作及首輪生成前凍結**。本項是同團隊自編產品開發探針，不是正式 temporal holdout、人評或同模型對照。保留上一批九輪 strict FAIL 與 T9 原件，不重播 T9 追分。

## Before、唯一變因與界線

`analysis/p4_explicit_episode_recall_focus_fresh_product_probe_result_2026-10-18.md` 的已曝光 T9：`「集合場所、覚えてる？」って台詞、変かな？`。新 focus 因引號正確拒絕，但舊 `_detect_relationship_intent` 把引號內 `覚えてる？` 當當輪 `ask_miss_me`；generic memory gravity 把上一輪駐輪場短期記憶設為可用答案，最後 deterministic surface 離題。raw、node graph 與 Safari 泡泡相同，故不是展示層假象。T1 逾時與 T3 引述指令時態錯述另屬不同變因，不在此批偷修。

本項唯一能力變因：**同一個有界 quote/outer-act scope certificate**，對一個完整且平衡的引號台詞，辨識它只是被評價的文本；只有引號外明示的台詞自然度、語氣或精簡問題授權本輪 act。證書同時約束 route/selected plan、上一輪記憶錨點的答案權限、最終自然日文以及圖節點。這不是通用語意解析或任意文案改寫。引號外另有真實記憶／關係問句、未閉合或多個引號、保護性線索、指令或不確定語法時不接管；照舊路徑處理，不能以「有引號」整輪遮斷。不能把引號內 private/third-party 字面當使用者事實，不新增 profile/fact 寫入、不變更 episode 檢索／排序／top-5、不得繞過日文與 safety guard。接管時圖保留原 route 作 before／scope override 收據，不能謊稱每個舊 shadow 推論都被修正。

允許檔案：新增 `uruha_quoted_line_act_scope_p4.py`、聚焦測試、薄 opt-in Web 入口與既有 detached controller 的薄繼承、此計畫／新資料／SHA、`CURRENT_TASK.md` 和必要結果報告。**不改** `uruha_leftbrain_rules.py`、`uruha_brain_mac.py`、先前 P4 focus／reported-ack 模組、既有凍結題／gold／raw、正式 DB、原始 dirty checkout，或無關 `output/graduate_application_report/`。若所需接線必須越界，先停作設計審查。

## 前瞻資料、產品 gate、成本

`datasets/p4_quoted_line_act_scope_fresh_probe_2026-10-18.json` 之八句在建立前對 repo 逐字搜尋 **0 命中**。T1 建來源；T2 無引號直接回憶，仍須由舊 focus 來源限定回答；T3 引號內回憶問句但引號外問口語自然度；T4 設不同短期記憶後 planned stop；T5 同 DB 重啟，測引號內關係問句、引號外問語氣；T6 無引號真關係問句；T7 引號加外層另一個真關係問句，不得被整輪阻斷；T8 `『』` 引號內回憶句、外層要求精簡。T8 只要求答外層精簡方向，不把精確文字改寫品質宣稱為本項能力。兩個 Safari session、T4 後同隔離 DB planned restart，每句一次、0 retry。零模型負控另含 ASCII quotes、英文／中文的有界外層編輯問題、未閉合／雙引號、外層真 request、safety/direct action、無記憶／不同記憶、繼承 focus 日文直接回憶。

首發 strict PASS 同時要求：

1. 聚焦與受影響相鄰零模型測試全過；新八輪 **8/8** raw `assistant_reply`＝runtime graph `UTTERANCE`＝當輪 Safari 泡泡，且可見回覆為自然日文。
2. T3/T5/T8 的當輪 selected/current act 是外層台詞評價／精簡，不是 `ask_miss_me` 或 `recall_context`；專用收據／圖顯示引號 span 非請求、無先前不相干 `memory_anchor` 答案權限，最終沒有拿 T1/T4 內容假裝回答。對自然度／語氣／精簡的回覆須答到外層問題，而非只顯示新節點。
3. T2 直接回憶的 source ID、plan 與可見值同 T1；若來源未進 retrieved pool 算 coverage FAIL，不靠猜。T6/T7 仍允許真關係問句（T7 尤其不能因含引號整輪屏蔽）。T1/T4 的來源不得無根據升為 profile facts。
4. T0–T8 九份 full profile 均 present、0 rows／同 digest，八個不同 episode，planned stop／同 DB restart／PID 退出／port vacant；每輪 user wait ≤20.0 秒。本 scope 新增模型呼叫 **0**；全管線 token 無可靠計量時標 unavailable 而非 0。逐輪列延遲與 scope selected/final 一致性。

任一 gate 不過整批 strict FAIL，原件保留；已曝光 T9 和本批不得重播改判。至多兩個有根據的新前瞻修正批，仍失敗則 `REVIEW_REQUIRED`。先凍結此計畫與資料 SHA，再做 opt-in 實作／聚焦與相鄰測試；首輪前凍結 code/依賴/資料 manifest、diff review、commit/push、核 PR #435 head，才啟隔離 Web/Safari。最後保存完整結果與成本、圖核對、planned stop、Git review/commit/push/PR head。

即使通過，也只證明**有界引述台詞的當輪 act-scope**，不證明任意語用理解、被理解感、長對話普遍可靠、同模型強 LLM 優勢、人類反應方程式或真人等價。
