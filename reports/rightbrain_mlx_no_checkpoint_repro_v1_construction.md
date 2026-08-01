# RightBrain MLX 無 checkpoint 梯度探針

- 決策：`authorize_exact_three_no_checkpoint_mlx_repetitions_only`
- 唯一改動：gradient checkpointing true -> false
- 模型、adapter、dropout、dtype、資料、800-token 配置：固定
- optimizer step：0

- PASS `experiment_id`
- PASS `frozen_before_backward`
- PASS `frozen_bindings`
- PASS `environment_exact`
- PASS `exact_batch_ids`
- PASS `only_checkpoint_changed`
- PASS `model_adapter_environment_fixed`
- PASS `runner_exists`
- PASS `outputs_absent`
- PASS `zero_update_boundaries`
