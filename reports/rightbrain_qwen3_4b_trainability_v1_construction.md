# RightBrain Qwen3-4B 可訓練性探針

- 決策：`authorize_exact_three_qwen3_4b_zero_update_repetitions_only`
- 模型：Qwen3-4B-Instruct-2507 官方固定快照
- adapter：全 36 層 rank-32 deterministic fresh LoRA
- 執行：固定一筆、無 checkpoint、零 optimizer step
- 人格與 production 修改：0

- PASS `experiment_id`
- PASS `frozen_before_backward`
- PASS `frozen_bindings`
- PASS `official_model_files_bound`
- PASS `environment_exact`
- PASS `official_model_metadata_exact`
- PASS `exact_batch_ids`
- PASS `dataset_provenance_safe`
- PASS `full_depth_lora`
- PASS `candidate_probe_contract`
- PASS `runner_exists`
- PASS `outputs_absent`
- PASS `zero_update_boundaries`
