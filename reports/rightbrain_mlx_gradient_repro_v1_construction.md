# RightBrain MLX 梯度重現探針建構

- 決策：`authorize_exact_three_mlx_zero_update_repetitions_only`
- 唯一改動：PyTorch MPS -> Apple MLX
- 基底與 adapter：保持 Qwen2.5-7B + v10
- checkpointing：保持開啟
- dropout：保持 0.08
- optimizer step：0

- PASS `experiment_id`
- PASS `frozen_before_backward`
- PASS `frozen_bindings`
- PASS `environment_file_exact`
- PASS `environment_runtime_exact`
- PASS `model_metadata_exact`
- PASS `exact_batch_ids`
- PASS `three_repetitions`
- PASS `eight_microsteps_zero_updates`
- PASS `single_backend_change`
- PASS `exact_adapter_mapping_contract`
- PASS `runner_exists`
- PASS `pre_backward_amendment_valid`
- PASS `outputs_absent`
- PASS `zero_update_boundaries`
