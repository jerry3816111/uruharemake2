# RightBrain float16 梯度重現探針建構

- 決策：`authorize_exact_three_float16_zero_update_repetitions_only`
- 唯一改動：base activation `bfloat16 -> float16`
- checkpointing：保持開啟
- LoRA dropout：保持 `0.08`
- trainable adapter：保持 FP32
- optimizer step：`0`

- PASS `experiment_id`
- PASS `frozen_before_backward`
- PASS `frozen_bindings`
- PASS `exact_actual_first_batch`
- PASS `three_isolated_repetitions`
- PASS `eight_micro_steps_zero_updates`
- PASS `only_candidate_change_float16`
- PASS `local_memory_limit_30_gib`
- PASS `snapshot_exists`
- PASS `initial_adapter_config_match`
- PASS `initial_adapter_model_match`
- PASS `runner_exists`
- PASS `outputs_absent`
- PASS `zero_update_boundaries`
