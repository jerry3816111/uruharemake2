# P4 顯性 episode 回憶：來源限定焦點契約（首發前計畫）

狀態：2026-10-18，**設計／新題已定、未實作、未對新題做模型或 Safari 生成**。這是開發者自編產品題，非獨立 holdout、人評或強 LLM 對照；同團隊設計審查不是獨立放行。保留 reported-ack B 兩批 strict FAIL／`REVIEW_REQUIRED`，不重播舊 T6 追分。

## Before 與單一變因

已曝光 B 修正批 T6 `さっき言った確認対象、覚えてる？` 的 raw SHA `b08aaa9d85bb0bc68f28ed162d5eb63082c5c087ddf2ea5c0037abc59421f304`：T2 使用者原話 episode `8ab9ebf2-5ce2-4db4-88f5-3025a89dc671` 在同 DB／T6 候選池，卻是 rank 7/7、score 1.2505、`selected=false`、不在 `passed_to_leftbrain`；工作記憶上限 5。另有獨立決策斷點：M22 已辨識 factual/memory，`_detect_relationship_intent` 仍由 `覚えてる？` 將 plan 變 `ask_miss_me/affection_tease_soften`，最終泡泡引用錯誤的近期引述。舊 `memory_query_support` 對正確 T2 和錯誤 T5 皆有 2/6 shared units；只加 top-k 或開 experimental generic recall 不足以安全修正。舊 T6 只作 before，**不計入新批成績**。

唯一能力變因：新增 opt-in 的「**具體顯性回憶問題 → 唯一使用者原話 episode → 同源 selected act → 同源自然日文 final**」契約。只讀既有 `memory_provenance.candidate_pool`，不改全域 retrieval、分數、上限 5、原始模型／B gate、profile 或寫入。針對日文、無引述、具體焦點的過去發言問句，從 episode 的 `User:` 原文而非模型 `Summary/Uruha` 擷取直接陳述；要有有效 episode ID/trace、焦點的充分重合且唯一，遇相同焦點不同原文、撤回／否定、引述／第三者話、敏感內容、無來源或不完整 provenance 則不可釋出事實。問句中缺證據可給短日文不確定回覆；寬泛關係問句與 protected/direct-action 路徑仍由前置系統處理。選中時新增可核的 handoff channel、plan/graph 憑證及 final 一致性；不得把候選池 audit 說成已交付，也不得從模型摘要推斷使用者事實。

可改：新 `uruha_explicit_episode_recall_focus_p4.py`、其聚焦測試、薄 opt-in Web 入口／既有隔離 controller 延伸、本卡、新資料／SHA、`CURRENT_TASK.md`、必要結果報告。不得改 `uruha_memory_runtime.py` 全域 scorer、`uruha_leftbrain_rules.py` 全域關係規則、B/A 模組、已凍結題／gold、正式 DB、原始 dirty checkout、無關 `output/graduate_application_report/`。若安全接線必須超出此範圍，先停在設計審查，不暗改第二變因。

## 新題、判準與執行

`datasets/p4_explicit_episode_recall_focus_fresh_probe_2026-10-18.json` 有九個逐字新輪次（建立前 repo exact 搜尋 0），T4 後 planned stop／同隔離 DB 重啟，兩個 Safari session、各輪一次／0 retry。T1/T2 是不同焦點的直接原話；T3/T4 是含相同詞的第三者引述干擾；T5/T7 需各自引用對應的原話／值，不能從最近引述或模型摘要拿答案。T6 是寬泛關係問句，不得被此契約接管；T8 是缺來源，須低壓日文不確定、不能虛構；T9 是討論引號內句型，不得把引號當真正的回憶請求。零模型契約另外固定：同焦點不同值、撤回／更正、敏感值、malformed episode/provenance、protected cue、英文／中文非准入、rank>5 正確證據等負控；這些不以 Safari 題字面寫成規則。

首發 strict PASS 同時要求：聚焦與相鄰零模型測試全過；新九輪 9/9 raw＝graph `UTTERANCE`＝當輪 Safari 泡泡、最終自然日文／既有身份安全不退化；T5/T7 2/2 source ID、焦點、handoff、selected plan、final 記載一致且各自含正確值、不含干擾值；至少一個正例原本不在五項 working memory 但經專用 handoff 可答，否則覆蓋不足而非成功；T6/T9 無 takeover、T8 無虛構；同 DB 重啟、九個新 episode ID、T0–T9 全量 profile row/count/digest 不變；每輪 user wait ≤20.0 秒、此契約新增模型呼叫 0，實際可得 token/延遲如實記錄。前置空 root/空 profile、官方 SHA 相符的 embedding 私有離線預熱、0-turn readiness/stop 必須先完成，不能把下載藏在 T1。任一 gate 不符整批 strict FAIL、保存原件；至多一個有根據且**全新**前瞻修正批，仍失敗即 `REVIEW_REQUIRED`。

先以 `.venv/product_checks/bin/python -m unittest -v test_p4_explicit_episode_recall_focus.py` 驗最小契約，再跑受影響的 `test_semantic_memory_recall_support_v1.py`、`test_memory_provenance_trace_v1.py`、`test_p4_reported_ack_selected_visible.py` 及必要 Web entry/controller preflight；首輪前凍結 code／依賴／dataset SHA、diff review、commit/push、核 PR #435 head。新真輪按隔離 controller 啟動與 verify-ready，逐輪保存 profile-full／episode／raw、核 graph 節點及 final；最後 planned stop、PID exited、port 7894 vacant。若只是單元通過或 graph 有節點、泡泡仍錯，產品 FAIL。

這一批最多證明**有界日文直接陳述的跨重啟來源回憶**；不證明任意長對話、跨語言事實回憶、人物心理、felt-understanding、人類方程式、同模型 LLM 優勢或正式 P3／研究 gate。失敗也作為瓶頸結果保留。
