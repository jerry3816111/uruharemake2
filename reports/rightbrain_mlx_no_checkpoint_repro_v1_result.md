# RightBrain MLX 無 checkpoint 梯度結果

- 判定：`no_checkpoint_does_not_restore_reproducible_gradients`
- 下一定位：`isolate_mlx_kernel_buffer_or_dtype_without_checkpoint`
- 三次執行完成：`False`
- 量測：`{"successful_repeat_count": 0, "failures": [{"error_type": "RuntimeError", "message": "Non-finite MLX loss at repeat 1 micro-step 1", "out_of_memory": false, "nonfinite": true, "mapping_or_token_contract": false}, {"error_type": "RuntimeError", "message": "Non-finite MLX loss at repeat 2 micro-step 1", "out_of_memory": false, "nonfinite": true, "mapping_or_token_contract": false}, {"error_type": "RuntimeError", "message": "Non-finite MLX loss at repeat 3 micro-step 1", "out_of_memory": false, "nonfinite": true, "mapping_or_token_contract": false}], "peak_memory_bytes": [25334104398, 25334104398, 25334104398]}`
- optimizer step：`0`
- production 修改：`0`
