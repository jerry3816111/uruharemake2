# RightBrain float16 梯度重現結果

- 判定：`float16_does_not_provide_a_usable_reproducible_path`
- 三次執行完成：`False`
- 量測：`{"successful_repeat_count": 1, "failures": [{"error_type": "RuntimeError", "message": "The total norm of order 2.0 for gradients from `parameters` is non-finite, so it cannot be clipped. To disable this error and scale the gradients by the non-finite norm anyway, set `error_if_nonfinite=False`", "out_of_memory": false, "nonfinite": true}, {"error_type": "RuntimeError", "message": "The total norm of order 2.0 for gradients from `parameters` is non-finite, so it cannot be clipped. To disable this error and scale the gradients by the non-finite norm anyway, set `error_if_nonfinite=False`", "out_of_memory": false, "nonfinite": true}], "peak_mps_driver_allocated_memory_bytes": [21343453184, 21343453184, 21343453184]}`
- optimizer step：`0`
- 正式 runtime 修改：`0`
