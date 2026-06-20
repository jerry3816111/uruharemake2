# UruhaBrain vNext 研究 90+ 診斷報告

- 產生時間：`2026-06-20T17:32:23+09:00`
- 研究認知成熟度分數：`94.79`
- 是否可主張研究 90+：`True`
- 表面對話對齊分數：`85.32`

## 判定

此分數聚焦於『像人類一樣處理與組織回應』的認知架構研究成熟度，不等同於表面語氣或英語對話資料集單項分數。

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
- `Runtime 動態 / 自主循環`: `90.48` (weight=0.12)
  - trace_key_presence_rate=1.0
  - self_correction_rate=0.2581
  - planner_detected_issue_turn_rate=0.2581
  - planner_unresolved_issue_turn_rate=0.0
  - planner_resolution_quality_rate=1.0
  - planner_repair_success_rate=1.0
  - open_loop_turn_rate=0.3226
  - autonomous_success_rate=1.0
- `對 prompt-only baseline 的研究優勢`: `89.4` (weight=0.1)
  - avg_score_delta=0.6851
  - relevance_dual=0.875
  - emotion_dual=0.7364
  - boundary_dual=1.0
- `人格穩定性`: `75.54` (weight=0.06)
  - mpi_stability_score=0.7554
  - mpi_overall_trait_cv=0.2446
- `表面對話對齊`: `85.32` (weight=0.08)
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
- `證據鏈 / 可重現性`: `100.0` (weight=0.06)
  - formal benchmark report present
  - research social reasoning audit report present
  - cognitive architecture report present
  - memory report present
  - benchmark symbolic selector test present

## 優勢

- 正式 ToMBench 已提升到 0.975，社會推理不再是明顯弱點。
- left-brain 高頻 routing 仍維持 36/36 readiness 與 route regression 穩定。
- 工作記憶 relevance、delayed recall 與 runtime trace/self-correction 已形成可驗證證據鏈。
- Memory Causal Effect 已驗證記憶不是只被檢索，而是會改變回答並被顯性引用。
- 相對於 prompt-only baseline，雙腦架構在 relevance、emotion、boundary、consistency 上仍有顯著優勢。

## 剩餘缺口

- DailyDialog act/emotion proxy 仍偏低，表示一般對話標籤對齊不是目前最強軸。
- DailyDialog act/emotion 是英文資料集上的 proxy，和本系統的三語角色對話不完全同域；後續應以人工標註的真實互動資料替代。
- Knowledge-Pretend Play Links 仍非滿分，是 ToM 細部殘留桶。

## 關鍵證據快照

- `formal_tombench_accuracy`: 0.975
- `research_social_reasoning_pass_rate`: 1.0
- `leftbrain_readiness_pass_rate`: 1.0
- `delayed_recall_rate`: 1.0
- `working_memory_relevance_rate`: 0.9474
- `memory_causal_appropriate_effect_rate`: 1.0
- `unwanted_memory_intrusion_rate`: 0.0
- `dialog_act_accuracy`: 0.3
- `emotion_accuracy`: 0.6167
- `diversity_unique_ratio`: 0.7604
- `stress_overall_pass_rate`: 1.0
- `stress_unique_reply_ratio`: 0.1306
- `stress_top_20_reply_concentration`: 0.2359
- `human_speech_layer_pass_rate`: 1.0
- `human_speech_layer_dialogue_act_match_rate`: 1.0
- `prompt_baseline_avg_score_delta`: 0.6851
- `mpi_stability_score`: 0.7554
