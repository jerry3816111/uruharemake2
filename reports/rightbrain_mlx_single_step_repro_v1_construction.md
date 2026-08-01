# RightBrain MLX 單步梯度定位探針

- 決策：`authorize_exact_three_single_step_mlx_repetitions_only`
- 改動：八步累加改成固定第一筆的單一步 backward
- 模型、adapter、dropout、dtype、800-token 配置、checkpointing：固定
- optimizer step：0

- PASS `experiment_id`
- PASS `frozen_before_backward`
- PASS `frozen_bindings`
- PASS `official_runtime_source_bound`
- PASS `environment_exact`
- PASS `exact_batch_ids`
- PASS `single_first_row_only`
- PASS `no_gradient_accumulation`
- PASS `only_localization_fields_changed`
- PASS `adapter_exactly_fixed`
- PASS `environment_and_model_exactly_fixed`
- PASS `runner_exists`
- PASS `outputs_absent`
- PASS `zero_update_boundaries`
