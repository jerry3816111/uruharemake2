# RightBrain max_norm 公平訓練試驗 v2 建構報告

- 決策：`authorize_exact_foreach_false_two_condition_pilot_only`
- 唯一訓練變因：`max_norm=0.3` 對 `3.0`
- 共通修正：兩組皆使用 `foreach=False`
- 評測前要求：第一批 raw norm 相對誤差不超過 `0.1%`
- 正式 runtime 修改：`0`

## 檢查

- PASS `experiment_id`
- PASS `frozen_before_training`
- PASS `exact_conditions`
- PASS `max_norm_values`
- PASS `foreach_false_for_both`
- PASS `same_dataset_80_rows`
- PASS `exact_80_micro_steps`
- PASS `exact_10_updates`
- PASS `frozen_bindings`
- PASS `holdout_source_separation`
- PASS `snapshot_exists`
- PASS `initial_adapter_config_match`
- PASS `initial_adapter_model_match`
- PASS `local_only`
- PASS `runner_exists`
- PASS `temporary_outputs_absent`
- PASS `generated_results_absent`
- PASS `no_production_authorization`
