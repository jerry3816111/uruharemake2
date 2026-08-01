# RightBrain MLX dropout=0 梯度探針建構

- 決策：`authorize_exact_three_mlx_dropout_zero_repetitions_only`
- 唯一改動：LoRA dropout 0.08 -> 0.0
- MLX、模型、adapter、batch、checkpointing：固定
- optimizer step：0

- PASS `experiment_id`
- PASS `frozen_before_backward`
- PASS `frozen_bindings`
- PASS `official_runtime_sources_bound`
- PASS `environment_exact`
- PASS `exact_batch_ids`
- PASS `only_probe_change_is_dropout`
- PASS `only_adapter_change_is_dropout`
- PASS `same_environment_and_model`
- PASS `runner_exists`
- PASS `outputs_absent`
- PASS `zero_update_boundaries`
