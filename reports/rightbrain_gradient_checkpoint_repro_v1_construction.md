# RightBrain checkpointing 梯度重現探針建構

- 決策：`authorize_exact_three_checkpoint_off_zero_update_repetitions_only`
- 唯一改動：gradient checkpointing `on -> off`
- LoRA dropout：保持 `0.08`
- optimizer step：`0`
- 本機記憶體上限：`30 GiB`

- PASS `experiment_id`
- PASS `frozen_before_backward`
- PASS `frozen_bindings`
- PASS `exact_actual_first_batch_indices`
- PASS `exact_row_ids`
- PASS `three_isolated_repetitions`
- PASS `eight_micro_steps_zero_updates`
- PASS `only_candidate_change_checkpointing_off`
- PASS `local_memory_limit_30_gib`
- PASS `snapshot_exists`
- PASS `initial_adapter_config_match`
- PASS `initial_adapter_model_match`
- PASS `runner_exists`
- PASS `outputs_absent`
- PASS `zero_update_boundaries`
