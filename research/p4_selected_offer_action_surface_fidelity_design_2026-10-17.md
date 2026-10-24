# P4 已選食物邀請行動 → 最終日文：表面忠實度設計審查

狀態：2026-10-17，**同團隊設計已定案；尚未實作、凍結新題或驗收**。原六輪已曝光、strict FAIL，不能在其答案上加例外追分；精確 before 見 `analysis/p4_third_party_question_evidence_fresh_product_probe_result_2026-10-17.md`。這是新的 action-to-utterance 問題，不是延長已 `REVIEW_REQUIRED` 的第三者問句 gate，也不解決該批 `一回、` 圖表語法 mismatch。

## 可反駁的 before 與問題

原 T2 `海苔昆布おにぎり、一口いる？` 由既有路徑真選 `intent=food_offer_generic`、`surface_act=named_offer_accept`、`dialogue_act=concrete_offer_response`、`grounding.offered_item=おにぎり`，selected core 是 `おにぎりなら普通にあり。少しもらう`，speech plan 含「おにぎりを名詞で拾う」。但 Safari 最終 `先に、今は昼のゆるい感じだけど、その話なら普通に分かる。`，只有「能理解這話」，沒有接受／拒絕一口。既有 M39 `accepted_verified_surface`、frame shadow preserved，均未涵蓋「已選對話行動有沒有真的說出來」。profile 沒有誤寫。這個反例否定「選對 intent 就等於使用者感到被接住」。

初步只讀路徑：`RightBrain.speak` 的 legacy 非結構化表面先產生 template，再用 `_refine_conversational_reply` 做對話密度優化。`_speech_plan_variants` 及 `_conversation_enrichment_variants` 已提供含物品和接受動作的候選，但後者亦加入 `_build_dynamic_context_anchor` 的時間／身體狀態候選。T2 raw 的 `dynamic_anchor.variants[0]` **逐字等於最終主句**；`model_surface_selection.selected_source=deterministic`、候選數 0，`model_surface_candidate_trace.disabled_reason=model_blend_disabled`，前綴 `先に、` 由 `_finalize_surface_reply` 的人格前綴路徑可解釋。`_reply_needs_conversation_density` 對 `named_offer_accept` 短句要求擴寫；`_required_surface_semantic_groups` 當輪數量為 0，未提供「物品＋接受」的保留義務。自我檢查明列 `speech_plan_grounding_miss` 和 `missing_turn_hook`、`needs_repair=true`，但 `self_monitor_repair.before==after`；M39 的 `selected_policy_id=null` 且仍報 `accepted_verified_surface`，既有 selected-action 執行節點則 `not_applicable`。這些是 raw 可核對事實；**是哪一個中間候選贏得排序仍是原碼推論**，因 raw 沒保存每個中間候選，尚非單步消融證明。

## 唯一設計變因及權限

單一變因是**候選選句時的 selected-action preservation**：僅在已真選安全、非記憶、非引用的直接日文食物邀請，且 selected `dialogue_act=concrete_offer_response`、`surface_act=named_offer_accept`／`named_offer_light_accept`、`grounding.offered_item` 可辨識時，讓最終表面候選必須同時表達該物品與所選的接受行動。優先利用既有自然候選；不替 planner 重選想吃／不想吃，不編造身體狀態，不把「知道這話」算作接受。若只有不符合的候選，應保守使用 selected core／原本合格的 speech variant 或報明確 mismatch，不可默默生成一個未授權的相反行動。若 final 之後仍被改壞，圖節點必須報 fail，不冒稱攔住。

同團隊只讀審查指出一個關鍵副作用：`_required_surface_semantic_groups` 也被 `_model_required_semantic_groups`→`_model_surface_disabled_reason` 重用；若直接新增群組，可能讓 `model_blend_enabled` 下原本 `missing_semantic_contract` 的模型生成突然獲准，變更來源和成本。故**保持全域 semantic groups 不變**；設計為產品限定、與既有群組獨立的 selected-offer predicate＋語義 validator，在 legacy 候選篩選／合格 core 回退有界執行，最終可見表面變換後再作 audit。不得改模型候選 eligibility、核心 generic LLM 參數、LeftBrain 選案、M31/M32、安全路由、writer、正式 DB 或第三者問句程式。准入須核 source 真的是單句當輪 offer（不是引號內、傳聞、條件、否定、第三者轉述、`Xが好き？`、`ねえ、好き？`、偏好陳述或多子句），且不可跨越既有 protected/refusal/OOC/記憶等非目標路徑。`required_marker_groups`／記憶群組現有優先權不能被產品 overlay 覆蓋；`_refine_conversational_reply` 在沒有完整群組候選時會退到 best partial，`_sanitize_reply` 的長度截斷、model blending、自我修復與最終語言 guard 也可能在候選篩選**之後**改壞句子。因此選句約束與最終可見稽核是同一 action 保留變因的兩個邊界；稽核不能把候選成功外推成泡泡成功。可見最小物品義務是既有 `grounding.offered_item` 的 canonical 名詞（原句修飾語如 `海苔昆布` 不自動保證），另須保留 offer 回應，不要求逐字等於 core；詞彙匹配不能用 `食べ` 子字串把 `食べない` 誤認接受，也不能把 `あり` 接在否定或矛盾後當接受。若無來源不得新增 `また`／`さっきから` 等重複暗示。稽核節點只在真正 selected action 後顯示「選中邀請回應 → 候選篩選 → 最終日文 action preserved / mismatch」，不得把內部分析傾倒到普通聊天泡泡。

## 實作邊界、驗收和停損

本次設計審查是同團隊非獨立審查；不是模型評測。v1 只收**單句、直接、日文、已由 planner 選為接受的 `X、一口いる？`**，且 X 必須有既有 grounded canonical food item 作結尾，前置修飾僅限不含主語／助詞的短名詞；危機詞、引用、第三人稱、條件、否定、第二句、過長與不清楚物品一律不准入，走原路。這是明說的有界覆蓋，不宣稱一般邀請語用。核對的是 canonical `offered_item`，不藉此聲稱保留 X 的每個修飾語。

預定最小 seam 是新產品限定模組 wrapping `RightBrain._refine_conversational_reply`：先呼叫原 refine，對其**長度 sanitize 後**的候選做獨立 action validator；若不合格，只從既有 `_speech_plan_variants`、selected `core_message_jp` 依預定順序挑第一個 sanitize 後也合格的句子，無合格者保留原句並記候選 mismatch，不能自行編新承諾。這是 **post-refine selector**，不是假稱攔截了內部全部候選；舊 `_required_surface_semantic_groups` 和模型 candidate eligibility 均不變。action validator 要求同一句/同一立場下的 canonical item＋明確第一人稱可承接的肯定接受動作，拒絕否定、疑問、引用、條件、第三者行動和後句反轉；只說 `あり`／`一口` 或泛泛「分かる」不足。若 strict validator 使某些自然句無法准入，標 uncovered，不能放寬到子字串取巧。

最終稽核僅在原 `emit_response_if_ready` 已完成 M31/M49/日文 guard、寫出真正 `result.reply` 後，對同一選案與**真正 final reply** 計算 preserved／mismatch，將不含原對話全文的 trace 放入回傳 `logic`，並把獨立 verify node 接在 graph 的 selected→utterance 主鏈。稽核不回改泡泡或 episode；不得把舊 `selected_action_surface_execution_p4=not_applicable` 冒稱本 action 已執行。非准入 source 必須 reply byte-identical、沒有新 node。由於 `RightBrain.speak` 會複製 logic，local refine trace 不可直接視為已到原 logic；final audit 必須依原 result 重新核對。准入後才因後段被改壞時，graph 應為 mismatch 而非 preserved。

允許檔案：新產品限定 implementation module、其明確產品入口安裝、零模型契約測試、新前瞻 dataset/plan/SHA、結果報告與 `CURRENT_TASK.md`；若 graph 收集器須最小接線，可改 `uruha_memory_observatory.py`，但不能重排其他 node；若 wrapper 無法如實捕捉 final，再由具體測試證明後考慮 `uruha_brain_mac.py` 的單點 hook，不能先擴寫核心。禁止變更舊六輪 dataset/gold/code freeze、LeftBrain、M31/M32、writer、正式 DB、baseline/正式門檻。資源上限：零模型開發測試先小後相鄰；新 Safari 最多一個首次六輪批次、各題一次、無答案 retry，20 秒/輪，首輪前凍結 SHA；額外啟動失敗另外計數。若首批 FAIL，最多兩個有根據且用新題的修正批次，仍 FAIL 則 `REVIEW_REQUIRED`。

- Before：原 T2 僅作歷史反例，不重新生成、不能當新 gold；如需新輸入定位，標 `dev diagnostic` 且與稍後 Safari 前瞻 source／物品**完全不同**。前瞻集至少一個同樣會受對話密度/時間 anchor 影響的全新食物 offer 值，另有不同 food 類別與跨輪上下文；後者須在第一次 Safari 送出前凍結，不可先探答案。
- 零模型/契約：正例驗 selected 不變、可見日文同時保留物品與接受／拒絕立場、人格自然且不捏造私密飢餓／外部事件；對抗候選含「我懂這話」、同物品但否認、接受另一物品、core 後接矛盾句、第三者要不要一口、無來源 `また`／`さっきから` 重複暗示，圖必須 fail closed。負例涵蓋第三者偏好問句／陳述、本人偏好、普通食物問題、引用／否定／條件／複句、中文／英文（仍交既有跨語流程）、危機與邊界、記憶召回、原 M29/M31 授權。`model_blend_enabled` 的准入與實際呼叫數不得因這個變因增加；profile/episodic writer 不變。
- 精確首層命令預定 `.venv/product_checks/bin/python -m pytest -q test_p4_selected_offer_action_surface_fidelity.py`；相鄰 `.venv/product_checks/bin/python -m pytest -q test_contextual_expression_commit_p2.py test_rightbrain_model_candidate_gate.py test_p4_third_party_question_evidence.py test_p4_current_statement_source_authority.py`，以及 `python -m py_compile`（實際環境用同一 venv Python）、`git diff --check`。先小測，再受影響相鄰、compile/diff、隔離入口 0-turn。全新前瞻 Safari 的 exact source/gold、0 retry、逐輪 row-ID、selected/graph/bubble、一次 planned same-DB restart、等待 ≤20 秒與可得模型／token／價格在首輪前 commit＋SHA。不能用少數固定 replay 代替泛化或同模型對照。任何語義、來源、graph、記憶、成本或程序 strict gate 失敗，保留原 raw FAIL；至多兩個有根據的修正批次，仍失敗列 `REVIEW_REQUIRED`，不可放寬 baseline 或重播曝露題。

預期最小可操作改善是 T2 類「已經正確選了要接受食物，最終真的回答邀請」而不是多一張統計報表。即使這一項產品 PASS，也不等於一般人類理解、優於強 LLM、人評被理解感、長期記憶泛化、正式 temporal holdout、VRM／Function Calling 完整交付或人腦方程式。這次因時間 anchor 的根因候選若被更深 read-only trace 否定，先修設計而不直接實作。
