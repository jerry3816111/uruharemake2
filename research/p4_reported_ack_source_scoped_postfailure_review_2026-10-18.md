# P4 reported-ack B 來源限定批：第二次失敗後只讀設計審查

狀態：`REVIEW_REQUIRED`；同團隊審查、非獨立驗收。舊 B 首發及本次前瞻修正批的資料、gold、raw、判分都不改；本文件不放行第三批 B 字串補丁或把現有 Web 例子重跑計分。本批 raw SHA `b08aaa9d85bb0bc68f28ed162d5eb63082c5c087ddf2ea5c0037abc59421f304`，逐輪結果見 `analysis/p4_reported_ack_source_scoped_memory_fresh_product_probe_result_2026-10-18.md`。

## 可證明的最早斷點

T5 原句 `先輩は「先に確認してね」と言った。` 的同輪 source/actor certificate 成立；A `admitted`，M31 `deferred_to_reported_ack_p4`、未呼叫 M31 模型，M22 general、route high。背景 `episode` 是 `expected=false/background_only`，具可追溯 ID；**不是**上一批的粗 memory gate 再度擋下。

`planner_debug.core_message_jp=先輩の言葉を思い出すね。`，而 `uruha_brain_mac.py` 的 `_normalize_plan` 在 casual 的 `jp_summary/core_message_jp/reply_goal/listener_state` 合併文本中遇 `思い出`，會無條件設 `intent=ask_miss_me`；接著將此 intent 映到 `surface_act=affection_tease_soften`。候選 bundle 和 multitick 路徑都會呼叫這個 normalization。raw 沒保留 normalization **之前**的完整模型候選，所以不能斷言模型原本就選 `ask_miss_me`，也不能把這項歸因只寫成模型幻覺；可以確定此字面觸發是足以製造目前 drift 的程式路徑。

`uruha_temporal_actor_scope_p4.apply_temporal_actor_scope_to_plan_p4` 先讓原 plan 更新，然後只在更新後 `intent=chat`／`scene=casual` 等條件成立時設 `selected_action=ack_reported_check_instruction_p4`。T5 更新後 intent 已是 `ask_miss_me`，故 `selected_action` 缺席；B `prepare_reported_ack_selected_visible_p4` 需要同輪 source＋A＋actual selected act 的完整憑證，於第一組 proof gate 以 `same_turn_source_or_admission_not_proved` 拒絕，沒有走到 memory gate。這個 fail-closed 比無憑證強行接管安全，卻讓報告承接在真實重啟產品中失敗。

最後自我監看／語言表面產生與原句無關的 `ちょっと手冷えてるけど、その話なら分かる`；P4-V 只檢出 quoted frame 的 `quoted_content_promoted_to_assertion`，P4-W 的 `quote_embedding_restore` 將**無關候選**包成 `「…」っていう記載なんだね。`。它改了框架形式，未驗證引文內容是否來自本輪說話者。`repaired` 在此只代表 narrow frame violations 消失，不代表語意或來源正確。

## 排除與不能下的結論

- 只刪 B 的 selected-action／memory gate 會讓未選中或顯性回憶情境也被本輪句型接管；不可用來追 T5 分。只改 P4-W 包引號邏輯也不能補回上游錯的 intent／selected act。
- T1/T3 `final_visible` 證明 B 在完整授權下能保留來源限定句，不證明跨重啟覆蓋、所有第三者轉述或整體語用理解。T1 20.2395 秒超出預設 20 秒，與 T5 coverage 是兩個獨立 strict FAIL。
- 現有 raw 不足以重建 normalization 前三個原始模型候選、斷言此詞對所有同義句造成相同錯誤、或量化移除規則的全域退步；需要先做只讀影響面盤點及零模型反例，再決定是否修改核心規則。

## 設計選擇與下一個放行條件

優先評估**輸入來源可證的 act 與模型 plan 的衝突仲裁**，不是再加一個針對 `先輩`／`思い出` 的答案例外：檢查上游第三者報告／本人請求／明示記憶／保護路由各有什麼同輪證據，在 normalization 前後明確標出 act 是否仍被支持。候選做法是讓完整來源證明、無混合直接請求且無 protected／factual memory 權限的 reported act，在一般 planner 風格選擇後仍能進入 actual selected plan；不能僅在 B 最終 guard 硬改泡泡，否則 graph 的選擇與回覆不一致。另一個較大選項是修 `_normalize_plan` 的 `思い出` 關係推斷，使它需要當輪關係訊號，而非只看候選文字；這涉及核心多意圖回歸，應另定單一變因、凍結多類正負控制和失敗成本後才動。

目前沒有證據比較兩方案的跨情境代價，**不選擇也不實作第三個 B 修正批次**。若啟動新的 act 仲裁工作項，須事前凍結未曝光的普通轉述、真正想念／回憶、混合直接請求、protected、顯性記憶與跨重啟題；逐輪核 source→normalized plan→selected→final＋graph，限制新增模型呼叫和等待，保留舊批為 before 而不重算 pass。圖上應明示「來源證明成立但 plan drift／selected 缺席」而不是只顯示 B not_applied。正式同模型 LLM、真人、temporal holdout 的比較仍各自 pending。

T6 的顯性記憶問答與 T7 的直接行動忠實度是**獨立問題**，不能與上述 act 仲裁或 B 表面句同時修改。下一個工作項可先選前者，因它直接關係到跨重啟記憶與使用者期待；必須有自身 before、單一變因與前瞻驗收，而非借本批已曝光 T6 追分。
