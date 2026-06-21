# UruhaBrain vNext 研究 90+ 診斷報告

- 產生時間：`2026-06-21T13:59:38+09:00`
- 研究認知成熟度分數：`94.96`
- 是否可主張研究 90+：`True`
- 是否可主張完整人類對話 90+：`False`
- 表面對話對齊分數：`82.67`

## 判定

研究認知分數衡量架構證據；完整人類對話判定另外要求真人盲評與真實失敗回放，兩者不可互相替代。

## 組件分數

- `左腦對話控制`: `100.0` (weight=0.18)
  - leftbrain_audit_pass_rate=1.0
  - run_leftbrain_90_readiness_audit.py: 36/36
  - test_leftbrain_rules.py / test_route_logic.py: PASS
- `社會推理 / ToM`: `99.17` (weight=0.24)
  - formal_tombench_accuracy=0.975
  - research_social_reasoning_pass_rate=1.0
  - tom_subtext_proxy_rate=1.0
- `記憶一致性 / 工作記憶`: `98.95` (weight=0.16)
  - delayed_recall_rate=1.0
  - profile_capture_rate=1.0
  - working_memory_relevance_rate=0.9474
  - memory_causal_appropriate_effect_rate=1.0
  - unwanted_memory_intrusion_rate=0.0
  - memory_used_explicitly_rate=1.0
- `Runtime 動態 / 自主循環`: `93.71` (weight=0.12)
  - trace_key_presence_rate=1.0
  - self_correction_rate=0.1944
  - planner_detected_issue_turn_rate=0.1944
  - planner_unresolved_issue_turn_rate=0.0
  - planner_resolution_quality_rate=1.0
  - planner_repair_success_rate=1.0
  - open_loop_turn_rate=0.25
  - autonomous_open_loop_eligible_count=5
  - autonomous_open_loop_detection_accuracy=1.0
  - autonomous_open_loop_key_accuracy=1.0
  - autonomous_open_loop_followup_rate=1.0
  - autonomous_proactive_semantic_match_rate=1.0
  - autonomous_proactive_delivery_rate=1.0
  - autonomous_proactive_memory_record_rate=1.0
  - autonomous_duplicate_suppression_rate=1.0
  - autonomous_success_rate=1.0
- `對 prompt-only baseline 的研究優勢`: `89.4` (weight=0.1)
  - avg_score_delta=0.6851
  - relevance_dual=0.875
  - emotion_dual=0.7364
  - boundary_dual=1.0
- `人格穩定性`: `75.54` (weight=0.06)
  - mpi_stability_score=0.7554
  - mpi_overall_trait_cv=0.2446
- `表面對話對齊`: `82.67` (weight=0.08)
  - dialog_act_accuracy=0.3
  - emotion_accuracy=0.6167
  - overall_unique_ratio=0.7604
  - overall_top_10_concentration=0.2917
  - stress_overall_pass_rate=1.0
  - stress_unique_reply_ratio=0.1306
  - stress_top_20_reply_concentration=0.2359
  - human_speech_layer_pass_rate=1.0
  - human_speech_layer_dialogue_act_match_rate=1.0
  - human_speech_layer_anchor_hit_rate=1.0
  - human_blind_s0_count=19
  - human_blind_normalized_mean=0.6474
  - human_blind_strict_yes_rate=0.4737
  - human_blind_acceptable_rate=0.8947
  - human_feedback_regression_pass_rate=1.0
  - planner_contract_observed_group_hit_rate=0.8
  - planner_contract_current_group_hit_rate=1.0
  - planner_contract_group_hit_delta=0.2
- `證據鏈 / 可重現性`: `100.0` (weight=0.06)
  - formal benchmark report present
  - research social reasoning audit report present
  - cognitive architecture report present
  - memory report present
  - benchmark symbolic selector test present
  - human blind ratings, keys, candidate sheets and provenance hashes present
  - human feedback regression replay report present

## 優勢

- 正式 ToMBench 已提升到 0.975，社會推理不再是明顯弱點。
- left-brain 高頻 routing 仍維持 36/36 readiness 與 route regression 穩定。
- 工作記憶 relevance、delayed recall 與 runtime trace/self-correction 已形成可驗證證據鏈。
- Memory Causal Effect 已驗證記憶不是只被檢索，而是會改變回答並被顯性引用。
- 相對於 prompt-only baseline，雙腦架構在 relevance、emotion、boundary、consistency 上仍有顯著優勢。
- 未完成對話在模擬沉默後可完成一次性交付，且同一迴圈不會立即重複輸出。
- 真人盲評資料已從外部 CSV 匯入正式研究管線，並保留盲碼、來源雜湊與 matched-control 配對。

## 剩餘缺口

- DailyDialog act/emotion proxy 仍偏低，表示一般對話標籤對齊不是目前最強軸。
- DailyDialog act/emotion 是英文資料集上的 proxy，和本系統的三語角色對話不完全同域；後續應以人工標註的真實互動資料替代。
- Knowledge-Pretend Play Links 仍非滿分，是 ToM 細部殘留桶。
- 主動延續目前只有 5 個合格情境，100% 僅代表這個小型可歸因測試通過，尚不能外推所有對話。
- 真人盲評目前只有 19 筆 S0 樣本；正規化均分 0.6474、嚴格 yes 率 0.4737，仍未達完整聊天成熟門檻。
- 10 筆既有 fail-like 回放已通過語意契約，但這是回歸證據，不是新 holdout 的真人自然度證明。

## 關鍵證據快照

- `formal_tombench_accuracy`: 0.975
- `research_social_reasoning_pass_rate`: 1.0
- `leftbrain_readiness_pass_rate`: 1.0
- `delayed_recall_rate`: 1.0
- `working_memory_relevance_rate`: 0.9474
- `memory_causal_appropriate_effect_rate`: 1.0
- `unwanted_memory_intrusion_rate`: 0.0
- `autonomous_open_loop_eligible_count`: 5
- `autonomous_open_loop_detection_accuracy`: 1.0
- `autonomous_open_loop_key_accuracy`: 1.0
- `autonomous_open_loop_followup_rate`: 1.0
- `autonomous_proactive_semantic_match_rate`: 1.0
- `autonomous_proactive_delivery_rate`: 1.0
- `autonomous_proactive_memory_record_rate`: 1.0
- `autonomous_duplicate_suppression_rate`: 1.0
- `dialog_act_accuracy`: 0.3
- `emotion_accuracy`: 0.6167
- `diversity_unique_ratio`: 0.7604
- `stress_overall_pass_rate`: 1.0
- `stress_unique_reply_ratio`: 0.1306
- `stress_top_20_reply_concentration`: 0.2359
- `human_speech_layer_pass_rate`: 1.0
- `human_speech_layer_dialogue_act_match_rate`: 1.0
- `human_blind_s0_annotation_count`: 19
- `human_blind_s0_normalized_mean_score`: 0.6474
- `human_blind_s0_chat_ready_yes_rate`: 0.4737
- `human_blind_s0_chat_ready_acceptable_rate`: 0.8947
- `human_feedback_regression_overall_auto_pass_rate`: 1.0
- `planner_contract_observed_group_hit_rate`: 0.8
- `planner_contract_current_group_hit_rate`: 1.0
- `planner_contract_group_hit_delta`: 0.2
- `prompt_baseline_avg_score_delta`: 0.6851
- `mpi_stability_score`: 0.7554
