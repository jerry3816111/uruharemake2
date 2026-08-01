# RightBrain max_norm 公平訓練試驗建構報告

- 結果：`authorize_exact_two_condition_pilot_only`
- 唯一變因：`max_norm=0.3` 對 `max_norm=3.0`
- 每組：80 micro-steps、10 optimizer updates、同一份資料與 seed
- 正式 runtime 修改：`0`

## 建構檢查

- PASS `experiment_id`
- PASS `frozen_before_training`
- PASS `exact_conditions`
- PASS `only_max_norm_differs`
- PASS `same_dataset_for_both_conditions`
- PASS `exact_micro_steps`
- PASS `exact_optimizer_updates`
- PASS `exact_gradient_accumulation`
- PASS `frozen_bindings`
- PASS `local_model_contract`
- PASS `holdout_source_separation`
- PASS `runner_exists`
- PASS `temporary_output_directories_absent`
- PASS `result_outputs_absent`
- PASS `no_production_authorization`

## 證據邊界

通過建構只允許執行兩個暫存 adapter 的小型試驗，不允許正式上線或人格相似度主張。
